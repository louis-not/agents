#!/usr/bin/env python3
"""Self-tests for plan.py. No agents, no network. Run after every edit of plan.py:

    python3 -m unittest discover -s ~/Repositories/nexus-workspace/agents/scripts -p 'test_plan.py'
"""
import json
import re
import tempfile
import unittest
from pathlib import Path

import plan as P

TEST_RE = re.compile(P.DEFAULT_TEST_PATTERN)
CMDS = ["npm run build", "npx vitest run test/pricing.test.ts"]
CRIT = ["the quote for the reference basket is 1,284.50 ± 0.01", "prices are never negative for any generated input"]


def ok_result():
    return {"results": [{"command": "npm run build", "exitCode": 0, "output": "built"},
                        {"command": "npx vitest run test/pricing.test.ts", "exitCode": 0, "testsRun": 4,
                         "output": "M03: the quote ... 1284.50"}],
            "missingCriteria": []}


class Judge(unittest.TestCase):
    def test_clean_check_passes(self):
        self.assertTrue(P.judge(CMDS, ok_result(), CRIT, TEST_RE)["ok"])

    def test_noise_remark_is_ignored_and_logged(self):
        r = ok_result(); r["missingCriteria"] = ["the exit code was not echoed in stdout"]
        v = P.judge(CMDS, r, CRIT, TEST_RE)
        self.assertTrue(v["ok"]); self.assertEqual(len(v["ignored"]), 1)

    def test_unconfirmed_criterion_fails(self):
        r = ok_result(); r["missingCriteria"] = [CRIT[1]]
        v = P.judge(CMDS, r, CRIT, TEST_RE)
        self.assertFalse(v["ok"]); self.assertIn("never negative", v["why"])

    def test_noise_word_naming_a_criterion_is_real(self):
        r = ok_result(); r["missingCriteria"] = ["log shows nothing about prices never negative generated input"]
        self.assertFalse(P.judge(CMDS, r, CRIT, TEST_RE)["ok"])

    def test_unreported_command_fails(self):
        r = ok_result(); r["results"].pop(0)
        self.assertIn("not run or not reported: npm run build", P.judge(CMDS, r, CRIT, TEST_RE)["why"])

    def test_quotes_and_spaces_do_not_matter(self):
        r = ok_result(); r["results"][0]["command"] = "npm  run  'build'"
        self.assertTrue(P.judge(CMDS, r, CRIT, TEST_RE)["ok"])

    def test_nonzero_exit_fails(self):
        r = ok_result(); r["results"][0]["exitCode"] = 2
        self.assertFalse(P.judge(CMDS, r, CRIT, TEST_RE)["ok"])

    def test_test_command_with_zero_tests_fails(self):
        r = ok_result(); r["results"][1]["testsRun"] = 0
        self.assertIn("ran no tests", P.judge(CMDS, r, CRIT, TEST_RE)["why"])

    def test_missing_results_fails(self):
        self.assertFalse(P.judge(CMDS, None, CRIT, TEST_RE)["ok"])


def write_plan(tmp: Path, tasks, gates=(), decisions=""):
    d = tmp / "019-x" / "plan"; d.mkdir(parents=True)
    (d / "config.json").write_text(json.dumps({"repo": "../..", "defaultCommands": ["npx tsc --noEmit"]}))
    (d / "main.json").write_text(json.dumps({"tasks": list(tasks), "gates": list(gates)}))
    if decisions:
        (tmp / "019-x" / "019-integration-log.md").write_text(decisions)
    return P.Plan(d)


def task(i, **kw):
    t = {"id": i, "title": "t " + i, "wave": "A", "agent": "software-developer", "model": "haiku",
         "deps": [], "owns": [f"src/{i}.ts"], "criteria": [f"{i}: answers 409 SLOT_TAKEN"],
         "commands": ["npx vitest run"]}
    t.update(kw)
    return t


