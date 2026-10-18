"""
SolarSentinel - Asset-Aware Impact Matching Engine (Phase V2.2)
Cross-references detected space-weather hazards against the Operational Asset Registry.
Produces defensive, conservative operational screening assessments.
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional

REGISTRY_FILE = "config/asset_registry.json"
DEFAULT_INPUT = "data/processed/risk_assessment.json"
DEFAULT_OUTPUT = "data/processed/asset_impacts.json"


def parse_scale_level(scale_str: str) -> int:
    """Parse G2 -> 2, S3 -> 3, R1 -> 1, G0 -> 0."""
    if not scale_str or len(scale_str) < 2:
        return 0
    try:
        return int(scale_str[1:])
    except ValueError:
        return 0


def load_asset_registry(registry_path: str = REGISTRY_FILE) -> List[Dict[str, Any]]:
    """Load operational asset definitions."""
    if not os.path.exists(registry_path):
        raise FileNotFoundError(f"Asset registry not found at {registry_path}")
    with open(registry_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
        return data.get("assets", [])


def screen_asset_for_event(asset: Dict[str, Any], event_assessment: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate whether a space weather event meets or approaches an asset's vulnerability thresholds.
    Adheres to conservative, defensive space operations terminology.
    """
    thresholds = asset.get("screening_thresholds", {})
    
    # Event parameters
    speed = float(event_assessment.get("speed_km_s") or 0.0)
    kp = float(event_assessment.get("max_kp_predicted") or 0.0)
    is_earth_directed = bool(event_assessment.get("is_earth_directed", False))
    g_scale = event_assessment.get("g_scale", "G0")
    s_scale = event_assessment.get("s_scale", "S0")
    r_scale = event_assessment.get("r_scale", "R0")
    
    event_g_val = parse_scale_level(g_scale)
    event_s_val = parse_scale_level(s_scale)
    event_r_val = parse_scale_level(r_scale)

    thresh_g_val = parse_scale_level(thresholds.get("min_g_scale", "G0"))
    thresh_s_val = parse_scale_level(thresholds.get("min_s_scale", "S0"))
    thresh_r_val = parse_scale_level(thresholds.get("min_r_scale", "R0"))
    min_kp = float(thresholds.get("min_kp", 99.0))
    min_speed = float(thresholds.get("min_speed_km_s", 9999.0))
    earth_req = bool(thresholds.get("earth_directed_required", False))

    triggers = []
    
    # Earth directed requirement check
    earth_ok = True
    if earth_req and not is_earth_directed:
        earth_ok = False

    # Check triggers
    if earth_ok:
        if kp >= min_kp:
            triggers.append(f"Predicted Kp {kp:.1f} reaches/exceeds asset baseline {min_kp:.1f}")
        if event_g_val >= thresh_g_val and thresh_g_val > 0:
            triggers.append(f"Geomagnetic storm {g_scale} meets threshold {thresholds.get('min_g_scale')}")
        if event_s_val >= thresh_s_val and thresh_s_val > 0:
            triggers.append(f"Solar radiation storm {s_scale} meets threshold {thresholds.get('min_s_scale')}")
        if event_r_val >= thresh_r_val and thresh_r_val > 0:
            triggers.append(f"Radio blackout {r_scale} meets threshold {thresholds.get('min_r_scale')}")
        if speed >= min_speed:
            triggers.append(f"Plasma velocity {speed:.1f} km/s exceeds threshold {min_speed:.1f} km/s")

    # Determine status
    if len(triggers) >= 2 or (len(triggers) >= 1 and event_g_val >= 3):
        status = "POTENTIALLY_AFFECTED"
        screening_note = "Screening threshold matched. Operational review strongly recommended."
    elif len(triggers) == 1 or (is_earth_directed and kp >= (min_kp - 1.0)):
        status = "MONITORING_ADVISED"
        screening_note = "Approaching sensitivity envelope. Active monitoring advised."
    else:
        status = "NOMINAL"
        screening_note = "Conditions remain within normal operating tolerances."

    return {
        "asset_id": asset.get("asset_id"),
        "name": asset.get("name"),
        "domain": asset.get("domain"),
        "criticality": asset.get("criticality"),
        "location": asset.get("location"),
        "operator": asset.get("operator"),
        "contact_email": asset.get("contact_email"),
        "impact_status": status,
        "screening_note": screening_note,
        "triggering_factors": triggers,
        "mitigation_sop": asset.get("standard_operating_procedure")
    }


