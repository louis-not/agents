#!/usr/bin/env bash
# gate-runner.sh - Deterministic code standards & test verification gate
# Runs secrets scan, linters, typecheckers, and test suites in one turn.
# Suppresses verbose passing stdout to save LLM tokens; reports concise failures.

set -o pipefail

QUIET=false
STAGED_ONLY=false
TMP_DIR=$(mktemp -d 2>/dev/null || mktemp -d -t 'gate_runner')
TRAP_EXIT() { rm -rf "$TMP_DIR"; }
trap TRAP_EXIT EXIT

for arg in "$@"; do
  case "$arg" in
    --quiet|-q) QUIET=true ;;
    --staged) STAGED_ONLY=true ;;
  esac
done

CHECKS_RUN=()
FAILURES=()

record_pass() {
  local stage="$1"
  CHECKS_RUN+=("${stage}[PASS]")
}

record_fail() {
  local stage="$1"
  local log_file="$2"
  CHECKS_RUN+=("${stage}[FAIL]")
  FAILURES+=("=== STAGE FAILED: ${stage} ===")
  if [ -f "$log_file" ]; then
    FAILURES+=("$(tail -n 25 "$log_file")")
  fi
}

run_step() {
  local stage="$1"
  shift
  local log="$TMP_DIR/${stage}.log"

  if "$@" > "$log" 2>&1; then
    record_pass "$stage"
  else
    record_fail "$stage" "$log"
    return 1
  fi
  return 0
}

# ---------------------------------------------------------
# 1. Secret & Sensitive File Leak Detection
# ---------------------------------------------------------
check_secrets() {
  local log="$TMP_DIR/secrets.log"
  local files
  if [ "$STAGED_ONLY" = true ]; then
    files=$(git diff --name-only --cached 2>/dev/null)
  else
    files=$(git status --porcelain 2>/dev/null | awk '{print $NF}')
  fi

  local leak_found=false
  for f in $files; do
    case "$f" in
      *.env|*.env.*|*.pem|*.key|*id_rsa*|*.keystore|*.p12|*credentials*.json)
        echo "Suspicious sensitive file staged or modified: $f" >> "$log"
        leak_found=true
        ;;
    esac
  done

  # Simple token pattern check in git diff
  if git diff HEAD 2>/dev/null | grep -E "AKIA[0-9A-Z]{16}|ghp_[0-9a-zA-Z]{36}|sk-ant-[0-9a-zA-Z]{20,}" >> "$log" 2>&1; then
    echo "Potential raw API token or key found in diff!" >> "$log"
    leak_found=true
  fi

  if [ "$leak_found" = true ]; then
    record_fail "secrets" "$log"
    return 1
  fi
  record_pass "secrets"
  return 0
}

check_secrets || true

# ---------------------------------------------------------
# 2. Python Stack Checks
# ---------------------------------------------------------
if [ -f "pyproject.toml" ] || [ -f "requirements.txt" ] || [ -f "setup.py" ]; then
  # Ruff or Flake8 linter
  if command -v ruff >/dev/null 2>&1; then
    run_step "python-lint" ruff check . || true
  elif command -v flake8 >/dev/null 2>&1; then
    run_step "python-lint" flake8 . || true
  fi

  # Mypy typecheck
  if [ -f "mypy.ini" ] || grep -q "tool.mypy" pyproject.toml 2>/dev/null; then
    if command -v mypy >/dev/null 2>&1; then
      run_step "python-typecheck" mypy . || true
    fi
  fi

  # Pytest
  if command -v pytest >/dev/null 2>&1; then
    run_step "python-test" pytest -q --tb=line || true
  fi
fi

# ---------------------------------------------------------
# 3. Node / TypeScript Stack Checks
# ---------------------------------------------------------
if [ -f "package.json" ]; then
  # Lint
  if grep -q '"lint"' package.json; then
    run_step "node-lint" npm run lint --silent || true
  fi

  # Typecheck
  if grep -q '"typecheck"' package.json; then
    run_step "node-typecheck" npm run typecheck --silent || true
  elif [ -f "tsconfig.json" ] && command -v npx >/dev/null 2>&1; then
    run_step "node-typecheck" npx tsc --noEmit || true
  fi

  # Test
  if grep -q '"test"' package.json && ! grep -q '"test": "echo .* no test' package.json; then
    run_step "node-test" npm test -- --silent || true
  fi
fi

# ---------------------------------------------------------
# 4. Android / Gradle Checks
# ---------------------------------------------------------
if [ -f "gradlew" ]; then
  run_step "gradle-test" ./gradlew testDebugUnitTest --quiet || true
fi

# ---------------------------------------------------------
# 5. Output Verdict
# ---------------------------------------------------------
TOTAL_CHECKS=${#CHECKS_RUN[@]}
FAILED_COUNT=${#FAILURES[@]}

if [ "$FAILED_COUNT" -eq 0 ]; then
  echo "VERDICT: ACCEPT"
  echo "CHECKS: ${CHECKS_RUN[*]}"
  exit 0
else
  echo "VERDICT: REJECT"
  echo "CHECKS: ${CHECKS_RUN[*]}"
  echo ""
  for failure_block in "${FAILURES[@]}"; do
    echo "$failure_block"
  done
  exit 1
fi
