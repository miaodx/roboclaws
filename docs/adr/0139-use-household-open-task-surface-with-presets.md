# ADR-0139: Use Household Open Task Surface With Presets

Status: Accepted

Date: 2026-06-12

## Context

ADR-0136 made `intent=open-ended` first-class so open household goals no longer
used cleanup-specific custom-mode language. That was a useful intermediate
state, but it still left `cleanup`, `map-build`, and `open-ended` as peer
public household intents. Operators and agents still had to understand why a
natural-language household task was an "intent" beside repeated benchmark jobs.

The next product direction is simpler: `surface=household-world` should select
the household open-task contract by default. Standard repeated jobs such as
cleanup and map-build should be optional presets layered over that surface.

## Decision

Use `surface=household-world prompt=...` as the public no-preset household
open-task route. It lowers internally to `task_intent=open-ended`, uses the
`household-open-task` skill, requires household world and episode capabilities,
and relies on agent-declared completion with public evidence.

Use `preset=cleanup` and `preset=map-build` for current standard household
jobs. Preset rows own the default skill, required capabilities, default scenario
setup, report profile, and validation gate tags:

- `preset=cleanup` selects cleanup skill behavior, manipulation capabilities,
  relocation setup, cleanup scoring, and cleanup report/checker gates.
- `preset=map-build` selects map evidence behavior, baseline setup, world and
  episode capabilities, and Runtime Metric Map gates.

Keep internal artifact and checker fields such as `task_intent`,
`goal_contract.intent`, and launch `intent` metadata while the runtime stack
still consumes them. These are implementation and artifact contract details, not
the household public command shape.

Planner proof keeps `intent=planner-proof` because it is a separate surface and
not part of the household preset migration.

## Rejected Alternatives

- Keep `cleanup`, `map-build`, and `open-ended` as peer public household
  intents. Rejected because it preserves the old taxonomy and keeps open-ended
  household work as one option beside repeated jobs instead of the base
  contract.

- Rename every cleanup-shaped runtime, server, and artifact path in the first
  slice. Rejected for scope control; runtime/server naming and task-neutral
  artifact schema cleanup can be separate forward-only migrations.

- Add a generic workflow engine or public policy axes. Rejected because the
  current need is a small preset registry, not a new framework.

## Consequences

- Public docs and examples should use `preset=cleanup` and `preset=map-build`
  for standard household jobs.
- Public no-preset household examples should use `prompt=...` and omit
  `intent=open-ended`.
- Operator-console no-preset route ids use `open-task` as the selector segment.
- Eval-harness rows include no-preset Codex and OpenAI Agents SDK household
  open-task rows, plus preset-based cleanup and map-build rows.
- Historical docs and ADR-0136 remain accurate as the prior intermediate
  decision, but active launch guidance follows this ADR.
