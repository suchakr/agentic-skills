#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "http://127.0.0.1:8090/api"

PROPERTY_ALIASES = {
    "atmosphere": "LandscapeMgr.atmosphereDisplayed",
    "landscape": "LandscapeMgr.landscapeDisplayed",
    "horizon": "GridLinesMgr.horizonLineDisplayed",
    "direction": "LandscapeMgr.cardinalPointsDisplayed",
    "stars": "StarMgr.flagStarsDisplayed",
    "lunar": "ConstellationMgr.lunarSystemDisplayed",
    "zodiac": "ConstellationMgr.zodiacDisplayed",
    "constellation-lines": "ConstellationMgr.linesDisplayed",
    "asterism-lines": "AsterismMgr.linesDisplayed",
    "grid-equatorial": "GridLinesMgr.equatorGridDisplayed",
    "grid-ecliptic": "GridLinesMgr.eclipticLineDisplayed",
    "grid-azimuthal": "GridLinesMgr.azimuthalGridDisplayed",
}

GRID_KIND_TO_PROPERTY = {
    "equatorial": "GridLinesMgr.equatorGridDisplayed",
    "ecliptic": "GridLinesMgr.eclipticLineDisplayed",
    "azimuthal": "GridLinesMgr.azimuthalGridDisplayed",
}


def request_json(url: str, method: str = "GET", data: dict[str, str] | None = None) -> object:
    payload = None
    headers = {"Accept": "application/json"}
    if data is not None:
        payload = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, data=payload, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as response:
        raw = response.read()
        if not raw:
            return {"ok": True}
        text = raw.decode("utf-8")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def tokenize(text: str) -> set[str]:
    normalized = normalize_text(text)
    return set(normalized.split()) if normalized else set()


def parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "on", "yes"}:
        return True
    if normalized in {"0", "false", "off", "no"}:
        return False
    raise ValueError(f"Expected on/off style value, got '{value}'")


def stringify_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value
    return json.dumps(value, separators=(",", ":"))


def parse_altaz_vector(raw: object) -> tuple[float, float]:
    if isinstance(raw, str):
        vector = json.loads(raw)
    else:
        vector = raw
    if not isinstance(vector, list) or len(vector) != 3:
        raise ValueError("Unexpected altAz vector shape")
    x, y, z = (float(vector[0]), float(vector[1]), float(vector[2]))
    alt_rad = math.asin(max(-1.0, min(1.0, z)))
    az_prime_rad = math.atan2(y, x)
    alt_deg = math.degrees(alt_rad)
    az_prime_deg = math.degrees(az_prime_rad)
    az_deg = (180.0 - az_prime_deg) % 360.0
    return az_deg, alt_deg


def current_altitude_degrees(base_url: str) -> float:
    view = request_json(f"{base_url}/main/view")
    if not isinstance(view, dict) or "altAz" not in view:
        raise ValueError("Could not fetch current view direction")
    _, alt_deg = parse_altaz_vector(view["altAz"])
    return alt_deg


def fetch_properties(base_url: str) -> dict[str, object]:
    result = request_json(f"{base_url}/stelproperty/list")
    if not isinstance(result, dict):
        raise ValueError("Unexpected response for property list")
    return result


def fetch_actions(base_url: str) -> dict[str, dict[str, object]]:
    result = request_json(f"{base_url}/stelaction/list")
    if not isinstance(result, dict):
        raise ValueError("Unexpected response for action list")

    flattened: dict[str, dict[str, object]] = {}
    for group_name, group_actions in result.items():
        if not isinstance(group_actions, list):
            continue
        for action in group_actions:
            if not isinstance(action, dict) or "id" not in action:
                continue
            action_id = str(action["id"])
            flattened[action_id] = {"group": group_name, **action}
    return flattened


def fetch_skycultures(base_url: str) -> dict[str, str]:
    result = request_json(f"{base_url}/view/listskyculture")
    if not isinstance(result, dict):
        raise ValueError("Unexpected response for sky culture list")
    return {str(key): str(value) for key, value in result.items()}


def current_skyculture_id(base_url: str) -> str:
    properties = fetch_properties(base_url)
    current = properties.get("StelSkyCultureMgr.currentSkyCultureID")
    if not isinstance(current, dict) or "value" not in current:
        raise ValueError("Could not determine current sky culture id")
    return str(current["value"])


