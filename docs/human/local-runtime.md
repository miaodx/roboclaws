# Local Runtime Reference

This page holds the small amount of local runtime setup that normal demo users
need. The rule is:

```text
Normal users configure keys only; command shape controls behavior.
```

## Provider Keys

Copy `.env.example` to `.env`, then fill only the keys you have:

```bash
KIMI_API_KEY=        # Kimi / Moonshot
MIMO_TP_KEY=        # MiMo
NV_API_KEY=          # NVIDIA NIM, optional

XM_LLM_BASE_URL=https://api.llm.mioffice.cn/v1  # Internal multi-model aggregator
XM_LLM_ANTHROPIC_BASE_URL=      # Optional Claude mify route override
XM_LLM_API_KEY=      # Default Codex mify route

CODEX_BASE_URL=      # Optional non-mify Codex Responses-compatible endpoint
CODEX_API_KEY=       # Optional non-mify Codex endpoint key
```

The launch recipes infer the repo-local runtime route from those keys. Codex
prefers the internal multi-model aggregator when `XM_LLM_API_KEY` is present
(`mify`, `xiaomi/mimo-v2.5`, Responses API, web search disabled). Explicit
`CODEX_BASE_URL` / `CODEX_API_KEY` remains available for non-mify debugging.
Claude Code prefers a MiMo key when available, then Kimi, then the mify
Anthropic route from `XM_LLM_API_KEY` (`mify-anthropic`,
`xiaomi/mimo-v2.5`). It falls back to the host system provider only off the work
network.

Run `just dev::network-status` before OpenClaw, Claude Code, or Codex
workflows. On the work network, OpenClaw and system-provider Claude Code are
blocked; repo-local `.env` Codex routes (`XM_LLM_API_KEY`, or
`CODEX_BASE_URL` plus `CODEX_API_KEY`) and Claude `mify-anthropic` remain
allowed. Work-network restrictions are documented in
[`AGENTS.md`](../../AGENTS.md).

For the current model/provider compatibility table, see
[`model-matrix.md`](model-matrix.md).

## Local Report Artifacts

Most demo commands write under `output/` and print the exact run directory.
Common examples:

| Run type | Typical output |
| --- | --- |
| Territory/Coverage games | `output/territory/<stamp>/`, `output/coverage/<stamp>/` |
| Coding-agent navigation | `output/runs/<stamp>/` |
| OpenClaw demos | `output/openclaw-*/<stamp>/` |
| Molmo cleanup | `output/molmo/<driver-or-profile>/<stamp>/seed-7/` |
| Molmo live CI rehearsal | `output/molmo/ci-rehearsal/<model>/` |
| Molmo planner proof bundle | `output/molmo/planner-proof*/` |

Each report directory is meant to be reviewable without re-running the model.
