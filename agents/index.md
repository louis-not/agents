# Agent index

Each agent's `description` already says when to use it; the Agent tool routes on that. This page holds only what a description can't: pipelines, hard routing rules, and what is a skill instead.

## Agents and skills
- **Agent** = needs its own context (independence, or bulky reading kept out of the caller), its own tool limits, its own model, or runs as a parallel unit of work.
- **Skill** = a procedure or body of knowledge applied by whoever is already working, or a conversation with the user. Costs nothing until invoked.

| Agents (`agents/`) | Model | Notes |
|---|---|---|
| head-orchestrator | sonnet | preloads `backlog-delegation`, `code-standards-gate` |
| software-developer, database-administrator, data-analyst, ux-designer, ui-designer | sonnet | builders; preload `executor-base` |
| tester, memories-writer | haiku | preload `executor-base` |
| troubleshooter | sonnet | read-only by `tools:` |
| checker | haiku | blind, read-only; feeds `plan.py judge` |
| reviewer | opus | read-only; spec conformance, gap settling, claim verification |
| embedded-firmware-engineer, controls-engineer, comms-integration-engineer, hil-test-engineer | sonnet | drone projects only; install per project |

Skills run in the main session: `orchestrate`, `brief-intake`, `product-critique`, `split-and-brief`, `parallel-build`, `e2e-verify` (forks a `tester`), `jules-delegation`, `marketing-strategy`, `hardware-review`. Skills heads and executors use: `backlog-delegation`, `code-standards-gate`, `parallel-build` §3, `executor-base`.

## Pipelines
- **Feature:** `product-critique` → `brief-intake` → `ux-designer` → `ui-designer` → `software-developer` → `tester` (or `checker` + `plan.py judge`) → `memories-writer`
- **Bug, cause known:** `software-developer` (fix + regression test) → `tester` → `memories-writer`
- **Incident, cause unknown:** `troubleshooter` (prove the cause) → `software-developer` or `database-administrator` → `tester` → `memories-writer`. Never skip to the developer while the cause is unproven.
- **DB change:** `database-administrator` → `tester` → `memories-writer`
- **Data → action:** `data-analyst` → `marketing-strategy` (main session) → `software-developer` if it repeats → `memories-writer`
- **Embedded:** `hardware-review` (boards change) → `controls-engineer` (behavior changes) → `embedded-firmware-engineer` → `comms-integration-engineer` (link changes) → `hil-test-engineer` → `memories-writer`

Skip stages deliberately, not by default. Scale ceremony to risk.

## Hard routing rules
- **"Done" needs someone other than the builder:** `tester`, or `checker` + `plan.py judge`. The builder's green run is never the final word.
- **Anything that writes to Postgres** goes through `database-administrator`.
- **Unknown cause goes to `troubleshooter` first.** It changes nothing and doesn't connect to the DB; it returns read-only SQL as an evidence request for the DBA.
- **Structure before surface:** wrong flow, screens or states → `ux-designer`; wrong spacing, colour or hierarchy → `ui-designer`; if both, UX first.
- **Embedded changes are verified by `hil-test-engineer`**, which names the level reached (host, SITL, HIL, bench, flight). Nothing powers, flashes, arms or flies real hardware without the user's explicit confirmation.
- **Interfaces are frozen contracts.** A change is a ruling by the main orchestrator, announced to every affected agent.
- **Route sideways, not deeper:** a product question mid-build goes back to the main session; a flow problem found while styling goes to `ux-designer`.
