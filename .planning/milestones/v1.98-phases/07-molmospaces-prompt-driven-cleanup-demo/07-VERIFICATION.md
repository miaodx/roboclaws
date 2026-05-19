# Phase 7 Verification - MolmoSpaces Prompt-Driven Cleanup Demo

**Date:** 2026-05-07
**Status:** PASS

## Verification Gates

| Gate | Result |
| --- | --- |
| `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_policy.py` | PASS — 4 public-policy tests passed. |
| `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_policy.py tests/test_molmo_cleanup_demo.py tests/test_verify_just_recipes.py` | PASS — 11 focused tests passed. |
| `just harness::molmo-prompt-cleanup` | PASS — wrote `output/molmo-prompt-cleanup-harness/run_result.json` and `report.html`. |
| `just verify::molmo-prompt-cleanup` | PASS — 11 focused tests passed, then the prompt harness passed. |
| `just verify::molmo-cleanup` | PASS — 21 focused tests passed, then the original Phase 6 harness passed. |
| `just verify::static` | PASS — ruff check, format check, and whitespace check passed. |

Pre-commit hooks also ran the fast non-integration pytest subset on the Python
implementation commits.

## Prompt Harness Artifact

`output/molmo-prompt-cleanup-harness/run_result.json` recorded:

- `task_prompt=帮我整理这个房间`
- `scenario_id=molmo-cleanup-default-7`
- `planner=public_heuristic`
- `planner_uses_private_manifest=false`
- `cleanup_status=success`
- `primitive_provenance=api_semantic`
- `restored_count=5`
- `total_targets=5`
- `success_threshold=3`
- report: `output/molmo-prompt-cleanup-harness/report.html`
- trace: `output/molmo-prompt-cleanup-harness/trace.jsonl`

## Acceptance Coverage

| Acceptance criterion | Status |
| --- | --- |
| Prompt is `帮我整理这个房间` | PASS — asserted by the harness checker. |
| Planner uses public state, not private manifest | PASS — `planner_uses_private_manifest=false`; policy tests consume public payloads only. |
| Cleanup succeeds above 3-of-5 threshold | PASS — 5/5 restored. |
| Trace contains public-policy tool loop | PASS — `observe`, `scene_objects`, `goto`, `pick`, `place`, and `done` events are emitted. |
| Phase 6 compatibility remains intact | PASS — `just verify::molmo-cleanup` still passes. |

## Residual Risks

- This is prompt-driven through a deterministic public heuristic, not a real VLM
  or OpenClaw agent.
- Primitive provenance remains `api_semantic`; this still does not prove
  planner-backed RBY1M/Franka manipulation.
- The current scenario is intentionally easy and semantic. Broader room
  generalization and real MolmoSpaces subprocess integration remain future work.
