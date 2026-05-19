# Real Robot Nav2 Cleanup Pilot Active Status

Last updated: 2026-05-19

## Implemented

- Plan and ADR-backed implementation landed in scoped commits. Current status
  records the supported end state rather than the historical CI Codex
  experiment: Codex proof is local-only through repo-local `.env`; hosted CI
  supports deterministic checks plus supported Claude Code and OpenClaw routes.
- `real_robot_cleanup_v1` exists and is included in
  `skills/molmo-realworld-cleanup/skill.json`.
- `DirectNav2Adapter` exists with mocked tests for success, timeout, cancel,
  distance rejection, and blocked manipulation.
- `run_physical_nav2_cleanup_pilot()` loads a validated prebuilt bundle plus
  robot profile, attempts every public inspection waypoint and every fixture
  preferred waypoint through `DirectNav2Adapter`, observes from reached
  waypoints with public camera-label evidence, keeps manipulation tools
  `blocked_capability`, snapshots `map_bundle/`, and renders
  `physical_navigation_pilot=true` / `physical_cleanup_ready=false`.
- Reusable Nav2 map bundle logic now lives under `roboclaws/maps/` with bundle
  writing/validation, metric-map projection, occupancy rasterization, and
  static costmap route validation.
- `scripts/maps/export_bundle.py` exports a public `agent_view` into a
  prebuilt bundle, and `scripts/maps/check_bundle.py` validates required
  Nav2/cleanup artifacts before agent runtime.
- `assets/maps/molmo-cleanup-default-7/` is a checked-in prebuilt map bundle
  with `map.yaml`, `map.pgm`, `semantics.json`, `profiles/rby1m.yaml`,
  `costmaps/rby1m.costmap_params.yaml`, and `preview.png`.
- Direct, MCP smoke, and live-agent cleanup entrypoints now accept
  `--map-bundle-dir` plus `--require-map-bundle`; non-smoke public
  `just task::run molmo-cleanup ...` profiles default to
  `assets/maps/molmo-cleanup-default-7` and fail before cleanup startup when
  the selected bundle is missing or invalid.
- `RealWorldCleanupContract.metric_map()` and `fixture_hints()` can project
  from the selected prebuilt bundle, and run finalizers copy that selected
  bundle into the immutable per-run `map_bundle/` snapshot.
- Molmo `navigate_to_waypoint` now records `navigation_backend:
  sim_costmap_planner` with route metadata while keeping manipulation
  primitives honestly semantic unless planner-backed evidence is attached.
- Molmo cleanup finalizers snapshot a Nav2-shaped `map_bundle/` into each run.
- Cleanup reports render a `Nav2 Map Bundle` section with `map.yaml`,
  `map.pgm`, `semantics.json`, robot profile, costmap params, preview, hashes,
  runtime costmap gaps, and static route-validation readiness.
- Detached Codex Molmo runs pass selected exported API/proxy environment
  variables into tmux, and the Docker-backed coding-agent wrapper forwards
  proxy variables into Codex.
- Local Codex runs are configured from the repo-local `.env` via
  `CODEX_BASE_URL`, `CODEX_API_KEY`, and supported provider/model settings.
  Hosted CI does not support Codex, Codex provider smoke, or Codex acceptance
  artifacts.
- The local Codex Nav2 cleanup command explicitly selects
  `map_bundle=molmo-cleanup-default-7`, validates the run-local
  `seed-7/map_bundle/` snapshot with `scripts/maps/check_bundle.py`, and uses a
  stricter world-labels kickoff prompt that tells Codex to plan through
  `metric_map` / `fixture_hints`, build an exact waypoint checklist, and avoid
  raw occupancy-image planning.
- The shared `world-labels` checker gate now requires waypoint honesty,
  real-robot alignment, `--min-restored-count 5`, and
  `--min-sweep-coverage 1.0`; local/operator Codex runs fail against that same
  cleanup bar.
- The Codex live runner now tolerates nonblocking console mirrors while keeping
  `codex-events.jsonl`, `codex.stderr.log`, and checker artifacts intact, matching
  the existing Claude runner behavior.
- The Codex live runner now defaults `world-labels` runs to the no-regression /
  real-robot-alignment checker floor even if a caller bypasses
  the public `just` recipe and invokes `run_live_codex_cleanup.py` directly.
- Broken legacy Molmo compatibility symlinks at removed root paths were deleted
  so the repo-wide static gate no longer asks Ruff to lint missing files.

## Verified

- Pre-commit fast subset passed on each implementation commit.
- Focused contract checks passed for skill manifests, semantic profiles,
  Nav2 adapter, cleanup artifacts, and Codex provider wiring.
- Latest deterministic map-package smoke:
  `output/molmo/nav2-map-package-smoke/0519_1700/seed-7/report.html`
