---
refactor_scope: sanitized-agent-steering
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-03
---

# Refactor Scope: Sanitized Agent Steering

## Status

DONE

## Target

Reduce magic-tweak entropy in the `world-labels-sanitized` live-agent route
while preserving the public/private cleanup contract.

In scope:

- `roboclaws/agents/prompts/household_cleanup.py`
- `scripts/molmo_cleanup/run_live_codex_cleanup.py`
- `skills/molmo-realworld-cleanup/SKILL.md`
- focused prompt/run-wrapper tests
- human-doc discoverability for the architecture hygiene review

Out of scope:

- changing private scoring semantics
- changing the sanitized public/private contract
- changing `done()` pending/held enforcement
- changing `destination_policy` or `destination_options`
- running slow paid/provider/GPU comparison matrices

## Accepted Severities

- P1: prompt and continuation rules duplicate public tool state and can hide
  correctness behind agent-specific steering.
- P2: sanitized-specific wording is repeated across kickoff prompt, skill docs,
  continuation prompts, and tests.

## Accepted Cleanup Checklist

- [x] Keep contract-level sanitized boundaries intact.
- [x] Remove hard "full anchor discovery sweep before first pick" steering.
- [x] Remove trace-derived continuation next-action injection.
- [x] Simplify final continuation closeout text to rely on public tool
  responses.
- [x] Replace duplicated prompt assertions with contract-first assertions.
- [x] Link the architecture hygiene review from the human docs index.

## Parked Cross-Seam / Future Ideas

- Consider extracting reusable prompt fragments only if duplication remains
  after this direct cleanup.
- Consider broader cleanup of camera-raw prompt strictness in a separate slice.
- Consider live-agent behavior comparison after a cheap sanitized rerun.

## Evidence Ladder

- L1: focused unit tests for prompt/run-wrapper behavior.
- L2: focused contract/dev-tool tests proving sanitized prompt routing and
  contract boundary expectations.

## Stop Condition

The sanitized live-agent route still tells agents to use public `done` recovery,
`required_tool`, `destination_policy`, and `destination_options`, but no longer
uses trace-derived exact next-action injection or a hard pre-pick full-sweep
rule. Focused tests pass, and remaining ideas are parked.

## Execution Log

- 2026-06-03: Gate created from architecture hygiene review and
  `$intuitive-reduce-entropy` recommendation.
- 2026-06-03: Removed sanitized hard pre-pick full-sweep steering and
  trace-derived continuation next-action injection. Focused tests passed:
  `./scripts/dev/run_pytest_standalone.sh -q
  tests/unit/molmo_cleanup/test_ci_live_reports.py::test_live_codex_sanitized_continuation_prompt_uses_contract_first_recovery
  tests/unit/molmo_cleanup/test_ci_live_reports.py::test_live_codex_final_continuation_prompt_prioritizes_required_sweep
  tests/unit/molmo_cleanup/test_ci_live_reports.py::test_live_codex_sanitized_lane_gets_larger_default_turn_budget
  tests/contract/dev_tools/test_task_agent_just_recipes.py::test_molmo_world_labels_sanitized_prompt_omits_destination_oracle_reliance
  tests/contract/skills/test_molmo_realworld_cleanup_skill.py::test_cleanup_skill_prioritizes_done_over_optional_reclean_loops
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_world_labels_sanitized_done_rejects_held_policy_required_object
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_world_labels_sanitized_done_rejects_policy_required_pending_objects`.
  `ruff check` passed for touched Python files. A broader
  `tests/contract/dev_tools/test_task_agent_just_recipes.py` file run still has
  the pre-existing unrelated `console::run` public facade expectation failure.
