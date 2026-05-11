# Phase 19 Verification

## Gates Run

```bash
./scripts/run_pytest_standalone.sh -q \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py \
  tests/test_molmo_cleanup_report.py \
  tests/test_molmo_realworld_mcp_server.py
```

Result: 21 passed.

```bash
.venv/bin/ruff check \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py
```

Result: passed.

```bash
.venv/bin/ruff format --check \
  scripts/check_molmo_realworld_cleanup_result.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_verify_just_recipes.py
```

Result: passed.

```bash
just verify::molmo-realworld-openclaw-visual-dogfood-kit
```

Result: passed. This generated and checked
`output/molmo-realworld-openclaw-visual-dogfood-kit/run_result.json`.

```bash
.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
  --expect-task "帮我收拾这个房间" \
  --expect-backend molmospaces_subprocess \
  --expect-policy openclaw_agent \
  --expect-mcp-server molmo_cleanup_realworld \
  --min-generated-mess-count 10 \
  --require-agent-driven \
  --require-openclaw-minimum \
  --require-clean-agent-run \
  --require-robot-views \
  output/molmo-realworld-openclaw-visual-dogfood-kit/run_result.json
```

Result: passed.

```bash
.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
  --expect-task "帮我收拾这个房间" \
  --expect-backend molmospaces_subprocess \
  --expect-policy openclaw_agent \
  --expect-mcp-server molmo_cleanup_realworld \
  --min-generated-mess-count 5 \
  --require-agent-driven \
  --require-openclaw-minimum \
  --require-robot-views \
  output/molmo-realworld-openclaw-gateway-visual-g5-1546/run_result.json
```

Result: passed.

## Visual Evidence

The deterministic visual kit produced 176 robot-view PNGs across 44
`robot_view_steps`, including FPV, chase, map, and verification images. Its
report includes Agent View, Semantic Substeps, Robot View Timeline, Score, and
Private Evaluation.

The live Gateway visual run produced 48 robot-view PNGs across 12
`robot_view_steps`, including FPV, chase, map, and verification images. Its
report includes Agent View, Semantic Substeps, Robot View Timeline, Score, and
Private Evaluation.

No `scene_objects` request appeared in either trace.

## Known Follow-Up

Live Gateway visual cleanup is not yet clean-policy success. The run restored
0/5 exact private targets, while 3/5 placements were semantically acceptable or
preferred. The model skipped `navigate_to_object` and
`navigate_to_receptacle`, so the checker accepts it only as minimum visual
evidence, not as a clean visual cleanup run.
