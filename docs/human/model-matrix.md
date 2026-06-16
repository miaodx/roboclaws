# Model Matrix — declared vs. vendor-spec

Canonical reference for every current model we advertise to the OpenClaw
Gateway via `scripts/openclaw/openclaw-bootstrap.sh`. Update this file whenever
the bootstrap provider JSON changes; CI does not cross-check the numbers
against vendor docs, so this is the audit trail. Historical rows are kept only
when they explain an incident or benchmark artifact and must be labeled as such.

Coding-agent provider/model route metadata is centralized in
`roboclaws/agents/provider_registry.py`; live route health verdicts are recorded
in `docs/human/model-route-verdicts.yaml`. This page keeps the human narrative
for context-window, endpoint, and incident rationale.

Why this file exists: on 2026-04-23 a MiMo chat run crashed because
`contextWindow: 32768` was declared for `mimo-v2-omni` while the vendor
publishes 256K. The Gateway's memory-flush threshold is
`contextWindow - 24000`, so a wrong number turns a headroom cushion into
an on-turn-one trigger. See the retro
in `docs/retrospectives/` for the full incident write-up.

Last full audit: 2026-04-23 (bootstrap `fd2b878`).
MiMo v2.5 migration audit: 2026-05-30.

## Gateway flush-threshold formula

From the Gateway runtime in the pinned Gateway image
(`ghcr.io/openclaw/openclaw:2026.4.25-beta.11`):

```
effective_flush_threshold = contextWindow - reserveTokensFloor - softThresholdTokens
                          = contextWindow - 20000 - 4000
                          = contextWindow - 24000
```

Defaults (`/app/dist/extensions/memory-core/index.js`):

- `DEFAULT_MEMORY_FLUSH_SOFT_TOKENS = 4000`
- `reserveTokensFloor = 20000`

Once the session crosses that threshold the Gateway injects a
`"Pre-compaction memory flush. … If nothing to store, reply with NO_REPLY."`
user turn. If the model picks a tool named `done` instead of replying
`NO_REPLY`, our `roboclaws__done` MCP tool fires and the chat session
terminates. So **a wrongly-low `contextWindow` is a correctness bug, not a
cosmetic one**.

## Active matrix

| Model id (upstream)               | Gateway namespace      | Declared ctx | Declared out cap | Vendor ctx (source)                              | Flush threshold | Status                                           |
|-----------------------------------|------------------------|--------------|------------------|--------------------------------------------------|-----------------|--------------------------------------------------|
| `kimi/k2p5`                       | `anthropic_kimi/k2p5`  | 262 144      | 32 768           | 256K — Moonshot K2.5 release                     | 238 144         | OK — live-probed end-to-end                      |
| `kimi/k2.6`                       | `anthropic_kimi/k2.6`  | 262 144      | 32 768           | 256K — Moonshot K2.6 release                     | 238 144         | OK — live-probed end-to-end                      |
| `nvidia/nemotron-nano-12b-v2-vl`  | `nvidia/…`             | 131 072      | 4 096            | 128K — NVIDIA NIM model card                     | 107 072         | OK — CI-verified                                 |
| `mimo-v2.5` *(openai)*            | `mimo_openai/…`        | 1 048 576    | 32 768           | 1M — MiMo updates page (V2.5 long-context line)  | 1 024 576       | OK — aligned 2026-04-23                          |
| `mimo-v2.5` *(anthropic)*         | `mimo_anthropic/…`     | 1 048 576    | 32 768           | 1M — MiMo updates page (V2.5 long-context line)  | 1 024 576       | OK — aligned 2026-04-23                          |

## Coding-Agent Route Health

`docs/human/model-route-verdicts.yaml` is the compact machine-readable verdict
table for coding-agent routes. The current MiniMax state is:

- **OpenAI Agents SDK + MiniMax Responses**: works for structured cleanup.
  Local paired runs on 2026-06-12 completed cleanup successfully for both
  `MiniMax-M3` and `MiniMax-M2.7-highspeed` with `score.status=success` and
  `mess_restoration_rate=1.0`. MiniMax M3 is the default MiniMax model now:
  it is the multimodal row with image support, and the single paired cleanup
  comparison did not show a speed win for `MiniMax-M2.7-highspeed`.
- **Codex CLI + MiniMax Responses**: blocked for MCP-driven cleanup today.
  The provider Responses route connects, but MiniMax emits MCP tool calls in
  a flattened name shape such as `mcp__cleanup__metric_map`,
  `mcp__cleanup__ping_tool`, or `cleanup__ping_tool`. Codex's MCP router
  rejects those as `unsupported call`; the expected routed shape is a Codex
  MCP call with server/namespace `cleanup` and unprefixed tool names such as
  `metric_map` or `ping_tool`.
