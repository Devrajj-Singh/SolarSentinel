# SolarSentinel V2: Master Engineering & Implementation Plan

## 1. Executive Summary & Objective

**SolarSentinel V2** elevates the working V1 prototype into an enterprise-grade, **UiPath-centric Space Weather Operations, Incident Detection, Risk Assessment, Alerting, and Human-in-the-Loop Response Automation Platform**.

### Core Tenet
> **UiPath is the central automation and orchestration conductor.**  
> Python, LLM reasoning, and external services serve as modular microservices governed directly by UiPath workflows. Business rules, state transitions, transaction lifecycles, and exception handling are orchestrated from UiPath Studio.

---

## 2. V2 Core Data & Workflow Architecture

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
                    [CreateTransactions.xaml]
              (Enqueue into data/queue/pending/)
                                 │
                                 ▼
                   [ProcessTransactions.xaml]
            (Per-Event Transactional Processing Loop)
                                 │
     ┌───────────────────────────┼───────────────────────────┐
     ▼                           ▼                           ▼
[NormalizeEvent]          [AnalyzeEvent]              [EvaluateRisk]
(Extract Kinematics)      (Groq GPT-OSS 120B)         (NOAA G/S/R Scales)
     │                           │                           │
     └───────────────────────────┼───────────────────────────┘
                                 ▼
                         [MatchAssets.xaml]
                   (Cross-Check Asset Registry)
                                 │
                                 ▼
                        [CreateIncident.xaml]
                    (Generate Incident Record)
                                 │
                                 ▼
                     [SendNotifications.xaml]
                 (Email / Local Mock / Webhook)
                                 │
                                 ▼
                      [HandleApproval.xaml]
                 (Human-in-the-Loop Sign-Off)
                                 │
                                 ▼
                      [FinalizeRun.xaml]
           (Update monitor_state.json & Audit Logs)
```

---

## 3. Detailed Phase Breakdown & Tasks

### Phase V2.1: UiPath Automation Core & Reliability (Immediate Focus)

#### Objective:
Transform the batch pipeline into a reliable, stateful, and modular transactional automation system in UiPath.

#### Deliverables & Tasks:
1. **State Persistence Engine**:
   - Path: `data/state/monitor_state.json`
   - Fields: `last_successful_run`, `last_event_timestamp`, `processed_event_ids`, `event_checksums`, `consecutive_failures`, `system_health`.
   - Guarantees **idempotency**: Re-running SolarSentinel against the same NASA/NOAA data creates zero duplicate transactions or alerts.
2. **Local Persistent Transaction Queue Abstraction**:
   - Directory: `data/queue/` (`pending/`, `in_progress/`, `completed/`, `failed/`)
   - Schema: `transaction_id`, `event_id`, `status` (`NEW`, `PROCESSING`, `ANALYZED`, `RISK_ASSESSED`, `ACTION_REQUIRED`, `WAITING_APPROVAL`, `COMPLETED`, `FAILED`, `RETRY`), `attempt_count`, `timestamps`, `payload`.
   - Fully mimics enterprise UiPath Queue semantics without requiring paid Orchestrator Cloud licenses.
   - Accompanying helper: `scripts/queue_manager.py` providing transactional pop/push/update commands.
3. **Modular UiPath Workflows (`uipath/SolarSentinel/`)**:
   - `Initialize.xaml`: Validates paths, loads `settings.json`, initializes state.
   - `HealthCheck.xaml`: Pre-flight connectivity probe for NASA, NOAA, Groq API, and storage. Returns `HEALTHY`, `DEGRADED`, or `FAILED`.
   - `CollectSpaceWeatherData.xaml`: Encapsulates DONKI/NOAA HTTP retrieval with exponential backoff retries.
   - `DetectNewEvents.xaml`: Filters incoming records against `monitor_state.json` using LINQ.
   - `CreateTransactions.xaml`: Enqueues verified new/updated events into `data/queue/pending/`.
   - `FinalizeRun.xaml`: Commits processed IDs to state, archives queue files, and logs run metrics.
   - `Main.xaml`: Master state machine invoking sub-workflows with global Try-Catch error boundary.

---

### Phase V2.2: Multi-Source Intelligence & Asset-Aware Incident Management

#### Objective:
Enrich observational data with official NOAA feeds and cross-reference detected hazards against operational assets.

#### Deliverables & Tasks:
1. **NOAA SWPC Ingestion**:
   - Endpoints: `https://services.swpc.noaa.gov/text/` and `https://services.swpc.noaa.gov/json/`
   - Products: Real-time Kp index, Solar Flare X-ray flux, active Geomagnetic Watches/Warnings.
   - Data provenance tagging: `source`, `source_url`, `retrieved_at`, `observed_or_forecast`.
2. **Multi-Hazard Deterministic Risk Engine**:
   - Classify events into official NOAA Space Weather Scales:
     - **G-Scale (Geomagnetic Storms)**: G1 (Minor, Kp=5) to G5 (Extreme, Kp=9).
     - **S-Scale (Solar Radiation Storms)**: S1 ($10^1$ pfu) to S5 ($10^5$ pfu).
     - **R-Scale (Radio Blackouts)**: R1 (M1 flare) to R5 (X20 flare).
