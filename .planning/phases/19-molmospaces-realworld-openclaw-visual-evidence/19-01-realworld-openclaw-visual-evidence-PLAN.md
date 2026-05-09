# 19-01 Real-World OpenClaw Visual Evidence Plan

## Goal

Produce reviewable OpenClaw Gateway evidence for the ADR-0003
`molmo_cleanup_realworld` MCP surface on the real MolmoSpaces/RBY1M visual
backend, so the report includes Agent View, Private Evaluation, Score, Semantic
Substeps, and Robot View Timeline.

## Tasks

1. Add a focused visual OpenClaw dogfood-kit recipe. It should run the
   deterministic smoke driver with `policy=openclaw_agent`,
   `backend=molmospaces_subprocess`, `--include-robot`, and
   `--record-robot-views`, then check the artifact with
   `--require-openclaw-minimum --require-robot-views`.
2. Add focused tests that prove the new recipe exists and delegates to the
   visual backend/report checker rather than the synthetic-only OpenClaw kit.
3. Run the visual kit gate locally to prove the report underlay still renders
   FPV, chase, map, and verification images for OpenClaw-labeled ADR-0003
   artifacts.
4. Launch a local OpenClaw Gateway attempt against
   `examples/molmo_realworld_cleanup_agent_server.py --backend
   molmospaces_subprocess --include-robot --record-robot-views --host
   0.0.0.0`. Validate the resulting artifact if Gateway reaches `done`, or
   record the exact blocker logs if it does not.
5. Update the source plan, roadmap/state, and Phase 19 summary/verification
   docs with evidence and remaining follow-ups.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_mcp_server.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_verify_just_recipes.py`
- `ruff check` and `ruff format --check` on changed Python files.
- `just verify::molmo-realworld-openclaw-visual-dogfood-kit`
- Checker command against the local Gateway artifact, if generated.

## Risks

- The visual backend is slower than the synthetic backend and depends on the
  isolated Python 3.11 MolmoSpaces runtime.
- Gateway may connect and use tools but fail before `done`; that still counts
  only if the artifact satisfies the OpenClaw minimum and robot-view gates.
- Robot-view evidence must come from the shared report underlay, not a
  one-off HTML renderer.
