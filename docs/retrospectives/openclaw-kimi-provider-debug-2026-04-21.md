# OpenClaw Kimi Provider Debug — 2026-04-21

## Purpose

Record the local debugging work on the single-agent autonomous OpenClaw loop
after the Phase 2.5 decision-audit refactor started stalling at the first
`observe`.

## Environment

- Repo-local workstation session
- Docker image: `ghcr.io/openclaw/openclaw:2026.4.14`
- AI2-THOR: local `uv` environment
- Upstream provider: Kimi / Moonshot

## What was added

- Runtime watchdog + `start_run` bridge metrics
- Timeout diagnostics capture from the Gateway container
- Explicit Kimi provider-mode switch in `scripts/openclaw-bootstrap.sh`
- Explicit `agents.defaults.imageModel.primary` pinning for the custom Kimi path
- Prompt / skill guidance telling the agent to avoid the generic Gateway `image`
  tool unless it is truly blocked
- Quoted bootstrap heredoc fix so Python comments containing backticks no longer
  trigger stray shell command substitution during pre-seed

## Provider paths compared

### 1. Custom provider override

- Provider id: `anthropic_kimi`
- Transport: `anthropic-messages`
- Host: `https://api.kimi.com/coding/`
- Current default model: `anthropic_kimi/k2.6`

### 2. Stock OpenClaw plugin/provider

- Provider id: `kimi`
- Transport: Gateway built-in `kimi-coding` plugin
- Current usable model on this pinned image: `kimi/k2p5`

## Key findings

### Direct upstream control

A direct control probe against Kimi's Anthropic-compatible `/coding` endpoint
returned in about `44s` for the kickoff prompt, so the local machine did have
working network/API access during this investigation.

### Custom provider: old vs new model id

- `anthropic_kimi/k2.6-code-preview`:
  - `1 observe`, `0 move`, then `wall_clock`
- `anthropic_kimi/k2.6`:
  - `3 observe`, `1 move`, then `wall_clock`

So the new `k2.6` id is better than the old preview id for the same custom
provider shape, but it still stalls far earlier than the stock plugin path.

### Stock plugin on pinned Docker image

- `kimi/k2p5` works on the pinned image and progresses in the autonomous loop
  before eventually hitting the same overall embedded-run timeout.
- `kimi/k2.6` does **not** work on `ghcr.io/openclaw/openclaw:2026.4.14`.
  The bootstrap probe fails with:
  - `Unknown model: kimi/k2.6`

This means the local Docker image is behind the remote OpenClaw instance's
catalog/provider state. Do not treat `plugin + k2.6` as a local regression in
roboclaws until the Gateway image is upgraded.

## Image-handling investigation

### Bootstrap / config changes

The bootstrap now seeds both:

- `agents.defaults.model.primary = anthropic_kimi/k2.6`
- `agents.defaults.imageModel.primary = anthropic_kimi/k2.6`

This matters because the pinned Gateway image auto-pairs the generic `image`
tool to the first image-capable model in the provider catalog when
`imageModel` is unset. Before the pin, the custom Kimi path could silently send
image-tool work to `anthropic_kimi/k2p5` even though the main agent model was
`anthropic_kimi/k2.6`.

### What actually works

Direct multimodal chat on the custom provider path works with **two**
`data:image/...` inputs in one request:

- FPV image
- overhead image

This was verified live against the local Gateway by extracting real run frames
and sending them through the normal chat-completions path. The model described
both images successfully.

### What does not work reliably

The generic Gateway `image` tool is still unreliable on the pinned local image:

- `/tmp/...` paths fail immediately at the local-media allowlist layer
- workspace-local media paths get past the allowlist, but the image-tool call
  still aborts upstream

So the current local best practice is:

1. Prefer normal multimodal chat with `data:image/...`
2. If a file path is unavoidable, use workspace-local media roots, not `/tmp`
3. Do not rely on the generic Gateway `image` tool for the autonomous loop on
   the pinned local image

## Current decision

- Keep the repo default on the **custom** provider path:
  - `PROVIDER=kimi`
  - `KIMI_PROVIDER_MODE=custom`
  - `MODEL=anthropic_kimi/k2.6`
- For the **stock plugin** path on the current pinned local Docker image, use:
  - `PROVIDER=kimi`
  - `KIMI_PROVIDER_MODE=plugin`
  - `MODEL=kimi/k2p5`
- Revisit `plugin + k2.6` only after upgrading the local OpenClaw image.

## Artifacts

### Short provider comparison runs

- Custom old id:
  - `output/openclaw-autonomous/provider-compare-custom-20260421T000000Z/`