- Upgrading the Docker smoke image from Codex `0.130.0` to `0.139.0` did not
  change this MiniMax MCP routing failure. Treat MiniMax in Codex as an
  explicit re-review route, not a working cleanup route, until either Codex's
  Responses MCP router accepts the flattened provider shape or MiniMax changes
  its tool-call encoding.
- The single paired Agent SDK cleanup run did not show a speed advantage for
  `MiniMax-M2.7-highspeed`: M3 finished in about 262.9 s wall time, while
  M2.7-highspeed finished in about 269.1 s. That is only one run, so use it as
  cautionary evidence, not a benchmark conclusion.

Current default-enabled API sources:

- `codex-env`: default model `gpt-5.5`, the strongest current Codex route.
- `mify`: default model `xiaomi/mimo-v2.5`.
- `mimo-openai-chat` / token plan: default model `mimo-v2.5`.
- `mimo-inside`: default-enabled on-demand route, default model `mimo-1000`.
  It is allowed for benchmark and explicit text-agent experiments, but it is
  not promoted as a product cleanup default until a separate route decision
  proves tool/runtime behavior.
- `minimax`: default model `MiniMax-M3`; `MiniMax-M2.7-highspeed` remains an
  explicit non-default variant.
- `kimi-openai-chat`: default model `kimi-k2.7-code`. Kimi K2.7 Code runs with
  Thinking On for the new code-model behavior. Roboclaws exposes a normalized
  `model_thinking_mode=default|enabled|disabled` switch and maps it to each
  provider wire API instead of assuming one schema fits every model.

Kimi K2.7 Code thinking check, 2026-06-16:

- Official Kimi Code docs say Kimi K2.7 Code launched on 2026-06-12 and the new
  model only takes effect with Thinking On:
  <https://www.kimi.com/code/docs/kimi-code/whats-new.html#kimi-k2-7-code-2026-%E5%B9%B4-6-%E6%9C%88-12-%E6%97%A5>.
- Live OpenAI Chat probes against `https://api.kimi.com/coding/v1` with
  `model=kimi-k2.7-code` all returned HTTP success. Omitting `thinking`,
  sending `thinking={"type":"enabled"}`, and sending
  `thinking={"type":"enabled","keep":"all"}` returned non-empty
  `reasoning_content`. Sending `thinking={"type":"disabled"}` also succeeded
  but returned no `reasoning_content`.
- Interpretation: `thinking=disabled` is a valid diagnostic contrast, not a
  transport error, but it disables the behavior Kimi documents as required for
  K2.7 Code. Default product/probe payloads therefore use Thinking On where the
  route supports it.

MiMo/Kimi Chat thinking checks, 2026-06-16:

- The OpenAI Chat-compatible MiMo token-plan route (`mimo-v2.5`) and MiMo inside
  route (`mimo-1000`) both accepted `thinking={"type":"enabled","keep":"all"}`
  and returned non-empty `reasoning_content`.
- The same routes accepted `thinking={"type":"disabled"}` and returned no
  `reasoning_content`.
- Responses-compatible routes `codex-env`, `mify`, and `minimax` accepted the
  OpenAI Responses `reasoning={"effort":"medium"}` shape.

Thinking / reasoning flags by current route:

| Route | Wire API | Roboclaws default flag | Notes |
| --- | --- | --- | --- |
| `kimi-openai-chat` / `kimi-k2.7-code` | OpenAI Chat | `thinking={"type":"enabled","keep":"all"}` in request body | Required for K2.7 Code behavior. `thinking=disabled` is accepted but disables `reasoning_content`. |
| `codex-env` / `gpt-5.5` | OpenAI Responses | `reasoning={"effort":"medium"}` | Uses the OpenAI Responses reasoning schema, not Kimi's `thinking` body. `model_thinking_mode=disabled` maps to `reasoning={"effort":"none"}`. |
| `minimax` / `MiniMax-M3` | OpenAI Responses | `reasoning={"effort":"medium"}` | M3 is the default MiniMax model. M2.7-highspeed can emit reasoning tokens, so probes keep larger token budgets. |
| `mify` / `xiaomi/mimo-v2.5` | OpenAI Responses | `reasoning={"effort":"medium"}` | Responses gateway accepted the OpenAI reasoning body in 2026-06-16 probes. |
| `mimo-openai-chat` / token plan | OpenAI Chat | `thinking={"type":"enabled","keep":"all"}` | Chat route accepted Kimi-style thinking body in 2026-06-16 probes. |
| `mimo-inside` / `mimo-1000` | OpenAI Chat | `thinking={"type":"enabled","keep":"all"}` | On-demand benchmark/text route; disabled mode removes `reasoning_content` in probes. |
| `mimo-anthropic`, `mify-anthropic`, `kimi-anthropic` | Anthropic-compatible routes | none in Roboclaws launch payloads | OpenClaw bootstrap model catalog marks its older Kimi/MiMo entries with `reasoning:false`; that is Gateway catalog metadata, not the OpenAI Chat `thinking` request field. |

