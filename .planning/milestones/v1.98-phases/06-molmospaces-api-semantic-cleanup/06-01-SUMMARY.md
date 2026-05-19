# 06-01 Summary — Scenario Contracts And Scorer

**Commit:** `8388ed3 feat: add MolmoSpaces cleanup scenario scoring`
**Status:** Complete

## Delivered

- Added `roboclaws/molmo_cleanup/types.py`, `scenario.py`, and `scoring.py`.
- Added deterministic default cleanup scenario with six public objects and five
  private scoring targets.
- Split public `scenario.json` from private `private_manifest.json`.
- Added private scorer with success at `restored_count >= 3`.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_scenario.py tests/test_molmo_cleanup_scoring.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup tests/test_molmo_cleanup_scenario.py tests/test_molmo_cleanup_scoring.py`
- Commit hook fast non-integration pytest passed.

## Boundary

The public scenario exposes current object/receptacle state only. It does not
expose `valid_receptacle_ids`, `success_threshold`, or the private manifest.
