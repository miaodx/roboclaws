# MolmoSpaces CI Live-Agent Reports

**Status:** Draft pre-GSD plan
**Created:** 2026-05-13
**Source:** User request; local comparison artifacts:
`output/molmo/compare-claude/kimi-k2.6/0513_1447/seed-7/report.html`,
`output/molmo/compare-claude/mimo-v2.5-pro-simple/0513_1526/seed-7/report.html`,
`output/molmo/compare-claude/mimo-v2-omni-simple/0513_1557/seed-7/report.html`;
`README.md`; `ARCHITECTURE.md`; `STATUS.md`; `.github/workflows/ci.yml`;
`just/molmo.just`; `scripts/reports/write_pages_index.py`
**Workflow:** `intuitive-flow` inline pre-plan

## Problem

The local MolmoSpaces cleanup runs for Kimi and two MiMo models now produce
reviewable `world-labels` reports for the same seed-7 task. Those reports are
useful because they show Agent View, Private Evaluation, semantic cleanup
substeps, RBY1M robot views, and checker-friendly run metadata.

The public CI Pages site does not yet publish this live Molmo cleanup matrix.
Today it publishes mock reports, Kimi AI2-THOR smokes, and best-effort OpenClaw
reports. Users still need local filesystem access to visualize the successful
Molmo cleanup artifacts.

## Goal

Add a CI path that can run the three proven Molmo cleanup live-agent variants
and publish their reports to GitHub Pages:

- Kimi K2.6
- MiMo v2.5 Pro simple
- MiMo v2 Omni simple

The result should be a stable web entrypoint from the existing Pages landing
page to each `report.html`, with enough CI metadata to tell whether a missing
tile is a skipped run, missing secret, install failure, timeout, or model run
failure.

## Idea-Shaping Mode

Direct route default. The user supplied concrete working artifacts and a likely
implementation shape, so this plan records repo-derived decisions and leaves
promotion/status-display choices open for approval before GSD handoff.

## Decisions Already Made

| # | Decision | Rationale |
|---|---|---|
| 1 | Use `docs/plans/` as the pre-GSD source of truth. | `STATUS.md` says there is no active GSD phase, and repo guidance routes pre-execution work through plans. |
| 2 | Treat the local seed-7 artifacts as the first validation evidence. | The request names three known-good artifacts; CI should preserve that proof, not discover a new task shape first. |
| 3 | Publish Molmo reports through the existing Pages job, not a separate static hosting path. | `.github/workflows/ci.yml` already assembles `site/` and deploys via GitHub Pages. |
| 4 | Keep live Molmo jobs best-effort at first. | Existing OpenClaw jobs use `continue-on-error` so flaky real-provider paths do not block the baseline Pages publish. |
| 5 | Use the existing `just task::run molmo-cleanup <driver> world-labels` facade where practical. | `AGENTS.md` and `just/task.just` make this the public command grammar. |

## Decisions Resolved On 2026-05-13

