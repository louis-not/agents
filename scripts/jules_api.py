#!/usr/bin/env python3
"""Thin wrapper over the Jules REST API (v1alpha) for the jules-delegation skill.

The key is read from $JULES_API_KEY or ~/.config/jules/api_key (never printed).

  jules_api.py new  --repo OWNER/REPO --branch BR --title T --prompt-file F [--plan-approval]
  jules_api.py get  SESSION_ID          # state, title, PR url and branch if any
  jules_api.py acts SESSION_ID [N]      # last N activities (default 8), one line each
  jules_api.py send SESSION_ID --prompt-file F
  jules_api.py approve SESSION_ID
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://jules.googleapis.com/v1alpha"


def _key() -> str:
    key = os.environ.get("JULES_API_KEY") or ""
    if not key:
        path = Path.home() / ".config" / "jules" / "api_key"
        if path.exists():
            key = path.read_text().strip()
    if not key:
        sys.exit("no Jules API key: set JULES_API_KEY or write ~/.config/jules/api_key")
    return key


def _call(method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{BASE}/{path}",
        data=data,
        method=method,
        headers={"x-goog-api-key": _key(), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode()
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code}: {e.read().decode()[:500]}")
    return json.loads(raw) if raw.strip() else {}


def _sid(value: str) -> str:
    return value if value.startswith("sessions/") else f"sessions/{value}"


def cmd_new(a: argparse.Namespace) -> None:
    body = {
        "prompt": Path(a.prompt_file).read_text(),
        "title": a.title,
        "sourceContext": {
            "source": f"sources/github/{a.repo}",
            "githubRepoContext": {"startingBranch": a.branch},
        },
        "automationMode": "AUTO_CREATE_PR",
        "requirePlanApproval": a.plan_approval,
    }
    s = _call("POST", "sessions", body)
    print(json.dumps({"id": s.get("id"), "name": s.get("name"), "url": s.get("url")}))


def cmd_get(a: argparse.Namespace) -> None:
    s = _call("GET", _sid(a.session))
    prs = [o["pullRequest"] for o in s.get("outputs", []) if "pullRequest" in o]
    print(json.dumps({"state": s.get("state"), "title": s.get("title"), "prs": prs}, indent=1))


def cmd_acts(a: argparse.Namespace) -> None:
    acts = _call("GET", f"{_sid(a.session)}/activities?pageSize=100").get("activities", [])
    for act in acts[-a.n :]:
        kind = next((k for k in act if k not in {"name", "id", "createTime", "originator", "artifacts"}), "?")
        detail = json.dumps(act.get(kind))[:240]
        print(f"{act.get('createTime', '')[:19]} {act.get('originator', '?'):6} {kind}: {detail}")


def cmd_send(a: argparse.Namespace) -> None:
    _call("POST", f"{_sid(a.session)}:sendMessage", {"prompt": Path(a.prompt_file).read_text()})
    print("sent")


def cmd_approve(a: argparse.Namespace) -> None:
    _call("POST", f"{_sid(a.session)}:approvePlan", {})
    print("approved")


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new")
    n.add_argument("--repo", required=True)
    n.add_argument("--branch", required=True)
    n.add_argument("--title", required=True)
    n.add_argument("--prompt-file", required=True)
    n.add_argument("--plan-approval", action="store_true")
    n.set_defaults(fn=cmd_new)
    g = sub.add_parser("get")
    g.add_argument("session")
    g.set_defaults(fn=cmd_get)
    ac = sub.add_parser("acts")
    ac.add_argument("session")
    ac.add_argument("n", nargs="?", type=int, default=8)
    ac.set_defaults(fn=cmd_acts)
    s = sub.add_parser("send")
    s.add_argument("session")
    s.add_argument("--prompt-file", required=True)
    s.set_defaults(fn=cmd_send)
    ap = sub.add_parser("approve")
    ap.add_argument("session")
    ap.set_defaults(fn=cmd_approve)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