def resolve_named_query(
    query: str,
    items: dict[str, str],
    kind: str,
) -> tuple[str, str]:
    if query in items:
        return query, items[query]

    normalized_query = normalize_text(query)

    exact_name_matches = [
        (item_id, item_name)
        for item_id, item_name in items.items()
        if normalize_text(item_name) == normalized_query
    ]
    if len(exact_name_matches) == 1:
        return exact_name_matches[0]

    query_tokens = tokenize(query)
    token_matches: list[tuple[str, str]] = []
    if query_tokens:
        for item_id, item_name in items.items():
            haystack_tokens = tokenize(item_id) | tokenize(item_name)
            if all(any(token in hay for hay in haystack_tokens) for token in query_tokens):
                token_matches.append((item_id, item_name))

    if len(token_matches) == 1:
        return token_matches[0]
    if len(token_matches) > 1:
        rendered = ", ".join(f"{item_id} ({item_name})" for item_id, item_name in token_matches[:8])
        raise ValueError(f"{kind} query '{query}' is ambiguous. Matches: {rendered}")

    substring_matches = [
        (item_id, item_name)
        for item_id, item_name in items.items()
        if normalized_query
        and (
            normalized_query in normalize_text(item_id)
            or normalized_query in normalize_text(item_name)
        )
    ]
    if len(substring_matches) == 1:
        return substring_matches[0]
    if len(substring_matches) > 1:
        rendered = ", ".join(f"{item_id} ({item_name})" for item_id, item_name in substring_matches[:8])
        raise ValueError(f"{kind} query '{query}' is ambiguous. Matches: {rendered}")

    raise ValueError(f"Unknown {kind} '{query}'")


def resolve_property(query: str, properties: dict[str, object]) -> str:
    alias = PROPERTY_ALIASES.get(query.strip().lower())
    if alias:
        return alias
    choices = {prop_id: prop_id for prop_id in properties}
    resolved_id, _ = resolve_named_query(query, choices, "property")
    return resolved_id


def resolve_action(query: str, actions: dict[str, dict[str, object]]) -> str:
    if query in actions:
        return query

    item_map = {
        action_id: f"{meta.get('text', '')} {meta.get('group', '')}".strip()
        for action_id, meta in actions.items()
    }
    resolved_id, _ = resolve_named_query(query, item_map, "action")
    return resolved_id


def property_get(base_url: str, query: str) -> dict[str, object]:
    properties = fetch_properties(base_url)
    prop_id = resolve_property(query, properties)
    meta = properties.get(prop_id)
    if not isinstance(meta, dict):
        raise ValueError(f"Could not fetch property '{prop_id}'")
    return {"id": prop_id, **meta}


def property_set(base_url: str, query: str, value: object) -> dict[str, object]:
    properties = fetch_properties(base_url)
    prop_id = resolve_property(query, properties)
    request_json(
        f"{base_url}/stelproperty/set",
        method="POST",
        data={"id": prop_id, "value": stringify_value(value)},
    )
    meta = property_get(base_url, prop_id)
    return {"ok": True, **meta}


def action_run(base_url: str, query: str) -> dict[str, object]:
    actions = fetch_actions(base_url)
    action_id = resolve_action(query, actions)
    result = request_json(f"{base_url}/stelaction/do", method="POST", data={"id": action_id})
    return {"id": action_id, "result": result}


def set_bool_property(base_url: str, prop_id: str, state: bool) -> dict[str, object]:
    return property_set(base_url, prop_id, state)


def toggle_bool_property(base_url: str, prop_id: str) -> dict[str, object]:
    meta = property_get(base_url, prop_id)
    current = meta.get("value")
    if not isinstance(current, bool):
        raise ValueError(f"Property '{prop_id}' is not a boolean property")
    return property_set(base_url, prop_id, not current)


def jd_from_calendar_string(raw: str) -> float:
    text = raw.strip()
    if re.fullmatch(r"[-+]?\d+(\.\d+)?", text):
        return float(text)

    match = re.fullmatch(
        r"(?P<year>[-+]?\d{1,6})-(?P<month>\d{2})-(?P<day>\d{2})"
        r"(?:[T ](?P<hour>\d{2}):(?P<minute>\d{2})(?::(?P<second>\d{2}(?:\.\d+)?))?)?",
        text,
    )
    if not match:
        raise ValueError(
            "Time must be a Julian day number or an astronomical-year date like "
            "'-2799-01-01T00:00:00'"
        )

    year = int(match.group("year"))
    month = int(match.group("month"))
    day = int(match.group("day"))
    hour = int(match.group("hour") or "0")
    minute = int(match.group("minute") or "0")
    second = float(match.group("second") or "0")

    if month <= 2:
        year -= 1
        month += 12

    a = math.floor(year / 100)
    b = 2 - a + math.floor(a / 4)
    frac_day = (hour + minute / 60 + second / 3600) / 24
    jd = (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        + day
        + frac_day
        + b
        - 1524.5
    )
    return jd


