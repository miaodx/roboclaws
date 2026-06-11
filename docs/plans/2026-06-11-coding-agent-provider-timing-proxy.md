---
plan_scope: coding-agent-provider-timing-proxy
status: IMPLEMENTED
created: 2026-06-11
last_reviewed: 2026-06-11
source:
  - coding-agent cleanup timing comparison
  - report-performance-analysis backfill
  - intuitive-reduce-entropy candidate 1
related_context:
  - docs/plans/molmo-cleanup-codex-harness-speedup.md
  - roboclaws/reports/live_performance.py
  - scripts/molmo_cleanup/run_live_codex_cleanup.py
  - scripts/molmo_cleanup/run_live_claude_cleanup.py
  - scripts/dev/coding_agent_env.sh
  - scripts/dev/coding_agent_docker.sh
---

# Coding-Agent Provider Timing Proxy

## Goal

Add an opt-in, repo-local, redacted timing proxy for live coding-agent provider
traffic so Codex CLI and Claude Code cleanup reports can expose observed model
HTTP duration without relying on provider/router internals or prompt logging.

The first target is the current comparison gap: Codex and Claude Code runs can
show wall time, MCP timing, and whatever usage their event logs expose, but they
often lack model API duration. The proxy should fill that timing gap with a
separate provider-request artifact instead of inventing per-call timing from
agent event logs.

## Accepted Direction

Use a custom narrow proxy, not mitmproxy, as the committed benchmark path.

Rationale:

- `mitmproxy` is strong for interactive inspection, but its default shape is
  traffic debugging and body inspection.
- The benchmark path should be privacy-safe by construction: no persisted
  prompts, response text, authorization headers, full headers, tool payloads, or
  model output.
- A repo-local proxy can write exactly the artifact contract the report
  extractor needs.
- Unit tests can exercise the proxy against a fake upstream without certificate
  setup, browser trust stores, or operator state.
- The proxy should be usable by Codex and Claude Code through existing base URL
  environment routing.

Mitmproxy remains acceptable as an ad-hoc local debugging tool, but it is not
the planned default or report artifact producer.

## Review Route

Reviewed on 2026-06-11 through `intuitive-flow` inline autoplan precheck. This
checkout does not expose a noninteractive `gstack-autoplan` executable, so the
plan keeps the already accepted direction and grill decisions as the execution
contract.

Scope changes from precheck: none. The first implementation remains opt-in,
privacy-safe provider HTTP timing for Codex CLI and Claude Code live cleanup
runs, with aggregate report extraction and explicit local-live validation gates.

## Implementation Status

Implemented on 2026-06-11 through `intuitive-flow`.

Shipped shape:

- `ROBOCLAWS_PROVIDER_TIMING_PROXY=1` starts a loopback-only provider timing
  proxy before Codex CLI or Claude Code live cleanup runs.
- Codex routes the resolved provider `base_url` through the proxy, keeps
  `wire_api=responses`, disables Responses WebSocket transport only in proxy
  mode for HTTP observability, and records that in `live_timing.json`.
- Claude Code routes `ANTHROPIC_BASE_URL` through the same proxy contract.
- The proxy writes sanitized `provider_request_metrics.jsonl` rows with scalar
  timing, byte counts, status codes, and safe upstream request ids only.
- Report extraction reads the provider artifact, exposes aggregate provider
  HTTP timing separately from `observed_model_api_s`, and adds explicit
  limitations for aggregate-only transport timing and non-compute timing.

Validation evidence:

- Deterministic tests:
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/reports/test_live_performance.py tests/unit/agents/test_provider_timing_proxy.py tests/unit/molmo_cleanup/test_ci_live_reports.py`
  passed with 40 tests.
- Integration route tests:
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py`
  passed with 119 tests.
- Lint/format:
  `.venv/bin/ruff check` and `.venv/bin/ruff format --check` passed for the
  touched Python files; `bash -n scripts/dev/coding_agent_docker.sh scripts/dev/coding_agent_env.sh`
  passed for shell wiring.
