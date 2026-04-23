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

From `/app/dist/agent-runner.runtime-DXJczOHi.js` in the pinned Gateway
image (`ghcr.io/openclaw/openclaw:2026.4.14`):

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

| Model id (upstream)               | Gateway namespace      | Declared ctx | Declared out cap | Vendor ctx (source)                     | Flush threshold | Status                                              |
|-----------------------------------|------------------------|--------------|------------------|-----------------------------------------|-----------------|-----------------------------------------------------|
| `kimi/k2p5`                       | `anthropic_kimi/k2p5`  | 262 144      | 32 768           | 256K — Moonshot K2.5 release            | 238 144         | OK — live-probed end-to-end                         |
| `kimi/k2.6`                       | `anthropic_kimi/k2.6`  | 262 144      | 32 768           | 256K — Moonshot K2.6 release            | 238 144         | OK — live-probed end-to-end                         |
| `nvidia/nemotron-nano-12b-v2-vl`  | `nvidia/…`             | 131 072      | 4 096            | 128K — NVIDIA NIM model card            | 107 072         | OK — CI-verified                                    |
| `mimo-v2-omni` *(openai)*         | `mimo_openai/…`        | 262 144      | 4 096            | 256K — MiMo 2026-03-18 release note     | 238 144         | OK — aligned 2026-04-23; re-probe `make chat`       |
| `mimo-v2.5-pro` *(openai)*        | `mimo_openai/…`        | 262 144      | 4 096            | needs vendor confirm (likely 256K)      | 238 144         | Aligned with v2-omni pending vendor confirm of V2.5 |
| `mimo-v2.5` *(openai)*            | `mimo_openai/…`        | 262 144      | 4 096            | needs vendor confirm (likely 256K)      | 238 144         | Aligned with v2-omni pending vendor confirm of V2.5 |
| `mimo-v2.5-pro` *(anthropic)*     | `mimo_anthropic/…`     | 262 144      | 4 096            | needs vendor confirm                    | 238 144         | Aligned pending vendor confirm                      |
| `mimo-v2.5` *(anthropic)*         | `mimo_anthropic/…`     | 262 144      | 4 096            | needs vendor confirm                    | 238 144         | Aligned pending vendor confirm                      |

> A flush threshold below ~20 k is effectively "trip on the first `observe`
> turn" because the two prompt images + bootstrap context + SOUL/AGENTS
> files already consume 7–10 k tokens.

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

1. ~~**Bootstrap**: update all MiMo models to `contextWindow: 262144`.~~
   Done 2026-04-23 (all 5 MiMo entries in `scripts/openclaw-bootstrap.sh`
   bumped from 32 768 → 262 144). `maxTokens: 4096` on all MiMo entries
   still looks placeholder — confirm against vendor output cap before
   trusting long-form tool-call plans.
2. **Vendor confirm V2.5**: `mimo-v2.5-pro` and `mimo-v2.5` are aligned
   at 262 144 pending vendor spec confirmation. If the vendor doc shows a
   lower number for the V2.5 line, revert those four rows (both openai
   and anthropic blocks).
3. **Tests**: `tests/test_openclaw_bootstrap.py` should assert
   `contextWindow >= 131072` for any advertised model so a copy-paste 32k
   slips through CI next time.
4. **Pre-merge probe** (per the user-memory rule "live-probe before
   merge"): run `make chat` + ask for a `snapshot` + let the session run
   to ~15 k tokens without crashing. If the Gateway still injects a
   flush, the declared context is still wrong.
5. **Tool-name hardening** (defense in depth): rename `roboclaws__done`
   to something the model can't confuse with a generic "flush complete"
   signal, or narrow its docstring so MiMo-class models won't pick it in
   response to a memory-flush prompt. Tracked separately; not required if
   the threshold fix holds.

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
