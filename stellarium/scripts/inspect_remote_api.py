#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


DEFAULT_BASE_URL = "http://127.0.0.1:8090/api"
DEFAULT_OUTPUT = Path(__file__).resolve().parent.parent / "references" / "remote-api-inventory.json"


def fetch_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8"))


def maybe_fetch_json(base_url: str, path: str) -> tuple[bool, object]:
    url = f"{base_url.rstrip('/')}/{path.lstrip('/')}"
    try:
        return True, fetch_json(url)
    except Exception as exc:  # keep inventory generation resilient
        return False, {"error": str(exc), "path": path}


def summarize_properties(properties: dict[str, object]) -> dict[str, object]:
    writable: dict[str, object] = {}
    interesting: dict[str, object] = {}
    keywords = (
        "skyculture",
        "culture",
        "landscape",
        "atmosphere",
        "cardinal",
        "grid",
        "constellation",
        "asterism",
        "label",
        "lunar",
        "zodiac",
        "projection",
        "mount",
        "location",
        "script",
        "fog",
    )

    for prop_id, meta in properties.items():
        if not isinstance(meta, dict):
            continue
        if meta.get("isWritable"):
            writable[prop_id] = meta
        lower_id = prop_id.lower()
        if any(keyword in lower_id for keyword in keywords):
            interesting[prop_id] = meta

    return {
        "writable_count": len(writable),
        "interesting_count": len(interesting),
        "interesting": interesting,
    }


def summarize_actions(actions: dict[str, object]) -> dict[str, object]:
    flat: dict[str, object] = {}
    interesting: dict[str, object] = {}
    keywords = (
        "atmosphere",
        "landscape",
        "cardinal",
        "grid",
        "constellation",
        "asterism",
        "label",
        "lunar",
        "zodiac",
        "projection",
        "mount",
        "script",
        "fog",
    )

    for group_name, group_actions in actions.items():
        if not isinstance(group_actions, list):
            continue
        for meta in group_actions:
            if not isinstance(meta, dict) or "id" not in meta:
                continue
            action_id = str(meta["id"])
            flat[action_id] = {"group": group_name, **meta}
            lower_id = action_id.lower()
            if any(keyword in lower_id for keyword in keywords):
                interesting[action_id] = {"group": group_name, **meta}

    return {
        "total_count": len(flat),
        "interesting_count": len(interesting),
        "interesting": interesting,
    }


def build_inventory(base_url: str) -> dict[str, object]:
    endpoints = {
        "main_status": "main/status",
        "main_plugins": "main/plugins",
        "main_view": "main/view",
        "scripts_list": "scripts/list",
        "scripts_status": "scripts/status",
        "stelaction_list": "stelaction/list",
        "stelproperty_list": "stelproperty/list",
        "view_listskyculture": "view/listskyculture",
        "view_listlandscape": "view/listlandscape",
        "view_listprojection": "view/listprojection",
        "location_list": "location/list",
        "location_countrylist": "location/countrylist",
        "location_planetlist": "location/planetlist",
    }

    raw: dict[str, object] = {}
    availability: dict[str, object] = {}
    for label, path in endpoints.items():
        ok, payload = maybe_fetch_json(base_url, path)
        availability[label] = {"ok": ok, "path": path}
        raw[label] = payload

    properties = raw.get("stelproperty_list", {})
    actions = raw.get("stelaction_list", {})

    inventory = {
        "base_url": base_url,
        "availability": availability,
        "summary": {},
        "raw": raw,
    }

    if isinstance(properties, dict):
        inventory["summary"]["properties"] = summarize_properties(properties)
    if isinstance(actions, dict):
        inventory["summary"]["actions"] = summarize_actions(actions)

    return inventory


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a running Stellarium Remote Control API and save an inventory snapshot.",
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    try:
        inventory = build_inventory(args.base_url)
    except urllib.error.URLError as exc:
        print(
            "Could not reach Stellarium Remote Control API. "
            "Make sure Stellarium is running and the Remote Control plugin is enabled.",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8")

    summary = inventory.get("summary", {})
    print(f"Wrote inventory to {args.output}")
    if "properties" in summary:
        print(
            "Properties:"
            f" writable={summary['properties']['writable_count']}"
            f" interesting={summary['properties']['interesting_count']}"
        )
    if "actions" in summary:
        print(
            "Actions:"
            f" total={summary['actions']['total_count']}"
            f" interesting={summary['actions']['interesting_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
