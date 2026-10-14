# SolarSentinel Architecture & Data Flow

## 1. System Overview

SolarSentinel is an educational and research decision-support prototype combining real-time space weather data retrieval, deterministic risk assessment, AI-assisted scientific reasoning, and RPA workflow automation using UiPath.

```
NASA DONKI APIs
      │
      ▼
UiPath HTTP Request (Data Collection)
      │
      ▼
Raw JSON Parser & Normalizer
      │
      ▼
Gemini AI Analysis (Structured Reasoner)
      │
      ▼
Deterministic Validation & Risk Engine
      │
 ┌────┴────────────────────────┬────────────────────────┐
 │                             │                        │
 ▼                             ▼                        ▼
LOW RISK                  MEDIUM RISK               HIGH RISK
[Auto-Log]               [Flag for Review]      [Human Approval Required]
 │                             │                        │
 └─────────────────────────────┼────────────────────────┘
                               │
                               ▼
                    Excel Master Event Log
                               │
                               ▼
                   Automated Summary Report
                               │
                               ▼
                      Alerts / Notifications
```

---

## 2. Core Architectural Components

### A. Data Collection Layer (UiPath)
- Periodically queries official NASA Space Weather Database Of Notifications, Knowledge, Information (DONKI) REST APIs.
- Endpoints monitored: Coronal Mass Ejections (`/CME`), Solar Flares (`/FLR`), and Geomagnetic Storms (`/GST`).
- Implements resilient network retry mechanisms and stores raw responses in structured data folders.

### B. Parsing & Normalization Layer
- Decouples raw NASA schema peculiarities into standardized internal event representations.
- Extracts key scientific telemetry: event timestamp, source location, speed, half-angle, estimated Earth impact/arrival time, and magnetic indices (Kp).

### C. AI Scientific Analysis Layer (Gemini)
- Ingests normalized event context and generates structured scientific assessment.
- Constrained to strict JSON output adhering to a predefined schema.
- Supplies confidence scores, event summaries, potential secondary impacts, and operational recommendations.

### D. Deterministic Risk & Decision Engine
- Evaluates AI outputs against hard scientific boundaries (e.g., CME Earth-directed speed thresholds, Kp-index predictions, NOAA space weather scales).
- Enforces guardrails: AI reasoning cannot override physical thresholds or execute destructive actions.

#### Risk Routing Matrix

| Severity Level | Operational Criteria | Workflow Action |
|---|---|---|
| **LOW** | Minor solar activity, non-Earth directed CMEs, low Kp index (< 5) | Auto-log to Excel; routine status report |
| **MEDIUM** | Moderate Earth-directed activity, Kp 5–6, elevated alert | Log to Excel; flag event for operator review |
| **HIGH** | Major Earth-directed CME, severe solar flare (X-class), Kp ≥ 7 | Halt auto-execution; require explicit human approval; dispatch high-priority alert |

### E. Storage & Reporting Layer (UiPath)
- Logs all processed events into a consolidated Excel database (`events_log.xlsx`).
- Maintains an immutable audit trail capturing NASA raw metrics, AI reasoning, and deterministic risk classifications.
- Compiles formatted executive summaries and incident reports for decision makers.

---

## 3. Guiding Principles & Safety Boundaries

1. **Evidence-Based**: NASA DONKI observations represent empirical ground truth; AI provides contextual reasoning; UiPath executes operations.
2. **Deterministic Authority**: Final workflow decisions remain governed by deterministic rules and human operators.
3. **Prototype Boundary**: SolarSentinel is designed for research and educational decision-support; it is not certified for direct physical control of critical infrastructure (satellites, aviation, power grids).