3. **Asset Registry (`config/asset_registry.json`)**:
   - Define operational assets (LEO Satellites, GEO Satellites, High-Latitude Power Grids, HF Transpolar Aviation, Radio Observatories).
   - Attributes: `asset_id`, `name`, `type`, `location`, `relevant_hazards`, `min_alert_threshold`, `contact_email`, `policy_action`.
4. **Asset-Aware Policy Matcher (`MatchAssets.xaml` / `scripts/match_assets.py`)**:
   - Matches event hazard severity against asset thresholds.
   - Uses conservative terminology: *"screening match"*, *"potentially relevant"*, *"requires operator review"*.
5. **Incident Management Model**:
   - Directory: `data/incidents/`
   - Fields: `incident_id`, `event_id`, `severity`, `status` (`OPEN`, `ACKNOWLEDGED`, `INVESTIGATING`, `AWAITING_APPROVAL`, `ESCALATED`, `RESOLVED`, `CLOSED`), `affected_assets`, `audit_history`.

---

### Phase V2.3: Operational Communications & Human-in-the-Loop

#### Objective:
Implement multi-channel alerting with delivery tracking, acknowledgement deadlines, and an interactive human approval gate.

#### Deliverables & Tasks:
1. **Notification Engine (`scripts/notify.py` / `SendNotifications.xaml`)**:
   - Primary: SMTP Email alerting with HTML executive briefing.
   - Safe Local Mock Inbox (`output/emails/`): Writes rendered HTML/text emails locally when SMTP credentials are not configured, enabling 100% offline demonstration.
   - Extensible provider interfaces for Microsoft Teams Webhooks and WhatsApp Business Cloud API.
2. **Human-in-the-Loop Approval Gate (`HandleApproval.xaml`)**:
   - High-severity incidents (`HIGH` risk / G3+ storm) enter `WAITING_APPROVAL`.
   - Records reviewer identity, decision (`APPROVE`, `REJECT`, `REQUEST_MORE_INFO`), timestamp, and operational reason.
3. **Escalation Logic**:
   - Configurable acknowledgement deadlines (e.g. T+15 min, T+30 min) with escalation logging.
4. **Automated Incident Dossiers**:
   - Generate per-incident briefing cards and updated Excel master logs.

---

### Phase V2.4: Control Center Dashboard & Simulation Suite

#### Objective:
Provide an operator interface and demonstration sandbox for university / stakeholder presentations.

#### Deliverables & Tasks:
1. **Control Center API**:
   - Lightweight FastAPI service reading state, queue, incidents, and audit trails.
2. **Operations Control Center UI**:
   - Modern dark-mode dashboard displaying:
     - Real-Time System Status (NASA, NOAA, Groq, UiPath status dots)
     - Automation Pipeline Monitor (live run status, queue counters, retries)
     - Space Weather Threat Matrix (active CMEs, Kp index, hazard distribution)
     - Incident Explorer (interactive incident inspection and resolution)
3. **What-If Space Weather Simulator**:
   - Controlled sandbox allowing operators to input custom plasma speed, direction, and Kp to preview risk ratings and asset matches.
   - Simulation events are strictly tagged `IS_SIMULATED: TRUE` and isolated from production logs.
4. **Deterministic College Demo Suite (Demos 1–7)**:
   - Pre-packaged scenarios demonstrating quiet conditions, moderate storm, high-risk approval, API retry recovery, and deduplication.

---

## 4. Phase V2.1 Step-by-Step Implementation Sequence

We start immediately with **Phase V2.1**:

1. **Step 1: Scaffolding Directories & State Schema**:
   - Create `data/state/`, `data/queue/pending/`, `data/queue/in_progress/`, `data/queue/completed/`, `data/queue/failed/`, `data/incidents/`, `output/audit/`, `output/emails/`.
   - Initialize `data/state/monitor_state.json`.
2. **Step 2: Transaction Queue & State Manager (`scripts/queue_manager.py`)**:
   - Build CLI and library for enqueueing, popping, updating transaction items, and state management.
3. **Step 3: Modular UiPath Workflows**:
   - Build `Initialize.xaml`
   - Build `HealthCheck.xaml`
   - Build `DetectNewEvents.xaml`
   - Build `CreateTransactions.xaml`
   - Build `FinalizeRun.xaml`
4. **Step 4: Master Orchestrator (`Main.xaml`)**:
   - Refactor `Main.xaml` to link `Initialize` $\rightarrow$ `HealthCheck` $\rightarrow$ `Collect` $\rightarrow$ `Detect` $\rightarrow$ `Queue` $\rightarrow$ `Process` $\rightarrow$ `Finalize`.
5. **Step 5: Testing & Verification**:
   - Run end-to-end to verify idempotency (Run 1 enqueues events; Run 2 detects 0 new events).
