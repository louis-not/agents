---
name: split-and-brief
description: >-
  Splits a confirmed brief into submodules, freezes the contracts between them, and writes a
  standalone brief for each head orchestrator. Use as the main orchestrator right after
  brief-intake, before launching any head-orchestrator agents.
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
- Group the submodules into waves: wave A has no dependencies, wave B depends on A, and so on.
- Contracts let consumers build against stubs, so most submodules usually fit in wave A.

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
Return: outcome, items with evidence, changed files, open issues
```

## 5. Launch
- Launch one head per submodule with `model: sonnet`. Use `subagent_type: head-orchestrator` if it's installed. Otherwise use `general-purpose`, with the contents of `~/Repositories/nexus-workspace/agents/prompts/head-orchestrator.md` at the top of the brief.
- Launch all heads in a wave in one message with parallel Agent calls.
- Continue a head with `SendMessage` for follow-ups. Don't start a fresh one.
