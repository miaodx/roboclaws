# MolmoSpaces Proof Request Feasibility Selection

## Goal

Use prior proof-result summaries to avoid rerunning exact-scene proof requests
that are already known to be RBY1M task-feasibility blocked, and make the
fallback-required state visible in the proof-bundle runner report.

## Scope

- Add a proof request selection schema to proof-bundle manifests.
- Let the proof-bundle runner consume a prior bundle manifest and exclude
  requests with prior `task_feasibility_status=blocked`.
- Render selected/excluded requests and fallback-required status in
  `report.html`.
- Extend the runner checker to validate the selection section.
- Keep fallback generation out of scope; this phase selects among current
  requests only.

## Acceptance

- Without a prior manifest, every ready request is selected.
- With a prior manifest and task-feasibility exclusion enabled, previously
  blocked requests are excluded from generated commands.
- If every ready request is excluded, the report shows fallback required.
- The selection section does not expose planner aliases to Agent View; it only
  appears in the private runner report.
- Focused tests cover selection construction, command filtering, runner CLI
  behavior, report rendering, and checker validation.

## Out Of Scope

- Generating alternate object/target proof requests.
- Making `HouseInvalidForTask` pass.
- Changing strict cleanup bridge readiness requirements.
