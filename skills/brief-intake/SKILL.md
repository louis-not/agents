---
name: brief-intake
description: >-
  Turns a feature request, PRD or brief into a confirmed spec before any work starts. Use as
  the main orchestrator at the start of every task bigger than a small fix: finds every
  ambiguity, asks all the questions in one batch with recommended defaults, and plays back a
  short brief for the user to confirm. Not for subagents.
---

# Brief Intake

Goal: by the end, nothing in the brief is left to guess. Execution can then run without stopping for questions.

## 1. Read first, then ask
- Read the whole brief, the repo's `CLAUDE.md`, its docs, specs or mockups, and the code the feature touches.
- Anything the code, docs or an obvious convention already answers is not a question. Decide it and record it as an assumption.

## 2. Find the ambiguities
Go through each category. Note every point where two reasonable engineers could build different things:

| Category | Ask about |
|---|---|
| Goal | Who it's for, what problem it solves, how success is measured |
| Scope | What's in, what's explicitly out, MVP vs later |
| Behavior | Main flow, alternate flows, what each screen or endpoint does |
| Edge cases | Empty, error, loading, limits, duplicates, permissions, offline |
| Data | Sources, schema changes, migrations, existing data, retention |
| Interfaces | APIs consumed or exposed, auth, third-party services, rate limits |
| UI | Layout source (mockup or design system), copy, languages (ID/EN), devices |
| Non-functional | Performance, security, cost, observability |
| Delivery | Environments, feature flags, deadlines, what "done" means |
| Testing | Acceptance criteria, test data, who checks what |

## 3. Ask once, in one batch
- Group the questions by category and number them.
- Give a recommended default for each, so the user can answer "all defaults except 4".
- Use `AskUserQuestion` for choices between 2-4 clear options (up to 4 questions per call). Put the rest in plain text in the same turn.
- Put the questions that change the most work first.

## 4. Play back the brief
After the answers, assign the execution track and write this for confirmation:

- **Track 1 (Light):** 1-2 files, bugfix, schema lookup, isolated script. Main dispatches 1 executor directly + runs gate runner. Bypasses Head and separate Tester.
- **Track 2 (Standard):** Single submodule or feature (1 endpoint + DB + UI). Main acts as Head directly, dispatching Dev and Tester directly.
- **Track 3 (Heavy):** Multi-submodule system architecture, cross-boundary seams, or high-risk migrations. Full 3-tier with parallel heads.

```
## Brief: <feature>
Track: Track 1 (Light) | Track 2 (Standard) | Track 3 (Heavy)
Goal: <one sentence>
In scope: <bullets>
Out of scope: <bullets>
Acceptance criteria:
  1. <testable statement>
  2. ...
Assumptions: <decisions you made without asking>
Open risks: <anything still uncertain, and how it'll be handled>
```

- Each acceptance criterion must be testable; verification checks against them later.
- If the repo keeps planning docs (for example `todos/planned/<n>-<slug>/`), save the brief there as `<n>-brief.md`.

## 5. Gate
Start execution only after the user confirms. If they change something, update the brief and play back only the changes.
