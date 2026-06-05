---
refactor_scope: fpv-visual-evidence-gate
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-05
---

# Refactor Scope: FPV Visual Evidence Gate

## Status

DONE

## Target

Make cleanup candidates actionable only when they carry reviewable
agent-facing FPV evidence, regardless of whether the candidate came from
world-labels, RAW-FPV model declarations, camera-labels, fake HTTP, or a real
visual-grounding producer such as Grounding DINO.

## Accepted Severities

- P1: Cleanup can continue from a structured or model-declared candidate even
  when the agent-facing FPV evidence is not reviewable.
- P1: RAW-FPV and world-labels expose different implicit actionability rules,
  which makes reports appear causally disconnected from the action chain.
- P2: Report timeline does not make the candidate producer, source
  observation, FPV bbox/region, reviewability, and actionability explicit
  enough for human review.

## Accepted Cleanup Checklist

- [x] Add one normalized visual-evidence/actionability payload for cleanup
  candidates.
- [x] Gate `navigate_to_object` / `pick` so non-reviewable candidates return a
  public recovery response instead of entering the cleanup chain.
- [x] Apply the same gate to world-label detections, RAW-FPV declarations, and
  camera-labels / external visual-grounding candidates.
- [x] Preserve Grounding DINO/fake HTTP as bbox-evidence producers, not truth
  oracles.
- [x] Show the source observation, producer, FPV bbox/region, reviewability,
  and actionability in reports.
- [x] Keep held-object `done` blockers and existing sanitized/RAW-FPV readiness
  contracts green.

## Parked Cross-Seam / Future Ideas

- Real Grounding DINO threshold tuning and GPU benchmark runs remain local
  provider/GPU gates.
- Broader report visual redesign is out of scope unless needed for the
  actionability evidence.
- Planner-backed manipulation proof is a separate primitive gate.

## Evidence Ladder

- L1/L2:
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_contract.py -q`
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`
- L2 report/checker:
  - targeted report/checker tests if report contracts change.
- Optional local smoke:
  - `just task::run household-cleanup mcp-smoke camera-labels visual_grounding=fake-http seed=7 generated_mess_count=5`

## Stop Condition

Stop when a candidate can enter `pick` only with `actionability_status=actionable`
and reviewable agent-facing FPV evidence, the report displays that evidence,
and focused contract tests pass. Real Grounding DINO execution may be skipped
with a documented local/GPU reason.

## Execution Log

- 2026-06-05: Created after manual review of Codex world-labels and RAW-FPV
  reports showed action chains that were not reviewable from the preceding FPV
  timeline frame. The accepted seam is a unified FPV visual-evidence gate across
  candidate producers.
- 2026-06-05: Implemented `visual_grounding_evidence_v1`, gated
  `navigate_to_visual_candidate`, `navigate_to_object`, and `pick` on
  reviewable agent-facing FPV bbox evidence, updated RAW-FPV guidance to
  bbox-first, and surfaced reviewability/actionability in Agent View/runtime map
  and report tables. Verified with:
  `ruff check roboclaws/household/realworld_contract.py roboclaws/household/realworld_mcp_server.py roboclaws/household/report.py roboclaws/household/raw_fpv_guidance.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_contract.py -q`;
  `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py -q`.
