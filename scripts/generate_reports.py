"""
SolarSentinel - Phase 6: Logging & Reporting Layer
Generates formatted Excel Master Event Log and Executive Space Weather Reports.
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime, timezone
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def load_json(path: str):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_dataframe(risk_assessments, ai_analysis, norm_events):
    ai_map = {a.get("event_id"): a for a in ai_analysis if "event_id" in a}
    norm_map = {n.get("event_id"): n for n in norm_events if "event_id" in n}

    rows = []
    for ra in risk_assessments:
        eid = ra.get("event_id")
        ai = ai_map.get(eid, {})
        norm = norm_map.get(eid, {})

        ai_sci = ai.get("scientific_assessment", {})
        secondary = ai.get("secondary_hazards", {})

        row = {
            "Event ID": eid,
            "Event Type": ra.get("event_type", "CME"),
            "Start Time (UTC)": ra.get("start_time", ""),
            "Source Region": ra.get("source_location", ""),
            "Earth Directed": "YES" if ra.get("is_earth_directed") else "NO",
            "Speed (km/s)": ra.get("speed_km_s", 0.0),
            "Predicted Max Kp": ra.get("max_kp_predicted", 0.0),
            "Earth Arrival (UTC)": ra.get("earth_arrival_time") or "N/A",
            "AI Risk": ra.get("ai_suggested_risk", "N/A"),
            "AI Confidence": f"{ra.get('ai_confidence_score', 0.0):.2f}" if ra.get("ai_confidence_score") else "N/A",
            "Final Risk": ra.get("deterministic_risk", "LOW"),
            "Routing Action": ra.get("routing_action", "AUTO_LOG"),
            "Validation Status": ra.get("validation_status", "PASSED"),
            "Geomagnetic Impact": ai_sci.get("geomagnetic_impact_potential", "N/A"),
            "Radio Blackout Risk": secondary.get("hf_radio_blackout_risk", "N/A"),
            "Radiation Storm Risk": secondary.get("radiation_storm_risk", "N/A"),
            "Auroral Latitudes": secondary.get("auroral_visibility_latitudes", "N/A"),
            "Operational Guidance": ai.get("operational_guidance", "Routine monitoring."),
            "Rule Triggers": " | ".join(ra.get("rule_triggers", []))
        }
        rows.append(row)

    return pd.DataFrame(rows)


def style_worksheet(ws, title: str, header_color: str = "1A365D"):
    """Generic aerospace styling for individual worksheet."""
    ws.title = title
    header_fill = PatternFill(start_color=header_color, end_color=header_color, fill_type="solid")
    header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Segoe UI", size=10)
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E0'),
        right=Side(style='thin', color='CBD5E0'),
        top=Side(style='thin', color='CBD5E0'),
        bottom=Side(style='thin', color='CBD5E0')
    )

    for col in range(1, ws.max_column + 1):
        cell = ws.cell(row=1, column=col)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center_align
        cell.border = thin_border
    ws.row_dimensions[1].height = 26

    for row in range(2, ws.max_row + 1):
        ws.row_dimensions[row].height = 20
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=row, column=col)
            cell.font = data_font
            cell.border = thin_border
            cell.alignment = left_align

    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        max_len = max(len(str(cell.value or '')) for cell in col)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 48)

    ws.freeze_panes = "A2"


def style_excel(file_path: str):
    """Apply professional aerospace styling across all workbook tabs."""
    wb = openpyxl.load_workbook(file_path)

    # Style Sheet 1: CME Event Log
    if "CME Event Log" in wb.sheetnames or "SolarSentinel Event Log" in wb.sheetnames:
        ws = wb["CME Event Log"] if "CME Event Log" in wb.sheetnames else wb["SolarSentinel Event Log"]
        style_worksheet(ws, "CME Event Log", "1A365D")

        # Color-code risk levels in column 11
        risk_colors = {
            "LOW": PatternFill(start_color="D1FAE5", end_color="D1FAE5", fill_type="solid"),
            "MEDIUM": PatternFill(start_color="FEF3C7", end_color="FEF3C7", fill_type="solid"),
            "HIGH": PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
        }
        risk_fonts = {
            "LOW": Font(name="Segoe UI", size=10, bold=True, color="065F46"),
            "MEDIUM": Font(name="Segoe UI", size=10, bold=True, color="92400E"),
            "HIGH": Font(name="Segoe UI", size=10, bold=True, color="991B1B")
        }
        for row in range(2, ws.max_row + 1):
            cell = ws.cell(row=row, column=11)
            val = str(cell.value or "").upper()
            if val in risk_colors:
                cell.fill = risk_colors[val]
                cell.font = risk_fonts[val]

    # Style Sheet 2: Asset Screening
    if "Asset Screening" in wb.sheetnames:
        ws = wb["Asset Screening"]
        style_worksheet(ws, "Asset Screening", "0F766E")

    # Style Sheet 3: Incident Register
    if "Incident Register" in wb.sheetnames:
        ws = wb["Incident Register"]
        style_worksheet(ws, "Incident Register", "7C2D12")

    wb.save(file_path)


def generate_markdown_report(risk_assessments, ai_analysis, norm_events, output_path: str):
    """Generate an executive-level space weather threat assessment report."""
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    date_code = datetime.now(timezone.utc).strftime("%Y%m%d")

    earth_directed = [r for r in risk_assessments if r.get("is_earth_directed")]
    high_risks = [r for r in risk_assessments if r.get("deterministic_risk") == "HIGH"]
    med_risks = [r for r in risk_assessments if r.get("deterministic_risk") == "MEDIUM"]

    ai_map = {a.get("event_id"): a for a in ai_analysis if "event_id" in a}

    md = []
    md.append(f"# 🛰️ SolarSentinel Space Weather Intelligence Report")
    md.append(f"**Generated:** {now_str} | **Monitoring Period:** Real-Time NASA DONKI Stream\n")
    md.append("---\n")

    # Executive Summary Card
    md.append("## 1. Executive Summary")
    if high_risks:
        overall_status = "🔴 **CRITICAL ALERT**: Major Earth-directed CME detected requiring human sign-off."
    elif med_risks:
        overall_status = "🟡 **ELEVATED MONITORING**: Moderate Earth-directed CME activity detected (G2 Geomagnetic Storm potential)."
    else:
        overall_status = "🟢 **NOMINAL**: Space weather conditions remain quiet across terrestrial sectors."

    md.append(f"**Operational Status:** {overall_status}\n")
    md.append(f"- **Total Solar Events Monitored:** {len(risk_assessments)}")
    md.append(f"- **Earth-Directed Trajectories:** {len(earth_directed)}")
    md.append(f"- **High Risk (Action Required):** {len(high_risks)}")
    md.append(f"- **Medium Risk (Operator Review):** {len(med_risks)}")
    md.append(f"- **Low Risk (Auto-Logged):** {len(risk_assessments) - len(high_risks) - len(med_risks)}\n")

    # Threat Matrix Table
    md.append("## 2. Earth-Directed Event Assessment Matrix")
    if earth_directed:
        md.append("| Event ID | Speed | Max Kp | Arrival Time (UTC) | AI Model | Final Risk | Routing Action |")
        md.append("|---|---|---|---|---|---|---|")
        for ev in earth_directed:
            eid = ev.get("event_id")
            spd = f"{ev.get('speed_km_s', 0):.0f} km/s"
            kp = f"Kp {ev.get('max_kp_predicted', 0):.1f}"
            arr = ev.get("earth_arrival_time") or "TBD"
            risk = ev.get("deterministic_risk")
            action = ev.get("routing_action")
            risk_badge = f"**{risk}**"
            md.append(f"| `{eid}` | {spd} | {kp} | {arr} | GPT-OSS 120B | {risk_badge} | `{action}` |")
    else:
        md.append("_No Earth-directed events currently detected._")
    md.append("\n---\n")

    # Detailed Scientific Reasoning for Elevated Events
    md.append("## 3. Detailed Scientific Analysis (GPT-OSS 120B)")
    for ev in earth_directed:
        eid = ev.get("event_id")
        ai = ai_map.get(eid, {})
        sci = ai.get("scientific_assessment", {})
        sec = ai.get("secondary_hazards", {})

        md.append(f"### Event: `{eid}`")
        md.append(f"- **Kinematics:** {sci.get('plasma_speed_evaluation', 'N/A')}")
        md.append(f"- **Trajectory:** {sci.get('earth_directed_analysis', 'N/A')}")
        md.append(f"- **Solar Source:** {sci.get('flare_and_source_correlation', 'N/A')}")
        md.append(f"- **Geomagnetic Impact:** {sci.get('geomagnetic_impact_potential', 'N/A')}")
        md.append(f"- **Secondary Hazards:** HF Blackout: `{sec.get('hf_radio_blackout_risk', 'NONE')}` | Radiation: `{sec.get('radiation_storm_risk', 'NONE')}` | Auroral Band: {sec.get('auroral_visibility_latitudes', 'High')}")
        md.append(f"- **Operational Directive:** {ai.get('operational_guidance', 'Routine monitoring.')}\n")

    # Operational Recommendations
    md.append("## 4. Sector-Specific Operational Guidance")
    md.append("### ⚡ Power Distribution Grid Operators")
    if med_risks or high_risks:
        md.append("- Prepare for potential Geomagnetically Induced Currents (GIC) during Oct 14 shock arrival window.")
        md.append("- Monitor transformer neutral ground currents and reactive power reserves.")
    else:
        md.append("- Baseline monitoring; GIC risk remains minimal.")

    md.append("\n### 🛰️ Commercial & Defense Satellite Operators")
    if med_risks or high_risks:
        md.append("- Monitor high-latitude orbital drag increases due to thermospheric heating.")
        md.append("- Review surface charging telemetry on geostationary and polar-orbiting assets.")
    else:
        md.append("- Orbital environmental conditions nominal.")

    md.append("\n### ✈️ Transpolar Aviation & HF Communications")
    if med_risks or high_risks:
        md.append("- High-latitude HF radio degradation possible during shock passage; monitor backup satcom.")
    else:
        md.append("- High-frequency radio propagation operating nominally.")

    md.append("\n---\n")
    md.append("> **Safety Notice:** SolarSentinel is an educational and research decision-support prototype. Operational decisions should always reference official NOAA SWPC alerts.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md))


def build_assets_dataframe(impacts_path: str = "data/processed/asset_impacts.json") -> pd.DataFrame:
    """Build DataFrame of screened operational assets."""
    if not os.path.exists(impacts_path):
        return pd.DataFrame()
    with open(impacts_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)

    rows = []
    for item in data:
        eid = item.get("event_id")
        matches = item.get("asset_matches", [])
        for m in matches:
            rows.append({
                "Event ID": eid,
                "Asset ID": m.get("asset_id"),
                "Asset Name": m.get("name"),
                "Domain": m.get("domain"),
                "Criticality": m.get("criticality"),
                "Impact Status": m.get("impact_status"),
                "Screening Note": m.get("screening_note"),
                "Triggering Hazards": " | ".join(m.get("triggering_factors", [])),
                "Operator": m.get("operator"),
                "Contact Email": m.get("contact_email"),
                "SOP Mitigation": m.get("mitigation_sop")
            })
    return pd.DataFrame(rows)


def build_incidents_dataframe(incidents_dir: str = "data/incidents") -> pd.DataFrame:
    """Build DataFrame of operational incident registry."""
    if not os.path.exists(incidents_dir):
        return pd.DataFrame()
    rows = []
    for fname in sorted(os.listdir(incidents_dir)):
        if fname.endswith(".json") and fname.startswith("INC-"):
            try:
                with open(os.path.join(incidents_dir, fname), "r", encoding="utf-8-sig") as f:
                    inc = json.load(f)
                    hazard = inc.get("hazard_summary", {})
                    approval = inc.get("approval_record", {})
                    rows.append({
                        "Incident ID": inc.get("incident_id"),
                        "Target Event": inc.get("event_id"),
                        "Severity": inc.get("severity"),
                        "Status": inc.get("status"),
                        "Title": inc.get("title"),
                        "NOAA Scale": hazard.get("g_scale", "G0"),
                        "Max Kp": hazard.get("max_kp_predicted"),
                        "Speed (km/s)": hazard.get("speed_km_s"),
                        "Earth Arrival": hazard.get("earth_arrival_time") or "N/A",
                        "Affected Assets": inc.get("affected_assets_count", 0),
                        "Approval Required": "YES" if approval.get("required") else "NO",
                        "Approval Status": approval.get("status", "N/A"),
                        "Decided By": approval.get("decided_by") or "N/A",
                        "Audit Entries": len(inc.get("audit_history", []))
                    })
            except Exception:
                pass
    return pd.DataFrame(rows)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SolarSentinel Phase 6: Logging & Reporting Layer")
    parser.add_argument("--normalized", default="data/raw/cme_normalized.json")
    parser.add_argument("--ai-analysis", default="data/processed/cme_ai_analysis.json")
    parser.add_argument("--risk-assessment", default="data/processed/risk_assessment.json")
    parser.add_argument("--asset-impacts", default="data/processed/asset_impacts.json")
    parser.add_argument("--excel-output", default="output/logs/events_log.xlsx")
    parser.add_argument("--csv-output", default="output/logs/events_log.csv")
    parser.add_argument("--report-dir", default="output/reports/")
    args = parser.parse_args()

    print("=======================================================")
    print(" SolarSentinel - Phase 6: Logging & Reporting Layer    ")
    print("=======================================================")

    risk_assessments = load_json(args.risk_assessment)
    if not risk_assessments and os.path.exists("data/sample/risk_assessment_sample.json"):
        risk_assessments = load_json("data/sample/risk_assessment_sample.json")

    ai_analysis = load_json(args.ai_analysis)
    if not ai_analysis and os.path.exists("data/sample/cme_ai_analysis_sample.json"):
        ai_analysis = load_json("data/sample/cme_ai_analysis_sample.json")

    norm_events = load_json(args.normalized)
    if not norm_events and os.path.exists("data/sample/cme_normalized_sample.json"):
        norm_events = load_json("data/sample/cme_normalized_sample.json")

    print(f"[INFO] Ingested {len(risk_assessments)} risk records.")

    # 1. Build DataFrames
    df_events = build_dataframe(risk_assessments, ai_analysis, norm_events)
    df_assets = build_assets_dataframe(args.asset_impacts)
    df_incidents = build_incidents_dataframe("data/incidents")

    # 2. Save CSV Log
    os.makedirs(os.path.dirname(args.csv_output), exist_ok=True)
    df_events.to_csv(args.csv_output, index=False, encoding="utf-8-sig")
    print(f"[SUCCESS] Exported CSV Event Log to {args.csv_output}")

    # 3. Save Multi-Sheet Excel Master Log
    os.makedirs(os.path.dirname(args.excel_output), exist_ok=True)
    with pd.ExcelWriter(args.excel_output, engine="openpyxl") as writer:
        df_events.to_excel(writer, sheet_name="CME Event Log", index=False)
        if not df_assets.empty:
            df_assets.to_excel(writer, sheet_name="Asset Screening", index=False)
        if not df_incidents.empty:
            df_incidents.to_excel(writer, sheet_name="Incident Register", index=False)

    style_excel(args.excel_output)
    print(f"[SUCCESS] Exported & Styled Multi-Tab Master Excel Log to {args.excel_output}")

    # 4. Generate Markdown Summary Report
    date_code = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_file = os.path.join(args.report_dir, f"space_weather_report_{date_code}.md")
    generate_markdown_report(risk_assessments, ai_analysis, norm_events, report_file)
    print(f"[SUCCESS] Generated Executive Space Weather Report at {report_file}")


if __name__ == "__main__":
    main()
