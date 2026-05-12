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
just task::run <task> <driver> [report] [key=value ...]
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

Reports:

- `visual` is the default. Use it for human-facing runs that should produce
  reviewable images, timelines, and metrics.
- `minimal` is for cheaper semantic evidence during AI-agent iteration.

If the third argument is `key=value`, `task::run` treats the report as omitted
and keeps the `visual` default.

## Live Agent Launch Behavior

`just task::run molmo-cleanup codex visual` launches a detached tmux session.
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
available. `claude` and `openclaw` live cleanup drivers still use their
existing interactive launch paths.

## Examples

```bash
just task::run molmo-cleanup codex
just task::run molmo-cleanup codex minimal
just task::run ai2thor-nav openclaw
just task::run territory vlm steps=20 agents=2
just task::run coverage script output_dir=output/script/coverage-smoke
just task::run molmo-planner-proof direct mode=dry-run
```

Prompt mappings for agents:

| Prompt | Command |
|---|---|
| "run the molmospace cleanup task with codex" | `just task::run molmo-cleanup codex visual` |
| "run the molmospace cleanup task with codex with minimal report" | `just task::run molmo-cleanup codex minimal` |
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
