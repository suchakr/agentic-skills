---
name: stellarium
description: "Use for controlling a running Stellarium instance through Remote Control HTTP and Stellarium scripting: inspect and change scene settings, move the camera, manage overlays and labels, run direct or file-based `.ssc` scripts, and probe optional media playback support."
prerequisites:
  runtime: [python3]
  external: [Stellarium with Remote Control plugin enabled on port 8090]
  pip: []
---

# Stellarium

Use this skill when the user wants Codex to control or script Stellarium.

This skill is intentionally generic. It should work with any running Stellarium instance that has the Remote Control plugin enabled. Do not assume a repo layout, named local scripts, or presentation-specific assets unless the user provides them.

## When To Use

Use this skill for tasks such as:

- changing time, location, field of view, or viewing direction
- toggling overlays such as atmosphere, landscape, grids, stars, horizon, direction markers, zodiac, lunar stations, and constellation or asterism lines
- inspecting or mutating Stellarium properties and actions
- running direct Stellarium script snippets
- running local `.ssc` script files
- turning an exploratory live session into a reusable `.ssc` artifact
- probing whether local audio or video playback is supported in the current Stellarium build

## Control Strategy

Use the lightest control path that fits the task.

1. Prefer Remote Control HTTP for interactive tweaks.
   This is best for small live changes: toggles, labels, and state inspection.

2. Use direct Stellarium script calls when a feature is exposed in scripting but does not behave reliably through generic property writes.
   Some features may appear writable as properties but only stick when invoked through script methods.

3. Use `.ssc` when the sequence should become portable or repeatable.
   A stable Stellarium demo, lesson flow, or scene setup should usually end up as a script artifact.

## Camera Control

Camera direction and FOV do not stick reliably through HTTP property writes. Use direct script calls as the default path — do not wait for a failure before switching.

- **Direction:** `core.moveToAltAzi(alt, azi, duration)` where alt is degrees above horizon and azi is compass bearing (0=N, 90=E, 180=S, 270=W). Use `duration=0` for instant moves.
- **FOV:** `StelMovementMgr.zoomTo(fov, duration)` where fov is in degrees.

Example (look east, 20° above horizon, 60° FOV):

    core.moveToAltAzi(20, 90, 0); StelMovementMgr.zoomTo(60, 0);

### Horizon framing

When the user wants the horizon visible (sunrise, moonrise, landscape shots), the camera altitude must account for FOV. Half the vertical FOV extends below the aim point — if altitude is too low, the ground fills the screen.

Rule of thumb: set altitude ≈ FOV / 3 to place the horizon in the lower third of the frame.

- FOV 60° → altitude ~20°
- FOV 90° → altitude ~30°
- FOV 40° → altitude ~13°

## Time

`stelrc.py goto-time` accepts UTC, not local time. The agent must manually offset for the location's UTC shift (visible in `status` output as `gmtShift`).

For example, Varanasi is UTC+05:53. To set local 06:30, send UTC 00:37.

## Readiness Check

Before any control sequence, verify Stellarium is reachable:

    curl -s http://localhost:8090/api/main/status | python3 -m json.tool

If this fails, Remote Control is not running. Instruct the user to enable it in Stellarium → Configuration → Plugins → Remote Control → enable at startup.

## Core Helpers

This skill may use local helper scripts when available.

- `scripts/stell_view.py`
  Vedic sky visualization preset. Sets location, time, Indian sky culture, overlays, and view in one command.
  Usage: `python3 stell_view.py --date YYYY-MM-DD --time HH:MM --place <city> [--view chakra|east|north|south|west] [--fov 200]`
  Views: `chakra` = full rashi wheel (ecliptic pole centered, location/time invariant); cardinal horizon views use `core.moveToAltAzi` compass convention (0=N, 90=E).
  Known cities: Mysore, Chennai, Bangalore, Mumbai, Delhi, Kolkata, Hyderabad, Pune, Kochi, Varanasi, Ujjain, Tirupati, Madurai, Coimbatore. Also accepts `lat,lon`.

