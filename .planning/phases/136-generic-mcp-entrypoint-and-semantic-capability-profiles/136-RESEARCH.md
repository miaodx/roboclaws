# Phase 136 Research: Generic MCP Entrypoint And Semantic Capability Profiles

## Question

What do we need to know to plan the metadata-first MCP profile/router slice
well, without turning it into a universal robot API or crossing local-dev
hardware gates?

## Primary Sources And Local Evidence

- MCP server tools are a list/call protocol with tool metadata, optional
  `inputSchema`, optional `outputSchema`, and structured content in responses:
  https://modelcontextprotocol.io/specification/draft/server/tools
- Nav2 exposes navigation as bounded actions such as NavigateToPose rather than
  as whole household tasks: https://docs.nav2.org/commander_api/index.html and
  https://api.nav2.org/actions/rolling/navigatetopose.html
- ROS 2 actions are long-running goal/result/feedback interactions, which maps
  better to a semantic navigation service than to raw simulator steps:
  https://docs.ros.org/en/rolling/Tutorials/Intermediate/Understanding-ROS2-Actions.html
- Habitat-Lab separates actions, sensors, measures, and task logic; this
  supports keeping task prompts outside the MCP tool boundary:
  https://aihabitat.org/docs/habitat-lab/
- PARTNR is a benchmark for human-robot planning and collaboration tasks, not a
  robot capability API; use it as vocabulary pressure only:
  https://arxiv.org/abs/2411.00081
- Local ADR-0003 and ADR-0006 require the cleanup agent view to exclude private
  scorer truth and the `scene_objects` shortcut.
- Local ADR-0004 chose separate AI2-THOR and Molmo MCP servers until contracts
  stabilized. Phase 136 should add a profile/router layer additively.

## Implementation Guidance

### Profile Schema

Use one small typed declaration module under `roboclaws/mcp/`.

Recommended fields:

- `profile_id`: stable id such as `ai2thor_navigation_v1`.
- `version`: integer schema/profile version.
- `backend`: implementation family such as `ai2thor` or `molmospaces`.
- `domain`: task domain such as `navigation` or `cleanup`.
- `capability_families`: tuple of declared families.
- `public_tools`: tuple of tool descriptors exposed by default.
- `accelerators`: tuple of opt-in tool descriptors excluded from canonical
  public tools.
- `privacy_exclusions`: forbidden key fragments checked against serialized
  public profile metadata.

Recommended tool descriptor fields:

- `name`: FastMCP/public tool name.
- `semantic_name`: capability/service name such as `perception.observe`.
- `family`: one of the declared capability families.
- `classification`: `canonical`, `composed`, or `accelerator`.
- `provenance`: accepted provenance vocabulary for the tool.
- `summary`: short maintainer-facing description.

### Naming And Registration

Keep current tool names for compatibility in this phase. Use semantic names in
metadata and docs so future profiles can converge without breaking existing
agents.

The generic entrypoint should load exactly one profile id and register only the
profile's `public_tools`. If an accelerator is requested without explicit
accelerator loading, fail before registration with an error naming the profile,
tool, and allowed profile ids.

### Provenance Vocabulary

Start with repo vocabulary already present in reports and plans:

- `api_semantic`
- `sim_planner`
- `simulator_metadata`
- `synthetic_contract`
- `camera_artifact`
- `simulated_camera_model`
- `planner_backed`
- `nav2_action`
- `blocked_capability`

Do not require every profile to use every value.

### Profile Mapping

`ai2thor_navigation_v1`:

- canonical public tools: `observe`, `observe_archived`, `move`, `done`;
- accelerators: `scene_objects`, `goto`;
- families: perception, localization, mapping, navigation, memory.

`molmospaces_cleanup_v1`:

- canonical public tools: `metric_map`, `fixture_hints`,
  `navigate_to_room`, `navigate_to_waypoint`, `observe`,
  `infer_camera_model_candidates`, `inspect_visible_object`,
  `navigate_to_object`, `pick`, `navigate_to_receptacle`,
  `open_receptacle`, `place`, `place_inside`, `close_receptacle`, `done`;
- accelerators: none in canonical ADR-0003 profile;
- families: perception, localization, mapping, navigation, manipulation.

### Validation Strategy

Fail closed in pure unit/contract tests:

- unknown profile ids fail before server registration;
- malformed descriptors fail validation;
- canonical profiles reject accelerator descriptors in `public_tools`;
- serialized Molmo profile metadata rejects private fields from ADR-0003 and
  ADR-0006;
- router registration exposes only tools declared by the selected profile;
- existing MCP tests stay green because current servers are not replaced.

## Risks And Mitigations

| Risk | Mitigation |
| --- | --- |
| Router becomes a renaming wrapper around unrelated tools. | Typed profile schema plus selected-profile registration tests. |
| `scene_objects` and `goto` look like real robot capabilities. | Keep them in `accelerators`, not canonical `public_tools`. |
| Molmo private truth leaks through profile metadata. | Reuse forbidden-key tests against serialized profile dictionaries. |
| Scope expands into live robot/Nav2 validation. | Keep ROS/Nav2 as vocabulary guidance only; no live integration in Phase 136. |
| Existing demos break. | Additive modules/tests only; current server factories remain unchanged. |

## Planning Recommendation

One plan is enough. Implement profile metadata and router registration together,
then update docs/skills and run focused fast tests. Do not split this into a
local-dev phase; the acceptance criteria are cloud-safe metadata and contract
tests.
