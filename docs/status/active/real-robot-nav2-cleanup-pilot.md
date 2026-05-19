# Real Robot Nav2 Cleanup Pilot Active Status

Last updated: 2026-05-19

## Implemented

- Plan and ADR-backed implementation landed in small commits:
  - `1d76f0d` `feat: snapshot nav2 map bundles in cleanup reports`
  - `fd01173` `feat: add real robot cleanup profile`
  - `7f7f987` `fix: allow codex responses websocket fallback`
  - `daff692` `fix: add openai codex http provider fallback`
  - `0c67850` `docs: record nav2 cleanup pilot blocker`
  - `f27f552` `fix: guard system codex on work network`
  - `0a7ebb7` `docs: note openai codex fallback key blocker`
  - `61c5903` `docs: audit codex nav2 cleanup blocker`
  - `4c5c185` `docs: add nav2 cleanup completion audit`
  - `d9e0c00` `docs: sync nav2 cleanup status commits`
  - `4734fab` `docs: record codex recipe preflight blocker`
  - `49ecbee` `docs: record codex openai smoke blocker`
  - `d568bc7` `docs: record local proxy audit blocker`
  - `3e4de60` `docs: record openai transport reset audit`
  - `2ac1d44` `docs: record codex openai task blocker`
  - `764a806` `fix: pass codex env into detached molmo runs`
  - `1d61de9` `docs: sync codex env fix evidence`
  - `31b42d4` `fix: fail fast when openai codex endpoint is unreachable`
  - `90a80d9` `fix: remove broken molmo legacy symlinks`
  - `4b3385f` `docs: note repo-local codex provider blockers`
  - `3b7c585` `docs: clarify codex provider smoke requirement`
  - `f2bb97b` `fix: guard codex provider smoke reachability`
  - `31615e9` `docs: sync codex provider blocker evidence`
  - `f1599c3` `docs: sync codex smoke guard evidence`
  - `12aee5a` `docs: record codex resume guard blocker`
  - `d27cce1` `docs: clarify official codex nav2 proof gate`
  - `8ade104` `ci: add official codex nav2 proof gate`
  - `a566b7f` `ci: preserve codex proof image tag`
  - `c6afc65` `docs: record official codex ci secret blocker`
  - `f6b1825` `docs: mark codex proof approval gate`
  - `70ccec1` `ci: wait for detached codex proof`
  - `d5bcf47` `fix: pass display env into codex molmo tmux`
  - `729da81` `ci: keep xvfb alive for codex molmo proof`
  - `fa6042c` `fix: normalize live agent docker workspace`
  - `771bbca` `docs: record official codex key blocker`
  - `76c542f` `ci: preflight official codex key`
  - `082896c` `docs: link codex proof key issue`
  - `f42420e` `docs: link nav2 cleanup draft pr`
  - `066a4ba` `docs: record codex key preflight run`
  - `236bbb2` `docs: record official artifact audit`
  - `e5a15cf` `docs: sync nav2 cleanup commit ledger`
  - `4dfda23` `docs: update current nav2 cleanup status`
  - `31637c4` `feat: add nav2 map bundle contract gate`
  - `d70ca89` `feat: gate cleanup runs on selected map bundles`
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
- `openai-responses` Codex runs now fail fast before detached launch when
  `api.openai.com` is unreachable from the invoking shell.
- `just code::codex-provider-smoke` uses the same `openai-responses`
  reachability guard, so the recommended preflight no longer waits for Codex
  retries when the official endpoint is blocked.
- CI has a dedicated opt-in official Codex GPT-5.5 Nav2 proof job gated by
  `workflow_dispatch` input `molmo_official_codex=true` and the repository
  `OPENAI_API_KEY` secret; it uploads
  `report-molmo-official-codex-gpt55-nav2` and runs the same no-regression /
  real-robot-alignment checker.
- The official CI job now runs a cheap Docker-backed Codex provider smoke before
  launching the Molmo backend, so missing or invalid official OpenAI credentials
  fail before Xvfb/tmux/Molmo runtime startup.
