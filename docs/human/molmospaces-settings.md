# MolmoSpaces Settings Matrix

This is the operator-facing map for MolmoSpaces cleanup demo settings. Use it
to choose the right run shape before making project-status claims.

## Canonical Status Demo

For the current project-status artifact, prefer:

```text
contract=realworld_cleanup_v1
backend=molmospaces_subprocess
perception_mode=visible_object_detections
include_robot=true
record_robot_views=true
robot_name=rby1m
fixture_hint_mode=room_only
primitive_provenance=api_semantic
```

This produces a real MolmoSpaces/RBY1M cleanup report with Agent View, Private
Evaluation, Score, Semantic Substeps, and Robot View Timeline. The timeline
contains FPV, chase, map, and verification images when the backend can capture
robot views.

Do not use the synthetic dogfood kit as the main status artifact. It is useful
for fast contract checks, but it has no robot camera timeline.

## Main Axes

| Axis | Values | Meaning | Status Claim |
|------|--------|---------|--------------|
| Contract | `realworld_cleanup_v1` | ADR-0003 public/private-safe surface. No `scene_objects`, no target list. | Target contract for demos. |
| Contract | `current_contract` | Older shortcut surface. Exposes global scene objects for loop proof. | Legacy/current-contract bridge only. |
| Backend | `api_semantic_synthetic` | Fast in-process semantic state mutation. | CI/smoke shape, not real visual proof. |
| Backend | `molmospaces_subprocess` | Real upstream MolmoSpaces/MuJoCo scene. | Required for real visual evidence. |
| Perception | `visible_object_detections` | Agent gets robot-local observed handles, categories, boxes, and support estimates. | Current best cleanup-success mode. |
| Perception | `raw_fpv_only` | Agent gets FPV observation artifact, no structured detections. | Camera evidence only; not cleanup success yet. |
| Perception | `camera_model_policy` | Raw FPV observation first, then simulated camera-model candidates become observed handles. | Supported by the deterministic demo/checker and MCP internals; not exposed by every CLI yet. |
| Visuals | `--include-robot --record-robot-views` | Capture RBY1M robot-view timeline. | Required for FPV/chase/map/verification report. |
| Visuals | omitted | No robot-view timeline. | Fast smoke only. |
| Fixture hints | `room_only` | Public room-level fixture hints. | Preferred ADR-0003 setting. |
| Fixture hints | `exact_fixtures` | Easier exact fixture hints. | Fallback/debug only. |
| Provenance | `api_semantic` | Cleanup tools mutate simulator semantic state. | Current normal cleanup loop. |
| Provenance | `planner_backed` | Cleanup subphase has matching RBY1M/CuRobo proof. | Future strict manipulation target. |

## Entrypoint Support

Not every entrypoint exposes every contract mode yet. Treat the matrix below as
the current source of truth before claiming a run supports a setting.

| Entrypoint | Visible Detections | Raw FPV Only | Camera Model Policy | Notes |
|------------|--------------------|--------------|---------------------|-------|
| `examples/molmo_cleanup/molmospaces_realworld_cleanup.py` | yes | yes | yes | Deterministic cleanup demo and checker path. |
| `scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py` | yes | yes | no | Dogfood/smoke wrapper used by several just recipes. |
| `examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py` | yes | yes | no | Direct Codex/Claude/OpenClaw server CLI. |
| `RealWorldCleanupContract` / `realworld_mcp_server` internals | yes | yes | yes | Underlying contract supports `infer_camera_model_candidates`. |

## Command Taxonomy

Use `molmo::*` for daily operator commands. It names the run by driver and
profile:

```bash
just molmo::cleanup <driver> <profile>
```

