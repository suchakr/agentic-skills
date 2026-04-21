#!/usr/bin/env python3
"""
stell_view.py - Vedic sky visualization preset for Stellarium

Usage:
    python3 stell_view.py --date 1998-05-14 --time 15:55 --place Mysore
    python3 stell_view.py --date 1998-05-14 --time "3:55pm" --place Chennai --view east
    python3 stell_view.py --date 1995-06-17 --time 20:32 --place Chennai --view chakra --fov 200

Views:
    chakra  - ecliptic pole centered, full rashi wheel (default, location/time invariant)
    east    - east horizon centered (lagna observation)
    north   - north horizon centered
    south   - south horizon centered
    west    - west horizon centered
"""

from __future__ import annotations
import argparse
import math
import sys
import urllib.parse
import urllib.request
import json

DEFAULT_PORT = 8090
IST_OFFSET_H = 5.5

LOCATIONS: dict[str, dict] = {
    "mysore":     {"lat": 12.2958, "lon": 76.6394, "alt": 770,  "name": "Mysore"},
    "chennai":    {"lat": 13.0827, "lon": 80.2707, "alt": 6,    "name": "Chennai"},
    "bangalore":  {"lat": 12.9716, "lon": 77.5946, "alt": 920,  "name": "Bangalore"},
    "bengaluru":  {"lat": 12.9716, "lon": 77.5946, "alt": 920,  "name": "Bengaluru"},
    "mumbai":     {"lat": 19.0760, "lon": 72.8777, "alt": 14,   "name": "Mumbai"},
    "delhi":      {"lat": 28.6139, "lon": 77.2090, "alt": 216,  "name": "Delhi"},
    "kolkata":    {"lat": 22.5726, "lon": 88.3639, "alt": 9,    "name": "Kolkata"},
    "hyderabad":  {"lat": 17.3850, "lon": 78.4867, "alt": 542,  "name": "Hyderabad"},
    "pune":       {"lat": 18.5204, "lon": 73.8567, "alt": 560,  "name": "Pune"},
    "kochi":      {"lat":  9.9312, "lon": 76.2673, "alt": 1,    "name": "Kochi"},
    "varanasi":   {"lat": 25.3176, "lon": 82.9739, "alt": 80,   "name": "Varanasi"},
    "ujjain":     {"lat": 23.1765, "lon": 75.7885, "alt": 491,  "name": "Ujjain"},
    "tirupati":   {"lat": 13.6288, "lon": 79.4192, "alt": 152,  "name": "Tirupati"},
    "madurai":    {"lat":  9.9252, "lon": 78.1198, "alt": 101,  "name": "Madurai"},
    "coimbatore": {"lat": 11.0168, "lon": 76.9558, "alt": 411,  "name": "Coimbatore"},
}

# Cardinal directions: (az_compass_deg, alt_deg)
# core.moveToAltAzi uses compass bearing: 0=N, 90=E, 180=S, 270=W
HORIZON_DIRS: dict[str, tuple[float, float]] = {
    "north": (0.0,   0.0),
    "east":  (90.0,  0.0),
    "south": (180.0, 0.0),
    "west":  (270.0, 0.0),
}

# Ecliptic north pole in J2000: RA=18h=270°, Dec=66.56°
ECLIPTIC_POLE_RA_DEG  = 270.0
ECLIPTIC_POLE_DEC_DEG = 66.5607


def api_post(path: str, data: dict, port: int = DEFAULT_PORT) -> str:
    url = f"http://localhost:{port}{path}"
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        return r.read().decode()


def script_run(snippet: str, port: int = DEFAULT_PORT) -> str:
    return api_post("/api/scripts/direct", {"code": snippet}, port)


def parse_time_ist(time_str: str) -> float:
    """Parse HH:MM or H:MMam/pm → decimal hours IST"""
    t = time_str.strip().lower()
    is_12h = "am" in t or "pm" in t
    is_pm = "pm" in t
    t = t.replace("am", "").replace("pm", "").strip()
    h, mn = map(int, t.split(":"))
    if is_12h:
        if is_pm and h != 12:
            h += 12
        elif not is_pm and h == 12:
            h = 0
    return h + mn / 60.0


def to_jd(year: int, month: int, day: int, h_ist: float) -> float:
    """Date + IST hours → Julian Day Number"""
    h_utc = h_ist - IST_OFFSET_H
    return (367 * year
            - int(7 * (year + int((month + 9) / 12)) / 4)
            + int(275 * month / 9)
            + day + 1721013.5
            + h_utc / 24.0)


