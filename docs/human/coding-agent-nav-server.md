# Direct Coding-Agent Household MCP Driver

Docker-backed Codex and Claude Code runs drive the household MCP server through
the public launch catalog. The simulator/backend and MCP server stay on the
host; the coding-agent CLI runs in the pinned `Dockerfile.coding-agents` image
with an isolated task workspace.

## Run Through The Public Catalog

Install the repo environment once:

```bash
uv sync --extra dev
```

Use `just run::surface` for normal runs:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=codex-cli provider_profile=codex-router-responses evidence_lane=world-public-labels
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=claude-code provider_profile=mimo-tp-anthropic evidence_lane=world-public-labels
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=codex-cli provider_profile=codex-router-responses prompt="find something useful to drink"
```

For map-only work:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=codex-cli provider_profile=codex-router-responses evidence_lane=camera-grounded-labels camera_labeler=grounding-dino
```

The launch catalog resolves world, backend, intent, provider profile, goal
contract, MCP server type, artifact paths, and checker policy before the lower
recipes run.

## Credentials And Runtime

Copy `.env.example` to `.env`, then fill the keys you have. Codex defaults to
`codex-router-responses` and requires `CODEX_BASE_URL` plus `CODEX_API_KEY`. To use mimo-mify-responses for
Codex, set `ROBOCLAWS_PROVIDER_PROFILE=mimo-mify-responses` explicitly with `XM_LLM_API_KEY`.
To use MiniMax's Responses-compatible route, set
`ROBOCLAWS_PROVIDER_PROFILE=minimax-responses` with `MM_API_KEY`; it defaults to
`MiniMax-M3`. M3 is the default MiniMax model because it is the
multimodal/image-capable row and local paired cleanup evidence did not show a
speed win for `MiniMax-M2.7-highspeed`. Set
`ROBOCLAWS_CODEX_MODEL=MiniMax-M2.7-highspeed` only for explicit comparison
runs. The highspeed model still emits reasoning tokens on the Responses route,
so tiny output-token budgets can stop before assistant text is produced. Claude
Code uses repo-local MiMo, Kimi, or MiMo mify Anthropic routes when present.

Provider/model metadata is centralized in
`roboclaws/agents/provider_registry.py`. The launch catalog, operator console,
OpenAI Agents SDK runner, and shell helpers use that registry for default
models, required env keys, wire API, route health, and route capabilities.
Evidence-lane gating stays separate from provider metadata: `camera-raw-fpv`
requires model image input plus verified runtime image transport, while
structured lanes such as `world-public-labels` and `camera-grounded-labels`
can use text-only routes. MiMo inside `mimo-1000` is default-enabled for
on-demand benchmark and explicit OpenAI-Agents-SDK text experiments, not a
product cleanup default. Kimi OpenAI Chat defaults to `kimi-k2.7-code`;
OpenAI Agents SDK routes use
`ROBOCLAWS_OPENAI_AGENTS_THINKING_MODE=default|enabled|disabled`. Responses
routes map this to the OpenAI `reasoning` body, while Chat-compatible routes
map it to the `thinking` body. Live route verdicts are recorded in
`docs/human/model-route-verdicts.yaml`.

Before long Codex runs, verify the selected endpoint:

```bash
just code::codex-provider-smoke
```

The public recipes launch Codex and Claude Code with the required local-demo
permissions through `scripts/dev/coding_agent_docker.sh`. Bare host `codex` or
`claude` runs are outside the supported demo path unless a human explicitly asks
for system-CLI debugging.

## MCP Lifecycle

The private MCP helper is available for manual debugging:

```bash
just agent::mcp up household-world.cleanup 127.0.0.1 18788 output/debug/household-mcp
just agent::mcp up household-world.map-build 127.0.0.1 18788 output/debug/map-build-mcp
just mcp::down
```

The server URL is:

```text
http://127.0.0.1:18788/mcp
```

Normal live-agent runs start and stop the appropriate server themselves. The
private implementation entrypoint is `python -m roboclaws.cli.agent_server`;
the maintainer facade uses canonical dispatch targets such as
`household-world.cleanup` and `household-world.map-build`.

## Isolated Agent Workspace

Docker-backed coding-agent tasks mount a generated workspace at
`/workspace/task` and task skills under `/workspace/skills/<name>`. Repo source,
`.git`, root agent instructions, and unrelated skills are not mounted into the
agent context. Current task mappings use `skills/molmo-realworld-cleanup`.

For Codex, the container also mounts an empty read-only `CODEX_HOME/skills`, so
system Codex skills are unavailable. Recipe-owned prompts should include the
operative task constraints and refer only to the mounted task skill.

## Artifacts

Runs write under `output/` and print the exact run directory. Important files:

- `trace.jsonl` records public MCP/tool events.
- `run_result.json` records public run state and checker inputs.
- `goal_contract.json` records the normalized launch goal.
- `runtime_metric_map.json` is present for map-build runs.
- `report.html` is the human review surface.

Private evaluator truth must not be added to agent-facing inputs or MCP profile
metadata. Reports may display public and private sections separately when the
checker owns that boundary.