| Axis | Values | Meaning |
|------|--------|---------|
| Driver | `direct` | Deterministic Python cleanup loop; no MCP server and no live LLM agent. |
| Driver | `mcp-smoke` | Deterministic script through ADR-0003 MCP tools; drives the same tool-call path but does not launch Codex or Claude. |
| Driver | `openclaw-smoke` | OpenClaw policy-labeled MCP smoke; proves OpenClaw-shaped artifact/checker wiring but does not launch Gateway. |
| Driver | `codex-live` | Live Codex CLI connected to the cleanup MCP server. |
| Driver | `claude-live` | Live Claude Code connected to the cleanup MCP server. |
| Driver | `openclaw-live` | Live OpenClaw Gateway connected to the cleanup MCP server. |
| Profile | `smoke` | Synthetic contract sanity; world labels; semantic report. |
| Profile | `world-labels` | MolmoSpaces/RBY1M report; agent receives structured world labels, not images. |
| Profile | `camera-raw` | MolmoSpaces/RBY1M report; agent receives raw camera artifacts and no structured labels. |
| Profile | `camera-labels` | MolmoSpaces/RBY1M report; agent receives camera-derived structured candidates. |

`verify::*` remains the confidence-gate namespace: it runs focused tests and then
delegates scenario execution to `harness::*`. `harness::*` remains the
lower-level implementation-rig namespace, useful when debugging a specific
script or checker. Prefer `molmo::*` when deciding what report to produce.

The convenient aliases are:

| Command | Expands To | Use It For |
|---------|------------|------------|
| `just molmo::quick-check` | `mcp-smoke smoke` | Cheap contract check; accepts `driver=` and `profile=` overrides. |
| `just molmo::review-report` | `direct world-labels` | Canonical human review/status report. |
| `just molmo::mcp-smoke-report` | `mcp-smoke world-labels` | Real visual MCP smoke without a live external agent. |
| `just molmo::openclaw-smoke-report` | `openclaw-smoke world-labels` | OpenClaw-labeled visual artifact without live Gateway. |
| `just molmo::camera-raw-report` | `direct camera-raw` | Camera-only observation evidence; not cleanup-success proof. |
| `just molmo::codex-report` | `codex-live world-labels` | Live Codex agent report. |
| `just molmo::claude-report` | `claude-live world-labels` | Live Claude Code agent report. |
| `just molmo::openclaw-report` | `openclaw-live world-labels` | Live OpenClaw Gateway report. |

For live Codex / Claude reports, optional repo-local `.env` provider overrides
are honored the same way as the direct navigation demos:

```bash
ROBOCLAWS_CODEX_PROVIDER=mimo-openai
ROBOCLAWS_CODEX_MODEL=mimo-v2.5-pro

ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic
ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6
```

`system` leaves the system CLI defaults unchanged. Kimi/MiMo profiles select
model, base URL, API-key env var, and protocol for the launched process only.
`ROBOCLAWS_CODE_AGENT_PROVIDER` and `ROBOCLAWS_CODE_AGENT_MODEL` can be used as
shared fallbacks. Before a long Codex visual cleanup run, use:

```bash
just code::codex-provider-smoke
```

`codex-live` is detached by default. `just molmo::codex-report` starts a tmux
session that owns the cleanup MCP server, `codex exec`, logs, checker, and
artifacts, then returns with status/attach/tail commands. Probe it without
attaching:

```bash
just molmo::status
just molmo::status output/molmo/codex-report/<stamp>/seed-7
```

The status probe reports tmux liveness, elapsed time, MCP tool progress,
`run_result.json` / `report.html` readiness, and the latest Codex message if
the CLI has written one. Only one detached Molmo/Codex cleanup run is allowed at
a time because each visual run owns a MuJoCo-backed MolmoSpaces backend. If a
run is active or the requested MCP port is busy, the launcher fails instead of
starting another simulator on a different port.

For quick axis overrides, use positional values or `driver=` / `profile=`
prefixes:

```bash
just molmo::quick-check openclaw-smoke smoke
just molmo::quick-check driver=openclaw-smoke profile=smoke
```

## Report Shapes

All Molmo cleanup demos should route through the shared cleanup report underlay
in `roboclaws/molmo_cleanup/report.py`. Different settings only add or omit
sections.

