# Just Command Surface

Roboclaws uses a small composable Just grammar instead of exposing every
task/driver/report combination as a separate recipe.

## Public Namespaces

- `task::*` is for humans and natural-language delegation.
- `agent::*` is for maintainer-level dispatch into private implementation
  modules.

Lower modules such as `openclaw::*`, `vlm::*`, `molmo::*`, `harness::*`,
`verify::*`, `mcp::*`, `code::*`, `chat::*`, `appliance::*`, and `dev::*` are
private. They remain runnable for debugging, but they are hidden from
`just --summary` and shell completion.

## Main Grammar

```bash
just task::run <task> <driver> [report|profile] [key=value ...]
```

Tasks:

- `ai2thor-nav`
- `territory`
- `coverage`
- `photo-chairs`
- `molmo-cleanup`
- `molmo-planner-proof`

Drivers:

- `openclaw`
- `vlm`
- `codex`
- `claude`
- `script`
- `direct`
- `mcp-smoke`

Reports for non-Molmo tasks:

- `visual` is the default. Use it for human-facing runs that should produce
  reviewable images, timelines, and metrics.
- `minimal` is for cheaper semantic evidence during AI-agent iteration.

Molmo cleanup profiles:

- `smoke` is the cheap synthetic contract sanity profile.
- `world-labels` is the default structured-label MolmoSpaces/RBY1M report.
- `camera-raw` withholds structured labels and provides raw camera artifacts.
- `camera-labels` registers structured candidates from camera observations.

If the third argument is `key=value`, `task::run` treats the report/profile as
omitted and keeps the task default (`visual` for non-Molmo tasks,
`world-labels` for Molmo cleanup).

## Live Agent Launch Behavior

`just task::run molmo-cleanup codex world-labels` launches a detached tmux session.
The session owns the cleanup MCP server, the `codex exec` process, raw Codex
logs, the MCP trace, and the final checker. The invoking terminal returns after
printing the tmux session name and artifact directory, so monitor sessions do
not spend their own context window on the live agent transcript.

Use the printed probe command, or let it find the latest Codex cleanup run:

```bash
just molmo::status
just molmo::status output/molmo/codex-report/<stamp>/seed-7
tmux attach -t <session>
tail -f output/molmo/codex-report/<stamp>/seed-7/driver.log
```

The probe summarizes tmux liveness, elapsed time, MCP tool progress,
`run_result.json` / `report.html` readiness, and the latest Codex message when
available. Only one detached Molmo/Codex cleanup run is allowed at a time
because each visual run owns a MuJoCo-backed MolmoSpaces backend. If a run is
active or the requested MCP port is already accepting connections, the launcher
fails instead of choosing another port. `claude` and `openclaw` live cleanup
drivers still use their existing interactive launch paths.

Repo-local `.env` provider profiles can route live Claude launchers, and may
route live Codex launchers when the selected endpoint supports Codex's
configured wire API, without editing user-level CLI config:

```bash
ROBOCLAWS_CODEX_PROVIDER=mimo-openai
ROBOCLAWS_CODEX_MODEL=mimo-v2.5-pro
ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic
ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6
```

Detached live Codex sessions inherit selected API key, provider, model, and
proxy variables exported in the invoking shell at launch time. They also source
repo-local `.env` inside the runner, so either route works for local-only
credentials.

Run `just code::codex-provider-smoke` before long Codex visual runs to verify
the selected OpenAI-compatible endpoint works with the pinned Docker-backed
Codex CLI. Do not assume a repo-local OpenAI-compatible provider supports Codex
until this smoke passes; some endpoints may not expose `/v1/responses`.
When `ROBOCLAWS_CODEX_PROVIDER=openai-responses`, the provider smoke and live
Codex launchers also probe `api.openai.com` before starting Codex and fail fast
if the official endpoint is unreachable.

Public Codex / Claude live-agent runs support only the pinned Docker toolchain:

```bash
ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic \
ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6 \
just task::run molmo-cleanup claude world-labels
```

The image is defined by `Dockerfile.coding-agents` and pins
`@openai/codex@0.130.0` plus `@anthropic-ai/claude-code@2.1.143` by default.
Update `scripts/dev/coding_agent_toolchain.env` deliberately when advancing the
agent CLIs. `just code::docker-install-wrappers` still exists for CI setup and
manual debugging where a `codex` or `claude` command path is required.

Codex runs that should use a developer's normal GPT/OpenAI Codex login can opt
into copying host Codex auth plus a minimal provider config into the pinned
container. Run this mode only off the work network; system-provider Codex is
guarded there because direct `api.openai.com` traffic is reset before MCP tool
calls:

```bash
ROBOCLAWS_CODE_AGENT_DOCKER_USE_HOST_CODEX_HOME=1 \
ROBOCLAWS_CODEX_PROVIDER=system \
ROBOCLAWS_CODEX_MODEL=gpt-5.2 \
just task::run molmo-cleanup codex world-labels
```

That mode does not mount the full host `~/.codex`: host agents, hooks, skills,
history, and unrelated user config stay outside the container.

Docker-backed coding-agent tasks use an isolated generated workspace. The agent
container sees `/workspace/task` plus only the skill directories named by
`ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS`, mounted at `/workspace/skills/<name>`.
Repo-root `AGENTS.md`, `CLAUDE.md`, `.git`, and implementation files are not
mounted; the MCP implementation stays on the host and is reached over HTTP.
Current task mappings:

- `ai2thor-nav` direct Codex/Claude: `ai2thor-navigator`
- `photo-chairs` direct Codex/Claude: `capture-object-photo`
- `molmo-cleanup` live Codex/Claude: `molmo-realworld-cleanup`

For Codex, isolated runs also mount an empty read-only `CODEX_HOME/skills`, so
bundled/system Codex skills are not available. Task prompts should read the
mounted skill explicitly, for example `../skills/ai2thor-navigator/SKILL.md` or
`../skills/molmo-realworld-cleanup/SKILL.md`.

## Examples

```bash
just task::run molmo-cleanup codex
just task::run molmo-cleanup codex smoke
just task::run molmo-cleanup direct camera-raw
just task::run molmo-cleanup direct camera-labels
just task::run ai2thor-nav openclaw
just task::run photo-chairs codex
just task::run territory vlm steps=20 agents=2
just task::run coverage script output_dir=output/script/coverage-smoke
just task::run molmo-planner-proof direct mode=dry-run
```

Prompt mappings for agents:

| Prompt | Command |
|---|---|
| "run the MolmoSpaces cleanup task with codex" | `just task::run molmo-cleanup codex world-labels` |
| "run the MolmoSpaces cleanup task with codex with smoke profile" | `just task::run molmo-cleanup codex smoke` |
| "run the MolmoSpaces cleanup camera raw profile" | `just task::run molmo-cleanup direct camera-raw` |
| "run the ai2thor nav task with openclaw" | `just task::run ai2thor-nav openclaw visual` |

## Maintainer Dispatch

Use `agent::*` only when you are intentionally bypassing the human task grammar:

```bash
just agent::run <task> <driver> [report] [key=value ...]
just agent::verify <target> [args ...]
just agent::harness <target> [args ...]
just agent::mcp up
just agent::gateway up
```

For tests, set `ROBOCLAWS_JUST_TRACE=1` to print the lower-level command route
without launching the underlying simulator, Gateway, or agent.
