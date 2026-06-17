# Roboclaws

[CI (main)](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml)
[Live Reports](https://miaodx.com/roboclaws/)
[Python](./pyproject.toml)
[Install](https://docs.astral.sh/uv/)
[License](./LICENSE)

> **Let's Bring Brain To Robots**

**Visible household-robot demos driven by MCP tools, reusable skills, and AI coding agents.**

Roboclaws is a thin demo repo for making AI-driven robotics behavior reviewable:
frames, maps, tool traces, scores, and public/private evaluation boundaries are
published as HTML reports instead of buried in terminal logs.

![Surface, intent, skill, and capability profile architecture](docs/human/mcp-skills-and-semantic-profiles.svg)

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
| Keep surfaces and presets separate | Public commands use `run::surface` with named `surface=...`, natural-language `prompt=...`, and optional `preset=...` entries for repeated jobs. |
| Keep strategy in skills | Skills own prompt strategy, scripts, examples, checks, and task-specific loops such as photo capture or cleanup. |
| Keep MCP bounded | MCP tools expose semantic robot capabilities like observe, move, pick, place, and done; they should not hide a whole task behind one opaque call. |
| Profile public capabilities | Semantic profiles describe reusable capability environments that skills can require; profiles compose by requirement, not by copying another profile's tools. |
| Label privileged help | Simulator or demo helpers such as full object inventory and target-relative teleport are useful, but they stay labeled as privileged tools, not canonical robot abilities. |
| Protect private evaluation truth | Hidden mess sets, acceptable destinations, private manifests, and scoring truth stay out of public profile metadata and agent-facing skill inputs. |
| Let reports improve skills | Traces, artifacts, and evals feed the skill lifecycle: improve, split, merge, prune, or promote behavior only when the boundary is stable. |

The working abstraction ladder is:

```text
open-ended goal
  -> runnable surface and optional preset
  -> agent skill
  -> capability profile requirements
  -> MCP capability tools
  -> backend variant
```

Default decision: improve or add a skill when behavior changes; add or rename a
surface only when the domain contract changes; add a `preset=` row when a known
task needs its own skill, capabilities, report, or gates. Promote behavior into
MCP only when multiple skills need it, the input/output shape is stable,
public/private boundaries are clear, and traces can preserve the important
substeps. The detailed profile and skill reference is
[docs/human/mcp-skills-and-semantic-profiles.md](docs/human/mcp-skills-and-semantic-profiles.md).

## Run Demos With Just

Install the project once:

```bash
uv sync --extra dev
```

The `dev` extra includes the standard MolmoSpaces/MuJoCo CPU runtime used by
local cleanup demos. Isaac Lab is scoped to the B1 / Map 12 digital-twin route
and generic local runtime proof; keep it isolated in `.venv-isaaclab/` and do
not treat it as part of normal MolmoSpaces demos.

The public command grammar is named-parameter only. Public household launches
name the operator-facing surface, world or scene, backend runtime, optional task
preset, and agent engine separately:

```bash
just run::surface surface=<surface> agent_engine=<engine> [world=<world>] [backend=<backend>] [preset=<preset>] [prompt=<goal>] [key=value ...]
```

For full command routing, profiles, and maintainer-only recipes, read
[just/README.md](just/README.md).

To monitor and launch the supported local coding-agent household routes from a
standalone browser console, run:

```bash
just console::run
```

The console uses the same world/backend/preset/agent-engine catalog for local
coding-agent runs; it does not accept arbitrary browser-submitted shell
commands.

## Demo Matrix

GitHub Actions publishes the report site at
[miaodx.com/roboclaws](https://miaodx.com/roboclaws/). If a link looks stale,
check the [CI workflow](https://github.com/MiaoDX/roboclaws/actions/workflows/ci.yml):
Pages republishes from successful `main` runs.

| Demo | What it proves | Run it locally | Live CI report |
| --- | --- | --- | --- |
| Semantic map build | A no-cleanup sweep starts from the Base Navigation Map and builds public runtime map evidence. Online `runtime_metric_map.json` output and converted Agibot `navigation_memory.json` can both feed the canonical Actionable Semantic Map Snapshot contract. | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=grounding-dino seed=7 scenario_setup=baseline` | Local artifact today. |
| Household cleanup | A cleanup agent tidies a relocated household setup from Base Navigation Map context while private scoring stays hidden. | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=5` | [Molmo live index](https://miaodx.com/roboclaws/molmo/live/), [Kimi K2.6](https://miaodx.com/roboclaws/molmo/live/kimi-k2.6/seed-7/report.html), [MiMo v2.5 Pro](https://miaodx.com/roboclaws/molmo/live/mimo-v2.5-pro/seed-7/report.html), [MiMo v2.5](https://miaodx.com/roboclaws/molmo/live/mimo-v2.5/seed-7/report.html) |
| Open-ended household goal | A coding agent receives a user goal, builds or uses household evidence, and declares task-level completion without cleanup-specific terminal scoring. | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=codex-cli provider_profile=codex-env prompt="find something useful to drink"` | Local artifact today. |
| Household live agent | Docker-backed Claude Code or Codex connects to the cleanup MCP server and produces the same cleanup report shape. | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=claude-code provider_profile=mimo-anthropic evidence_lane=world-public-labels seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=5` | Same Molmo live index; CI currently runs Claude Code through Kimi/MiMo provider profiles. |
| Planner proof | A household cleanup run can hand off planner proof requests for local manipulation evidence without changing the public cleanup contract. | `just run::surface surface=planner-proof world=planner-proof/default backend=mujoco intent=planner-proof agent_engine=direct-runner mode=dry-run` | Local artifact today. |
| Agent operator console | Standalone local browser console for supported Codex, Claude Code, and experimental OpenAI Agents SDK household routes with backend locks, launch-axis gates, live state, and artifact links. | `just console::run` | Local-only operator surface. |
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
| Coding-agent household MCP guide | [docs/human/coding-agent-nav-server.md](docs/human/coding-agent-nav-server.md)                             |
| MolmoSpaces settings             | [docs/human/molmospaces-settings.md](docs/human/molmospaces-settings.md)                                   |
| Current project focus            | [STATUS.md](STATUS.md)                                                                                     |
| Agent operating rules            | [AGENTS.md](AGENTS.md)                                                                                     |


## Related Projects

- [Roboharness](https://github.com/MiaoDX/roboharness) - visual testing harness for AI coding agents in robot simulation
- [Robowbc](https://github.com/MiaoDX/robowbc) - whole-body-control experiments
- [OpenClaw](https://github.com/openclaw/openclaw) - open-source personal AI assistant
- [ROSClaw](https://github.com/PlaiPin/rosclaw) - OpenClaw to ROS 2 bridge

## License

MIT