| # | Decision | Rationale | Revisit If |
|---|---|---|---|
| 1 | Use GitHub-hosted `ubuntu-latest` first. | The team wants CI-machine proof if possible, and this mirrors the existing AI2-THOR smoke jobs. | Two consecutive runs fail because of disk, renderer, missing asset, or hosted-runner runtime constraints after caching/prewarm is in place. |
| 2 | Cache MolmoSpaces assets in GitHub Actions, analogous to the existing `~/.ai2thor` cache. | The proven local run stores the target scene under `~/.cache/molmospaces/assets/.../scenes/procthor-10k-val/val_0.xml`; caching avoids re-downloading or reinstalling the same MuJoCo scene each run. | The asset root proves non-deterministic across CI checkouts, in which case add a stable `MOLMOSPACES_*` cache-root override before falling back to self-hosted CI. |
| 3 | Cache both `~/.cache/molmospaces` and `~/.cache/molmo-spaces-resources`. | Runtime scene/robot assets live under `~/.cache/molmospaces/assets`, while ADR-0104 identifies `~/.cache/molmo-spaces-resources` as the symlink-resolved resource/grasp-cache root used by MolmoSpaces loaders. | Cache size exceeds GitHub cache limits or restore time becomes larger than cold prewarm. |
| 4 | Add a dedicated prewarm step before the live model call. | The live agent should spend its budget on cleanup behavior, not lazy scene/robot installation. | Prewarm alone cannot validate robot-view rendering; then make prewarm write one small RBY1M view bundle. |
| 5 | Start with `workflow_dispatch` plus a `[molmo-live]` push tag on `main`, not every push. | The full matrix can take about an hour and spends real provider budget. Opt-in CI gives reviewable web artifacts without slowing normal pushes. | After several green tagged runs, promote to a nightly schedule or required main smoke. |
| 6 | Run the three variants as a matrix with `max-parallel: 1`, `fail-fast: false`, and model-specific artifacts. | This keeps the workflow compact while serializing provider/MuJoCo load. | Matrix artifact aggregation makes Pages assembly brittle; then split into three chained jobs. |
| 7 | Live Molmo failures do not block baseline Pages deployment. | Missing live-provider evidence should be visible through status artifacts, but it should not remove existing mock, Kimi smoke, or OpenClaw reports. | The live matrix becomes the primary release gate. |
| 8 | Install and version-check both Codex and Claude Code in the live job, but run the first live cleanup matrix through Claude Code. | The working local artifacts are under `compare-claude`, and the existing Codex lifecycle is useful as a reference/secondary smoke. | The team wants Codex-vs-Claude cleanup comparison as part of the same public matrix. |
| 9 | Use only repo-scoped provider secrets: `KIMI_API_KEY` and `MIMO_TP_KEY`. | Repo-local provider profiles can map those keys to Anthropic-compatible Claude Code endpoints without exposing `.env`. | Provider auth changes or GitHub Actions secret policy needs a narrower environment. |
| 10 | Mimic the GitHub CI job locally before editing the workflow. | A local rehearsal can prove command shape, cache roots, prewarm, live-agent lifecycle, checker gates, and Pages assembly before spending hosted CI attempts. | The local machine and GitHub-hosted runner differ in a way the rehearsal cannot model, such as disk pressure or renderer behavior. |

## Remaining Open Decisions

| # | Question | Default Recommendation | Why It Matters |
|---|---|---|---|
| 1 | Should successful opt-in live reports be promoted to nightly after initial proof? | Yes, after two green `[molmo-live]` runs on GitHub-hosted CI. | Nightly keeps the public Pages result fresh without imposing a one-hour cost on every push. |
| 2 | Should the first implementation publish failed/skipped model status tiles, or only successful report links? | Publish status tiles from a small manifest. | Silent omission makes it hard to distinguish a skipped run from a broken model. |

## Non-Goals

- Do not add planner-backed RBY1M/CuRobo proof execution to this CI path.
- Do not require all live Molmo runs to pass before the baseline Pages site
  deploys.
- Do not commit ignored `output/` artifacts.
- Do not replace local validation; CI should continuously reproduce an already
  proven local run.
- Do not broaden the cleanup task beyond seed 7 and the existing Chinese task
  prompt in the first version.
- Do not expose private scoring truth to the live agent. Private Evaluation can
  remain in the final report artifact.

## Smallest Demo

Add an opt-in CI job that runs one known-good live cleanup variant and publishes
it to Pages:

```bash
ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic \
ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6 \
just task::run molmo-cleanup claude world-labels \
  seed=7 \
  generated_mess_count=5 \
  output_dir=output/molmo/ci-live/kimi-k2.6
```

Acceptance evidence:

- `output/molmo/ci-live/kimi-k2.6/<stamp>/seed-7/report.html`
- `run_result.json` has `backend=molmospaces_subprocess`,
  `policy=claude_agent`, `cleanup_profile=world-labels`,
  `agent_driven=true`, `adr_0003_satisfied=true`, and `final_status=success`.
