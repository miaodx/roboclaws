# MCP Skills and Semantic Profiles

This note is the small human-facing explanation of how Roboclaws connects
agent skills, MCP tools, and semantic robot capabilities. It is meant for
teammates who need the design logic without reading the GSD phase logs.

## The Short Version

A user gives a **task prompt** such as "take photos of the chairs" or "clean the
room." Roboclaws should not turn that whole task into one giant MCP tool.
Instead:

1. The **agent skill** tells the model how to work in this environment.
2. The **MCP server** exposes the tools the agent may call.
3. The **semantic contract profile** describes which tools are canonical robot
   capabilities for that backend/domain, and which tools are only accelerators.
4. The **report/checker path** records what the agent did and which claims are
   public, private, semantic, or planner-backed.

The profile layer is metadata and routing discipline. It does not replace the
existing AI2-THOR or MolmoSpaces MCP servers.

## Why This Exists

Roboclaws now has two useful but different robot-demo stacks:

- AI2-THOR navigation, where simulator metadata can provide helpful shortcuts
  like full object inventory and teleport-like target positioning.
- MolmoSpaces cleanup, where private evaluator truth must stay hidden from the
  cleanup agent and manipulation claims need provenance.

Without a shared vocabulary, it is easy to blur these layers:

- A demo recipe such as `just task::run molmo-cleanup claude world-labels` can
  look like the user's open-ended task.
- A simulator helper such as `scene_objects` can look like real robot
  perception.
- A semantic state edit can look like planner-backed manipulation.

Semantic profiles make those boundaries explicit while preserving the fast demo
paths that are useful for development.

## Layer Model

| Layer | Owns | Examples | What to watch |
| --- | --- | --- | --- |
| Task prompt | User intent | "clean the room", "photograph all chairs" | Do not collapse this into one opaque MCP tool. |
| Agent skill | Operating instructions for a model | `skills/ai2thor-navigator/SKILL.md` | Skills may recommend accelerators, but should say they are accelerators. |
| MCP server | Concrete callable tool surface | AI2-THOR navigation server, Molmo cleanup server | Server tools are real callables, not all equally canonical. |
| Semantic profile | Public capability contract and exclusions | `ai2thor_navigation_v1`, `molmospaces_cleanup_v1` | Profiles must not expose private evaluator truth or simulator-only shortcuts as canonical capabilities. |
| Report/checker | Evidence and claim boundary | trace JSONL, cleanup report, planner proof report | Reports say what happened and what level of proof backs it. |

## Current Profiles

### `ai2thor_navigation_v1`

Canonical public capability tools:

- `observe`
- `observe_archived`
- `move`
- `done`

Accelerator exclusions:

- `scene_objects` is an AI2-THOR object-inventory oracle.
- `goto` is a target-relative teleport-style helper.

Those accelerators remain available on the demo server because they make photo
tasks and harness iterations efficient. They are not presented as real robot
perception or real robot navigation capabilities.

### `molmospaces_cleanup_v1`

Canonical public capability tools include the ADR-0003 cleanup surface:

- public map and fixture context;
- waypoint/object/receptacle navigation;
- public observation and inspection;
- pick/place/open/close operations;
- episode completion.

The profile is public-agent metadata only. It must not expose generated mess
sets, acceptable destinations, private manifests, hidden target lists,
`is_misplaced`, private scoring truth, or AI2-THOR object inventory shortcuts.

## Design Considerations

### Keep Profiles Backend/Domain Specific

There is no premature universal robot API here. A navigation-only AI2-THOR
profile and a cleanup-oriented MolmoSpaces profile can share capability-family
names while exposing different tools.

Future profiles can combine environment and task domain, for example:

- `real_robot_cleanup_v1`
- `ai2thor_photo_v1`
- `molmospaces_camera_cleanup_v1`

### Keep Planning in the Agent

The model should plan over capabilities. MCP should expose bounded abilities
and semantic services, not whole-task tools like `cleanup_room()`.

This keeps the agent behavior inspectable: the report can show the steps the
agent chose instead of hiding the work behind one tool call.

### Treat Accelerators Honestly

Accelerators are allowed when they are useful for demos, debugging, or cheap
proof loops. They must be labeled as accelerators and excluded from canonical
profile metadata unless redesigned as composed semantic services with traceable
substeps.

### Preserve Public/Private Boundaries

Molmo cleanup has a hard boundary between the agent's public view and private
evaluation truth. Profile metadata belongs on the public side, so it must fail
closed if private evaluator terms leak into serialized metadata.

### Keep Existing Servers Stable

The profile/router layer is additive. Existing servers, command recipes, and
reports continue to work. Profiles give us a cleaner way to describe and later
route selected tool surfaces.

## How a Request Flows

```text
User task prompt
  -> agent skill explains operating strategy and tool etiquette
  -> selected MCP server exposes concrete tools
  -> semantic profile declares canonical public tools and exclusions
  -> agent calls tools
  -> trace/report/checker records behavior and proof level
```

For AI2-THOR photo tasks, the skill may still tell the agent to use
`scene_objects` and `goto` because the goal is an efficient demo artifact.
The semantic profile still records that these are accelerators, not general
robot capabilities.

For Molmo cleanup, the profile keeps the public cleanup surface separate from
private scoring and planner proof evidence. A clean report can therefore be
honest about whether the result is `api_semantic`, `planner_backed`, or
`blocked_capability`.

## Adding a New Profile

When adding a profile, start from the contract, not the implementation helper:

1. Name the backend/domain profile, such as `<environment>_<task-domain>_v1`.
2. List capability families: perception, localization, mapping, navigation,
   manipulation, memory, and episode.
3. List canonical public tools.
4. List accelerators separately.
5. List private terms that must never appear in public metadata.
6. Add contract tests that prove profile validation fails closed.
7. Update the relevant human doc if the new profile changes how teammates
   should reason about the system.

Do not add a new profile just to rename a demo recipe. Demo recipes choose how
to run a scenario; semantic profiles describe what public robot capabilities
the agent is allowed to rely on.

## Where to Look in the Repo

| Need | File |
| --- | --- |
| Profile declarations and built-ins | `roboclaws/mcp/profiles.py` |
| Generic profile router helper | `roboclaws/mcp/entrypoint.py` |
| AI2-THOR navigation MCP server | `roboclaws/mcp/server.py` |
| Molmo cleanup MCP server | `roboclaws/molmo_cleanup/realworld_mcp_server.py` |
| AI2-THOR agent skill | `skills/ai2thor-navigator/SKILL.md` |
| Profile/router contract tests | `tests/contract/mcp/test_semantic_profiles.py` |

Planning artifacts for Phase 136 explain the implementation history, but this
document is the human entry point for sharing the architecture with teammates.
