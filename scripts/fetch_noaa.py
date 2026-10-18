"""
SolarSentinel - NOAA SWPC Live Ingestion Module (Phase V2.2)
Fetches real-time Planetary K-index and Space Weather Alerts/Watches/Warnings from NOAA SWPC.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, List

# Standard User-Agent to avoid Cloudflare/WAF 403 blocks
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

NOAA_KP_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
NOAA_ALERTS_URL = "https://services.swpc.noaa.gov/products/alerts.json"
OUTPUT_FILE = "data/raw/noaa_swpc.json"


def kp_to_g_scale(kp: float) -> str:
    """Map planetary Kp index to official NOAA G-Scale."""
    if kp >= 9.0:
        return "G5"  # Extreme
    elif kp >= 8.0:
        return "G4"  # Severe
    elif kp >= 7.0:
        return "G3"  # Strong
    elif kp >= 6.0:
        return "G2"  # Moderate
    elif kp >= 5.0:
        return "G1"  # Minor
    else:
        return "G0"  # Nominal / Quiet


def fetch_json(url: str, timeout: int = 8) -> Any:
    """Fetch JSON from URL with custom headers and timeout."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        data = response.read().decode("utf-8-sig")
        return json.loads(data)


def get_fallback_data() -> Dict[str, Any]:
    """Provide realistic fallback NOAA data if endpoint is unreachable."""
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "provenance": {
            "source": "NOAA Space Weather Prediction Center (Fallback Mock)",
            "source_urls": [NOAA_KP_URL, NOAA_ALERTS_URL],
            "retrieved_at_utc": now_iso,
            "is_live": False
        },
        "current_conditions": {
            "observed_kp": 3.0,
            "g_scale": "G0",
            "condition": "QUIET",
            "station_count": 8,
            "latest_time_tag": now_iso
        },
        "recent_kp_peak_24h": {
            "max_kp": 4.0,
            "g_scale": "G0",
            "time_tag": now_iso
        },
        "active_alerts_count": 1,
        "active_alerts": [
            {
                "product_id": "K04W",
                "issue_datetime": now_iso,
                "message": "NOAA SWPC Geomagnetic K-index of 4 expected. Area of impact primarily poleward of 65 degrees."
            }
        ]
    }


def fetch_noaa_data() -> Dict[str, Any]:
    """Fetch and synthesize NOAA planetary K-index and active alerts."""
    now_iso = datetime.now(timezone.utc).isoformat()
    is_live = True
    kp_data = None
    alerts_data = None

    # Fetch K-index
    try:
        kp_data = fetch_json(NOAA_KP_URL)
    except Exception as e:
        print(f"[WARN] Failed to fetch NOAA Kp data ({e}).", file=sys.stderr)
        is_live = False

    # Fetch Alerts
    try:
        alerts_data = fetch_json(NOAA_ALERTS_URL)
    except Exception as e:
        print(f"[WARN] Failed to fetch NOAA alerts ({e}).", file=sys.stderr)
        is_live = False

    if not kp_data and not alerts_data:
        print("[INFO] Using realistic NOAA fallback data.", file=sys.stderr)
        return get_fallback_data()

    # Process Kp data
    current_kp = 0.0
    latest_time = now_iso
    station_count = 0
    max_kp_24h = 0.0
    max_kp_time = now_iso

    if kp_data and len(kp_data) > 0:
        # Check if list of dicts or list of lists
        if isinstance(kp_data[0], dict):
            # Sort by time_tag
            valid_pts = [pt for pt in kp_data if "Kp" in pt and pt["Kp"] is not None]
            if valid_pts:
                latest = valid_pts[-1]
                current_kp = float(latest.get("Kp", 0.0))
                latest_time = latest.get("time_tag", now_iso)
                station_count = latest.get("station_count", 0)

                # Look at last 8 readings (~24 hours at 3h cadence)
                last_24h = valid_pts[-8:]
                peak_pt = max(last_24h, key=lambda x: float(x.get("Kp", 0.0)))
                max_kp_24h = float(peak_pt.get("Kp", 0.0))
                max_kp_time = peak_pt.get("time_tag", now_iso)
        elif isinstance(kp_data[0], list):
            # Format: [header, row1, row2...]
            # Header often: ["time_tag", "Kp", "a_running", "station_count"]
            valid_pts = kp_data[1:]
            if valid_pts:
                latest = valid_pts[-1]
                try:
                    current_kp = float(latest[1])
                    latest_time = str(latest[0])
                    station_count = int(latest[3]) if len(latest) > 3 else 0
                except (ValueError, IndexError):
                    pass
                last_24h = valid_pts[-8:]
                try:
                    max_kp_24h = max(float(r[1]) for r in last_24h if r[1] is not None)
                except ValueError:
                    max_kp_24h = current_kp

    # Process Alerts
    cleaned_alerts = []
    if alerts_data and isinstance(alerts_data, list):
        for item in alerts_data[:10]:  # Top 10 most recent
            cleaned_alerts.append({
                "product_id": item.get("product_id", "UNKNOWN"),
                "issue_datetime": item.get("issue_datetime", ""),
                "message": item.get("message", "").strip()[:500]  # Truncate to relevant summary
            })

    result = {
        "provenance": {
            "source": "NOAA Space Weather Prediction Center (SWPC)",
            "source_urls": [NOAA_KP_URL, NOAA_ALERTS_URL],
            "retrieved_at_utc": now_iso,
            "is_live": is_live
        },
        "current_conditions": {
            "observed_kp": round(current_kp, 1),
            "g_scale": kp_to_g_scale(current_kp),
            "condition": "STORM" if current_kp >= 5.0 else ("UNSETTLED" if current_kp >= 4.0 else "QUIET"),
            "station_count": station_count,
            "latest_time_tag": latest_time
        },
        "recent_kp_peak_24h": {
            "max_kp": round(max_kp_24h, 1),
            "g_scale": kp_to_g_scale(max_kp_24h),
            "time_tag": max_kp_time
        },
        "active_alerts_count": len(cleaned_alerts),
        "active_alerts": cleaned_alerts
    }

    return result


def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    print("=== SolarSentinel NOAA SWPC Ingestion Layer ===")
    data = fetch_noaa_data()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    cur = data["current_conditions"]
    print(f"[SUCCESS] NOAA SWPC feed retrieved ({'LIVE' if data['provenance']['is_live'] else 'FALLBACK'}).")
    print(f"  Observed Kp Index : {cur['observed_kp']} ({cur['g_scale']} - {cur['condition']})")
    print(f"  24h Peak Kp Index : {data['recent_kp_peak_24h']['max_kp']} ({data['recent_kp_peak_24h']['g_scale']})")
    print(f"  Active Alerts     : {data['active_alerts_count']} warnings/watches in effect.")
    print(f"  Saved to          : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
