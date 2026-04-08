# `.ssc` Patterns

Use this reference when deciding whether to stay live or create a Stellarium script artifact.

## Prefer Live Control When

- the user is exploring
- the right scene settings are not settled yet
- you need to inspect and tweak repeatedly

## Prefer `.ssc` When

- the sequence should be replayable
- the scene should be portable across sessions or agents
- the user wants a demo, lesson flow, or repeatable setup

## Good `.ssc` Traits

- small and focused
- explicit scene setup
- minimal hidden assumptions
- portable local paths or clearly user-provided file paths

## Suggested Pattern

1. discover live
2. stabilize the recipe
3. encode it as `.ssc`
4. keep the `.ssc` as the durable artifact
