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
- **Done when:** checks that prove it works (tests, commands, expected output)
- **Depends on:** other item IDs, or none

A good item is one focused change an executor can finish and verify alone. If it needs "and" to describe, it's probably two items.

## 2. Pick the agent
Use `~/Repositories/nexus-workspace/agents/agents/index.md`. Short version:

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
| Nothing above fits | `general-purpose` |

If the specialist isn't installed as a native agent type, use `general-purpose` and paste the agent's `.md` body into the brief.

## 3. Pick the model

| Use `haiku` (default) | Use `sonnet` |
|---|---|
| Clear spec, one or two files | Design or judgment calls |
| Boilerplate, CRUD, wiring | Tricky debugging, concurrency, security |
| Tests for a defined contract | Changes across many files |
| Search, lookups, conversions | Schema and migration design |
| Docs and changelog | A Haiku attempt came back wrong |

Escalate once after a bad attempt; don't retry the same tier twice. If Sonnet also fails, report the item as blocked.

## 4. Pick the skills
List the skills that apply by name, for example `frontend-design` for UI work, `claude-api` for anything calling Claude, `code-standards-gate` for a reviewing `tester`. If none fit, write "none".

## 5. Write the executor brief
Give just enough context, no more:

```
<contents of ~/Repositories/nexus-workspace/agents/prompts/executor.md>

## Your role
<agent name, or its pasted .md body>

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
- Review each result with `code-standards-gate`, then send it to a `tester` executor for verification.
- On failure, use `SendMessage` to send the same executor the failing output and the expected behavior.
- Track item status: todo → in progress → review → accepted, blocked or escalated.
