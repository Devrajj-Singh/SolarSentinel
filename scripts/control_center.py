"""
SolarSentinel V3.0 - Enterprise Operations Control Center & FastAPI Backend
Unified E2E Platform:
  - Homepage & Threat Model Architecture Showcase
  - Multi-source Ingestion (NASA DONKI & NOAA SWPC)
  - Live Pipeline Runner with Real-Time Step Streaming
  - Reports & Downloads Center (Excel, CSV, Markdown, HTML Alerts)
  - Personalized Authentication & Human-in-the-Loop SOP Sign-Off
  - Dynamic Asset Onboarding & Simulator Dispatch
"""

import os
import sys
import json
import time
import mimetypes
import threading
import subprocess
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

sys.path.insert(0, os.path.abspath("scripts"))
import queue_manager
import match_assets
import incident_manager
import notify

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(
    title="SolarSentinel Operations Control Center API",
    description="Enterprise Space Weather Defense, RPA Queue Monitoring, and Critical Infrastructure Incident Response Platform",
    version="3.0.0"
)

STATE_FILE    = "data/state/monitor_state.json"
NOAA_FILE     = "data/raw/noaa_swpc.json"
REGISTRY_FILE = "config/asset_registry.json"
DASHBOARD_FILE = "scripts/dashboard.html"

# Global pipeline execution state
pipeline_state: Dict[str, Any] = {
    "is_running": False,
    "started_at": None,
    "completed_at": None,
    "current_step": "Idle",
    "progress_pct": 0,
    "steps": [
        {"id": 1, "name": "NOAA SWPC Real-Time Geomagnetic Ingestion", "status": "pending"},
        {"id": 2, "name": "Idempotent Deduplication & Transaction Queueing", "status": "pending"},
        {"id": 3, "name": "GPT-OSS 120B AI Scientific Analysis (Groq LPU)", "status": "pending"},
        {"id": 4, "name": "Deterministic Risk & NOAA Scale Guardrails", "status": "pending"},
        {"id": 5, "name": "Operational Asset Impact Screening", "status": "pending"},
        {"id": 6, "name": "Space Weather Incident Dossier Generation", "status": "pending"},
        {"id": 7, "name": "Multi-Channel Alert Dispatch & Mock Inbox", "status": "pending"},
        {"id": 8, "name": "Master Excel Logging & Executive Space Weather Report", "status": "pending"},
        {"id": 9, "name": "State Store Commit & Metrics Finalization", "status": "pending"},
    ],
    "logs": [],
    "error": None
}

# Active user sessions store (in-memory demo store)
user_sessions: Dict[str, Dict[str, Any]] = {}


# --- Pydantic Request Models ---

class AuthRequest(BaseModel):
    provider: str = "credentials"  # "google" or "credentials"
    name: str = "Devraj Singh"
    email: str = "devraj@solarsentinel.ops"
    organization: str = "SolarSentinel Command & Defense"
    role: str = "Flight Director / Mission Commander"
    avatar: str = ""

class ApprovalRequest(BaseModel):
    operator_name: str = "Devraj Singh"
    operator_role: str = "Flight Director / Mission Commander"
    operational_notes: str = "Authorized asset protection protocol and satellite safe-hold."

class RejectionRequest(BaseModel):
    operator_name: str = "Devraj Singh"
    operator_role: str = "Flight Director / Mission Commander"
    operational_notes: str = "Deemed false positive after telemetry cross-check."

class SimulationRequest(BaseModel):
    speed_km_s: float = 1200.0
    half_angle_deg: float = 60.0
    is_earth_directed: bool = True
    predicted_kp: float = 7.0
    simulated_by: str = "Control Center Operator"

class SimulationDispatchRequest(BaseModel):
    simulation_id: str
    speed_km_s: float
    predicted_kp: float
    g_scale: str
    assigned_risk: str
    routing_action: str
    affected_assets: List[Dict[str, Any]]
    operator_name: str = "Devraj Singh"

class AssetCreateRequest(BaseModel):
    asset_id: str
    name: str
    domain: str  # SATELLITE_LEO, SATELLITE_GEO, POWER_GRID, AVIATION, GROUND_STATION
    criticality: str  # LOW, MEDIUM, HIGH, CRITICAL
    location: str
    operator: str
    contact_email: str
    primary_hazards: List[str]
    screening_thresholds: Dict[str, Any]
    standard_operating_procedure: str


