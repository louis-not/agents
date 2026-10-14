# agents

Base prompts, skills and specialist roles for running Claude Code as a three-tier orchestration.

| Tier | Model | Prompt |
|---|---|---|
| Main orchestrator | Opus | `prompts/main-orchestrator.md` (imported by `prompts/CLAUDE.md`) |
| Head orchestrator | Sonnet | `prompts/head-orchestrator.md` |
| Executor | Haiku (Sonnet if needed) | `prompts/executor.md` + a role from `agents/` |

## Layout
- `prompts/`: `CLAUDE.md` (global base) and one base prompt per tier
- `skills/`: procedures each tier follows (`brief-intake`, `split-and-brief`, `backlog-delegation`, `code-standards-gate`, `e2e-verify`)
- `agents/`: specialist roles for executors; `index.md` says which one to pick

## Setup
Clone to `~/Repositories/nexus-workspace/agents`; the prompts use that path. Then link the global `CLAUDE.md` and the skills:

```bash
R=~/Repositories/nexus-workspace/agents
ln -sf $R/prompts/CLAUDE.md ~/.claude/CLAUDE.md
for s in $R/skills/*/; do ln -sfn "$s" ~/.claude/skills/$(basename "$s"); done
```

Agents are not installed as native subagent types. Heads and executors run as `general-purpose` with the role's `.md` pasted into the brief.

## How a task runs
1. The main session loads `CLAUDE.md` and settles every open question with you (`brief-intake`).
2. It splits the work and launches one Sonnet head per submodule (`split-and-brief`).
3. Each head delegates backlog items to Haiku or Sonnet executors (`backlog-delegation`), then reviews and tests each one (`code-standards-gate`).
4. The main session tests the whole feature end to end (`e2e-verify`) and reports back.

## Editing
Edit files here; the links make changes live. `agents/head-orchestrator.md` repeats `prompts/head-orchestrator.md` below its frontmatter, so update both together.

## Jules Delegation (Google Cloud async coding agent)
Modules that are self-contained and testable from a GitHub clone can be dispatched to Jules via `jules-delegation`:
- Uses Jules REST API (`agents/scripts/jules_api.py`) with `automationMode: AUTO_CREATE_PR`.
- Jules prompts live in `prompts/*.jules.md`.
- Head orchestrator / Main orchestrator (AGY) reviews each opened PR, runs `code-standards-gate`, and merges to the feature integration branch.