- The official CI proof keeps a manually managed Xvfb server alive for the
  detached tmux runner and normalizes live-agent Docker workspaces to absolute
  paths before mounting them.
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
- Latest focused checks for the CI launcher fixes:
  - `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); print('yaml ok')"`
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_ci_live_reports.py tests/contract/dev_tools/test_code_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  - pre-commit fast non-integration pytest subset on `fa6042c`
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
| Implement `docs/plans/real-robot-nav2-cleanup-pilot.md` | Commits `1d76f0d`, `fd01173`, `7f7f987`, `daff692`, `0c67850`, `f27f552`, `0a7ebb7`, `61c5903`, `4c5c185`, `d9e0c00`, `4734fab`, `49ecbee`, `d568bc7`, `3e4de60`, `2ac1d44`, `764a806`, `1d61de9`, `31b42d4`, `90a80d9`, `4b3385f`, `3b7c585`, `f2bb97b`, `31637c4`, `d70ca89`; this status file tracks the remaining gate. | Implemented except official Codex proof |
| Honor ADR-0127 direct Nav2 adapter before ROSClaw | `roboclaws/molmo_cleanup/nav2_adapter.py`; `tests/contract/molmo_cleanup/test_nav2_adapter.py` covers success, timeout, cancel, max-distance rejection, and blocked manipulation. | Implemented |
| Honor ADR-0128 `real_robot_cleanup_v1` profile | `roboclaws/mcp/profiles.py`; `skills/molmo-realworld-cleanup/skill.json`; semantic profile tests. | Implemented |
| Honor ADR-0129 Nav2 map artifacts for simulator/hardware parity | `roboclaws/maps/`; `scripts/maps/check_bundle.py`; `assets/maps/molmo-cleanup-default-7/`; direct and MCP finalizers copy the selected prebuilt bundle into `map_bundle/`; `metric_map()` / `fixture_hints()` project from selected bundles; `navigate_to_waypoint` records `sim_costmap_planner` route metadata. | Implemented |
| Add Nav2 nav maps to report file | `output/molmo/nav2-map-package-smoke/0519_1700/seed-7/report.html` contains `Nav2 Map Bundle`, `map_bundle/map.yaml`, preview, hashes, runtime gap notes, and `Static costmap routes`. | Verified on deterministic report |
| Ensure cleanup report has no clear regression | Deterministic smoke `output/molmo/nav2-selected-bundle-smoke/0519_1728` passed checker with restored `5/5`, sweep coverage `1.0`, selected bundle projection, and run-local selected bundle snapshot. | Verified for deterministic smoke |
| First hardware pilot acceptance path | Deterministic artifact `output/molmo/physical-nav2-pilot-local-check/report.html` loads the selected prebuilt bundle and `rby1m` profile, attempts 8 inspection waypoints plus 10 fixture preferred waypoints through `DirectNav2Adapter`, observes every reached waypoint, blocks `pick`/`place`/`place_inside`/`open_receptacle`/`close_receptacle`, snapshots `map_bundle/`, and renders `physical_navigation_pilot=true` / `physical_cleanup_ready=false`. | Implemented with mock Nav2 client; real hardware still operator-run |
| Use MolmoSpaces cleanup by official Codex GPT-5.5 as main implementation target | Latest opt-in official CI preflight `26046576875` reaches the official proof preflight, verifies `api.openai.com` is reachable, then fails Docker-backed Codex provider smoke with `401 invalid_api_key`; the Molmo proof step is skipped and no valid proof artifact is uploaded. Earlier local attempts fail on work-network OpenAI reachability or are historical runs without Nav2/no-regression evidence. | Blocked |
| Commit in scoped chunks | Current branch contains small implementation, fallback, guard, and blocker/audit commits. | Satisfied |

Completion rule: do not mark the goal complete until an official Codex GPT-5.5
Molmo cleanup run has a `run_result.json` and `report.html` that pass the
real-robot-alignment checker without a clear cleanup regression.

## Blocked Requirement

The official system-provider Codex GPT-5.5 Molmo cleanup run is not complete on
this work network, and the GitHub Actions official OpenAI route is blocked by
credentials. Direct local `https://api.openai.com/v1/responses` access is reset,
and no usable local HTTP/SOCKS proxy was found. In CI, the official endpoint is
reachable but the configured repository `OPENAI_API_KEY` secret is rejected by
OpenAI.

Latest fresh attempt:

- Command profile: `ROBOCLAWS_CODEX_PROVIDER=system`,
  `ROBOCLAWS_CODEX_MODEL=gpt-5.5`,
  `ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS=1`
- Run directory:
  `output/molmo/codex-gpt55-nav2-report-postfix/0518_2055/seed-7`
- Status: failed, exit `1`
- Trace: `3` runtime events, `0` cleanup requests, `0` responses
- Missing artifacts: `run_result.json`, `report.html`
- Error: stream disconnected before completion while sending request to
  `https://api.openai.com/v1/responses`

The official OpenAI API fallback is wired but cannot complete on this machine
yet:

- Command profile: `ROBOCLAWS_CODEX_PROVIDER=openai-responses`,
  `ROBOCLAWS_CODEX_MODEL=gpt-5.5`
