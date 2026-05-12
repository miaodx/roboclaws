# MolmoSpaces Placement Grounding

## Problem

MolmoSpaces cleanup reports can show a semantic object/receptacle binding while
the robot-view evidence does not show the object. Recent review examples:

- `navigate_to_object observed_002`: Book bound to DiningTable, object pixels 0.
- `navigate_to_object observed_005`: Plate bound to DiningTable, object pixels 0.
- `place observed_009`: Book placed on Desk, object pixels 0.

The root cause is that current `api_semantic` cleanup primitives move MuJoCo
free bodies to deterministic receptacle-relative offsets and update semantic
state, but do not prove support/contact or visual grounding.

## Goal

Make semantic cleanup artifacts honest and mechanically guarded:

- Mess seeding must place moved objects on or inside the claimed source
  receptacle, with placement diagnostics attached.
- Cleanup `place` must put the object onto the target receptacle surface.
- Cleanup `place_inside` must put the object into an open receptacle.
- Fridge-like flows must expose `close_receptacle` after `place_inside`.
- Robot-view reports/checkers must flag focused cleanup actions whose visual
  evidence does not show the focused object.

## Decisions

- Keep this as one coherent implementation slice. Do not create a separate GSD
  phase for every report/checker tweak.
- Use current `api_semantic` primitives, but add placement diagnostics and
  visual-evidence gates so the report does not overclaim physical proof.
- `close_receptacle` is a semantic tool in this slice. It closes the MuJoCo
  joint state where the backend exposes closeable joints; planner-backed close
  proof remains out of scope.

## Non-Goals

- Do not replace cleanup primitives with planner-backed pick/place.
- Do not solve upstream RBY1M/CuRobo grasp feasibility blockers.
- Do not require every object to be visible after it is placed inside a closed
  refrigerator; contained-in proof is the inside-placement evidence.

## Acceptance Criteria

- Public MCP/contract surfaces list and route `close_receptacle`.
- Canonical inside cleanup sequence becomes:
  `navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle -> place_inside -> close_receptacle`.
- Surface placement and mess placement emit support diagnostics tying object,
  relation, and receptacle together.
- Focused robot-view actions report a visual-grounding status:
  `ok`, `weak_object_visibility`, or `contained_inside`.
- Checkers fail focused surface actions with zero object pixels unless the
  object is explicitly `contained_inside`.
- Contract tests cover close routing, semantic-loop close ordering, and
  zero-pixel visual grounding.

## Verification

- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_molmo_semantic_cleanup_loop.py -q`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
- `uv run ruff check <changed files>`
- Re-render and check the reviewed artifact when compatible with the new
  stricter visual-grounding gate.
