# MolmoSpaces Proof Request Fallback Generation

## Goal

When prior proof-bundle results show an exact cleanup-scene proof request is
RBY1M task-feasibility blocked, generate private alternate proof requests from
the same cleanup object/target binding metadata so the next runner dry-run has
explicit fallback commands to try.

## Scope

- Add a fallback-generation schema inside proof request selection.
- Generate fallback proof requests for task-feasibility-blocked source requests
  by varying private planner object and target aliases already emitted by the
  observed-handle binding.
- Keep cleanup-facing `object_id`, `target_receptacle_id`, source receptacle,
  and semantic tools unchanged so any later promoted proof still binds to the
  same cleanup subphases.
- Add runner CLI flags to enable fallback generation and cap generated alias
  attempts.
- Render generated fallback requests in the proof-bundle runner report.
- Extend the runner checker to validate generated fallback request rows and
  generated command counts.

## Acceptance

- With prior blocked proof results and fallback generation enabled, the runner
  emits generated fallback proof requests and commands instead of stopping at
  `fallback_required`.
- Generated fallback requests are private runner artifacts only; they do not
  change Agent View or the original cleanup artifact.
- Generated fallback commands preserve cleanup-facing IDs while substituting
  alternate private planner aliases.
- If no alternate alias is available, the report still shows fallback required
  and explains that no generated request was available.
- Focused tests cover generation, CLI wiring, report rendering, and checker
  validation.

## Out Of Scope

- Proving a generated fallback passes RBY1M/CuRobo execution.
- Creating a new cleanup run or changing the hidden Generated Mess Set.
- Relaxing strict cleanup primitive binding or bridge-readiness requirements.

## Result - 2026-05-10

Phase 57 implemented bounded private fallback generation in the proof-bundle
runner. A dry-run against `output/debug-real-binding/run_result.json` with a
synthetic prior blocked summary generated four fallback commands, rendered the
`Generated Fallback Requests` report table, and passed the runner checker.
