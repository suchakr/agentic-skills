# Agentic Skills

A personal collection of reusable skills for AI coding agents.

## Convention

Each skill lives in its own directory with a `SKILL.md` entry point that defines the skill's name, trigger description, persona, and response format. Skills may also include:

- `references/` — supporting knowledge files loaded on demand
- `scripts/` — helper scripts the skill can invoke
- `agents/` — agent-specific configuration (e.g. `openai.yaml` for Codex CLI)

## Skills

### sanskrit-tutor

Scholarly Sanskrit tutor focused on Paninian grammar (Ashtadhyayi), shloka analysis, and adaptive learner coaching. Supports composition correction, verse parsing (padachheda/anvaya), compound and morphology analysis, drill generation, and mixed tutoring sessions including technical Jyotisha contexts. Adopts the persona "कोविदः".

**Prerequisites:** None — pure prompt and reference material.

**Try:**
- `"Check my Sanskrit: मम गृहे एकः वृक्षः अस्ति"` — composition correction
- `"Parse: धर्मक्षेत्रे कुरुक्षेत्रे समवेता युयुत्सवः"` — verse analysis
- `"Run a mixed tutoring session at intermediate level"` — adaptive drilling

### stellarium

Remote control and scripting for a running Stellarium instance via the Remote Control HTTP plugin. Handles camera movement, overlay toggles, time/location changes, `.ssc` script authoring, and media playback probing. Uses a lightweight-first strategy: HTTP for live tweaks, direct script calls for sticky features, `.ssc` artifacts for reusable sequences.

**Prerequisites:** Python 3 (stdlib only, no pip packages). A running [Stellarium](https://stellarium.org/) instance with the Remote Control plugin enabled (default port 8090).

**Try:**
- `"Show the sky from Varanasi on winter solstice, 1000 CE"`
- `"Point at Jupiter and zoom to 20° FOV"`
- `"Write an .ssc script that tours the planets"`

## Installation

Each agent platform has its own skills directory. Installation is a symlink from that directory to the skill folder in this repo.

### OpenAI Codex CLI

```bash
ln -s /path/to/agentic-skills/<skill-name> ~/.codex/skills/<skill-name>
```

For example:

```bash
ln -s ~/projects/agentic-skills/sanskrit-tutor ~/.codex/skills/sanskrit-tutor
ln -s ~/projects/agentic-skills/stellarium ~/.codex/skills/stellarium
```

### Warp / Oz

Warp discovers skills from the same `~/.codex/skills/` directory, so the Codex CLI symlinks above also make skills available to Warp's Oz agent.

### Other agents

Any agent that resolves skills via a `SKILL.md` entry point can use these skills. Symlink or copy the skill directory into the agent's expected skills location.

If the agent supports agent-specific config, check the skill's `agents/` subdirectory for a matching config file.

## Development

Skills are edited in place in this repo. Because agents read through symlinks, changes are picked up immediately — useful for iterative testing.

Use feature branches for larger rework so `main` stays stable for day-to-day use. If you need full isolation between "live" and "dev" versions, consider a `git worktree` pointed at `main` for the symlink targets.
