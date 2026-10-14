# SolarSentinel 🛰️☀️

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**SolarSentinel** is an AI-assisted space-weather intelligence and Robotic Process Automation (RPA) system designed as an educational and research decision-support prototype. It automatically retrieves observational space weather data from NASA APIs (DONKI), standardizes scientific metrics, utilizes Gemini AI for structured contextual assessment, applies deterministic risk rules, and uses UiPath RPA to orchestrate end-to-end data logging, reporting, and operational alerting.

---

> ### ⚠️ Operational Safety Disclaimer
> **SolarSentinel is a research and educational decision-support prototype.**  
> It is **not** an operational space-weather forecasting system and should **never** be used for direct physical control of satellites, power distribution grids, aviation routing, or life-critical infrastructure. Always consult official space weather agencies (such as NOAA Space Weather Prediction Center - SWPC) for active operational alerts.

---

## Architecture Overview

SolarSentinel follows a layered, evidence-grounded architecture:

```
NASA DONKI APIs ──> UiPath RPA ──> JSON Normalizer ──> Gemini AI Analysis ──> Deterministic Risk Engine ──> Excel Log & Reports
```

For the complete architectural design and risk routing matrix, see [`docs/architecture.md`](docs/architecture.md).

---

## Project Roadmap & Phases

- [x] **Phase 1: Foundation** — Project scaffolding, configuration templates, sample NASA datasets, and repository standards.
- [x] **Phase 2: Data Collection** — UiPath HTTP retrieval for NASA DONKI endpoints (CME, FLR, GST).
- [x] **Phase 3: Data Processing** — JSON parsing, schema extraction, and metric normalization (`NormalizeEvents.xaml`).
- [x] **Phase 4: AI Analysis** — Integration with GPT-OSS 120B (OpenAI Open-Weight MoE) via Groq LPU with strict structured JSON output and schema validation.
- [x] **Phase 5: Risk Engine** — Deterministic classification rules (LOW / MEDIUM / HIGH), safety guardrails, and routing logic (`scripts/risk_engine.py`).
- [x] **Phase 6: Logging & Reporting** — Styled Excel master log (`output/logs/events_log.xlsx`) and executive space weather intelligence reports (`output/reports/`).
- [x] **Phase 7: Notifications & Polish** — High-priority alerts, human-in-the-loop approvals, and end-to-end workflow verification (`scripts/run_pipeline.py`).

---

## Technology Stack

- **RPA Platform**: UiPath Studio (System, WebAPI, and Excel Activities)
- **Data Source**: NASA Space Weather Database Of Notifications, Knowledge, Information (DONKI) REST APIs
- **AI Model**: GPT-OSS 120B (`openai/gpt-oss-120b`, OpenAI Open-Weight MoE) / Gemini fallback
- **Data & Configuration**: JSON, Microsoft Excel (`.xlsx`)
- **Scripting (Optional / Helpers)**: Python 3.10+
- **Version Control**: Git & GitHub

---

## Getting Started

### 1. Prerequisites
- [UiPath Studio](https://www.uipath.com/) installed on a Windows workstation.
- A free [NASA API Key](https://api.nasa.gov/).
- A [Google AI Studio API Key](https://aistudio.google.com/) for Gemini access.

### 2. Configuration Setup
1. Copy the sample settings template:
   ```bash
   cp config/settings.example.json config/settings.json
   ```
2. Open `config/settings.json` and insert your API keys:
   - `nasa.api_key`: Your NASA API key (or `DEMO_KEY` for light testing).
   - `gemini.api_key`: Your Gemini API key.

> **Note**: `config/settings.json` is protected by `.gitignore` and must never be committed to source control.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
