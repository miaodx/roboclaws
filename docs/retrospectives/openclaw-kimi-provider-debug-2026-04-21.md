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

## Follow-up

- Keep `custom + anthropic_kimi/k2.6` as the repo default
- Use `plugin + kimi/k2p5` for pinned-local Docker comparisons until the image
  is upgraded
- When debugging the custom path further, focus on:
  - why the Gateway image tool sees malformed/unsupported JPEG input
  - why it later falls back to `/tmp/fpv.jpg`
  - whether the remote OpenClaw instance uses a newer image or different media
    allowlist behavior
