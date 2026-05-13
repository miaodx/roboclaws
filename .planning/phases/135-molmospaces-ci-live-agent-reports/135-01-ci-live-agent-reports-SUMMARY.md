# Phase 135 Summary: MolmoSpaces CI Live-Agent Reports

Completed: 2026-05-13
Source plan: `135-01-ci-live-agent-reports-PLAN.md`
Source PRD: `docs/plans/molmospaces-ci-live-agent-reports.md`

## What Changed

- Added `roboclaws/molmo_cleanup/ci_live_reports.py` for the three fixed live
  CI model entries and their status/manifest contract.
- Added `scripts/molmo_cleanup/run_live_claude_cleanup.py`, a non-interactive
  Claude Code runner that owns MCP server lifecycle, `claude -p` execution,
  transcript/status files, result checking, and cleanup.
- Added `scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py` for local and CI
  execution of one entry or all entries, including dry-run status manifests,
  secret-based skipping, preflight failure statuses, and published report copy.
- Added `scripts/molmo_cleanup/prewarm_molmospaces_ci_assets.py` to initialize
  the seed-7 RBY1M MolmoSpaces scenario before live provider calls.
- Added `scripts/molmo_cleanup/assemble_ci_live_pages.py` and extended
  `scripts/reports/write_pages_index.py` so Pages renders success/skipped/failed
  Molmo live tiles from `site/molmo/live/live-report-manifest.json`.
- Added `just molmo::ci-rehearsal <entry>` and `just molmo::ci-rehearsal-all`
  for local mimicry of the hosted job.
- Extended `.github/workflows/ci.yml` with an opt-in Molmo live matrix on
  GitHub-hosted `ubuntu-latest`, serialized model entries, uv and MolmoSpaces
  caches, Node 22, Codex + Claude Code install/version checks, and best-effort
  artifact download into Pages.

## Status

Implementation complete and non-live verified. Real hosted/live proof is not
claimed yet; it depends on GitHub Actions secrets `KIMI_API_KEY` and
`MIMO_TP_KEY` plus a `workflow_dispatch` run or a `[molmo-live]` push to `main`.

## Evidence

- `just molmo::ci-rehearsal kimi-k2.6 --dry-run`
- `.venv/bin/python scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py --all --dry-run --skip-uv-sync --skip-prewarm --skip-version-check --output-dir output/molmo/ci-rehearsal-all --published-dir output/molmo/ci-rehearsal-all/site/molmo/live`
- `.venv/bin/python scripts/molmo_cleanup/assemble_ci_live_pages.py output/molmo/ci-rehearsal-all/site/molmo/live output/molmo/ci-rehearsal-all/site-copy/molmo/live`
- `.venv/bin/python scripts/reports/write_pages_index.py output/molmo/ci-rehearsal-all/site-copy --include-molmo-live`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/ci_live_reports.py scripts/molmo_cleanup/prewarm_molmospaces_ci_assets.py scripts/molmo_cleanup/run_live_claude_cleanup.py scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py scripts/molmo_cleanup/assemble_ci_live_pages.py scripts/reports/write_pages_index.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/ci_live_reports.py scripts/molmo_cleanup/prewarm_molmospaces_ci_assets.py scripts/molmo_cleanup/run_live_claude_cleanup.py scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py scripts/molmo_cleanup/assemble_ci_live_pages.py scripts/reports/write_pages_index.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text()); print('workflow yaml ok')"`
