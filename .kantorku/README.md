# KantorKu Agent Workspace

This is the portable agent workspace for **KantorKu** — the AI worker orchestration framework.

## Quick Start

```bash
# 1. Bootstrap the workspace
bash .kantorku/tools/bootstrap.sh

# 2. Check system health
bash .kantorku/tools/guard.sh doctor

# 3. Start working with skills
bash .kantorku/tools/skill-navigator.sh list
```

## Directory Layout

| Path | Purpose |
|------|---------|
| `AGENTS.md` | Operating rules for the KantorKu agent |
| `config.toml` | Default workspace configuration |
| `chat.md` | Session start prompt template |
| `memory/MEMORY.md` | Project memory — persists across sessions |
| `skills/` | Skill definitions with agent configs |
| `tools/` | Bootstrap, guard, benchmark, intake scripts |
| `home-sync/` | Config baseline and approval rules |
| `reports/` | Evolve state, audit scores, benchmarks |

## Skills

| Skill | Purpose | Keywords |
|-------|---------|----------|
| library | Knowledge management & search | search, ask, ingest, browse, shelf, book, knowledge |
| office | Orchestration & planning | plan, execute, verify, brief, contract, delegate, manage |
| debug | Troubleshooting & diagnosis | fix, debug, error, trace, diagnose, reproduce |
| evolve | Improvement & optimization | evolve, optimize, tune, upgrade, improve, benchmark |
| deploy | Deployment & configuration | deploy, docker, config, setup, install, bootstrap |

## Workflows

- **Idea to PR**: `intake → plan → implement → review → pr-summary`
- **Plan-Implement-Verify**: `plan → implement → verify`

## Tools

| Tool | Purpose |
|------|---------|
| `bootstrap.sh` / `bootstrap.ps1` | Initialize workspace (Linux/Windows) |
| `doctor.sh` | Health check for workspace integrity |
| `guard.sh` | Config drift protection & auto-repair |
| `skill-navigator.sh` | Skill discovery & routing |
| `benchmark.sh` | Portfolio metrics & scenario benchmarks |
| `intake.sh` | Repository intake pipeline |
| `evolve-auto.sh` | Automated evolve cycle runner |

## Configuration

Copy `config.toml` to `kantorku.toml` and customize:

```bash
cp .kantorku/config.toml framework/kantorku.toml
# Edit with your API keys
kantorku setup
```