- Pages exposes the report at
  `/molmo/live/kimi-k2.6/seed-7/report.html` or a similarly stable path.

## Fuller Demo

Run and publish the three-model comparison matrix:

| Page Tile | Provider Profile | Model | Expected Driver |
|---|---|---|---|
| Kimi K2.6 | `kimi-anthropic` | `kimi-k2.6` | `claude` |
| MiMo v2.5 Pro Simple | `mimo-anthropic` | `mimo-v2.5-pro` | `claude` |
| MiMo v2 Omni Simple | `mimo-anthropic` or provider-specific profile | `mimo-v2-omni` | `claude` |

The first implementation should mirror the local artifacts' shape:

- seed: `7`
- task: `帮我收拾这个房间`
- profile: `world-labels`
- generated mess count: `5` if the goal is exact comparison with the cited
  local runs; `10` only after confirming the longer task stays inside the CI
  budget.
- expected artifact size: about 20 MB per successful run based on the three
  cited local directories.

## Local CI Rehearsal

Before changing `.github/workflows/ci.yml`, add or run a repo-local rehearsal
that mirrors the future live Molmo CI job on the local workstation.

The rehearsal should use the same command structure, cache roots, environment
variables, output layout, checker, and Pages assembly logic that GitHub Actions
will use.

Minimum local rehearsal:

```bash
uv sync --extra dev --extra molmospaces

ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic \
ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6 \
KIMI_API_KEY="$KIMI_API_KEY" \
just task::run molmo-cleanup claude world-labels \
  seed=7 \
  generated_mess_count=5 \
  output_dir=output/molmo/ci-rehearsal/kimi-k2.6
```

Preferred command surface:

```bash
just molmo::ci-rehearsal kimi-k2.6
just molmo::ci-rehearsal mimo-v2.5-pro-simple
just molmo::ci-rehearsal mimo-v2-omni-simple
```

The `ci-rehearsal` recipe should:

- print `codex --version` and `claude --version`;
- run `uv sync --extra dev --extra molmospaces` or verify the synced
  environment;
- use/cache the same roots planned for CI:
  `~/.cache/uv`, `~/.cache/molmospaces`, and
  `~/.cache/molmo-spaces-resources`;
- prewarm `procthor-10k-val/val_0.xml` with `rby1m`, seed 7, and
  `generated_mess_count=5`;
- run the live model variant non-interactively;
- run `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`;
- assemble a local Pages preview under `output/molmo/ci-rehearsal/site/`;
- write a small manifest showing each model's status, report path, and failure
  reason if any.

This is not a replacement for GitHub-hosted proof. It is the first executable
gate before committing workflow YAML.

## Implementation Slices

1. Add a local CI rehearsal wrapper.

   - Add `just molmo::ci-rehearsal <model-entry>` or a script under
     `scripts/molmo_cleanup/` that can be called by both the local recipe and
     GitHub Actions.
   - Support the three model entries:
     `kimi-k2.6`, `mimo-v2.5-pro-simple`, and
     `mimo-v2-omni-simple`.
   - Use `output/molmo/ci-rehearsal/<model>/` locally and the same internal
     layout the CI artifact upload will expect.
   - The first successful rehearsal only needs one model; the full rehearsal
     should run all three serially.

2. Add a CI-safe Molmo live command wrapper.

   - Prefer a script under `scripts/molmo_cleanup/` that accepts a run matrix
     entry and calls the existing `just task::run` or lower-level recipe.
   - Make it non-interactive for CI. `just molmo::claude-report` currently
     launches `claude` interactively; CI likely needs a Claude Code print/exec
     mode equivalent or a wrapper that feeds the kickoff prompt and exits.
   - Codex already has `scripts/molmo_cleanup/run_live_codex_cleanup.py` using
     `codex exec`; mirror that lifecycle for Claude Code if no equivalent
     exists.

