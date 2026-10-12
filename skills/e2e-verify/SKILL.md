---
name: e2e-verify
description: >-
  Tests an integrated feature end to end against its acceptance criteria before reporting to
  the user. Use as the main orchestrator after all heads report done. Starts the real app or
  services locally, runs the user flows, and collects real evidence. Works for FastAPI
  backends, React/Vite frontends, Docker Compose stacks, Android apps and scrapers.
---

# End-to-End Verify

Goal: prove the feature works as the user will use it, with evidence. Never run this against production.

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

## 4. Fix loop
For each failure, record the check, expected vs actual and the evidence, then route it to the owning head. Test again after their fix. Re-run the regression check too.

## 5. Clean up
Stop every process you started (`docker compose down`, kill background servers). Don't delete volumes or data without asking.

## 6. Report

```
## End-to-end result: PASS | FAIL | PARTIAL
| AC | Check | Result | Evidence |
|---|---|---|---|
| AC1 | <check> | pass/fail | <command and output excerpt, or screenshot path> |
Suites: <repo → command → result>
Not tested: <what, and why>
```
