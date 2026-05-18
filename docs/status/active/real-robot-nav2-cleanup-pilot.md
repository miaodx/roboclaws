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
- `real_robot_cleanup_v1` exists and is included in
  `skills/molmo-realworld-cleanup/skill.json`.
- `DirectNav2Adapter` exists with mocked tests for success, timeout, cancel,
  distance rejection, and blocked manipulation.
- Molmo cleanup finalizers snapshot a Nav2-shaped `map_bundle/` into each run.
- Cleanup reports render a `Nav2 Map Bundle` section with `map.yaml`,
  `map.pgm`, `semantics.json`, robot profile, costmap params, preview, hashes,
  and runtime costmap gaps.

## Verified

- Pre-commit fast subset passed on each implementation commit.
- Focused contract checks passed for skill manifests, semantic profiles,
  Nav2 adapter, cleanup artifacts, and Codex provider wiring.
- Deterministic regression report:
  `output/molmo/nav2-map-regression/0518_2046/seed-7/report.html`
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
| Implement `docs/plans/real-robot-nav2-cleanup-pilot.md` | Commits `1d76f0d`, `fd01173`, `7f7f987`, `daff692`, `0c67850`, `f27f552`, `0a7ebb7`, `61c5903`, `4c5c185`; this status file tracks the remaining gate. | Implemented except official Codex proof |
| Honor ADR-0127 direct Nav2 adapter before ROSClaw | `roboclaws/molmo_cleanup/nav2_adapter.py`; `tests/contract/molmo_cleanup/test_nav2_adapter.py` covers success, timeout, cancel, max-distance rejection, and blocked manipulation. | Implemented |
| Honor ADR-0128 `real_robot_cleanup_v1` profile | `roboclaws/mcp/profiles.py`; `skills/molmo-realworld-cleanup/skill.json`; semantic profile tests. | Implemented |
| Honor ADR-0129 Nav2 map artifacts for simulator/hardware parity | `roboclaws/molmo_cleanup/nav2_map_bundle.py`; `metric_map()` bundle metadata; direct and MCP finalizers snapshot `map_bundle/`. | Implemented |
| Add Nav2 nav maps to report file | `output/molmo/nav2-map-regression/0518_2046/seed-7/report.html` contains `Nav2 Map Bundle`, `map_bundle/map.yaml`, preview, hashes, and runtime gap notes. | Verified on deterministic report |
| Ensure cleanup report has no clear regression | Deterministic smoke `output/molmo/nav2-map-regression/0518_2046` passed checker with restored `5/5` and sweep coverage `1.0`. | Verified for deterministic smoke |
| Use MolmoSpaces cleanup by official Codex GPT-5.5 as main implementation target | Latest explicit `gpt-5.5` attempts either fail before agent cleanup (`codex-gpt55-nav2-report-postfix/0518_2055`) or are historical runs without Nav2/no-regression evidence. | Blocked |
| Commit in scoped chunks | Current branch contains small implementation, fallback, guard, and blocker/audit commits. | Satisfied |

Completion rule: do not mark the goal complete until an official Codex GPT-5.5
Molmo cleanup run has a `run_result.json` and `report.html` that pass the
real-robot-alignment checker without a clear cleanup regression.

## Blocked Requirement

The official system-provider Codex GPT-5.5 Molmo cleanup run is not complete on
this work network. Direct `https://api.openai.com/v1/responses` access is reset,
and no usable local HTTP/SOCKS proxy was found.

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
- `ROBOCLAWS_CODEX_PROVIDER=system` is blocked by the work-network guard.
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

Then validate the resulting report with `--require-real-robot-alignment`. Do not
mark the active goal complete until that official Codex GPT-5.5 cleanup report
exists and has no clear regression.