class Lint(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def errors(self, *tasks, gates=(), decisions=""):
        return P.lint(write_plan(self.tmp, tasks, gates, decisions))[0]

    def test_good_plan_is_clean(self):
        self.assertEqual(self.errors(task("M01"), task("M02", deps=["M01"])), [])

    def test_echo_suffix_refused(self):
        self.assertTrue(any("suffix" in e for e in self.errors(task("M01", commands=["npm test; echo $?"]))))

    def test_reviewer_clause_without_prefix_refused(self):
        e = self.errors(task("M01", criteria=["the reviewer checks the numbers"]))
        self.assertTrue(any("without the 'review: ' prefix" in x for x in e))

    def test_review_prefix_needs_review_true(self):
        e = self.errors(task("M01", criteria=["answers 404", "review: wording matches"]))
        self.assertTrue(any("review is not true" in x for x in e))

    def test_two_owners_refused(self):
        e = self.errors(task("M01", owns=["src/a/**"]), task("M02", owns=["src/a/b.ts"]))
        self.assertTrue(any("two owners" in x for x in e))

    def test_cycle_and_unknown_dep_refused(self):
        e = self.errors(task("M01", deps=["M02"]), task("M02", deps=["M01"]), task("M03", deps=["Z9"]))
        self.assertTrue(any("cycle" in x for x in e)); self.assertTrue(any("unknown dependency Z9" in x for x in e))

    def test_max_effort_and_bad_model_refused(self):
        e = self.errors(task("M01", effort="max", model="gpt"))
        self.assertTrue(any("effort" in x for x in e)); self.assertTrue(any("model" in x for x in e))

    def test_decision_without_routing_line_refused(self):
        e = self.errors(task("M01"), decisions="### R1 M01: a question\n**Answer.** yes\n")
        self.assertTrue(any("Applies to" in x for x in e))


class Routing(unittest.TestCase):
    def test_only_named_decisions_reach_a_task(self):
        tmp = Path(tempfile.mkdtemp())
        log = ("## Track entries\nstuff\n"
               "### R1 M01: does cancel free the slot?\n**Answer.** No.\n**Applies to:** M01, M05\n"
               "### R2 M02: page size?\n**Answer.** 50.\n**Applies to:** M02\n")
        p = write_plan(tmp, [task("M01"), task("M02"), task("M05")], decisions=log)
        e5, last = P.routed_decisions(p, "M05")
        self.assertEqual(len(e5), 1); self.assertIn("R1", e5[0]); self.assertEqual(last, "R2")
        prompt = P.build_prompt(p, "M05", 1, "", "")
        self.assertIn("R1", prompt); self.assertNotIn("page size", prompt)
        self.assertIn("checker is blind", prompt); self.assertIn("names a class", prompt)
        self.assertIn("after R2", prompt)

    def test_retry_prompt_carries_feedback(self):
        p = write_plan(Path(tempfile.mkdtemp()), [task("M01")])
        s = P.build_prompt(p, "M01", 2, "npx vitest run exited 1: boom", "")
        self.assertIn("boom", s); self.assertIn("Find the cause", s)


class LadderAndStatus(unittest.TestCase):
    def test_ladder(self):
        p = write_plan(Path(tempfile.mkdtemp()), [task("M01", effort="medium")])
        self.assertEqual(P.ladder(p, "M01", 1)["model"], "haiku")
        self.assertEqual(P.ladder(p, "M01", 2)["model"], "sonnet")
        self.assertEqual(P.ladder(p, "M01", 3), {"subagent_type": "software-developer", "model": "opus", "effort": "high"})

    def test_status_orders_ready_by_longest_chain(self):
        p = write_plan(Path(tempfile.mkdtemp()),
                       [task("M01"), task("M02"), task("M03", deps=["M02"]), task("M04", deps=["M03"])])
        P.main(["record", str(p.dir), "M01", "passed"])
        s = P.status(p)
        self.assertEqual(s["tasks"]["done"], ["M01"])
        self.assertEqual(s["tasks"]["ready"][0], "M02")
        self.assertEqual(s["criticalPath"], 3)


if __name__ == "__main__":
    unittest.main()