- Detached Codex env propagation check:
  `output/molmo/codex-gpt55-nav2-openai-env-pass-check/0518_2219/seed-7`
  reaches Codex with `openai-responses` and fails on the OpenAI network reset,
  not on missing `OPENAI_API_KEY`.
- Fast guard check:
  `output/molmo/codex-gpt55-nav2-openai-fast-guard-check/0518_2228` fails
  before tmux launch because `api.openai.com` is not reachable.
- Shell syntax/routing checks: `bash -n scripts/dev/coding_agent_docker.sh` and
  `bash -n scripts/dev/coding_agent_env.sh`; `just --list`.
- Maintainer mock gate: `just agent::verify mock` passes after the broken
  legacy symlink cleanup.
- Latest focused checks for the map contract slice:
  - `uv run ruff check roboclaws/maps roboclaws/molmo_cleanup/nav2_map_bundle.py roboclaws/molmo_cleanup/realworld_contract.py roboclaws/molmo_cleanup/report.py scripts/maps tests/contract/maps tests/contract/molmo_cleanup/test_molmo_realworld_contract.py scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_nav2_map_bundle_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py -q`
  - pre-commit fast non-integration pytest subset on `31637c4`
  - `uv run python scripts/maps/check_bundle.py assets/maps/molmo-cleanup-default-7`
  - `uv run python scripts/maps/check_bundle.py output/molmo/nav2-map-package-smoke/0519_1700/seed-7/map_bundle`
  - report content audit confirmed `Static costmap routes`,
    `sim_costmap_planner`, `Nav2 Map Bundle`, and `map_bundle/map.yaml` render
    in `output/molmo/nav2-map-package-smoke/0519_1700/seed-7/report.html`.
- Latest selected-bundle runtime gate checks:
  - `uv sync --extra dev`
  - `uv run ruff check roboclaws/maps roboclaws/molmo_cleanup/nav2_map_bundle.py roboclaws/molmo_cleanup/realworld_contract.py roboclaws/molmo_cleanup/realworld_mcp_server.py examples/molmo_cleanup/molmospaces_realworld_cleanup.py examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py just tests/contract/maps tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/dev_tools/test_task_agent_just_recipes.py`
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_nav2_map_bundle_contract.py tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  - `just --list`
  - `just task::run molmo-cleanup direct smoke output_dir=output/molmo/nav2-selected-bundle-smoke seed=7 generated_mess_count=5 map_bundle=molmo-cleanup-default-7`
  - `uv run python scripts/maps/check_bundle.py output/molmo/nav2-selected-bundle-smoke/0519_1728/seed-7/map_bundle`
  - `uv run python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py output/molmo/nav2-selected-bundle-smoke/0519_1728 --expect-backend api_semantic_synthetic --expect-policy deterministic_sweep_baseline --expect-profile smoke --expect-seeds 7 --min-generated-mess-count 5 --require-advisory-scoring --min-restored-count 5 --min-sweep-coverage 1.0 --require-waypoint-honesty --require-real-robot-alignment`
