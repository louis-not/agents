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

## 4. Run the checks
Use the project's own commands. Look in `CLAUDE.md`, `package.json` scripts, `pyproject.toml`, `Makefile`, `pytest.ini` or CI config first. Common defaults:

| Stack | Commands |
|---|---|
| Python | `pytest -q`, `ruff check .`, `mypy .` (if configured) |
| Node / Vite | `npm run lint`, `npm run typecheck` or `tsc --noEmit`, `npm test`, `npm run build` |
| Android | `./gradlew lint testDebugUnitTest assembleDebug` |
| Docker | `docker compose build` |

Use the project's venv or conda env. Don't install packages globally.

## 5. Verdict
Return exactly this:

```
Verdict: ACCEPT | REJECT
Item: <id>
Checks run: <command → pass/fail, one line each>
Issues (if REJECT):
  1. <file:line> <what's wrong> → <what's expected>
```

Reject on any failing check or unchecked box that matters. Don't fix the code yourself; send the issues back to the executor.
