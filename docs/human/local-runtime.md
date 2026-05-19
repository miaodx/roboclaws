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

CODEX_BASE_URL=      # Codex Responses-compatible endpoint
CODEX_API_KEY=       # Codex endpoint key
```

The launch recipes infer the repo-local runtime route from those keys. Codex
uses `CODEX_BASE_URL` / `CODEX_API_KEY`. Claude Code prefers a MiMo key when
available, then Kimi, and otherwise falls back to the host system provider only
off the work network.

Run `just dev::network-status` before OpenClaw, Claude Code, or Codex
workflows; work-network restrictions are documented in
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
