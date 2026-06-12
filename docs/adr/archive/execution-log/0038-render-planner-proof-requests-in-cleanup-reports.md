# 0038. Render Planner Proof Requests In Cleanup Reports

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0037 makes completed ADR-0003 cleanup artifacts emit private planner proof
request manifests. That closes the machine-readable handoff from cleanup runs
to local proof-bundle generation, but the shared `report.html` still does not
show whether a run produced proof requests, which requests are ready, or which
cleanup object/target bindings are blocked.

The project already treats cleanup reports as the primary review artifact.
Phase 45 made the report visual core canonical across current-contract and
ADR-0003 runs, and the broader MolmoSpaces plan requires new evidence to remain
visually reviewable instead of living only in sidecar JSON.

## Decision

Cleanup Artifact Reports will render a `Planner Proof Requests` section whenever
`run_result.json` contains a `planner_cleanup_proof_requests_v1` manifest. The
section will summarize ready/blocked request counts and list each cleanup-facing
request with its semantic tools, source fixture, target fixture, and private
planner aliases.

The section remains post-run private evidence. It must not become Agent View,
must not alter public traces, and must sit with the other planner/private
evidence panels after the visual core and before the Agent View section.

## Consequences

- Reviewers can see the proof-generation handoff directly in `report.html`.
- Planner aliases remain private report/evaluation evidence, not Cleanup Agent
  input.
- Existing artifacts without planner proof requests remain valid; the section is
  present only when the manifest exists.
