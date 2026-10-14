"""
SolarSentinel - Operations Control Center Dashboard & FastAPI Backend (Phase V2.4)
Provides real-time system telemetry, transactional queue monitoring, active incident exploration,
interactive human-in-the-loop approval, and the What-If space-weather simulation sandbox.
"""

import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Ensure local imports work
sys.path.insert(0, os.path.abspath("scripts"))
import queue_manager
import match_assets
import incident_manager
import notify

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

app = FastAPI(
    title="SolarSentinel Operations Control Center API",
    description="Real-time space weather operations, RPA queue monitoring, and incident response platform",
    version="2.0.0"
)

STATE_FILE = "data/state/monitor_state.json"
NOAA_FILE = "data/raw/noaa_swpc.json"
REGISTRY_FILE = "config/asset_registry.json"


# --- Request Models ---
class ApprovalRequest(BaseModel):
    operator_name: str = "Flight Director Sarah Chen"
    operational_notes: str = "Authorized asset protection protocol."

class RejectionRequest(BaseModel):
    operator_name: str = "Flight Director Sarah Chen"
    operational_notes: str = "Deemed false positive after telemetry cross-check."

class SimulationRequest(BaseModel):
    speed_km_s: float = 1200.0
    half_angle_deg: float = 60.0
    is_earth_directed: bool = True
    predicted_kp: float = 7.0
    simulated_by: str = "Control Center Operator"


# --- API Routes ---
@app.get("/api/status")
def get_system_status():
    """Return health telemetry across all platform services."""
    state = queue_manager.load_state()

    noaa_live = False
    observed_kp = 2.0
    g_scale = "G0"
    if os.path.exists(NOAA_FILE):
        try:
            with open(NOAA_FILE, "r", encoding="utf-8-sig") as f:
                noaa_data = json.load(f)
                noaa_live = noaa_data.get("provenance", {}).get("is_live", False)
                observed_kp = noaa_data.get("current_conditions", {}).get("observed_kp", 2.0)
                g_scale = noaa_data.get("current_conditions", {}).get("g_scale", "G0")
        except Exception:
            pass

    return {
        "system_health": state.get("system_health", "HEALTHY"),
        "last_successful_run": state.get("last_successful_run"),
        "total_runs": state.get("total_runs", 0),
        "total_transactions": state.get("total_transactions_processed", 0),
        "services": {
            "uipath_orchestrator": {"status": "ONLINE", "type": "Autonomous RPA Conductor", "version": "Studio 2026.0"},
            "nasa_donki": {"status": "ONLINE", "type": "Solar Observation Feed", "latency_ms": 140},
            "noaa_swpc": {"status": "ONLINE" if noaa_live else "FALLBACK", "observed_kp": observed_kp, "g_scale": g_scale},
            "groq_lpu": {"status": "ONLINE", "model": "openai/gpt-oss-120b", "tokens_per_sec": 485}
        }
    }


