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
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=claude-code provider_profile=mimo-anthropic evidence_lane=world-oracle-labels
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=codex-cli provider_profile=codex-env prompt="find something useful to drink"
```

For map-only work:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels
```

The launch catalog resolves world, backend, intent, provider profile, goal
contract, MCP server type, artifact paths, and checker policy before the lower
recipes run.

## Credentials And Runtime

Copy `.env.example` to `.env`, then fill the keys you have. Codex defaults to
`codex-env` and requires `CODEX_BASE_URL` plus `CODEX_API_KEY`. To use mify for
Codex, set `ROBOCLAWS_CODEX_PROVIDER=mify` explicitly with `XM_LLM_API_KEY`.
Claude Code uses repo-local MiMo, Kimi, or mify Anthropic routes when present.

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
just mcp::up household-cleanup 127.0.0.1 18788 output/debug/household-mcp
just mcp::up semantic-map-build 127.0.0.1 18788 output/debug/map-build-mcp
just mcp::down
```

The server URL is:

```text
http://127.0.0.1:18788/mcp
```

Normal live-agent runs start and stop the appropriate server themselves. The
server entrypoint is `python -m roboclaws.cli.agent_server`, and it accepts only
current household server ids: `household-cleanup` and `semantic-map-build`.

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