Open-ended thinking A/B:

```bash
ROBOCLAWS_OPENAI_AGENTS_THINKING_MODE=enabled \
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco \
  agent_engine=openai-agents-sdk provider_profile=kimi-openai-chat \
  evidence_lane=world-oracle-labels prompt="find something useful to drink"

ROBOCLAWS_OPENAI_AGENTS_THINKING_MODE=disabled \
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco \
  agent_engine=openai-agents-sdk provider_profile=kimi-openai-chat \
  evidence_lane=world-oracle-labels prompt="find something useful to drink"
```

Compare `run_result.json`, `openai-agents-trace.json`, model-call usage,
reasoning tokens/`reasoning_content` availability, wall time, and open-ended
grader outcome. Keep the same provider profile, world, evidence lane, prompt,
seed, and scenario setup when comparing enabled vs disabled.

## Periodic Model Benchmarks

Dev-provider probes live in the harness recipe layer, not the product provider
registry. They are meant to answer "does this route still connect, through
which wire format, and how fast is sustained output today?"

The broad matrix benchmark covers OpenAI Chat, OpenAI Responses, and Anthropic
Messages wire formats where each provider route has a plausible endpoint:

```bash
set -a && source .env && set +a
just dev::model-matrix-benchmark --iterations 1 --timeout-s 240
```

The default run has two layers:

- `health`: short support/status probe with `max_tokens=512`
- `throughput`: longer generation probe with
  `throughput_max_tokens=2048`, reporting `median_output_tokens_per_s` and
  `median_output_chars_per_s`

For layered speed checks, use these three groups:

- `first-content`: minimal first visible content probe. OpenAI Chat cases use
  streaming and record `median_first_content_s`; Responses and Anthropic cases
  use full-response elapsed time as the visible-output fallback. Its default
  `first_content_max_tokens=256` leaves room for Anthropic-compatible routes
  that may emit hidden thinking tokens before visible text.
- `stream-throughput`: sustained OpenAI Chat streaming decode-rate probe. It
  reports `median_first_content_s`, `median_decode_s`, and
  `median_decode_output_tokens_per_s`, which is the clearest MiMo UltraSpeed
  style TPS measurement.
- `agent-case`: curated public-safe prompts based on recent Codex / OpenAI
  Agents SDK cleanup, camera-grounded, raw route-health, and eval-matrix cases.
  It tests typical Roboclaws agent reasoning/output shape without replaying raw
  provider prompts, private scorer truth, credentials, or full old model text.

Use `--layer health` for a cheap periodic support check, `--layer first-content`
for latency, `--layer throughput` for non-stream broad TPS, `--layer
stream-throughput` for decode-rate TPS, and `--layer agent-case` for realistic
Roboclaws agent-shaped output. Artifacts are written under
`output/dev/model-matrix/<timestamp>/model_matrix_benchmark.json`; they record
configured env-key names, support status, usage token counts when providers
return them, and output previews only. Full model outputs and configured base
URLs are intentionally not persisted.

Recommended periodic run:

```bash
just dev::model-matrix-benchmark --iterations 1 \
  --layer first-content --layer throughput --layer agent-case \
  --timeout-s 240
```

List the curated real-agent cases:

```bash
just dev::model-matrix-benchmark --list-agent-cases
```

For MiMo OpenAI Chat-only speed comparison across the three MiMo provider
groups, use the same matrix benchmark with provider and wire filters:

```bash
just dev::model-matrix-benchmark --provider mimo-token-plan --provider mify --provider mimo-inside --wire openai-chat --layer throughput --iterations 1 --timeout-s 240
```

That MiMo-focused benchmark includes:

- MiMo token plan: `mimo-v2.5`, `mimo-v2.5-pro`
- MiMo mify: `xiaomi/mimo-v2.5`, `xiaomi/mimo-v2.5-pro`
- MiMo inside: `mimo-v2.5`, `mimo-v2.5-pro`, `mimo-1000`

