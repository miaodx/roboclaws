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

Use root `STATUS.md` for the current project focus. This index is a navigation
aid, not a source of truth for current priority.

### Active Or Recently Touched

- [Household Map, Launch, And Open-Ended Contracts](2026-06-11-household-map-launch-open-ended-contracts.md)
- [Retire AI2-THOR And VLM Direct](refactor-retire-ai2thor-vlm-direct.md)
- [Open-Ended Proof Status Contract](2026-06-11-open-ended-proof-status.md)
- [VLM Direct Sidecar And OpenClaw Status Cleanup](2026-06-12-vlm-direct-sidecar-and-openclaw-status-cleanup.md)
- [Eval Harness Skill Entrypoint](2026-06-15-eval-harness-skill-entrypoint.md)
- [Agent Validation Matrix Skill](2026-06-11-agent-validation-matrix-skill.md) (historical)
- [Adaptive Target Inspection](2026-06-11-adaptive-target-inspection.md)
- [Live-Agent Adaptive Inspection Triggerability](2026-06-11-live-agent-adaptive-inspection-triggerability.md)
- [Report Performance Analysis Skill](2026-06-11-report-performance-analysis-skill.md)
- [Auto Semantic Map Build](auto-semantic-map-build.md)
- [Operator Console Orthogonal Launch Refactor](operator-console-orthogonal-launch-refactor.md)
- [RAW-FPV Subagent Visual Labeling Probe](raw-fpv-subagent-visual-labeling-probe.md)
- [Live Agent Runtime SDK Perf Follow-ups](live-agent-runtime-sdk-perf-followups.md)
- [Live Agent Runtime SDK Spike](live-agent-runtime-sdk-spike.md)

### Household World, Map Build, And Cleanup

- [Household Map, Launch, And Open-Ended Contracts](2026-06-11-household-map-launch-open-ended-contracts.md)
- [Open-Ended Proof Status Contract](2026-06-11-open-ended-proof-status.md)
- [Adaptive Target Inspection](2026-06-11-adaptive-target-inspection.md)
- [Live-Agent Adaptive Inspection Triggerability](2026-06-11-live-agent-adaptive-inspection-triggerability.md)
- [Mujoco Isaac Minimal Map Task Parity](mujoco-isaac-minimal-map-task-parity.md)
- [Actionable Semantic Map Snapshot](refactor-actionable-semantic-map-snapshot.md)
- [Minimal-First Semantic Map Pipeline](refactor-reduce-entropy-minimal-semantic-map.md)
- [Done Readiness Held State](refactor-reduce-entropy-done-readiness-held-state.md)
- [RAW_FPV Visual Candidate Actionability](refactor-raw-fpv-visual-candidate-actionability.md)
- [FPV Visual Scan/Confirm Gate](refactor-fpv-visual-evidence-gate.md)
- [Sanitized Agent Steering](refactor-reduce-entropy-sanitized-agent-steering.md)
- [Molmo Cleanup Memory And Routine Entropy](refactor-reduce-entropy-molmo-cleanup-memory.md)
- [MolmoSpaces Bounded Concurrent Cleanup Runs](molmospaces-bounded-concurrent-cleanup.md)
- [MolmoSpaces Sanitized World Labels Lane](molmospaces-sanitized-world-labels-lane.md)
- [MolmoSpaces Waypoint-Honest Cleanup Flow](molmospaces-waypoint-honest-cleanup-flow.md)
- [MolmoSpaces Real-Robot Contract Alignment](molmospaces-real-robot-contract-alignment.md)
- [Environment Setup Relocation Contract](environment-setup-relocation-contract.md)

### Real Robot And Backend Work

- [Agibot G2 Cleanup Support Pilot](agibot-g2-cleanup-support-pilot.md)
- [Agibot Robot Map 9 Dry-Run Rehearsal](agibot-robot-map-9-dry-run-rehearsal.md)
- [Agibot Robot Map 9 Semantic Actions Rehearsal](agibot-robot-map-9-semantic-actions-rehearsal.md)
- [MolmoSpaces Agibot Contract Rehearsal](molmospaces-agibot-contract-rehearsal.md)
- [Real Robot Nav2 Cleanup Pilot](real-robot-nav2-cleanup-pilot.md)
- [Agibot RAW_FPV Preflight](refactor-agibot-raw-fpv-preflight.md)
- [B1 Map 12 Digital Twin Navigation Readiness](refactor-reduce-entropy-b1-map12-digital-twin.md)

### Rendering, Cameras, And Visual Grounding

- [Isaac Lab MolmoSpaces Backend Support](isaac-lab-molmospaces-backend-support.md)
- [MuJoCo Isaac Object And Render Parity Audit](mujoco-isaac-object-render-parity-audit.md)
- [MuJoCo Isaac Render Difference Probe Directions](mujoco-isaac-render-difference-probe-directions.md)
- [MuJoCo Isaac Visual Parity Convergence](mujoco-isaac-visual-parity-convergence.md)
- [Runtime Render State Parity](refactor-runtime-render-state-parity.md)
- [Scene Camera Material Vs Light Diagnostic](scene-camera-material-vs-light-diagnostic.md)
- [Genesis Scene-Camera Backend Lane](genesis-scene-camera-backend-lane.md)
- [MolmoSpaces HTTP Visual Grounding Service](molmospaces-http-visual-grounding-service.md)
- [Visual Grounding GPU Sidecar Benchmark](visual-grounding-gpu-sidecar-benchmark.md)
- [VLM Direct Sidecar And OpenClaw Status Cleanup](2026-06-12-vlm-direct-sidecar-and-openclaw-status-cleanup.md)

### Launch, Console, And Agent Runtime

- [Household Map, Launch, And Open-Ended Contracts](2026-06-11-household-map-launch-open-ended-contracts.md)
- [Retire AI2-THOR And VLM Direct](refactor-retire-ai2thor-vlm-direct.md)
- [Eval Harness Skill Entrypoint](2026-06-15-eval-harness-skill-entrypoint.md)
- [Agent Validation Matrix Skill](2026-06-11-agent-validation-matrix-skill.md) (historical)
- [Task Surface, Intent, And Goal Contract Refactor](task-surface-intent-goal-contract-refactor.md)
- [Domain-First Launch Architecture](refactor-reduce-entropy-domain-first-launch-architecture.md)
- [Operator Console Agent Interaction](operator-console-agent-interaction.md)
- [Operator Console Layered Launch Gates](operator-console-layered-launch-gates.md)
- [Operator Console UI](refactor-operator-console-ui.md)
- [Standalone Codex Operator Console](standalone-codex-operator-console.md)
- [Standalone Operator Console UI Design Contract](standalone-codex-operator-console-UI-SPEC.md)
- [Operator Console UI Review](standalone-codex-operator-console-UI-REVIEW.md)
- [Live Agent Runner Boundary](refactor-live-agent-runner-boundary.md)
- [VLM Direct Sidecar And OpenClaw Status Cleanup](2026-06-12-vlm-direct-sidecar-and-openclaw-status-cleanup.md)
- [Codex Harness Sidecar Lifecycle](refactor-codex-harness-sidecar-lifecycle.md)
- [Molmo Cleanup Codex Harness Speedup](molmo-cleanup-codex-harness-speedup.md)
- [MiMo v2.5 Migration](refactor-mimo-v25-migration.md)

### Naming And Evidence Lanes

- [Evidence Lane Naming Refactor](refactor-evidence-lane-naming.md)
