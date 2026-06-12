# 0035. Use Bound Planner Proof Bundles for Cleanup Coverage

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0034 added an opt-in path that can route one matching observed-handle
cleanup attempt through the probe-backed planner executor. This proves the
shared semantic cleanup loop has a real executor integration point, but a normal
ADR-0003 cleanup run still contains several objects. One proof can make one
object planner-backed while the remaining objects stay `api_semantic`, so the
overall cleanup primitive gate and planner cleanup bridge remain blocked.

The next integration gap is proof coverage. A full cleanup artifact should be
able to attach multiple strict bound planner proofs and select the proof whose
cleanup primitive binding matches each observed object and target fixture.

## Decision

Represent multiple attached strict planner proofs as a cleanup proof bundle.
The bundle preserves each proof attachment, each cleanup primitive binding, and
each proof's visual artifacts. During cleanup, the ADR-0003 harness may select a
matching proof attachment per observed object and target fixture, then wrap only
that object's semantic loop with the probe-backed executor.

The existing single-proof path remains supported. Default cleanup still remains
`api_semantic`, and a missing or mismatched proof for any object must not be
silently reused for another object.

## Consequences

- Synthetic and future real artifacts can demonstrate the full cleanup
  primitive gate using proof coverage across all cleaned objects.
- The report can show one visual underlay with multiple attached proof views
  instead of creating another report implementation.
- This still does not prove that one live planner session autonomously generated
  every proof. The artifact only claims planner-backed cleanup when every
  cleanup subphase has per-call executor evidence bound to its object and
  target.