- Status with repo `.env`: failed before launch because `.env` does not export
  `OPENAI_API_KEY`
- Status with host Codex auth key exported in-process: cheap
  `just code::codex-provider-smoke` reaches Codex startup but fails all retries
  against `https://api.openai.com/v1/responses`
- Error: `stream disconnected before completion: error sending request for url
  (https://api.openai.com/v1/responses)`

Latest task-level OpenAI fallback attempt:

- Command profile: `ROBOCLAWS_CODEX_PROVIDER=openai-responses`,
  `ROBOCLAWS_CODEX_MODEL=gpt-5.5`,
  `ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS=1`, host Codex auth key
  exported into the detached tmux environment without writing it to `.env`
- Run directory:
  `output/molmo/codex-gpt55-nav2-openai-env-pass-check/0518_2219/seed-7`
- Status: failed, exit `1`
- Trace: `3` runtime events, `0` cleanup requests, `0` responses
- Missing artifacts: `run_result.json`, `report.html`
- Error: `stream disconnected before completion: error sending request for url
  (https://api.openai.com/v1/responses)`
- Note: the earlier
  `output/molmo/codex-gpt55-nav2-openai-auth-tmux-check/0518_2214/seed-7`
  proved the same network blocker when the key was injected into tmux manually;
  `0518_2219` verifies the normal exported-shell path now reaches that blocker.

Latest unblock/audit check on 2026-05-18:

- `just dev::network-status` still reports `network: work`.
- `OPENAI_API_KEY`, `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` are unset after
  loading `.env`.
- Host Codex auth has an `OPENAI_API_KEY`-named credential, but using it only
  moves `openai-responses` from key preflight to the same `api.openai.com`
  network reset.
- Common local proxy ports `7890`, `7891`, `7897`, `1080`, `1087`, `20171`,
  `8080`, and `3128` are closed.
- Non-standard local listeners on `31080`, `31443`, `31055`, `31056`, `19514`,
  and `5345` were also probed as HTTP/SOCKS/HTTPS CONNECT candidates; none
  successfully tunnel `api.openai.com`.
- Direct OpenAI reachability is still unavailable: both resolved IPv4 addresses
  reset connections to `api.openai.com`; HTTP/1.1, HTTP/2, TLS 1.2, TLS 1.3,
  and raw `openssl s_client` probes all fail before TLS completes; no native
  IPv6 route is available.
- `ROBOCLAWS_CODEX_PROVIDER=openai-responses` fails provider-arg construction
  before launch because `OPENAI_API_KEY` is missing.
- `ROBOCLAWS_CODEX_PROVIDER=openai-responses` with the host Codex auth key fails
  the cheap provider smoke with request errors to
  `https://api.openai.com/v1/responses`; no system-provider fallback was used.
- Legacy Kimi/MiMo Codex control profiles were not substitutes for the official
  proof on this host; current repo-local Codex workflows use `codex-env`.
- `ROBOCLAWS_CODEX_PROVIDER=system` is blocked by the work-network guard.
- Resume check at 22:54 CST with the host Codex auth key injected into only the
  subprocess environment still fails before Codex launch: `just
  code::codex-provider-smoke` and the public `just task::run molmo-cleanup codex
  world-labels output_dir=output/molmo/codex-gpt55-nav2-resume-guard-check
  seed=7 generated_mess_count=5` both stop at the `openai-responses`
  `api.openai.com` reachability guard.
- The resume-check task created
  `output/molmo/codex-gpt55-nav2-resume-guard-check/0518_2254/seed-7`, but no
  `run_result.json`, `report.html`, or `map_bundle/map.yaml` exists because the
  official Codex agent was not launched.