- Latest deterministic physical-pilot contract checks:
  - `uv run ruff check roboclaws/molmo_cleanup/nav2_adapter.py roboclaws/molmo_cleanup/physical_nav2_pilot.py roboclaws/molmo_cleanup/report.py scripts/molmo_cleanup/run_physical_nav2_cleanup_pilot.py tests/contract/molmo_cleanup/test_nav2_adapter.py tests/contract/molmo_cleanup/test_physical_nav2_pilot.py`
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_nav2_adapter.py tests/contract/molmo_cleanup/test_physical_nav2_pilot.py tests/contract/reports/test_molmo_cleanup_report.py -q`
  - `uv run python scripts/molmo_cleanup/run_physical_nav2_cleanup_pilot.py --map-bundle-dir assets/maps/molmo-cleanup-default-7 --run-dir output/molmo/physical-nav2-pilot-local-check`
  - `uv run python scripts/maps/check_bundle.py output/molmo/physical-nav2-pilot-local-check/map_bundle`
  - report content audit confirmed `physical_navigation_pilot=true`,
    `physical_cleanup_ready=false`, `nav2_action=18`, and `Nav2 Map Bundle`
    render in
    `output/molmo/physical-nav2-pilot-local-check/report.html`.
- Latest local Codex consumption hardening checks:
  - `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); print('yaml ok')"`
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/molmo_cleanup/test_ci_live_reports.py -q`
  - `just task::run molmo-cleanup codex world-labels map_bundle=molmo-cleanup-default-7` traces to the local Codex live route with the selected bundle override.
  - commit hook fast non-integration pytest subset passed on `9f78781`.
  - push CI `26090699226` and PR CI `26090702438` passed on branch head
    `9f78781`; normal push / pull_request CI stayed green.
  - `uv sync --extra dev --extra molmospaces`
  - `uv run ruff check tests/contract/dev_tools/test_task_agent_just_recipes.py`
  - `uv run ruff format --check tests/contract/dev_tools/test_task_agent_just_recipes.py`
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/molmo_cleanup/test_ci_live_reports.py -q`
  - `ROBOCLAWS_JUST_TRACE=1 just task::run molmo-cleanup codex world-labels map_bundle=molmo-cleanup-default-7`
  - `git diff --check`
  - commit hook fast non-integration pytest subset passed on `e603873`.
  - `uv run ruff check scripts/molmo_cleanup/run_live_codex_cleanup.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
  - `uv run ruff format --check scripts/molmo_cleanup/run_live_codex_cleanup.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_ci_live_reports.py -q`
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_ci_live_reports.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  - `git diff --check`
  - commit hook fast non-integration pytest subset passed on `b7dc8e0`.
  - push CI `26092360723` and PR CI `26092363092` passed on branch head
    `c93a760`; normal push / pull_request CI stayed green.
  - final status-only push CI `26092495797` and PR CI `26092497470` passed on
    branch head `2f2b19c`; normal push / pull_request CI stayed green.
  - `uv run ruff check scripts/molmo_cleanup/run_live_codex_cleanup.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
  - `uv run ruff format --check scripts/molmo_cleanup/run_live_codex_cleanup.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_ci_live_reports.py -q`
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_ci_live_reports.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  - `git diff --check`
  - commit hook fast non-integration pytest subset passed on `e2582c4`.
  - Attempted deterministic artifact exercise:
    `just task::run molmo-cleanup direct world-labels output_dir=output/molmo/world-labels-strict-gate-check seed=7 generated_mess_count=5 map_bundle=molmo-cleanup-default-7`.
    After installing the declared `molmospaces` extra, the run remained stuck
    in the Molmo subprocess worker `snapshot` step before producing
    `before.png`; it was terminated with exit `143`, leaving no
    `run_result.json`, `report.html`, or `map_bundle/` artifact for this
    local check.
- Latest focused checks for the CI launcher fixes:
  - `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); print('yaml ok')"`
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_ci_live_reports.py tests/contract/dev_tools/test_code_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  - pre-commit fast non-integration pytest subset on `fa6042c`
- Latest runtime-boundary cleanup checks:
  - `rg -n "codex" .github/workflows/ci.yml || true` returned no workflow Codex references.
  - `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); print('yaml ok')"`
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_code_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  - `ROBOCLAWS_JUST_TRACE=1 just task::run molmo-cleanup codex world-labels map_bundle=molmo-cleanup-default-7`
  - `git diff --check`
  - push CI `26094330522` and PR CI `26094327321` passed on branch head
    `9f87bd0`; hosted live/Pages jobs skipped as expected on this branch event.
- Explicit checker passed:

```bash
uv run python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  output/molmo/nav2-map-package-smoke/0519_1700 \
  --expect-backend api_semantic_synthetic \
  --expect-policy deterministic_sweep_baseline \
  --expect-profile smoke \
  --expect-seeds 7 \
  --min-generated-mess-count 5 \
  --require-advisory-scoring \
  --min-restored-count 5 \
  --min-sweep-coverage 1.0 \
  --require-waypoint-honesty \
  --require-real-robot-alignment
```

Result: restored `5/5`, sweep coverage `1.0`, Nav2 map bundle present,
`sim_costmap_planner` route validation present.

Resume audit on 2026-05-18T18:26:51Z:

- The explicit checker above was rerun and passed.
- Focused contract tests for the Nav2 adapter, Molmo cleanup report, MCP
  semantic profile, checker wiring, and CI route passed: `52 passed`.
- A report content audit confirmed
  `output/molmo/nav2-map-regression/0518_2046/seed-7/report.html` still renders
  `Nav2 Map Bundle`, `map_bundle/map.yaml`, restored `5/5`, sweep `100%`, and
  the expected `api_semantic_synthetic` / `realworld_contract_smoke_agent`
  metadata.

## Completion Audit Checklist

Objective requirements mapped to current evidence:

