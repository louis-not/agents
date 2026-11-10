---
name: split-and-brief
description: >-
  Main session, Track 3: split a confirmed brief along seams, freeze the contracts, give each file one owner, and write a standalone brief per head.
---

# Split and Brief

## 1. Find the seams
Split along boundaries where the work can proceed independently once a contract exists. Typical seams:
- backend API / domain logic
- database schema and migrations
- frontend screens and state
- 3D scene or canvas
- ML or data pipeline
- Android app layer
- infra, CI and deployment

Size check: each submodule should be about 2-8 backlog items. Merge smaller ones. Split bigger ones along a further seam.

## 2. Freeze the contracts
For each boundary between submodules, write the contract before anyone builds:

```
### Contract C<n>: <provider> → <consumer>
Kind: REST endpoint | event | schema | file format | component props | function
Shape: <exact request/response, fields and types, status codes or errors>
Owner: <submodule that implements it>
Notes: <auth, pagination, versioning, example payload>
```

- Prefer contracts the tooling can enforce: OpenAPI, Pydantic models, TypeScript types generated from OpenAPI, DB migrations.
- Give each file or directory exactly one owning submodule.
- If the repo keeps planning docs, save the contracts as `<n>-contracts.md` next to the brief. Changing a contract later is your decision; tell every affected head.

## 3. Order the work
- **Wave 0** (Track 3): contracts as code, test harness and walking skeleton, frozen at G0. Details in `parallel-build` §2.
- Group the rest into waves: wave A has no dependencies beyond G0, wave B depends on A, and so on.
- Contracts let consumers build against stubs, so most submodules usually fit in wave A.
- The longest chain of dependent work is the floor on time. Cut dependencies before adding agents.
- Track 3: write `plan/config.json`, `plan/w0.json` and `plan/gates.json` (see `parallel-build`), and run `plan.py lint`.

## 4. Write each head's brief
Heads see nothing of this conversation. Each brief must stand alone:

```
## Submodule: <name>
Goal: <one sentence>
Context: <repo path, stack, docs and files to read, the user's answers that apply>
In scope: <...>
Out of scope: <...>
Owns: <files and directories>
Contracts: <C-numbers it provides or consumes, pasted in full>
Constraints: <conventions, libraries, things not to touch>
Definition of done: <acceptance criteria for this submodule and the tests that must pass>
Plan: <slice>/plan/  (write your tasks only to plan/<head>.json; follow the parallel-build skill), or "none"
Skills: <beyond the two you preload: parallel-build only if Plan is set; a domain skill only if this submodule needs it>
Return: outcome, items with evidence, changed files, open issues
```

## 5. Launch
- Launch one head per submodule with `model: sonnet`. Use `subagent_type: head-orchestrator` if it's installed. Otherwise use `general-purpose`, with the body of `agents/head-orchestrator.md` and the two skills it preloads at the top of the brief.
- Launch all heads in a wave in one message with parallel Agent calls.
- Continue a head with `SendMessage` for follow-ups. Don't start a fresh one.
