# Claude Guide

Roboclaws is a household robot demo repo with MCP tools, reusable skills, and
SDK/direct runtimes. Python 3.12+.

`AGENTS.md` is the canonical repo-wide playbook. Follow it first.

## Claude-Specific Notes

- Treat `AGENTS.md` as shared repo guidance; keep this file to Claude-only
  deltas.
- Do not duplicate long setup, command, or workflow sections here. Add durable
  repo-specific agent procedures under `docs/agents/**` and keep human project
  truth in `README.md`, `ARCHITECTURE.md`, `STATUS.md`, and `docs/human/**`.
- Claude Code native subagents are acceptable when the host supports them
  reliably and file ownership is explicit.
