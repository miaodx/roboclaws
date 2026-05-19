---
phase: 07
plan: 01
slug: public-cleanup-policy
type: execute
wave: 1
depends_on: []
files_modified:
  - roboclaws/molmo_cleanup/policy.py
  - tests/test_molmo_cleanup_policy.py
autonomous: true
requirements_addressed: [MOLMO-PROMPT-01, MOLMO-PROMPT-02]
---

<objective>
Add a public-only cleanup policy that turns task text plus public
`scene_objects` state into object/receptacle cleanup actions.
</objective>

<tasks>

<task type="tdd">
  <name>Task 1: Infer cleanup targets from public state</name>
  <action>
    Add `roboclaws/molmo_cleanup/policy.py`. The policy consumes the task prompt,
    public objects, and public receptacles. It maps household categories/names to
    suitable receptacle names using public information only.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_policy.py</automated>
  </verify>
</task>

<task type="tdd">
  <name>Task 2: Avoid private-manifest and no-op dependency</name>
  <action>
    Tests must prove the policy never requires `valid_receptacle_ids`,
    `private_manifest`, or `success_threshold`, and skips objects already located
    at the inferred target.
  </action>
  <verify>
    <automated>./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_policy.py</automated>
  </verify>
</task>

</tasks>

<success_criteria>
- The policy restores the default five misplaced objects using only public
  object/receptacle data.
- The policy ignores non-target public objects such as the TV remote.
- No MolmoSpaces dependency or real VLM dependency is introduced.
</success_criteria>