- Custom new id:
  - `output/openclaw-autonomous/provider-compare-custom-k26-20260421T000000Z/`
- Plugin old id:
  - `output/openclaw-autonomous/provider-compare-plugin-20260421T000000Z/`

### Plugin `k2.6` failure

Observed locally via bootstrap:

- `PROVIDER=kimi KIMI_PROVIDER_MODE=plugin MODEL=kimi/k2.6 ./scripts/openclaw-bootstrap.sh`
- Failure: `Unknown model: kimi/k2.6`

### Long autonomous probes

- Custom default:
  - `output/openclaw-autonomous/long-custom-k26-20260421T000000Z/`
  - `1 observe`, `0 move`, `wall_clock`
  - Gateway inner log shows repeated image-tool failures before timeout:
    - upstream decode failure on a `data:image/jpeg;base64,...` payload
    - local-path rejection for `/tmp/fpv.jpg`
- Plugin on pinned Docker image:
  - `output/openclaw-autonomous/long-plugin-k2p5-20260421T000000Z/`
  - `8 observe`, `7 move`, `wall_clock`
  - No image-tool failure was logged in the plugin path
  - The run progressed normally for several observe/move turns before hitting
    the same embedded-run timeout ceiling

## Working hypothesis

The custom/provider regression is not just "Kimi is slow" or "the local network
is bad". The stronger signal is that the custom path is invoking Gateway image
tooling in a way the pinned local image cannot complete cleanly:

- one failure path reports invalid or unsupported image data
- another reports that `/tmp/fpv.jpg` is outside an allowed local-media
  directory

That divergence did **not** appear in the stock plugin path on the same Docker
image, which strongly suggests the custom path is exercising a different
tool-or-media branch inside Gateway.

## Latest demo reruns after image-model pinning

Two fresh autonomous demo runs were executed locally on `FloorPlan201` with:

- `--max-moves 30`
- `--wall-budget 180`
- fresh bootstrap per run
- `TIMEOUT_SECONDS=240` via the bridge/bootstrap path

### 1. Custom default (`anthropic_kimi/k2.6`)

Artifacts:

- `output/openclaw-autonomous/demo-custom-k26-20260421T063424Z/`

Outcome:

- `4 observe`
- `2 move`
- `terminated_by=wall_clock`
- `gateway_error=read_timeout`

Important detail from the inner Gateway log:

- the agent still tried the old
  `curl -sS http://host.docker.internal:18788/observe | python3 .../decode.py`
  pattern
- Gateway `exec` refused it with:
  - `exec preflight: complex interpreter invocation detected`
- the agent then fell back to the generic `image` tool on workspace-local files:
  - `.../media/fpv.jpg`
  - `.../media/overhead.jpg`
- both image-tool calls aborted upstream even though the paths were allowed

This means the newer prompt/skill guidance was **not** enough to suppress the
older tool strategy in the long-running custom run.

### 2. Stock plugin (`kimi/k2p5`)

Artifacts:

- `output/openclaw-autonomous/demo-plugin-k2p5-20260421T063930Z/`

Outcome:

- `1 observe`
- `0 move`
- `terminated_by=wall_clock`
- `gateway_error=read_timeout`

Important detail:

- this rerun did **not** show the same `exec preflight` or generic `image`
  failures in the Gateway log
- but it stalled even earlier, after the very first `observe`

### Side-by-side takeaway

After the image-model pin and prompt cleanup:

- the custom path now progresses **further** than the plugin path on this local
  rerun
- but the custom path still contains a legacy internal strategy that tries to
  pipe `observe` through `python3 decode.py` and then falls back to the generic
  image tool
- the plugin path avoids that visible failure mode, but still stalls inside the
  same long-lived Gateway request

So the current local state is not "plugin good, custom bad" anymore. It is:

- `custom`: more progress, but obviously taking a bad internal branch
- `plugin`: less progress, cleaner log, still timing out

Both still end on Gateway-side read timeout.

## Follow-up

- Keep `custom + anthropic_kimi/k2.6` as the repo default
- Use `plugin + kimi/k2p5` for pinned-local Docker comparisons until the image
  is upgraded
- When debugging the custom path further, focus on:
  - why the long-running agent still chooses the old
    `curl | python3 decode.py` flow instead of directly parsing the `observe`
    JSON
  - how to remove or structurally block that path rather than trying to steer
    it away with prompt wording alone
  - why the generic `image` tool still aborts on workspace-local media paths
    even though direct multimodal `data:image` chat works
  - whether the remote OpenClaw instance uses a newer image or different media
    / tool behavior than local `ghcr.io/openclaw/openclaw:2026.4.14`
