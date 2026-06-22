# Plans

`docs/plans/` holds pre-GSD plans, refactor scopes, design probes, and
implementation handoff documents. Plans answer what should change, what is out
of scope, how work should be sequenced, and which gates or artifacts define
done.

Plans are not ADRs. If a task also makes a durable public contract, safety,
private-data, MCP/tool, command-surface, or architecture-layer decision, create
a short ADR in `docs/adr/` and link it from the plan. Keep execution details in
the plan.

For agent-facing implementation plans, prefer an eval-harness section
that starts with:

```bash
just agent::eval recommend plan=docs/plans/<plan>.md budget=focused
just agent::eval execute plan=docs/plans/<plan>.md budget=focused
```

Add explicit overrides only when the plan already knows a required axis such as
`agent_engine=...`, `evidence_lane=...`, or `camera_labeler=...`.

## Naming

For new plan files, use a date-prefixed slug:

```text
YYYY-MM-DD-short-topic.md
```

Example:

```text
2026-06-11-target-search-actionability.md
```

Do not bulk-rename existing plans just to add dates. When touching an older
plan, add or refresh its header metadata instead:

```text
**Status:** Proposed | Active | Implemented | Superseded | Parked
**Created:** YYYY-MM-DD
**Last reviewed:** YYYY-MM-DD
**Current implementation contract:** ...
**Related ADRs:** ...
**Supersedes / Superseded by:** ...
```

## Current Index

Use root `STATUS.md` for the current project focus and human review links.
This directory is intentionally searchable instead of hand-indexed; long
curated lists drift faster than the plans do.

Useful searches:

```bash
rg -n "^\\*\\*Status:\\*\\*" docs/plans
rg -n "surface=household-world|agent::eval|runtime_map_prior" docs/plans
```

Retirement records and superseded proposals stay here as history. They are not
current implementation guidance unless `STATUS.md`, `ARCHITECTURE.md`, or a
new active plan explicitly promotes them.
