# Phase 135 Verification: MolmoSpaces CI Live-Agent Reports

Date: 2026-05-13
Source plan: `135-01-ci-live-agent-reports-PLAN.md`

## Verification Scope

This verification covers implementation, command-shape rehearsal, status
manifest generation, Pages assembly, focused unit coverage, formatting, linting,
and GitHub Actions YAML parsing.

It does not claim that GitHub-hosted live provider execution has already passed.
That proof requires configured GitHub Actions secrets and a hosted
`workflow_dispatch` or `[molmo-live]` run.

## Acceptance Mapping

| Requirement | Evidence |
|---|---|
| Local CI rehearsal exists for model entries | `just molmo::ci-rehearsal kimi-k2.6 --dry-run`; `just --list molmo` shows `ci-rehearsal` and `ci-rehearsal-all`. |
| Rehearsal records provider/cache/status shape | Dry-run status at `output/molmo/ci-rehearsal/site/molmo/live/kimi-k2.6/status.json` records `ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic`, `ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6`, cache roots, command, and dry-run reason. |
| Three model entries are supported | `tests/unit/molmo_cleanup/test_ci_live_reports.py::test_ci_live_model_entries_match_provider_profiles`; entries use real model IDs `kimi-k2.6`, `mimo-v2.5-pro`, and `mimo-v2-omni`. |
| Claude Code live execution is non-interactive | `scripts/molmo_cleanup/run_live_claude_cleanup.py --help`; implementation uses `claude -p --output-format stream-json` with full permission flags. |
| MolmoSpaces assets are prewarmed/cached | `scripts/molmo_cleanup/prewarm_molmospaces_ci_assets.py --help`; workflow caches `~/.cache/uv`, `~/.cache/molmospaces`, and `~/.cache/molmo-spaces-resources`, and the matrix script prewarms seed 7 / `rby1m` / generated mess count 5 before live calls when secrets exist. |
| CI installs Codex and Claude Code | `.github/workflows/ci.yml` has Node 22 setup, npm install for `@openai/codex` and `@anthropic-ai/claude-code`, and `codex --version` / `claude --version`. |
| Hosted CI is opt-in and long enough | `.github/workflows/ci.yml` runs `molmo-live-cleanup` only for `workflow_dispatch` with `molmo_live=true` or `[molmo-live]` pushes to `main`; matrix is `max-parallel: 1`; timeout is 75 minutes per entry. |
| Pages exposes report/status tiles | `scripts/molmo_cleanup/assemble_ci_live_pages.py` plus `scripts/reports/write_pages_index.py --include-molmo-live`; focused test `test_publish_seed_run_and_pages_index_render_molmo_live_tiles`. |
| Baseline Pages does not depend on live Molmo success | Workflow marks `molmo-live-cleanup` `continue-on-error`, downloads its artifacts best-effort, and only includes Molmo live tiles when artifacts exist. |

## Commands Run

- `just molmo::ci-rehearsal kimi-k2.6 --dry-run`
- `.venv/bin/python scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py --all --dry-run --skip-uv-sync --skip-prewarm --skip-version-check --output-dir output/molmo/ci-rehearsal-all --published-dir output/molmo/ci-rehearsal-all/site/molmo/live`
- `.venv/bin/python scripts/molmo_cleanup/assemble_ci_live_pages.py output/molmo/ci-rehearsal-all/site/molmo/live output/molmo/ci-rehearsal-all/site-copy/molmo/live`
- `.venv/bin/python scripts/reports/write_pages_index.py output/molmo/ci-rehearsal-all/site-copy --include-molmo-live`
- `just --list molmo`
- `.venv/bin/python scripts/molmo_cleanup/run_live_claude_cleanup.py --help`
- `.venv/bin/python scripts/molmo_cleanup/prewarm_molmospaces_ci_assets.py --help`
- `.venv/bin/python scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py --help`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/ci_live_reports.py scripts/molmo_cleanup/prewarm_molmospaces_ci_assets.py scripts/molmo_cleanup/run_live_claude_cleanup.py scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py scripts/molmo_cleanup/assemble_ci_live_pages.py scripts/reports/write_pages_index.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/ci_live_reports.py scripts/molmo_cleanup/prewarm_molmospaces_ci_assets.py scripts/molmo_cleanup/run_live_claude_cleanup.py scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py scripts/molmo_cleanup/assemble_ci_live_pages.py scripts/reports/write_pages_index.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text()); print('workflow yaml ok')"`

## Verdict

Phase 135 is implemented and verified for the repo-side pipeline and local
non-live rehearsal. The remaining external validation is to run the opt-in
hosted workflow with `KIMI_API_KEY` and `MIMO_TP_KEY` configured in GitHub
Actions secrets.
