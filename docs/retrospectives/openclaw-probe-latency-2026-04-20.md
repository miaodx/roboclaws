# OpenClaw coverage probe latency note (2026-04-20)

**Date:** 2026-04-20

**Code commit under test:** `51be7bdd4d57236619227c5831cbbbc6a0e160e7`
(`feat: add probe latency telemetry`)

**Primary command:** `make openclaw-probe-coverage`

**Artifacts:**
- Replay: `output/openclaw-probe/coverage/replay.json`
- Saved frames: `output/openclaw-probe/coverage/agent_frames/` and
  `output/openclaw-probe/coverage/overhead/`

## Result

The probe completed successfully:

- Termination: `coverage_reached`
- Steps: `73`
- Duration: `3099.75s`
- Provider summary: `calls=73 ok=73 retry=2 transient=2 fail=0`

## Timing split

From `replay.json` per-turn telemetry:

- Total provider-call time: `3040.03s`
- Mean provider-call time: `41.64s`
- Median provider-call time: `33.02s`
- P95 provider-call time: `69.82s`
- Total retry delay: `4.0s`
- Total map render time: `0.57s`
- Total action execution time: `42.77s`
- Total step-loop time: `3083.45s`

## What this means

The run is bottlenecked by provider latency, not by local game-loop work.

- Prompt/image preparation is negligible.
- AI2-THOR action execution is visible but small relative to provider time.
- Retry backoff exists, but it is not the dominant source of wall-clock.

Typical payload size during the run was modest:

- Images: about `20-24 KB` JPEG total per turn
- Base64 image payload: about `27-32 KB` total per turn
- State JSON: about `2.1-2.3 KB` per turn

That is not large enough to explain `20-70s` turns by itself.

## Replay A/B diagnostics

After the probe, the saved turns were replayed through the live Gateway and
through the direct `kimi-coding` provider path.

### OpenClaw Gateway replay

- `PING`: `2.36s`
- Step `0`: `21.79s`
- Step `19`: `32.40s`
- Step `72`: `24.69s`

### Direct `kimi-coding` replay

With a strict single-attempt `45s` timeout:

- Text-only state: timed out at `45.44s`, returned fallback action
- Full payload: timed out at `45.39s`, returned fallback action

## Important outlier interpretation

The worst in-game turn was step `19`:

- In-game provider-call time: `225.13s`
- Replay of the same saved OpenClaw payload: `32.40s`

This strongly suggests the huge in-game spike was a transient upstream failure
plus retry path, not a heavy payload and not local loop overhead.

## Bottom line

On this 2026-04-20 run, the evidence supports:

1. The main bottleneck is upstream model latency inside provider calls.
2. Rare extreme stalls are caused by transient upstream failures and retry
   behavior.
3. Payload size and local render/encode work are secondary.
4. In this environment, the OpenClaw Gateway path outperformed the direct
   `kimi-coding` path on the same saved turn.

This note is intended to preserve the result so future work can optimize
timeout/retry policy or prompt shape without rerunning the full probe just to
re-establish the baseline.