def location_search(base_url: str, term: str) -> list[str]:
    query = urllib.parse.urlencode({"term": term})
    result = request_json(f"{base_url}/locationsearch/search?{query}")
    if not isinstance(result, list):
        raise ValueError("Unexpected response for location search")
    return [str(item) for item in result]


def location_goto_named(base_url: str, query: str) -> dict[str, object]:
    matches = location_search(base_url, query)
    if matches:
        item_map = {match: match for match in matches}
        resolved_id, _ = resolve_named_query(query, item_map, "location")
    else:
        resolved_id = query

    request_json(
        f"{base_url}/location/setlocationfields",
        method="POST",
        data={"id": resolved_id},
    )
    return {"ok": True, "id": resolved_id, "search_matches": matches}


def location_goto_coordinates(
    base_url: str,
    latitude: float,
    longitude: float,
    altitude: float | None,
    name: str | None,
    country: str | None,
    planet: str | None,
) -> dict[str, object]:
    data = {
        "latitude": stringify_value(latitude),
        "longitude": stringify_value(longitude),
    }
    if altitude is not None:
        data["altitude"] = stringify_value(altitude)
    if name:
        data["name"] = name
    if country:
        data["country"] = country
    if planet:
        data["planet"] = planet

    request_json(f"{base_url}/location/setlocationfields", method="POST", data=data)
    return {"ok": True, **data}


def escape_script_string(text: str) -> str:
    return json.dumps(text)


