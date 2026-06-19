# Python Quality Backend Entropy Ratchet

Owner/session: Codex main session
Started: 2026-06-20
State: active

## Scope

Continue the accepted Python quality/backend entropy campaign one vertical
slice at a time. Source truth remains the active plan; completed slices belong
only in the completed ledger.

## Source Of Truth

- Plan: `docs/plans/refactor-python-quality-backend-entropy.md`
- Completed ledger: `docs/plans/refactor-python-quality-backend-entropy-completed.md`

## Latest Checkpoint

2026-06-20: B1 Gaussian scene topdown capture now rejects malformed or
parseable non-object hidden `--camera-request` packets before Isaac capture or
`capture_result.json` writes. Focused topdown contract tests, touched-file
Ruff/format, `git diff --check`, changed-code review, and ratchet passed.
Quality signal: 0 Ruff complexity rows, 79 oversized modules.

## Next Action

Pick a fresh fail-aloud/source-truth seam from current ratchet evidence. Good
remaining candidates include `scripts/maps/suggest_b1_map12_manual_anchor_semantics.py`
source loads or `scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py`
explicit `--points` loading.

## Touched Areas

- `scripts/maps/render_b1_scene_gaussian_topdown.py`
- `tests/contract/maps/test_b1_scene_gaussian_topdown.py`
- `docs/plans/refactor-python-quality-backend-entropy.md`
- `docs/plans/refactor-python-quality-backend-entropy-completed.md`

## No-Touch Scope

- Do not touch unrelated `docs/status/active/2026-06-18-sdk-storage-targets.md`.
- Avoid adding to `tests/contract/maps/test_b1_map12_verified_alignment.py`
  unless also compacting local debt; it is at the 2000-line hard ceiling.
