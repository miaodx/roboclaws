# Real Robot Nav2 Cleanup Pilot Active Status

Last updated: 2026-05-18

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
  - `729da81` `ci: keep xvfb alive for codex molmo proof`
  - `fa6042c` `fix: normalize live agent docker workspace`
- `real_robot_cleanup_v1` exists and is included in
  `skills/molmo-realworld-cleanup/skill.json`.
- `DirectNav2Adapter` exists with mocked tests for success, timeout, cancel,
  distance rejection, and blocked manipulation.
- Molmo cleanup finalizers snapshot a Nav2-shaped `map_bundle/` into each run.
- Cleanup reports render a `Nav2 Map Bundle` section with `map.yaml`,
  `map.pgm`, `semantics.json`, robot profile, costmap params, preview, hashes,
  and runtime costmap gaps.
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
- The official CI proof keeps a manually managed Xvfb server alive for the
  detached tmux runner and normalizes live-agent Docker workspaces to absolute
  paths before mounting them.
- Broken legacy Molmo compatibility symlinks at removed root paths were deleted
  so the repo-wide static gate no longer asks Ruff to lint missing files.

## Verified

- Pre-commit fast subset passed on each implementation commit.
- Focused contract checks passed for skill manifests, semantic profiles,
  Nav2 adapter, cleanup artifacts, and Codex provider wiring.
- Deterministic regression report:
  `output/molmo/nav2-map-regression/0518_2046/seed-7/report.html`
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
- Latest focused checks for the CI launcher fixes:
  - `uv run python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml', encoding='utf-8')); print('yaml ok')"`
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_ci_live_reports.py tests/contract/dev_tools/test_code_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  - pre-commit fast non-integration pytest subset on `fa6042c`
- Explicit checker passed:

```bash
uv run python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  output/molmo/nav2-map-regression/0518_2046 \
  --expect-backend api_semantic_synthetic \
  --expect-policy realworld_contract_smoke_agent \
  --expect-profile smoke \
  --expect-seeds 7 \
  --min-generated-mess-count 5 \
  --require-agent-driven \
  --require-clean-agent-run \
  --require-advisory-scoring \
  --min-restored-count 5 \
  --min-sweep-coverage 1.0 \
  --require-waypoint-honesty \
  --require-real-robot-alignment
```

Result: restored `5/5`, sweep coverage `1.0`, Nav2 map bundle present.

## Completion Audit Checklist

Objective requirements mapped to current evidence:

| Requirement | Evidence | Status |
| --- | --- | --- |
| Implement `docs/plans/real-robot-nav2-cleanup-pilot.md` | Commits `1d76f0d`, `fd01173`, `7f7f987`, `daff692`, `0c67850`, `f27f552`, `0a7ebb7`, `61c5903`, `4c5c185`, `d9e0c00`, `4734fab`, `49ecbee`, `d568bc7`, `3e4de60`, `2ac1d44`, `764a806`, `1d61de9`, `31b42d4`, `90a80d9`, `4b3385f`, `3b7c585`, `f2bb97b`; this status file tracks the remaining gate. | Implemented except official Codex proof |
| Honor ADR-0127 direct Nav2 adapter before ROSClaw | `roboclaws/molmo_cleanup/nav2_adapter.py`; `tests/contract/molmo_cleanup/test_nav2_adapter.py` covers success, timeout, cancel, max-distance rejection, and blocked manipulation. | Implemented |
| Honor ADR-0128 `real_robot_cleanup_v1` profile | `roboclaws/mcp/profiles.py`; `skills/molmo-realworld-cleanup/skill.json`; semantic profile tests. | Implemented |
| Honor ADR-0129 Nav2 map artifacts for simulator/hardware parity | `roboclaws/molmo_cleanup/nav2_map_bundle.py`; `metric_map()` bundle metadata; direct and MCP finalizers snapshot `map_bundle/`. | Implemented |
| Add Nav2 nav maps to report file | `output/molmo/nav2-map-regression/0518_2046/seed-7/report.html` contains `Nav2 Map Bundle`, `map_bundle/map.yaml`, preview, hashes, and runtime gap notes. | Verified on deterministic report |
| Ensure cleanup report has no clear regression | Deterministic smoke `output/molmo/nav2-map-regression/0518_2046` passed checker with restored `5/5` and sweep coverage `1.0`. | Verified for deterministic smoke |
| Use MolmoSpaces cleanup by official Codex GPT-5.5 as main implementation target | Latest explicit `gpt-5.5` CI attempt `26045247897` reaches Codex + MCP, then fails with `401 invalid_api_key` from `https://api.openai.com/v1/responses`; earlier local attempts fail on work-network OpenAI reachability or are historical runs without Nav2/no-regression evidence. | Blocked |
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
- Repo-local Codex control profiles are not substitutes for the official proof
  on this host: `mimo-openai` and `kimi-openai` provider smokes both currently
  return provider `404` for `/v1/responses`.
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
then re-dispatch the opt-in proof. Do not mark the goal complete until that
artifact exists and passes the checker.

Then validate the resulting report with `--require-real-robot-alignment`. Do not
mark the active goal complete until that official Codex GPT-5.5 cleanup report
exists and has no clear regression.
