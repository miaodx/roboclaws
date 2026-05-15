# Roboclaws

[CI (main)](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml)
[Live Reports](https://miaodx.com/roboclaws/)
[Python](./pyproject.toml)
[Install](https://docs.astral.sh/uv/)
[License](./LICENSE)

> **Let's Bring Brain To Robots**

**Visible robotics demos driven by VLM policies, OpenClaw, and AI coding agents.**

Roboclaws is a thin demo repo for making AI-driven robotics behavior reviewable:
frames, maps, tool traces, scores, and public/private evaluation boundaries are
published as HTML reports instead of buried in terminal logs.

![Skill-first robotics](docs/human/skill-first-robotics.svg)

It answers three practical questions:

- How can an AI agent drive a robot?
- What context and tools does the agent need?
- What did the agent actually do in the simulated or robot-backed world?

## Run Demos With Just

Install the project once:

```bash
uv sync --extra dev --extra openclaw
```

For MolmoSpaces/MuJoCo cleanup demos, include the heavier extra:

```bash
uv sync --extra dev --extra molmospaces
```

The public command grammar is:

```bash
just task::run <task> <driver> [report|profile] [key=value ...]
```

For full command routing, profiles, and maintainer-only recipes, read
[just/README.md](just/README.md).

## Demo Matrix

GitHub Actions publishes the report site at
[miaodx.com/roboclaws](https://miaodx.com/roboclaws/). If a link looks stale,
check the [CI workflow](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml):
Pages republishes from successful `main` runs.

| Demo | What it proves | Run it locally | Live CI report |
| --- | --- | --- | --- |
| AI2-THOR territory | Multiple robots compete for reachable cells in an iTHOR scene. | Local VLM route is being repaired; use mock/OpenClaw reports for now. | [mock](https://miaodx.com/roboclaws/territory/report.html), [Kimi smoke](https://miaodx.com/roboclaws/smoke/territory/report.html), [OpenClaw](https://miaodx.com/roboclaws/openclaw/territory/report.html) |
| AI2-THOR coverage | Multiple robots cooperate to cover as much of the room as possible. | `just task::run coverage vlm visual agents=2 steps=100` | [mock](https://miaodx.com/roboclaws/coverage/report.html), [Kimi smoke](https://miaodx.com/roboclaws/smoke/coverage/report.html), [OpenClaw](https://miaodx.com/roboclaws/openclaw/coverage/report.html) |
| OpenClaw navigation | OpenClaw Gateway agents control robots through the shared Roboclaws APIs. | `just task::run ai2thor-nav openclaw visual` | [openclaw/demo/report.html](https://miaodx.com/roboclaws/openclaw/demo/report.html) |
| Coding-agent MCP control | Codex or Claude Code drives the robot directly through MCP tools. | `just task::run ai2thor-nav codex visual` or `just task::run ai2thor-nav claude visual` | Local-only today; reports write to `output/runs/<stamp>/`. |
| Photo task | A robot navigates the room and photographs chairs/sofas. | `just task::run photo-chairs openclaw visual` | Local/OpenClaw report artifact. |
| MolmoSpaces cleanup | A cleanup agent tidies a generated household mess while private scoring stays hidden. | `just task::run molmo-cleanup direct world-labels seed=7 generated_mess_count=5` | [Molmo live index](https://miaodx.com/roboclaws/molmo/live/), [Kimi K2.6](https://miaodx.com/roboclaws/molmo/live/kimi-k2.6/seed-7/report.html), [MiMo v2.5 Pro](https://miaodx.com/roboclaws/molmo/live/mimo-v2.5-pro/seed-7/report.html), [MiMo v2 Omni](https://miaodx.com/roboclaws/molmo/live/mimo-v2-omni/seed-7/report.html) |
| MolmoSpaces live agent | Claude Code or Codex connects to the cleanup MCP server and produces the same cleanup report shape. | `just task::run molmo-cleanup claude world-labels seed=7 generated_mess_count=5` | Same Molmo live index; CI currently runs Claude Code through Kimi/MiMo provider profiles. |
| Railway appliance | Single-container hosted demo with UI, viewer, Gateway, and AI2-THOR. | `DEMO_PASSWORD=demo just appliance::run local` | Local appliance surface. |
| Maintainer gate | Fast mock confidence check before shipping repo changes. | `just agent::verify mock` | CI status: [workflow](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml) |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the code map and the full operating
mode contract.

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

Run `just dev::network-status` before OpenClaw or system-provider Claude Code
workflows; work-network restrictions are documented in [AGENTS.md](AGENTS.md).

## Local Report Artifacts

Most demo commands write under `output/` and print the exact run directory.
Common examples:


| Run type                   | Typical output                                          |
| -------------------------- | ------------------------------------------------------- |
| Territory/Coverage games   | `output/territory/<stamp>/`, `output/coverage/<stamp>/` |
| Coding-agent navigation    | `output/runs/<stamp>/`                                  |
| OpenClaw demos             | `output/openclaw-*/<stamp>/`                            |
| Molmo cleanup              | `output/molmo/<driver-or-profile>/<stamp>/seed-7/`      |
| Molmo live CI rehearsal    | `output/molmo/ci-rehearsal/<model>/`                    |
| Molmo planner proof bundle | `output/molmo/planner-proof*/`                          |


Each report directory is meant to be reviewable without re-running the model.

## Documentation Map


| Need                             | Read                                                                                                       |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Code map and operating modes     | [ARCHITECTURE.md](ARCHITECTURE.md)                                                                         |
| Human setup/runbooks/domain docs | [docs/human/README.md](docs/human/README.md)                                                               |
| Skill-first MCP architecture     | [docs/human/mcp-skills-and-semantic-profiles.md](docs/human/mcp-skills-and-semantic-profiles.md)           |
| Public command grammar           | [just/README.md](just/README.md)                                                                           |
| Coding-agent navigation guide    | [docs/human/coding-agent-nav-server.md](docs/human/coding-agent-nav-server.md)                             |
| MolmoSpaces settings             | [docs/human/molmospaces-settings.md](docs/human/molmospaces-settings.md)                                   |
| Current project focus            | [STATUS.md](STATUS.md)                                                                                     |
| Agent operating rules            | [AGENTS.md](AGENTS.md)                                                                                     |


## Related Projects

- [Roboharness](https://github.com/MiaoDX/roboharness) - visual testing harness for AI coding agents in robot simulation
- [Robowbc](https://github.com/MiaoDX/robowbc) - whole-body-control experiments
- [OpenClaw](https://github.com/openclaw/openclaw) - open-source personal AI assistant
- [ROSClaw](https://github.com/PlaiPin/rosclaw) - OpenClaw to ROS 2 bridge
- [AI2-THOR](https://github.com/allenai/ai2thor) - interactive 3D indoor simulation

## License

MIT
