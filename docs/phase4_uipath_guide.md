# Phase 4 Guide: AI Scientific Analysis Layer with GPT-OSS 120B in UiPath Studio

This guide provides step-by-step instructions for implementing the **AI Scientific Analysis Layer** (`AnalyzeEvents.xaml`) in **UiPath Studio** and integrating the **GPT-OSS 120B** reasoning model into the SolarSentinel pipeline.

---

## 1. Overview & Architectural Motivation

### Why GPT-OSS 120B?
**`gpt-oss-120b`** is an open-weight Mixture-of-Experts (MoE) language model developed by OpenAI:
- **Architecture**: ~117 Billion total parameters with **5.1 Billion active parameters per token**, offering high reasoning throughput with low inference latency.
- **Reasoning Tier**: Optimized for complex multi-step reasoning and autonomous agentic workflows (comparable to advanced reasoning models like o4-mini).
- **Context Window**: 131,072 tokens with native structured JSON schema adherence.
- **Open Standards**: Fully compatible with the standard OpenAI Chat Completions API format (`POST /v1/chat/completions`), enabling deployment via **OpenRouter** (`openai/gpt-oss-120b`), **Ollama** (`http://localhost:11434/v1`), **Groq**, **vLLM**, or self-hosted GPU endpoints.

### Pipeline Placement
```
data/raw/cme_normalized.json ──> UiPath (AnalyzeEvents.xaml) ──> GPT-OSS 120B API ──> data/processed/cme_ai_analysis.json
```

---

## 2. API Endpoints & Authentication Configuration

In `config/settings.example.json` (and `config/settings.json`), the `ai_service` section is configured for **Groq** by default:

```json
"ai_service": {
  "provider": "groq",
  "model": "openai/gpt-oss-120b",
  "endpoint": "https://api.groq.com/openai/v1/chat/completions",
  "api_key": "YOUR_GROQ_API_KEY_HERE",
  "temperature": 0.2,
  "max_tokens": 2048
}
```

### Supported Providers:
1. **Groq (Recommended - Fast LPU Inference)**:
   - Endpoint: `https://api.groq.com/openai/v1/chat/completions`
   - Model: `openai/gpt-oss-120b` (or `llama-3.3-70b-versatile`)
   - Header: `Authorization: Bearer <GROQ_API_KEY>`
   - Speed: ~500 tokens/sec
2. **OpenRouter**:
   - Endpoint: `https://openrouter.ai/api/v1/chat/completions`
   - Model: `openai/gpt-oss-120b`
   - Header: `Authorization: Bearer <OPENROUTER_API_KEY>`
3. **Local Ollama**:
   - Endpoint: `http://localhost:11434/v1/chat/completions`
   - Model: `gpt-oss:120b`
   - Header: None or dummy bearer token

---

## 3. Structured Analysis JSON Schema

Every assessment returned by GPT-OSS 120B strictly adheres to this contract:

```json
{
  "analysis_id": "ANL-2026-10-12T05:09:00-CME-001",
  "event_id": "2026-10-12T05:09:00-CME-001",
  "model_used": "gpt-oss-120b",
  "timestamp": "2026-10-14T13:28:17Z",
  "scientific_assessment": {
    "plasma_speed_evaluation": "Observed plasma speed is 741.0 km/s (moderate CME speed).",
    "earth_directed_analysis": "Trajectory is Earth-directed with arrival time: 2026-10-14T11:30Z.",
    "flare_and_source_correlation": "Source location S16E23 associated with eruptive solar prominence.",
    "geomagnetic_impact_potential": "Significant geomagnetic disturbance expected (predicted Kp 6.0, G2 Moderate storm)."
  },
  "risk_recommendation": {
    "suggested_risk_level": "HIGH",
    "confidence_score": 0.90,
    "primary_rationale": "Earth-directed shock with predicted Kp=6.0 and speed=741.0 km/s exceeding storm thresholds."
  },
  "secondary_hazards": {
    "hf_radio_blackout_risk": "MODERATE",
    "radiation_storm_risk": "MODERATE",
    "auroral_visibility_latitudes": "Mid-to-high latitudes (~50-60 deg)"
  },
  "operational_guidance": "Elevated alert: monitor satellite charging and grid phase deviations. Human review recommended."
}
```

