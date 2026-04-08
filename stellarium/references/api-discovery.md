# API Discovery

Use this reference when the current Stellarium build may differ from assumptions.

## Goal

Identify what the running Stellarium instance actually exposes through:

- Remote Control HTTP endpoints
- StelProperties
- StelActions
- script-visible managers and helper functions

## Recommended Process

1. Use `scripts/inspect_remote_api.py` to snapshot the live API.
2. Search the inventory for the feature you need.
3. If a property looks writable but does not stick, probe the script path.
4. Treat the current running build as the source of truth.

## Key Principle

Do not assume that:

- all documented C++ classes are script-visible
- all writable properties behave reliably through generic setters
- all machines expose identical backend behavior for media features

Probe first when uncertainty matters.