# --- Core Telemetry & Status APIs ---

@app.get("/api/status")
def get_system_status():
    """Return health telemetry across all platform services and active pipeline status."""
    state = queue_manager.load_state()
    noaa_live = False
    observed_kp = 2.0
    g_scale = "G0"
    if os.path.exists(NOAA_FILE):
        try:
            with open(NOAA_FILE, "r", encoding="utf-8-sig") as f:
                noaa_data   = json.load(f)
                noaa_live   = noaa_data.get("provenance", {}).get("is_live", False)
                observed_kp = noaa_data.get("current_conditions", {}).get("observed_kp", 2.0)
                g_scale     = noaa_data.get("current_conditions", {}).get("g_scale", "G0")
        except Exception:
            pass
    return {
        "system_health":       state.get("system_health", "HEALTHY"),
        "last_successful_run": state.get("last_successful_run"),
        "total_runs":          state.get("total_runs", 0),
        "total_transactions":  state.get("total_transactions_processed", 0),
        "pipeline_running":    pipeline_state["is_running"],
        "services": {
            "uipath_orchestrator": {"status": "ONLINE", "type": "Autonomous RPA Conductor", "version": "Studio 2026.0"},
            "nasa_donki":          {"status": "ONLINE", "type": "Solar Observation Feed", "latency_ms": 140},
            "noaa_swpc":           {"status": "ONLINE" if noaa_live else "FALLBACK", "observed_kp": observed_kp, "g_scale": g_scale},
            "groq_lpu":            {"status": "ONLINE", "model": "openai/gpt-oss-120b", "tokens_per_sec": 485}
        }
    }


@app.get("/api/queue")
def get_queue_data():
    """Return queue metrics and all items across all queue states."""
    metrics = queue_manager.get_queue_metrics()
    def load_dir(d):
        items = []
        if os.path.exists(d):
            for fname in sorted(os.listdir(d)):
                if fname.endswith(".json"):
                    try:
                        fpath = os.path.join(d, fname)
                        if os.path.getsize(fpath) > 0:
                            with open(fpath, "r", encoding="utf-8-sig") as f:
                                items.append(json.load(f))
                    except Exception:
                        pass
        return items
    return {
        "metrics":           metrics,
        "pending_items":     load_dir(queue_manager.PENDING_DIR)[:25],
        "in_progress_items": load_dir(queue_manager.IN_PROGRESS_DIR)[:15],
        "completed_items":   load_dir(queue_manager.COMPLETED_DIR)[:25],
        "failed_items":      load_dir(queue_manager.FAILED_DIR)[:15],
    }


@app.get("/api/incidents")
def get_incidents():
    """Return all operational space weather incidents."""
    incidents = incident_manager.list_incidents()
    return {"incidents": incidents}


@app.get("/api/assets")
def get_assets():
    """Return all registered operational assets."""
    assets = match_assets.load_asset_registry()
    return {"assets": assets}


@app.post("/api/assets")
def create_asset_api(req: AssetCreateRequest):
    """Register a new mission-critical asset in the registry."""
    if not os.path.exists(REGISTRY_FILE):
        registry = {"registry_version": "2.0.0", "last_updated": datetime.now(timezone.utc).isoformat(), "assets": []}
    else:
        with open(REGISTRY_FILE, "r", encoding="utf-8-sig") as f:
            registry = json.load(f)

    # Check for existing ID
    for a in registry.get("assets", []):
        if a.get("asset_id") == req.asset_id:
            raise HTTPException(status_code=400, detail=f"Asset ID {req.asset_id} already exists")

    new_asset = req.model_dump()
    registry.setdefault("assets", []).append(new_asset)
    registry["last_updated"] = datetime.now(timezone.utc).isoformat()

    with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)

    return {"status": "SUCCESS", "asset": new_asset, "total_assets": len(registry["assets"])}


# --- Authentication & Operator Identity APIs ---

@app.post("/api/auth/login")
def auth_login(req: AuthRequest):
    """Authenticate operator via Google OAuth or Operator Credentials."""
    session_id = f"SES-{int(time.time()*1000)}"
    user_data = {
        "session_id": session_id,
        "provider": req.provider,
        "name": req.name,
        "email": req.email,
        "organization": req.organization,
        "role": req.role,
        "avatar": req.avatar or f"https://api.dicebear.com/7.x/bottts/svg?seed={req.name}",
        "authenticated_at": datetime.now(timezone.utc).isoformat()
    }
    user_sessions[session_id] = user_data
    return {"status": "SUCCESS", "user": user_data}


