# 0039. Render Planner Proof Bundle Runner Reports

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0037 added a local runner that turns private cleanup proof request manifests
into exact bound `run_molmo_planner_manipulation_probe.py` commands. The runner
currently writes `proof_bundle_run_manifest.json`, but no visual report. That
breaks the MolmoSpaces demo pattern: every meaningful artifact should have a
reviewable `report.html`, especially when it is the local-dev handoff from a
cleanup artifact to real proof generation.

ADR-0038 made the originating cleanup report show proof requests. The next
artifact in that flow should be equally reviewable: which requests became
commands, which proof outputs are expected, and what cleanup rerun command will
consume the generated proof bundle.

## Decision

The planner proof bundle runner will write a `report.html` next to
`proof_bundle_run_manifest.json`. The report will show:

- source cleanup artifact;
- dry-run/executed status;
- proof request and command counts;
- one row per generated probe command;
- expected proof `run_result.json` and `report.html` paths;
- optional cleanup rerun command.

The report is command/evidence UI only. It does not claim real planner proof
unless the underlying proof run results exist and pass their own strict checks.

## Consequences

- Local operators can review and copy exact proof-generation commands from a
  browser-visible artifact.
- The local-dev handoff now has the same visible-output discipline as cleanup
  and planner probe artifacts.
- Real proof validity remains delegated to the individual planner probe reports
  and checkers.
