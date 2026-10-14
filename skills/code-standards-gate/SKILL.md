---
name: code-standards-gate
description: >-
  Reviews a finished change against coding standards and runs the project's checks, then
  returns ACCEPT or REJECT with specifics. Use as a head orchestrator, or a tester executor,
  before accepting any backlog item. Covers Python/FastAPI, TypeScript/React, Kotlin/Android
  and SQL.
---

# Code Standards Gate

## 1. See the change
- Run `git status` and `git diff` (or `git diff <base>...`) to see exactly what changed.
- Read the backlog item's contract and "done when", and judge the diff against them, not against what the executor said.

## 2. General checklist
- [ ] Does what the contract says, nothing more. No unrequested refactors or features.
- [ ] Only touches files the item owns.
- [ ] Matches the surrounding code: naming, structure, patterns, comment density.
- [ ] Tests cover new and changed behavior, including one failure or edge case.
- [ ] Errors are handled at boundaries; inputs from users or the network are validated.
- [ ] No secrets, tokens, `.env` contents or keystores. No hard-coded URLs that should be config.
- [ ] No dead code, commented-out code, debug prints or stray TODOs.
- [ ] Frozen contracts are respected exactly: names, types, status codes.

## 3. Stack checklist

**Python / FastAPI**
- Type hints on public functions. Pydantic models for request and response bodies.
- No blocking IO inside `async def`. Use async clients, or run in a threadpool.
- No bare `except:`. Log errors with context. Return proper HTTP errors.
- DB sessions are scoped and closed. Queries are parameterized. Schema changes go through Alembic and `database-administrator`.

**TypeScript / React**
- Strict types; no `any` or `@ts-ignore` without a reason.
- API types are generated from OpenAPI, not hand-written, where the project does that.
- Hooks rules are followed. Effects have correct dependencies and clean up.
- Server state lives in TanStack Query (or the project's choice), not copied into local state.
- User-facing text goes through i18n when the project has it. Keep on-screen text minimal.

**Kotlin / Android**
- No network or disk IO on the main thread. Coroutines use the right scope (`viewModelScope`, `lifecycleScope`).
- UI state lives in a ViewModel. Strings live in resources, not hard-coded.
- No secrets in `BuildConfig` or resources. Permissions are requested at runtime where needed.

**SQL / migrations**
- Reversible, with a down migration. Safe on existing data. Indexes where queries need them.
- Reviewed or applied by `database-administrator`.

## 4. Run the checks (Token-efficient execution)
Run the automated gate script first. It executes secrets scans, linters, typechecks, and tests in one turn with silent stdout on pass:

```bash
~/Repositories/nexus-workspace/agents/scripts/gate-runner.sh
```

If running commands manually, look in `CLAUDE.md`, `package.json`, `pyproject.toml`, or `Makefile`. **Never dump raw passing test stdout into context**. Suppress stdout and only report failures:

| Stack | Commands (Token-Suppressed) |
|---|---|
| Python | `pytest -q --tb=line > /tmp/test.log 2>&1 && echo "pytest: PASS" \|\| tail -n 25 /tmp/test.log`, `ruff check .` |
| Node / Vite | `npm run lint --silent`, `npx tsc --noEmit`, `npm test -- --silent` |
| Android | `./gradlew lint testDebugUnitTest assembleDebug --quiet` |
| Docker | `docker compose build` |

Use the project's venv or conda env. Don't install packages globally.

## 5. Verdict (Telegraphic output)
Return exactly this compact format:

```
Verdict: ACCEPT | REJECT
Item: <id>
Checks: <command -> PASS/FAIL, one line each>
Issues (if REJECT):
  - <file:line> <what's wrong> -> <what's expected>
```

Reject on any failing check or unchecked box that matters. Don't fix the code yourself; send the issues back to the executor.
