---
name: parallel-build
description: >-
  Runs a slice as a parallel agentic build: the plan as data (plan/*.json), wave 0 contracts and
  a walking skeleton frozen at G0, then every task on one fixed path (build, blind check, script
  verdict, review if flagged, ladder, journal). Spec gaps settle once into routed decisions.
  Use as the main orchestrator for Track 3 (and Track 2 with 6+ items) after brief-intake, and as
  a head running its tasks. Full rationale: parallel-agentic-build.md.
---

# Parallel Build

`E` = `~/Repositories/nexus-workspace/agents/scripts/plan.py` (inside nexus-workspace: `agents/scripts/plan.py`). `P` = the slice's plan dir, `todos/planned/<n>-<slug>/plan/`.

Four things hold at every size: **one writer per file, criteria provable from output, a check by someone other than the builder, shared decisions settled before the fan-out.**

## 1. Main: write the plan (after `brief-intake`, with `split-and-brief`)
Slice folder: `<n>-brief.md`, `<n>-contracts.md`, `<n>-integration-log.md` (decision log), `plan/`, `questions/`, `change-requests/`, `reports/`, `owner-questions.md`, `handoff.md`.

- `plan/config.json`: `repo` (repo root relative to `plan/`), `defaultCommands` (appended to every task's check, e.g. the typecheck), optionally `testCommandPattern`.
- `plan/w0.json` (main writes): wave 0 tasks. `plan/gates.json` (main writes): G0 and later gates. `plan/<head>.json` (each head writes its own tasks). One writer per plan file.
- Task fields: `id` (`M03`), `title`, `wave`, `agent`, `model` (haiku|sonnet|opus), `effort` (low|medium|high|xhigh, never max), `deps`, `owns`, `reads`, `criteria`, `commands`, `review`, `notes`. Gate fields: `id` (`G0`), `after`, `commands`, `review`, `owner`, `provides`, `then`. Example: [templates/plan-example/](templates/plan-example/).
- A dep exists only where a task reads another's output. Cut arrows before adding agents: the longest chain is the floor on time.
- A task fits one agent run (20-40 min). Set `review: true` and higher effort where a silent error spreads.
- **Criteria** (the checker is blind): one observable claim with its number, shown by a test named `<ID>: <criterion>` that prints what it proves. Expected values come from the spec, never from running the new code. A clause only a person or reviewer can judge gets its own `review: ` criterion. Commands: only what the task's own tests don't cover, ending with the area's smoke command. No `; echo`, no `|| true`, and never edit command text after the run starts.
- Run `python3 E lint P --agents <agents dir>` after **every** plan change. Fix every error.

## 2. Wave 0 and G0
Wave 0 (strongest capable model, high effort) builds what every later task stands on: shared types, constants, data formats, the test harness (fixtures, fixed clock, seeded data) and a **walking skeleton**, the thinnest system that runs end to end. Modules join the skeleton **by existing** (registry generated from exports, or an eager file glob); a missing module answers a stub (`501 not built: <area>.<op>`). Nobody edits a shared entry file to wire in. The smoke command runs the whole system and prints which parts are still stubs.

G0 runs typecheck, tests, build and the smoke command, reviews every contract task, and freezes `provides`. After G0 a contract changes only by change request, ruled as an R# in the integration log. Don't open wave A until G0 is logged.

**Measure before you scale:** after G0 and the first ~10 wave-A tasks, note tokens per task (retries included) in the integration log, multiply by the task count, and set the number of parallel builders. An assumed cost is usually several times too low.

## 3. Head: run each task on one path
For each ready task (`python3 E status P` lists them, longest chain first). Launch independent ones in one message.

1. `python3 E record P <ID> started --attempt N`
2. **Build.** `python3 E ladder P <ID> N` gives `subagent_type`, `model`, `effort`. Prompt = `python3 E prompt P build <ID> --attempt N [--feedback F] [--reason R]`, pasted **verbatim**. Never paraphrase a generated prompt.
3. Builder replies `blocked`: record `blocked` with the question or change-request path, and return it to the main orchestrator. Dependents wait; other tasks go on.
4. **Check.** Save the builder's JSON to `P/runs/<ID>-<N>-build.json`. Launch `checker` (haiku) with `python3 E prompt P check <ID> --evidence <that file>`. Save its JSON reply to `P/runs/<ID>-<N>-check.json`.
5. **Verdict.** `python3 E judge P <ID> P/runs/<ID>-<N>-check.json`. Exit 0 = PASS. You don't overrule it either way.
6. **Review** (only `review: true`, only after PASS). Launch `reviewer` with `python3 E prompt P review <ID> [--earlier <findings file>]`. Any blocking item counts as a FAIL.
7. FAIL: write the `why` (or the blocking items, with their class) to `P/runs/<ID>-<N>-feedback.md`, then go to step 2 with `N+1`. The ladder runs: attempt 2 is one model or effort up, attempt 3 is opus at high. After 3 attempts, record `failed` and return it.
8. PASS: run `code-standards-gate` on the diff, then `python3 E record P <ID> passed --attempt N --model M --note "<evidence>"`. Dependents can now start.

Don't read source to second-guess a PASS. Read the result files.

## 4. Gaps, decisions and the owner
- A builder writes `questions/<ID>-<n>.md` (gap another task depends on) or `change-requests/<ID>-<n>.md` (contract outside its files) and replies `blocked`.
- **Main settles each once:** one `reviewer` call with the question and the files it cites. Append the answer to the integration log as `### R<n> <ID>: <question>`, with `**Answer.**`, `**Spec files:**` and `**Applies to:** <every task id it concerns>`. An entry without `Applies to:` reaches nobody (lint refuses it). The generated prompt of every task named there carries the entry. Then rebuild the blocked task with `--reason "R<n>"`.
- An accepted change request is applied by **the owner of the file**, never the requester.
- A real product rule (not a gap) goes to `owner-questions.md` with the options and a **provisional default the build uses meanwhile**. Tell the user once, in a batch. Don't stop the build for it.
- Hand back every finding with its class and the instruction to scan for it. Gate rounds should shrink (for example 18 → 5 → 0); if they don't, the fixes are per-instance.

## 5. State, stop, resume
- The journal (`P/journal.jsonl`, append-only) plus the tree is the state. The user lands commits at gates; agents never commit.
- **Resume:** `python3 E status P`. For a task marked `started` with files on disk, run the **check first** (step 4) before building. If it passes, record `passed` with no builder. If it fails, build with `--reason "files on disk are an earlier attempt; complete what is missing, do not rewrite working code"` plus the check's `why`.
- **Stop** (allowance, end of day): stop running agents, refresh `handoff.md` ([templates/templates.md](templates/templates.md)) with the status output, half-done tasks and exact resume commands. The repository is the memory; nothing lives only in a session.
- Never rebuild passing work. Re-review a module only when its files changed since its last clean review.

## 6. After every run
Append to the integration log: tasks passed/failed/blocked with causes, retries and the cause of each, measured tokens. A retry cause that will recur becomes a rule in the task `notes`, the builder rules in `plan.py`, or a lint check. A prose reminder alone isn't enough.
