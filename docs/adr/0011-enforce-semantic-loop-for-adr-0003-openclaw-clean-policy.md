# Enforce Semantic Loop For ADR-0003 OpenClaw Clean Policy

Roboclaws will make the ADR-0003 `molmo_cleanup_realworld` MCP surface enforce
the public semantic cleanup loop instead of silently repairing skipped phases
inside lower-level backend calls.

Phase 19 proved the report/view underlay for live OpenClaw Gateway artifacts,
but the live policy skipped `navigate_to_object` and `navigate_to_receptacle`
before calling `pick` and `place`. The backend tolerated that by auto-navigating
internally, which preserved state mutation but weakened the public semantic
subphases and made the report differ from the intended `nav -> pick -> nav ->
open? -> place` evidence shape.

The real-world MCP contract will therefore reject out-of-order semantic cleanup
calls with public, non-private guidance:

- `pick(object_id)` requires a successful `navigate_to_object(object_id)` first;
- `place(fixture_id)` and `place_inside(fixture_id)` require a successful
  `navigate_to_receptacle(fixture_id)` for the held object first;
- `place_inside(fixture_id)` also requires `open_receptacle(fixture_id)` when
  the fixture advertises `open` / `place_inside` affordances;
- rejected calls return `error_reason=semantic_order` with the required next
  tool and recovery hint, but no Generated Mess Set, target count, acceptable
  destination set, or private scorer truth.

This keeps ADR-0003 public/private separation intact while turning the semantic
loop from prompt-only convention into an executable contract. Deterministic
smoke agents and direct coding agents already follow this order, so their clean
paths should remain unchanged. OpenClaw runs that skip phases will now fail
visibly and be able to recover by calling the required public tool.

Acceptance for clean OpenClaw policy success remains stricter than minimum
Gateway viability: clean artifacts should have no semantic-order errors, all
handled objects should complete the public semantic loop, and the shared report
should show the normalized subphases from ADR-0009.