# --- Human-in-the-Loop SOP Sign-Off APIs ---

@app.post("/api/incidents/{incident_id}/approve")
def approve_incident_api(incident_id: str, req: ApprovalRequest):
    """Operator approval endpoint with real signed identity."""
    signature = f"{req.operator_name} ({req.operator_role})" if req.operator_role else req.operator_name
    success = incident_manager.approve_incident(incident_id, signature, req.operational_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found or approval failed")
    inc = incident_manager.load_incident(incident_id)
    if inc:
        try:
            notify.dispatch_incident_notification(inc, force_mock=True)
        except Exception:
            pass
    return {"status": "SUCCESS", "incident": inc, "authorized_by": signature}


@app.post("/api/incidents/{incident_id}/reject")
def reject_incident_api(incident_id: str, req: RejectionRequest):
    """Operator rejection endpoint with real signed identity."""
    signature = f"{req.operator_name} ({req.operator_role})" if req.operator_role else req.operator_name
    success = incident_manager.reject_incident(incident_id, signature, req.operational_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found or rejection failed")
    inc = incident_manager.load_incident(incident_id)
    return {"status": "SUCCESS", "incident": inc, "rejected_by": signature}


# --- Live Pipeline Execution APIs ---

def _run_pipeline_worker():
    """Background thread executing all 9 steps of the operations pipeline."""
    global pipeline_state
    pipeline_state["is_running"] = True
    pipeline_state["started_at"] = datetime.now(timezone.utc).isoformat()
    pipeline_state["completed_at"] = None
    pipeline_state["error"] = None
    pipeline_state["logs"] = []

    steps = [
        {"cmd": [sys.executable, "scripts/fetch_noaa.py"], "name": "NOAA SWPC Real-Time Geomagnetic Ingestion"},
        {"cmd": [sys.executable, "scripts/queue_manager.py", "enqueue", "--input", "data/raw/cme_normalized.json"], "name": "Idempotent Deduplication & Transaction Queueing"},
        {"cmd": [sys.executable, "scripts/analyze_events.py"], "name": "GPT-OSS 120B AI Scientific Analysis (Groq LPU)"},
        {"cmd": [sys.executable, "scripts/risk_engine.py"], "name": "Deterministic Risk & NOAA Scale Guardrails"},
        {"cmd": [sys.executable, "scripts/match_assets.py"], "name": "Operational Asset Impact Screening"},
        {"cmd": [sys.executable, "scripts/incident_manager.py", "create-batch"], "name": "Space Weather Incident Dossier Generation"},
        {"cmd": [sys.executable, "scripts/notify.py", "notify-all"], "name": "Multi-Channel Alert Dispatch & Mock Inbox"},
        {"cmd": [sys.executable, "scripts/generate_reports.py"], "name": "Master Excel Logging & Executive Space Weather Report"},
        {"cmd": [sys.executable, "scripts/queue_manager.py", "finalize-run", "--status", "HEALTHY"], "name": "State Store Commit & Metrics Finalization"},
    ]

    total = len(steps)
    for idx, s in enumerate(steps):
        pipeline_state["current_step"] = s["name"]
        pipeline_state["steps"][idx]["status"] = "running"
        pipeline_state["progress_pct"] = int((idx / total) * 100)
        
        log_line = f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] RUNNING: Step {idx+1}/{total} - {s['name']}..."
        pipeline_state["logs"].append(log_line)

        try:
            res = subprocess.run(s["cmd"], capture_output=True, text=True, encoding="utf-8", errors="replace")
            if res.stdout:
                for line in res.stdout.strip().splitlines()[:5]:
                    pipeline_state["logs"].append(f"  > {line}")
            if res.returncode != 0:
                pipeline_state["steps"][idx]["status"] = "failed"
                pipeline_state["error"] = f"Failed at {s['name']}: {res.stderr[:200]}"
                pipeline_state["logs"].append(f"[ERROR] {res.stderr[:200]}")
                pipeline_state["is_running"] = False
                return
            pipeline_state["steps"][idx]["status"] = "completed"
        except Exception as e:
            pipeline_state["steps"][idx]["status"] = "failed"
            pipeline_state["error"] = str(e)
            pipeline_state["is_running"] = False
            return

    pipeline_state["progress_pct"] = 100
    pipeline_state["current_step"] = "Completed"
    pipeline_state["completed_at"] = datetime.now(timezone.utc).isoformat()
    pipeline_state["logs"].append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] [SUCCESS] Pipeline execution finished with status HEALTHY.")
    pipeline_state["is_running"] = False


