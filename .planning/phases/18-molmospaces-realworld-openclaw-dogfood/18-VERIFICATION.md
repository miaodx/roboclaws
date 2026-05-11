# Phase 18 Verification

## Gates Run

```bash
./scripts/run_pytest_standalone.sh -q \
  tests/test_molmo_cleanup_report.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_realworld_agent_server.py \
  tests/test_verify_just_recipes.py \
  tests/test_molmo_realworld_mcp_server.py
```

Result: 22 passed.

```bash
.venv/bin/ruff check \
  examples/molmo_realworld_cleanup_agent_server.py \
  roboclaws/molmo_cleanup/report.py \
  roboclaws/molmo_cleanup/semantic_timeline.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_cleanup_report.py \
  tests/test_molmo_realworld_agent_server.py \
  tests/test_verify_just_recipes.py
```

Result: passed.

```bash
.venv/bin/ruff format --check \
  examples/molmo_realworld_cleanup_agent_server.py \
  roboclaws/molmo_cleanup/report.py \
  roboclaws/molmo_cleanup/semantic_timeline.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_cleanup_report.py \
  tests/test_molmo_realworld_agent_server.py \
  tests/test_verify_just_recipes.py
```

Result: passed.

```bash
just verify::molmo-realworld-openclaw-dogfood-kit
```

Result: passed. This generated and checked
`output/molmo-realworld-openclaw-dogfood-kit/run_result.json`.

```bash
.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
  --expect-task "帮我收拾这个房间" \
  --expect-backend api_semantic_synthetic \
  --expect-policy openclaw_agent \
  --expect-mcp-server molmo_cleanup_realworld \
  --min-generated-mess-count 5 \
  --require-agent-driven \
  --require-openclaw-minimum \
  --require-clean-agent-run \
  output/molmo-realworld-openclaw-gateway-synth-bind-all/run_result.json
```

Result: passed.

## Real OpenClaw Evidence

OpenClaw Gateway was launched locally through `scripts/openclaw-bootstrap.sh`
with `skills/molmo-realworld-cleanup`,
`ROBOCLAWS_MCP_URL=http://host.docker.internal:18791/mcp`, and
`ROBOCLAWS_TOOL_PROFILE=minimal`.

The successful Gateway run produced:

- `output/molmo-realworld-openclaw-gateway-synth-bind-all/run_result.json`
- `output/molmo-realworld-openclaw-gateway-synth-bind-all/report.html`
- `output/molmo-realworld-openclaw-gateway-synth-bind-all/trace.jsonl`

Key metrics:

- backend: `api_semantic_synthetic`
- policy: `openclaw_agent`
- contract: `realworld_cleanup_v1`
- mcp_server: `molmo_cleanup_realworld`
- cleanup_status: `success`
- completion_status: `success`
- generated_mess_count: `5`
- mess_restoration_rate: `1.0`
- sweep_coverage_rate: `1.0`
- disturbance_count: `0`
- semantic_substeps: `5`
- tool requests: metric_map 1, fixture_hints 1, navigate_to_waypoint 8,
  observe 8, navigate_to_object 5, pick 5, navigate_to_receptacle 5,
  open_receptacle 1, place 4, place_inside 1, done 1.

No `scene_objects` request appeared in the trace.

## Known Follow-Up

The real visual MolmoSpaces/RBY1M OpenClaw run was not executed in this phase.
The slower visual run should be a separate local evidence pass using the same
report underlay after the synthetic Gateway path is stable.