- `scripts/stelrc.py`
  Generic wrapper for Remote Control HTTP, property and action inspection, file-based script execution, and common alias commands.

- `scripts/inspect_remote_api.py`
  Snapshot and inspect the live API surface from the current Stellarium build.

These helpers are implementation details. The user should not need to think in terms of raw HTTP calls unless debugging.

### stelrc.py quick reference

State inspection:

    stelrc.py status
    stelrc.py view

Navigation:

    stelrc.py goto-time "1000-12-21T00:37:00" [--timerate 200]
    stelrc.py goto-direction E [--alt 20]
    stelrc.py location show
    stelrc.py location search "Varanasi"
    stelrc.py location goto --latitude 25.32 --longitude 83.01 [--altitude 80] [--name "Varanasi"]
    stelrc.py focus Jupiter [--mode center|zoom|mark]
    stelrc.py fov 60

Overlay toggles (on | off | toggle | show):

    stelrc.py atmosphere on
    stelrc.py constellation-lines toggle
    stelrc.py grid equatorial on

Sky culture:

    stelrc.py skyculture list
    stelrc.py skyculture set indian

Scripting:

    stelrc.py script-direct 'core.moveToAltAzi(20, 90, 0);'
    stelrc.py run-file path/to/script.ssc

Properties and actions:

    stelrc.py property list [query]
    stelrc.py property get "StelMovementMgr.autoMoveDuration"
    stelrc.py property set "StelMovementMgr.autoMoveDuration" 1.0
    stelrc.py action list [query]
    stelrc.py action run actionToggleNightMode

Labels:

    stelrc.py label-screen "Hello" --x 100 --y 100 [--size 24] [--color "#FFFFFF"]

### inspect_remote_api.py quick reference

    inspect_remote_api.py [--base-url URL] [--output PATH]

Saves a full inventory of properties, actions, and endpoints to JSON.

## Expected Workflow

For most tasks:

1. Inspect the current Stellarium state if needed.
2. Apply a minimal change.
3. Re-read state when a control is known to be unreliable.
4. If a property does not stick, try the script path.
5. If the sequence becomes useful, encode it as `.ssc`.

## Failure Handling

Use these fallbacks deliberately:

- If a property write does not stick, retry with direct script calls.
- If a named location lookup fails, use coordinates.
- If media support is uncertain, run a probe script first.
- If a feature is absent from both properties and actions, treat it as possibly unavailable from Remote Control and avoid bluffing.

## Media

Some Stellarium builds expose media functionality only partially through scripting.

- Test audio or video playback empirically on the running build.
- Prefer a probe script before building higher-level media workflows.
- Do not assume all documented engine classes are exposed identically in the script environment.

See:

- `references/media.md`

## `.ssc` Artifacts

Use `.ssc` as the preferred portable artifact for reusable Stellarium sequences.

- exploratory live control is good for discovery
- `.ssc` is better for sharing, replay, and repeatability

See:

- `references/ssc-patterns.md`

## API Discovery

When the supported surface is unclear for the current build:

1. inspect the live Remote Control API
2. identify writable properties and actions
3. test suspicious features with tiny probes

See:

- `references/api-discovery.md`

## Cross-skill Coordination

When the astronomical scene requires interpreting a Sanskrit source text, coordinate with the `sanskrit-tutor` skill for verse parsing, compound analysis, or Jyotisha vocabulary clarification before setting the Stellarium scene.

If `sanskrit-tutor` is not installed, transliterate key terms and note that a full grammatical analysis requires the sanskrit-tutor skill.

## Scope

This skill is about Stellarium control and scripting.

It should not assume:

- a specific presentation repository
- named local Stellarium demos
- archaeoastronomy-specific scenarios
- local media files unless the user points to them

Those can be layered on as optional examples, but they are not part of the core skill contract.