def direct_script(base_url: str, code: str) -> dict[str, object]:
    return request_json(f"{base_url}/scripts/direct", method="POST", data={"code": code})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stelrc.py",
        description="Helper for the Stellarium Remote Control HTTP API with generic and human-friendly commands.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Remote Control API base URL")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status", help="Fetch /main/status")
    subparsers.add_parser("view", help="Fetch /main/view")

    focus = subparsers.add_parser("focus", help="Focus an object by name")
    focus.add_argument("target")
    focus.add_argument("--mode", choices=["center", "zoom", "mark"], default="center")

    fov = subparsers.add_parser("fov", help="Set field of view in degrees")
    fov.add_argument("degrees")

    find = subparsers.add_parser("find", help="Search for an object name")
    find.add_argument("text")

    run_script = subparsers.add_parser("run-script", help="Run a named Stellarium script")
    run_script.add_argument("id")

    run_file = subparsers.add_parser("run-file", help="Run a local script file by sending its contents to /scripts/direct")
    run_file.add_argument("path")

    script_direct = subparsers.add_parser("script-direct", help="Run direct script source")
    script_direct.add_argument("code")

    skyculture = subparsers.add_parser("skyculture", help="List, show, or set the current sky culture")
    skyculture_subparsers = skyculture.add_subparsers(dest="skyculture_command", required=True)
    skyculture_subparsers.add_parser("list")
    skyculture_subparsers.add_parser("show")
    skyculture_set = skyculture_subparsers.add_parser("set")
    skyculture_set.add_argument("id")

    prop = subparsers.add_parser("property", help="Generic StelProperty access")
    prop_subparsers = prop.add_subparsers(dest="property_command", required=True)
    prop_list = prop_subparsers.add_parser("list")
    prop_list.add_argument("query", nargs="?")
    prop_get = prop_subparsers.add_parser("get")
    prop_get.add_argument("query")
    prop_set = prop_subparsers.add_parser("set")
    prop_set.add_argument("query")
    prop_set.add_argument("value")

    action = subparsers.add_parser("action", help="Generic StelAction access")
    action_subparsers = action.add_subparsers(dest="action_command", required=True)
    action_list = action_subparsers.add_parser("list")
    action_list.add_argument("query", nargs="?")
    action_run_parser = action_subparsers.add_parser("run")
    action_run_parser.add_argument("query")

    for name in [
        "atmosphere",
        "landscape",
        "horizon",
        "direction",
        "stars",
        "lunar",
        "zodiac",
        "constellation-lines",
        "asterism-lines",
    ]:
        feature = subparsers.add_parser(name, help=f"Show, hide, or inspect {name}")
        feature.add_argument("state", nargs="?", choices=["on", "off", "toggle", "show"])

    grid = subparsers.add_parser("grid", help="Control common grid overlays")
    grid.add_argument("kind", choices=sorted(GRID_KIND_TO_PROPERTY))
    grid.add_argument("state", choices=["on", "off", "toggle", "show"])

    location = subparsers.add_parser("location", help="Search, show, or go to a location")
    location_subparsers = location.add_subparsers(dest="location_command", required=True)
    location_subparsers.add_parser("show")
    location_search_parser = location_subparsers.add_parser("search")
    location_search_parser.add_argument("term")
    location_goto = location_subparsers.add_parser("goto")
    location_goto.add_argument("query", nargs="?")
    location_goto.add_argument("--latitude", type=float)
    location_goto.add_argument("--longitude", type=float)
    location_goto.add_argument("--altitude", type=float)
    location_goto.add_argument("--name")
    location_goto.add_argument("--country")
    location_goto.add_argument("--planet")

    goto_time = subparsers.add_parser("goto-time", help="Set time by Julian day or astronomical-year calendar string")
    goto_time.add_argument("time_value")
    goto_time.add_argument("--timerate", type=float, default=0.0)

    goto_direction = subparsers.add_parser("goto-direction", help="Point the view toward a cardinal direction")
    goto_direction.add_argument("direction", choices=["N", "E", "S", "W", "n", "e", "s", "w"])
    goto_direction.add_argument("--alt", type=float, help="Altitude in degrees; defaults to the current altitude")

    wait_parser = subparsers.add_parser("wait", help="Pause locally for a number of seconds")
    wait_parser.add_argument("seconds", type=float)

    label = subparsers.add_parser("label-screen", help="Place a screen label using a tiny direct script")
    label.add_argument("text")
    label.add_argument("--x", type=int, required=True)
    label.add_argument("--y", type=int, required=True)
    label.add_argument("--size", type=int, default=24)
    label.add_argument("--color", default="#FFFFFF")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    base_url = args.base_url.rstrip("/")

    try:
        if args.command == "status":
            result = request_json(f"{base_url}/main/status")
        elif args.command == "view":
            result = request_json(f"{base_url}/main/view")
        elif args.command == "focus":
            result = request_json(
                f"{base_url}/main/focus",
                method="POST",
                data={"target": args.target, "mode": args.mode},
            )
        elif args.command == "fov":
            result = request_json(f"{base_url}/main/fov", method="POST", data={"fov": args.degrees})
        elif args.command == "find":
            query = urllib.parse.urlencode({"str": args.text})
            result = request_json(f"{base_url}/objects/find?{query}")
        elif args.command == "run-script":
            result = request_json(f"{base_url}/scripts/run", method="POST", data={"id": args.id})
        elif args.command == "run-file":
            script_path = Path(args.path).expanduser()
            if not script_path.is_absolute():
                script_path = (Path.cwd() / script_path).resolve()
            code = script_path.read_text(encoding="utf-8")
            result = direct_script(base_url, code)
        elif args.command == "script-direct":
            result = direct_script(base_url, args.code)
        elif args.command == "skyculture":
            cultures = fetch_skycultures(base_url)
            if args.skyculture_command == "list":
                current_id = current_skyculture_id(base_url)
                result = {"current": {"id": current_id, "name": cultures.get(current_id, current_id)}, "available": cultures}
            elif args.skyculture_command == "show":
                current_id = current_skyculture_id(base_url)
                result = {"id": current_id, "name": cultures.get(current_id, current_id)}
            elif args.skyculture_command == "set":
                resolved_id, resolved_name = resolve_named_query(args.id, cultures, "sky culture")
                result = property_set(base_url, "StelSkyCultureMgr.currentSkyCultureID", resolved_id)
                result.update({"matched": args.id, "name": resolved_name})
            else:
                raise ValueError(f"Unsupported skyculture command: {args.skyculture_command}")
        elif args.command == "property":
            if args.property_command == "list":
                properties = fetch_properties(base_url)
                if args.query:
                    needle = normalize_text(args.query)
                    filtered = {
                        prop_id: meta
                        for prop_id, meta in properties.items()
                        if needle in normalize_text(prop_id)
                    }
                    result = filtered
                else:
                    result = properties
            elif args.property_command == "get":
                result = property_get(base_url, args.query)
            elif args.property_command == "set":
                result = property_set(base_url, args.query, args.value)
            else:
                raise ValueError(f"Unsupported property command: {args.property_command}")
        elif args.command == "action":
            if args.action_command == "list":
                actions = fetch_actions(base_url)
                if args.query:
                    needle = normalize_text(args.query)
                    result = {
                        action_id: meta
                        for action_id, meta in actions.items()
                        if needle in normalize_text(action_id)
                        or needle in normalize_text(str(meta.get("text", "")))
                        or needle in normalize_text(str(meta.get("group", "")))
                    }
                else:
                    result = actions
            elif args.action_command == "run":
                result = action_run(base_url, args.query)
            else:
                raise ValueError(f"Unsupported action command: {args.action_command}")
        elif args.command in {
            "atmosphere",
            "landscape",
            "horizon",
            "direction",
            "stars",
            "lunar",
            "zodiac",
            "constellation-lines",
            "asterism-lines",
        }:
            prop_id = PROPERTY_ALIASES[args.command]
            if args.state in (None, "show"):
                result = property_get(base_url, prop_id)
            elif args.state == "toggle":
                result = toggle_bool_property(base_url, prop_id)
            else:
                result = set_bool_property(base_url, prop_id, parse_bool(args.state))
        elif args.command == "grid":
            prop_id = GRID_KIND_TO_PROPERTY[args.kind]
            if args.state == "show":
                result = property_get(base_url, prop_id)
            elif args.state == "toggle":
                result = toggle_bool_property(base_url, prop_id)
            else:
                result = set_bool_property(base_url, prop_id, parse_bool(args.state))
        elif args.command == "location":
            if args.location_command == "show":
                status = request_json(f"{base_url}/main/status")
                if not isinstance(status, dict) or "location" not in status:
                    raise ValueError("Could not fetch current location")
                result = status["location"]
            elif args.location_command == "search":
                result = location_search(base_url, args.term)
            elif args.location_command == "goto":
                if args.query:
                    result = location_goto_named(base_url, args.query)
                elif args.latitude is not None and args.longitude is not None:
                    result = location_goto_coordinates(
                        base_url,
                        latitude=args.latitude,
                        longitude=args.longitude,
                        altitude=args.altitude,
                        name=args.name,
                        country=args.country,
                        planet=args.planet,
                    )
                else:
                    raise ValueError("Provide either a location query or both --latitude and --longitude")
            else:
                raise ValueError(f"Unsupported location command: {args.location_command}")
        elif args.command == "goto-time":
            jd = jd_from_calendar_string(args.time_value)
            result = request_json(
                f"{base_url}/main/time",
                method="POST",
                data={"time": stringify_value(jd), "timerate": stringify_value(args.timerate)},
            )
            if isinstance(result, dict):
                result["jday"] = jd
            else:
                result = {"result": result, "jday": jd}
        elif args.command == "goto-direction":
            azimuth_map = {"N": 0.0, "E": 90.0, "S": 180.0, "W": 270.0}
            direction = args.direction.upper()
            altitude = args.alt if args.alt is not None else current_altitude_degrees(base_url)
            result = request_json(
                f"{base_url}/main/view",
                method="POST",
                data={"az": stringify_value(azimuth_map[direction]), "alt": stringify_value(altitude)},
            )
            if isinstance(result, dict):
                result.update({"az": azimuth_map[direction], "alt": altitude, "direction": direction})
            else:
                result = {"result": result, "az": azimuth_map[direction], "alt": altitude, "direction": direction}
        elif args.command == "wait":
            time.sleep(args.seconds)
            result = {"ok": True, "waited_seconds": args.seconds}
        elif args.command == "label-screen":
            code = (
                f"var __codex_label = LabelMgr.labelScreen("
                f"{escape_script_string(args.text)}, {args.x}, {args.y}, false, {args.size}, {escape_script_string(args.color)});"
                "LabelMgr.setLabelShow(__codex_label, true);"
            )
            result = direct_script(base_url, code)
        else:
            raise ValueError(f"Unsupported command: {args.command}")
    except urllib.error.URLError as exc:
        print(
            "Could not reach Stellarium Remote Control API. "
            "Make sure Stellarium is running and the Remote Control plugin is enabled.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
