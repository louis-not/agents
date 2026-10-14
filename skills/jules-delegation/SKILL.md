---
name: jules-delegation
description: >-
  Hands a self-contained module to a Jules session (Google's async GitHub coding agent), then
  reviews and merges the PR it opens. Use as the main orchestrator when a module can be built and
  tested from a GitHub clone alone. Covers the git and PR rules for the whole loop. Not for
  modules that need local services, secrets or uncommitted code.
---

# Jules Delegation

Jules runs in a cloud VM on a fresh clone from GitHub and opens its own branch and PR. Local executors never touch git; Jules always does. The rules below keep the two from colliding.

## 0. Is the module a fit?
Use Jules only if all hold:
- Self-contained: builds and tests from a clean clone, no local infra, no `.env` secrets.
- Contracts to other modules are frozen and written down.
- Big enough to justify a VM boot (a module, not a one-line fix).

Otherwise use `backlog-delegation` with local executors.

## 1. Prepare git (before dispatching)
Jules only sees what is on GitHub. Local or unpushed work is invisible.
1. Check `git remote -v` and `gh auth status`. The repo must be on GitHub with the Jules app installed.
2. Create one integration branch per feature from the up-to-date default branch: `feat/<slug>`.
3. Commit the frozen contracts, interfaces, test stubs and the repo's `AGENTS.md` to that branch and push it. **Ask the user before pushing**, unless they already said to in this conversation.
4. Make sure each module owns disjoint files. Two parallel Jules sessions never share a file.
5. Check `AGENTS.md` at the repo root has the build and test commands, the coding standards and "touch only your module's files". Start from [AGENTS-template.md](./AGENTS-template.md) if missing.

## 2. Dispatch
One session per module:
- `sourceContext.githubRepoContext.startingBranch` = the integration branch, never the default branch.
- `automationMode: AUTO_CREATE_PR` so Jules opens the PR itself.
- `requirePlanApproval: true` for risky or unclear modules, `false` for routine ones.
- Prompt = a Jules prompt from `agents/prompts/` with its Brief section filled in (goal, owned files, contracts, "Done when" checks, the exact test command). The prompt text is pasted whole, because Jules can't read files outside the repo:

  | Job | Prompt |
  |---|---|
  | Own and build a whole module (default) | `head-orchestrator.jules.md` |
  | One small, bounded item | `executor.jules.md` |
  | Write and run tests on someone else's branch | `tester.jules.md` |
  | Address review findings on an existing PR | `fixer.jules.md` |
  | Find a root cause without fixing it | `troubleshooter.jules.md` |
- **Never put secrets, tokens or production URLs in the prompt.**
- Record the session ID, module, branch and time in `.agents/jules-sessions.json` so you can poll and resume.

Jules picks its own branch name, so don't rely on one. Find it from the session or the PR. Confirm in the first pilot that the PR base equals the starting branch.

## 3. Watch
- Poll the session's activities. Don't loop tightly.
- Plan awaiting approval: read it against the brief, then `approvePlan`, or `sendMessage` with corrections.
- Jules asks a question: answer with `sendMessage`.

## 4. Review the PR
```bash
gh pr list --state open
gh pr checkout <n>
gh pr diff <n>
```
Run `code-standards-gate` on the diff against the integration branch (`git diff origin/feat/<slug>...HEAD`), plus the module's tests locally where possible.
- Files changed outside the module's owned paths: REJECT.
- Secrets, `.env`, keystores or generated junk in the diff: REJECT.
- ACCEPT: If the PR was created on behalf of the same user who owns the token/session, GitHub blocks approving your own PR via API (`Can not approve your own pull request`). In that case, leave an approving comment (`gh pr comment <n> --body "ACCEPT: ..."`), or directly merge with `gh pr merge <n> --merge --delete-branch`.
- REJECT: write specific findings. While the session is still active, send them with `sendMessage` (or `python3 agents/scripts/jules_api.py send <session_id> --prompt-file <file>`) and do not push to Jules's branch yourself, because that causes conflicts. If the session has finished, comment on the PR with `gh pr comment <n>`, and either start a follow-up session on that PR branch or fix it yourself and say so.

## 5. Merge
- Ask the user before merging, unless they said to in this conversation.
- Merge accepted PRs into the **integration branch only**, one at a time. After each merge, the next PR must be updated against the new tip (`gh pr checkout`, `git merge origin/feat/<slug>`) and its tests re-run.
- Never force-push. Never rewrite Jules's branch history.
- Follow the repo's merge style and commit message convention.
- Run `e2e-verify` on the integration branch once all modules are in.
- Merging `feat/<slug>` to the default branch, tagging and releasing are the user's call. "Apply to main" does not mean "create a release".

## 6. Clean up
Delete merged Jules branches only after the user agrees. Update `.agents/jules-sessions.json`.