- Validation Matrix:
  `output/agent-validation-matrix/20260611T131715Z/validation_matrix.json`
  recorded four required passing gates: route-trace contract tests, cleanup
  policy/semantic-loop tests, direct-runner household product gate, and Codex
  cleanup world-oracle gate.
- Codex proxy live gate:
  `output/provider-timing-proxy/codex-proxy-rerun/0611_2055/seed-7`
  finished with exit 0, cleanup success, 14/14 sweep coverage, 5/5 semantic
  acceptability, 68 provider metric rows, and 361.167s aggregate provider HTTP
  duration.
- Claude proxy live gate:
  `output/provider-timing-proxy/claude-proxy/0611_2105/seed-7`
  finished with exit 0, cleanup success, 14/14 sweep coverage, 5/5 semantic
  acceptability, 90 provider metric rows, and 401.994s aggregate provider HTTP
  duration.
- Report extraction:
  `scripts/reports/extract_live_report_metrics.py --write-model-call-metrics`
  over both proxy run dirs produced `provider_request_count`,
  `provider_http_duration_s`, `provider_http_time_to_first_byte_s`,
  `provider_http_stream_duration_s`, `provider_http_status_counts`, and
  `provider_http_limitations`.
- Privacy scan:
  both proxy metric files had zero matches for authorization headers,
  key-shaped values, prompt phrases, tool payload phrases, body JSON markers,
  and repo-local `.env` secret values. The only body-related fields were scalar
  byte counts: `request_body_bytes` and `response_body_bytes`.
- Codex overhead check:
  the proxy Codex run above was compared with the same-day no-proxy Codex
  Validation Matrix run
  `output/agent-validation-matrix/20260611T131715Z/gates/codex-cleanup-world-oracle/run/0611_2118/seed-7`.
  Both reached the same success bar. The proxy run wall time was 480.599s;
  the no-proxy run wall time was 594.426s. This sample shows no material proxy
  overhead, but it remains diagnostic run-to-run evidence rather than a
  statistically stable benchmark.

Follow-up default policy, added 2026-06-11: proxy mode is now default-on for
benchmark-style live coding-agent paths that need comparable performance
evidence, specifically Agent Validation Matrix live Codex/Claude gates and the
CI/live cleanup matrix. Ordinary `just run::surface` Codex/Claude launches
remain opt-in unless their caller sets `ROBOCLAWS_PROVIDER_TIMING_PROXY=1`.
All default-on benchmark paths preserve `ROBOCLAWS_PROVIDER_TIMING_PROXY=0` as
an escape hatch. Persisting body-derived request mappings or claiming
provider-internal compute time still requires a separate decision.

## Grill Batch 1 Decisions

Accepted on 2026-06-11:

- Keep provider HTTP timing as a separate observed transport metric. It may
  explain missing model API duration, but it must not be relabeled as internal
  model compute time.
- Do not parse provider request or response bodies in proxy v1. Runner metadata
  supplies `agent_engine`, `provider_profile`, and configured `model`; the proxy
  only counts body bytes.
- When `ROBOCLAWS_PROVIDER_TIMING_PROXY=1`, proxy startup/config failures fail
  before launching the agent. Opt-in benchmark mode should not silently produce
  another ambiguous run without provider timing.
- Codex proxy mode keeps `wire_api=responses`. If the pinned Codex CLI/provider
  would otherwise use Responses WebSocket transport, proxy mode may disable that
  transport only for the proxy-enabled run so the HTTP proxy observes all
  provider requests. This changes transport selection, not the Responses API.
- The implementation must measure any Codex transport overhead. If disabling
  WebSocket transport is materially slower or incompatible for a provider route,
  record that route as unsupported for proxy timing instead of forcing it into
  the benchmark.
- Keep v1 Docker reachability scoped to the supported host-network runtime. Bind
  locally by default and fail clearly for unsupported Docker networking rather
  than binding broadly.

## Scope

- Add a small provider timing proxy runtime and CLI.
- Route Codex CLI through the proxy when explicitly enabled.
- Route Claude Code through the proxy when explicitly enabled.
- Emit a sanitized `provider_request_metrics.jsonl` artifact in each run
  directory.
