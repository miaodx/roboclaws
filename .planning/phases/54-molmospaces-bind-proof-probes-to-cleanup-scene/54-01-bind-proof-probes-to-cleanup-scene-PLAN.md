# 54-01 Bind Proof Probes To Cleanup Scene Plan

## Goal

Close the architecture gap where proof-bundle execution sampled unrelated
MolmoSpaces tasks instead of the cleanup artifact's real scene/object/target.

## Tasks

1. Add ADR/source-plan context for real cleanup-scene proof binding.
2. Extend planner proof requests and proof-bundle commands with cleanup scene
   metadata.
3. Configure planner probes to sample from the cleanup scene and requested
   pickup/target aliases.
4. Move the local execute-rerun harness to real MolmoSpaces cleanup with robot
   views.
5. Verify with focused unit tests and a local exact-scene probe artifact.

## Verification

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/run_molmo_planner_proof_bundle_from_requests.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_verify_just_recipes.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/run_molmo_planner_proof_bundle_from_requests.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_verify_just_recipes.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_verify_just_recipes.py tests/test_molmo_cleanup_report.py`
- Local probe: run one exact-scene RBY1M/CuRobo proof request from a real
  `molmospaces_subprocess` cleanup artifact and record whether it promotes
  binding or exposes a narrower upstream task-feasibility blocker.

## Result

Implemented. Exact cleanup-scene commands are generated and the local probe now
loads the requested real cleanup scene. Validation exposes the next blocker:
upstream RBY1M task sampling rejects the requested cleanup objects with
`HouseInvalidForTask` / robot placement infeasibility before sampled binding can
be promoted.
