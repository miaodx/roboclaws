---
phase: 06
plan: 03
slug: demo-report-and-harness
type: execute
wave: 3
depends_on: [06-01, 06-02]
files_modified:
  - roboclaws/molmo_cleanup/report.py
  - examples/molmospaces_cleanup_demo.py
  - scripts/prepare_molmospaces_room.py
  - just/harness.just
  - just/verify.just
  - tests/test_molmo_cleanup_demo.py
  - tests/test_molmo_cleanup_report.py
autonomous: true
requirements_addressed: [MOLMO-CLEANUP-05, MOLMO-CLEANUP-06]
---

<objective>
Produce the visible cleanup artifact: deterministic demo runner, report.html,
run_result.json, trace.jsonl, and a named harness gate.
</objective>

<tasks>

<task type="tdd">
  <name>Task 1: Render cleanup report artifacts</name>
  <action>
    Add report rendering that shows the public task, object move table, final
    private score, and `api_semantic` provenance. Keep it self-contained and
    deterministic.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py</automated>
  </verify>
</task>

<task type="tdd">
  <name>Task 2: Add deterministic demo and harness recipe</name>
  <action>
    Add `scripts/prepare_molmospaces_room.py` for scenario materialization and
    `examples/molmospaces_cleanup_demo.py` for a deterministic scripted cleanup
    over the direct MCP-style contract. Add `just harness::molmo-cleanup` and
    `just verify::molmo-cleanup` as focused gates.
  </action>
  <verify>
    <automated>just harness::molmo-cleanup</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- The demo writes `trace.jsonl`, `run_result.json`, `report.html`, and state
  snapshots under the requested output directory.
- The harness recipe exits 0 and checks the run result.
- The verify recipe delegates execution to the harness namespace.
</success_criteria>
