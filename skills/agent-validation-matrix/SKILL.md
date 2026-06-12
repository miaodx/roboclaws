---
name: agent-validation-matrix
description: Select and run relevant Roboclaws validation gates from a plan, diff, or explicit axes.
---

# Agent Validation Matrix

Use this skill when a Roboclaws plan, diff, or agent-facing change needs an
auditable validation matrix. The skill selects deterministic, product,
live-agent, Agent SDK, perception, simulator, and map/cleanup-consumer gates
from explicit source signals. It is a validation orchestrator, not a robot
behavior skill.

Keep task strategy in task skills such as `molmo-realworld-cleanup`. Keep robot
capability semantics in MCP tools and profile contracts. This skill only
answers:

1. which gates are relevant;
2. why each gate was selected, skipped, run, or blocked;
3. where the resulting evidence lives.

## Commands

Recommend a matrix without running commands:

```bash
just agent::harness agent-validation recommend \
  plan=docs/plans/example.md \
  budget=focused
```

Execute the relevant gates for a plan or diff:

```bash
just agent::harness agent-validation execute \
  plan=docs/plans/example.md \
  budget=focused
```

Diff-based selection:

```bash
just agent::harness agent-validation execute since=origin/main budget=focused
```

Explicit axis overrides:

```bash
just agent::harness agent-validation recommend \
  agent_engine=codex-cli,openai-agents-sdk \
  provider_profile=codex-env \
  evidence_lane=camera-grounded-labels \
  camera_labeler=grounding-dino
```

## Budgets

- `smoke`: deterministic confidence only; relevant expensive gates are recorded
  as skipped by user budget.
- `focused`: required deterministic gates plus the smallest relevant product or
  live gates.
- `full`: broader selected matrix for comparison work.

Do not skip an expensive gate because it is expensive. Skip it only when it is
irrelevant, impossible in the current environment, blocked by network/key/
hardware/runtime, or explicitly budget-capped by the user.

## Outputs

Each run writes:

```text
output/agent-validation-matrix/<stamp>/
  validation_matrix.json
  validation_matrix.md
  validation_matrix.html
  gates/<gate-id>/
```

Every gate records its command, axes, source signals, selection rationale,
status, blocker category when blocked, and artifacts or logs when available.

## Selection Rules

The selector is deterministic. It uses rule tables over plan text, git diff
paths, and explicit overrides. It does not use an LLM classifier.

Important signals:

- Agent SDK files select `agent_engine=openai-agents-sdk` gates.
- Cleanup skill, prompt, or routine files select live coding-agent cleanup gates
  and cleanup contract checks.
- MCP server, `done` readiness, checker, and report contract files select
  MCP/checker contract tests plus an affected product row.
- Visual grounding, DINO, and camera labeler files select camera-grounded
  gates including `camera_labeler=grounding-dino`.
- RAW-FPV files select `evidence_lane=camera-raw-fpv` gates.
- Runtime Metric Map, semantic map, actionability, and waypoint files select
  map-build gates plus a cleanup consumer prior gate.
- Launch catalog, provider profile, and operator-console route files select
  route trace tests plus a representative product launch gate.

The retired `codex-cleanup-harness8` route is not supported. Equivalent Codex
cleanup gates may appear only as selected rows in an `agent-validation` manifest
when the current plan, diff, or override requires them.
