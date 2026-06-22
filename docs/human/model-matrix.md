# Model Matrix

This page is the short human summary for current model/provider routes.

Authoritative sources:

- Route metadata: `roboclaws/agents/provider_registry.py`
- Live route verdicts: `docs/human/model-route-verdicts.yaml`
- Local runtime keys: `docs/human/local-runtime.md`

Historical provider incidents and superseded model rows belong in
`docs/retrospectives/`, `docs/adr/`, or archived plans, not in this current
route summary.

## Default Routes

| Agent engine | Default provider profile | Default model | Current status |
| --- | --- | --- | --- |
| `codex-cli` | `codex-router-responses` | `gpt-5.5` | Healthy default route for structured and camera-label lanes. |
| `claude-code` | `mimo-tp-anthropic` | `mimo-v2.5` | Healthy when the repo-local key is configured. |
| `openai-agents-sdk` | explicit profile required | route-specific | Experimental/non-default product route. |
| `direct-runner` | none | none | Deterministic; no model route. |

Useful explicit profiles:

| Provider profile | Wire API | Default model | Notes |
| --- | --- | --- | --- |
| `mimo-mify-responses` | Responses | `xiaomi/mimo-v2.5` | Codex route is degraded in current verdicts; use only when explicitly selected. |
| `minimax-responses` | Responses | `MiniMax-M3` | Healthy for OpenAI Agents SDK structured cleanup; blocked for Codex MCP cleanup today. |
| `kimi-openai-chat` | OpenAI Chat | `kimi-k2.7-code` | Experimental OpenAI Agents SDK route; uses provider-specific thinking fields. |
| `mimo-inside-openai-chat` | OpenAI Chat | `mimo-1000` | On-demand benchmark/text route, not a product cleanup default. |
| `kimi-anthropic` | Anthropic-compatible | `kimi-k2.6` | Explicit Claude Code route. |
| `mimo-mify-anthropic` | Anthropic-compatible | `xiaomi/mimo-v2.5` | Explicit Claude Code route via the internal aggregator. |

## Route Rules

- Structured lanes can use text-only routes when tool transport is healthy.
- Raw camera lanes require both image input support and verified runtime image
  transport for the selected engine/profile pair.
- `ROBOCLAWS_OPENAI_AGENTS_THINKING_MODE=default|enabled|disabled` is only for
  OpenAI Agents SDK routes. Responses routes map it to `reasoning`; Chat routes
  map it to the provider-specific thinking field.
- `disabled` thinking mode is for diagnostics only when the provider supports
  it.
- Do not infer route health from model capability alone; use
  `model-route-verdicts.yaml`.

## Update Checklist

When a provider route changes:

1. Update `roboclaws/agents/provider_registry.py`.
2. Update `docs/human/model-route-verdicts.yaml` with live evidence.
3. Update this summary only if the default, health interpretation, or operator
   guidance changed.
4. Run the focused provider/route tests or the model-matrix benchmark command
   below.

## Useful Commands

```bash
just dev::model-matrix-benchmark --iterations 1 --timeout-s 240
just dev::model-matrix-benchmark --list-agent-cases
```

The benchmark writes under `output/dev/model-matrix/<timestamp>/`.