3. Install and verify coding-agent CLIs in CI.

   - Install Node.js 22 before CLI install, which satisfies the newer Codex
     npm path and exceeds Claude Code's Node 18+ floor.
   - Install Codex and Claude Code from pinned versions or a repo variable,
     normally via `npm install -g @openai/codex @anthropic-ai/claude-code`,
     then run `codex --version` and `claude --version`.
   - Keep the repo wrappers' full-permission defaults for live demos; do not add
     bare `codex` or `claude` launch paths that silently change permissions.
   - For provider profiles, set `ROBOCLAWS_CLAUDE_PROVIDER` /
     `ROBOCLAWS_CLAUDE_MODEL` and pass `KIMI_API_KEY` / `MIMO_TP_KEY` via
     secrets.

4. Prepare the MolmoSpaces runtime.

   - Switch CI setup for this job to `uv sync --extra dev --extra molmospaces`
     instead of plain `pip install -e ".[dev]"`.
   - Cache uv downloads, Git dependency checkout/build state, and the
     MolmoSpaces/MuJoCo assets that are safe to cache.
   - Add `actions/cache@v4` entries for:
     - `~/.cache/uv`
     - `~/.cache/molmospaces`
     - `~/.cache/molmo-spaces-resources`
   - Key MolmoSpaces caches by runner OS, Python version, `uv.lock`,
     `pyproject.toml`, scene source/index, robot name, and generated mess count.
   - Add a prewarm step that initializes the exact scene used by the local
     proof: `scene_source=procthor-10k-val`, `scene_index=0`, `seed=7`,
     `include_robot=true`, `robot_name=rby1m`, and `generated_mess_count=5`.
   - Prefer a dedicated prewarm script over relying on the first live agent run
     to lazily install scenes. The prewarm script should assert:
     - `import molmo_spaces` succeeds;
     - `~/.cache/molmospaces/assets/.../scenes/procthor-10k-val/val_0.xml`
       exists after install;
     - the RBY1M robot XML exists;
     - one minimal robot-view capture can be written, unless this proves too
       slow for GitHub-hosted CI.

5. Add the live Molmo CI job.

   - Trigger: start with `workflow_dispatch` and optional `[molmo-live]` push
     tag on `main`.
   - Timeout: set explicit job `timeout-minutes: 90` and per-run step
     `timeout-minutes: 60` so hangs fail with useful logs.
   - Concurrency: `molmo-live-agent` with `cancel-in-progress: false`.
   - Matrix: three entries with `max-parallel: 1` and `fail-fast: false`.
   - Upload artifact names:
     - `report-molmo-live-kimi-k2.6`
     - `report-molmo-live-mimo-v2.5-pro-simple`
     - `report-molmo-live-mimo-v2-omni-simple`
   - Always upload `report.html`, `run_result.json`, `trace.jsonl`,
     `agent_view.json`, `private_evaluation.json`,
     `advisory_evaluation.json`, `planner_proof_requests.json`,
     `before.png`, `after.png`, `robot_views/**`, and driver/checker logs.

6. Publish the live Molmo reports to Pages.

   - Extend `publish-pages.needs` with the new live Molmo job, but keep it
     best-effort like the OpenClaw jobs.
   - Download `report-molmo-live-kimi-k2.6`,
     `report-molmo-live-mimo-v2.5-pro-simple`, and
     `report-molmo-live-mimo-v2-omni-simple` best-effort into
     `molmo-live-src/<model>/`.
   - Copy successful matrix entries to stable paths under `site/molmo/live/`.
   - Extend `scripts/reports/write_pages_index.py` with an
     `--include-molmo-live` flag that auto-detects available model directories
     and renders tiles.
   - Consider a small `manifest.json` for the landing page so failed/skipped
     entries can display status instead of silently disappearing.

7. Add focused tests.

   - Test Pages index generation detects `site/molmo/live/<model>/seed-7`.
   - Test the CI wrapper builds the right provider environment without exposing
     secrets.
   - Test report artifact validation can run on a directory containing only the
     uploaded subset.
   - Keep real Molmo live execution marked local/slow or CI-opt-in; do not make
     it part of `lint-and-mock`.