- GitHub-side proof audit after pushing the opt-in CI route:
  - Run `26044677029` on `729da81` kept Xvfb alive and got past the previous
    display lifecycle failure, then failed because the live-agent Docker
    workspace was mounted from a relative path.
  - Run `26045247897` on `fa6042c` got past Xvfb, started the MCP server,
    added the Codex MCP server, connected to MCP, and failed only after Codex
    tried `https://api.openai.com/v1/responses` with the repository
    `OPENAI_API_KEY` secret.
  - Run `26046576875` on `f42420e` validated the latest CI preflight: lint/mock
    passed, `api.openai.com` was reachable, the Docker-backed Codex provider
    smoke failed with `401 invalid_api_key`, the Molmo proof step was skipped,
    and no `report-molmo-official-codex-gpt55-nav2` artifact was uploaded.
  - Resume audit on 2026-05-18T18:23:06Z through 2026-05-18T18:25:41Z
    polled `gh secret list --repo MiaoDX/roboclaws` six times. The
    `OPENAI_API_KEY` repository secret remained timestamped
    `2026-05-18T15:29:18Z`, the known rejected credential, so no redispatch was
    attempted.
  - Follow-up bounded watcher on 2026-05-18T19:52:52Z through
    2026-05-18T19:57:30Z polled the same secret ten more times. The
    `OPENAI_API_KEY` repository secret still remained timestamped
    `2026-05-18T15:29:18Z`, and the no-redispatch decision was recorded on
    issue #111:
    https://github.com/MiaoDX/roboclaws/issues/111#issuecomment-4481522784
  - Later bounded watchers on 2026-05-18T20:04:08Z through
    2026-05-18T20:09:46Z and on 2026-05-18T20:11:48Z through
    2026-05-18T20:21:31Z polled the same secret 32 more times total. Every
    poll still returned `OPENAI_API_KEY=2026-05-18T15:29:18Z`, so no official
    proof redispatch was attempted. The issue tracker evidence is recorded at
    https://github.com/MiaoDX/roboclaws/issues/111#issuecomment-4481637122 and
    https://github.com/MiaoDX/roboclaws/issues/111#issuecomment-4481757333
  - Fresh resume check on 2026-05-18T21:03:14Z (2026-05-19 local time) still
    showed `OPENAI_API_KEY=2026-05-18T15:29:18Z`. Latest normal push/PR CI is
    green on branch head `3d60857`, PR #112 is still draft, and no official
    proof redispatch was attempted because the secret timestamp is unchanged.
  - Bounded watcher on 2026-05-18T21:12:22Z through 2026-05-18T21:16:58Z
    polled the same secret ten more times. Every poll still returned
    `OPENAI_API_KEY=2026-05-18T15:29:18Z`, so no official proof redispatch was
    attempted.
  - Longer bounded watcher on 2026-05-18T21:33:19Z through
    2026-05-18T21:48:12Z polled the same secret 30 more times. Every poll still
    returned `OPENAI_API_KEY=2026-05-18T15:29:18Z`, so no official proof
    redispatch was attempted.
  - Local official-proof route recheck after that watcher still reported
    `network: work`, `OPENAI_API_KEY_set=false`, no `HTTPS_PROXY` /
    `ALL_PROXY`, and a direct `curl -I --max-time 10
    https://api.openai.com/v1/responses` connection reset. This host still
    cannot run the official OpenAI-backed Codex proof directly.
  - Follow-up bounded watcher on 2026-05-18T22:26:24Z through
    2026-05-18T22:31:01Z polled the same secret ten more times. Every poll still
    returned `OPENAI_API_KEY=2026-05-18T15:29:18Z`, so no official proof
    redispatch was attempted.
  - Additional delayed guard checks from 2026-05-18T22:38:08Z through
    2026-05-18T22:57:04Z still returned
    `OPENAI_API_KEY=2026-05-18T15:29:18Z`. No official proof redispatch was
    attempted.
  - Follow-up delayed guard checks from 2026-05-18T23:00:13Z through
    2026-05-18T23:22:24Z still returned
    `OPENAI_API_KEY=2026-05-18T15:29:18Z`. No official proof redispatch was
    attempted.
  - Continued delayed guard checks from 2026-05-18T23:25:56Z through
    2026-05-18T23:42:16Z still returned
    `OPENAI_API_KEY=2026-05-18T15:29:18Z`. No official proof redispatch was
    attempted.
  - Follow-up delayed guard checks from 2026-05-18T23:45:50Z through
    2026-05-19T00:02:09Z still returned
    `OPENAI_API_KEY=2026-05-18T15:29:18Z`. No official proof redispatch was
    attempted.
  - Post-midnight delayed guard checks from 2026-05-19T00:05:37Z through
    2026-05-19T00:16:26Z still returned
    `OPENAI_API_KEY=2026-05-18T15:29:18Z`. No official proof redispatch was
    attempted.
  - Continued post-midnight guard checks from 2026-05-19T00:20:16Z through
    2026-05-19T00:31:36Z still returned
    `OPENAI_API_KEY=2026-05-18T15:29:18Z`. No official proof redispatch was
    attempted.
  - Fresh guard check at 2026-05-19T01:48:48Z and bounded watcher from
    2026-05-19T01:50:56Z through 2026-05-19T02:00:02Z still returned
    `OPENAI_API_KEY=2026-05-18T15:29:18Z` on all 10 watcher polls. No official
    proof redispatch was attempted.
  - Issue #111 was refreshed at 2026-05-19T02:02:22Z so its body now points at
    branch head `3a3b209`, latest opt-in preflight run `26046576875`, the local
    work-network/OpenAI reset blocker, and the exact artifact/checker
    acceptance criteria.
  - Completion-audit refresh at 2026-05-19T02:03Z reconfirmed the deterministic
    Nav2 report artifact still has `seed-7/run_result.json`,
    `seed-7/report.html`, `seed-7/map_bundle/map.yaml`, report `Nav2 Map
    Bundle` rendering, restored `5/5`, sweep `100%`, and a passing
    `--require-real-robot-alignment` checker run.
  - Repository-wide artifact-name audit: older failed runs `26045247897`,
    `26044677029`, `26044165616`, `26043711467`, and `26043342849` do have
    artifacts named `report-molmo-official-codex-gpt55-nav2`, but none contains
    the required `seed-7/run_result.json`, `seed-7/report.html`, or
    `seed-7/map_bundle/map.yaml`; each is only a failed-run bundle with
    `live_status.json` and partial logs/artifacts.
  - Current CI-side blocker: the `OPENAI_API_KEY` repository secret is present
    but is not a valid key for the official OpenAI Responses API. This
    machine's host Codex auth is configured for
    `https://api-router.evad.mioffice.cn/v1`, so that credential is not a valid
    substitute for `api.openai.com`.
