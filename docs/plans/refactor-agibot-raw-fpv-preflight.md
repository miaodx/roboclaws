---
refactor_scope: agibot-raw-fpv-preflight
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-05
---

# Refactor Scope: Agibot RAW_FPV Preflight

## Status

DONE

## Target

Make Agibot `head_color` RAW_FPV status a canonical non-moving preflight instead
of an ad hoc probe that future operators or agents have to rediscover.

## Accepted Severities

- P1: a live camera can be falsely reported unavailable when the CPython 3.10
  GDK environment lacks numpy; this should fail loudly as an environment error.
- P2: SDK runner camera initialization did not match the vendor documented order
  of `Camera()` followed by an initialization wait.
- P2: the Chinese Agibot runbook did not clearly separate RAW_FPV preflight from
  the later `camera-labels` hardware acceptance lane.

## Accepted Cleanup Checklist

- [x] Add a tracked read-only RAW_FPV status command under the Agibot SDK tool
  boundary.
- [x] Declare numpy for the Agibot SDK Python 3.10 tool environment.
- [x] Align the SDK runner observe path with the vendor camera init order.
- [x] Update the Chinese Agibot runbook with the canonical command and known
  Python/numpy failure mode.
- [x] Add focused contract tests for the checker and runner order/loud-failure
  behavior.
- [x] Run focused verification and mark this gate `DONE`.

## Parked Cross-Seam / Future Ideas

- The repo-root `scripts/agibot/capture_map_context_views.py` still targets the
  repo `.venv` in the runbook, while live `agibot_gdk` requires Python 3.10.
  Consider routing that script through the vendor SDK boundary later.
- Route `10.42.0.0/24 via 10.42.1.101` may still matter for other GDK services,
  but it is not the current RAW_FPV blocker after frames were read successfully.

## Evidence Ladder

- L1/L2 focused contract tests for status payload shape, no movement fields,
  runner camera init order, and numpy failure messaging.
- L5 optional local hardware proof: `uv run python tools/check_raw_fpv_status.py
  --cameras default-open` saves a valid `head_color_latest.jpg`.

## Stop Condition

Stop when the accepted checklist is complete, focused tests pass, and remaining
ideas are parked outside this preflight slice.

## Execution Log

- 2026-06-05: Added canonical RAW_FPV checker, numpy dependency, vendor-order
  runner observe init, and runbook guidance.
- 2026-06-05: Verified focused Agibot contract tests and local hardware
  preflight. `head_color` reported `640x400`, about `29.96 FPS`, and saved a
  valid JPEG with no motion or navigation submission.