`mimo-1000` is the current default-enabled MiMo inside label for on-demand
benchmark and explicit text-agent use. Xiaomi's 2026-06-08 UltraSpeed note
describes the route as a 1T MiMo V2.5 Pro variant focused on 1000+ TPS
generation: <https://mimo.xiaomi.com/blog/mimo-tilert-1000tps>. Keep it out of
active product cleanup defaults until a separate provider-route decision
promotes it.
Use `--layer stream-throughput` on OpenAI Chat cases when you need a decode-rate
style measurement that excludes first-content latency from the TPS denominator.

The default stream prompt is deliberately moderate. To reproduce the 1k-class
UltraSpeed case, force a long enough completion so the fixed first-content cost
does not dominate the denominator:

```bash
just dev::model-matrix-benchmark \
  --case mimo-inside:mimo-1000:openai-chat \
  --layer stream-throughput \
  --iterations 1 \
  --stream-throughput-max-tokens 8192 \
  --stream-throughput-prompt 'Sustained streaming throughput benchmark. Write exactly 20 numbered paragraphs, each paragraph exactly 180 English words, about household robotics evaluation, semantic maps, model-provider reliability, simulator evidence, route health, and long-running operations. Do not use markdown headings, tables, code blocks, or bullet lists. Continue until all 20 paragraphs are complete.' \
  --timeout-s 240
```

> A flush threshold below ~20 k is effectively "trip on the first `observe`
> turn" because the two prompt images + bootstrap context + SOUL/AGENTS
> files already consume 7-10 k tokens.
>
> `maxTokens` is an output-cap hint, not a context budget. It was 4 096 on
> every MiMo entry (placeholder); live-probed at 2026-04-23 that all three
> MiMo variants accept `max_tokens=32768` (one even accepts 65 536) without
> error. Set to 32 768 to match Kimi — a single tool-call round-trip with a
> long rationale fits comfortably.
>
> Image input note: `mimo-v2.5` was live-probed on 2026-05-28 with both the
> mify OpenAI-compatible route (`xiaomi/mimo-v2.5`, chat and responses) and
> the mify Anthropic-compatible route
> (`https://api.llm.mioffice.cn/anthropic`, `xiaomi/mimo-v2.5`). Both accepted
> a PNG image and described image contents. The native MiMo OpenAI-compatible
> route (`mimo-v2.5`, chat) and native MiMo Anthropic-compatible route
> (`mimo-v2.5`) also accepted image blocks. `mimo-v2.5` is the single supported
> MiMo route and is vision-capable.

## Historical MiMo incident row

The row below is not an active route after the 2026-05-30 v2.5 migration. It is
retained only to explain the 2026-04-23 Gateway flush-threshold incident and
older benchmark/report artifacts. Xiaomi's model-deprecation page maps the old
full-modal id to `mimo-v2.5` and says the old id expires on 2026-06-30.

| Model id (upstream)               | Gateway namespace      | Declared ctx | Declared out cap | Vendor ctx (source)                              | Flush threshold | Status                                           |
|-----------------------------------|------------------------|--------------|------------------|--------------------------------------------------|-----------------|--------------------------------------------------|
| `mimo-v2-omni` *(openai)*         | `mimo_openai/…`        | 262 144      | 32 768           | 256K — MiMo 2026-03-18 release note              | 238 144         | Historical only — replaced by `mimo-v2.5`        |

## Provider endpoints (for live probing)

```
kimi       api=anthropic-messages    baseUrl=https://api.kimi.com/coding/
kimi-stock api=anthropic-messages    baseUrl=(stock plugin; /app/dist/provider-catalog-BCrO6TZn.js)
nvidia     api=openai-completions    baseUrl=https://integrate.api.nvidia.com/v1
mimo       api=openai-completions    baseUrl=https://token-plan-cn.xiaomimimo.com/v1
mimo       api=anthropic-messages    baseUrl=https://token-plan-cn.xiaomimimo.com/anthropic
```

Auth envs:

```
KIMI_API_KEY        — Kimi coding tier
NV_API_KEY          — NVIDIA NIM (NVIDIA_API_KEY also accepted)
MIMO_TP_KEY         — MiMo token-plan (xiaomimimo.com)
```

## Historical MiMo `/v1/models` snapshot (live, 2026-04-23)

Returned ids on `https://token-plan-cn.xiaomimimo.com/v1/models` with
`MIMO_TP_KEY` set during the 2026-04-23 audit:

