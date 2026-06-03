# Human Docs

This folder is the human-readable documentation surface beyond the root
`README.md`, `ARCHITECTURE.md`, and `STATUS.md`.

AI agents should also read these docs when they need human-facing context.

## Read First

- [Domain vocabulary](domain.md)
- [Contributing](contributing.md)
- [UT and CI design](ut_ci_design.md)
- [Agent/task command taxonomy](agent-task-command-taxonomy.md)
- [Skill-first MCP architecture](mcp-skills-and-semantic-profiles.md)
- [Architecture hygiene review](architecture-hygiene-review.md)
- [Technical design](technical-design.md)
- [MolmoSpaces settings](molmospaces-settings.md)
- [MolmoSpaces visual grounding results](molmospaces-visual-grounding-results.md)
- [MolmoSpaces cleanup profile architecture](molmospaces-cleanup-mode-architecture.md)
- [Model matrix](model-matrix.md)

## Runbooks

- [Local runtime reference](local-runtime.md)
- [Direct Codex/Claude robot driver](coding-agent-nav-server.md)
- [Agibot G2 Codex A Acceptance](agibot-g2-codex-a-acceptance.md)
- [Agibot G2 Cleanup Pilot](agibot-g2-cleanup-pilot.md)
- [Real Robot Nav2 Cleanup Pilot](real-robot-nav2-cleanup-pilot.md)
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