- Public recipe preflight also fails before Codex launch:
  - `ROBOCLAWS_CODEX_PROVIDER=system ROBOCLAWS_CODEX_MODEL=gpt-5.5
    ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS=1 just task::run
    molmo-cleanup codex world-labels
    output_dir=output/molmo/codex-gpt55-nav2-guard-check seed=7
    generated_mess_count=5` exits `1` at the work-network guard.
  - `ROBOCLAWS_CODEX_PROVIDER=openai-responses ROBOCLAWS_CODEX_MODEL=gpt-5.5
    just task::run molmo-cleanup codex world-labels
    output_dir=output/molmo/codex-gpt55-nav2-openai-key-check seed=7
    generated_mess_count=5` exits `2` because `OPENAI_API_KEY` is missing.

Historical Codex output audit:

- `output/molmo/codex-camera-raw/0518_0956/seed-7` is a system Codex
  `--model gpt-5.5` run and finished, but restored `0/10` and has no Nav2 map
  bundle.
- `output/molmo/codex-camera-raw/0518_1357/seed-7` is a system Codex
  `--model gpt-5.5` run, but live status is failed/checker exit `1`, exact
  restoration was `5/10`, and it has no Nav2 map bundle.
- `output/molmo/codex-report/0512_2307/seed-7` passed the older cleanup checker
  with `8/10` exact restoration and sweep coverage `1.0`, but its recorded
  Codex command does not explicitly pin `gpt-5.5` and the run predates Nav2 map
  bundle snapshots.
- No existing `output/molmo/codex*/**/run_result.json` currently satisfies all
  three remaining evidence requirements: explicit official Codex GPT-5.5,
  no-clear-regression cleanup result, and Nav2 map bundle report artifacts.

## Next Action

Run from a non-work network or with an official OpenAI API key on a network
where `api.openai.com` is reachable:

```bash
ROBOCLAWS_CODEX_PROVIDER=openai-responses \
ROBOCLAWS_CODEX_MODEL=gpt-5.5 \
just task::run molmo-cleanup codex world-labels \
  output_dir=output/molmo/codex-gpt55-nav2-report \
  seed=7 \
  generated_mess_count=5
```

If local OpenAI access remains blocked but GitHub Actions has the official
`OPENAI_API_KEY` repository secret, use the dedicated opt-in CI proof:

```bash
gh workflow run ci.yml \
  -f molmo_live=false \
  -f molmo_official_codex=true
```

Current CI-side blocker: replace the GitHub `OPENAI_API_KEY` repository secret
with a valid official OpenAI API key for `https://api.openai.com/v1/responses`,
then re-dispatch the opt-in proof. The preflight step should pass before the
Molmo backend starts. Do not redispatch before `gh secret list --repo
MiaoDX/roboclaws` shows `OPENAI_API_KEY` updated after
`2026-05-18T15:29:18Z`. Do not mark the goal complete until that artifact
exists and passes the checker. The human-owned credential unblock is tracked in
GitHub issue #111: https://github.com/MiaoDX/roboclaws/issues/111

Review surface: draft PR #112 remains blocked until the official Codex GPT-5.5
artifact exists and passes the checker:
https://github.com/MiaoDX/roboclaws/pull/112

Then validate the resulting report with `--require-real-robot-alignment`. Do not
mark the active goal complete until that official Codex GPT-5.5 cleanup report
exists and has no clear regression.
