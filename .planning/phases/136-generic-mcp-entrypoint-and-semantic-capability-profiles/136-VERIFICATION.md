# Phase 136 Verification: Generic MCP Entrypoint And Semantic Capability Profiles

Date: 2026-05-14
Source plan: `136-01-generic-mcp-entrypoint-semantic-capabilities-PLAN.md`
Implementation commit: `b620a44`

## Verification Scope

This verification covers the additive semantic MCP profile metadata layer, the
generic profile router prototype, accelerator/privacy fail-closed tests,
docs/skill vocabulary updates, linting, formatting, and mock/contract test
coverage.

It does not claim ROS/Nav2, Docker Gateway, live VLM, GPU, paid API, or
real-robot validation.

## Acceptance Mapping

| Requirement | Evidence |
|---|---|
| Profile declaration schema exists | `roboclaws/mcp/profiles.py` defines `ContractProfile`, `ToolDescriptor`, capability families, classifications, provenance vocabulary, profile lookup, and validation helpers. |
| AI2-THOR profile excludes accelerators | `tests/contract/mcp/test_semantic_profiles.py::test_ai2thor_profile_labels_scene_objects_and_goto_as_accelerators` verifies `scene_objects` and `goto` are accelerator exclusions, not public profile tools. |
| Molmo profile preserves ADR-0003 privacy boundary | `test_molmo_profile_public_metadata_omits_private_evaluator_terms` and `test_public_profile_safety_rejects_private_terms_in_serialized_metadata` verify public metadata omits configured private evaluator terms. |
| Generic router registers one selected public surface | `test_router_registers_only_selected_profile_public_tools`, `test_register_profile_tools_helper_registers_selected_public_tools`, and `test_router_rejects_handlers_not_in_public_profile`. |
| Existing server behavior is additive | No existing MCP server class or `just task::run ...` recipe was replaced; docs explicitly keep accelerators available for AI2-THOR demo efficiency while excluding them from canonical profile metadata. |

## Commands Run

- `.venv/bin/ruff check roboclaws/mcp/profiles.py roboclaws/mcp/entrypoint.py tests/contract/mcp/test_semantic_profiles.py`
- `.venv/bin/ruff format --check roboclaws/mcp/profiles.py roboclaws/mcp/entrypoint.py tests/contract/mcp/test_semantic_profiles.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/mcp/test_semantic_profiles.py tests/contract/mcp/test_mcp_server.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/molmo_cleanup/test_molmo_cleanup_profiles.py`
- Commit hook for `b620a44`: staged Python `ruff check`, staged Python `ruff format --check`, and the repo fast non-integration pytest subset.

## Results

- Targeted Ruff check: pass.
- Targeted Ruff format check: pass.
- Focused MCP/Molmo contract tests: pass (`71 passed`) with existing Pillow
  deprecation warnings in older image conversion paths.
- Commit hook fast pytest subset: pass, with existing Pillow deprecation
  warnings and expected skips.

## Verdict

Phase 136 is implemented and verified for the additive profile/router
prototype. No external local-dev validation gate remains for this phase.
