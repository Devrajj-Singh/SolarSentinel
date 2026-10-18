"""
SolarSentinel - End-to-End Pipeline Orchestrator (Phase 7)
Orchestrates:
  1. Data Ingestion & Normalization Verification
  2. AI Scientific Reasoning (GPT-OSS 120B on Groq)
  3. Deterministic Safety & Risk Engine
  4. Master Excel Logging & Executive Space Weather Report Generation
  5. Operational Alert Dispatch & Human-in-the-Loop Routing
"""

import os
import sys
import subprocess
import json
from datetime import datetime, timezone

# Ensure stdout handles UTF-8 on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def print_banner(text: str):
    print("\n" + "=" * 64)
    print(f"  {text}")
    print("=" * 64)


def run_step(step_name: str, cmd: list):
    print(f"\n[RUNNING STEP] {step_name}...")
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print(f"[ERROR] Step failed with code {res.returncode}:")
        print(res.stderr)
        sys.exit(res.returncode)
    print(res.stdout)


def main():
    print_banner("[SOLARSENTINEL V2] Autonomous Operations & Intelligence Pipeline")
    print(f"Execution Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # 1. NOAA SWPC Live Ingestion
    run_step(
        "Step 1: NOAA SWPC Real-Time Geomagnetic Ingestion",
        [sys.executable, "scripts/fetch_noaa.py"]
    )

    # 2. Idempotent Transaction Enqueueing
    run_step(
        "Step 2: Idempotent Deduplication & Queue Management",
        [sys.executable, "scripts/queue_manager.py", "enqueue", "--input", "data/raw/cme_normalized.json"]
    )

    # 3. AI Scientific Analysis Layer
    run_step(
        "Step 3: GPT-OSS 120B AI Scientific Analysis (Groq LPU)",
        [sys.executable, "scripts/analyze_events.py"]
    )

    # 4. Deterministic Risk Engine
    run_step(
        "Step 4: Deterministic Risk & Decision Engine (NOAA Scales)",
        [sys.executable, "scripts/risk_engine.py"]
    )

    # 5. Asset Registry Screening Matcher
    run_step(
        "Step 5: Operational Asset Impact Screening",
        [sys.executable, "scripts/match_assets.py"]
    )

    # 6. Incident Management Creation
    run_step(
        "Step 6: Space Weather Incident Dossier Generation",
        [sys.executable, "scripts/incident_manager.py", "create-batch"]
    )

    # 7. Multi-Channel Notification Dispatcher
    run_step(
        "Step 7: Multi-Channel Alert Dispatch & Local Mock Inbox",
        [sys.executable, "scripts/notify.py", "notify-all"]
    )

    # 8. Master Multi-Tab Excel Logging & Executive Report
    run_step(
        "Step 8: Master Excel Logging & Executive Space Weather Report",
        [sys.executable, "scripts/generate_reports.py"]
    )

    # 9. Finalize Run State
    run_step(
        "Step 9: State Store Commit & Metrics Finalization",
        [sys.executable, "scripts/queue_manager.py", "finalize-run", "--status", "HEALTHY"]
    )

    print_banner("[SUCCESS] SolarSentinel V2 Pipeline Execution Complete")
    print("Generated Artifacts & Output Locations:")
    print("  * Master Excel Log   : output/logs/events_log.xlsx (3 Styled Tabs)")
    print("  * Executive Report   : output/reports/space_weather_report_*.md")
    print("  * Local Mock Inbox   : output/emails/ (Rendered HTML & Plaintext Alerts)")
    print("  * Webhook Payloads   : output/audit/ (MS Teams / Slack Adaptive Cards)")
    print("  * Incident Dossiers  : data/incidents/ (Immutable Audit Trails)")
    print("  * Transaction Queue  : data/queue/ (Pending / In-Progress / Completed)")
    print("  * Operations Center  : Run 'python scripts/control_center.py' for Live Dashboard")


if __name__ == "__main__":
    main()
