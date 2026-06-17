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
XM_LLM_API_KEY=      # Codex mify key only with explicit ROBOCLAWS_CODEX_PROVIDER=mify

CODEX_BASE_URL=      # Default Codex codex-env Responses-compatible endpoint
CODEX_API_KEY=       # Default Codex codex-env endpoint key
```

The launch recipes infer the repo-local runtime route from explicit provider
settings. Codex defaults to `codex-env` and requires `CODEX_BASE_URL` plus
`CODEX_API_KEY` (`gpt-5.5`, Responses API). It does not fall back to mify when
`XM_LLM_API_KEY` is present. To use mify, set `ROBOCLAWS_CODEX_PROVIDER=mify`
explicitly; that profile uses `XM_LLM_API_KEY`, `xiaomi/mimo-v2.5`, Responses
API, and web search disabled.
Claude Code prefers a MiMo key when available, then Kimi, then the mify
Anthropic route from `XM_LLM_API_KEY` (`mify-anthropic`,
`xiaomi/mimo-v2.5`). It falls back to the host system provider only off the work
network.

Run `just dev::network-status` before OpenClaw, Claude Code, or Codex
workflows. On the work network, OpenClaw and system-provider Claude Code are
blocked; the repo-local Codex `codex-env` route (`CODEX_BASE_URL` plus
`CODEX_API_KEY`), explicit Codex mify override, and Claude `mify-anthropic` remain
allowed. Work-network restrictions are documented in
[`AGENTS.md`](../../AGENTS.md).

For the current model/provider compatibility table, see
[`model-matrix.md`](model-matrix.md).

## Local Report Artifacts

Most demo commands write under `output/` and print the exact run directory.
Common examples:

| Run type | Typical output |
| --- | --- |
| Product household run | `output/molmo/<recipe-or-run>/<stamp>/seed-7/` or the explicit `output_dir=...` passed to `just run::surface` |
| Eval harness | `output/eval-harness/<stamp>/` |
| Eval suite | `output/evals/<suite>/<stamp>/` with eval results plus links to product run artifacts |
| Planner proof bundle | `output/molmo/planner-proof*/` |
| Historical semantic-map/cleanup roots | `output/household/semantic-map-build/<driver>-*/`, `output/household/household-cleanup/<driver>-*/` |

Each report directory is meant to be reviewable without re-running the model.
Historical roots may appear in old reports and tests, but new eval evidence
should be found through the eval-suite output and its linked product artifacts.
