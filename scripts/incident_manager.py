"""
SolarSentinel - Space Weather Incident Management Subsystem (Phase V2.2)
Creates, tracks, and manages operational incidents for space-weather threats and asset impacts.
Provides immutable audit trails and supports human-in-the-loop approval workflows.
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

INCIDENTS_DIR = "data/incidents"


def ensure_incident_dir():
    """Ensure data/incidents directory exists."""
    os.makedirs(INCIDENTS_DIR, exist_ok=True)


def generate_incident_id(event_id: str) -> str:
    """Deterministic, clean incident ID."""
    date_prefix = datetime.now(timezone.utc).strftime("%Y%m%d")
    safe_eid = event_id.replace(":", "-")
    return f"INC-{date_prefix}-{safe_eid}"


def create_incident_record(
    event_assessment: Dict[str, Any],
    asset_match: Optional[Dict[str, Any]] = None,
    ai_analysis: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Construct a complete incident dossier.
    Sets severity and approval gating based on physical scales and asset criticality.
    """
    event_id = event_assessment.get("event_id", "UNKNOWN_EVENT")
    inc_id = generate_incident_id(event_id)
    now_iso = datetime.now(timezone.utc).isoformat()

    risk_level = event_assessment.get("risk_level") or event_assessment.get("deterministic_risk") or "LOW"
    if isinstance(risk_level, dict):
        risk_level = risk_level.get("final_risk_level", "LOW")
    risk_level = str(risk_level).upper()

    kp = float(event_assessment.get("max_kp_predicted") or 0.0)
    speed = float(event_assessment.get("speed_km_s") or 0.0)
    g_scale = event_assessment.get("g_scale", "G0")
    is_earth_directed = bool(event_assessment.get("is_earth_directed", False))

    affected_assets = []
    if asset_match and "asset_matches" in asset_match:
        affected_assets = [m for m in asset_match["asset_matches"] if m.get("impact_status") != "NOMINAL"]

    # Evaluate incident severity
    has_critical_asset = any(a.get("criticality") == "CRITICAL" and a.get("impact_status") == "POTENTIALLY_AFFECTED" for a in affected_assets)
    if risk_level == "HIGH" or kp >= 7.0 or has_critical_asset:
        severity = "HIGH"
        status = "AWAITING_APPROVAL"
        approval_required = True
    elif risk_level == "MEDIUM" or kp >= 5.0 or len(affected_assets) > 0:
        severity = "MEDIUM"
        status = "INVESTIGATING"
        approval_required = False
    else:
        severity = "LOW"
        status = "OPEN"
        approval_required = False

    # Extract AI rationale if present
    ai_summary = "Deterministic physical evaluation only."
    if ai_analysis and "scientific_assessment" in ai_analysis:
        ai_summary = ai_analysis["scientific_assessment"].get("coronal_features_summary", "")

    # Compile SOP mitigations
    mitigations = []
    for a in affected_assets:
        sop = a.get("mitigation_sop")
        if sop:
            mitigations.append({
                "asset_id": a.get("asset_id"),
                "asset_name": a.get("name"),
                "status": a.get("impact_status"),
                "operator": a.get("operator"),
                "contact_email": a.get("contact_email"),
                "sop_action": sop
            })

    incident = {
        "incident_id": inc_id,
        "event_id": event_id,
        "created_at": now_iso,
        "updated_at": now_iso,
        "severity": severity,
        "status": status,
        "title": f"Space Weather Hazard: {severity} Risk ({g_scale} / Kp {kp:.1f}) for {event_id}",
        "hazard_summary": {
            "speed_km_s": speed,
            "max_kp_predicted": kp,
            "g_scale": g_scale,
            "is_earth_directed": is_earth_directed,
            "earth_arrival_time": event_assessment.get("earth_arrival_time"),
            "risk_tier": risk_level
        },
        "ai_intelligence_brief": ai_summary,
        "affected_assets_count": len(affected_assets),
        "affected_assets": mitigations,
        "approval_record": {
            "required": approval_required,
            "status": "PENDING" if approval_required else "NOT_REQUIRED",
            "decided_by": None,
            "decision_time": None,
            "operational_notes": None
        },
        "audit_history": [
            {
                "timestamp": now_iso,
                "actor": "SolarSentinel Autonomous Engine",
                "action": "INCIDENT_CREATED",
                "notes": f"Incident initialized with severity={severity}, status={status}."
            }
        ]
    }

    return incident


