# Surface And Agent Command Taxonomy

The implemented public command model is the surface/intent catalog in
`just run::surface`. Older `task::run` and AI2-THOR task ids are retired.

## Public Surface

Normal users should start with:

```bash
just run::surface surface=<surface> agent_engine=<engine> [world=<world>] [backend=<backend>] [intent=<intent>] [provider_profile=<profile>] [key=value ...]
```

Current surfaces:

- `household-world`
- `planner-proof`

Current household intents:

- `map-build`
- `cleanup`
- `open-ended`

Current household backends:

- `mujoco`
- `isaaclab`
- `agibot-gdk`

Current agent engines:

- `direct-runner`
- `codex-cli`
- `claude-code`
- `openai-agents-sdk`
- `openclaw-gateway`
- `script-runner`

`prompt=...` without an explicit household intent resolves to
`intent=open-ended`. `intent=cleanup prompt=...` keeps cleanup semantics while
narrowing the user-scoped cleanup request.

## Maintainer Dispatch

`agent::*` is the compact maintainer facade:

```bash
just agent::run <dispatch-target> <agent-engine> [evidence-lane|mode] [key=value ...]
just agent::verify <target> [args ...]
just agent::harness <target> [args ...]
just agent::mcp up|down
just agent::gateway up|down|pull-image
```

Lower modules such as `molmo::*`, `harness::*`, `verify::*`, `mcp::*`,
`code::*`, `chat::*`, and `openclaw::*` are private implementation details.
They remain runnable for debugging, but they are hidden from `just --summary`
and should not be the first response to natural-language run requests.

## Evidence Lanes

Household cleanup/map-build routes use `evidence_lane` to describe what the
agent sees:

- `world-oracle-labels`
- `world-public-labels`
- `camera-raw-fpv`
- `camera-grounded-labels` with `camera_labeler=<labeler>`

`smoke` is a cheap verification preset/private runner mode, not a public
evidence lane.

## Verification

The command taxonomy is covered by:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools
just --summary
just agent::verify ci-required
```
