# 0080. Scope Proof Selection Memory by Planner Object

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0075 matched prior proof selection memory by public cleanup object/target
pair when regenerated manifests changed request IDs. ADR-0079 then made later
proof-bundle manifests complete prior-evidence carriers.

Phase 89 generated a broader ADR-0003 source cleanup artifact with 10 ready
planner proof requests. That exposed two identity gaps:

- `request_id` values such as `proof_001` are local to one source artifact and
  can collide across independent cleanup runs.
- public `observed_*` handles are also local to a cleanup run, so the same
  internal planner object can reappear under a different public handle.

Bare request-ID memory could therefore hide genuinely new candidates, while
cleanup-pair-only memory could retry a known blocked planner object when it
was observed under a new public handle.

## Decision

Treat prior proof selection memory as scoped identity, not global request-ID
state.

Selection now matches prior proof results in this order:

1. guarded `request_id`, only when the current request and prior result also
   agree on a complete public cleanup pair or planner-object/public-target
   pair;
2. public cleanup `object_id` plus `target_receptacle_id`;
3. internal planner object alias plus public target receptacle.

The third key is private runner evidence. It is used only inside proof request
selection and proof-bundle runner reports; it does not enter Agent View or
change the cleanup report contract.

## Consequences

- Broader cleanup artifacts can reuse local IDs like `proof_001` without
  inheriting unrelated blockers.
- Known grasp-infeasible internal object/target pairs stay filtered even when
  public `observed_*` handles change.
- The runner keeps one underlying proof-selection implementation shared by
  source requests, standalone prior results, nested prior manifests, fallback
  memory, and report rendering.
- The next capability step is now executing the selected broader exact-scene
  candidates, not adding another report path.

## Evidence

Phase 89 validates planner-object proof memory with:

- regression coverage that a colliding `request_id` does not exclude a
  different cleanup pair;
- regression coverage that prior blockers match by planner object plus public
  target when a new source artifact gives the same object a different observed
  handle;
- a broader 10-object source artifact at
  `output/debug-phase89-broader-candidate-source/`;
- a post-fix dry-run at
  `output/debug-phase89-planner-pair-selection-dry-run/`, where 10 ready proof
  requests produced 8 selected commands and excluded only the two known
  grasp-infeasible internal book/shelf and bowl/sink planner-object pairs.

Verification on 2026-05-10:

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase89-broader-candidate-source/run_result.json`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase89-planner-pair-selection-dry-run/proof_bundle_run_manifest.json`
