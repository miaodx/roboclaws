# Local Runtime Reference

This page holds local runtime details that are too operational for the root
`README.md`: provider keys, coding-agent provider profiles, and report artifact
locations.

## Provider Keys

Real provider runs read keys from the environment or the gitignored repo-local
`.env` file:

```bash
export KIMI_API_KEY=...       # Kimi / Moonshot
export MIMO_TP_KEY=...        # MiMo provider profiles
export NV_API_KEY=...         # NVIDIA NIM, optional
```

Repo-local coding-agent provider profiles can route Codex or Claude Code
through Kimi/MiMo without changing user-level CLI config:

```bash
# Codex provider routing is present but not the validated README path yet.
ROBOCLAWS_CODEX_PROVIDER=mimo-openai
ROBOCLAWS_CODEX_MODEL=mimo-v2.5-pro

ROBOCLAWS_CLAUDE_PROVIDER=mimo-anthropic
ROBOCLAWS_CLAUDE_MODEL=mimo-v2-omni
```

Run `just dev::network-status` before OpenClaw, system-provider Claude Code, or
system-provider Codex workflows; work-network restrictions are documented in
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
