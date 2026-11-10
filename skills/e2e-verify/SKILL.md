---
name: e2e-verify
description: >-
  Tests an integrated feature end to end against its acceptance criteria and returns a result
  table with evidence. Invoke as the main orchestrator with the brief path (and the criteria)
  as arguments, once all heads report done. Runs in a forked tester: starts the real app or
  services locally, runs the user flows, collects evidence, cleans up. Works for FastAPI,
  React/Vite, Docker Compose, Android apps and scrapers.
context: fork
agent: tester
---

# End-to-End Verify

Goal: prove the feature works as the user will use it, with evidence. Never run this against production.

You start with no conversation history. Your input: $ARGUMENTS. Read the brief (and its acceptance criteria) from there. Don't fix anything; report.

## 1. Plan
Turn each acceptance criterion from the brief into one or more checks:

```
AC1 <criterion>
  Steps: <what to do>
  Expected: <observable result>
  How: curl | browser | adb | script | test suite
```

Include the main flow, at least one error or edge flow per criterion, and one regression check on a nearby existing feature.

## 2. Bring it up locally
Find the project's way to run it. Check `CLAUDE.md`, the README, `docker-compose.yml`, `package.json`, `Makefile` and `.env.example`.

| Stack | Typical start | Ready when |
|---|---|---|
| Docker Compose | `docker compose up -d --build` | `docker compose ps` shows healthy; health endpoint returns 200 |
| FastAPI | `uvicorn app.main:app --port 8000` (in background) | `curl -sf localhost:8000/health` or `/docs` |
| Vite / React | `npm run dev -- --port 5173` (in background) | `curl -sf localhost:5173` |
| Android | `./gradlew installDebug` on an emulator or device | `adb shell am start -n <pkg>/<activity>` succeeds |
| Scraper | Run on a small, fixed sample of targets | Output files or rows appear |

- Run long-lived processes in the background, and remember every process you started.
- Use local or test data and the project's env or venv. If the feature needs a production-only secret or service, stop and tell the user.

## 3. Run the checks
- **APIs:** `curl` each endpoint in the plan. Check status, response shape against the contract, and error cases.
- **Web UI:** use a browser tool if one is available (built-in browser or Claude in Chrome; load its skill first), otherwise Playwright if the project has it. Walk each flow and screenshot key states. Check the console for errors.
- **Android:** `adb` to launch and drive the app, `adb exec-out screencap -p > shot.png` for evidence, `adb logcat` for crashes.
- **Data and jobs:** run the job, then check its output: row counts, sample records, file contents.
- **Suites:** run the full test suite and build for every touched repo.

## 4. Clean up
Stop every process you started (`docker compose down`, kill background servers). Don't delete volumes or data without asking.

## 5. Report

```
## End-to-end result: PASS | FAIL | PARTIAL
| AC | Check | Result | Evidence |
|---|---|---|---|
| AC1 | <check> | pass/fail | <command and output excerpt, or screenshot path> |
Suites: <repo → command → result>
Not tested: <what, and why>
Failures: <per failing check: expected vs actual, the class of the defect, the likely owning area>
```