```
mimo-v2-omni
mimo-v2-pro                ← exists upstream; NOT advertised in our bootstrap
mimo-v2-tts
mimo-v2.5
mimo-v2.5-pro              ← exists upstream; retired 2026-06-04, NOT a route we use
mimo-v2.5-tts
mimo-v2.5-tts-voiceclone
mimo-v2.5-tts-voicedesign
```

The single supported MiMo route is the vision-capable `mimo-v2.5`. Everything
else above is an upstream-catalog id, not an active route: `mimo-v2-pro` ≠
`mimo-v2.5-pro`; do not add new v2-line routes, and do not re-add the text-only
`mimo-v2.5-pro` route (it and its text-bridge foundation were removed 2026-06-04).

## Vendor links (authoritative)

- MiMo — <https://platform.xiaomimimo.com/docs/updates/model>
  (release notes index; `mimo-v2-omni` entry dated 2026-03-18 states
  "Supports up to 256K context length")
- MiMo deprecation — <https://platform.xiaomimimo.com/docs/zh-CN/updates/deprecate>
  (`mimo-v2-omni` maps to `mimo-v2.5` and expires on 2026-06-30)
- Moonshot / Kimi — <https://platform.moonshot.ai/docs/pricing/chat>
  (K2, K2.5, K2.6 pricing + spec pages)
- NVIDIA Nemotron Nano 12B V2 VL — <https://build.nvidia.com/nvidia/nemotron-nano-12b-v2-vl>

The MiMo platform and Kimi platform docs are client-rendered SPAs —
raw-HTML fetches return the React shell, not the rendered content. If you
need to re-verify a value, either open the page in a browser or live-probe
the model with a growing prompt until the provider returns a 400 about
context-length.

## Fix queue

1. ~~**Bootstrap**: align all MiMo models with vendor context-window spec.~~
   Done 2026-04-23. `mimo-v2-omni` → 262 144 (256K, vendor release note);
   `mimo-v2.5` and `mimo-v2.5-pro` (both openai and anthropic blocks) →
   1 048 576 (1M, per the V2.5 long-context line on the MiMo updates
   page). `maxTokens` bumped 4 096 → 32 768 across all MiMo entries after
   a live probe confirmed the upstream accepts it (see above).
2. ~~**Tests**: assert `contextWindow >= 131072` for every advertised model.~~
   Done 2026-04-23: `tests/contract/openclaw/test_openclaw_bootstrap.py::`
   `test_advertised_context_windows_clear_flush_headroom`. A regex over
   the raw bootstrap pulls every `"contextWindow":N` literal, so new
   provider branches are covered without teaching
   `_extract_provider_entry_for` another shape.
3. **Pre-merge probe** (per the user-memory rule "live-probe before
   merge"): run `just chat::run` + ask for a `snapshot` + let the session run
   to ~15 k tokens without crashing. If the Gateway still injects a
   flush, the declared context is still wrong.
4. ~~**Tool-name hardening** (defense in depth): narrow the
   `roboclaws__done` docstring so models can't confuse it with a generic
   "flush complete" signal.~~ Done 2026-04-23 — docstring calls out that
   `done` means **navigation episode ended**, not "memory flush finished"
   or "I have nothing to store", and instructs the model to reply with
   `NO_REPLY` instead when the user turn is a `memory-core` flush.
   Renaming the tool would break examples/tests across the repo — left
   as future work if the narrowed docstring isn't enough.
5. **`maxTokens` high-end probe** (follow-up): v2.5 probe accepted
   `max_tokens=65536` without error. Bumping to 65 536 might unlock
   longer single-turn tool plans, but 32 768 matches Kimi and was the
   conservative choice; revisit if we ever need bigger single-turn
   outputs.

## How to re-audit

```bash
set -a && source .env && set +a

# MiMo
curl -sS -H "Authorization: Bearer $MIMO_TP_KEY" \
  https://token-plan-cn.xiaomimimo.com/v1/models | jq .

# NVIDIA
curl -sS -H "Authorization: Bearer $NV_API_KEY" \
  'https://integrate.api.nvidia.com/v1/models' | jq '.data[] | select(.id|test("nemotron-nano-12b"))'

# Kimi — /models requires the kimi.com host that matches the coding
# tier; the moonshot.cn host rejects the coding key with 401.
curl -sS -H "Authorization: Bearer $KIMI_API_KEY" \
  https://api.kimi.com/coding/v1/models | jq .
```

The `/models` endpoints return ids only — they don't expose
`context_window` or `max_output_tokens`. For those fields, the vendor's
release-notes page is the source of truth; live verification means
pushing a growing prompt until the upstream errors.
