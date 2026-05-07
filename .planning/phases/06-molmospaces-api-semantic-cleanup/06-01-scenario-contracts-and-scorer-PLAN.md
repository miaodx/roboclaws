---
phase: 06
plan: 01
slug: scenario-contracts-and-scorer
type: execute
wave: 1
depends_on: []
files_modified:
  - roboclaws/molmo_cleanup/types.py
  - roboclaws/molmo_cleanup/scenario.py
  - roboclaws/molmo_cleanup/scoring.py
  - tests/test_molmo_cleanup_scenario.py
  - tests/test_molmo_cleanup_scoring.py
autonomous: true
requirements_addressed: [MOLMO-CLEANUP-01, MOLMO-CLEANUP-02]
---

<objective>
Define the deterministic cleanup scenario, public/private manifest split, and
private scorer before any backend primitives are implemented.
</objective>

<tasks>

<task type="tdd">
  <name>Task 1: Pin the public/private scenario contract</name>
  <action>
    Add `roboclaws/molmo_cleanup/types.py` and `scenario.py` with dataclasses or
    typed dictionaries for cleanup objects, receptacles, public scenario payload,
    private scoring manifest, and scene state.

    The public scenario must include object IDs, names, current locations,
    receptacle IDs, and task text. It must not include each object's valid target
    set.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_scenario.py</automated>
  </verify>
</task>

<task type="tdd">
  <name>Task 2: Implement private scoring</name>
  <action>
    Add `scoring.py` with a deterministic `score_cleanup(...)` function that
    compares final object locations against the private manifest and returns
    restored/missed object IDs, restored count, total targets, and success status.
    Phase success is `restored_count >= 3` for the default five-object scenario.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_scoring.py</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- Tests prove the public payload cannot leak private valid targets.
- Scoring distinguishes success, partial, and stale/incomplete cleanup states.
- No MolmoSpaces dependency or import is introduced.
</success_criteria>
