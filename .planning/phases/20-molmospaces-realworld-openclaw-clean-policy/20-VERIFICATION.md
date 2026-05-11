# Phase 20 Verification

## Gates Run

```bash
./scripts/run_pytest_standalone.sh -q \
  tests/test_molmo_realworld_contract.py \
  tests/test_molmo_realworld_mcp_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py
```

Result: 21 passed.

```bash
.venv/bin/ruff check \
  roboclaws/molmo_cleanup/realworld_contract.py \
  roboclaws/molmo_cleanup/semantic_timeline.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  examples/molmo_realworld_cleanup_agent_server.py \
  tests/test_molmo_realworld_contract.py \
  tests/test_molmo_realworld_mcp_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py
```

Result: passed.

```bash
.venv/bin/ruff format --check \
  roboclaws/molmo_cleanup/realworld_contract.py \
  roboclaws/molmo_cleanup/semantic_timeline.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  examples/molmo_realworld_cleanup_agent_server.py \
  tests/test_molmo_realworld_contract.py \
  tests/test_molmo_realworld_mcp_server.py \
  tests/test_check_molmo_realworld_cleanup_result.py
```

Result: passed.

```bash
just verify::molmo-realworld-agent-dogfood-kit
```

Result: passed. The generated artifact recorded:

- `cleanup_status=success`
- `semantic_order_errors=0`
- `complete_semantic_substep_objects=5`
- `fridge_inside_sequence_ok=true`

```bash
just verify::molmo-realworld-openclaw-dogfood-kit
```

Result: passed. The OpenClaw-labeled synthetic artifact recorded:

- `policy=openclaw_agent`
- `cleanup_status=success`
- `semantic_order_errors=0`
- `complete_semantic_substep_objects=5`

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

## Local Gateway Note

No new live Gateway model run was attempted in Phase 20. The contract and
checker are now stricter, so a future live Gateway run that repeats the Phase 19
shortcut behavior should either receive `semantic_order` errors and recover, or
be rejected as not-clean evidence.
