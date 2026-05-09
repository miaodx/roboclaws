# 18-01 Summary: Real-World OpenClaw Dogfood

## Outcome

Phase 18 is complete for the first OpenClaw viability slice. OpenClaw Gateway
successfully connected to `molmo_cleanup_realworld`, used the ADR-0003 public
MCP tools, avoided `scene_objects`, completed the synthetic cleanup run, and
passed both the OpenClaw minimum gate and the clean agent run gate.

## Evidence

- Synthetic Gateway artifact:
  `output/molmo-realworld-openclaw-gateway-synth-bind-all/run_result.json`
- Report:
  `output/molmo-realworld-openclaw-gateway-synth-bind-all/report.html`
- `policy=openclaw_agent`
- `contract=realworld_cleanup_v1`
- `mcp_server=molmo_cleanup_realworld`
- `agent_driven=true`
- `cleanup_status=success`
- `completion_status=success`
- `generated_mess_count=5`
- `mess_restoration_rate=1.0`
- `sweep_coverage_rate=1.0`
- `disturbance_count=0`
- `semantic_substeps=5`
- `stale_reference_errors=0`
- `premature_done=false`
- `fridge_inside_sequence_ok=true`

## Gateway Notes

The first attempt used the direct-agent server default bind
`--host 127.0.0.1`. Gateway config was correct, but Docker could not fetch the
MCP server through `http://host.docker.internal:18791/mcp`, so the model only
saw `session_status`.

The successful attempt used:

```bash
.venv/bin/python examples/molmo_realworld_cleanup_agent_server.py \
  --host 0.0.0.0 \
  --port 18791 \
  --output-dir output/molmo-realworld-openclaw-gateway-synth-bind-all \
  --seed 7 \
  --policy openclaw_agent \
  --task "帮我收拾这个房间" \
  --backend api_semantic_synthetic
```

and bootstrapped Gateway with:

```bash
AGENTS=1 \
PERSONALITY_PROBE=0 \
SKILLS_DIR=$PWD/skills/molmo-realworld-cleanup \
ROBOCLAWS_MCP_URL=http://host.docker.internal:18791/mcp \
ROBOCLAWS_TOOL_PROFILE=minimal \
PROVIDER=mimo \
TIMEOUT_SECONDS=1200 \
PROBE_TIMEOUT=180 \
./scripts/openclaw-bootstrap.sh
```

The real MolmoSpaces/RBY1M visual Gateway run remains a follow-up. The first
OpenClaw gate deliberately proves Gateway tool-use viability and clean policy
behavior on the ADR-0003 surface before spending local wall clock on the slower
visual backend.

## Architecture Follow-Up Closed

ADR-0009 now records that MolmoSpaces cleanup demos share one report underlay.
The shared report renderer now shows semantic cleanup subphases as
`nav -> pick -> nav -> open? -> place`, while raw traces keep full tool names.
