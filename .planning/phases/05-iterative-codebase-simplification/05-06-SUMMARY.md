---
phase: 05-iterative-codebase-simplification
plan: 06
subsystem: vlm
tags: [vlm, kimi, openai, providers, nvidia]
requires:
  - phase: 4
    provides: Provider-facing regression coverage
provides:
  - Leaner provider dispatch and shared provider setup paths across the VLM layer
affects: [direct-vlm, openclaw, examples]
tech-stack:
  added: []
  patterns:
    - "Unify repeated provider setup inside provider files without re-merging the split modules"
key-files:
  created: []
  modified:
    - "roboclaws/core/vlm.py"
    - "roboclaws/core/providers/kimi.py"
    - "roboclaws/core/providers/openai.py"
key-decisions:
  - "Kept each provider in its own file and shared only the obvious setup/usage paths."
  - "Preserved `_build_messages()` compatibility because tests and callers rely on it."
patterns-established:
  - "Provider simplify passes should reduce routing/setup duplication without changing model-selection behavior."
requirements-completed: []
duration: batch-session
completed: 2026-04-23
---

# Phase 5 / Plan 06 Summary

**The VLM layer now routes provider selection and shared provider setup through smaller helpers, reducing duplication across `vlm.py`, `kimi.py`, and `openai.py` without changing public provider APIs.**

## Accomplishments

- Simplified [roboclaws/core/vlm.py](/home/mi/ws/gogo/roboclaws/roboclaws/core/vlm.py) by replacing the long provider-selection chain with `_PROVIDER_CLASSES` and extracting `_parse_soul_labels`; final line count: 380.
- Simplified [roboclaws/core/providers/openai.py](/home/mi/ws/gogo/roboclaws/roboclaws/core/providers/openai.py) with a shared `_OpenAIBase`; final line count: 222.
- Simplified [roboclaws/core/providers/kimi.py](/home/mi/ws/gogo/roboclaws/roboclaws/core/providers/kimi.py) with shared timeout/status/content helpers and trimmed verbose comment blocks; final line count: 421.

## Validation

- `env -i PATH=".venv/bin:/usr/bin:/bin" HOME="$HOME" .venv/bin/pytest tests/test_vlm.py tests/test_provider_retry.py tests/test_nvidia_provider.py -x -q`
- `.venv/bin/ruff check roboclaws/core/vlm.py roboclaws/core/providers/openai.py roboclaws/core/providers/kimi.py`
- `.venv/bin/ruff format --check roboclaws/core/vlm.py roboclaws/core/providers/openai.py roboclaws/core/providers/kimi.py`
- Final repo gate: `env -i ... .venv/bin/pytest -x -q`, `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`

## Notes

- Provider caller-import checks remained stable across the repo after the cleanup.
- The plan originally called for separate commits for `vlm.py` and the provider files; this execution kept the group in a single reviewed worktree batch instead.

---
*Phase: 05-iterative-codebase-simplification*
*Plan: 06*
*Completed: 2026-04-23*