def save_incident(incident: Dict[str, Any]) -> str:
    """Save incident to data/incidents/."""
    ensure_incident_dir()
    inc_id = incident["incident_id"]
    filepath = os.path.join(INCIDENTS_DIR, f"{inc_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(incident, f, indent=2)
    return filepath


def load_incident(inc_id: str) -> Optional[Dict[str, Any]]:
    """Load an incident by ID."""
    ensure_incident_dir()
    filepath = os.path.join(INCIDENTS_DIR, f"{inc_id}.json")
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def list_incidents() -> List[Dict[str, Any]]:
    """List all incident records in data/incidents/."""
    ensure_incident_dir()
    records = []
    for fname in sorted(os.listdir(INCIDENTS_DIR)):
        if fname.endswith(".json") and fname.startswith("INC-"):
            try:
                with open(os.path.join(INCIDENTS_DIR, fname), "r", encoding="utf-8-sig") as f:
                    records.append(json.load(f))
            except Exception:
                pass
    return records


def approve_incident(inc_id: str, operator_name: str, notes: str) -> bool:
    """Record operator approval for an incident."""
    inc = load_incident(inc_id)
    if not inc:
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    inc["status"] = "RESOLVED"
    inc["updated_at"] = now_iso
    inc["approval_record"] = {
        "required": True,
        "status": "APPROVED",
        "decided_by": operator_name,
        "decision_time": now_iso,
        "operational_notes": notes
    }
    inc["audit_history"].append({
        "timestamp": now_iso,
        "actor": operator_name,
        "action": "OPERATOR_APPROVED",
        "notes": f"Operator approval granted: {notes}"
    })

    save_incident(inc)
    return True


def reject_incident(inc_id: str, operator_name: str, notes: str) -> bool:
    """Record operator rejection (false positive / nominal downgrade)."""
    inc = load_incident(inc_id)
    if not inc:
        return False

    now_iso = datetime.now(timezone.utc).isoformat()
    inc["status"] = "CLOSED"
    inc["updated_at"] = now_iso
    inc["approval_record"] = {
        "required": True,
        "status": "REJECTED",
        "decided_by": operator_name,
        "decision_time": now_iso,
        "operational_notes": notes
    }
    inc["audit_history"].append({
        "timestamp": now_iso,
        "actor": operator_name,
        "action": "OPERATOR_REJECTED",
        "notes": f"Operator marked incident rejected: {notes}"
    })

    save_incident(inc)
    return True


def main():
    parser = argparse.ArgumentParser(description="SolarSentinel Incident Management Controller")
    subparsers = parser.add_subparsers(dest="command")

    # Command: generate-from-assessment
    gen_p = subparsers.add_parser("create-batch", help="Generate incidents from assessed events & asset matches")
    gen_p.add_argument("--assessments", default="data/sample/risk_assessment_sample.json", help="Path to risk assessments")
    gen_p.add_argument("--impacts", default="data/processed/asset_impacts.json", help="Path to asset impacts")

    # Command: list
    subparsers.add_parser("list", help="List all incident records")

    # Command: get
    get_p = subparsers.add_parser("get", help="Get incident details")
    get_p.add_argument("--incident-id", required=True, help="Incident ID")

    # Command: approve
    app_p = subparsers.add_parser("approve", help="Approve an incident")
    app_p.add_argument("--incident-id", required=True, help="Incident ID")
    app_p.add_argument("--operator", default="Duty Flight Director", help="Operator name/callsign")
    app_p.add_argument("--notes", default="Approved response protocol.", help="Sign-off notes")

    # Command: reject
    rej_p = subparsers.add_parser("reject", help="Reject an incident")
    rej_p.add_argument("--incident-id", required=True, help="Incident ID")
    rej_p.add_argument("--operator", default="Duty Flight Director", help="Operator name/callsign")
    rej_p.add_argument("--notes", default="Deemed non-hazardous after telemetry review.", help="Rejection rationale")

    args = parser.parse_args()

    if args.command == "create-batch":
        ensure_incident_dir()
        if not os.path.exists(args.assessments):
            print(f"[ERROR] Assessments file not found: {args.assessments}")
            sys.exit(1)

        with open(args.assessments, "r", encoding="utf-8-sig") as f:
            assessments = json.load(f)

        impacts_by_eid = {}
        if os.path.exists(args.impacts):
            with open(args.impacts, "r", encoding="utf-8-sig") as f:
                impact_data = json.load(f)
                for item in impact_data:
                    impacts_by_eid[item.get("event_id")] = item

        created_count = 0
        for ev in assessments:
            eid = ev.get("event_id")
            impact = impacts_by_eid.get(eid)
            # Only create incident if event is elevated (MEDIUM / HIGH) or has affected assets
            risk = ev.get("deterministic_risk", "LOW")
            if isinstance(risk, dict):
                risk = risk.get("final_risk_level", "LOW")

            affected_cnt = impact.get("potentially_affected_count", 0) if impact else 0
            if risk in ("MEDIUM", "HIGH") or affected_cnt > 0:
                inc = create_incident_record(ev, impact)
                save_incident(inc)
                created_count += 1
                print(f"  + Created {inc['incident_id']} [Severity: {inc['severity']} | Status: {inc['status']}]")

        print(f"[SUCCESS] Created {created_count} operational incident files in {INCIDENTS_DIR}/.")

    elif args.command == "list":
        incidents = list_incidents()
        print(f"=== SolarSentinel Incident Registry ({len(incidents)} Incidents) ===")
        for inc in incidents:
            print(f"[{inc['severity']}] {inc['incident_id']} | Status: {inc['status']} | Event: {inc['event_id']}")
            print(f"      Title: {inc['title']}")
            print(f"      Assets: {inc['affected_assets_count']} | Approval: {inc['approval_record']['status']}")

    elif args.command == "get":
        inc = load_incident(args.incident_id)
        if not inc:
            print(f"[ERROR] Incident {args.incident_id} not found.")
            sys.exit(1)
        print(json.dumps(inc, indent=2))

    elif args.command == "approve":
        if approve_incident(args.incident_id, args.operator, args.notes):
            print(f"[SUCCESS] Incident {args.incident_id} APPROVED by {args.operator}.")
        else:
            print(f"[ERROR] Failed to approve incident {args.incident_id}.")

    elif args.command == "reject":
        if reject_incident(args.incident_id, args.operator, args.notes):
            print(f"[SUCCESS] Incident {args.incident_id} REJECTED by {args.operator}.")
        else:
            print(f"[ERROR] Failed to reject incident {args.incident_id}.")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
