# Real Robot Nav2 Cleanup Pilot Active Status

Last updated: 2026-05-18

## Implemented

- Plan and ADR-backed implementation landed in small commits:
  - `1d76f0d` `feat: snapshot nav2 map bundles in cleanup reports`
  - `fd01173` `feat: add real robot cleanup profile`
  - `7f7f987` `fix: allow codex responses websocket fallback`
  - `daff692` `fix: add openai codex http provider fallback`
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

The official OpenAI API fallback is wired but cannot run on this machine yet:

- Command profile: `ROBOCLAWS_CODEX_PROVIDER=openai-responses`,
  `ROBOCLAWS_CODEX_MODEL=gpt-5.5`
- Status: failed before launch
- Error: `openai-responses requires OPENAI_API_KEY`

Latest unblock/audit check on 2026-05-18:

- `just dev::network-status` still reports `network: work`.
- `OPENAI_API_KEY`, `HTTP_PROXY`, `HTTPS_PROXY`, and `ALL_PROXY` are unset after
  loading `.env`.
- Common local proxy ports `7890`, `7891`, `7897`, `1080`, `1087`, `20171`,
  `8080`, and `3128` are closed.
- Direct OpenAI reachability is still unavailable: IPv4 resets connections to
  `api.openai.com`; IPv6 does not resolve.
- `ROBOCLAWS_CODEX_PROVIDER=openai-responses` fails provider-arg construction
  before launch because `OPENAI_API_KEY` is missing.
- `ROBOCLAWS_CODEX_PROVIDER=system` is blocked by the work-network guard.

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
