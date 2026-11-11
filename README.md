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

## Agent or skill?
`parallel-build` is a **skill, not an agent**: there is no `parallel-build` role in `agents/` and no plan should name one. It is a procedure the main session (writing the plan) or a head (running tasks) follows. The agents that do the work are the roles in each task's `agent` field (`software-developer`, `tester`, `database-administrator`, ...) plus `checker` and `reviewer`. If a usage report lists "parallel-build", that is the driver's orchestration turns, not a separate agent. Rule of thumb in [index.md](agents/index.md): needs its own context, tools or model → agent; a procedure applied in place → skill.

## How a task runs
The main session loads `orchestrate`, which proposes a track and waits for your confirmation. Pick the lightest track that holds the risk; each step up adds calls.

| Track | Use for | Who does what |
|---|---|---|
| 1 Light | 1-2 files, bug fix, query, diagnosis | Main session or one executor; `gate-runner.sh` |
| 2 Standard | One submodule (endpoint + DB + UI) | One head runs `backlog-delegation`: Haiku/Sonnet executors, then `code-standards-gate` per item |
| 3 Heavy | Several submodules, cross-service seams | `split-and-brief` (contracts frozen) → one head per submodule on `parallel-build` → `e2e-verify` |

Track 2 with 6+ items may use `parallel-build` too. Don't pick Track 3 for a single-submodule slice: it costs more per task (see below).

1. The main session settles every open question with you (`brief-intake`).
2. It splits the work and launches one Sonnet head per submodule (`split-and-brief`).
3. Each head delegates items to executors and gates each one.
4. The main session tests the whole feature end to end (`e2e-verify`) and reports back.

## Parallel builds (Track 3)
Based on `parallel-agentic-build.md`. The plan is data (`<slice>/plan/*.json`), so `plan.py` can lint it, order it by the longest chain, and generate every prompt from it, including only the decisions that name each task. Wave 0 builds contracts, the test harness and a walking skeleton, and G0 freezes them. After that, each task runs one fixed path: build → `checker` (blind) → `plan.py judge` (the script decides) → `reviewer` if flagged → ladder (haiku → sonnet → opus, 3 attempts) → journal. A spec gap is settled once, as an R# entry with an `Applies to:` line. Agents still never commit: the journal plus the tree is the state, and the user lands commits at gates.

### What it costs, and how to keep it down
Per task: one builder + one checker + (if flagged) one reviewer, times retries, plus the head's turns to drive the loop. Every builder starts cold with the project preamble and its contracts. Most overhead is the **driver** (head or main), which carries the full skill text each turn.
- **Measure first.** After G0 and ~10 wave-A tasks, log tokens per task (retries included) in the integration log, multiply by the task count, then set the number of parallel builders.
- **Size tasks to 20-40 min.** Fewer, coarser tasks mean fewer cold starts. Set `review: true` only where a silent error would spread.
- **Cut dependency arrows before adding agents.** The longest chain is the floor on time.
- **Don't read source to second-guess a PASS.** Read the result files.
- **Don't spawn a head or executor whose output won't change the gate decision.**

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

