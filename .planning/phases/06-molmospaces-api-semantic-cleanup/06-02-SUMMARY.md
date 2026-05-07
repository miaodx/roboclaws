# 06-02 Summary — API-Semantic Backend And MCP Contract

**Commit:** `26e6552 feat: add MolmoSpaces cleanup tool contract`
**Status:** Complete

## Delivered

- Added `ApiSemanticCleanupBackend` with `observe`, `scene_objects`, `goto`,
  `pick`, `place`, and `done`.
- Added direct-call `MolmoCleanupToolContract` so tests and demos can exercise
  MCP-style tools without binding a network server.
- Added structured `stale_reference`, `not_holding`, and `already_holding`
  errors.
- Labeled semantic movement primitives with `primitive_provenance=api_semantic`.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_backend.py tests/test_molmo_cleanup_mcp_contract.py tests/test_molmo_cleanup_scenario.py tests/test_molmo_cleanup_scoring.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup tests/test_molmo_cleanup_backend.py tests/test_molmo_cleanup_mcp_contract.py tests/test_molmo_cleanup_scenario.py tests/test_molmo_cleanup_scoring.py`
- Commit hook fast non-integration pytest passed.

## Boundary

This is a fake/MolmoSpaces-shaped contract harness. It does not import
MolmoSpaces and does not claim real robot manipulation.
