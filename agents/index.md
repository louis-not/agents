# Agent Index — which agent to pick

Routing guide for the orchestrator (and humans). Pick by the **nature of the task**, not by which agent sounds smartest. When a task spans stages, chain agents in pipeline order rather than asking one agent to do everything.

## Quick decision table

| If the task is… | Use | Not |
|---|---|---|
| "Should we build this?" / feasibility, scope pressure-test, backlog breakdown | `product-agent` | software-developer (don't scope by coding) |
| How a feature should *work* — flows, screens, navigation, states, usability review | `ux-designer` | ui-designer (that's the visual layer) |
| How a feature should *look* — layout, typography, color, components, design-system work | `ui-designer` | ux-designer (that's structure, not pixels) |
| Build / fix / refactor production code from a spec | `software-developer` | tester (verifies, doesn't build) |
| Verify a change: write + run tests, lint, typecheck, report real pass/fail | `tester` | software-developer (can't grade its own homework) |
| Something is broken and nobody knows why — pipeline error, wrong data, mystery failure | `troubleshooter` | software-developer (don't debug by editing) |
| Anything touching PostgreSQL — schema, migrations, indexes, data fixes, query review | `database-administrator` | software-developer (DB changes need the guardrail) |
| "What does this data say?" — explore/analyze datasets, build metrics, verify numbers | `data-analyst` | digital-marketing-specialist (interprets, doesn't compute) |
| Campaigns, funnels, lead-gen, CRM/lifecycle strategy, marketing copy | `digital-marketing-specialist` | data-analyst (computes, doesn't decide the play) |
| Record what happened — update `.agents/` hub, specs, memories, changelog | `memories-writer` | doing it inline as an afterthought |

## Trigger phrases → agent

- "is it worth building", "break this down into tickets", "what's the MVP" → **product-agent**
- "design the flow", "where should this live in the nav", "review the UX" → **ux-designer**
- "style this", "make it look good", "design tokens", "visual polish pass" → **ui-designer**
- "implement", "fix this bug", "refactor", "add the endpoint" → **software-developer**
- "add tests", "verify this", "is this actually correct", "why is CI red" → **tester**
- "why did this fail", "the pipeline broke", "this number is wrong", "worked yesterday", "find the root cause" → **troubleshooter**
- "migration", "add an index", "backfill", "delete these rows", "slow query" → **database-administrator**
- "analyze this export", "segment these leads", "is this number right", "build this metric" → **data-analyst**
- "plan a campaign", "improve the funnel", "reactivate lapsed customers", "review this copy" → **digital-marketing-specialist**
- "write this up", "update the changelog", "remember this decision" → **memories-writer**

## Standard pipelines

**Feature (full):**
`product-agent` (scope + tickets) → `ux-designer` (flow) → `ui-designer` (visuals) → `software-developer` (build) → `tester` (verify) → `memories-writer` (record)

**Bug fix (cause known):**
`software-developer` (fix + regression test) → `tester` (independent verify) → `memories-writer` (changelog)

**Incident / unknown cause:**
`troubleshooter` (isolate + prove root cause, read-only) → `software-developer` or `database-administrator` (fix) → `tester` (verify) → `memories-writer` (record cause + fix)
Never skip straight to the developer when the cause is unproven — a fix aimed at a symptom is how the same failure comes back.

**DB change:**
`database-administrator` (analyze → propose → apply) → `tester` (verify downstream behavior) → `memories-writer` (record migration + rollback path)

**Backend-only feature (no UI):** skip the designers; keep product → develop → test → record.

**Marketing/CRM analysis (e.g. GHL extraction):**
`data-analyst` (profile + analyze the data) → `digital-marketing-specialist` (turn findings into segments/campaigns) → `software-developer` (automate what's repeated) → `memories-writer` (record metric definitions + decisions)

Skip stages deliberately, not by default — but don't run the full pipeline for a one-line fix. Scale ceremony to risk.

## The testing loop (most common chain)

1. `software-developer` implements; runs its own tests; hands off the **contract, changed files, and commands run**.
2. `tester` independently authors + executes tests against the contract; returns a verdict: **passes / fails / passes-with-caveats** with real output.
3. Defects go **back to `software-developer`** — the tester reports and reproduces, it does not rewrite the feature.
4. Repeat until the tester's verdict is `PASSES`; then `memories-writer` records the outcome.

The developer's green run is never the final word; the tester is the quality gate.

## Hard routing rules

- **Anything that writes to Postgres** (DDL, unbounded DML, backfills) goes through `database-administrator` — even if a developer could technically run it. It blocks destructive ops and demands rollbacks; that's the point.
- **"Done" requires the tester.** No change is declared complete on the implementer's claim alone.
- **Unknown cause requires the troubleshooter.** When a failure's cause isn't proven, diagnose before dispatching a fix. The troubleshooter is read-only by design — it never edits, migrates, restarts, or deploys; it hands over a proven cause and the recommended fix.
- **The troubleshooter does not connect to the database either.** It writes bounded read-only SQL and returns it as a DB evidence request for the `database-administrator` to run.
- **Design questions split at structure vs. surface**: wrong screens/flow/states → `ux-designer`; wrong spacing/color/hierarchy → `ui-designer`. If both, UX first — don't polish a broken skeleton.
- **Agents route sideways, not deeper**: product questions surfacing mid-build go to `product-agent`; flow problems found while styling go to `ux-designer`. Each agent stays in its lane and names the handoff.

## Agent reference

| Agent | Role in one line | Posture |
|---|---|---|
| [head-orchestrator](head-orchestrator.md) | Owns one submodule: plans backlog, delegates to executors, tests before accepting | Sonnet; delegates, never talks to the user |
| [product-agent](product-agent.md) | Feasibility critique and engineer-ready backlog breakdown | Critical partner — will say "don't build this" |
| [ux-designer](ux-designer.md) | Flows, information architecture, interaction + state design | Upstream of visuals; designs the whole journey |
| [ui-designer](ui-designer.md) | Visual design as implementation-ready specs or code | Downstream of UX; system over one-off screens |
| [software-developer](software-developer.md) | Turns specs into production-quality code | Builder; understands before changing |
| [tester](tester.md) | Writes and runs tests; reports observed results | Skeptical gate; assumes broken until proven |
| [troubleshooter](troubleshooter.md) | Isolates and proves the root cause of a failure | Read-only detective; changes nothing, proves everything |
| [database-administrator](database-administrator.md) | Designs, reviews, and safely applies Postgres changes | Guardrail; smallest safe change, always a rollback |
| [data-analyst](data-analyst.md) | Answers questions with numbers from real data | Rigorous; profiles first, reproducible, caveats stated |
| [digital-marketing-specialist](digital-marketing-specialist.md) | Campaign, funnel, and CRM/lifecycle strategy | Commercial skeptic; every play ships with a metric |
| [memories-writer](memories-writer.md) | Curates the `.agents/` hub after work lands | Librarian; edits existing docs before adding new |

## Jules (Async GitHub Agent) Role Prompts
When delegating work to Google Jules via `jules-delegation`, use the self-contained prompt matching the task:
- **Module Owner / Submodule Lead**: `prompts/head-orchestrator.jules.md` (owns end-to-end plan, execution, self-review, and PR creation)
- **Single Backlog Item**: `prompts/executor.jules.md` (bounded change in a single area/file)
- **Independent Testing**: `prompts/tester.jules.md` (authors and executes tests against contracts on an external branch)
- **Review Follow-up**: `prompts/fixer.jules.md` (addresses review findings from `code-standards-gate`)
- **Root-Cause Investigation**: `prompts/troubleshooter.jules.md` (reproduces failure, isolates cause without mutating code)

