#!/usr/bin/env python3
"""plan.py - the plan engine for parallel agentic builds (stdlib only).

The plan is data. Heads generate every prompt from it, a script (not an agent) decides
pass/fail, and an append-only journal records state. See skills/parallel-build/SKILL.md.

Plan directory layout (usually <slice>/plan/):
  config.json        optional: {"repo": "<repo root, relative to plan dir>",
                                 "decisions": "<decision log, relative to plan dir>",
                                 "defaultCommands": [...], "testCommandPattern": "<regex>",
                                 "escalation": {"model": "sonnet", "effort": "high"}}  (attempt 3; default opus/high)
  *.json             plan files: {"tasks": [...], "gates": [...]}; one file per owner
                     (main: w0.json + gates.json; each head: <head>.json)
  journal.jsonl      append-only events, written by `record`

Commands:
  lint     <plan>                         refuse a bad plan before a run (exit 1 on error)
  status   <plan>                         done / ready (longest chain first) / blocked / failed
  ladder   <plan> <ID> <attempt>          agent, model and effort for this attempt
  prompt   <plan> build|check|review <ID> [--attempt N] [--feedback FILE] [--reason TEXT]
  judge    <plan> <ID> <check.json|->     the verdict, from the checker's structured result
  record   <plan> <ID> <event> [--attempt N] [--model M] [--note TEXT]
  decisions <plan> <ID>                   the decision-log entries routed to this task
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MODELS = ("haiku", "sonnet", "opus")
EFFORTS = ("low", "medium", "high", "xhigh")
EFFORT_UP = {"low": "medium", "medium": "high", "high": "xhigh", "xhigh": "xhigh"}
MODEL_UP = {"haiku": "sonnet", "sonnet": "sonnet", "opus": "opus"}
ESCALATION = {"model": "opus", "effort": "high"}
EVENTS = ("started", "passed", "failed", "blocked", "reopened")
DEFAULT_TEST_PATTERN = (
    r"^(npx vitest|vitest|npm (run )?test|pnpm (run )?test|yarn test|npx playwright test"
    r"|pytest|python3? -m pytest|uv run pytest|poetry run pytest|\./gradlew \S*[Tt]est)\b"
)
ID_RE = re.compile(r"^[A-Z]{1,3}\d{1,3}[a-z]?$")
GATE_RE = re.compile(r"^G[A-Z0-9]{1,4}$")
SUFFIX_RE = re.compile(r"(;|&&|\|\|)\s*(echo|true|exit)\b|\$\?|\becho\s+\$")
REVIEWER_RE = re.compile(r"\b(reviewer|reviewed by|a reviewer|manual(ly)? check|eyeball)\b", re.I)
VAGUE_RE = re.compile(r"\b(works?|properly|correctly|well|nicely|as expected|looks? (good|right))\b", re.I)
NOISE_RE = re.compile(
    r"\b(logs?|log files?|exit codes?|exit status|wrapper|not echoed|echo|stdout|stderr|transcripts?)\b", re.I
)
DECISION_HEAD_RE = re.compile(r"^###\s+([RD]\d+)\b(.*)$")
APPLIES_RE = re.compile(r"\*\*Applies to:\*\*\s*(.+)", re.I)


# ---------------------------------------------------------------- loading


class Plan:
    def __init__(self, plan_dir: Path):
        self.dir = plan_dir.resolve()
        cfg_path = plan_dir / "config.json"
        self.config = json.loads(cfg_path.read_text()) if cfg_path.exists() else {}
        self.repo = (plan_dir / self.config.get("repo", ".")).resolve()
        self.tasks: dict[str, dict] = {}
        self.gates: dict[str, dict] = {}
        self.sources: dict[str, str] = {}
        self.load_errors: list[str] = []
        for f in sorted(plan_dir.glob("*.json")):
            if f.name == "config.json":
                continue
            try:
                data = json.loads(f.read_text())
            except json.JSONDecodeError as e:
                self.load_errors.append(f"{f.name}: invalid JSON ({e})")
                continue
            for kind, store in (("tasks", self.tasks), ("gates", self.gates)):
                for rec in data.get(kind, []):
                    rid = rec.get("id", "?")
                    if rid in self.tasks or rid in self.gates:
                        self.load_errors.append(f"duplicate id {rid} ({self.sources[rid]} and {f.name})")
                        continue
                    store[rid] = rec
                    self.sources[rid] = f.name

    @property
    def journal_path(self) -> Path:
        return self.dir / "journal.jsonl"

    @property
    def decisions_path(self) -> Path | None:
        if "decisions" in self.config:
            return (self.dir / self.config["decisions"]).resolve()
        slice_dir = self.dir.parent
        logs = sorted(slice_dir.glob("*integration-log.md"))
        if logs:
            return logs[0]
        cand = slice_dir / "decisions.md"
        return cand if cand.exists() else None

    def test_pattern(self) -> re.Pattern:
        return re.compile(self.config.get("testCommandPattern", DEFAULT_TEST_PATTERN))

    def check_commands(self, t: dict) -> list[str]:
        return list(t.get("commands", [])) + list(self.config.get("defaultCommands", []))

    def check_criteria(self, t: dict) -> list[str]:
        return [c for c in t.get("criteria", []) if not c.lower().startswith("review:")]

    def review_points(self, t: dict) -> list[str]:
        return [c[len("review:"):].strip() for c in t.get("criteria", []) if c.lower().startswith("review:")]

    def state(self) -> dict[str, dict]:
        """Latest event per id from the journal."""
        out: dict[str, dict] = {}
        if self.journal_path.exists():
            for line in self.journal_path.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                out[ev["id"]] = ev
        return out

    def done(self) -> set[str]:
        return {i for i, ev in self.state().items() if ev["event"] == "passed"}


def load(path: str) -> Plan:
    p = Path(path)
    if p.is_file():
        p = p.parent
    if not p.is_dir():
        sys.exit(f"plan.py: no plan directory at {path}")
    return Plan(p)


# ---------------------------------------------------------------- lint


def _overlaps(a: str, b: str) -> bool:
    """True when two owned paths can name the same file (exact, or a dir/glob containing the other)."""

    def base(p: str) -> str:
        return re.split(r"[*?\[]", p, maxsplit=1)[0].rstrip("/")

    if a == b:
        return True
    ga, gb = any(c in a for c in "*?["), any(c in b for c in "*?[")
    ba, bb = base(a), base(b)
    if ga and (b == ba or b.startswith(ba + "/")):
        return True
    if gb and (a == bb or a.startswith(bb + "/")):
        return True
    if ga and gb and (ba.startswith(bb + "/") or bb.startswith(ba + "/") or ba == bb):
        return True
    return False


def _cycles(nodes: dict[str, list[str]]) -> list[str]:
    seen, stack, found = set(), [], []

    def visit(n: str):
        if n in stack:
            found.append(" -> ".join(stack[stack.index(n):] + [n]))
            return
        if n in seen:
            return
        seen.add(n)
        stack.append(n)
        for d in nodes.get(n, []):
            visit(d)
        stack.pop()

    for n in nodes:
        visit(n)
    return found


def lint(plan: Plan, agents_dir: Path | None = None) -> tuple[list[str], list[str]]:
    errors, warnings = list(plan.load_errors), []
    ids = set(plan.tasks) | set(plan.gates)
    graph: dict[str, list[str]] = {}

    for tid, t in plan.tasks.items():
        where = f"{tid} ({plan.sources[tid]})"
        if not ID_RE.match(tid):
            errors.append(f"{where}: id must look like M03 or M03a")
        for field in ("title", "wave", "agent", "owns", "criteria"):
            # a finished task whose files a ruling handed on keeps "owns": [] and says so with "released": "R<n>"
            if field == "owns" and t.get("released") and t.get("owns") == []:
                continue
            if not t.get(field):
                errors.append(f"{where}: missing {field}")
        model = t.get("model", "haiku")
        if model not in MODELS:
            errors.append(f"{where}: model {model!r} not in {MODELS}")
        effort = t.get("effort", "medium")
        if effort not in EFFORTS:
            errors.append(f"{where}: effort {effort!r} not in {EFFORTS} (never max)")
        if agents_dir and t.get("agent") and not (agents_dir / f"{t['agent']}.md").exists():
            errors.append(f"{where}: no agent file {t['agent']}.md in {agents_dir}")
        for d in t.get("deps", []):
            if d not in ids:
                errors.append(f"{where}: unknown dependency {d}")
        graph[tid] = list(t.get("deps", []))
        crit = t.get("criteria", [])
        review_crit = [c for c in crit if c.lower().startswith("review:")]
        if review_crit and not t.get("review"):
            errors.append(f"{where}: has a 'review:' criterion but review is not true")
        if crit and not plan.check_criteria(t) and not plan.check_commands(t):
            errors.append(f"{where}: nothing a machine can check (no plain criterion, no command)")
        for c in crit:
            if not c.lower().startswith("review:") and REVIEWER_RE.search(c):
                errors.append(f"{where}: criterion names a reviewer without the 'review: ' prefix: {c[:80]}")
            if not c.lower().startswith("review:") and VAGUE_RE.search(c) and not re.search(r"\d|`|\"", c):
                warnings.append(f"{where}: criterion may not be provable from output (no number, code or quote): {c[:80]}")
        for cmd in t.get("commands", []):
            if SUFFIX_RE.search(cmd):
                errors.append(f"{where}: command has an echo / exit-code suffix: {cmd}")
        for r in t.get("reads", []):
            if not any((base / r).exists() for base in (plan.dir, plan.dir.parent, plan.repo)):
                errors.append(f"{where}: reads {r!r} names no file (looked in plan dir, slice dir, repo)")
        if not t.get("deps") and t.get("wave") not in ("0", "A0") and plan.gates:
            warnings.append(f"{where}: wave {t.get('wave')} task waits for no gate; does its smoke command need the skeleton?")

    for gid, g in plan.gates.items():
        where = f"{gid} ({plan.sources[gid]})"
        if not GATE_RE.match(gid):
            errors.append(f"{where}: gate id must look like G0 or GA")
        for a in g.get("after", []):
            if a not in ids:
                errors.append(f"{where}: after names unknown id {a}")
        for r in g.get("review", []):
            if r not in plan.tasks:
                errors.append(f"{where}: review names unknown task {r}")
        for cmd in g.get("commands", []):
            if SUFFIX_RE.search(cmd):
                errors.append(f"{where}: command has an echo / exit-code suffix: {cmd}")
        graph[gid] = list(g.get("after", []))

    for c in _cycles(graph):
        errors.append(f"dependency cycle: {c}")

    owned = [(tid, p) for tid, t in plan.tasks.items() for p in t.get("owns", [])]
    for i, (ta, pa) in enumerate(owned):
        for tb, pb in owned[i + 1:]:
            if ta != tb and _overlaps(pa, pb):
                errors.append(f"file has two owners: {pa} ({ta}) and {pb} ({tb})")

    dpath = plan.decisions_path
    if dpath and dpath.exists():
        for did, _title, body in parse_decisions(dpath.read_text()):
            if not APPLIES_RE.search(body):
                errors.append(f"decision {did} in {dpath.name} has no '**Applies to:**' line, so it reaches nobody")
    return errors, warnings


# ---------------------------------------------------------------- decisions


def parse_decisions(text: str) -> list[tuple[str, str, str]]:
    out, cur = [], None
    for line in text.splitlines():
        m = DECISION_HEAD_RE.match(line)
        if m:
            if cur:
                out.append(cur)
            cur = [m.group(1), m.group(2).strip(), line + "\n"]
        elif line.startswith("## ") or line.startswith("### "):
            if cur:
                out.append(cur)
            cur = None
        elif cur:
            cur[2] += line + "\n"
    if cur:
        out.append(cur)
    return [tuple(x) for x in out]


def routed_decisions(plan: Plan, tid: str) -> tuple[list[str], str]:
    dpath = plan.decisions_path
    if not dpath or not dpath.exists():
        return [], ""
    entries, last = [], ""
    for did, title, body in parse_decisions(dpath.read_text()):
        last = did
        m = APPLIES_RE.search(body)
        names = set(re.findall(r"[A-Z]{1,3}\d{1,3}[a-z]?", m.group(1))) if m else set()
        if tid in names or re.search(rf"\b{re.escape(tid)}\b", title):
            entries.append(body.strip())
    return entries, last


# ---------------------------------------------------------------- judge


def _norm(s) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\"'`]", "", str(s or ""))).strip()


def _words(s: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9@]+", _norm(s).lower()) if len(w) > 3}


def _names_criterion(entry: str, criteria: list[str]) -> bool:
    a = _words(entry)
    if not a:
        return False
    return any(len(a & _words(c)) / len(a) >= 0.6 for c in criteria)


def _clip(s, n: int) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[:n] + " [...]"


def judge(commands: list[str], check: dict | None, criteria: list[str], test_re: re.Pattern) -> dict:
    """Pass only when every command was reported, exited 0, every test command ran tests,
    and no real criterion is unconfirmed. Noise remarks that name no criterion are ignored."""
    if not check or not isinstance(check.get("results"), list):
        return {"ok": False, "why": "the check returned no results", "ignored": []}
    problems, ignored = [], []
    results = check["results"]
    for i, c in enumerate(commands):
        r = results[i] if len(results) == len(commands) else None
        if not r or _norm(r.get("command")) != _norm(c):
            r = next((x for x in results if _norm(x.get("command")) == _norm(c)), None)
        if r is None:
            problems.append(f"not run or not reported: {c}")
        elif r.get("exitCode") != 0:
            problems.append(f"{c} exited {r.get('exitCode')}: {_clip(r.get('output'), 1500)}")
        elif test_re.search(c.strip()) and not (r.get("testsRun") or 0) > 0:
            problems.append(f"{c} ran no tests")
    for m in check.get("missingCriteria") or []:
        if NOISE_RE.search(m) and not _names_criterion(m, criteria):
            ignored.append(_clip(m, 160))
        else:
            problems.append(f"not shown by any passing test or command: {m}")
    return {"ok": not problems, "why": "\n".join(problems), "ignored": ignored}


# ---------------------------------------------------------------- prompts

BUILD_RULES = """\
## Rules of this build (read before you start)
- **The checker is blind.** It runs the commands below and reads their output plus your evidence lines. It never sees your notes or reasoning. Prove each criterion with a test named `<ID>: <criterion>` (the criterion's own words) that **prints** what it proves, or a line a listed command prints.
- **Expected values come from the specification**, computed by hand or a separate small script, never by running the code under test.
- **Never weaken, skip or special-case a test** to make it pass. Never edit a command's text.
- **Write only the files you own** (plus your report, questions and change requests).
- **One request, all gaps.** Before writing any question or change request, scan every section you read for all gaps and put them in one file.
- **A finding names a class.** When you fix a mistake, find and fix every other instance of the same kind in your files, and test them.
- A choice only your own files see: decide it and note it in your report. A gap another task also depends on: write a question and reply `blocked`. A contract outside your files must change: write a change request and reply `blocked`. Before blocking on a name or shape another task owns, read that task's files; it may exist.
"""

REPLY_FORMAT = """\
## Reply
Max 15 lines of prose, then exactly one fenced JSON block:
```json
{"status": "done|blocked|failed", "summary": "<one paragraph>", "files": ["<changed paths>"],
 "evidence": ["<ID>: <criterion> -> <test name or printed line>"]}
```
Long notes go to `{report}`; end it with `Lesson: <rule>` if something cost you a retry.
"""


def build_prompt(plan: Plan, tid: str, attempt: int, feedback: str, reason: str) -> str:
    t = plan.tasks[tid]
    decisions, last = routed_decisions(plan, tid)
    slice_dir = plan.dir.parent
    deps_files = []
    for d in t.get("deps", []):
        if d in plan.tasks:
            deps_files += plan.tasks[d].get("owns", [])
    parts = [f"# Task {tid} {t['title']} (wave {t['wave']}, attempt {attempt} of 3)\n", BUILD_RULES]
    if t.get("reads"):
        parts.append("## Read (nothing else unless these point on)\n" + "\n".join(f"- {r}" for r in t["reads"]) + "\n")
    parts.append("## Decisions that name this task\n" + ("\n\n".join(decisions) if decisions else "None.") + "\n")
    if last:
        parts.append(f"The last decision given to you is {last}. If you hit a gap, first search the decision log "
                     f"(`{plan.decisions_path.name if plan.decisions_path else 'decisions.md'}`) for entries after {last}; "
                     "do not read the whole log.\n")
    if deps_files:
        parts.append("## Finished work you build on (read only what you import or call)\n"
                     + "\n".join(f"- {p}" for p in deps_files) + "\n")
    parts.append("## You own (the only files you may write)\n" + "\n".join(f"- {p}" for p in t["owns"]) + "\n")
    parts.append("## Criteria (each must be provable from command output)\n"
                 + "\n".join(f"- {tid}: {c}" for c in plan.check_criteria(t)) + "\n")
    rp = plan.review_points(t)
    if rp:
        parts.append("## A reviewer will also check\n" + "\n".join(f"- {c}" for c in rp) + "\n")
    if t.get("notes"):
        parts.append(f"## Notes\n{t['notes']}\n")
    parts.append("## Run before replying (the checker runs exactly these)\n"
                 + "\n".join(f"- `{c}`" for c in plan.check_commands(t)) + "\n")
    parts.append(f"## Questions and change requests\n"
                 f"- Question: `{slice_dir}/questions/{tid}-<n>.md` with: Question (one line); The specification says "
                 f"\"<quote>\" (<section>); Options A/B; My pick and why; Who else depends on it.\n"
                 f"- Change request: `{slice_dir}/change-requests/{tid}-<n>.md` with: The change (exact file, field, "
                 f"type or value); Why (the spec's words, and why nothing inside your files would do); All gaps found.\n")
    if reason:
        parts.append(f"## Why this task is being rebuilt\n{reason}\n")
    if attempt > 1 or feedback:
        parts.append("## Previous attempt\nThe files on disk are the previous attempt. Find the cause before you change "
                     "code. Never weaken, skip or special-case a test.\n\n" + (feedback or "") + "\n")
    parts.append(REPLY_FORMAT.replace("{report}", f"{slice_dir}/reports/{tid}.md"))
    return "\n".join(parts)


def check_prompt(plan: Plan, tid: str, evidence: list[str]) -> str:
    t = plan.tasks[tid]
    cmds = plan.check_commands(t)
    crit = plan.check_criteria(t)
    out = [f"# Check {tid} {t['title']}\n",
           "You are a blind checker. You cannot edit files. Run each command below **exactly as written**, in order, "
           "from the repo root, each to completion. Do not fix anything.\n",
           "## Commands\n" + "\n".join(f"{i + 1}. `{c}`" for i, c in enumerate(cmds)) + "\n",
           "## Criteria to confirm from that output\n" + "\n".join(f"- {tid}: {c}" for c in crit) + "\n"]
    if evidence:
        out.append("## Builder's evidence (claims to confirm, not facts)\n" + "\n".join(f"- {e}" for e in evidence) + "\n")
    out.append(
        "## Reply: only this JSON (under 4,000 characters)\n"
        "```json\n"
        '{"results": [{"command": "<exactly as written>", "exitCode": 0, "testsRun": 0, '
        '"output": "<the lines that matter, max 20>"}],\n'
        ' "missingCriteria": ["<copy the criterion text exactly>"]}\n'
        "```\n"
        "List a criterion as missing only by copying its text, and only when no passing test name or printed line "
        "shows it. Remarks about logs, unprinted exit codes, wrappers or files you were not given are not criteria; "
        "leave them out.\n")
    return "\n".join(out)


def review_prompt(plan: Plan, tid: str, earlier: str) -> str:
    t = plan.tasks[tid]
    out = [f"# Review {tid} {t['title']}\n",
           "You are a read-only reviewer. Compare the work with the specification, not with the builder's claims.\n"]
    if t.get("reads"):
        out.append("## Specification\n" + "\n".join(f"- {r}" for r in t["reads"]) + "\n")
    out.append("## Owned files\n" + "\n".join(f"- {p}" for p in t["owns"]) + "\n")
    out.append("## Criteria\n" + "\n".join(f"- {c}" for c in t["criteria"]) + "\n")
    if earlier:
        out.append("## Earlier review\nRead only `git diff` of the owned files since the earlier review. Earlier "
                   "findings:\n" + earlier + "\n")
    else:
        out.append("Read the owned files whole.\n")
    out.append(
        "## Blocking means\nA wrong result; a missing requirement; a test that does not test what its name says; a "
        "value special-cased to pass; a write outside the owned files. Style is not blocking.\n\n"
        "Name the **class** of each mistake and list every other instance of it you can see.\n\n"
        "## Reply: only this JSON\n```json\n"
        '{"blocking": [{"file": "<path:line>", "class": "<kind of mistake>", "what": "<wrong>", '
        '"expected": "<per spec>", "others": ["<path:line>"]}], "summary": "<one line>"}\n```\n')
    return "\n".join(out)


# ---------------------------------------------------------------- status


def chain_below(plan: Plan) -> dict[str, int]:
    """Longest chain of dependents below each id (critical-path priority)."""
    rdeps: dict[str, list[str]] = {}
    for tid, t in plan.tasks.items():
        for d in t.get("deps", []):
            rdeps.setdefault(d, []).append(tid)
    for gid, g in plan.gates.items():
        for a in g.get("after", []):
            rdeps.setdefault(a, []).append(gid)
    memo: dict[str, int] = {}

    def depth(n: str, seen=()) -> int:
        if n in memo:
            return memo[n]
        if n in seen:
            return 0
        memo[n] = 1 + max((depth(c, seen + (n,)) for c in rdeps.get(n, [])), default=0)
        return memo[n]

    return {i: depth(i) for i in list(plan.tasks) + list(plan.gates)}


def status(plan: Plan) -> dict:
    st = plan.state()
    done = {i for i, ev in st.items() if ev["event"] == "passed"}
    prio = chain_below(plan)
    rows = {"done": [], "running": [], "ready": [], "waiting": [], "blocked": [], "failed": []}
    for tid, t in plan.tasks.items():
        ev = st.get(tid, {}).get("event")
        if ev == "passed":
            rows["done"].append(tid)
        elif ev == "blocked":
            rows["blocked"].append(tid)
        elif ev == "failed":
            rows["failed"].append(tid)
        elif ev == "started":
            rows["running"].append(tid)
        elif all(d in done for d in t.get("deps", [])):
            rows["ready"].append(tid)
        else:
            rows["waiting"].append(tid)
    rows["ready"].sort(key=lambda i: -prio.get(i, 0))
    gates = {}
    for gid, g in plan.gates.items():
        gates[gid] = "passed" if gid in done else ("ready" if all(a in done for a in g.get("after", [])) else "waiting")
    longest = max(prio.values(), default=0)
    return {"tasks": rows, "gates": gates, "criticalPath": longest,
            "counts": {k: len(v) for k, v in rows.items()}}


# ---------------------------------------------------------------- cli


def ladder(plan: Plan, tid: str, attempt: int) -> dict:
    t = plan.tasks[tid]
    model, effort = t.get("model", "haiku"), t.get("effort", "medium")
    if attempt <= 1:
        return {"subagent_type": t["agent"], "model": model, "effort": effort}
    if attempt == 2:
        return {"subagent_type": t["agent"], "model": MODEL_UP[model],
                "effort": EFFORT_UP[effort] if MODEL_UP[model] == model else effort}
    return {"subagent_type": t.get("escalation", t["agent"]), **{**ESCALATION, **plan.config.get("escalation", {})}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="plan.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("lint"); s.add_argument("plan"); s.add_argument("--agents", help="dir of agent .md files")
    s = sub.add_parser("status"); s.add_argument("plan"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("ladder"); s.add_argument("plan"); s.add_argument("id"); s.add_argument("attempt", type=int)
    s = sub.add_parser("prompt"); s.add_argument("plan"); s.add_argument("kind", choices=("build", "check", "review"))
    s.add_argument("id"); s.add_argument("--attempt", type=int, default=1); s.add_argument("--feedback")
    s.add_argument("--reason", default=""); s.add_argument("--evidence", help="JSON file: the builder's reply")
    s.add_argument("--earlier", help="file with the earlier review's findings")
    s = sub.add_parser("judge"); s.add_argument("plan"); s.add_argument("id"); s.add_argument("check")
    s = sub.add_parser("record"); s.add_argument("plan"); s.add_argument("id"); s.add_argument("event", choices=EVENTS)
    s.add_argument("--attempt", type=int, default=1); s.add_argument("--model", default=""); s.add_argument("--note", default="")
    s = sub.add_parser("decisions"); s.add_argument("plan"); s.add_argument("id")
    a = ap.parse_args(argv)
    plan = load(a.plan)

    if a.cmd == "lint":
        errors, warnings = lint(plan, Path(a.agents) if a.agents else None)
        for w in warnings:
            print(f"warning: {w}")
        for e in errors:
            print(f"error: {e}")
        print(f"plan lint: {len(plan.tasks)} tasks, {len(plan.gates)} gates, "
              f"{len(errors)} errors, {len(warnings)} warnings")
        return 1 if errors else 0

    if a.cmd != "status" and a.id not in plan.tasks and a.id not in plan.gates:
        sys.exit(f"plan.py: unknown id {a.id}")

    if a.cmd == "status":
        r = status(plan)
        if a.json:
            print(json.dumps(r, indent=2))
        else:
            for k, v in r["tasks"].items():
                print(f"{k:8} {len(v):3}  {' '.join(v)}")
            print("gates    " + "  ".join(f"{g}:{s}" for g, s in r["gates"].items()))
            print(f"critical path: {r['criticalPath']} steps")
        return 0
    if a.cmd == "ladder":
        print(json.dumps(ladder(plan, a.id, a.attempt)))
        return 0
    if a.cmd == "decisions":
        entries, last = routed_decisions(plan, a.id)
        print("\n\n".join(entries) if entries else f"no decision names {a.id}")
        print(f"\n(last entry in the log: {last or 'none'})")
        return 0
    if a.cmd == "prompt":
        if a.kind == "build":
            fb = Path(a.feedback).read_text() if a.feedback else ""
            print(build_prompt(plan, a.id, a.attempt, fb, a.reason))
        elif a.kind == "check":
            ev = []
            if a.evidence:
                ev = json.loads(Path(a.evidence).read_text()).get("evidence", [])
            print(check_prompt(plan, a.id, ev))
        else:
            print(review_prompt(plan, a.id, Path(a.earlier).read_text() if a.earlier else ""))
        return 0
    if a.cmd == "judge":
        raw = sys.stdin.read() if a.check == "-" else Path(a.check).read_text()
        m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.S)
        try:
            check = json.loads(m.group(1) if m else raw)
        except json.JSONDecodeError:
            check = None
        t = plan.tasks[a.id]
        v = judge(plan.check_commands(t), check, plan.check_criteria(t), plan.test_pattern())
        print(json.dumps({"id": a.id, "verdict": "PASS" if v["ok"] else "FAIL", **v}, indent=2))
        return 0 if v["ok"] else 1
    if a.cmd == "record":
        ev = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), "id": a.id, "event": a.event,
              "attempt": a.attempt, "model": a.model, "note": _clip(a.note, 600)}
        with plan.journal_path.open("a") as f:
            f.write(json.dumps(ev) + "\n")
        print(json.dumps(ev))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
