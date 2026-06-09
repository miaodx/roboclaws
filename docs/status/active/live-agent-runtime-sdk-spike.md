# Live Agent Runtime SDK Spike Capsule

Canonical source: `docs/plans/live-agent-runtime-sdk-spike.md`

Current slice: Observability V1 for the private `openai-agents-live` route.

Status: completed on 2026-06-09.

Result:

- `live_timing.json` now contains `timeline.schema == "live_agent_timeline_v1"`.
- The timeline records semantic identifiers: `surface`, `intent`,
  `task_name`, `task_intent_mode`, `runtime`, `provider_profile`, `model`, and
  `evidence_lane`.
- The OpenAI Agents SDK route writes sanitized span artifacts:
  `openai-agents-spans.jsonl`.
- Span artifacts keep trace/span IDs, timing, span types, model/usage, MCP tool
  metadata, and errors. They do not persist raw prompts, model text, function
  inputs/outputs, credentials, or private evaluator truth.
- `LiveAgentResult` artifact discovery now includes OpenAI Agents span files.
- The lower private `just molmo::cleanup` direct route now synthesizes the
  default goal contract when no explicit contract path is supplied.
- `openai-agents-live` remains private/non-default.
- `done`/`run_result.json` remains the only cleanup success signal.

Live evidence:

- `world-public-labels` passed:
  `output/household/household-cleanup/openai-agents-observability-v1-world-public/0609_2119/seed-7/`
- `camera-grounded-labels` passed:
  `output/household/household-cleanup/openai-agents-observability-v1-camera-grounded/0609_2140/seed-7/`
- `camera-raw-fpv` produced the V1 timeline and sanitized spans, but failed
  before checker success:
  `output/household/household-cleanup/openai-agents-observability-v1-raw-fpv/0609_2202/seed-7/`

Raw-FPV failure classification:

- The run stopped after one continuation attempt with a provider-wrapped
  context-window failure, after two grounded cleanup chains and repeated
  unresolved visual candidates.
- The SDK exception classifier now has a regression test that classifies this
  wording as `provider_context_failure` before treating the HTTP 502 wrapper as
  a transient upstream outage.

Verification:

- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py -q`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
- `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py roboclaws/agents/live_runtime.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py tests/contract/dev_tools/test_task_agent_just_recipes.py`

No-touch scope preserved:

- Do not promote `openai-agents-live` to a public/default route.
- Do not change MCP cleanup success semantics.
- Do not replace or remove existing `codex-live` / `claude-live` behavior.
- Do not write credentials, raw full prompts, or private evaluator truth to
  observability artifacts.

Parked work:

- Anthropic Claude Agent SDK spike.
- Pi SDK MCP adapter prototype.
- Public/default route promotion for `openai-agents-live`.
- Raw-FPV strategy/context optimization, if maintainers want that lane to pass
  cleanup gates rather than only produce classified observability evidence.
