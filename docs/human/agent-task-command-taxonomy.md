# Surface And Agent Command Taxonomy

The implemented public command model is the surface open-task catalog in
`just run::surface`, with optional presets for repeated household jobs. Older
`task::run` and AI2-THOR task ids are retired.

## Public Surface

Normal users should start with:

```bash
just run::surface surface=<surface> agent_engine=<engine> [world=<world>] [backend=<backend>] [preset=<preset>] [prompt=<goal>] [provider_profile=<profile>] [key=value ...]
```

Current surfaces:

- `household-world`
- `planner-proof`

Current household presets:

- `map-build`
- `cleanup`

No-preset household runs are open-ended prompt-driven tasks.

Current household backends:

- `mujoco`
- `isaaclab`
- `agibot-gdk`

Current agent engines:

- `direct-runner`
- `codex-cli`
- `claude-code`
- `openai-agents-sdk`

Validation-required maintainer engines such as `openclaw-gateway` are not part
of the normal public engine list.

`prompt=...` without a household preset runs the default open-task contract.
`preset=cleanup prompt=...` keeps cleanup semantics while narrowing the
user-scoped cleanup request.

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

## Validation And Eval Layers

These layers are maintainer surfaces, not ordinary product-run axes:

| Layer | Command Shape | Use |
| --- | --- | --- |
| Validation matrix | `just agent::harness agent-validation recommend|execute ...` | Selects and records gates for a plan, diff, or explicit axis set. |
| Eval suite | `just agent::eval suite=<suite> ...` | Runs versioned samples, trials, graders, aggregate metrics, and failure replay. |
| Harness recipe | `harness::*` or lower private modules | Executes specialist proofs used by product, validation, or eval flows. |

The validation matrix answers "what should this change validate?" Eval suites
answer "is this capability improving across a stable benchmark?" Harness
recipes answer "how do we execute this low-level proof?"

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