- Extend report-performance extraction to include observed provider HTTP timing
  from that artifact.
- Keep model usage attribution honest:
  - use event-log usage when the agent exposes it;
  - use proxy duration for HTTP timing;
  - do not claim exact token-per-request attribution unless a reliable mapping
    exists.
- Add focused tests for proxy privacy, streaming timing, report extraction, and
  runner environment wiring.

## Non-Goals

- No HTTPS certificate MITM.
- No persisted request body, response body, prompts, model text, tool payloads,
  or authorization headers.
- No attempt to decompose provider/router internals beyond observable HTTP
  boundaries.
- No default-on behavior for live runs until local validation proves the proxy
  is stable.
- No replacement for existing `codex-events.jsonl`, `claude-events.jsonl`,
  `live_timing.json`, or `model_call_metrics.jsonl`.
- No claim that proxy timing is identical to provider-side model compute time;
  it is observed client-to-upstream HTTP duration.

## Artifact Contract

Write one JSON line per upstream provider HTTP request:

```json
{
  "schema": "roboclaws_provider_request_metric_v1",
  "proxy_request_id": "uuid-or-short-id",
  "agent_engine": "codex-cli",
  "provider_profile": "codex-env",
  "method": "POST",
  "path": "/v1/responses",
  "started_at_epoch": 1781180000.123,
  "upstream_headers_received_at_epoch": 1781180001.234,
  "first_response_byte_at_epoch": 1781180001.456,
  "finished_at_epoch": 1781180010.789,
  "duration_s": 10.666,
  "time_to_headers_s": 1.111,
  "time_to_first_byte_s": 1.333,
  "stream_duration_s": 9.333,
  "request_body_bytes": 12345,
  "response_body_bytes": 67890,
  "status_code": 200,
  "streaming": true,
  "provider_request_id": "safe-upstream-request-id-if-present",
  "model": "runner-configured-model",
  "limitations": []
}
```

Privacy contract:

- Never write authorization values.
- Never write full request or response bodies.
- Never write prompt, instructions, tool payload, tool output, model output, or
  compact continuation state.
- Do not parse provider request or response bodies in proxy v1.
- Optionally extract safe provider request IDs from known response headers.

## Runtime Design

Add a minimal pass-through proxy such as:

- `roboclaws/agents/provider_timing_proxy.py`
- `scripts/dev/provider_timing_proxy.py`

Implementation shape:

- Bind locally by default.
- Accept only a configured upstream base URL.
- Forward method, path, query, body, and required headers.
- Strip hop-by-hop headers.
- Preserve streaming behavior by forwarding chunks as they arrive.
- Count bytes while streaming rather than buffering complete responses.
- Write metrics incrementally to `provider_request_metrics.jsonl`.
- Fail closed on missing upstream config or unexpected absolute upstream hosts.
- Receive safe run metadata from the runner instead of deriving metadata from
  provider bodies.

Recommended dependency approach:

- Use an already-present async HTTP/server stack from the dev environment, but
  declare any direct dependency in `pyproject.toml`.
- Prefer `aiohttp` for a small server/client implementation if it keeps the
  dependency set simpler than adding a new web framework.

## Codex Integration

Current route:

```text
Codex CLI
  -> model_providers.<provider>.base_url
  -> provider/router
```

Opt-in timing route:

```text
Codex CLI
  -> model_providers.<provider>.base_url=http://127.0.0.1:<proxy-port>
  -> ROBOCLAWS_TIMING_PROXY_UPSTREAM_BASE_URL=<original provider base_url>
  -> provider/router
```

Required work:

- Add an opt-in flag or environment knob such as
  `ROBOCLAWS_PROVIDER_TIMING_PROXY=1`.
- In the Codex cleanup runner, start the proxy before launching Codex and stop
  it after the agent process exits.
- Preserve the original resolved provider base URL as the proxy upstream. For
  `codex-env`, that starts from `CODEX_BASE_URL`; for `mify`, it starts from the
  selected mify Responses-compatible base URL.
