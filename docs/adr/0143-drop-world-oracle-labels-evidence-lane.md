# ADR-0143: Drop World Oracle Labels As An Evidence Lane

Status: Accepted

Date: 2026-06-16

Supersedes:

- ADR-0136 wording that used `world-oracle-labels` as the example real evidence
  lane for smoke and household structured-label runs.
- The `world-oracle-labels` lane in
  `docs/plans/refactor-evidence-lane-naming.md`.

## Context

The household evidence-lane model separated what the agent sees from how camera
labels are produced. That model is still useful, but the structured world-label
axis kept two simulator-backed lanes:

- `world-oracle-labels`, a privileged upper-bound lane that can expose
  cleanup-ready destination/tool hints from simulator state.
- `world-public-labels`, a sanitized structured-label lane that withholds
  destination/tool oracle hints and pre-confirmed navigation authorization.

Keeping both lanes active makes the public/private boundary harder to reason
about. It also causes default commands, operator-console routes, eval rows, and
smoke metadata to present the privileged upper-bound lane as ordinary agent
evidence.

Roboclaws has no backward-compatibility requirement for obsolete demo surfaces.
The current architecture direction prefers one honest public structured-label
path over preserving a privileged baseline as an agent-visible run mode.

## Decision

Remove `world-oracle-labels` as an active evidence lane.

The current household evidence lanes are:

```text
world-public-labels
camera-grounded-labels
camera-raw-fpv
```

`smoke` remains a synthetic verification preset, not an evidence lane. Smoke
runs should emit `preset=smoke` plus `evidence_lane=world-public-labels`.

Structured world-label runs use the sanitized public policy. They may expose
public category/fixture-affordance destination policy, but they must not expose
private acceptable-destination truth, cleanup-ready destination decisions,
placement-tool oracle hints, or pre-confirmed navigation authorization to the
agent.

If a future slice needs privileged upper-bound diagnostics, it must introduce
them as private eval fixtures, scorer-only controls, or report-only evidence.
It must not reintroduce them as an agent-visible evidence lane without a new ADR.

## Rejected Alternatives

- Keep `world-oracle-labels` as a maintainer-only lane. Rejected because it
  preserves the same concept in current launch/eval code and invites drift back
  into product defaults.
- Alias `world-oracle-labels` to `world-public-labels`. Rejected because it
  hides a public contract change behind compatibility behavior.
- Rename Oracle to `sim-oracle-upper-bound`. Rejected for this slice because
  the goal is to remove privileged agent-visible upper-bound behavior, not to
  preserve it under a clearer name.
- Omit `evidence_lane` from smoke metadata. Rejected because reports, evals,
  and checkers use evidence-lane identity; smoke should carry Public identity
  while also declaring `preset=smoke`.

## Consequences

- Active launch routes, operator-console selections, eval samples,
  eval-harness rows, smoke metadata, and current docs must use
  `world-public-labels` for structured world-label evidence.
- Tests should assert that `world-oracle-labels` is rejected rather than
  accepted as a compatibility alias.
- Product gates for structured world-label routes should remain strict:
  waypoint honesty, real-robot alignment, semantic accepted count, and sweep
  coverage continue to apply where relevant.
- Historical plans, retrospectives, old output paths, private scorer language,
  and unrelated rendering diagnostics may still contain the word `oracle`, but
  current household evidence-lane strings and constants must not expose
  `world-oracle-labels`.
- The implementation plan is
  `docs/plans/2026-06-16-drop-world-oracle-labels.md`.
