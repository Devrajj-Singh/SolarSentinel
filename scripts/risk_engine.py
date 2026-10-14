"""
SolarSentinel - Deterministic Risk & Decision Engine (Phase 5)
Evaluates scientific telemetry and AI reasoning against hard physical boundaries.
Enforces safety guardrails: AI reasoning cannot override physical thresholds.
"""

import os
import sys
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple


def load_json(filepath: str) -> Any:
    """Load JSON file handling utf-8-sig."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")
    with open(filepath, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def evaluate_event_risk(
    norm_event: Dict[str, Any],
    ai_assessment: Optional[Dict[str, Any]],
    config: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Applies deterministic space-weather risk rules.
    Cross-checks observational ground truth against AI suggestions.
    """
    event_id = norm_event.get("event_id")
    is_earth_directed = norm_event.get("is_earth_directed", False)
    speed = float(norm_event.get("speed_km_s") or 0.0)
    kp = float(norm_event.get("max_kp_predicted") or 0.0)
    arrival_time = norm_event.get("earth_arrival_time")

    # Extract AI recommendation if available
    ai_risk = "UNKNOWN"
    ai_confidence = 0.0
    ai_rationale = "No AI analysis available"
    if ai_assessment:
        rec = ai_assessment.get("risk_recommendation", {})
        ai_risk = rec.get("suggested_risk_level", "UNKNOWN").upper()
        ai_confidence = float(rec.get("confidence_score") or 0.0)
        ai_rationale = rec.get("primary_rationale", "")

    rule_triggers: List[str] = []
    final_risk: str = "LOW"
    routing_action: str = "AUTO_LOG"
    validation_status: str = "PASSED"

    # --- RULE SET 1: Non-Earth Directed Trajectory ---
    if not is_earth_directed:
        rule_triggers.append("RULE_NON_EARTH_DIRECTED: Off-axis CME trajectory, no direct terrestrial impact.")
        final_risk = "LOW"
        routing_action = "AUTO_LOG"
        if ai_risk in ("MEDIUM", "HIGH"):
            validation_status = "OVERRIDDEN_BY_RULE"
            rule_triggers.append(f"OVERRIDE: AI suggested {ai_risk} for off-axis CME. Downgraded to LOW by physical trajectory constraint.")

    # --- RULE SET 2: Earth-Directed Physical Thresholds ---
    else:
        rule_triggers.append("RULE_EARTH_DIRECTED: Interplanetary shock heading toward Earth.")

        # Severe / Extreme Geomagnetic Storm Threshold (Kp >= 7 or Speed >= 1500 km/s)
        if kp >= 7.0 or speed >= 1500.0:
            final_risk = "HIGH"
            routing_action = "HUMAN_APPROVAL_REQUIRED"
            rule_triggers.append(f"RULE_HIGH_SEVERITY: Severe conditions detected (Kp={kp}, Speed={speed:.1f} km/s). Requires human operator sign-off.")
            if ai_risk != "HIGH":
                validation_status = "OVERRIDDEN_BY_RULE"
                rule_triggers.append(f"OVERRIDE: AI suggested {ai_risk}. Escalated to HIGH by physical threshold.")

        # Moderate Geomagnetic Storm Threshold (Kp 5.0 - 6.9 or Speed 700 - 1499 km/s)
        elif kp >= 5.0 or speed >= 700.0:
            final_risk = "MEDIUM"
            routing_action = "OPERATOR_REVIEW"
            rule_triggers.append(f"RULE_ELEVATED_ACTIVITY: Moderate disturbance expected (Kp={kp}, Speed={speed:.1f} km/s). G1/G2 threshold reached.")
            if ai_risk == "LOW":
                validation_status = "OVERRIDDEN_BY_RULE"
                rule_triggers.append("OVERRIDE: AI suggested LOW for Kp >= 5.0 / Speed >= 700 km/s. Escalated to MEDIUM.")
            elif ai_risk == "HIGH":
                # If AI detected complex secondary factors (e.g. active region flare sequence)
                final_risk = "HIGH"
                routing_action = "HUMAN_APPROVAL_REQUIRED"
                rule_triggers.append("AI_ELEVATION_ACCEPTED: AI recommended HIGH risk based on secondary factors.")

        # Low Activity / Minor Disturbance (Kp < 5.0 and Speed < 700 km/s)
        else:
            final_risk = "LOW"
            routing_action = "AUTO_LOG"
            rule_triggers.append(f"RULE_QUIET_CONDITIONS: Below geomagnetic storm threshold (Kp={kp}, Speed={speed:.1f} km/s). G0 conditions.")
            if ai_risk in ("MEDIUM", "HIGH"):
                # Check AI confidence
                if ai_confidence >= 0.85:
                    final_risk = "MEDIUM"
                    routing_action = "OPERATOR_REVIEW"
                    rule_triggers.append("AI_MARGINAL_ELEVATION: AI detected cautionary factors with high confidence. Elevated to MEDIUM for safety.")
                else:
                    validation_status = "OVERRIDDEN_BY_RULE"
                    rule_triggers.append(f"OVERRIDE: AI suggested {ai_risk} without sufficient telemetry evidence. Downgraded to LOW.")

    # --- RULE SET 3: AI Low Confidence Guardrail ---
    if ai_assessment and ai_confidence < 0.50:
        validation_status = "FLAGGED_INCONSISTENCY"
        rule_triggers.append(f"GUARDRAIL_LOW_CONFIDENCE: AI confidence score ({ai_confidence:.2f}) is below acceptable threshold (0.50).")
        if final_risk == "LOW":
            final_risk = "MEDIUM"
            routing_action = "OPERATOR_REVIEW"

    return {
        "event_id": event_id,
        "event_type": norm_event.get("event_type", "CME"),
        "start_time": norm_event.get("start_time"),
        "source_location": norm_event.get("source_location"),
        "is_earth_directed": is_earth_directed,
        "speed_km_s": speed,
        "max_kp_predicted": kp,
        "earth_arrival_time": arrival_time,
        "ai_suggested_risk": ai_risk,
        "ai_confidence_score": ai_confidence,
        "ai_rationale": ai_rationale,
        "deterministic_risk": final_risk,
        "routing_action": routing_action,
        "validation_status": validation_status,
        "rule_triggers": rule_triggers,
        "evaluated_at": datetime.now(timezone.utc).isoformat()
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SolarSentinel Phase 5: Deterministic Risk & Decision Engine")
    parser.add_argument("--normalized", default="data/raw/cme_normalized.json", help="Path to normalized events JSON")
    parser.add_argument("--ai-analysis", default="data/processed/cme_ai_analysis.json", help="Path to AI analysis JSON")
    parser.add_argument("--config", default="config/settings.json", help="Path to settings JSON")
    parser.add_argument("--output", default="data/processed/risk_assessment.json", help="Output path for risk assessment")
    args = parser.parse_args()

    print("=======================================================")
    print(" SolarSentinel - Phase 5: Deterministic Risk Engine    ")
    print("=======================================================")

    # Load normalized events
    normalized_events = load_json(args.normalized)
    print(f"[INFO] Loaded {len(normalized_events)} normalized events from {args.normalized}")

    # Load AI analysis results (keyed by event_id)
    ai_map = {}
    if os.path.exists(args.ai_analysis):
        ai_records = load_json(args.ai_analysis)
        for rec in ai_records:
            if "event_id" in rec:
                ai_map[rec["event_id"]] = rec
        print(f"[INFO] Loaded {len(ai_map)} AI assessments from {args.ai_analysis}")
    else:
        print(f"[WARN] AI analysis file not found at {args.ai_analysis}. Operating on physical rules only.")

    # Evaluate all events
    assessments = []
    risk_summary = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    action_summary = {"AUTO_LOG": 0, "OPERATOR_REVIEW": 0, "HUMAN_APPROVAL_REQUIRED": 0}

    for event in normalized_events:
        eid = event.get("event_id")
        ai_data = ai_map.get(eid)
        result = evaluate_event_risk(event, ai_data, {})
        assessments.append(result)

        risk = result["deterministic_risk"]
        action = result["routing_action"]
        risk_summary[risk] = risk_summary.get(risk, 0) + 1
        action_summary[action] = action_summary.get(action, 0) + 1

    # Save consolidated risk assessments
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(assessments, f, indent=2)

    print(f"\n[SUCCESS] Wrote {len(assessments)} risk evaluations to {args.output}")
    print("\n---------------- Risk Breakdown ----------------")
    for rk, count in risk_summary.items():
        print(f"  {rk:8s}: {count:2d} events")
    print("\n--------------- Routing Actions ----------------")
    for act, count in action_summary.items():
        print(f"  {act:25s}: {count:2d} events")

    # Display Earth-directed details
    earth_events = [a for a in assessments if a["is_earth_directed"]]
    print(f"\n--- Earth-Directed Events Detail ({len(earth_events)}) ---")
    for ev in earth_events:
        print(f"Event ID: {ev['event_id']}")
        print(f"  Speed: {ev['speed_km_s']} km/s | Max Kp: {ev['max_kp_predicted']} | Arrival: {ev['earth_arrival_time']}")
        print(f"  AI Suggestion: {ev['ai_suggested_risk']} (Confidence: {ev['ai_confidence_score']:.2f})")
        print(f"  Final Risk   : {ev['deterministic_risk']} -> Action: {ev['routing_action']}")
        print(f"  Status       : {ev['validation_status']}")
        for trigger in ev["rule_triggers"]:
            print(f"    - {trigger}")
        print()


if __name__ == "__main__":
    main()
