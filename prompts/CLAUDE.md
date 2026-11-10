# Global instructions

Loaded in every Claude Code session on this machine. Project-level `CLAUDE.md` files override anything here.

## About me
- I build AI agents, chatbots, scrapers, dashboards and Android apps, mostly for Ismaya Group projects (SML, BangkaX, Virality Engine, Echo, Nexus, Holocron).
- Repos live in `~/Repositories`. Android projects live in `~/AndroidStudioProjects`.

## Environment
- Linux, bash. Tools available: Python 3 (miniconda), Node, Java, Docker, git, `gh`.
- Python: use the project's venv or conda env if it has one. Don't install packages globally.

## How to work with me
- Keep answers short and direct. Skip long preambles and recaps.
- For a bug, find and explain the root cause first, then fix it.
- Make the smallest change that solves the problem and match the existing code style. Don't refactor or add features I didn't ask for.
- Run the relevant tests or build after a change and tell me the real result, including failures.
- In UI work, keep on-screen text minimal. Prefer tooltips and progressive disclosure over walls of text.

## Orchestration
Work in three tiers (main session Opus → `head-orchestrator` agents on Sonnet → executor agents on Haiku or Sonnet). Roles and procedures live in `~/Repositories/nexus-workspace/agents/`.

If you are the main session and the task is bigger than a small fix, load the `orchestrate` skill first. Subagents: follow your agent file and task.

## Git and releases
- Ask before you push, merge, force-push, tag, create a release or deploy, unless I've said to do it in this conversation.
- "Apply to main" doesn't mean "create a release".
- Never commit secrets, `.env` files, keystores or credentials.

## Safety
- Ask before running destructive commands (`rm -rf`, dropping DBs, `docker system prune`, `kubectl delete`, and similar).
- Treat production systems as read-only unless I explicitly say otherwise.