def resolve_location(place: str) -> tuple[float, float, int, str]:
    """Returns (lat, lon, alt, name). Accepts city name or 'lat,lon'."""
    key = place.strip().lower()
    if key in LOCATIONS:
        loc = LOCATIONS[key]
        return loc["lat"], loc["lon"], loc["alt"], loc["name"]
    if "," in place:
        lat, lon = map(float, place.split(",", 1))
        return lat, lon, 0, place
    known = ", ".join(sorted(LOCATIONS))
    print(f"Unknown place '{place}'. Known cities: {known}", file=sys.stderr)
    sys.exit(1)


def apply_vedic_preset(port: int = DEFAULT_PORT) -> None:
    """Apply full Indian sky culture visual preset via property API."""
    props = [
        ("StelSkyCultureMgr.currentSkyCultureID",   "indian"),
        ("StelSkyCultureMgr.screenLabelStyle",       "Native"),
        ("StelSkyCultureMgr.zodiacLabelStyle",       "Native"),
        ("StelSkyCultureMgr.infoLabelStyle",         "Native"),
        ("StelSkyCultureMgr.lunarSystemLabelStyle",  "Native"),
        ("GridLinesMgr.eclipticLineDisplayed",       "true"),
        ("GridLinesMgr.horizonLineDisplayed",        "true"),
        ("ConstellationMgr.zodiacDisplayed",         "true"),
        ("ConstellationMgr.boundariesDisplayed",     "true"),
        ("ConstellationMgr.namesDisplayed",          "true"),
        ("ConstellationMgr.lunarSystemDisplayed",    "true"),
        ("LandscapeMgr.currentLandscapeID",          "zero"),
        ("LandscapeMgr.atmosphereDisplayed",         "false"),
        ("SolarSystem.flagSunScale",                 "true"),
        ("SolarSystem.flagMoonScale",                "true"),
        ("SolarSystem.sunScale",                     "20"),
        ("SolarSystem.moonScale",                    "20"),
    ]
    for prop_id, value in props:
        api_post("/api/stelproperty/set", {"id": prop_id, "value": value}, port)


def set_view(mode: str, fov: float, port: int = DEFAULT_PORT) -> None:
    """Point camera via Stellarium script (reliable, compass-correct)."""
    if mode == "chakra":
        # Ecliptic north pole — full rashi wheel, location/time invariant
        script = (
            f"core.moveToRaDec({ECLIPTIC_POLE_RA_DEG}, {ECLIPTIC_POLE_DEC_DEG}, 0); "
            f"StelMovementMgr.zoomTo({fov}, 0);"
        )
    else:
        az, alt = HORIZON_DIRS[mode]
        script = (
            f"core.moveToAltAzi({alt}, {az}, 0); "
            f"StelMovementMgr.zoomTo({fov}, 0);"
        )
    result = script_run(script, port)
    if "error" in result.lower():
        # Fallback to REST API for direction, script for FOV
        print(f"  Script fallback: {result}", file=sys.stderr)
        if mode == "chakra":
            api_post("/api/main/view",
                     {"j2000": f"[0,-0.3979,0.9175]"}, port)
        api_post("/api/main/fov", {"fov": str(fov)}, port)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Set Stellarium to a Vedic sky visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--date",  required=True,
                        help="Date in YYYY-MM-DD format")
    parser.add_argument("--time",  required=True,
                        help="Time in IST: HH:MM or H:MMam/pm")
    parser.add_argument("--place", required=True,
                        help="City name or 'lat,lon'")
    parser.add_argument("--view",  default="chakra",
                        choices=["chakra", "east", "north", "south", "west"],
                        help="View mode (default: chakra)")
    parser.add_argument("--fov",   type=float, default=200.0,
                        help="Field of view in degrees (default: 200)")
    parser.add_argument("--port",  type=int, default=DEFAULT_PORT,
                        help=f"Stellarium Remote Control port (default: {DEFAULT_PORT})")
    args = parser.parse_args()

    lat, lon, alt, name = resolve_location(args.place)

    y, m, d = map(int, args.date.split("-"))
    h_ist = parse_time_ist(args.time)
    jd = to_jd(y, m, d, h_ist)

    print(f"Location : {name}  ({lat:.4f}°N, {lon:.4f}°E, {alt}m)")
    print(f"Date/Time: {args.date}  {args.time} IST  → JD {jd:.6f}")
    print(f"View     : {args.view}  FOV={args.fov}°")
    print("Applying...")

    api_post("/api/location/setlocationfields", {
        "latitude": lat, "longitude": lon,
        "altitude": alt, "name": name, "country": "India",
    }, args.port)

    api_post("/api/main/time", {"time": jd, "timerate": 0}, args.port)

    apply_vedic_preset(args.port)
    set_view(args.view, args.fov, args.port)

    print("Done.")


if __name__ == "__main__":
    main()
