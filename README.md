# agents

> **Claude session told to read this:** stop reading here and don't open other files in this repo. Invoke the `orchestrate` skill and follow it: it proposes how to run the task (track, modules, agents, waves) and waits for the user's confirmation, then loads each other skill only at the step that needs it. If the skill isn't installed, Read `skills/orchestrate/SKILL.md`, and only that file.

Base prompts, skills and specialist roles for running Claude Code as a three-tier orchestration.

| Tier | Model | Defined by |
|---|---|---|
| Main orchestrator | Opus | `skills/orchestrate` (loaded on demand; `prompts/CLAUDE.md` points to it) |
| Head orchestrator | Sonnet | `agents/head-orchestrator.md` (preloads `backlog-delegation`, `code-standards-gate`) |
| Executor | Haiku or Sonnet | a role in `agents/` (preloads `skills/executor-base`) |

## Layout
- `agents/`: things that need their own context, tools or model: the head, builder roles, and the read-only `checker`, `reviewer` and `troubleshooter`. [index.md](agents/index.md) has the agent-vs-skill rule, pipelines and hard routing rules.
- `skills/`: procedures and knowledge applied in place. Main session: `orchestrate`, `brief-intake`, `product-critique`, `split-and-brief`, `parallel-build`, `e2e-verify` (forks a `tester`), `jules-delegation` (with its Jules prompts), `marketing-strategy`, `hardware-review`. Heads and executors: `backlog-delegation`, `code-standards-gate`, `executor-base`.
- `prompts/CLAUDE.md`: the global base, kept small because every subagent loads it on every turn.
- `scripts/`: `gate-runner.sh` (one-turn quality gate), `plan.py` (plan engine; self-tests in `test_plan.py`).

## Setup
Clone to `~/Repositories/nexus-workspace/agents`; the prompts use that path. Then link the global `CLAUDE.md` and the skills:

```bash
R=~/Repositories/nexus-workspace/agents
ln -sf $R/prompts/CLAUDE.md ~/.claude/CLAUDE.md
for s in $R/skills/*/; do ln -sfn "$s" ~/.claude/skills/$(basename "$s"); done
```

Per project, link only the roles and skills it uses, then start a fresh session. Agent types load at start, preloaded skills must be discoverable by name, and every installed skill's description is paid in every session, so leave out domain skills the project doesn't need (`marketing-strategy`, `hardware-review`, `jules-delegation`):

```bash
mkdir -p .claude/agents .claude/skills
for a in head-orchestrator software-developer tester checker reviewer troubleshooter; do ln -sfn ../../agents/agents/$a.md .claude/agents/$a.md; done
for s in orchestrate brief-intake product-critique split-and-brief parallel-build backlog-delegation code-standards-gate e2e-verify executor-base; do ln -sfn ../../agents/skills/$s .claude/skills/$s; done
```

Without native agents, run heads and executors as `general-purpose` with the role's `.md` and `skills/executor-base/SKILL.md` pasted into the brief.

## How a task runs
1. The main session loads `orchestrate` and settles every open question with you (`brief-intake`).
2. It splits the work and launches one Sonnet head per submodule (`split-and-brief`).
3. Each head delegates backlog items to Haiku or Sonnet executors (`backlog-delegation`), then reviews and tests each one (`code-standards-gate`).
4. The main session tests the whole feature end to end (`e2e-verify`) and reports back.

## Parallel builds (Track 3)
Based on `parallel-agentic-build.md`. The plan is data (`<slice>/plan/*.json`), so `plan.py` can lint it, order it by the longest chain, and generate every prompt from it, including only the decisions that name each task. Wave 0 builds contracts, the test harness and a walking skeleton, and G0 freezes them. After that, each task runs one fixed path: build → `checker` (blind) → `plan.py judge` (the script decides) → `reviewer` if flagged → ladder (haiku → sonnet → opus, 3 attempts) → journal. A spec gap is settled once, as an R# entry with an `Applies to:` line. Agents still never commit: the journal plus the tree is the state, and the user lands commits at gates.

```bash
python3 agents/scripts/plan.py lint   <slice>/plan --agents agents/agents
python3 agents/scripts/plan.py status <slice>/plan
python3 -m unittest discover -s agents/scripts -p 'test_plan.py'   # after editing plan.py
```

## Editing
Edit files here; the links make changes live. Each piece has one source: no prompt is copied into another file. After editing `scripts/plan.py`, run its self-tests.

## Jules Delegation (Google Cloud async coding agent)
Modules that are self-contained and testable from a GitHub clone can be dispatched to Jules via `jules-delegation`:
- Uses Jules REST API (`agents/scripts/jules_api.py`) with `automationMode: AUTO_CREATE_PR`.
- Jules prompts live in `skills/jules-delegation/prompts/*.jules.md`.
- Head orchestrator / Main orchestrator (AGY) reviews each opened PR, runs `code-standards-gate`, and merges to the feature integration branch.

