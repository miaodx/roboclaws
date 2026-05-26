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

![Task, skill, and capability profile architecture](docs/human/mcp-skills-and-semantic-profiles.svg)

It answers three practical questions:

- How can an AI agent drive a robot?
- What context and tools does the agent need?
- What did the agent actually do in the simulated or robot-backed world?

## MCP and Skill Design Principles

Roboclaws treats reusable robot behavior as **skills first** and MCP tools as a
bounded public robot capability surface.

| Principle | Practice |
| --- | --- |
| Start from open-ended goals | A user asks for work such as "clean the room" or "take useful photos"; an agent selects or creates a skill to do it. |
| Keep tasks as run surfaces | Public commands such as `semantic-map-build` and `household-cleanup` own parameters, reports, and acceptance gates. |
| Keep strategy in skills | Skills own prompt strategy, scripts, examples, checks, and task-specific loops such as photo capture or cleanup. |
| Keep MCP bounded | MCP tools expose semantic robot capabilities like observe, move, pick, place, and done; they should not hide a whole task behind one opaque call. |
| Profile public capabilities | Semantic profiles describe reusable capability environments that skills can require; profiles compose by requirement, not by copying another profile's tools. |
| Label privileged help | Simulator or demo helpers such as full object inventory and target-relative teleport are useful, but they stay labeled as privileged tools, not canonical robot abilities. |
| Protect private evaluation truth | Hidden mess sets, acceptable destinations, private manifests, and scoring truth stay out of public profile metadata and agent-facing skill inputs. |
| Let reports improve skills | Traces, artifacts, and evals feed the skill lifecycle: improve, split, merge, prune, or promote behavior only when the boundary is stable. |

The working abstraction ladder is:

```text
open-ended goal
  -> runnable task
  -> agent skill
  -> capability profile requirements
  -> MCP capability tools
  -> backend variant
```

Default decision: improve or add a skill when behavior changes; add or rename a
runnable task only when the public command, parameters, report shape, or
acceptance gates change. Promote behavior into MCP only when multiple skills
need it, the input/output shape is stable, public/private boundaries are clear,
and traces can preserve the important substeps. The detailed profile and skill
reference is
[docs/human/mcp-skills-and-semantic-profiles.md](docs/human/mcp-skills-and-semantic-profiles.md).

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
| Coding-agent MCP control | Docker-backed Codex or Claude Code drives the robot directly through MCP tools. | `just task::run ai2thor-nav codex visual` or `just task::run ai2thor-nav claude visual` | Local-only today; reports write to `output/runs/<stamp>/`. |
| Photo task | A robot navigates the room and photographs chairs/sofas. | `just task::run photo-chairs openclaw visual` | Local/OpenClaw report artifact. |
| MolmoSpaces cleanup | A cleanup agent tidies a generated household mess while private scoring stays hidden. | `just task::run molmo-cleanup direct world-labels seed=7 generated_mess_count=5` | [Molmo live index](https://miaodx.com/roboclaws/molmo/live/), [Kimi K2.6](https://miaodx.com/roboclaws/molmo/live/kimi-k2.6/seed-7/report.html), [MiMo v2.5 Pro](https://miaodx.com/roboclaws/molmo/live/mimo-v2.5-pro/seed-7/report.html), [MiMo v2 Omni](https://miaodx.com/roboclaws/molmo/live/mimo-v2-omni/seed-7/report.html) |
| MolmoSpaces live agent | Docker-backed Claude Code or Codex connects to the cleanup MCP server and produces the same cleanup report shape. | `just task::run molmo-cleanup claude world-labels seed=7 generated_mess_count=5` | Same Molmo live index; CI currently runs Claude Code through Kimi/MiMo provider profiles. |
| Railway appliance | Single-container hosted demo with UI, viewer, Gateway, and AI2-THOR. | `DEMO_PASSWORD=demo just appliance::run local` | Local appliance surface. |
| Maintainer gate | Fast mock confidence check before shipping repo changes. | `just agent::verify mock` | CI status: [workflow](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml) |

See [ARCHITECTURE.md](ARCHITECTURE.md) for the code map and the full operating
mode contract.

## Documentation Map


| Need                             | Read                                                                                                       |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Code map and operating modes     | [ARCHITECTURE.md](ARCHITECTURE.md)                                                                         |
| Human setup/runbooks/domain docs | [docs/human/README.md](docs/human/README.md)                                                               |
| Detailed MCP profile reference   | [docs/human/mcp-skills-and-semantic-profiles.md](docs/human/mcp-skills-and-semantic-profiles.md)           |
| Skill library convention         | [skills/README.md](skills/README.md)                                                                       |
| Public command grammar           | [just/README.md](just/README.md)                                                                           |
| Local keys and report artifacts  | [docs/human/local-runtime.md](docs/human/local-runtime.md)                                                 |
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
