# 0048. Generate Private Fallback Proof Requests

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0047 lets the proof-bundle runner skip requests already known to be
RBY1M task-feasibility blocked. That prevents repeated local GPU work, but it
also creates a dead end: if every current request is blocked, the runner can
only report that fallback generation is required.

The cleanup artifact already contains private observed-handle binding metadata
with candidate planner-facing pickup and place names. Those aliases are not
part of Agent View, but they are exactly the private data a local proof runner
can use to produce alternate exact-scene probe commands. The next useful step
is to generate bounded fallback requests from that existing metadata while
keeping the cleanup-facing object/target identity stable.

## Decision

Proof request selection will optionally generate private fallback proof requests
for source requests excluded because their prior proof result was
`task_feasibility_status=blocked`.

Generated fallback requests will:

- keep the same cleanup-facing `object_id`, `target_receptacle_id`, source
  receptacle, and semantic tool list as the source request;
- vary only private planner-facing object/target aliases from the existing
  observed-handle binding candidate lists;
- carry `source_request_id`, fallback reason, prior blockers, and alias
  metadata in the runner manifest and report;
- be selected by the runner exactly like normal ready requests when fallback
  generation is enabled.

The runner report and checker will render and validate generated fallback
requests separately from the original selected/excluded rows.

## Consequences

- Local dry-runs can move from "all current requests blocked" to an explicit,
  reviewable set of fallback probe commands.
- The original cleanup artifact remains unchanged, and generated aliases remain
  private runner evidence.
- A generated request is not a proven feasible proof. It is a bounded retry
  candidate; real RBY1M/CuRobo execution and the strict proof checker still
  decide whether it can promote cleanup primitive binding.
