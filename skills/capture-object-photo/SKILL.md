---
name: capture-object-photo
description: Capture labeled photos of target objects using the AI2-THOR navigation MCP surface as a skill-level behavior, not a new MCP tool.
---

# Capture Object Photo

Use this skill when the operator asks for photos of objects in an AI2-THOR
scene, for example "photograph every sofa and chair." This is an agent skill
that composes lower-level tools; it is not a new MCP capability.

## Boundary

The skill runs over `ai2thor_navigation_v1`:

- Canonical capability tools: `roboclaws__observe`,
  `roboclaws__observe_archived`, `roboclaws__move`, `roboclaws__done`.
- Privileged AI2-THOR demo helpers: `roboclaws__scene_objects`,
  `roboclaws__goto`.

Use the privileged helpers when the goal is an efficient AI2-THOR demo or
harness run. Do not describe them as real-robot perception or real-robot
navigation.

## Flow

1. Call `roboclaws__observe(label="preflight")` if no fresh observation exists.
2. Call `roboclaws__scene_objects(filter_types="Sofa,Chair,ArmChair")`, adjusted
   to the requested object types.
3. Plan the route from the returned `objects` list. Nearest-first is the default.
   If you can run local scripts, you may save the JSON and run:

   ```bash
   python skills/capture-object-photo/scripts/plan_capture_route.py \
     --input scene-objects.json \
     --filter-types Sofa,Chair,ArmChair \
     --pretty
   ```

4. For each target in the route:
   - call `roboclaws__goto(object_id=<objectId>, distance=1.0, face=True)`;
   - call `roboclaws__observe(label="<type>-<index>")` to verify framing and
     capture the labeled snapshot;
   - if framing needs one small correction, use one `roboclaws__move(...)` and
     then `roboclaws__observe_archived(label="<type>-<index>")`.
5. Call `roboclaws__done(reason="Photographed ...")` and list every label in
   the reason.

## Capture Rules

- Use lowercase hyphenated labels: `sofa-1`, `chair-1`, `armchair-1`.
- Prefer one subject per frame. If two objects dominate the view, move or strafe
  so the requested target is the clear subject.
- Always use labeled observe calls for final evidence. Unlabeled `latest.*.png`
  files are live-view aids, not durable photo evidence.
- Keep the report honest: the useful composite action here is
  `locate -> navigate -> observe_archived/observe -> done`, owned by this skill.
  Promote no new MCP tool unless several skills need the same stable capability
  boundary.
