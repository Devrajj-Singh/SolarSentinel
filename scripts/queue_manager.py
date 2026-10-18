"""
SolarSentinel - Local Transaction Queue & State Manager (Phase V2.1)
Provides an idempotent, transactional queue abstraction matching UiPath Queue semantics.
"""

import os
import sys
import json
import hashlib
import shutil
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

QUEUE_DIR = "data/queue"
PENDING_DIR = os.path.join(QUEUE_DIR, "pending")
IN_PROGRESS_DIR = os.path.join(QUEUE_DIR, "in_progress")
COMPLETED_DIR = os.path.join(QUEUE_DIR, "completed")
FAILED_DIR = os.path.join(QUEUE_DIR, "failed")
STATE_FILE = "data/state/monitor_state.json"


def ensure_queue_dirs():
    """Ensure all queue and state directories exist."""
    for d in [PENDING_DIR, IN_PROGRESS_DIR, COMPLETED_DIR, FAILED_DIR, os.path.dirname(STATE_FILE)]:
        os.makedirs(d, exist_ok=True)


def load_state() -> Dict[str, Any]:
    """Load monitor state with fallback defaults."""
    ensure_queue_dirs()
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_successful_run": None,
        "last_event_timestamp": None,
        "processed_event_ids": [],
        "event_checksums": {},
        "consecutive_failures": 0,
        "system_health": "HEALTHY",
        "total_runs": 0,
        "total_transactions_processed": 0
    }


def save_state(state: Dict[str, Any]):
    """Persist monitor state atomically."""
    ensure_queue_dirs()
    temp_file = STATE_FILE + ".tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    shutil.move(temp_file, STATE_FILE)


def compute_event_checksum(event: Dict[str, Any]) -> str:
    """Compute a deterministic hash for an event to detect updates."""
    # Hash key scientific metrics
    core_keys = ["event_id", "speed_km_s", "half_angle_deg", "is_earth_directed", "earth_arrival_time", "max_kp_predicted"]
    sub = {k: event.get(k) for k in core_keys}
    s = json.dumps(sub, sort_keys=True)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def enqueue_new_events(events: List[Dict[str, Any]], force_all: bool = False) -> List[str]:
    """
    Compare events against monitor_state.json.
    Enqueue only new or updated events into data/queue/pending/.
    Returns list of newly enqueued transaction IDs.
    """
    ensure_queue_dirs()
    state = load_state()
    processed_ids = set(state.get("processed_event_ids", []))
    checksums = state.get("event_checksums", {})

    # Check active queue items (pending or in_progress) to avoid duplicate queueing
    active_eids = set()
    for q_dir in [PENDING_DIR, IN_PROGRESS_DIR]:
        for fname in os.listdir(q_dir):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(q_dir, fname), "r", encoding="utf-8") as f:
                        q_data = json.load(f)
                        if "event_id" in q_data:
                            active_eids.add(q_data["event_id"])
                except Exception:
                    pass

    enqueued_txns = []

    for event in events:
        eid = event.get("event_id")
        if not eid:
            continue

        if eid in active_eids and not force_all:
            continue

        chk = compute_event_checksum(event)
        is_new = eid not in processed_ids
        is_updated = (not is_new) and (checksums.get(eid) != chk)

        if is_new or is_updated or force_all:
            # Create a clean transaction item
            now_iso = datetime.now(timezone.utc).isoformat()
            ts_code = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
            safe_eid = eid.replace(":", "-")
            txn_id = f"TXN-{ts_code}-{safe_eid}"

            txn_payload = {
                "transaction_id": txn_id,
                "event_id": eid,
                "status": "NEW",
                "attempt_count": 0,
                "max_retries": 3,
                "created_at": now_iso,
                "started_at": None,
                "completed_at": None,
                "checksum": chk,
                "is_update": is_updated,
                "error_message": None,
                "payload": event
            }

            txn_path = os.path.join(PENDING_DIR, f"{txn_id}.json")
            with open(txn_path, "w", encoding="utf-8") as f:
                json.dump(txn_payload, f, indent=2)

            enqueued_txns.append(txn_id)

    return enqueued_txns


