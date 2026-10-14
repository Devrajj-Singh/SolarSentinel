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
    print_banner("[SOLARSENTINEL] End-to-End Automated Pipeline")
    print(f"Execution Timestamp: {datetime.now(timezone.utc).isoformat()}")

    # Check normalized input exists
    norm_file = "data/raw/cme_normalized.json"
    if not os.path.exists(norm_file):
        print(f"[ERROR] Normalized input file {norm_file} not found. Run Phase 2/3 first.")
        sys.exit(1)

    # 1. Run AI Analysis Layer
    run_step(
        "Phase 4: GPT-OSS 120B AI Scientific Analysis",
        [sys.executable, "scripts/analyze_events.py"]
    )

    # 2. Run Deterministic Risk Engine
    run_step(
        "Phase 5: Deterministic Risk & Decision Engine",
        [sys.executable, "scripts/risk_engine.py"]
    )

    # 3. Run Logging & Reporting Engine
    run_step(
        "Phase 6: Master Excel Logging & Executive Reporting",
        [sys.executable, "scripts/generate_reports.py"]
    )

    # 4. Phase 7: Operational Alert Dispatch & Human-in-the-Loop Review
    print_banner("[ALERT CENTER] Phase 7: Operational Alerts & Human Routing")
    risk_file = "data/processed/risk_assessment.json"
    if os.path.exists(risk_file):
        with open(risk_file, "r", encoding="utf-8") as f:
            assessments = json.load(f)

        elevated = [a for a in assessments if a.get("routing_action") in ("OPERATOR_REVIEW", "HUMAN_APPROVAL_REQUIRED")]

        if elevated:
            print(f"[ALERT] {len(elevated)} event(s) require operational attention:")
            for ev in elevated:
                eid = ev.get("event_id")
                risk = ev.get("deterministic_risk")
                action = ev.get("routing_action")
                speed = ev.get("speed_km_s")
                kp = ev.get("max_kp_predicted")
                arr = ev.get("earth_arrival_time")

                print(f"\n  [!] FLAGGED EVENT: {eid}")
                print(f"      Severity Level : {risk}")
                print(f"      Routing Action : {action}")
                print(f"      Kinematics     : Speed {speed:.0f} km/s | Max Predicted Kp {kp:.1f}")
                print(f"      Earth Arrival  : {arr}")
                print(f"      AI Model Used  : GPT-OSS 120B (Groq LPU)")
                print(f"      Operational Rec: Check transformer ground currents & GIC alert channels.")
                print(f"      Status         : [PENDING OPERATOR SIGN-OFF]")
        else:
            print("  [OK] All events evaluated as LOW risk. Auto-logged with zero manual intervention required.")

    print_banner("[SUCCESS] Pipeline Complete: All Stages Successfully Executed")
    print("Generated Artifacts:")
    print("  - Excel Master Log : output/logs/events_log.xlsx")
    print("  - CSV Master Log   : output/logs/events_log.csv")
    print("  - Executive Report : output/reports/space_weather_report_*.md")
    print("  - Processed AI Data: data/processed/cme_ai_analysis.json")
    print("  - Risk Assessment  : data/processed/risk_assessment.json")


if __name__ == "__main__":
    main()