## Acceptance Criteria

- GitHub Actions can install and verify both `codex` and `claude` CLIs in the
  live Molmo job.
- A local CI rehearsal can run at least the Kimi K2.6 variant through prewarm,
  live cleanup, checker validation, artifact staging, and local Pages assembly
  before the workflow YAML is changed.
- The first implementation attempts GitHub-hosted `ubuntu-latest` before
  introducing self-hosted runner requirements.
- The CI job can run long enough for the target report, with explicit
  job/step timeouts and non-interactive failure logs.
- MolmoSpaces scene/runtime assets under `~/.cache/molmospaces` and
  `~/.cache/molmo-spaces-resources` are prewarmed or restored from cache before
  the live model call starts.
- At least one live Molmo report is published to GitHub Pages from CI.
- The full matrix publishes Kimi K2.6, MiMo v2.5 Pro simple, and MiMo v2 Omni
  simple reports from the same seed/task shape as the local artifacts.
- The Pages landing page links directly to each available report.
- Missing or failed live Molmo entries leave diagnostics in GitHub Actions
  artifacts and do not remove baseline mock/smoke/OpenClaw report visibility.
- No provider secret, `.env` content, bearer token, or raw credential-bearing
  config is written into uploaded artifacts or Pages.

## Verification Plan

Local/non-provider checks:

```bash
uv sync --extra dev --extra molmospaces
ruff check .github scripts/reports scripts/molmo_cleanup
ruff format --check .github scripts/reports scripts/molmo_cleanup
./scripts/dev/run_pytest_standalone.sh -q tests/contract/reports tests/unit/molmo_cleanup
```

Live checks after owner approval:

```bash
ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic \
ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6 \
just task::run molmo-cleanup claude world-labels \
  seed=7 \
  generated_mess_count=5 \
  output_dir=output/molmo/ci-live/kimi-k2.6
```

Then run the checker:

```bash
.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  --expect-backend molmospaces_subprocess \
  --expect-policy claude_agent \
  --expect-profile world-labels \
  --expect-mcp-server molmo_cleanup_realworld \
  --min-generated-mess-count 5 \
  --require-agent-driven \
  --require-advisory-scoring \
  --require-robot-views \
  --require-waypoint-honesty \
  --require-real-robot-alignment \
  --require-clean-agent-run \
  output/molmo/ci-live/kimi-k2.6/<stamp>/seed-7/run_result.json
```

## Risks

- GitHub-hosted runners may not be reliable for real MolmoSpaces/MuJoCo
  rendering even with CPU torch and cached assets.
- Live provider CLI behavior can change; pin versions or make CLI versions
  repo variables.
- The existing Claude live recipe is interactive, while CI needs a
  non-interactive lifecycle like the Codex runner.
- Uploading full robot-view timelines is currently affordable at about 20 MB
  per cited run, but larger generated mess counts or raw-camera profiles can
  grow quickly.
- Best-effort live jobs can hide regressions if the landing page omits failed
  entries without status.

## External References To Verify During Implementation

- OpenAI Codex CLI getting started:
  `https://help.openai.com/en/articles/11096431-openai-codex-cli-getting-started`
- Claude Code setup:
  `https://docs.anthropic.com/en/docs/claude-code/getting-started`
- GitHub Actions workflow syntax for `timeout-minutes`:
  `https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions`

## GSD Handoff Trigger

After the owner approves the remaining open decisions above, hand this plan to
GSD as a new roadmap scope:

```yaml
docs:
  - path: docs/plans/molmospaces-ci-live-agent-reports.md
    type: PRD
```

Then run `gsd-ingest-docs --manifest <manifest> --mode merge`, inspect the
created roadmap phase, and run
`gsd-plan-phase <created-phase> --prd docs/plans/molmospaces-ci-live-agent-reports.md`.