- Keep `model_providers.<provider>.wire_api="responses"`.
- If needed for complete HTTP observability, disable Responses WebSocket
  transport only for the proxy-enabled Codex run. Record the transport setting
  in `live_timing.json`.
- Write proxy metrics into the run directory.
- Record proxy metadata in `live_timing.json`, including enabled/disabled state,
  upstream origin, bind URL, metrics path, and any proxy start/stop failure.
- For Docker-backed Codex, support the default host-network wrapper route only
  in v1. If the proxy is not reachable from the container, fail before launching
  Codex with an explicit unsupported-route error.

## Claude Code Integration

Current route:

```text
Claude Code
  -> ANTHROPIC_BASE_URL
  -> provider/router
```

Opt-in timing route:

```text
Claude Code
  -> ANTHROPIC_BASE_URL=http://127.0.0.1:<proxy-port>
  -> ROBOCLAWS_TIMING_PROXY_UPSTREAM_BASE_URL=<original ANTHROPIC_BASE_URL>
  -> provider/router
```

Required work:

- Reuse the same proxy runtime and artifact schema.
- In the Claude cleanup runner, start the proxy before launching Claude Code and
  stop it after the agent process exits.
- Preserve the original `ANTHROPIC_BASE_URL` as the proxy upstream.
- Keep `ANTHROPIC_API_KEY` unchanged and forwarded only in memory.
- Pass any required proxy upstream/bind environment through
  `scripts/dev/coding_agent_docker.sh`.
- Include Claude provider profile metadata in `live_timing.json` and
  `provider_request_metrics.jsonl`.

## Report Extraction

Extend `roboclaws/reports/live_performance.py`:

- Add `provider_request_metrics.jsonl` to the safe scan list.
- Read `roboclaws_provider_request_metric_v1` rows.
- Add aggregate provider timing to the report-performance timing packet:
  - `provider_request_count`
  - `provider_http_duration_s`
  - `provider_http_time_to_first_byte_s`
  - `provider_http_stream_duration_s`
  - `provider_http_status_counts`
- For model-call rows, attach observed provider HTTP timing as separate
  transport evidence when exact call mapping is unavailable.
- Preserve the current limitation note when only aggregate timing is known.
- Add a limitation such as `provider_http_timing_not_internal_model_compute`.

Extractor policy:

- Proxy timing can fill the missing "model API duration" comparison column as
  observed provider HTTP time.
- It must not overwrite event-log usage.
- It must not imply per-call token attribution for Codex or Claude Code unless
  the run artifact supplies a reliable request mapping.
- It must keep an explicit distinction between `observed_model_api_s` emitted by
  SDK/agent telemetry and `provider_http_duration_s` observed by the proxy.

## Verification

Deterministic gates:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/reports/test_live_performance.py
./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_provider_timing_proxy.py
```

Contract/integration gates:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py
./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py
```

Lint for touched files:

```bash
.venv/bin/ruff check \
  roboclaws/agents/provider_timing_proxy.py \
  roboclaws/reports/live_performance.py \
  scripts/dev/provider_timing_proxy.py \
  scripts/dev/coding_agent_docker.sh \
  scripts/dev/coding_agent_env.sh \
  scripts/molmo_cleanup/run_live_codex_cleanup.py \
  scripts/molmo_cleanup/run_live_claude_cleanup.py \
  tests/unit/agents/test_provider_timing_proxy.py \
  tests/unit/reports/test_live_performance.py \
  tests/unit/molmo_cleanup/test_ci_live_reports.py
```

Product run gates, opt-in and local:

```bash
ROBOCLAWS_PROVIDER_TIMING_PROXY=1 \
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco \
  intent=cleanup agent_engine=codex-cli provider_profile=codex-env \
  evidence_lane=world-oracle-labels seed=7 \
  scenario_setup=relocate-cleanup-related-objects relocation_count=5
```

```bash
ROBOCLAWS_PROVIDER_TIMING_PROXY=1 \
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco \
  intent=cleanup agent_engine=claude-code provider_profile=mimo-anthropic \
  evidence_lane=world-oracle-labels seed=7 \
  scenario_setup=relocate-cleanup-related-objects relocation_count=5
```

