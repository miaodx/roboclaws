# 16-01 Real-World Agent MCP Plan

## Goal

Expose the ADR-0003 cleanup contract through MCP so agent-driven policies can be
evaluated without the current-contract `scene_objects` shortcut.

## Tasks

1. Add a real-world Molmo cleanup MCP server/factory backed by
   `RealWorldCleanupContract`.
2. Register only ADR-0003 public tools:
   `metric_map`, `fixture_hints`, `navigate_to_room`, `navigate_to_waypoint`,
   `observe`, `inspect_visible_object`, `navigate_to_object`, `pick`,
   `navigate_to_receptacle`, `open_receptacle`, `place`, `place_inside`, and
   `done`.
3. Reuse the shared cleanup report and semantic timeline underlay so reports
   keep Agent View, Private Evaluation, Score, Cleanup Trace, and Robot View
   Timeline sections.
4. Add a deterministic MCP smoke runner that chooses cleanup actions from public
   MCP responses only.
5. Extend checker/tests/just recipes for the real-world MCP artifact shape.
6. Run focused tests and one real MolmoSpaces/RBY1M visual smoke.

## Verification

- `pytest -q tests/test_molmo_realworld_mcp_server.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_verify_just_recipes.py`
- `ruff check` and `ruff format --check` on changed Python files.
- `just harness::molmo-realworld-agent-mcp "1" "output/molmo-realworld-agent-mcp-harness" "帮我收拾这个房间" "10"`

## Risks

- Reusing current-contract server code directly could leak `scene_objects` into
  ADR-0003. The real-world surface should be explicit and tested for absent
  `scene_objects`.
- Real 10-object robot-view evidence is slow. Keep the required evidence to one
  seed for this phase.
