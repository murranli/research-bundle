# Research Bundle

Agent Skills for turning a loose research question into a traceable report.

This repository contains an **agent-runtime-neutral skill bundle** for structured desktop research: intent framing, question decomposition, search planning, retrieval execution, evidence audit, report composition, HTML/PDF rendering, and workflow review.

It provides the skill instructions and local state contract only. You choose the runtime agent, model, browser, and retrieval providers.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/install.sh | bash
```

The installer auto-detects common Agent Skills directories, including Codex and Claude Code personal skills folders, and installs the bundle into every directory it finds.

For an explicit target:

```bash
curl -fsSL https://raw.githubusercontent.com/murranli/research-bundle/main/install.sh | bash -s -- --target "$HOME/.claude/skills"
```

After installation, start your agent and ask it to use `entropy-research`, for example:

```text
Use entropy-research to evaluate whether Xiaohongshu has a product opportunity in local-life search and decision-making.
```

## What Gets Installed

```text
entropy-research/      main orchestrator
goal-decompose/        intent and sub-question decomposition
search-strategy/       channel-aware search planning
retrieval-exec/        retrieval execution recordkeeping
content-audit/         evidence sufficiency and gap audit
report-compose/        report structure and claims
report-render/         HTML report rendering
review-deliver/        workflow review and final deliverables
_shared/               state contract and helper scripts
```

The skills communicate through a local `.entropy/<run_id>/` state directory in the workspace where the agent is running.

## Runtime Notes

- Python 3 is required for the helper scripts.
- Retrieval is provider-agnostic at the skill level. The current command hints are compatible with Agent-Reach-style channels, but users may adapt them to their own tooling.
- No account cookies, API keys, login state, or retrieval credentials are included.
- Local run outputs are ignored by git via `.entropy/`. Share only sanitized examples or final reports you intentionally review.

## Repository Layout

```text
install.sh
entropy-research-bundle/
  README.md
  _shared/
  entropy-research/
  goal-decompose/
  search-strategy/
  retrieval-exec/
  content-audit/
  report-compose/
  report-render/
  review-deliver/
  examples/
```

## Security

Treat every third-party skill bundle as executable instructions. Review `SKILL.md` files and helper scripts before installation, especially when an agent can run shell commands.

Before making a fork public, scan for credentials and remove local `.entropy/` runs.

See [SECURITY.md](SECURITY.md).
