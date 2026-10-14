# AGENTS.md (template for repos Jules works on)

Copy to the repo root and fill in. Jules reads it on every session.

## Project
<one line: what this repo is, main stack>

## Setup and checks
- Install: `<command>`
- Test: `<command>`
- Lint and typecheck: `<command>`
- All three must pass before you finish. Report the real output.

## Rules
- Touch only the files and paths named in your task. If you need a change elsewhere, stop and say so in the PR description.
- Don't change the contracts (interfaces, schemas, API shapes) listed in your task.
- Follow the existing code style. No refactors or features that weren't asked for.
- Never commit secrets, `.env` files, keystores or credentials.
- Don't force-push or rewrite history.

## Git
- Branch from the starting branch you were given. Open the PR against it, not the default branch.
- Commit messages: <repo convention, e.g. `feat(scope): summary`>.
- PR description: what changed, which "Done when" checks you ran with results, and anything left undone.
