# Agentic Skills

A collection of reusable [agent skills](https://agentskills.io/) for AI coding agents.

Skills follow the open `SKILL.md` standard and work with any compatible agent platform.

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

Clone this repo, then symlink each skill into your agent's skills directory.

```bash
git clone https://github.com/suchakr/agentic-skills.git
```

### Per-platform paths

**OpenAI Codex CLI** — `~/.codex/skills/`

```bash
ln -s /path/to/agentic-skills/sanskrit-tutor ~/.codex/skills/sanskrit-tutor
ln -s /path/to/agentic-skills/stellarium ~/.codex/skills/stellarium
```

**Warp / Oz** — discovers from `~/.codex/skills/` (same symlinks as Codex CLI).

**GitHub Copilot CLI** — `~/.copilot/skills/` or `~/.agents/skills/`

```bash
mkdir -p ~/.copilot/skills
ln -s /path/to/agentic-skills/sanskrit-tutor ~/.copilot/skills/sanskrit-tutor
ln -s /path/to/agentic-skills/stellarium ~/.copilot/skills/stellarium
```

**Google Antigravity** — `~/.gemini/antigravity/skills/`

```bash
mkdir -p ~/.gemini/antigravity/skills
ln -s /path/to/agentic-skills/sanskrit-tutor ~/.gemini/antigravity/skills/sanskrit-tutor
ln -s /path/to/agentic-skills/stellarium ~/.gemini/antigravity/skills/stellarium
```

### Other agents

Any agent that supports the `SKILL.md` open standard can use these skills. Symlink or copy the skill directory into the agent's expected skills location.

If the agent supports agent-specific config, check the skill's `agents/` subdirectory for a matching file (e.g. `agents/openai.yaml` for Codex CLI).

## Development

Skills are edited in place in this repo. Because agents read through symlinks, changes are picked up immediately — useful for iterative testing.

Use feature branches for larger rework so `main` stays stable for day-to-day use. If you need full isolation between "live" and "dev" versions, consider a `git worktree` pointed at `main` for the symlink targets.
