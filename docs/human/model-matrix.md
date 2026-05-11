# Model Matrix — declared vs. vendor-spec

Canonical reference for every model we advertise to the OpenClaw Gateway via
`scripts/openclaw-bootstrap.sh`. Update this file whenever the bootstrap
provider JSON changes; CI does not cross-check the numbers against vendor
docs, so this is the audit trail.

Why this file exists: on 2026-04-23 a MiMo chat run crashed because
`contextWindow: 32768` was declared for `mimo-v2-omni` while the vendor
publishes 256K. The Gateway's memory-flush threshold is
`contextWindow - 24000`, so a wrong number turns a headroom cushion into
an on-turn-one trigger. See
`.planning/phases/02.8-split-model-vision/02.8-CONTEXT.md` and the retro
in `docs/retrospectives/` for the full incident write-up.

Last full audit: 2026-04-23 (bootstrap `fd2b878`).

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
| `mimo-v2-omni` *(openai)*         | `mimo_openai/…`        | 262 144      | 32 768           | 256K — MiMo 2026-03-18 release note              | 238 144         | OK — aligned 2026-04-23; `maxTokens` probed live |
| `mimo-v2.5-pro` *(openai)*        | `mimo_openai/…`        | 1 048 576    | 32 768           | 1M — MiMo updates page (V2.5 long-context line)  | 1 024 576       | OK — aligned 2026-04-23                          |
| `mimo-v2.5` *(openai)*            | `mimo_openai/…`        | 1 048 576    | 32 768           | 1M — MiMo updates page (V2.5 long-context line)  | 1 024 576       | OK — aligned 2026-04-23                          |
| `mimo-v2.5-pro` *(anthropic)*     | `mimo_anthropic/…`     | 1 048 576    | 32 768           | 1M — MiMo updates page (V2.5 long-context line)  | 1 024 576       | OK — aligned 2026-04-23                          |
| `mimo-v2.5` *(anthropic)*         | `mimo_anthropic/…`     | 1 048 576    | 32 768           | 1M — MiMo updates page (V2.5 long-context line)  | 1 024 576       | OK — aligned 2026-04-23                          |

> A flush threshold below ~20 k is effectively "trip on the first `observe`
> turn" because the two prompt images + bootstrap context + SOUL/AGENTS
> files already consume 7–10 k tokens.
>
> `maxTokens` is an output-cap hint, not a context budget. It was 4 096 on
> every MiMo entry (placeholder); live-probed at 2026-04-23 that all three
> MiMo variants accept `max_tokens=32768` (one even accepts 65 536) without
> error. Set to 32 768 to match Kimi — a single tool-call round-trip with a
> long rationale fits comfortably.

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

## MiMo `/v1/models` (live, 2026-04-23)

Returned ids on `https://token-plan-cn.xiaomimimo.com/v1/models` with
`MIMO_TP_KEY` set:

```
mimo-v2-omni
mimo-v2-pro                ← exists upstream; NOT advertised in our bootstrap
mimo-v2-tts
mimo-v2.5
mimo-v2.5-pro
mimo-v2.5-tts
mimo-v2.5-tts-voiceclone
mimo-v2.5-tts-voicedesign
```

`mimo-v2-pro` ≠ `mimo-v2.5-pro`. If we ever want a text-only companion for
`mimo-v2-omni` on the v2 line, that's a separate probe target.

## Vendor links (authoritative)

- MiMo — <https://platform.xiaomimimo.com/docs/updates/model>
  (release notes index; `mimo-v2-omni` entry dated 2026-03-18 states
  "Supports up to 256K context length")
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