def get_next_transaction() -> Optional[Dict[str, Any]]:
    """
    Pops the next pending transaction and transitions it to IN_PROGRESS.
    Thread-safe and atomic file movement.
    """
    ensure_queue_dirs()
    pending_files = sorted([f for f in os.listdir(PENDING_DIR) if f.endswith(".json")])
    if not pending_files:
        return None

    target_file = pending_files[0]
    src_path = os.path.join(PENDING_DIR, target_file)
    dst_path = os.path.join(IN_PROGRESS_DIR, target_file)

    try:
        shutil.move(src_path, dst_path)
    except Exception as e:
        # File might have been claimed by another process
        return None

    with open(dst_path, "r", encoding="utf-8") as f:
        txn = json.load(f)

    txn["status"] = "PROCESSING"
    txn["started_at"] = datetime.now(timezone.utc).isoformat()
    txn["attempt_count"] = txn.get("attempt_count", 0) + 1

    with open(dst_path, "w", encoding="utf-8") as f:
        json.dump(txn, f, indent=2)

    return txn


def update_transaction_status(txn_id: str, status: str, error_msg: Optional[str] = None):
    """Update in-progress transaction status."""
    ensure_queue_dirs()
    file_path = os.path.join(IN_PROGRESS_DIR, f"{txn_id}.json")
    if not os.path.exists(file_path):
        return

    with open(file_path, "r", encoding="utf-8") as f:
        txn = json.load(f)

    txn["status"] = status
    if error_msg:
        txn["error_message"] = error_msg
    txn["updated_at"] = datetime.now(timezone.utc).isoformat()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(txn, f, indent=2)


def complete_transaction(txn_id: str, results_summary: Optional[Dict[str, Any]] = None):
    """Mark transaction COMPLETED and move to completed directory."""
    ensure_queue_dirs()
    src = os.path.join(IN_PROGRESS_DIR, f"{txn_id}.json")
    dst = os.path.join(COMPLETED_DIR, f"{txn_id}.json")

    if not os.path.exists(src):
        return

    with open(src, "r", encoding="utf-8") as f:
        txn = json.load(f)

    txn["status"] = "COMPLETED"
    txn["completed_at"] = datetime.now(timezone.utc).isoformat()
    if results_summary:
        txn["results_summary"] = results_summary

    with open(src, "w", encoding="utf-8") as f:
        json.dump(txn, f, indent=2)

    shutil.move(src, dst)

    # Update state
    state = load_state()
    eid = txn.get("event_id")
    chk = txn.get("checksum")
    if eid and eid not in state.get("processed_event_ids", []):
        state["processed_event_ids"].append(eid)
    if eid and chk:
        state["event_checksums"][eid] = chk
    state["total_transactions_processed"] = state.get("total_transactions_processed", 0) + 1
    save_state(state)


def fail_transaction(txn_id: str, error_msg: str):
    """Mark transaction FAILED or requeue if attempts remain."""
    ensure_queue_dirs()
    src = os.path.join(IN_PROGRESS_DIR, f"{txn_id}.json")
    if not os.path.exists(src):
        return

    with open(src, "r", encoding="utf-8") as f:
        txn = json.load(f)

    txn["error_message"] = error_msg
    attempts = txn.get("attempt_count", 1)
    max_retries = txn.get("max_retries", 3)

    if attempts < max_retries:
        txn["status"] = "RETRY"
        dst = os.path.join(PENDING_DIR, f"{txn_id}.json")
        with open(src, "w", encoding="utf-8") as f:
            json.dump(txn, f, indent=2)
        shutil.move(src, dst)
    else:
        txn["status"] = "FAILED"
        txn["completed_at"] = datetime.now(timezone.utc).isoformat()
        dst = os.path.join(FAILED_DIR, f"{txn_id}.json")
        with open(src, "w", encoding="utf-8") as f:
            json.dump(txn, f, indent=2)
        shutil.move(src, dst)