Post-run report extraction:

```bash
python scripts/reports/extract_live_report_metrics.py \
  --write-model-call-metrics \
  <codex-run-dir> <claude-run-dir>
```

Codex transport overhead check:

```bash
# Compare otherwise equivalent Codex runs with and without proxy mode /
# WebSocket-transport disablement. The success claim is artifact completeness
# plus no material wall-time regression beyond recent run-to-run variance.
```

Manual acceptance checks:

- Each run directory contains `provider_request_metrics.jsonl`.
- The file contains duration and TTFB fields for provider HTTP requests.
- Privacy scan finds no prompt text, model output, tool payloads, or API keys.
- `report.html` and extracted comparison packets show observed provider HTTP
  timing without removing existing wall/MCP timing.
- Proxy-enabled runs still complete the same cleanup checker gates as matching
  non-proxy runs.

## Preflight Contract

Preflight status: `ACCEPTED`

Task source: plan path plus user request.

Canonical source:

- `docs/plans/2026-06-11-coding-agent-provider-timing-proxy.md`

Route:

- durable `$intuitive-flow`

Goal:

- Implement opt-in redacted provider HTTP timing for Codex CLI and Claude Code
  live cleanup runs, with report extraction and validation-matrix-backed proof.

Context package:

- Must read:
  - `docs/plans/2026-06-11-coding-agent-provider-timing-proxy.md`
  - `skills/agent-validation-matrix/SKILL.md`
  - `roboclaws/reports/live_performance.py`
  - `scripts/molmo_cleanup/run_live_codex_cleanup.py`
  - `scripts/molmo_cleanup/run_live_claude_cleanup.py`
  - `scripts/dev/coding_agent_env.sh`
  - `scripts/dev/coding_agent_docker.sh`
  - `tests/unit/reports/test_live_performance.py`
  - `tests/unit/molmo_cleanup/test_ci_live_reports.py`
  - `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- Useful evidence:
  - `output/report-performance-analysis/0611-gpt-cleanup-backfill/metrics-with-rerun2.json`
  - recent Codex/SDK cleanup run dirs used for comparison
- Do not read unless needed:
  - historical AI2-THOR/direct-VLM plans
  - unrelated `.planning/phases/*`
  - large raw live logs outside the selected comparison runs

Definition of Done:

- SUCCESS only if:
  - Codex and Claude Code both support `ROBOCLAWS_PROVIDER_TIMING_PROXY=1`.
  - Proxy streams responses without full response buffering.
  - `provider_request_metrics.jsonl` is written and privacy-safe.
  - Report metrics expose provider HTTP timing separately from
    `observed_model_api_s`.
  - Codex remains `wire_api=responses`; any WebSocket transport change is
    recorded and overhead-checked.
  - Agent Validation Matrix evidence is produced.
  - Required deterministic, integration, and local live gates pass.
- BLOCKED_NEEDS_DECISION if:
  - proxy should become default-on;
  - proxy must parse request/response bodies;
  - exact per-call token mapping becomes required.
- BLOCKED_NEEDS_LOCAL_VALIDATION if:
  - code/tests pass but provider-backed Docker/MuJoCo Codex or Claude Code
    cleanup runs cannot be executed locally.
- INTERMEDIATE_ONLY if explicitly approved:
  - deterministic implementation lands without live provider proof.
- Must not regress:
  - existing no-proxy Codex/Claude cleanup routes;
  - `model_call_metrics.jsonl`;
  - report privacy scan;
  - coding-agent Docker isolation and provider env routing.

Validation matrix gates:

```bash
just agent::harness agent-validation recommend \
  plan=docs/plans/2026-06-11-coding-agent-provider-timing-proxy.md \
  budget=focused

just agent::harness agent-validation execute \
  plan=docs/plans/2026-06-11-coding-agent-provider-timing-proxy.md \
  budget=focused
```

Required deterministic gates:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/reports/test_live_performance.py \
  tests/unit/agents/test_provider_timing_proxy.py \
  tests/unit/molmo_cleanup/test_ci_live_reports.py

.venv/bin/ruff check <touched files>
```

Required integration gates:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Required product run gates:

```bash
ROBOCLAWS_PROVIDER_TIMING_PROXY=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  intent=cleanup agent_engine=codex-cli provider_profile=codex-env \
  evidence_lane=world-oracle-labels seed=7 \
  scenario_setup=relocate-cleanup-related-objects relocation_count=5

ROBOCLAWS_PROVIDER_TIMING_PROXY=1 just run::surface \
  surface=household-world world=molmospaces/val_0 backend=mujoco \
  intent=cleanup agent_engine=claude-code provider_profile=mimo-anthropic \
  evidence_lane=world-oracle-labels seed=7 \
  scenario_setup=relocate-cleanup-related-objects relocation_count=5
```

Required local/live/manual gates:

- Real provider keys, Docker, and MuJoCo runtime are required.
- Extract report metrics for both live run dirs.
- Verify no prompt, API key, tool payload, or model output leakage in proxy
  metrics.
- Compare proxy vs no-proxy Codex timing for WebSocket/transport overhead.

Optional exploratory gates:

- Run a `mitmproxy` or similar spike only if Codex WebSocket transport
  disablement materially changes performance.

Execution surface:

- Main session: supervise implementation, Validation Matrix output, and final
  complete/blocked judgment.
- Worker: none required.
- Worker-local goal: none.

## Acceptance Criteria

SUCCESS only if:

- Codex and Claude Code both support opt-in provider timing through the same
  artifact schema.
- The proxy forwards streaming responses without buffering the full provider
  response.
- Provider HTTP duration appears in report-performance metrics.
- Missing Codex or Claude Code event-log model duration is represented as
  observed proxy timing with clear limitations.
- Codex proxy mode still uses the Responses API; any WebSocket disablement is
  limited to transport observability and is measured for overhead.
- Privacy tests prove sensitive request/response material is not persisted.
- Focused deterministic tests and the local product gates above pass.

BLOCKED_NEEDS_LOCAL_VALIDATION if:

- Deterministic tests pass but provider-backed Codex/Claude Code cleanup runs
  cannot be executed in the current environment.

BLOCKED_NEEDS_DECISION if:

- We need the proxy to become default-on rather than opt-in.
- We decide to record more than safe scalar request metadata.
- Provider-specific request mapping becomes required for exact per-call token
  attribution.

## Implementation Slices

1. Artifact and extractor foundation
   - Add provider metric schema constants and parser.
   - Add report aggregate fields and privacy scan coverage.
   - Add unit tests with synthetic `provider_request_metrics.jsonl`.

2. Proxy runtime
   - Implement pass-through streaming proxy.
   - Add fake-upstream tests for normal, streaming, upstream error, and privacy
     cases.
   - Do not parse request or response bodies beyond byte counts.

3. Codex runner wiring
   - Start/stop proxy when opt-in env is set.
   - Route the resolved Codex provider base URL through proxy while keeping
     `wire_api=responses`.
   - Make any WebSocket transport disablement opt-in to proxy mode and record it
     in timing metadata.
   - Persist proxy metadata and metrics.

4. Claude Code runner wiring
   - Start/stop proxy when opt-in env is set.
   - Route `ANTHROPIC_BASE_URL` through proxy.
   - Update Docker env passthrough as needed.

5. Local live validation and comparison
   - Run one Codex cleanup and one Claude Code cleanup with proxy enabled.
   - Extract metrics.
   - Compare against recent no-proxy runs for overhead and artifact completeness.

## Expected Performance Impact

The proxy adds one local hop and lightweight metric writing. Expected overhead
should be small relative to model latency, especially for long streaming coding
agent turns. The implementation still needs measurement:

- compare proxy vs no-proxy wall time on at least one Codex and one Claude Code
  run;
- inspect `provider_http_duration_s` vs agent wall time;
- flag material overhead if proxy-enabled wall time regresses by more than the
  natural run-to-run variance seen in recent cleanup reruns.

## To Execute

```text
/goal execute docs/plans/2026-06-11-coding-agent-provider-timing-proxy.md with intuitive-flow
```