def match_all_assets_for_events(
    assessed_events: List[Dict[str, Any]],
    registry_path: str = REGISTRY_FILE
) -> List[Dict[str, Any]]:
    """Screen all registered assets against a list of assessed events."""
    assets = load_asset_registry(registry_path)
    results = []

    for event in assessed_events:
        eid = event.get("event_id")
        matches = []
        affected_count = 0
        monitoring_count = 0

        risk_raw = event.get("deterministic_risk")
        if isinstance(risk_raw, dict):
            risk_level = risk_raw.get("final_risk_level", "LOW")
        elif isinstance(risk_raw, str):
            risk_level = risk_raw
        else:
            risk_level = event.get("final_risk", "LOW")

        kp_val = float(event.get("max_kp_predicted") or 0.0)
        g_scale_val = event.get("g_scale")
        if not g_scale_val:
            if kp_val >= 9.0: g_scale_val = "G5"
            elif kp_val >= 8.0: g_scale_val = "G4"
            elif kp_val >= 7.0: g_scale_val = "G3"
            elif kp_val >= 6.0: g_scale_val = "G2"
            elif kp_val >= 5.0: g_scale_val = "G1"
            else: g_scale_val = "G0"

        # Inject computed g_scale into event copy for screening
        event_copy = dict(event)
        event_copy["g_scale"] = g_scale_val

        for asset in assets:
            res = screen_asset_for_event(asset, event_copy)
            if res["impact_status"] != "NOMINAL":
                matches.append(res)
                if res["impact_status"] == "POTENTIALLY_AFFECTED":
                    affected_count += 1
                elif res["impact_status"] == "MONITORING_ADVISED":
                    monitoring_count += 1

        results.append({
            "event_id": eid,
            "speed_km_s": event.get("speed_km_s"),
            "is_earth_directed": event.get("is_earth_directed"),
            "max_kp_predicted": kp_val,
            "g_scale": g_scale_val,
            "risk_level": risk_level,
            "total_assets_registered": len(assets),
            "potentially_affected_count": affected_count,
            "monitoring_advised_count": monitoring_count,
            "asset_matches": matches
        })

    return results


def main():
    parser = argparse.ArgumentParser(description="SolarSentinel Asset-Aware Screening Matcher")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Path to risk-assessed events JSON")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Path to save asset impact matches")
    parser.add_argument("--registry", default=REGISTRY_FILE, help="Path to asset registry JSON")
    args = parser.parse_args()

    input_file = args.input
    if not os.path.exists(input_file):
        if os.path.exists("data/sample/risk_assessment_sample.json"):
            input_file = "data/sample/risk_assessment_sample.json"
        else:
            print(f"[ERROR] Input file {args.input} not found.")
            sys.exit(1)

    with open(input_file, "r", encoding="utf-8-sig") as f:
        events = json.load(f)

    # In case input is a single dict or dict with "assessed_events"
    if isinstance(events, dict) and "assessed_events" in events:
        event_list = events["assessed_events"]
    elif isinstance(events, list):
        event_list = events
    else:
        event_list = [events]

    print(f"=== SolarSentinel Asset Matching Engine ===")
    print(f"Evaluating {len(event_list)} events against asset registry...")
    matched_results = match_all_assets_for_events(event_list, args.registry)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(matched_results, f, indent=2)

    total_affected = sum(r["potentially_affected_count"] for r in matched_results)
    total_monitoring = sum(r["monitoring_advised_count"] for r in matched_results)
    print(f"[SUCCESS] Screening complete.")
    print(f"  Potentially Affected Asset Matches : {total_affected}")
    print(f"  Monitoring Advised Matches         : {total_monitoring}")
    print(f"  Results saved to                   : {args.output}")


if __name__ == "__main__":
    main()
