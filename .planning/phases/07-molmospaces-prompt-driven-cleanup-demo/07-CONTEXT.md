# Phase 7: MolmoSpaces prompt-driven cleanup demo - Context

**Gathered:** 2026-05-07
**Status:** Ready for execution
**Source:** `docs/plans/molmospaces-manipulation-spike.md`
**Predecessor:** Phase 6 shipped the `api_semantic` cleanup scaffold.

<domain>
## Phase Boundary

Turn the Phase 6 scaffold into a prompt-driven cleanup artifact for
`帮我整理这个房间` / `帮我收拾这个房间`.

This phase must prove that the cleanup loop can choose actions from public room
state and public tool responses, not from the private scoring manifest.

This phase must produce:

- A public-only cleanup planner/policy that consumes `observe` /
  `scene_objects` payloads and task text.
- A demo runner mode that uses the public policy for `帮我整理这个房间`.
- Harness and verify gates that fail if the run uses the private manifest as the
  planner.
- Artifacts that still label primitive execution as `api_semantic` until real
  RBY1M/Franka planner-backed manipulation is proven.

Not in scope:

- Real robot grasping or planner-backed pick/place.
- OpenClaw Gateway routing.
- Top-level `molmo_spaces` import or a repo Python-version migration.
- Multi-agent MolmoSpaces.

</domain>

<decisions>
## Implementation Decisions

### D-01: Public policy before real model
The deterministic harness uses a small public-domain cleanup policy so tests can
prove the action loop without a VLM. The policy is a stand-in for a coding agent:
it may use object names/categories and receptacle names/kinds, but must not read
`scenario.private_manifest`.

### D-02: Prompt-driven is not yet real manipulation
The run can be prompt-driven and still `api_semantic`. These are separate axes:
planner source (`public_heuristic`, future `coding_agent`) and primitive
provenance (`api_semantic`, future `real`).

### D-03: Private manifest remains scorer-only
The private manifest may only be used by `done()` / `score_cleanup(...)` and by
post-run verification. It must not drive the planner.

</decisions>

<acceptance>
## Phase Acceptance Criteria

- `just harness::molmo-prompt-cleanup` exits 0 and writes a deterministic run
  under `output/molmo-prompt-cleanup-harness/`.
- `run_result.json` records `task_prompt="帮我整理这个房间"`,
  `planner=public_heuristic`, `planner_uses_private_manifest=false`,
  `cleanup_status=success`, and `restored_count >= 3`.
- The trace includes `observe`, `scene_objects`, `goto`, `pick`, `place`, and
  `done` events from the public-policy loop.
- Focused tests cover policy target inference, skipped already-correct objects,
  no private-manifest planner dependency, and artifact schema.
- Source plan and roadmap distinguish Phase 6 scaffold from Phase 7 prompt
  proof.

</acceptance>

---

*Phase: 07-molmospaces-prompt-driven-cleanup-demo*
*Context gathered: 2026-05-07 from the active hybrid plan*
