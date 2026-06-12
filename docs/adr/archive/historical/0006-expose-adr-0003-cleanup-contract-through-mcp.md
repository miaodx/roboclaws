# Expose ADR-0003 Cleanup Contract Through MCP

Roboclaws will expose the ADR-0003 real-world cleanup contract through a Molmo
cleanup MCP surface that is separate from the historical current-contract
`scene_objects` bridge. The current-contract bridge remains useful for
transitional Codex/Claude/OpenClaw tool-viability evidence, but it is not the
right interface for model policies that must discover cleanup candidates through
public map/perception inputs.

The ADR-0003 MCP surface exposes `metric_map`, `fixture_hints`,
`navigate_to_room`, `navigate_to_waypoint`, `observe`,
`inspect_visible_object`, `navigate_to_object`, `pick`,
`navigate_to_receptacle`, `open_receptacle`, `place`, `place_inside`, and
`done`. It must not expose `scene_objects`, Generated Mess Set, target count,
private manifest, acceptable destination sets, `is_misplaced`, or hidden target
receptacles. Small movable object IDs are only stable Observed Object Handles
after local observation.

The first phase may validate the surface with a deterministic MCP smoke agent
that uses only public tool responses. Direct Codex/Claude/OpenClaw dogfood
against this stricter surface is a follow-up phase once the MCP contract and
artifacts are stable.
