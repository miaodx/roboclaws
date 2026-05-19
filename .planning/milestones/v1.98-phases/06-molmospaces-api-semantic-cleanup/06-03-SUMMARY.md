# 06-03 Summary — Demo Report And Harness

**Commit:** `bbbbbaa feat: add MolmoSpaces cleanup harness`
**Status:** Complete

## Delivered

- Added `examples/molmospaces_cleanup_demo.py`, which writes `trace.jsonl`,
  `run_result.json`, `scenario.json`, `private_manifest.json`, `before.png`,
  `after.png`, and `report.html`.
- Added `roboclaws/molmo_cleanup/report.py` for deterministic room-state PNGs
  and a self-contained cleanup report.
- Added `scripts/prepare_molmospaces_room.py` and
  `scripts/check_molmospaces_cleanup_result.py`.
- Added `just harness::molmo-cleanup` and `just verify::molmo-cleanup`.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_molmo_cleanup_demo.py tests/test_verify_just_recipes.py`
- `just harness::molmo-cleanup`
- Commit hook fast non-integration pytest passed.

## Harness Result

`just harness::molmo-cleanup` produced
`output/molmo-cleanup-harness/run_result.json` with:

- `cleanup_status=success`
- `restored_count=5`
- `total_targets=5`
- `primitive_provenance=api_semantic`