| Shape | Required Settings | Expected Sections |
|-------|-------------------|-------------------|
| Synthetic cleanup smoke | `api_semantic_synthetic` | Summary, before/after, semantic substeps, score, advisory/private sections where available. No robot timeline. |
| Real visual cleanup | `molmospaces_subprocess`, `include_robot`, `record_robot_views` | Synthetic sections plus Robot View Timeline with FPV, chase, map, verification. |
| Raw FPV evidence | `perception_mode=raw_fpv_only`, robot views enabled | Raw FPV Observations plus visual timeline. No structured observed-object table. |
| Camera-model policy | `perception_mode=camera_model_policy` | Raw FPV observation evidence plus Camera Model Policy section. |
| Planner proof attached | `--planner-proof-run-result ...` | Attached Planner Proof, Cleanup Primitive Gate, Planner Cleanup Bridge. |
| Proof bundle runner | proof-bundle runner script | Separate runner report with selected commands, proof results, blockers, grasp/task-feasibility evidence. |

## Recommended Recipes

Molmo operator recipes write runs under Shanghai-local timestamp folders:
`output/molmo/<recipe>/<MMDD_HHMM>/...`. Recipes place each seed below that
timestamp root, for example `output/molmo/review-report/0511_1628/seed-1/`.

Fast synthetic contract smoke:

```bash
just molmo::quick-check
```

Real visual status/review report:

```bash
just molmo::review-report
```

Real visual MCP smoke:

```bash
just molmo::mcp-smoke-report
```

Real visual OpenClaw-shaped smoke:

```bash
just molmo::openclaw-smoke-report
```

Raw camera evidence:

```bash
just molmo::camera-raw-report
```

Live external-agent reports:

```bash
just molmo::codex-report
just molmo::claude-report
just molmo::openclaw-report
```

`openclaw-report` keeps the repo work-network guard. `claude-report` is blocked
on the work network only when using the system Claude Code provider; it may run
there with `ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic` or
`ROBOCLAWS_CLAUDE_PROVIDER=mimo-anthropic`. Run `just dev::network-status` first
if you are unsure which network you are on.

Planner proof-bundle dry run:

```bash
just harness::molmo-planner-proof-bundle-runner
```

Local strict proof/rerun attempt:

```bash
just harness::molmo-planner-proof-bundle-execute-rerun
```

## Current Boundaries

- A clean semantic cleanup run does not prove physical manipulation.
- `api_semantic` means the simulator state was updated through semantic tools.
- `raw_fpv_only` proves camera artifact plumbing, not camera-only cleanup
  success.
- `camera_model_policy` uses deterministic simulated camera-model evidence
  today; it is not real VLM pixel inference, and the direct external-agent
  server CLI does not expose it yet.
- The global planner cleanup bridge remains blocked until cleanup subphases are
  planner-backed for the required object/target bindings.
- OpenClaw minimum viability and clean cleanup success are separate gates.

## Source Docs

- [ADR-0003](../adr/0003-separate-cleanup-agent-view-from-private-evaluation.md):
  public Agent View vs private evaluation.
- [ADR-0009](../adr/0009-use-shared-molmo-cleanup-report-underlay.md):
  shared Molmo cleanup report underlay.
- [ADR-0010](../adr/0010-require-real-visual-openclaw-evidence-for-adr-0003-cleanup.md):
  real visual OpenClaw evidence requirements.
- [ADR-0013](../adr/0013-add-raw-fpv-observation-mode-for-adr-0003-cleanup.md):
  raw FPV-only perception mode.
- [ADR-0020](../adr/0020-add-camera-model-policy-mode-for-adr-0003-cleanup.md):
  camera-model policy mode.
- [ADR-0028](../adr/0028-add-planner-cleanup-bridge-readiness-evidence.md):
  planner cleanup bridge readiness.
- [`domain.md`](domain.md): domain vocabulary and shipped-history notes.
