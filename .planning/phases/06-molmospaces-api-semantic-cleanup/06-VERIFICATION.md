# Phase 6 Verification — MolmoSpaces API-Semantic Cleanup Pilot

**Date:** 2026-05-07
**Status:** PASS

## Preflight

| Command | Result |
| --- | --- |
| `uv --version && uv pip install -e ".[dev]"` | PASS — `uv 0.9.27`; editable `roboclaws==0.1.0` installed. |
| `.venv/bin/python -c "import ai2thor; ..."` | PASS — `ai2thor 5.0.0 ok`. |
| `set -a && source .env && ... VLM key check` | PASS — at least one VLM key is present after sourcing `.env`; no key value printed. |
| `docker ps -a ... openclaw-gateway` | Existing `openclaw-gateway` was already running and healthy; left untouched. |

The active Gateway container image was
`ghcr.io/openclaw/openclaw:2026.4.25-beta.11`. Phase 6 does not use OpenClaw,
so this was treated as another agent's state and not modified.

## Verification Gates

| Gate | Result |
| --- | --- |
| `just verify::molmo-cleanup` | PASS — 20 focused tests passed, then `just harness::molmo-cleanup` passed. |
| `just harness::molmo-cleanup` | PASS — wrote `output/molmo-cleanup-harness/run_result.json` and `report.html`. |
| `just verify::contract` | PASS — 63 contract/report/regression tests passed. |
| `just verify::static` | PASS — ruff check and format check passed; `git diff --check` passed. |

Commit hooks also ran the fast non-integration pytest subset on each Python
slice commit.

## Harness Artifact

`output/molmo-cleanup-harness/run_result.json` recorded:

- `scenario_id=molmo-cleanup-default-7`
- `cleanup_status=success`
- `primitive_provenance=api_semantic`
- `planner=scripted_reference`
- `restored_count=5`
- `total_targets=5`
- `success_threshold=3`
- report: `output/molmo-cleanup-harness/report.html`
- trace: `output/molmo-cleanup-harness/trace.jsonl`
- snapshots: `before.png`, `after.png`

## Acceptance Coverage

| Acceptance criterion | Status |
| --- | --- |
| Public scenario hides private valid target map | PASS — unit tests assert no `valid_receptacle_ids`, `success_threshold`, or `private_manifest` in public tool payloads. |
| Private scorer gates success at 3-of-5 | PASS — scorer tests cover success, partial success, and failure. |
| Stable/stale ID semantics | PASS — backend tests cover `stale_reference`, `not_holding`, and `already_holding`. |
| Provenance is surfaced in artifacts | PASS — tool responses, `run_result.json`, and `report.html` include `api_semantic`. |
| Harness proves artifact works | PASS — `just harness::molmo-cleanup` validates success and report existence. |
| Existing contract/static gates stay green | PASS — `verify::contract` and `verify::static` passed. |

## Residual Risks

- This phase is intentionally `api_semantic`; it does not prove real robot
  grasping, RBY1M/Franka planning, or MuJoCo contact-rich manipulation.
- The deterministic demo is a scripted reference run and uses the private
  manifest to choose target receptacles. That is acceptable for the harness but
  must not be described as autonomous policy performance.
- The repo still does not import MolmoSpaces at top level. A future local-dev
  adapter must use an optional Python 3.11 subprocess or raise the repo Python
  floor deliberately.
- OpenClaw integration remains deferred. The existing Gateway container was not
  exercised by this phase.
