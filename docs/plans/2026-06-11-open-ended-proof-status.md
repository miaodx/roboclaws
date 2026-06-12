---
plan_scope: open-ended-proof-status
status: IMPLEMENTED
created: 2026-06-11
last_reviewed: 2026-06-11
source:
  - latest operator-console Proof false-negative investigation
  - intuitive-reduce-entropy
  - grill-with-docs-batch
related_context:
  - CONTEXT.md#household-world-and-cleanup-vocabulary
---

# Open-Ended Proof Status Contract

## Current Implementation Contract

Fix the operator-console Proof false negative for
`surface=household-world intent=open-ended` by making the terminal
intent-level outcome explicit and keeping cleanup restoration score advisory.

The latest failing UI run produced a passing checker log and `exit_status=0`,
but `run_result.json` also contained cleanup-shaped top-level fields:

```text
task_intent=open-ended
cleanup_status=failed
completion_status=failed
final_status=failed
score.status=success
score.total_targets=0
score.sweep_coverage_rate=1.0
```

`roboclaws/operator_console/state.py` currently treats those top-level
`failed` strings as authoritative Proof failure, so the UI says
`Checker failed. Open Checker Output for details.` even when the open-ended
artifact checker passed.

## Accepted Decisions

1. Open-ended terminal status is intent-level, not cleanup-score-level.
2. For `intent=open-ended`, the Proof panel means the open-ended intent checker
   and hard artifact gates passed.
3. Cleanup restoration fields may remain in the artifact as advisory evidence,
   but they must not drive operator-console Proof failure for open-ended runs.
4. The operator-console state reducer may be intent-aware using `task_intent`,
   `goal_contract.intent`, or route `checker_id`.
5. No new ADR is needed; this implements the existing surface/intent and
   advisory-scoring contracts.

## Scope

- Normalize open-ended `run_result.json` terminal outcome so future artifacts
  expose an explicit `Open-Ended Intent Outcome`.
- Update operator-console proof derivation so open-ended advisory cleanup
  scores do not mask a passing open-ended checker.
- Preserve cleanup intent behavior: cleanup runs should still fail Proof when
  cleanup status or clean-agent gates fail.
- Add regression coverage for the exact false-negative shape.

## Non-Goals

- No broad cleanup scoring redesign.
- No change to private scorer truth, generated mess sets, or cleanup
  acceptance thresholds.
- No change to cleanup report rendering except where status labels need to
  distinguish advisory cleanup score from terminal open-ended outcome.
- No live Isaac, Codex, or provider run required for this implementation slice.

## Affected Paths

- `roboclaws/household/realworld_contract.py`
- `roboclaws/household/realworld_mcp_server.py`
- `roboclaws/operator_console/state.py`
- `tests/unit/operator_console/test_state.py`
- `tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`
- `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`

## Data Flow

```text
operator prompt
  -> launch catalog: intent=open-ended / checker=open_ended_report
  -> live agent calls done(reason)
  -> MCP server writes run_result.json
       - intent_status / goal_status: success
       - cleanup score: advisory, not terminal
  -> checker validates open-ended artifacts
  -> checker.log records pass/fail
  -> operator_console/state.py derives checker_status by intent
  -> Proof panel displays passed or failed
```

## Verification

Focused regression:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_state.py
```

Contract/checker coverage:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Lint for touched modules:

```bash
.venv/bin/ruff check \
  roboclaws/household/realworld_contract.py \
  roboclaws/household/realworld_mcp_server.py \
  roboclaws/operator_console/state.py \
  tests/unit/operator_console/test_state.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

## Regression Test Requirements

- Open-ended `run_result.json` with legacy cleanup-shaped
  `cleanup_status=failed`, `completion_status=failed`, and `final_status=failed`
  plus passing `checker.log` must not render Proof as failed when open-ended
  hard gates are satisfied.
- Cleanup intent with the same top-level failure fields must still render Proof
  as failed.
- Producer-side open-ended completion with zero cleanup targets must serialize
  an explicit terminal intent outcome that is not cleanup failure.
- Checker tests must continue to accept open-ended scan-only runs with no
  visible movable objects.

## Stop Condition

The slice is complete when the focused tests and lint above pass, the latest
false-negative artifact shape is covered by a unit regression, and no cleanup
intent regression was introduced.

## Implementation Closeout

Implemented on 2026-06-11.

- Live MCP open-ended artifacts now emit explicit `intent_status`,
  `goal_status`, and terminal `final_status=success` while marking cleanup
  restoration fields as advisory.
- Operator-console Proof derivation is intent-aware: open-ended cleanup-score
  failures no longer override a passing open-ended artifact result, while
  cleanup-intent failures remain authoritative.
- Regression coverage includes the exact legacy false-negative shape and the
  matching cleanup-intent failure shape.

Verification passed:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_state.py
./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_custom_task_mode_is_recorded_in_run_result
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
.venv/bin/ruff check \
  roboclaws/household/realworld_contract.py \
  roboclaws/household/realworld_mcp_server.py \
  roboclaws/operator_console/state.py \
  tests/unit/operator_console/test_state.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Remaining gates: none for this slice.
