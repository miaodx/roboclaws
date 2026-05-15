# Human Docs

This folder is the human-readable documentation surface beyond the root
`README.md`, `ARCHITECTURE.md`, and `STATUS.md`.

AI agents should also read these docs when they need human-facing context.

## Read First

- [Domain vocabulary](domain.md)
- [Contributing](contributing.md)
- [Agent/task command taxonomy](agent-task-command-taxonomy.md)
- [Skill-first MCP architecture](mcp-skills-and-semantic-profiles.md)
- [Technical design](technical-design.md)
- [MolmoSpaces settings](molmospaces-settings.md)
- [MolmoSpaces cleanup profile architecture](molmospaces-cleanup-mode-architecture.md)
- [Model matrix](model-matrix.md)

## Runbooks

- [Direct Codex/Claude robot driver](coding-agent-nav-server.md)
- [OpenClaw demo](openclaw/demo.md)
- [OpenClaw local development](openclaw/local.md)
- [OpenClaw Gateway internals](openclaw/gateway-internals.md)
- [Railway deploy](railway/deploy.md)
- [Railway appliance plan](railway/appliance-plan.md)

## AI-Agent Docs

Other `docs/` folders are still useful to agents, but they are not the normal
human review surface:

- `docs/adr/` - durable decision records
- `docs/plans/` - pre-GSD plans and generated planning detail
- `docs/retrospectives/` - shipped history
- `docs/status/active/` - parallel work notes
- `docs/ai/` - implementation evidence, experiments, and agent-only runbooks
