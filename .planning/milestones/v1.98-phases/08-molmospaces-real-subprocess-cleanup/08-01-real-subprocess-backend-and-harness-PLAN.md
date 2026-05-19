---
phase: 08
plan: 01
slug: real-subprocess-backend-and-harness
type: execute
wave: 1
depends_on: [07]
files_modified:
  - scripts/molmospaces_subprocess_worker.py
  - roboclaws/molmo_cleanup/subprocess_backend.py
  - roboclaws/molmo_cleanup/mcp_contract.py
  - roboclaws/molmo_cleanup/policy.py
  - roboclaws/molmo_cleanup/report.py
  - examples/molmospaces_cleanup_demo.py
  - scripts/check_molmospaces_cleanup_result.py
  - just/harness.just
  - just/verify.just
  - tests/test_molmo_cleanup_demo.py
  - tests/test_molmo_cleanup_subprocess_backend.py
  - tests/test_verify_just_recipes.py
  - docs/retrospectives/plans/molmospaces-manipulation-spike.md
  - .planning/ROADMAP.md
  - .planning/STATE.md
  - .planning/milestones/v1.98-phases/08-molmospaces-real-subprocess-cleanup/08-VERIFICATION.md
autonomous: true
requirements_addressed: [MOLMO-REAL-01, MOLMO-REAL-02, MOLMO-REAL-03]
---

<objective>
Replace the prompt cleanup proof's synthetic backend with a real upstream
MolmoSpaces/MuJoCo subprocess backend while preserving public-only planning and
scorer-only private manifests.
</objective>

<tasks>

<task type="tdd">
  <name>Task 1: Add isolated subprocess backend</name>
  <action>
    Add a Python 3.10 wrapper that shells into the isolated Python 3.11
    MolmoSpaces runtime. Add a worker that installs/loads an upstream
    `procthor-10k-val` scene, reads scene metadata and MuJoCo state, seeds a
    deterministic easy cleanup setup, and mutates real MuJoCo free-joint `qpos`
    on `place`.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_subprocess_backend.py</automated>
  </verify>
</task>

<task type="tdd">
  <name>Task 2: Wire public prompt demo to the real backend</name>
  <action>
    Extend `examples/molmospaces_cleanup_demo.py` with
    `--backend molmospaces_subprocess`; keep the public heuristic planner using
    only `observe` / `scene_objects` output. Record backend, runtime, scene
    stats, artifact paths, primitive provenance summary, and
    `planner_uses_private_manifest=false` in `run_result.json`.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_policy.py tests/test_molmo_cleanup_demo.py tests/test_verify_just_recipes.py</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 3: Add harness and verify gates</name>
  <action>
    Add `just harness::molmo-real-cleanup` and
    `just verify::molmo-real-cleanup`. The checker must assert
    `backend=molmospaces_subprocess`, the exact Chinese prompt, and
    public-planner/private-scorer separation.
  </action>
  <verify>
    <automated>just verify::molmo-real-cleanup</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 4: Record verification and update source truth</name>
  <action>
    Update the hybrid plan, roadmap, state, and phase verification evidence with
    the real-runtime result and the remaining boundary that
    `primitive_provenance=real` is still deferred until planner-backed
    manipulation is proven.
  </action>
</task>

</tasks>

<success_criteria>
- `run_result.json` records `backend=molmospaces_subprocess`.
- The backend loads a real upstream MolmoSpaces/MuJoCo scene through Python
  3.11 and records runtime/model stats.
- `scene_objects` and scoring read real scene/MuJoCo state.
- The prompt `帮我整理这个房间` runs through the public cleanup loop.
- Planner does not read `private_manifest`.
- Required artifacts exist: `before.png`, `after.png`, `trace.jsonl`,
  `run_result.json`, and `report.html`.
- Primitive provenance is `api_semantic`, not `real`, and the implementation
  mutates real MuJoCo state.
</success_criteria>
