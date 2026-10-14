"""
SolarSentinel - AI Scientific Analysis Layer
Model: GPT-OSS 120B (OpenAI Open-Weight MoE) via OpenAI-compatible API
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

SYSTEM_PROMPT = """You are SolarSentinel AI, an advanced heliophysics and space-weather intelligence reasoning engine.
Your task is to analyze normalized Coronal Mass Ejection (CME) telemetry observed by NASA spacecraft (SOHO, STEREO, GOES) and modeled by the WSA-ENLIL solar wind simulation.

For each CME event provided, produce a rigorous scientific assessment adhering to the following rules:
1. Plasma Speed & Energetics:
   - < 500 km/s: Slow / ambient solar wind speed
   - 500 - 1000 km/s: Moderate CME
   - 1000 - 2000 km/s: Fast, energetic CME
   - > 2000 km/s: Extremely high-speed CME with acute shock front
2. Earth Impact Potential:
   - Non-Earth directed: Negligible geomagnetic disturbance (G0/ambient).
   - Earth-directed: Evaluate arrival window, flank vs head-on shock, and predicted max Kp index.
     * Kp < 5: Below geomagnetic storm threshold (G0)
     * Kp 5 (G1 Minor): Weak power grid fluctuations, auroral activity at high latitudes
     * Kp 6 (G2 Moderate): High-latitude power systems may experience voltage alarms
     * Kp 7 (G3 Strong): False alarms on protection devices, GPS satellite orientation irregularities
     * Kp 8 (G4 Severe) / Kp 9 (G5 Extreme): Extensive grid voltage problems, satellite surface charging, aurora seen down to mid-latitudes
3. Evidence-Grounded Output:
   - Base all reasoning on the provided parameters. Do NOT invent unobserved metrics.
4. Output Format:
   - You MUST output ONLY valid JSON matching the exact schema specified, with no markdown code fences and no extraneous text.
