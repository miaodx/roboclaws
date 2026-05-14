---
refactor_scope: report-artifact-size
status: DONE
accepted_severities:
  - P1
last_verified: 2026-05-14
---

# Refactor Scope: Report Artifact Size

## Status

DONE

## Target

Report artifact size at two seams:

- public GitHub Pages publishing surface: the assembled `site/` directory
  created by the `publish-pages` CI job before `actions/upload-pages-artifact`
- report generation defaults for optional assets that can be rebuilt from other
  generated evidence

## Accepted Severities

P1 for Pages correctness and artifact bloat. P2 is explicitly accepted for the
bounded generation cleanup requested on 2026-05-14: stop generating optional
rebuildable GIFs by default while keeping an explicit opt-in path.

## Accepted P0/P1 Checklist

- Add a deterministic Pages-site pruning step that preserves all HTML files and
  every local file referenced from HTML `src`/`href` style attributes.
- Do not remove Molmo live `robot_views/*.png`, `before.png`, or `after.png`
  when the Molmo report references them.
- Remove unreferenced raw evidence from public Pages output, especially
  AI2-THOR/OpenClaw sibling frame directories and replay/debug files already
  embedded in or absent from `report.html`.
- Fail the publish job if any generated HTML has a missing local file reference
  after pruning.
- Stop generating rebuildable replay GIFs by default in CI/demo report paths
  where PNG frames remain available, while preserving an explicit flag or API
  path for users who still want a GIF.

## Parked P2 / Future Ideas

- Change AI2-THOR/OpenClaw report generation to externalize images instead of
  embedding large base64 payloads in `report.html`.
- Add compact Molmo timeline modes such as key-frame sampling or thumbnails.
- Publish a separate downloadable full-evidence bundle from Pages for users who
  want raw JSON, JSONL, logs, and every frame.
- Stop generating raw PNG frame directories by default only after report
  generators no longer need them to build self-contained HTML.

## Evidence Ladder

- L1: unit tests for local-link parsing, missing-reference failure,
  unreferenced-file pruning, and replay GIF opt-in behavior.
- L2: CI workflow invokes the pruner before uploading the Pages artifact.
- L3: run the pruner against an assembled Pages site artifact and compare file
  count / byte size before and after.

## Stop Condition

Stop when `publish-pages` prunes only the public `site/` directory, all local
HTML references are verified after pruning, Molmo referenced images remain
published, rebuildable GIF generation is off by default with an explicit opt-in,
and tests for the pruning/generation contracts pass.

## Execution Log

- 2026-05-14: Started implementation after artifact inspection showed public
  Pages contained duplicate AI2-THOR/OpenClaw raw frames plus Molmo raw logs.
- 2026-05-14: Scope reopened at user request to include bounded generation
  cleanup for optional GIF artifacts.
- 2026-05-14: Implemented Pages pruning, missing-reference verification, and
  default-off GIF generation with explicit opt-in paths. Verified with:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_pages_site_prune.py tests/contract/reports/test_replay.py tests/contract/reports/test_render_autonomous_replay.py tests/unit/examples tests/contract/openclaw/test_openclaw_demo.py tests/contract/openclaw/test_openclaw_nav_autonomous.py -q`;
  `uv run ruff check .`; `uv run ruff format --check .`.
- 2026-05-14: Rehearsed against `/tmp/roboclaws-pages-site-25846916840` copy:
  `files=1240->471`, `bytes=385935969->261132345`, `removed=124803624`,
  `missing_refs=0`.
