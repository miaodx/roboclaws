# Phase 10 Context - MolmoSpaces Semantic Substeps

## Source Feedback

The Phase 09 report made FPV much more readable, but artifact review surfaced
two remaining semantic gaps:

- Non-focused `before` / `observe` / `scene_objects` verification panels look
  broken because there is no focused target and the report-only camera does not
  include the robot.
- The manipulation loop is still too coarse. It jumps straight to the target
  receptacle before `pick`, then places there. A reviewable robot cleanup should
  show object-side navigation, pick, target-side navigation, optional
  receptacle opening, placement, and object-level completion.

## Existing Boundaries

- Keep the real upstream MolmoSpaces/MuJoCo subprocess backend.
- Keep the public cleanup planner public-only; it must not read
  `private_manifest`.
- Keep `primitive_provenance=api_semantic` until planner-backed RBY1M/Franka
  pick/place is proven.
- FPV/chase must remain real RBY1M MuJoCo cameras.
- Verification panels are public MuJoCo state report aids and must be labeled
  as such.

## Key Design Decision

Semantic substeps are report/runtime steps, not separate GSD phases per object.
GSD Phase 10 owns the implementation; each object in the run gets a public
semantic substep sequence:

`navigate_to_object -> pick -> navigate_to_receptacle -> optional open_receptacle -> place/place_inside -> object_done`

For fridge targets, `open_receptacle` should mutate the real articulated
fridge joint qpos, and `place_inside` should record containment/readback rather
than leaving the apple visible outside the refrigerator.