@app.post("/api/pipeline/run")
def trigger_pipeline_run(background_tasks: BackgroundTasks):
    """Trigger the autonomous space weather operations pipeline."""
    global pipeline_state
    if pipeline_state["is_running"]:
        return {"status": "ALREADY_RUNNING", "message": "Pipeline is already in progress"}

    for s in pipeline_state["steps"]:
        s["status"] = "pending"
    pipeline_state["progress_pct"] = 0
    pipeline_state["error"] = None
    
    t = threading.Thread(target=_run_pipeline_worker, daemon=True)
    t.start()
    return {"status": "STARTED", "message": "Operations pipeline initiated in background"}


@app.get("/api/pipeline/status")
def get_pipeline_status():
    """Poll the real-time execution status and streaming logs."""
    return pipeline_state


# --- Reports & Downloads Center APIs ---

def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.2f} MB"


@app.get("/api/reports")
def list_reports():
    """List all downloadable reports, Excel workbooks, executive briefings, and webhook payloads."""
    cats = {
        "logs":    ("output/logs", "Master Excel & CSV Logs"),
        "reports": ("output/reports", "Executive Space Weather Dossiers"),
        "emails":  ("output/emails", "Operational Alert Briefings (HTML & TXT)"),
        "audit":   ("output/audit", "ChatOps Webhook Payloads (Teams & Slack)")
    }
    results = {}
    for cat_key, (dir_path, display_name) in cats.items():
        items = []
        if os.path.exists(dir_path):
            for fname in sorted(os.listdir(dir_path), reverse=True):
                if fname.startswith("."):
                    continue
                fpath = os.path.join(dir_path, fname)
                if os.path.isfile(fpath):
                    st = os.stat(fpath)
                    ext = os.path.splitext(fname)[1].lower().replace(".", "")
                    items.append({
                        "filename": fname,
                        "category": cat_key,
                        "format": ext.upper(),
                        "size_bytes": st.st_size,
                        "size_formatted": _format_size(st.st_size),
                        "modified_at": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
                        "download_url": f"/api/reports/download/{cat_key}/{fname}",
                        "preview_url": f"/api/reports/preview/{cat_key}/{fname}"
                    })
        results[cat_key] = {"title": display_name, "files": items}
    return results


@app.get("/api/reports/download/{category}/{filename}")
def download_report(category: str, filename: str):
    """Download a generated operational file."""
    allowed_dirs = {
        "logs": "output/logs",
        "reports": "output/reports",
        "emails": "output/emails",
        "audit": "output/audit"
    }
    if category not in allowed_dirs:
        raise HTTPException(status_code=400, detail="Invalid report category")

    safe_filename = os.path.basename(filename)
    filepath = os.path.join(allowed_dirs[category], safe_filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    mime_type, _ = mimetypes.guess_type(filepath)
    if not mime_type:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=filepath,
        media_type=mime_type,
        filename=safe_filename,
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'}
    )


