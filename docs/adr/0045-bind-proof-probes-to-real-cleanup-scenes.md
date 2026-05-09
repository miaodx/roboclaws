# 0045. Bind Proof Probes To Real Cleanup Scenes

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0044 added a local proof-bundle execute-rerun gate, but its first local run
started from a synthetic cleanup artifact. The generated proof requests carried
cleanup aliases such as `toy_car_01` and `sink_01`, while the RBY1M/CuRobo
probe sampled unrelated upstream MolmoSpaces tasks. The strict binding check
correctly refused to promote cleanup primitive evidence.

This exposed an architectural problem, not a report problem: proof execution
must sample from the same real MolmoSpaces scene and requested planner aliases
that produced the cleanup artifact. Synthetic artifacts can still prove the
shared semantic loop and report underlay, but they cannot prove exact
planner-backed cleanup primitive replacement.

## Decision

Planner proof request manifests will carry real cleanup scene metadata when the
backend exposes it. Proof-bundle commands will pass that scene XML into the
planner probe. The probe will use the cleanup scene, requested pickup object,
and requested target receptacle before sampling its upstream task, and its
report will show the exact-scene request.

The local execute-rerun gate will start from `backend=molmospaces_subprocess`
with robot views instead of synthetic cleanup. The dry-run runner harness may
remain synthetic because it only checks command/report shape.

## Consequences

- Exact sampled-task binding now has one real path through the shared cleanup
  architecture instead of a second synthetic proof implementation.
- The proof-bundle runner report shows which real scene the proof commands use.
- Local validation now exposes the next real blocker: some requested cleanup
  objects in the real scene fail upstream RBY1M task sampling with
  `HouseInvalidForTask` / robot placement infeasibility before sampled binding
  can be promoted.
