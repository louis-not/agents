---
name: backlog-delegation
description: >-
  Breaks a submodule into backlog items and hands each to the right executor with the right
  model, skills and a minimal brief. Use as a head orchestrator after confirming your context,
  and again when re-dispatching a failed item.
---

# Backlog Delegation

## 1. Write the backlog
Each item has:
- **ID and title**, for example `B3 Add /forecasts endpoint`
- **Contract:** inputs, outputs and the interfaces it must respect
- **Files:** the ones it owns. Two parallel items never share a file.
- **Done when:** checks that prove it works. Each is one observable claim with its number, shown by a test named `<ID>: <claim>` that prints what it proves. "Works correctly" can't be checked; "a taken slot answers 409 SLOT_TAKEN" can.
- **Depends on:** other item IDs, or none

A good item is one focused change an executor can finish and verify alone. If it needs "and" to describe, it's probably two items.

If the slice has a plan dir, write the items as task records in `plan/<your-head>.json` instead (fields and example in the `parallel-build` skill) and run `plan.py lint`. The prompts are then generated from the records; skip §5.

## 2. Pick the agent
Agent descriptions route most items. Hard routing rules and pipelines: `agents/index.md`. Short version:

| Item | Agent |
|---|---|
| Build, fix or refactor code | `software-developer` |
| Write and run tests, check a change | `tester` |
| Unknown cause of a failure | `troubleshooter` (read-only) |
| Anything that writes to Postgres | `database-administrator` |
| Flows, states, navigation | `ux-designer` |
| Visual design, styling | `ui-designer` |
| Numbers from data | `data-analyst` |
| Docs, changelog, `.agents/` hub | `memories-writer` |
| Code or file search | `Explore` |
| Blind check of a task's commands (plan dir) | `checker` |
| Spec conformance of a flagged task | `reviewer` |
| Nothing above fits | `general-purpose` |

If the specialist isn't installed as a native agent type, use `general-purpose` and paste the agent's `.md` body and `skills/executor-base/SKILL.md` into the brief.

## 3. Pick the model

| Use `haiku` (default) | Use `sonnet` |
|---|---|
| Clear spec, one or two files | Design or judgment calls |
| Boilerplate, CRUD, wiring | Tricky debugging, concurrency, security |
| Tests for a defined contract | Changes across many files |
| Search, lookups, conversions | Schema and migration design |
| Docs and changelog | A Haiku attempt came back wrong |

The ladder: attempt 2 goes one model up (or one effort up on Sonnet) with the failing evidence; attempt 3 goes to `opus` at high effort. After 3 attempts, report the item as failed. Never use max effort: it over-thinks and edits beyond scope.

## 4. Pick the skills
List the skills that apply by name, for example `frontend-design` for UI work, `claude-api` for anything calling Claude, `code-standards-gate` for a reviewing `tester`. If none fit, write "none".

## 5. Write the executor brief
Give just enough context, no more. The role and the `executor-base` rules come with the native agent; don't paste them.

```
## Backlog item: <id> <title>
Context: <repo path, stack, the 2-5 files that matter>
Task: <what to do>
Contract: <inputs, outputs, interfaces to respect>
Conventions: <style, libraries, patterns to follow, with one example file>
Skills: <names, or "none">
Done when: <checks that must pass>
Don't touch: <files and areas outside scope>
```

## 6. Run the loop
- Launch the independent items in one message. Launch the dependent ones as their dependencies are accepted.
- Verify each result with someone other than its builder: `checker` (blind, runs the "Done when" commands) and `plan.py judge` for the verdict when there's a plan, otherwise a `tester` executor. Then `code-standards-gate`.
- On failure, use `SendMessage` to send the same executor the failing output and the expected behavior.
- Track item status: todo → in progress → review → accepted, blocked or escalated.