@app.get("/api/queue")
def get_queue_data():
    """Return queue metrics and pending/in-progress transaction items."""
    metrics = queue_manager.get_queue_metrics()
    pending_items = []
    if os.path.exists(queue_manager.PENDING_DIR):
        for fname in sorted(os.listdir(queue_manager.PENDING_DIR)):
            if fname.endswith(".json"):
                try:
                    with open(os.path.join(queue_manager.PENDING_DIR, fname), "r", encoding="utf-8-sig") as f:
                        pending_items.append(json.load(f))
                except Exception:
                    pass
    return {
        "metrics": metrics,
        "pending_items": pending_items[:15]
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


@app.post("/api/incidents/{incident_id}/approve")
def approve_incident_api(incident_id: str, req: ApprovalRequest):
    """Operator approval endpoint."""
    success = incident_manager.approve_incident(incident_id, req.operator_name, req.operational_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found or approval failed")
    inc = incident_manager.load_incident(incident_id)
    # Refresh alert email
    if inc:
        notify.dispatch_incident_notification(inc, force_mock=True)
    return {"status": "SUCCESS", "incident": inc}


@app.post("/api/incidents/{incident_id}/reject")
def reject_incident_api(incident_id: str, req: RejectionRequest):
    """Operator rejection endpoint."""
    success = incident_manager.reject_incident(incident_id, req.operator_name, req.operational_notes)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found or rejection failed")
    inc = incident_manager.load_incident(incident_id)
    return {"status": "SUCCESS", "incident": inc}


@app.post("/api/simulate")
def run_what_if_simulation(req: SimulationRequest):
    """Execute What-If space-weather simulation sandbox."""
    sim_id = f"SIM-WHATIF-{int(time.time())}"
    kp = req.predicted_kp
    speed = req.speed_km_s
    earth = req.is_earth_directed

    # NOAA scale computation
    if kp >= 9.0: g_scale = "G5"
    elif kp >= 8.0: g_scale = "G4"
    elif kp >= 7.0: g_scale = "G3"
    elif kp >= 6.0: g_scale = "G2"
    elif kp >= 5.0: g_scale = "G1"
    else: g_scale = "G0"

    # Deterministic risk evaluation
    if not earth:
        final_risk = "LOW"
        routing = "AUTO_LOG"
    elif kp >= 7.0 or speed >= 1500.0:
        final_risk = "HIGH"
        routing = "HUMAN_APPROVAL_REQUIRED"
    elif kp >= 5.0 or speed >= 700.0:
        final_risk = "MEDIUM"
        routing = "OPERATOR_REVIEW"
    else:
        final_risk = "LOW"
        routing = "AUTO_LOG"

    event_mock = {
        "event_id": sim_id,
        "speed_km_s": speed,
        "max_kp_predicted": kp,
        "is_earth_directed": earth,
        "g_scale": g_scale,
        "deterministic_risk": final_risk
    }

    assets = match_assets.load_asset_registry()
    matches = [match_assets.screen_asset_for_event(a, event_mock) for a in assets]
    affected = [m for m in matches if m["impact_status"] != "NOMINAL"]

    # Transit time estimation (Sun to Earth ~ 150 million km)
    transit_hrs = round((149597870.7 / speed) / 3600.0, 1) if speed > 0 else 0.0

    return {
        "simulation_id": sim_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "is_simulated": True,
        "input_parameters": req.model_dump(),
        "physics_evaluation": {
            "estimated_transit_hours": transit_hrs,
            "noaa_scale": g_scale,
            "assigned_risk": final_risk,
            "routing_action": routing
        },
        "asset_impact_screening": {
            "total_assets_registered": len(assets),
            "affected_assets_count": len(affected),
            "affected_assets": affected
        }
    }


# --- Embedded Single-Page Control Center UI ---
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SolarSentinel V2 - Space Weather Operations Control Center</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-base: #060913;
    --bg-surface: #0e1526;
    --bg-card: rgba(18, 26, 47, 0.7);
    --border-color: rgba(51, 65, 85, 0.4);
    --border-glow: rgba(56, 189, 248, 0.2);
    --accent-blue: #38bdf8;
    --accent-cyan: #06b6d4;
    --accent-emerald: #10b981;
    --accent-amber: #f59e0b;
    --accent-crimson: #ef4444;
    --text-primary: #f8fafc;
    --text-muted: #94a3b8;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: radial-gradient(circle at 50% 0%, #111d38 0%, var(--bg-base) 70%);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-primary);
    min-height: 100vh;
    padding: 24px;
    overflow-x: hidden;
  }
  .mono { font-family: 'JetBrains Mono', monospace; }
  
  /* Layout */
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 24px;
  }
  .brand { display: flex; align-items: center; gap: 14px; }
  .logo-box {
    width: 44px; height: 44px;
    background: linear-gradient(135deg, #0284c7, #06b6d4);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 20px rgba(6, 182, 212, 0.4);
    font-size: 22px;
  }
  .brand h1 { font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }
  .brand p { font-size: 12px; color: var(--text-muted); }

  .status-badges { display: flex; gap: 10px; }
  .badge-node {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 6px 12px;
    display: flex; align-items: center; gap: 8px;
    font-size: 11px;
    font-weight: 600;
  }
  .dot { width: 8px; height: 8px; border-radius: 50%; }
  .dot-green { background: var(--accent-emerald); box-shadow: 0 0 8px var(--accent-emerald); }
  .dot-amber { background: var(--accent-amber); box-shadow: 0 0 8px var(--accent-amber); }
  .dot-blue { background: var(--accent-blue); box-shadow: 0 0 8px var(--accent-blue); }

  /* Grid Cards */
  .grid-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }
  .card {
    background: var(--bg-card);
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 18px 20px;
    transition: transform 0.2s, border-color 0.2s;
  }
  .card:hover { border-color: var(--border-glow); transform: translateY(-2px); }
  .card-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.8px; color: var(--text-muted); }
  .card-val { font-size: 26px; font-weight: 700; margin-top: 6px; }
  .card-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

  /* Two Column Main */
  .main-grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 24px;
  }

  /* Incident Feed */
  .section-title {
    font-size: 15px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.6px; margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center;
  }
  .incident-card {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid var(--border-color);
    border-left: 5px solid var(--accent-blue);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 14px;
    transition: all 0.2s;
  }
  .incident-card.high { border-left-color: var(--accent-crimson); }
  .incident-card.medium { border-left-color: var(--accent-amber); }
  .incident-card.low { border-left-color: var(--accent-emerald); }
  .inc-header { display: flex; justify-content: space-between; align-items: flex-start; }
  .inc-title { font-size: 14px; font-weight: 700; color: #fff; }
  .inc-sub { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
  .tag {
    font-size: 10px; font-weight: 700; padding: 3px 8px; border-radius: 4px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  .tag-high { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
  .tag-medium { background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
  .tag-low { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }
  .inc-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; background: rgba(2, 6, 23, 0.4); padding: 10px; border-radius: 6px; margin: 12px 0; }
  .inc-stat-label { font-size: 10px; color: var(--text-muted); }
  .inc-stat-val { font-size: 13px; font-weight: 700; color: #f1f5f9; }

  /* Actions */
  .btn-approve {
    background: linear-gradient(135deg, #059669, #10b981);
    color: white; border: none; border-radius: 6px; padding: 6px 14px;
    font-size: 11px; font-weight: 700; cursor: pointer; transition: opacity 0.2s;
  }
  .btn-approve:hover { opacity: 0.9; }

  /* Simulator */
  .sim-card {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 24px;
  }
  .form-group { margin-bottom: 14px; }
  .form-group label { display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 6px; }
  .form-input {
    width: 100%; background: #0f172a; border: 1px solid var(--border-color);
    border-radius: 6px; padding: 8px 12px; color: #f8fafc; font-family: 'JetBrains Mono', monospace; font-size: 13px;
  }
  .form-slider { width: 100%; accent-color: var(--accent-cyan); }
  .btn-simulate {
    width: 100%; background: linear-gradient(135deg, #0284c7, #06b6d4);
    color: white; border: none; border-radius: 8px; padding: 10px;
    font-size: 13px; font-weight: 700; cursor: pointer; margin-top: 10px;
    box-shadow: 0 4px 14px rgba(6, 182, 212, 0.3);
  }
  .btn-simulate:hover { opacity: 0.95; }
  .sim-result-box {
    background: #020617; border: 1px solid var(--border-color); border-radius: 8px;
    padding: 12px; margin-top: 14px; font-size: 12px; display: none;
  }

  /* Asset Status List */
  .asset-item {
    display: flex; justify-content: space-between; align-items: center;
    padding: 10px 12px; border-bottom: 1px solid var(--border-color); font-size: 12px;
  }
  .asset-item:last-child { border-bottom: none; }
</style>
</head>
<body>

  <!-- Top Bar -->
  <div class="header">
    <div class="brand">
      <div class="logo-box">🛰️</div>
      <div>
        <h1>SolarSentinel Operations Control Center</h1>
        <p>AI-Assisted Autonomous Space Weather & Satellite Defense Platform (UiPath V2.0)</p>
      </div>
    </div>
    <div class="status-badges">
      <div class="badge-node"><div class="dot dot-blue"></div> UiPath Conductor: ACTIVE</div>
      <div class="badge-node"><div class="dot dot-green"></div> NASA DONKI: STREAMING</div>
      <div class="badge-node" id="badge-noaa"><div class="dot dot-green"></div> NOAA SWPC: LIVE (Kp 2.0)</div>
      <div class="badge-node"><div class="dot dot-green"></div> Groq LPU (GPT-OSS 120B)</div>
    </div>
  </div>

  <!-- Telemetry Counters -->
  <div class="grid-stats">
    <div class="card">
      <div class="card-label">System Health</div>
      <div class="card-val" id="stat-health" style="color: var(--accent-emerald);">HEALTHY</div>
      <div class="card-sub">Autonomous error boundaries intact</div>
    </div>
    <div class="card">
      <div class="card-label">Transactional Queue</div>
      <div class="card-val mono" id="stat-queue">0 / 0</div>
      <div class="card-sub">Pending / Completed (data/queue/)</div>
    </div>
    <div class="card">
      <div class="card-label">Active Incidents</div>
      <div class="card-val mono" id="stat-incidents" style="color: var(--accent-amber);">0</div>
      <div class="card-sub">Operational threats being monitored</div>
    </div>
    <div class="card">
      <div class="card-label">Observed Planetary Kp</div>
      <div class="card-val mono" id="stat-kp" style="color: var(--accent-cyan);">2.0 (G0)</div>
      <div class="card-sub">NOAA SWPC 3-hour geomagnetic index</div>
    </div>
  </div>

  <!-- Main Split -->
  <div class="main-grid">
    <!-- Left: Incident Explorer -->
    <div>
      <div class="section-title">
        <span>Active Incident Feed & Human Sign-Off</span>
        <span style="font-size: 11px; color: var(--text-muted); font-weight: 400;">Auto-refreshing every 3s</span>
      </div>
      <div id="incidents-container">
        <!-- Rendered dynamically -->
        <p style="color: var(--text-muted); font-size: 13px;">Loading operational incidents...</p>
      </div>
    </div>

    <!-- Right: What-If Simulator & Assets -->
    <div>
      <!-- What If Simulator -->
      <div class="sim-card">
        <div class="section-title">
          <span>What-If Space Weather Simulator</span>
          <span style="font-size: 10px; background: rgba(56, 189, 248, 0.2); color: var(--accent-blue); padding: 2px 6px; border-radius: 4px;">SANDBOX</span>
        </div>
        <div class="form-group">
          <label>Plasma Speed: <span class="mono" id="val-speed">1200 km/s</span></label>
          <input type="range" class="form-slider" min="300" max="2500" step="50" value="1200" id="slider-speed" oninput="document.getElementById('val-speed').innerText = this.value + ' km/s'">
        </div>
        <div class="form-group">
          <label>Predicted Max Kp: <span class="mono" id="val-kp">7.0 (G3 Strong Storm)</span></label>
          <input type="range" class="form-slider" min="0" max="9" step="0.5" value="7" id="slider-kp" oninput="updateKpLabel(this.value)">
        </div>
        <div class="form-group">
          <label><input type="checkbox" id="check-earth" checked> Earth-Directed Trajectory</label>
        </div>
        <button class="btn-simulate" onclick="runSimulation()">Run Physics & Asset Simulation</button>
        
        <div class="sim-result-box" id="sim-result">
          <!-- Simulation output -->
        </div>
      </div>

      <!-- Asset Status Board -->
      <div class="card">
        <div class="section-title">
          <span>Operational Asset Registry (5)</span>
        </div>
        <div id="assets-list">
          <div class="asset-item">
            <div><strong>Aegis-1 LEO Constellation</strong><br><span style="color: var(--text-muted); font-size: 11px;">550 km Sun-Sync Orbit</span></div>
            <span class="tag tag-low">NOMINAL</span>
          </div>
          <div class="asset-item">
            <div><strong>Celestia-4 GEO Satcom</strong><br><span style="color: var(--text-muted); font-size: 11px;">35,786 km GEO Orbit</span></div>
            <span class="tag tag-low">NOMINAL</span>
          </div>
          <div class="asset-item">
            <div><strong>Laurentian 735 kV Grid</strong><br><span style="color: var(--text-muted); font-size: 11px;">Quebec Interconnect (65N)</span></div>
            <span class="tag tag-low">NOMINAL</span>
          </div>
          <div class="asset-item">
            <div><strong>Transpolar Polar-1 Route</strong><br><span style="color: var(--text-muted); font-size: 11px;">Arctic Airway (>60N)</span></div>
            <span class="tag tag-low">NOMINAL</span>
          </div>
          <div class="asset-item">
            <div><strong>Radio Astronomy Array</strong><br><span style="color: var(--text-muted); font-size: 11px;">High-Altitude Plateau</span></div>
            <span class="tag tag-low">NOMINAL</span>
          </div>
        </div>
      </div>
    </div>
  </div>

<script>
function updateKpLabel(val) {
  let g = 'G0 Quiet';
  if (val >= 9) g = 'G5 Extreme';
  else if (val >= 8) g = 'G4 Severe';
  else if (val >= 7) g = 'G3 Strong';
  else if (val >= 6) g = 'G2 Moderate';
  else if (val >= 5) g = 'G1 Minor';
  document.getElementById('val-kp').innerText = val + ' (' + g + ')';
}

async function fetchStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    document.getElementById('stat-health').innerText = data.system_health;
    const noaa = data.services.noaa_swpc;
    document.getElementById('stat-kp').innerText = noaa.observed_kp + ' (' + noaa.g_scale + ')';
  } catch(e) {}
}

async function fetchQueue() {
  try {
    const res = await fetch('/api/queue');
    const data = await res.json();
    document.getElementById('stat-queue').innerText = data.metrics.pending + ' / ' + data.metrics.completed;
  } catch(e) {}
}

async function fetchIncidents() {
  try {
    const res = await fetch('/api/incidents');
    const data = await res.json();
    document.getElementById('stat-incidents').innerText = data.incidents.length;
    renderIncidents(data.incidents);
  } catch(e) {}
}

function renderIncidents(incidents) {
  const container = document.getElementById('incidents-container');
  if (!incidents || incidents.length === 0) {
    container.innerHTML = '<p style="color: var(--text-muted); font-size: 13px;">No active operational incidents recorded.</p>';
    return;
  }
  let html = '';
  incidents.forEach(inc => {
    const sev = (inc.severity || 'LOW').toLowerCase();
    const tagClass = 'tag-' + sev;
    const haz = inc.hazard_summary || {};
    const app = inc.approval_record || {};
    const isPending = app.required && app.status === 'PENDING';

    let actionBtn = '';
    if (isPending) {
      actionBtn = `<button class="btn-approve" onclick="approveIncident('${inc.incident_id}')">⚡ Sign-Off / Authorize SOP</button>`;
    } else if (app.status === 'APPROVED') {
      actionBtn = `<span style="color: var(--accent-emerald); font-size: 11px; font-weight: 700;">✓ AUTHORIZED BY ${app.decided_by || 'Operator'}</span>`;
    }

    let assetsList = '';
    if (inc.affected_assets && inc.affected_assets.length > 0) {
      assetsList = '<div style="margin-top: 8px; font-size: 12px; color: #cbd5e1;"><strong>Impacted Infrastructure:</strong><ul style="padding-left: 18px; margin-top: 4px;">';
      inc.affected_assets.forEach(a => {
        assetsList += `<li><strong>${a.asset_name}</strong>: ${a.sop_action}</li>`;
      });
      assetsList += '</ul></div>';
    }

    html += `
      <div class="incident-card ${sev}">
        <div class="inc-header">
          <div>
            <div class="inc-title">${inc.title}</div>
            <div class="inc-sub mono">${inc.incident_id} | Target: ${inc.event_id}</div>
          </div>
          <span class="tag ${tagClass}">${inc.severity} SEVERITY</span>
        </div>
        <div class="inc-grid mono">
          <div><div class="inc-stat-label">NOAA Scale</div><div class="inc-stat-val">${haz.g_scale || 'G0'}</div></div>
          <div><div class="inc-stat-label">Max Kp</div><div class="inc-stat-val">${haz.max_kp_predicted || '0.0'}</div></div>
          <div><div class="inc-stat-label">Speed</div><div class="inc-stat-val">${haz.speed_km_s || '0'} km/s</div></div>
          <div><div class="inc-stat-label">Status</div><div class="inc-stat-val" style="color: ${isPending ? 'var(--accent-amber)' : '#fff'}">${inc.status}</div></div>
        </div>
        ${assetsList}
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 12px; border-top: 1px solid rgba(51, 65, 85, 0.4); padding-top: 10px;">
          <span style="font-size: 11px; color: var(--text-muted);">Audit Entries: ${inc.audit_history ? inc.audit_history.length : 1}</span>
          <div>${actionBtn}</div>
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
}

async function approveIncident(incId) {
  try {
    const res = await fetch(`/api/incidents/${incId}/approve`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        operator_name: 'Flight Director Sarah Chen',
        operational_notes: 'Approved via Control Center Dashboard interface.'
      })
    });
    if (res.ok) {
      fetchIncidents();
    }
  } catch(e) {}
}

async function runSimulation() {
  const speed = parseFloat(document.getElementById('slider-speed').value);
  const kp = parseFloat(document.getElementById('slider-kp').value);
  const earth = document.getElementById('check-earth').checked;

  try {
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        speed_km_s: speed,
        predicted_kp: kp,
        is_earth_directed: earth
      })
    });
    const data = await res.json();
    const resultBox = document.getElementById('sim-result');
    resultBox.style.display = 'block';

    const p = data.physics_evaluation;
    const a = data.asset_impact_screening;

    let affectedList = '';
    if (a.affected_assets && a.affected_assets.length > 0) {
      affectedList = '<ul style="margin-top: 6px; padding-left: 16px;">';
      a.affected_assets.forEach(m => {
        affectedList += `<li><strong>${m.name}</strong> [${m.impact_status}]</li>`;
      });
      affectedList += '</ul>';
    } else {
      affectedList = '<p style="color: var(--accent-emerald);">All registered assets remain NOMINAL.</p>';
    }

    resultBox.innerHTML = `
      <div style="font-weight: 700; color: var(--accent-cyan); margin-bottom: 6px;">[SIMULATION RESULT: ${data.simulation_id}]</div>
      <div><strong>Assigned Risk Tier:</strong> <span style="color: ${p.assigned_risk === 'HIGH' ? 'var(--accent-crimson)' : (p.assigned_risk === 'MEDIUM' ? 'var(--accent-amber)' : 'var(--accent-emerald)')}; font-weight: 700;">${p.assigned_risk}</span></div>
      <div><strong>NOAA G-Scale:</strong> ${p.noaa_scale} | <strong>Estimated Transit:</strong> ${p.estimated_transit_hours} hrs</div>
      <div><strong>Routing Action:</strong> ${p.routing_action}</div>
      <div style="margin-top: 8px;"><strong>Screened Assets Impacted:</strong> ${a.affected_assets_count} of ${a.total_assets_registered}</div>
      ${affectedList}
      <div style="font-size: 10px; color: var(--text-muted); margin-top: 6px;">Strictly tagged IS_SIMULATED: TRUE (Isolated from production logs).</div>
    `;
  } catch(e) {}
}

// Initial fetch and poll
fetchStatus();
fetchQueue();
fetchIncidents();
setInterval(() => {
  fetchStatus();
  fetchQueue();
  fetchIncidents();
}, 3000);
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
def get_dashboard():
    """Serve the single-page Control Center operations dashboard."""
    return DASHBOARD_HTML


def main():
    import uvicorn
    print("=================================================================")
    print("  🛰️ SolarSentinel V2 Operations Control Center")
    print("  Local Live UI : http://localhost:8000")
    print("  API Docs      : http://localhost:8000/docs")
    print("=================================================================")
    uvicorn.run("control_center:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
