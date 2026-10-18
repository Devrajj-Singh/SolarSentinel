"""
SolarSentinel - Multi-Channel Notification Engine (Phase V2.3)
Generates aerospace-grade operational briefing emails (HTML + Plaintext) and Webhook payloads.
Provides a Safe Local Mock Inbox in output/emails/ when live SMTP is unconfigured.
"""

import os
import sys
import json
import smtplib
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

INCIDENTS_DIR = "data/incidents"
OUTPUT_EMAILS_DIR = "output/emails"
OUTPUT_AUDIT_DIR = "output/audit"
CONFIG_FILE = "config/settings.json"


def ensure_dirs():
    """Ensure output directories exist."""
    os.makedirs(OUTPUT_EMAILS_DIR, exist_ok=True)
    os.makedirs(OUTPUT_AUDIT_DIR, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """Load configuration with safe fallbacks."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def render_html_briefing(incident: Dict[str, Any]) -> str:
    """Render aerospace-styled HTML operational alert email."""
    inc_id = incident.get("incident_id", "UNKNOWN")
    event_id = incident.get("event_id", "UNKNOWN")
    severity = incident.get("severity", "MEDIUM")
    status = incident.get("status", "OPEN")
    hazard = incident.get("hazard_summary", {})
    affected = incident.get("affected_assets", [])
    approval = incident.get("approval_record", {})
    g_scale = hazard.get("g_scale", "G0")
    kp = float(hazard.get("max_kp_predicted") or 0.0)
    speed = float(hazard.get("speed_km_s") or 0.0)
    arrival = hazard.get("earth_arrival_time") or "N/A"

    badge_color = "#ef4444" if severity in ("HIGH", "CRITICAL") else ("#f59e0b" if severity == "MEDIUM" else "#10b981")
    badge_bg = "#450a0a" if severity in ("HIGH", "CRITICAL") else ("#451a03" if severity == "MEDIUM" else "#064e3b")

    assets_html = ""
    if affected:
        for a in affected:
            assets_html += f"""
            <div style="background: rgba(30, 41, 59, 0.7); border-left: 4px solid {badge_color}; border-radius: 6px; padding: 12px 16px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong style="color: #f1f5f9; font-size: 14px;">{a.get('asset_name')}</strong>
                    <span style="color: #94a3b8; font-size: 11px; background: #0f172a; padding: 2px 8px; border-radius: 4px;">{a.get('asset_id')}</span>
                </div>
                <div style="color: #cbd5e1; font-size: 12px; margin-top: 6px;"><strong>Operator:</strong> {a.get('operator')} ({a.get('contact_email')})</div>
                <div style="color: #93c5fd; font-size: 12px; margin-top: 6px; background: rgba(15, 23, 42, 0.6); padding: 8px 10px; border-radius: 4px;">
                    <strong>SOP Mitigation:</strong> {a.get('sop_action')}
                </div>
            </div>
            """
    else:
        assets_html = "<p style='color: #94a3b8; font-size: 13px; font-style: italic;'>No critical operational assets currently match screening thresholds.</p>"

    approval_box = ""
    if approval.get("required"):
        app_status = approval.get("status", "PENDING")
        app_color = "#10b981" if app_status == "APPROVED" else ("#ef4444" if app_status == "REJECTED" else "#f59e0b")
        approval_box = f"""
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 14px 18px; margin: 20px 0;">
            <div style="color: {app_color}; font-weight: bold; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;">
                Human-in-the-Loop Sign-Off: {app_status}
            </div>
            <div style="color: #cbd5e1; font-size: 12px; margin-top: 4px;">
                Decided By: {approval.get('decided_by') or 'Pending Flight Director Review'} | Notes: {approval.get('operational_notes') or 'Awaiting operator signature'}
            </div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ margin: 0; padding: 0; background-color: #0b0f19; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #f8fafc; }}
  .container {{ max-width: 680px; margin: 20px auto; background: #111827; border: 1px solid #1f2937; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5); }}
  .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); padding: 24px 28px; border-bottom: 1px solid #1f2937; }}
  .badge {{ display: inline-block; background-color: {badge_bg}; color: {badge_color}; border: 1px solid {badge_color}; border-radius: 4px; padding: 4px 12px; font-size: 11px; font-weight: 700; letter-spacing: 0.8px; text-transform: uppercase; }}
  .title {{ margin: 12px 0 4px 0; font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: -0.3px; }}
  .subtitle {{ color: #94a3b8; font-size: 13px; margin: 0; }}
  .body {{ padding: 24px 28px; }}
  .telemetry-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0; }}
  .stat-card {{ background: #1e293b; padding: 12px; border-radius: 8px; border: 1px solid #334155; text-align: center; }}
  .stat-label {{ color: #94a3b8; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }}
  .stat-val {{ color: #f8fafc; font-size: 16px; font-weight: 700; margin-top: 4px; }}
  .footer {{ background: #0f172a; padding: 16px 28px; font-size: 11px; color: #64748b; border-top: 1px solid #1f2937; text-align: center; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <span class="badge">{severity} SEVERITY ALERT</span>
    <h1 class="title">SolarSentinel Space Weather Alert</h1>
    <p class="subtitle">Incident ID: <strong>{inc_id}</strong> | Target Event: <strong>{event_id}</strong></p>
  </div>
  <div class="body">
    <div class="telemetry-grid">
      <div class="stat-card">
        <div class="stat-label">NOAA Scale</div>
        <div class="stat-val" style="color: {badge_color};">{g_scale}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Max Kp</div>
        <div class="stat-val">{kp:.1f}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Velocity</div>
        <div class="stat-val">{speed:.0f} km/s</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Earth Arrival</div>
        <div class="stat-val" style="font-size: 13px;">{arrival}</div>
      </div>
    </div>

    {approval_box}

    <h3 style="color: #f1f5f9; font-size: 14px; text-transform: uppercase; letter-spacing: 0.6px; margin-top: 24px; margin-bottom: 12px;">
      Operational Asset Screening Matches ({len(affected)})
    </h3>
    {assets_html}

    <div style="margin-top: 24px; padding-top: 16px; border-top: 1px solid #1f2937; color: #94a3b8; font-size: 12px;">
      <strong>Autonomous RPA Source:</strong> UiPath Master Orchestrator | <strong>AI Model:</strong> GPT-OSS 120B (Groq LPU)
    </div>
  </div>
  <div class="footer">
    SolarSentinel Autonomous Space Weather Early Warning Platform | CONFIDENTIAL OPERATIONAL TELEMETRY
  </div>
</div>
</body>
</html>"""
    return html


def render_plaintext_briefing(incident: Dict[str, Any]) -> str:
    """Render plain text briefing for notification fallbacks."""
    inc_id = incident.get("incident_id")
    event_id = incident.get("event_id")
    severity = incident.get("severity")
    hazard = incident.get("hazard_summary", {})
    affected = incident.get("affected_assets", [])

    lines = [
        "==========================================================",
        f"  🛰️ SOLARSENTINEL OPERATIONAL SPACE WEATHER ALERT  ",
        "==========================================================",
        f"Incident ID   : {inc_id}",
        f"Event ID      : {event_id}",
        f"Severity      : {severity}",
        f"NOAA Scale    : {hazard.get('g_scale', 'G0')} (Kp {hazard.get('max_kp_predicted')})",
        f"Velocity      : {hazard.get('speed_km_s')} km/s",
        f"Earth Arrival : {hazard.get('earth_arrival_time') or 'N/A'}",
        "----------------------------------------------------------",
        f"AFFECTED ASSETS ({len(affected)}):"
    ]
    for a in affected:
        lines.append(f"  * {a.get('asset_name')} [{a.get('status')}]")
        lines.append(f"    SOP Mitigation: {a.get('sop_action')}")
        lines.append(f"    Operator: {a.get('operator')} ({a.get('contact_email')})")
    lines.append("==========================================================")
    return "\n".join(lines)


def render_webhook_payload(incident: Dict[str, Any]) -> Dict[str, Any]:
    """Render Microsoft Teams / Slack compatible card payload."""
    severity = incident.get("severity", "MEDIUM")
    theme_color = "EF4444" if severity in ("HIGH", "CRITICAL") else ("F59E0B" if severity == "MEDIUM" else "10B981")
    hazard = incident.get("hazard_summary", {})

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": theme_color,
        "summary": f"SolarSentinel {severity} Alert: {incident.get('incident_id')}",
        "sections": [
            {
                "activityTitle": f"SolarSentinel Space Weather Alert: {severity}",
                "activitySubtitle": f"Incident: {incident.get('incident_id')} | Event: {incident.get('event_id')}",
                "facts": [
                    {"name": "NOAA Scale", "value": hazard.get("g_scale", "G0")},
                    {"name": "Predicted Kp", "value": str(hazard.get("max_kp_predicted"))},
                    {"name": "Speed", "value": f"{hazard.get('speed_km_s')} km/s"},
                    {"name": "Earth Arrival", "value": str(hazard.get("earth_arrival_time") or "N/A")},
                    {"name": "Affected Assets", "value": str(incident.get("affected_assets_count", 0))}
                ],
                "markdown": True
            }
        ]
    }


def dispatch_incident_notification(
    incident: Dict[str, Any],
    force_mock: bool = False
) -> Dict[str, Any]:
    """
    Dispatch notification: writes to local mock inbox (output/emails/) and sends SMTP if configured.
    """
    ensure_dirs()
    inc_id = incident.get("incident_id", "UNKNOWN")
    html_content = render_html_briefing(incident)
    txt_content = render_plaintext_briefing(incident)
    webhook_card = render_webhook_payload(incident)

    # 1. Always write to Safe Local Mock Inbox
    html_path = os.path.join(OUTPUT_EMAILS_DIR, f"{inc_id}.html")
    txt_path = os.path.join(OUTPUT_EMAILS_DIR, f"{inc_id}.txt")
    webhook_path = os.path.join(OUTPUT_AUDIT_DIR, f"webhook_{inc_id}.json")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(txt_content)
    with open(webhook_path, "w", encoding="utf-8") as f:
        json.dump(webhook_card, f, indent=2)

    config = load_config()
    smtp_cfg = config.get("notifications", {}).get("email", {})
    smtp_enabled = smtp_cfg.get("enabled", False) and not force_mock
    smtp_sent = False

    # 2. Live SMTP if configured
    if smtp_enabled:
        host = smtp_cfg.get("smtp_host")
        port = smtp_cfg.get("smtp_port", 587)
        sender = smtp_cfg.get("sender_email")
        password = smtp_cfg.get("sender_password")
        recipients = smtp_cfg.get("recipients", [])

        if host and sender and password and recipients:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = f"SolarSentinel {incident.get('severity')} Alert: {inc_id}"
                msg["From"] = sender
                msg["To"] = ", ".join(recipients)
                msg.attach(MIMEText(txt_content, "plain"))
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(host, port, timeout=10) as server:
                    server.starttls()
                    server.login(sender, password)
                    server.sendmail(sender, recipients, msg.as_string())
                smtp_sent = True
            except Exception as e:
                print(f"[WARN] Live SMTP transmission failed ({e}). Mock email preserved.", file=sys.stderr)

    return {
        "incident_id": inc_id,
        "local_html_inbox": html_path,
        "local_txt_inbox": txt_path,
        "webhook_audit": webhook_path,
        "smtp_sent": smtp_sent
    }


def main():
    parser = argparse.ArgumentParser(description="SolarSentinel Multi-Channel Notification Engine")
    subparsers = parser.add_subparsers(dest="command")

    # Command: notify-all
    subparsers.add_parser("notify-all", help="Generate briefings and dispatch alerts for all active incidents")

    # Command: notify-incident
    single_p = subparsers.add_parser("notify-incident", help="Dispatch alerts for a single incident")
    single_p.add_argument("--incident-id", required=True, help="Incident ID to notify")

    args = parser.parse_args()

    if args.command == "notify-all":
        ensure_dirs()
        incidents = []
        if os.path.exists(INCIDENTS_DIR):
            for fname in sorted(os.listdir(INCIDENTS_DIR)):
                if fname.endswith(".json") and fname.startswith("INC-"):
                    with open(os.path.join(INCIDENTS_DIR, fname), "r", encoding="utf-8-sig") as f:
                        incidents.append(json.load(f))

        print(f"=== SolarSentinel Notification Dispatcher ===")
        print(f"Found {len(incidents)} operational incidents.")
        dispatched = 0
        for inc in incidents:
            res = dispatch_incident_notification(inc)
            dispatched += 1
            print(f"  + Dispatched {inc['incident_id']} -> Local Mock Inbox: {res['local_html_inbox']}")

        print(f"[SUCCESS] {dispatched} operational briefings generated in {OUTPUT_EMAILS_DIR}/.")

    elif args.command == "notify-incident":
        filepath = os.path.join(INCIDENTS_DIR, f"{args.incident_id}.json")
        if not os.path.exists(filepath):
            print(f"[ERROR] Incident file not found: {filepath}")
            sys.exit(1)
        with open(filepath, "r", encoding="utf-8-sig") as f:
            inc = json.load(f)
        res = dispatch_incident_notification(inc)
        print(f"[SUCCESS] Dispatched alert for {args.incident_id}.")
        print(f"  Local HTML Inbox : {res['local_html_inbox']}")
        print(f"  Webhook Payload  : {res['webhook_audit']}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
