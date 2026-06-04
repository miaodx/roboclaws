---
refactor_scope: raw-fpv-visual-candidate-actionability
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-04
---

# Refactor Scope: RAW_FPV Visual Candidate Actionability

## Status

DONE

## Target

Make the `camera-raw` / RAW_FPV cleanup lane actionable for coding agents by
removing drift between the live Codex prompt, the agent prompt, and the
household MCP contract for `navigate_to_visual_candidate`.

## Accepted Severities

- P1: Prompt/contract source-of-truth drift that tells the agent to provide
  `target_fixture_id` from empty minimal-map `fixture_hints`.
- P1: Contract recovery responses that let the agent loop on invalid
  `image_region` or `target_fixture_id` shapes without an exact repair schema.
- P2: Duplicated RAW_FPV tool-use prose that can drift between kickoff,
  continuation, observation instructions, and validation errors.

## Accepted Cleanup Checklist

- [x] Centralize the canonical RAW_FPV `navigate_to_visual_candidate`
  instruction so kickoff, continuation, and observation/tool recovery text agree.
- [x] In minimal map mode, instruct agents to omit `target_fixture_id`; never
  require a value copied from empty `fixture_hints`.
- [x] Return a concrete recovery payload for malformed RAW_FPV visual candidates:
  accepted `image_region` forms, minimal-map target-fixture rule, a valid
  example, and the immediate next action.
- [x] Add tests that guard prompt/contract alignment and schema-level recovery.
- [x] Run focused L1/L2 tests for the RAW_FPV prompt/contract seam.

## Parked Cross-Seam / Future Ideas

- Codex/mify 429 backoff and full 8-row scheduling belong in a separate
  `codex-harness-rate-limit-backoff` scope.
- Live provider validation remains local/paid/provider-sensitive. Rerun only
  `direct-camera-raw` and `dino-prior-camera-raw` after deterministic tests pass.
- Do not replace RAW_FPV with camera-labels evidence; RAW_FPV remains the
  agent-input proof lane.

## Evidence Ladder

- L0 static:
  - Inspect target diffs and ensure unrelated dirty files remain untouched.
  - Python tooling/LSP status: `pyproject.toml` and `uv.lock` exist; no
    repo-local Pyright/Mypy/LSP config was found, so symbol-level confidence
    comes from static search plus focused tests.
- L1 unit/mock:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
- L2 contract:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
- L6 live harness:
  - Optional/local after deterministic gates:
    `ROBOCLAWS_CODEX_PROVIDER=mify ROBOCLAWS_CODEX_MODEL=xiaomi/mimo-v2.5 just agent::harness codex-cleanup-harness8 execute row=direct-camera-raw row=dino-prior-camera-raw ...`

## Stop Condition

Stop when the accepted checklist is complete, focused L1/L2 tests pass, prompt
and contract text no longer contradict minimal-map RAW_FPV rules, and any live
RAW_FPV harness rerun is either green or explicitly left as local/provider
evidence rather than claimed.

## Execution Log

- 2026-06-04: Created scope after the mify/MiMo 8-case harness showed completed
  RAW_FPV rows scanning all waypoints but never reaching a successful pick/place.
  The direct contradiction is that the live continuation prompt required a
  `target_fixture_id` from `fixture_hints`, while minimal-map RAW_FPV contract
  guidance says to omit it until grounding returns a public candidate fixture.
- 2026-06-04: Implemented the deterministic RAW_FPV actionability slice.
  - Added `roboclaws.household.raw_fpv_guidance` as the canonical source for
    RAW_FPV visual-candidate instruction text, accepted `image_region` forms,
    invalid fields to avoid, and structured recovery payloads.
  - Updated kickoff prompts, live Codex continuation prompts, observation
    instructions, and invalid-candidate contract responses to use the canonical
    guidance.
  - Hardened minimal-map RAW_FPV manual candidate validation so invented
    `target_fixture_id` values are rejected with repair guidance; successful
    candidates still omit `target_fixture_id` and use returned
    `candidate_fixture_id` / `recommended_tool`.
  - Added prompt and contract tests for minimal-map omission, schema-level
    recovery, and stale continuation-prompt drift.
- 2026-06-04 evidence:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
    passed with 32 tests.
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
    passed with 48 tests.
  - `ruff check roboclaws/household/raw_fpv_guidance.py roboclaws/household/realworld_contract.py roboclaws/agents/prompts/household_cleanup.py scripts/molmo_cleanup/run_live_codex_cleanup.py tests/unit/molmo_cleanup/test_ci_live_reports.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
    passed.
  - `python -m py_compile roboclaws/household/raw_fpv_guidance.py roboclaws/household/realworld_contract.py roboclaws/agents/prompts/household_cleanup.py scripts/molmo_cleanup/run_live_codex_cleanup.py`
    passed.
  - Static search for `copied from fixture_hints` now finds only the negative
    regression assertion in `tests/unit/molmo_cleanup/test_ci_live_reports.py`.
- 2026-06-04 skipped gate:
  - L6 live mify/MiMo RAW_FPV harness rerun was not executed in this deterministic
    code slice. Use it as follow-up provider evidence after committing:
    `ROBOCLAWS_CODEX_PROVIDER=mify ROBOCLAWS_CODEX_MODEL=xiaomi/mimo-v2.5 just agent::harness codex-cleanup-harness8 execute row=direct-camera-raw row=dino-prior-camera-raw ...`