def get_queue_metrics() -> Dict[str, int]:
    """Return count of items in each queue state."""
    ensure_queue_dirs()
    return {
        "pending": len([f for f in os.listdir(PENDING_DIR) if f.endswith(".json")]),
        "in_progress": len([f for f in os.listdir(IN_PROGRESS_DIR) if f.endswith(".json")]),
        "completed": len([f for f in os.listdir(COMPLETED_DIR) if f.endswith(".json")]),
        "failed": len([f for f in os.listdir(FAILED_DIR) if f.endswith(".json")])
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SolarSentinel Local Transaction Queue Manager")
    subparsers = parser.add_subparsers(dest="command")

    # Command: status
    subparsers.add_parser("status", help="Display queue counts and monitor state")

    # Command: enqueue
    enqueue_p = subparsers.add_parser("enqueue", help="Enqueue new/updated events from normalized JSON")
    enqueue_p.add_argument("--input", default="data/raw/cme_normalized.json", help="Path to normalized events")
    enqueue_p.add_argument("--force", action="store_true", help="Force enqueue all events even if processed")

    # Command: get-next
    subparsers.add_parser("get-next", help="Pop and return the next pending transaction JSON")

    # Command: complete
    complete_p = subparsers.add_parser("complete", help="Mark transaction as COMPLETED")
    complete_p.add_argument("--txn-id", required=True, help="Transaction ID")

    # Command: fail
    fail_p = subparsers.add_parser("fail", help="Mark transaction as FAILED / RETRY")
    fail_p.add_argument("--txn-id", required=True, help="Transaction ID")
    fail_p.add_argument("--error", default="Unknown error", help="Error description")

    # Command: finalize-run
    final_p = subparsers.add_parser("finalize-run", help="Update state timestamps and complete run")
    final_p.add_argument("--status", default="HEALTHY", help="Run status")

    args = parser.parse_args()

    if args.command == "status":
        metrics = get_queue_metrics()
        state = load_state()
        print("=== SolarSentinel Queue & State Monitor ===")
        print(f"System Health       : {state.get('system_health')}")
        print(f"Last Successful Run : {state.get('last_successful_run') or 'Never'}")
        print(f"Processed Event IDs : {len(state.get('processed_event_ids', []))}")
        print(f"Total Transactions  : {state.get('total_transactions_processed', 0)}")
        print("\n--- Queue Counters ---")
        print(f"  Pending           : {metrics['pending']}")
        print(f"  In-Progress       : {metrics['in_progress']}")
        print(f"  Completed         : {metrics['completed']}")
        print(f"  Failed            : {metrics['failed']}")

    elif args.command == "enqueue":
        if not os.path.exists(args.input):
            print(f"[ERROR] Input file {args.input} does not exist.")
            sys.exit(1)
        with open(args.input, "r", encoding="utf-8-sig") as f:
            events = json.load(f)
        txns = enqueue_new_events(events, force_all=args.force)
        print(f"[SUCCESS] Evaluated {len(events)} events. Enqueued {len(txns)} new/updated transactions.")
        for tid in txns:
            print(f"  + Enqueued: {tid}")

    elif args.command == "get-next":
        txn = get_next_transaction()
        if txn:
            print(json.dumps(txn, indent=2))
        else:
            print("NO_ITEMS")

    elif args.command == "complete":
        complete_transaction(args.txn_id)
        print(f"[SUCCESS] Transaction {args.txn_id} marked as COMPLETED.")

    elif args.command == "fail":
        fail_transaction(args.txn_id, args.error)
        print(f"[SUCCESS] Transaction {args.txn_id} processed with failure: {args.error}")

    elif args.command == "finalize-run":
        state = load_state()
        state["last_successful_run"] = datetime.now(timezone.utc).isoformat()
        state["system_health"] = args.status
        state["total_runs"] = state.get("total_runs", 0) + 1
        save_state(state)
        print(f"[SUCCESS] Updated monitor state. Total runs: {state['total_runs']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()