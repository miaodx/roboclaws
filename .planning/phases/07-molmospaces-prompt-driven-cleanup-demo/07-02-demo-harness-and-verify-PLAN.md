---
phase: 07
plan: 02
slug: demo-harness-and-verify
type: execute
wave: 2
depends_on: [07-01]
files_modified:
  - examples/molmospaces_cleanup_demo.py
  - scripts/check_molmospaces_cleanup_result.py
  - just/harness.just
  - just/verify.just
  - tests/test_molmo_cleanup_demo.py
  - tests/test_verify_just_recipes.py
  - .planning/phases/07-molmospaces-prompt-driven-cleanup-demo/07-VERIFICATION.md
  - docs/plans/molmospaces-manipulation-spike.md
  - .planning/ROADMAP.md
autonomous: true
requirements_addressed: [MOLMO-PROMPT-03, MOLMO-PROMPT-04]
---

<objective>
Wire the public policy into a prompt cleanup harness so
`帮我整理这个房间` succeeds without using the private manifest as planner input.
</objective>

<tasks>

<task type="tdd">
  <name>Task 1: Add prompt-driven demo mode</name>
  <action>
    Extend the cleanup demo runner with `--planner public_heuristic` and
    `--task "帮我整理这个房间"`. The run result must record the prompt, planner,
    whether the planner used the private manifest, and primitive provenance.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_demo.py</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 2: Add harness and verify recipes</name>
  <action>
    Add `just harness::molmo-prompt-cleanup` and
    `just verify::molmo-prompt-cleanup`. The checker should fail when the prompt
    run reports `planner_uses_private_manifest=true`.
  </action>
  <verify>
    <automated>just verify::molmo-prompt-cleanup</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 3: Record verification and update source truth</name>
  <action>
    Write Phase 7 verification evidence and update the source hybrid plan plus
    roadmap so the next state is clear.
  </action>
</task>

</tasks>

<success_criteria>
- `just verify::molmo-prompt-cleanup` passes.
- `run_result.json` proves prompt-driven public planning and scorer-only private
  manifest use.
- Existing `just verify::molmo-cleanup` remains green.
</success_criteria>