| Requirement | Evidence | Status |
| --- | --- | --- |
| Implement `docs/plans/real-robot-nav2-cleanup-pilot.md` | Commits `1d76f0d`, `fd01173`, `7f7f987`, `daff692`, `0c67850`, `f27f552`, `0a7ebb7`, `61c5903`, `4c5c185`, `d9e0c00`, `4734fab`, `49ecbee`, `d568bc7`, `3e4de60`, `2ac1d44`, `764a806`, `1d61de9`, `31b42d4`, `90a80d9`, `4b3385f`, `3b7c585`, `f2bb97b`, `31637c4`, `d70ca89`, `cb41d9c`, `9f78781`, `e603873`, `b7dc8e0`, `c93a760`, `2f2b19c`, `e2582c4`; this status file tracks the local Codex consumption boundary cleanup. | Implemented; local Codex proof remains operator-run |
| Honor ADR-0127 direct Nav2 adapter before ROSClaw | `roboclaws/molmo_cleanup/nav2_adapter.py`; `tests/contract/molmo_cleanup/test_nav2_adapter.py` covers success, timeout, cancel, max-distance rejection, and blocked manipulation. | Implemented |
| Honor ADR-0128 `real_robot_cleanup_v1` profile | `roboclaws/mcp/profiles.py`; `skills/molmo-realworld-cleanup/skill.json`; semantic profile tests. | Implemented |
| Honor ADR-0129 Nav2 map artifacts for simulator/hardware parity | `roboclaws/maps/`; `scripts/maps/check_bundle.py`; `assets/maps/molmo-cleanup-default-7/`; direct and MCP finalizers copy the selected prebuilt bundle into `map_bundle/`; `metric_map()` / `fixture_hints()` project from selected bundles; `navigate_to_waypoint` records `sim_costmap_planner` route metadata. | Implemented |
| Add Nav2 nav maps to report file | `output/molmo/nav2-map-package-smoke/0519_1700/seed-7/report.html` contains `Nav2 Map Bundle`, `map_bundle/map.yaml`, preview, hashes, runtime gap notes, and `Static costmap routes`. | Verified on deterministic report |
| Ensure cleanup report has no clear regression | Deterministic smoke `output/molmo/nav2-selected-bundle-smoke/0519_1728` passed checker with restored `5/5`, sweep coverage `1.0`, selected bundle projection, and run-local selected bundle snapshot. | Verified for deterministic smoke |
| First hardware pilot acceptance path | Deterministic artifact `output/molmo/physical-nav2-pilot-local-check/report.html` loads the selected prebuilt bundle and `rby1m` profile, attempts 8 inspection waypoints plus 10 fixture preferred waypoints through `DirectNav2Adapter`, observes every reached waypoint, blocks `pick`/`place`/`place_inside`/`open_receptacle`/`close_receptacle`, snapshots `map_bundle/`, and renders `physical_navigation_pilot=true` / `physical_cleanup_ready=false`. | Implemented with mock Nav2 client; real hardware still operator-run |
| Keep MolmoSpaces cleanup consumable by local Codex | The local Codex route uses the pinned coding-agent runtime, passes repo-local `.env` API/provider settings into detached Molmo runs, explicitly selects `map_bundle=molmo-cleanup-default-7`, checks `seed-7/map_bundle/`, and runs the no-regression / real-robot-alignment checker. Hosted CI no longer supports Codex and must not publish Codex acceptance artifacts. | Local route implemented; live proof is operator-run |
| Commit in scoped chunks | Current branch contains small implementation, fallback, guard, and blocker/audit commits. | Satisfied |

Completion rule: hosted CI Codex artifacts are not a completion gate. Codex
acceptance evidence, when needed, is a local operator run through the repo-local
`.env` route that produces `run_result.json`, `report.html`, and
`map_bundle/map.yaml` and passes the real-robot-alignment checker without a
clear cleanup regression.

## Runtime Boundary

Hosted CI does not support Codex. It may run deterministic checks plus supported
Claude Code and OpenClaw routes, but it must not launch Codex, run Codex
provider smoke, or publish Codex acceptance artifacts.

Local runtime support:

- Work network: Codex and Claude Code are supported only through the local
  CLI/runtime using API base, key, provider, and model settings from the
  repo-local `.env`; OpenClaw is not supported.
- Non-work network: the same `.env`-configured Codex and Claude Code routes are
  supported, plus OpenClaw.

Current local Codex evidence:

- The route wiring passes selected API/proxy environment variables into detached
  Molmo tmux runs and forwards proxy variables into the Docker-backed
  coding-agent wrapper.
- `world-labels` runs default to the no-regression /
  real-robot-alignment checker floor even when invoked through
  `run_live_codex_cleanup.py` directly.

## Next Action

Run any Codex cleanup proof locally through the repo-local `.env` configuration:

```bash
just task::run molmo-cleanup codex world-labels \
  output_dir=output/molmo/codex-gpt55-nav2-report \
  seed=7 \
  generated_mess_count=5 \
  map_bundle=molmo-cleanup-default-7
```

Validate the resulting local report with `scripts/maps/check_bundle.py` and the
cleanup checker using `--require-real-robot-alignment`. Do not use GitHub
Actions or repository `OPENAI_API_KEY` secrets for Codex proof.
