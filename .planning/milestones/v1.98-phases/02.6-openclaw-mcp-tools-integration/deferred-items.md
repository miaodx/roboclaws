# Phase 02.6 — Deferred Items

Issues discovered during plan execution that are **out of scope** for the
current plan and deferred for later cleanup.

## Discovered 2026-04-21 (plan 02.6-05 — delete sim_server)

### Pre-existing ruff violations (UNRELATED to Phase 02.6)

Running `ruff check .` + `ruff format --check .` at the end of plan 02.6-05
surfaces 5 check errors and 6 format-diffs in files that **pre-date this
phase**. Per the executor scope-boundary rule ("only auto-fix issues
DIRECTLY caused by the current task's changes"), these are logged here
rather than fixed in plan 05.

**`ruff check` offenders (5 errors):**

- `scripts/diagnose_openclaw_latency.py:12` — E501 line 103 chars
- `scripts/diagnose_openclaw_latency.py:15` — E501 line 104 chars
- `scripts/write_pages_index.py:165` — E501 line 104 chars
- `tests/test_visualizer_soul_overlay.py:3-6` — I001 import block order
- `tests/test_visualizer_soul_overlay.py:6` — F401 unused `pytest` import

**`ruff format --check` offenders (6 files):**

- `roboclaws/core/visualizer.py`
- `scripts/diagnose_openclaw_latency.py`
- `tests/test_openclaw_diagnostics.py`
- `tests/test_visualizer_soul_overlay.py`
- (+2 more per output)

**Provenance (git blame sample):**

- `scripts/diagnose_openclaw_latency.py` — commit `51be7bd feat: add probe
  latency telemetry` (pre-Phase 02.6)
- `tests/test_visualizer_soul_overlay.py` — commit `d1e8ea3 feat(phase-2.2):
  long-running OpenClaw games` (Phase 2.2)
- `roboclaws/core/visualizer.py` — edited by Phase 2.2 (`d1e8ea3`)

All offenders were introduced before this phase began. Ruff was not run as
a merge gate historically, which is how this accumulated.

**Suggested resolution:** Open a separate bounded cleanup PR
(`chore: ruff autofix + format across pre-phase 02.6 debt`) that runs
`ruff check --fix .` and `ruff format .` in one go. This is a pure
mechanical-fix PR and should not be bundled into a feature phase.

## Noted (non-issue, retained for posterity)

### `scripts/openclaw-bootstrap.sh` comment narrative

Lines 102-105 in the bootstrap script still say "plan 05 removes it
entirely when the sim_server.py HTTP path is deleted" — that narrative is
now mildly stale (plan 05 HAS run; the HTTP path IS deleted). The plan 05
action block explicitly said "Do NOT touch the plan-02 fallback block near
line 89-102 that emits the deprecation warning," so this comment was left
intact. The fallback code itself (lines 106-116) is the real artifact and
correctly describes itself as a legacy-var graceful-degrade. Safe to refresh
the wording in plan 07 (docs-update) if desired.
