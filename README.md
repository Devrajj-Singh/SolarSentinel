# SolarSentinel V2 🛰️☀️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![UiPath: Studio 2026.0](https://img.shields.io/badge/UiPath-Studio%202026.0-orange.svg)](https://www.uipath.com/)
[![LLM: GPT--OSS%20120B](https://img.shields.io/badge/AI%20Model-GPT--OSS%20120B%20(Groq)-green.svg)](https://groq.com/)

**SolarSentinel V2** is an enterprise-grade, **UiPath-centric Space Weather Operations, Incident Detection, Asset Risk Assessment, Alerting, and Human-in-the-Loop Automation Platform**.

It continuously ingests observational solar telemetry from NASA DONKI and real-time geomagnetic disturbance feeds from NOAA Space Weather Prediction Center (SWPC), coordinates scientific reasoning via the Groq-accelerated `openai/gpt-oss-120b` open-weight model, enforces deterministic physical safety guardrails, cross-references threats against an operational infrastructure Asset Registry, and manages full incident lifecycles with Human-in-the-Loop sign-offs.

---

> ### ⚠️ Operational Safety Disclaimer
> **SolarSentinel is a research and educational decision-support platform.**  
> It is **not** an operational space-weather forecasting system and should **never** be used for direct physical control of satellites, power distribution grids, aviation routing, or life-critical infrastructure. Operational decisions must always reference official space weather agencies (such as NOAA Space Weather Prediction Center - SWPC).

---

## 🛰️ Key Features in SolarSentinel V2

```
                       NASA DONKI & NOAA SWPC
                                 │
                                 ▼
                     [UiPath Scheduled Runner]
                                 │
                   ┌─────────────┴─────────────┐
                   ▼                           ▼
            [HealthCheck.xaml]         [Initialize.xaml]
            (Probe APIs & Env)         (Load Config & State)
                   │                           │
                   └─────────────┬─────────────┘
                                 ▼
                 [CollectSpaceWeatherData.xaml]
                 (Resilient Ingestion with Retries)
                                 │
                                 ▼
                     [DetectNewEvents.xaml]
                 (Idempotent Deduplication Check)
                                 │
                                 ▼
                    [ProcessTransactions.xaml]
            (Per-Event Transactional Processing Loop)
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
[NormalizeEvent]          [AnalyzeEvent]              [EvaluateRisk]
(Kinematic Extraction)    (Groq GPT-OSS 120B)         (NOAA G/S/R Scales)
     │                           │                           │
     └───────────────────────────┼───────────────────────────┘
                                 ▼
                         [MatchAssets.xaml]
                   (config/asset_registry.json)
                                 │
                                 ▼
                        [CreateIncident.xaml]
                    (Generate Incident Record)
                                 │
                    ┌────────────┴────────────┐
                    ▼                         ▼
        [SendNotifications.xaml]     [HandleApproval.xaml]
     (HTML Email / Mock / Webhook)  (Human-in-the-Loop Sign-off)
                    │                         │
                    └────────────┬────────────┘
                                 ▼
                      [FinalizeRun.xaml]
           (Update monitor_state.json & Excel Logs)
```

1. **UiPath-Centric Conductor & Modular Workflows**:
   UiPath Studio modern Windows orchestrator coordinating modular sub-workflows:
   - `Initialize.xaml` & `HealthCheck.xaml`: Environment diagnostic probes and UTC monitoring window computation.
   - `CollectSpaceWeatherData.xaml`: Resilient HTTP ingestion with exponential backoff.
   - `DetectNewEvents.xaml`: Checksum-based idempotent deduplication.
   - `ProcessTransactions.xaml`: Transactional loop per space-weather event.
   - `MatchAssets.xaml`: Cross-referencing threats against operational infrastructure.
   - `CreateIncident.xaml`: Official incident dossier generation.
   - `SendNotifications.xaml`: Multi-channel briefing alerts.
   - `HandleApproval.xaml`: Human-in-the-loop sign-off gating for high-severity hazards.
   - `FinalizeRun.xaml`: Atomic state store commits.

2. **Persistent Transaction Queue & State Store**:
   - Directory-backed FIFO transactional queue (`data/queue/pending/`, `in_progress/`, `completed/`, `failed/`) replicating enterprise UiPath Orchestrator queue semantics locally with zero external license fees.
   - Idempotency hashing (`scripts/queue_manager.py`): Repeated pipeline executions against the same observation window create **0 duplicate queue items and 0 duplicate alerts**.

3. **Multi-Source Space Weather Feeds**:
   - **NASA DONKI**: CME velocity, source coordinates, angular width, and interplanetary shock predictions.
   - **NOAA SWPC**: Real-time Planetary Kp index (`scripts/fetch_noaa.py`), active Geomagnetic Storm Watches/Warnings, and official NOAA scales (G1–G5 Geomagnetic, S1–S5 Radiation, R1–R5 Radio Blackouts).

4. **Operational Asset Registry (`config/asset_registry.json`)**:
   Cross-references hazards against critical space and ground assets:
   - **Aegis-1 LEO Constellation**: Thermospheric neutral density surge, atmospheric drag, surface charging.
   - **Celestia-4 GEO Satcom**: Relativistic electron deep dielectric discharge ($E > 2$ MeV), star tracker blindness.
   - **Laurentian 735 kV Northern Grid**: Geomagnetically Induced Currents (GIC), transformer core half-cycle saturation.
   - **Transpolar Flight Corridor Polar-1**: Polar Cap Absorption (PCA) HF radio blackout, flight rerouting.
   - **Radio Astronomy Array**: Solar radio bursts, ionospheric scintillation phase degradation.

5. **Incident Management Subsystem (`scripts/incident_manager.py`)**:
   - Structured JSON incident records in `data/incidents/INC-*.json` with severity levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) and lifecycle states (`OPEN` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `AWAITING_APPROVAL` $\rightarrow$ `RESOLVED`).
   - Immutable audit trail capturing every state transition, operator name, and rationale.

6. **Multi-Channel Alerting & Safe Local Mock Inbox**:
   - **Safe Local Mock Inbox (`output/emails/`)**: Generates beautiful, aerospace-styled dark-mode `.html` and `.txt` operational briefings directly to disk. Enables 100% offline demonstration without requiring real SMTP credentials or risking spam.
   - **Live SMTP Transmission**: Seamlessly dispatches real emails when credentials are provided in `config/settings.json`.
   - **Webhook Payloads (`output/audit/`)**: Pre-formatted Microsoft Teams Adaptive Cards and Slack Block Kit JSON payloads.

7. **Operations Control Center UI & API (`scripts/control_center.py`)**:
   - Modern dark-mode dashboard running on FastAPI (`http://localhost:8000`).
   - Live telemetry monitors for NASA, NOAA, Groq, and UiPath.
   - Transactional queue counters with real-time polling.
   - Interactive incident feed with one-click **"⚡ Sign-Off / Authorize SOP"** button.
   - **What-If Space Weather Simulator Sandbox**: Interactive sliders to test hypothetical coronal mass ejections (Speed, Kp, Direction) with strict `IS_SIMULATED: TRUE` isolation.

8. **Deterministic College Demo Suite (`scripts/run_demo.py`)**:
   Zero-friction, pre-scripted scenarios demonstrating:
   - `Scenario 1`: Quiet Baseline Monitoring (G0 conditions, zero false alarms).
   - `Scenario 2`: Moderate Geomagnetic Storm (G2) (LEO aerodynamic drag mitigation).
   - `Scenario 3`: Severe Solar Superstorm (G4/G5) (Critical Grid & GEO exposure, approval gate).
   - `Scenario 4`: Idempotency Proof (Re-running identical stream produces 0 duplicates).
   - `Scenario 5`: Cloudflare / API Fallback Resilience (Deterministic physical safety rules).
   - `Scenario 6`: Human-in-the-Loop Sign-Off (Flight Director authorization flow).
   - `Scenario 7`: What-If Carrington-Class Simulation Sandbox.

---

## 🛠️ Technology Stack

| Layer | Technology | Details |
|:---|:---|:---|
| **Central RPA Conductor** | UiPath Studio (Windows, Modern) | Core state machine, exception boundaries, workflows |
| **Observation Feeds** | NASA DONKI & NOAA SWPC | Live REST APIs for CMEs, Kp index, and storm warnings |
| **Scientific Reasoning** | GPT-OSS 120B via Groq LPUs | Low-latency (~500 tokens/sec) scientific analysis |
| **Deterministic Risk Engine**| Python 3.10+ | Hard physical boundary rules & NOAA G/S/R scales |
| **Queue & State Engine** | Python File-System Semaphore | Idempotent FIFO queue (`data/queue/`) & state store |
| **Control Center & API** | FastAPI + Uvicorn + HTML5/CSS3 | Dark-mode operations dashboard at `http://localhost:8000` |
| **Reporting & Dossiers** | OpenPyXL + Pandas + Markdown | Multi-tab Excel Master Log & executive dossiers |

---

## 🚀 Quickstart Guide

### 1. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Devrajj-Singh/SolarSentinel.git
cd SolarSentinel

# Set up virtual environment & dependencies
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration Setup
```bash
# Copy the example settings template
cp config/settings.example.json config/settings.json
```
Edit `config/settings.json` to insert your Groq API key and optional NASA/SMTP credentials:
```json
{
  "groq": {
    "api_key": "your_groq_api_key_here",
    "model": "openai/gpt-oss-120b"
  }
}
```
*(Note: `config/settings.json` is protected by `.gitignore` and never committed to source control).*

### 3. Run the Autonomous Pipeline
Execute the full end-to-end autonomous operational pipeline:
```bash
python scripts/run_pipeline.py
```
This runs all 9 autonomous steps: NOAA ingestion, deduplication, AI scientific reasoning, deterministic risk evaluation, asset matching, incident dossier creation, notification dispatch, multi-sheet Excel logging, and state commit.

### 4. Launch the Operations Control Center
```bash
python scripts/control_center.py
```
Open your browser to:
- **Control Center UI**: [http://localhost:8000](http://localhost:8000)
- **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5. Run the College Demo Suite
Run any of the 7 pre-scripted evaluation scenarios:
```bash
# Run a specific scenario (1-7)
python scripts/run_demo.py --scenario 3

# Run all 7 scenarios sequentially
python scripts/run_demo.py --all
```

---

## 📂 Repository Structure

```
SolarSentinel/
├── config/
│   ├── asset_registry.json         # Operational infrastructure asset registry
│   ├── settings.example.json       # Sanitized configuration template
│   └── settings.json               # Local API credentials (git-ignored)
├── data/
│   ├── incidents/                  # Official space-weather incident dossiers
│   ├── queue/                      # Persistent transactional queue
│   │   ├── pending/                # Awaiting execution
│   │   ├── in_progress/            # Active transaction processing
│   │   ├── completed/              # Successfully committed transactions
│   │   └── failed/                 # Dead-letter / retry queue
│   ├── processed/                  # Normalized AI & risk assessment outputs
│   ├── raw/                        # Ingested NASA DONKI & NOAA SWPC feeds
│   ├── sample/                     # Pre-packaged versioned evaluation samples
│   └── state/                      # monitor_state.json operational tracking
├── output/
│   ├── audit/                      # Microsoft Teams / Slack webhook payloads
│   ├── emails/                     # Safe Local Mock Inbox (HTML & TXT briefings)
│   ├── logs/                       # Master Excel Log (3 Tabs) & CSV audit log
│   └── reports/                    # Executive Markdown briefing reports
├── scripts/
│   ├── analyze_events.py           # GPT-OSS 120B AI scientific analysis (Groq)
│   ├── control_center.py           # FastAPI Control Center & embedded dashboard
│   ├── fetch_noaa.py               # NOAA SWPC live geomagnetic data collector
│   ├── generate_reports.py         # Multi-sheet Excel & Markdown report engine
│   ├── incident_manager.py         # Space weather incident lifecycle controller
│   ├── match_assets.py             # Asset-aware vulnerability screening engine
│   ├── notify.py                   # Multi-channel notification dispatcher
│   ├── queue_manager.py            # Transaction queue & state store CLI/library
│   ├── risk_engine.py              # Deterministic multi-scale risk engine
│   ├── run_demo.py                 # Deterministic College Demo Suite (Scenarios 1-7)
│   └── run_pipeline.py             # End-to-end master autonomous pipeline
├── uipath/SolarSentinel/
│   ├── CollectSpaceWeatherData.xaml# Resilient NASA DONKI HTTP ingestion
│   ├── CreateIncident.xaml         # Incident creation workflow
│   ├── DetectNewEvents.xaml        # Idempotent deduplication check
│   ├── FinalizeRun.xaml            # State store persistence
│   ├── HandleApproval.xaml         # Human-in-the-loop approval gate
│   ├── HealthCheck.xaml            # Pre-flight diagnostic probe
│   ├── Initialize.xaml             # Configuration & UTC window initialization
│   ├── Main.xaml                   # Master orchestrator & TryCatch error boundary
│   ├── MatchAssets.xaml            # Operational asset matching workflow
│   ├── NormalizeEvents.xaml        # CME metric normalization
│   ├── ProcessTransactions.xaml    # Transaction item loop
│   ├── SendNotifications.xaml      # Multi-channel notification dispatch
│   └── project.json                # UiPath project configuration
├── docs/
│   ├── architecture.md             # V1 architectural specifications
│   └── v2_plan.md                  # SolarSentinel V2 master engineering plan
└── README.md
```

---

## 📊 Master Excel Log Structure (`events_log.xlsx`)

The generated Excel workbook (`output/logs/events_log.xlsx`) features three styled, frozen-header tabs:

1. **`CME Event Log`**: Ingested and normalized solar events, kinematic parameters, AI confidence scores, NOAA planetary Kp predictions, deterministic risk ratings, and physical rule triggers.
2. **`Asset Screening`**: Operational space and ground infrastructure matches, criticality tiers, impact statuses (`POTENTIALLY_AFFECTED`, `MONITORING_ADVISED`, `NOMINAL`), triggering factors, and specific Standard Operating Procedure (SOP) mitigation actions.
3. **`Incident Register`**: Official incident records, unique incident IDs, target event associations, assigned severities, real-time lifecycle statuses, and human-in-the-loop authorization states.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