---

## 4. Implementation in UiPath Studio (`AnalyzeEvents.xaml`)

### Workflow Arguments
Create the following arguments in `AnalyzeEvents.xaml`:

| Argument Name | Direction | Argument Type | Default Value | Description |
|---|---|---|---|---|
| `in_normalizedFilePath` | `In` | `String` | `"..\..\data\raw\cme_normalized.json"` | Path to normalized CME events |
| `in_outputFilePath` | `In` | `String` | `"..\..\data\processed\cme_ai_analysis.json"` | Target processed output path |
| `in_configFilePath` | `In` | `String` | `"..\..\config\settings.json"` | Settings file path |

---

### Step-by-Step Activities

#### Step 4.1: Log Start Message
- **Activity**: `Log Message`
- **Level**: `Info`
- **Message**: `"=== Starting Phase 4: GPT-OSS 120B AI Scientific Analysis ==="`

#### Step 4.2: Option A — Direct Python Bridge Invocation (Recommended for Studio)
Since SolarSentinel includes `scripts/analyze_events.py` (which handles API authentication, JSON schema enforcement, retry logic, and mock fallback):
1. **Activity**: `Start Process` / `Run Command`
   - **FileName**: `"python"`
   - **Arguments**: `"scripts/analyze_events.py --input data/raw/cme_normalized.json --output data/processed/cme_ai_analysis.json"`
   - **WorkingDirectory**: `"C:\Users\Devraj\SolarSentinel"`
2. **Activity**: `Path Exists`
   - **Path**: `in_outputFilePath`
   - **PathType**: `File`
   - **Exists**: `analysisExists` (Boolean)
3. **Activity**: `Log Message`
   - **Message**: `"AI Analysis generated successfully. Exists: " + analysisExists.ToString`

#### Step 4.3: Option B — Native UiPath NetHttpRequest
If executing pure UiPath without local Python:
1. **Activity**: `Read Text File` → `cme_normalized.json`
2. **Activity**: `For Each` token in `JArray.Parse(jsonContent)` where `item("is_earth_directed").Value(Of Boolean) = True`
3. **Activity**: `NetHttpRequest`
   - **Method**: `POST`
   - **RequestUrl**: `"https://openrouter.ai/api/v1/chat/completions"`
   - **Headers**:
     - `Content-Type`: `application/json`
     - `Authorization`: `"Bearer " + apiKey`
   - **TextPayload**: Formatted JSON chat payload with `model: "openai/gpt-oss-120b"`
4. **Activity**: `Write Text File` → Save consolidated assessments to `data/processed/cme_ai_analysis.json`

---

## 5. Integrating into `Main.xaml`

In `Main.xaml`, sequence the workflows end-to-end:
```
1. NetHttpRequest (NASA DONKI /CME)
2. Write Text File (data/raw/cme_response.json)
3. Invoke NormalizeEvents.xaml
   - in_inputFilePath: "data/raw/cme_response.json"
   - in_outputFilePath: "data/raw/cme_normalized.json"
4. Invoke AnalyzeEvents.xaml
   - in_normalizedFilePath: "data/raw/cme_normalized.json"
   - in_outputFilePath: "data/processed/cme_ai_analysis.json"
```

---

## 6. Verification & Testing

You can verify the AI layer standalone at any time:
```bash
# Test with deterministic mock engine (no API key required)
python scripts/analyze_events.py --mock

# Test with live GPT-OSS 120B model (requires API key in environment or settings.json)
python scripts/analyze_events.py
```