"""

ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "analysis_id": {"type": "string"},
        "event_id": {"type": "string"},
        "model_used": {"type": "string"},
        "timestamp": {"type": "string"},
        "scientific_assessment": {
            "type": "object",
            "properties": {
                "plasma_speed_evaluation": {"type": "string"},
                "earth_directed_analysis": {"type": "string"},
                "flare_and_source_correlation": {"type": "string"},
                "geomagnetic_impact_potential": {"type": "string"}
            },
            "required": ["plasma_speed_evaluation", "earth_directed_analysis", "flare_and_source_correlation", "geomagnetic_impact_potential"]
        },
        "risk_recommendation": {
            "type": "object",
            "properties": {
                "suggested_risk_level": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
                "confidence_score": {"type": "number"},
                "primary_rationale": {"type": "string"}
            },
            "required": ["suggested_risk_level", "confidence_score", "primary_rationale"]
        },
        "secondary_hazards": {
            "type": "object",
            "properties": {
                "hf_radio_blackout_risk": {"type": "string", "enum": ["NONE", "LOW", "MODERATE", "HIGH"]},
                "radiation_storm_risk": {"type": "string", "enum": ["NONE", "LOW", "MODERATE", "HIGH"]},
                "auroral_visibility_latitudes": {"type": "string"}
            },
            "required": ["hf_radio_blackout_risk", "radiation_storm_risk", "auroral_visibility_latitudes"]
        },
        "operational_guidance": {"type": "string"}
    },
    "required": ["analysis_id", "event_id", "model_used", "timestamp", "scientific_assessment", "risk_recommendation", "secondary_hazards", "operational_guidance"]
}


def load_config(config_path: str = "config/settings.json") -> Dict[str, Any]:
    """Load configuration from settings.json or fallback to settings.example.json."""
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    fallback_path = "config/settings.example.json"
    if os.path.exists(fallback_path):
        with open(fallback_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_normalized_events(file_path: str = "data/raw/cme_normalized.json") -> List[Dict[str, Any]]:
    """Load normalized CME events handling utf-8-sig."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Normalized events file not found at: {file_path}")
    with open(file_path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def build_analysis_prompt(event: Dict[str, Any]) -> str:
    """Format an event into a scientific prompt for GPT-OSS 120B."""
    return f"""Please perform a space weather scientific assessment for the following normalized CME event:

Event ID: {event.get('event_id')}
Catalog: {event.get('catalog')}
Start Time: {event.get('start_time')}
Source Location: {event.get('source_location')} (Active Region: {event.get('active_region')})
Instruments: {', '.join(event.get('instruments', []))}
Plasma Speed: {event.get('speed_km_s')} km/s
Half Angle: {event.get('half_angle_deg')} degrees
CME Type: {event.get('cme_type')} (Feature: {event.get('feature_code')})
Earth-Directed Trajectory: {event.get('is_earth_directed')}
Estimated Earth Arrival: {event.get('earth_arrival_time')}
Predicted Max Kp Index: {event.get('max_kp_predicted')}
Cataloger Note: {event.get('note')}

Respond ONLY with a JSON object conforming strictly to this structure:
{{
  "analysis_id": "ANL-{event.get('event_id')}",
  "event_id": "{event.get('event_id')}",
  "model_used": "gpt-oss-120b",
  "timestamp": "{datetime.now(timezone.utc).isoformat()}",
  "scientific_assessment": {{
    "plasma_speed_evaluation": "<assessment of speed and energetics>",
    "earth_directed_analysis": "<analysis of trajectory, arrival time, and directness>",
    "flare_and_source_correlation": "<assessment of source region, solar flare, or filament eruption>",
    "geomagnetic_impact_potential": "<geomagnetic disturbance estimation>"
  }},
  "risk_recommendation": {{
    "suggested_risk_level": "LOW" | "MEDIUM" | "HIGH",
    "confidence_score": <float between 0.0 and 1.0>,
    "primary_rationale": "<summary justification>"
  }},
  "secondary_hazards": {{
    "hf_radio_blackout_risk": "NONE" | "LOW" | "MODERATE" | "HIGH",
    "radiation_storm_risk": "NONE" | "LOW" | "MODERATE" | "HIGH",
    "auroral_visibility_latitudes": "<e.g., Polar latitudes (>65 deg)>"
  }},
  "operational_guidance": "<recommended monitoring and operational next steps>"
}}
"""


def call_gpt_oss_api(prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Call the OpenAI-compatible API hosting GPT-OSS 120B."""
    ai_cfg = config.get("ai_service", {})
    endpoint = ai_cfg.get("endpoint", "https://api.groq.com/openai/v1/chat/completions")
    model = ai_cfg.get("model", "openai/gpt-oss-120b")
    api_key = (
        os.environ.get("GROQ_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ai_cfg.get("api_key", "")
    )
    temperature = ai_cfg.get("temperature", 0.2)
    max_tokens = ai_cfg.get("max_tokens", 2048)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 SolarSentinel/1.0"
    }
    if api_key and api_key not in ("YOUR_AI_API_KEY_HERE", "YOUR_GROQ_API_KEY_HERE"):
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            content = resp_data["choices"][0]["message"]["content"]
            # Clean possible markdown wrapping if returned
            clean_content = content.strip()
            if clean_content.startswith("```json"):
                clean_content = clean_content[7:]
            if clean_content.startswith("```"):
                clean_content = clean_content[3:]
            if clean_content.endswith("```"):
                clean_content = clean_content[:-3]
            return json.loads(clean_content.strip())
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code} Error calling {endpoint}: {error_body or e.reason}")
    except Exception as e:
        raise RuntimeError(f"Error calling GPT-OSS 120B endpoint ({endpoint}): {e}")


def generate_mock_assessment(event: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic scientific mock evaluation for offline testing and validation."""
    is_earth = event.get("is_earth_directed", False)
    speed = event.get("speed_km_s") or 0.0
    kp = event.get("max_kp_predicted") or 0.0

    if is_earth and (speed > 1000 or kp >= 6):
        risk_level = "HIGH"
        confidence = 0.90
        geomag = f"Significant geomagnetic disturbance expected (Kp~{kp}). G2/G3 storm conditions likely."
        blackout = "MODERATE"
        rad_risk = "MODERATE"
        aurora = "Mid-to-high latitudes (~50-60 deg)"
        guidance = "Elevated alert: monitor satellite charging and grid phase deviations. Human review recommended."
    elif is_earth:
        risk_level = "LOW" if kp < 5 else "MEDIUM"
        confidence = 0.88
        geomag = f"Minor to moderate Earth shock expected on {event.get('earth_arrival_time', 'TBD')} with predicted Kp {kp}."
        blackout = "LOW"
        rad_risk = "LOW"
        aurora = "High geomagnetic latitudes (>60 deg)"
        guidance = "Routine monitoring of ACE/DSCOVR solar wind magnetic field (Bz component) as shock approaches."
    else:
        risk_level = "LOW"
        confidence = 0.95
        geomag = "Non-Earth directed trajectory. Nominal solar wind conditions expected at L1/Earth."
        blackout = "NONE"
        rad_risk = "NONE"
        aurora = "Normal auroral oval (polar regions)"
        guidance = "Standard archive logging. No operational alerts required for terrestrial or orbital infrastructure."

    return {
        "analysis_id": f"ANL-{event.get('event_id')}",
        "event_id": event.get("event_id"),
        "model_used": "gpt-oss-120b (simulated/offline)",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scientific_assessment": {
            "plasma_speed_evaluation": f"Observed plasma speed is {speed:.1f} km/s ({'slow' if speed < 500 else 'moderate' if speed < 1000 else 'fast'}).",
            "earth_directed_analysis": f"Trajectory is {'Earth-directed' if is_earth else 'directed away from Earth'} with arrival time: {event.get('earth_arrival_time') or 'N/A'}.",
            "flare_and_source_correlation": f"Source location {event.get('source_location', 'UNKNOWN')} in active region {event.get('active_region') or 'None'}.",
            "geomagnetic_impact_potential": geomag
        },
        "risk_recommendation": {
            "suggested_risk_level": risk_level,
            "confidence_score": confidence,
            "primary_rationale": f"{'Earth-directed shock' if is_earth else 'Off-axis trajectory'} with predicted Kp={kp} and speed={speed:.1f} km/s."
        },
        "secondary_hazards": {
            "hf_radio_blackout_risk": blackout,
            "radiation_storm_risk": rad_risk,
            "auroral_visibility_latitudes": aurora
        },
        "operational_guidance": guidance
    }


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SolarSentinel GPT-OSS 120B AI Analysis Layer")
    parser.add_argument("--input", default="data/raw/cme_normalized.json", help="Path to normalized CME JSON")
    parser.add_argument("--output", default="data/processed/cme_ai_analysis.json", help="Output path for AI analysis")
    parser.add_argument("--config", default="config/settings.json", help="Path to configuration file")
    parser.add_argument("--mock", action="store_true", help="Run with deterministic mock engine (no API calls)")
    parser.add_argument("--earth-directed-only", action="store_true", default=True, help="Analyze only Earth-directed events")
    args = parser.parse_args()

    print("=== SolarSentinel AI Analysis Layer ===")
    print(f"Model: GPT-OSS 120B (OpenAI Open-Weight MoE)")
    print(f"Input: {args.input}")
    print(f"Output: {args.output}")

    config = load_config(args.config)
    ai_cfg = config.get("ai_service", {})
    api_key = (
        os.environ.get("GROQ_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or ai_cfg.get("api_key", "")
    )
    use_mock = args.mock or not api_key or api_key in ("YOUR_AI_API_KEY_HERE", "YOUR_GROQ_API_KEY_HERE")

    if use_mock:
        print("[INFO] Running in mock/offline mode (no valid API key detected or --mock specified).")
    else:
        print(f"[INFO] Using live API endpoint: {ai_cfg.get('endpoint')}")
        print(f"[INFO] Model target: {ai_cfg.get('model', 'openai/gpt-oss-120b')}")

    events = load_normalized_events(args.input)
    print(f"[INFO] Loaded {len(events)} total CME events.")

    target_events = [e for e in events if e.get("is_earth_directed")] if args.earth_directed_only else events
    print(f"[INFO] Evaluating {len(target_events)} events (Earth-directed filter: {args.earth_directed_only}).")

    results = []
    for i, event in enumerate(target_events, 1):
        event_id = event.get("event_id")
        print(f"[{i}/{len(target_events)}] Analyzing {event_id} (Speed: {event.get('speed_km_s')} km/s, Kp: {event.get('max_kp_predicted')})...")
        if use_mock:
            assessment = generate_mock_assessment(event)
        else:
            prompt = build_analysis_prompt(event)
            try:
                assessment = call_gpt_oss_api(prompt, config)
            except Exception as ex:
                print(f"[WARN] Live API call failed: {ex}. Falling back to deterministic assessment.")
                assessment = generate_mock_assessment(event)

        results.append(assessment)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n[SUCCESS] Saved {len(results)} structured AI assessments to {args.output}")


if __name__ == "__main__":
    main()
