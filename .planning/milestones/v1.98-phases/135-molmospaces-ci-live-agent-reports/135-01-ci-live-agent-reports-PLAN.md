# Phase 135 Plan: MolmoSpaces CI Live-Agent Reports

## Source

- PRD: `docs/retrospectives/plans/molmospaces-ci-live-agent-reports.md`
- Local evidence:
  - `output/molmo/compare-claude/kimi-k2.6/0513_1447/seed-7/report.html`
  - `output/molmo/compare-claude/mimo-v2.5-pro-simple/0513_1526/seed-7/report.html`
  - `output/molmo/compare-claude/mimo-v2-omni-simple/0513_1557/seed-7/report.html`

## Goal

Add an opt-in GitHub-hosted CI path that can run the three proven
MolmoSpaces cleanup live-agent variants through Claude Code provider profiles,
cache/prewarm the MolmoSpaces/MuJoCo assets, and publish status plus report
links on the existing GitHub Pages report site.

## Scope

- Add a local CI rehearsal command before relying on hosted CI.
- Add CI-safe non-interactive Claude Code live cleanup execution.
- Prewarm/cache `~/.cache/uv`, `~/.cache/molmospaces`, and
  `~/.cache/molmo-spaces-resources`.
- Run the seed-7, generated-mess-count-5 `world-labels` task for:
  `kimi-k2.6`, `mimo-v2.5-pro`, and `mimo-v2-omni`.
- Treat the historical `*-simple` local artifact suffix as a Claude Code
  simple-mode run label, not a model ID. Provider helpers still export
  `CLAUDE_CODE_SIMPLE=1` for Anthropic-compatible repo-local providers.
- Publish successful reports and skipped/failed statuses through the existing
  Pages landing page.

## Non-Goals

- Do not make live Molmo CI mandatory on every push.
- Do not commit generated `output/` artifacts.
- Do not add planner-backed RBY1M/CuRobo primitive proof to this CI path.
- Do not broaden beyond the three cited model entries in this first slice.

## Tasks

1. Add a non-interactive Claude Code live-runner that mirrors the Codex runner:
   MCP server lifecycle, status file, provider env, agent transcript, checker,
   and cleanup on failure.
2. Add a local CI rehearsal wrapper and `just molmo::ci-rehearsal <entry>` for
   the three model entries.
3. Add a MolmoSpaces asset prewarm command for the seed-7 RBY1M world-labels
   scenario.
4. Add a small live-report manifest/publishing helper so Pages can show success,
   skipped, and failed model tiles.
5. Extend `.github/workflows/ci.yml` with an opt-in `[molmo-live]` /
   `workflow_dispatch` matrix on `ubuntu-latest`, Node 22 coding-agent CLI
   install/version checks, uv install, MolmoSpaces caches, serialized model
   runs, and best-effort artifact upload.
6. Add focused tests for model-entry resolution, status manifest/page assembly,
   and non-interactive command construction.
7. Run focused non-live verification locally. Treat real live CI execution as
   pending until provider keys and GitHub Actions secrets are available.

## Acceptance Checks

- `just molmo::ci-rehearsal kimi-k2.6 --dry-run` or the equivalent script path
  writes the same command/provider/cache/status shape without spending live
  model budget.
- The live runner launches Claude Code with `-p/--print` and full permission
  defaults, not the interactive TUI.
- A model manifest records `success`, `skipped`, or `failed` with report path
  or failure reason.
- `scripts/reports/write_pages_index.py` exposes Molmo live tiles when a
  manifest is present under `site/molmo/live/`.
- `.github/workflows/ci.yml` can run the matrix only for `workflow_dispatch`
  or `[molmo-live]` pushes to `main`, and baseline Pages publishing remains
  available if live Molmo artifacts are absent or failed.
- Focused lint/format/tests pass for changed files that do not require real
  VLM keys or hosted CI.

## Verification Plan

- `just molmo::ci-rehearsal kimi-k2.6 --dry-run`
- `.venv/bin/python scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py --entry kimi-k2.6 --dry-run --output-dir <tmp>`
- `.venv/bin/python -m pytest tests/...` focused on new runner/rehearsal/pages
  behavior
- `ruff check` and `ruff format --check` on changed Python files

## Result

Complete on 2026-05-13 for the implementation and non-live verification slice.

The repo now has:

- a non-interactive Claude Code live cleanup runner;
- local `just molmo::ci-rehearsal` and `just molmo::ci-rehearsal-all`
  commands;
- MolmoSpaces CI asset prewarm and live matrix scripts;
- Pages assembly and status/report tiles for Molmo live entries;
- an opt-in GitHub Actions matrix for `workflow_dispatch` or `[molmo-live]`
  pushes to `main`, using GitHub-hosted `ubuntu-latest`, uv/MolmoSpaces caches,
  Node 22, Codex + Claude Code version checks, and serialized model entries.

Verification completed without spending live provider budget. Real hosted proof
still requires GitHub Actions secrets `KIMI_API_KEY` and `MIMO_TP_KEY`, plus a
manual `workflow_dispatch` or `[molmo-live]` push.

Verification:

- `just molmo::ci-rehearsal kimi-k2.6 --dry-run`
- `.venv/bin/python scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py --all --dry-run --skip-uv-sync --skip-prewarm --skip-version-check --output-dir output/molmo/ci-rehearsal-all --published-dir output/molmo/ci-rehearsal-all/site/molmo/live`
- `.venv/bin/python scripts/molmo_cleanup/assemble_ci_live_pages.py output/molmo/ci-rehearsal-all/site/molmo/live output/molmo/ci-rehearsal-all/site-copy/molmo/live`
- `.venv/bin/python scripts/reports/write_pages_index.py output/molmo/ci-rehearsal-all/site-copy --include-molmo-live`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/ci_live_reports.py scripts/molmo_cleanup/prewarm_molmospaces_ci_assets.py scripts/molmo_cleanup/run_live_claude_cleanup.py scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py scripts/molmo_cleanup/assemble_ci_live_pages.py scripts/reports/write_pages_index.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/ci_live_reports.py scripts/molmo_cleanup/prewarm_molmospaces_ci_assets.py scripts/molmo_cleanup/run_live_claude_cleanup.py scripts/molmo_cleanup/run_ci_live_cleanup_matrix.py scripts/molmo_cleanup/assemble_ci_live_pages.py scripts/reports/write_pages_index.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `python3 -c "import pathlib, yaml; yaml.safe_load(pathlib.Path('.github/workflows/ci.yml').read_text()); print('workflow yaml ok')"`
