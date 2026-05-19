# 19-01 Summary: Real-World OpenClaw Visual Evidence

## Outcome

Phase 19 is complete for the visual-evidence slice. The OpenClaw-labeled visual
kit produced a clean ADR-0003 artifact on the real MolmoSpaces/RBY1M backend,
and a live OpenClaw Gateway run produced a minimum-valid visual artifact with
the full shared report view set.

The live Gateway run is not a clean cleanup success. Gateway swept all public
waypoints and generated robot-view evidence, but it skipped the full
`nav -> pick -> nav -> place` semantic tool sequence and chose several
semantically weak destinations. The artifact is therefore recorded as minimum
visual evidence only.

## Evidence

Deterministic OpenClaw-labeled visual kit:

- `output/molmo-realworld-openclaw-visual-dogfood-kit/run_result.json`
- `output/molmo-realworld-openclaw-visual-dogfood-kit/report.html`
- `backend=molmospaces_subprocess`
- `policy=openclaw_agent`
- `cleanup_status=success`
- `generated_mess_count=10`
- `mess_restoration_rate=0.8`
- `sweep_coverage_rate=1.0`
- `disturbance_count=0`
- `semantic_substeps=10`
- `robot_view_steps=44`
- `robot view PNGs=176`

Live OpenClaw Gateway visual run:

- `output/molmo-realworld-openclaw-gateway-visual-g5-1546/run_result.json`
- `output/molmo-realworld-openclaw-gateway-visual-g5-1546/report.html`
- `backend=molmospaces_subprocess`
- `policy=openclaw_agent`
- `cleanup_status=failed`
- `generated_mess_count=5`
- `mess_restoration_rate=0.0`
- `sweep_coverage_rate=1.0`
- `disturbance_count=0`
- `semantic_substeps=5`
- `robot_view_steps=12`
- `robot view PNGs=48`
- no `scene_objects` trace event

## Gateway Notes

The live Gateway server used:

```bash
.venv/bin/python examples/molmo_realworld_cleanup_agent_server.py \
  --host 0.0.0.0 \
  --port 18791 \
  --output-dir output/molmo-realworld-openclaw-gateway-visual-g5-1546 \
  --seed 7 \
  --policy openclaw_agent \
  --task "帮我收拾这个房间" \
  --backend molmospaces_subprocess \
  --generated-mess-count 5 \
  --include-robot \
  --robot-name rby1m \
  --record-robot-views
```

Gateway was bootstrapped with:

```bash
AGENTS=1 \
PERSONALITY_PROBE=0 \
SKILLS_DIR=$PWD/skills/molmo-realworld-cleanup \
ROBOCLAWS_MCP_URL=http://host.docker.internal:18791/mcp \
ROBOCLAWS_TOOL_PROFILE=minimal \
PROVIDER=mimo \
TIMEOUT_SECONDS=1800 \
PROBE_TIMEOUT=180 \
./scripts/openclaw-bootstrap.sh
```

The live policy behavior is useful evidence for the next hardening phase: it
read the metric map and fixture hints, swept all 14 waypoints, and used only
public MCP tools, but it called `pick` and `place` directly instead of the full
semantic navigation loop. The report accurately exposes that as cards with only
`pick -> place` rather than hiding the shortcut.

## Architecture Follow-Up Closed

ADR-0010 is satisfied for visual evidence. OpenClaw cleanup artifacts can now be
checked in two modes:

- clean visual evidence: complete semantic action set plus robot views;
- minimum visual evidence: OpenClaw public-tool trace plus valid FPV, chase,
  map, and verification images even if the policy skips semantic phases.
