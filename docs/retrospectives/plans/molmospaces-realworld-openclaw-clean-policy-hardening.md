# MolmoSpaces Real-World OpenClaw Clean Policy Hardening

**Status:** Completed 2026-05-09 under GSD Phase 20
**Created:** 2026-05-09
**Source:** `CONTEXT.md`, ADR-0003, ADR-0006, ADR-0008, ADR-0009, ADR-0010, Phase 19 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 19 closed the real MolmoSpaces/RBY1M visual evidence gap for OpenClaw, but
the live Gateway run was only minimum-valid. It swept public waypoints and
produced robot-view artifacts, yet skipped the intended semantic cleanup loop by
calling `pick` and `place` directly. The backend silently repaired those skips
with internal auto-navigation, so the object state changed but the public
semantic report did not match the desired `nav -> pick -> nav -> open? -> place`
shape.

## Decision

Implement ADR-0011 as the clean-policy hardening slice for
`molmo_cleanup_realworld`.

This phase should:

- make public semantic ordering executable in the ADR-0003 contract, not just
  prompt text;
- reject skipped `pick`, `place`, and `place_inside` calls with
  `error_reason=semantic_order` and public recovery guidance;
- keep deterministic smoke agents and clean direct-agent paths working because
  they already call the loop in order;
- expose semantic-order diagnostics in `run_result.json` and make the strict
  clean checker reject clean artifacts that contain those errors;
- update the OpenClaw cleanup skill and server kickoff text so Gateway sees the
  same loop contract the checker enforces.

## Non-Goals

- Do not expose `scene_objects`, private manifests, target counts, or acceptable
  destination sets.
- Do not add a second report renderer or contract-specific semantic timeline.
- Do not make planner-backed RBY1M/Franka manipulation part of this phase.
- Do not require a live Gateway clean success before merging the contract
  hardening; live Gateway should be attempted when practical and recorded
  separately as evidence.

## Deliverables

- ADR-0011 and this source plan.
- `.planning/milestones/v1.98-phases/20-molmospaces-realworld-openclaw-clean-policy/20-01-realworld-openclaw-clean-policy-PLAN.md`.
- Contract-level semantic ordering guards for `pick`, `place`, and
  `place_inside`.
- Tests proving skipped semantic phases are rejected without private-truth
  leakage and correct loops still pass.
- Checker diagnostics that distinguish semantic-order failures from stale
  references and reject them under `--require-clean-agent-run`.
- Updated OpenClaw skill/server guidance.

## Acceptance Criteria

- A direct `pick(observed_*)` before `navigate_to_object(observed_*)` returns
  `ok=false`, `error_reason=semantic_order`, and a public required-tool hint.
- A direct `place(fixture_id)` before
  `navigate_to_receptacle(fixture_id)` returns the same class of public
  semantic-order error.
- Fridge-like `place_inside(fixture_id)` requires `open_receptacle(fixture_id)`
  after navigation.
- Deterministic smoke artifacts still pass
  `--require-agent-driven --require-clean-agent-run` with no semantic-order
  errors.
- `skills/molmo-realworld-cleanup/SKILL.md` and server kickoff text clearly
  say the MCP server rejects skipped semantic phases.
- The shared report/semantic timeline underlay remains unchanged except for
  consuming the stricter trace diagnostics.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_realworld_contract.py tests/test_molmo_realworld_mcp_server.py tests/test_check_molmo_realworld_cleanup_result.py`
- `ruff check` and `ruff format --check` on changed Python files.
- `just verify::molmo-realworld-agent-dogfood-kit`
- Optional local visual/OpenClaw rerun if time allows:
  `just verify::molmo-realworld-openclaw-visual-dogfood-kit` and a live Gateway
  attempt against the hardened server.

## Completion Evidence

- `pick`, `place`, `place_inside`, and fridge `open_receptacle` ordering are now
  enforced in `RealWorldCleanupContract`.
- Focused tests passed:
  `tests/test_molmo_realworld_contract.py`,
  `tests/test_molmo_realworld_mcp_server.py`, and
  `tests/test_check_molmo_realworld_cleanup_result.py`.
- `just verify::molmo-realworld-agent-dogfood-kit` passed with
  `semantic_order_errors=0`.
- `just verify::molmo-realworld-openclaw-dogfood-kit` passed with
  `policy=openclaw_agent`, `cleanup_status=success`, and
  `semantic_order_errors=0`.
- Existing real visual OpenClaw artifact
  `output/molmo-realworld-openclaw-visual-dogfood-kit/run_result.json` passed
  the strict clean visual checker after the hardening.