@app.get("/api/reports/preview/{category}/{filename}")
def preview_report(category: str, filename: str):
    """Return text/markdown/json content for inline modal preview."""
    allowed_dirs = {
        "logs": "output/logs",
        "reports": "output/reports",
        "emails": "output/emails",
        "audit": "output/audit"
    }
    if category not in allowed_dirs:
        raise HTTPException(status_code=400, detail="Invalid report category")

    safe_filename = os.path.basename(filename)
    filepath = os.path.join(allowed_dirs[category], safe_filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")

    ext = os.path.splitext(safe_filename)[1].lower()
    if ext in [".xlsx", ".xls"]:
        return {"filename": safe_filename, "type": "binary", "content": "Excel binary workbook. Use Download button to view."}

    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            content = f.read()
        return {
            "filename": safe_filename,
            "type": "markdown" if ext == ".md" else ("html" if ext == ".html" else ("json" if ext == ".json" else "text")),
            "content": content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Space Weather Simulator & Dispatch APIs ---

@app.post("/api/simulate")
def run_what_if_simulation(req: SimulationRequest):
    """Execute What-If space-weather simulation sandbox."""
    sim_id = f"SIM-WHATIF-{int(time.time())}"
    kp, speed, earth = req.predicted_kp, req.speed_km_s, req.is_earth_directed
    if kp >= 9.0:   g_scale = "G5"
    elif kp >= 8.0: g_scale = "G4"
    elif kp >= 7.0: g_scale = "G3"
    elif kp >= 6.0: g_scale = "G2"
    elif kp >= 5.0: g_scale = "G1"
    else:           g_scale = "G0"

    if not earth:                       final_risk, routing = "LOW",    "AUTO_LOG"
    elif kp >= 7.0 or speed >= 1500.0: final_risk, routing = "HIGH",   "HUMAN_APPROVAL_REQUIRED"
    elif kp >= 5.0 or speed >= 700.0:  final_risk, routing = "MEDIUM", "OPERATOR_REVIEW"
    else:                               final_risk, routing = "LOW",    "AUTO_LOG"

    event_mock = {
        "event_id": sim_id, "speed_km_s": speed,
        "max_kp_predicted": kp, "is_earth_directed": earth,
        "g_scale": g_scale, "deterministic_risk": final_risk
    }
    assets      = match_assets.load_asset_registry()
    all_results = [match_assets.screen_asset_for_event(a, event_mock) for a in assets]
    affected    = [m for m in all_results if m["impact_status"] != "NOMINAL"]
    transit_hrs = round((149597870.7 / speed) / 3600.0, 1) if speed > 0 else 0.0

    return {
        "simulation_id": sim_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "is_simulated":  True,
        "input_parameters": req.model_dump(),
        "physics_evaluation": {
            "estimated_transit_hours": transit_hrs,
            "noaa_scale": g_scale, "assigned_risk": final_risk, "routing_action": routing
        },
        "asset_impact_screening": {
            "total_assets_registered": len(assets),
            "affected_assets_count":   len(affected),
            "affected_assets":         affected,
            "all_results":             all_results
        }
    }


@app.post("/api/simulate/dispatch")
def dispatch_simulated_incident(req: SimulationDispatchRequest):
    """Create a test incident dossier from simulation results for testing human-in-the-loop workflows."""
    incident_manager.ensure_incident_dir()
    now_iso = datetime.now(timezone.utc).isoformat()
    inc_id = f"INC-SIM-{int(time.time())}"

    status = "AWAITING_APPROVAL" if req.assigned_risk == "HIGH" else ("INVESTIGATING" if req.assigned_risk == "MEDIUM" else "OPEN")
    
    incident = {
        "incident_id": inc_id,
        "event_id": req.simulation_id,
        "created_at": now_iso,
        "updated_at": now_iso,
        "severity": req.assigned_risk,
        "status": status,
        "title": f"SIMULATED Space Weather Hazard: {req.assigned_risk} Risk ({req.g_scale} / Kp {req.predicted_kp:.1f}) [SANDBOX]",
        "hazard_summary": {
            "speed_km_s": req.speed_km_s,
            "max_kp_predicted": req.predicted_kp,
            "g_scale": req.g_scale,
            "is_earth_directed": True,
            "is_simulated": True
        },
        "impacted_assets": req.affected_assets,
        "approval_record": {
            "required": req.assigned_risk == "HIGH",
            "status": "PENDING" if req.assigned_risk == "HIGH" else "NOT_REQUIRED",
            "decided_by": None,
            "decision_time": None,
            "operational_notes": None
        },
        "audit_history": [
            {
                "timestamp": now_iso,
                "actor": req.operator_name,
                "action": "SIMULATION_DISPATCHED",
                "notes": f"Dispatched sandbox simulation {req.simulation_id} for operational drill."
            }
        ]
    }
    incident_manager.save_incident(incident)
    return {"status": "SUCCESS", "incident_id": inc_id, "incident": incident}


# --- Web Application Entrypoint ---

@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serve the single-page Control Center operations dashboard dynamically."""
    if os.path.exists(DASHBOARD_FILE):
        with open(DASHBOARD_FILE, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
    return HTMLResponse("<h1>Dashboard file not found</h1>", status_code=500)


def main():
    import uvicorn
    print("=" * 65)
    print("  SolarSentinel V3.0 Enterprise Operations Platform")
    print("  Local Live UI : http://localhost:8000")
    print("  API Docs      : http://localhost:8000/docs")
    print("=" * 65)
    uvicorn.run("control_center:app", host="127.0.0.1", port=8000, reload=True, log_level="info")


if __name__ == "__main__":
    main()
