# ADR-0143: Drop World Oracle Labels And Fake Camera Inputs As Active Inputs

Status: Accepted

Date: 2026-06-16

Supersedes:

- ADR-0136 wording that used `world-oracle-labels` as the example real evidence
  lane for smoke and household structured-label runs.
- The `world-oracle-labels` lane in
  `docs/plans/refactor-evidence-lane-naming.md`.
- ADR-0138 wording that treated `sim-projected-labels`, `fake-http`, and
  `contract-fake` as current visual-grounding runtime choices.

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

The camera-labeler axis has a similar, smaller problem:
`sim-projected-labels` produces camera-shaped evidence through simulator
projection. That is useful as a deterministic control, but it is not a
deployable perception capability and a real robot cannot obtain it. `fake-http`
and `contract-fake` are even less deployable when they survive as selectable
sidecar pipelines, benchmark defaults, or runbook validation routes. Keeping
any of these as simulator defaults makes map-build proof look camera-grounded
while still depending on simulator-only or fake information.

Roboclaws has no backward-compatibility requirement for obsolete demo surfaces.
The current architecture direction prefers one honest public structured-label
path and one deployable camera-labeler default over preserving privileged or
simulator-only baselines as agent-visible product run modes.

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

Remove `sim-projected-labels`, `fake-http`, and `contract-fake` from active
public/operator/product camera-labeler support and from runnable current
validation routes. Simulator product map-build and real-robot-facing proof
routes should use:

```text
evidence_lane=camera-grounded-labels camera_labeler=grounding-dino
```

`world-public-labels` remains the deterministic structured-simulator baseline
for CI, smoke, contract checks, and cheap debugging. `camera-raw-fpv` remains
the raw camera ablation lane.

If a future slice needs privileged upper-bound diagnostics, it must introduce
them as private eval fixtures, scorer-only controls, or report-only evidence.
It must not reintroduce them as an agent-visible evidence lane without a new ADR.
If a future slice needs simulator projection for low-level testing, it must keep
that as private test/support code or explicit historical evidence, not as a
selectable product `camera_labeler`.
If a test cannot run the deployable camera sidecar, it should fail or skip with
explicit blocked evidence rather than substitute `fake-http`, `contract-fake`,
or another fake camera-labeler route. Parser or schema coverage may use private
static payloads, but not a runnable sidecar, selectable pipeline id, harness
default, or current validation command.

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
- Keep `sim-projected-labels` as the simulator camera-grounded default.
  Rejected because it preserves simulator-only perception as the product proof
  route and weakens the real-robot deployment target.
- Alias `sim-projected-labels` to `grounding-dino` or fall back to projection
  when the sidecar is missing. Rejected because it hides grounding failures and
  recreates the false-confidence pattern this ADR removes.
- Keep `fake-http` or `contract-fake` as runnable camera-grounded substitutes.
  Rejected because fake camera labels cannot run on a real robot, and allowing
  them as active routes would let simulator validation pass while the deployable
  perception path remains broken.
- Keep fake transports only as benchmark/harness defaults. Rejected because a
  green benchmark-shaped run would still mask the deployable sidecar being
  absent or broken.

## Consequences

- Active launch routes, operator-console selections, eval samples,
  eval-harness rows, smoke metadata, and current docs must use
  `world-public-labels` for structured world-label evidence.
- Tests should assert that `world-oracle-labels` is rejected rather than
  accepted as a compatibility alias.
- Product gates for structured world-label routes should remain strict:
  waypoint honesty, real-robot alignment, semantic accepted count, and sweep
  coverage continue to apply where relevant.
- Simulator product/default map-build routes and real-robot-facing proof should
  use `camera-grounded-labels` with `camera_labeler=grounding-dino`.
- `grounding-dino` product proof routes must fail clearly, preferably after
  writing explicit blocked/missing-sidecar evidence, when the External Visual
  Grounding Service is unavailable. Eval harness rows may record blocked
  preflight packets. Neither path may silently fall back to simulator
  projection or fake transport.
- Active public/operator camera labelers should exclude `sim-projected-labels`.
  They should also exclude `fake-http` and `contract-fake`.
- Camera-grounded tests and evals should use the deployable sidecar path or
  report a blocked/missing-sidecar result. They must not maintain product
  confidence with fake camera-labeler routes.
- Current benchmark and harness defaults must not use `fake-http` or
  `contract-fake` as validation proof. If real model dependencies are
  unavailable, the result is blocked or missing-sidecar evidence.
- Product/default simulator `preset=map-build` uses
  `camera-grounded-labels camera_labeler=grounding-dino`. Cleanup structured
  baselines use `world-public-labels` in this slice; physical cleanup remains
  separate until manipulation proof is no longer blocked.
- Historical plans, retrospectives, old output paths, private scorer language,
  private static test fixtures, and unrelated rendering diagnostics may still
  contain old Oracle, simulator-projection, or fake-transport terminology, but
  current household evidence-lane strings, camera-labeler choices, docs,
  runbooks, harness defaults, and launch defaults must not expose
  `world-oracle-labels`, `sim-projected-labels`, `fake-http`, or
  `contract-fake` as active product or validation routes.
- The implementation plan is
  `docs/plans/2026-06-16-drop-world-oracle-labels.md`.
