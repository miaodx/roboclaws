# OpenClaw cold-start investigation (2026-04-28)

**Status:** Open. Ship-able portion landed in commit `bd5037b`. The remaining
~89s gap is documented and a follow-up investigation lane is described below.

## Versions under test

| Component | Version |
|---|---|
| Repo commit (HEAD at investigation time) | `bd5037b` (`perf: cut openclaw cold-start time-to-usable from 348s → 136s`) |
| Branch | `dongxu/dev-0427` (+9 ahead of `origin/dongxu/dev-0427`) |
| Gateway image tag | `ghcr.io/openclaw/openclaw:2026.4.25-beta.11` |
| Gateway image digest | `sha256:2f43456f4632668152076cc229f84a09057cf19cc90df5a0d219fb5512650e30` |
| Gateway image package version (`/app/package.json`) | `2026.4.25-beta.11` |
| Node inside image | `v24.14.0` |
| Host kernel | `Linux 6.17.0-20-generic` |
| Host Docker | `29.2.1` |
| Investigation host | local (Linux), real `KIMI_API_KEY` / `MIMO_TP_KEY` available, AI2-THOR resident, 1-agent appliance probe |

Re-run on a different host or different image tag will produce different
absolute timings; the *shape* of the breakdown (which phase dominates) is
what to compare across runs.

## What shipped (commit `bd5037b`)

Two independent fixes, both validated by live `just appliance::run` probe:

1. **Pricing-catalog blackhole.** `--add-host openrouter.ai:0.0.0.0,raw.githubusercontent.com:0.0.0.0`
   added to both `scripts/openclaw-bootstrap.sh` and `just/appliance.just`.
   Gateway hardcodes `FETCH_TIMEOUT_MS=60000` in `/app/dist/usage-format-*.js`
   and exposes no opt-out config. With the URLs unreachable both fetches
   return `ECONNREFUSED` immediately and the pricing layer falls through to
   `replaceGatewayModelPricingCache(new Map())`. Saves ~60s on cold start.

2. **`acpx.config.probeAgent` pinned to `agent_ids[0]`** instead of upstream
   default `codex` (which isn't installed). Required shape:
   `plugins.entries.<id>.{enabled: true, config: {…}}` — without
   `enabled: true` the entries-system warns "plugin disabled (bundled
   (disabled by default)) but config is present" and silently drops the
   config block. Pinned in both bootstrap paths plus regression tests.

### Probe result table from commit message (BEFORE / AFTER)

|                            |  Before  |  After   |      Saved      |
|----------------------------|----------|----------|-----------------|
| gateway ready              | +28s     | +21s     | 7s              |
| pricing fetch resolves     | +88s     | +21s     | 67s (fail-fast) |
| embedded ACPX registered   | +175s    | +110s    | 65s             |
| first chat.history success | +348s    | +136s    | 212s (62%)      |
| first chat.history latency | 53,043ms | 26,381ms | 27s             |

That's the user-visible win — appliance is usable in 136s instead of 348s.

## What remained: the ~89s gap from gateway-ready to ACPX-registered

After the two fixes above, the gap between `gateway ready` and
`embedded ACPX registered` was still ~89s. This investigation drills into
that gap.

### Method

Enabled `OPENCLAW_GATEWAY_STARTUP_TRACE=1` (the gateway emits one
`startup trace: <phase> <duration>ms total=<total>ms` line per phase).
The appliance image runs the gateway under supervisord with a hardcoded
env list, so we bind-mounted a tweaked `supervisord.conf`:

```
-v $(pwd)/.tmp/probe-trace/supervisord.conf:/opt/roboclaws/deploy/railway/supervisord.conf:ro
```

(Only change: `OPENCLAW_GATEWAY_STARTUP_TRACE="1"` appended to the
`[program:openclaw-gateway]` `environment=` line.)

Probe runner script: `.tmp/probe-trace/run.sh` (uncommitted).

### Result: per-phase breakdown (appliance, post-`bd5037b`, 1 agent, mimo provider)

| Phase | Duration | Cumulative |
|---|---|---|
| cli + config + auth | ~16s | 16.0s |
| `plugins.bootstrap` | **14.7s** | 15.6s |
| `http.bound` + `post-attach.log/update` | 0.6s | 16.2s |
| **`sidecars.session-locks`** | **65.0s** | 81.1s |
| `sidecars.gmail-watch` / `gmail-model` / `internal-hooks` | <1ms each | 81.1s |
| **`sidecars.channels`** (prewarm + startChannels) | **39.5s** | 120.6s |
| `sidecars.plugin-services` (incl. acpx register) | 11ms | 120.6s |
| `sidecars.memory` / `restart-sentinel` / `recovery` | <10ms each | 120.6s |
| **Total to `/readyz`=200** | | **120.6s** |

The `embedded acpx runtime backend registered` log line fires at the end
of `sidecars.plugin-services`, i.e. when the post-attach phase finishes
and the gateway is fully ready. The 89s in the user-visible table is
dominantly `sidecars.session-locks (65s) + sidecars.channels (39.5s)`,
not a single timeout.

### Standalone-vs-appliance comparison

Running the same image (`ghcr.io/openclaw/openclaw:2026.4.25-beta.11`)
**alone** with no appliance overhead and the same `OPENCLAW_GATEWAY_STARTUP_TRACE=1`:

| Phase | Standalone | Appliance | Δ |
|---|---|---|---|
| `plugins.bootstrap` | 43.0s | 14.7s | -28s (allow-list pin from commit `e596e62`) |
| **`sidecars.session-locks`** | **2.2ms** | **65,000ms** | **~30,000×** |
| `sidecars.channels` | 1.1ms | 39,500ms | (channels configured) |
| **Total ready** | **44.2s** | **120.6s** | +76s in appliance |

That `2.2ms → 65s` blowup on `sidecars.session-locks` is the surprise.
The cleanup work itself is the same on both runs: `cleanStaleLockFiles`
in `/app/dist/session-write-lock-CtSNXxG5.js` reads
`<stateDir>/agents/<id>/sessions/`, filters for `.jsonl.lock` entries, runs
`process.kill(pid, 0)` per lock. Both runs operate on **empty data**:

- The persistent docker volume `roboclaws-appliance-data` contains zero
  gateway lock files (only an unrelated AI2-THOR Unity download lock at
  `/data/home/.ai2thor/tmp/`).
- The gateway's actual `stateDir` is `/home/node/.openclaw` which is on
  the container layer, not the volume — fresh on every `docker run --rm`.
- Seed creates `agents/agent-0/agent/` and `agents/main/agent/` but no
  `sessions/` subdirectory, so `cleanStaleLockFiles` returns ENOENT and
  exits microseconds later.

So the 65,000ms is not the function body — it's a **65-second event-loop
pause inside the `measure()` window**, while the trivial `await` is
queued behind something else hogging the loop. The standalone gateway
proves the function itself runs in 2ms; the appliance proves something
in the parallel work starves it.

### What was ruled out

| Hypothesis | Verdict | Evidence |
|---|---|---|
| `channelConnectGraceMs=120s` is a startup gate | **Wrong.** | `channel-health-policy.ts` — it only suppresses the health-monitor's *restart* attempts during cold-start. The monitor doesn't run for the first `monitorStartupGraceMs=60s` then on a 5-min interval. Cannot cause boot-time latency. |
| Stale session locks accumulating in volume | **Wrong.** | Volume has 6MB total, zero gateway-related lock files. |
| Pricing fetch is on the session-locks critical path | **Wrong.** | `[model-pricing]` errors fire at +22s (8ms after sidecars start); the blackhole works. session-locks completes 65s later, independent. |
| Plugin manifest scan is the long pole | **Partially right** before the allow-list fix (43s standalone → 14.7s appliance), but **not the dominant remaining cost**. |

### What was NOT ruled out (open investigation)

- **Which parallel JS work is starving the event loop during `sidecars.session-locks`?**
  Plugin-auto-enable, agent-CLI sub-process spawn for the embedded ACP
  channel, sync model-catalog file writes (`ensureOpenClawModelsJson`),
  and channel-manager async setup all begin in this window. None has been
  isolated as the culprit yet.
- **Is the `sidecars.channels` 39.5s the structural floor or has slack?**
  This phase is `prewarmConfiguredPrimaryModel` + `startChannels()`. The
  prewarm path resolves the configured model and writes
  `~/.openclaw/.../models.json`. The `startChannels()` path spawns the
  embedded ACP channel. Either could plausibly shrink with image-level
  changes; from outside the image, the only visible knob is
  `OPENCLAW_SKIP_CHANNELS=1` (which would break chat — not useful).

## Reproduction recipe

Pin the versions at the top of this doc.

```bash
# 1. Tweaked supervisord.conf with trace env appended
mkdir -p .tmp/probe-trace
sed 's|OPENCLAW_AUTH_MODE="token"$|OPENCLAW_AUTH_MODE="token",OPENCLAW_GATEWAY_STARTUP_TRACE="1"|' \
  deploy/railway/supervisord.conf > .tmp/probe-trace/supervisord.conf

# 2. Run appliance with bind-mount
docker rm -f roboclaws-appliance-trace 2>/dev/null
docker run -d --rm --env-file .env \
  --name roboclaws-appliance-trace \
  -e PORT=8080 -e HOME=/data -e ROBOCLAWS_HOME=/data \
  -e DEMO_PASSWORD="${DEMO_PASSWORD:-demo}" \
  -p 8080:8080 \
  --add-host openrouter.ai:0.0.0.0 \
  --add-host raw.githubusercontent.com:0.0.0.0 \
  -v $(pwd)/.tmp/probe-trace/supervisord.conf:/opt/roboclaws/deploy/railway/supervisord.conf:ro \
  -v roboclaws-appliance-data:/data \
  -v "$HOME/.ai2thor:/data/.ai2thor" \
  roboclaws-appliance

# 3. Capture timestamped logs
docker logs -f --timestamps roboclaws-appliance-trace > .tmp/probe-trace/logs.txt 2>&1

# 4. Per-phase summary
grep "startup trace" .tmp/probe-trace/logs.txt
```

For the standalone-baseline comparison:

```bash
docker run --rm \
  -e PORT=18789 -e HOME=/home/node \
  -e OPENCLAW_AUTH_MODE=token -e OPENCLAW_TOKEN=demo \
  -e OPENCLAW_GATEWAY_STARTUP_TRACE=1 \
  -p 18789:18789 \
  --add-host openrouter.ai:0.0.0.0 \
  --add-host raw.githubusercontent.com:0.0.0.0 \
  ghcr.io/openclaw/openclaw:2026.4.25-beta.11 \
  node openclaw.mjs gateway --allow-unconfigured
```

## What remains

1. **Identify the JS work that starves the event loop during the 65s
   `sidecars.session-locks` window in the appliance.** Most direct path:
   run the appliance with `node --inspect` and capture a CPU profile
   covering `+22s` to `+87s` after gateway-process start. Estimated
   investment: 1–2 hours. Likely outcome: a specific synchronous code
   path (or a chain of dynamic imports) inside the gateway image that we
   can either avoid or report upstream.

2. **Decide whether the `sidecars.channels` 39.5s is structural.**
   Re-run with `OPENCLAW_SKIP_ACPX_RUNTIME=1` (skips embedded ACP plugin
   entirely) and observe the channels phase. If it drops to <5s, the
   embedded-ACP channel is the cost; otherwise the cost is in
   `prewarmConfiguredPrimaryModel` for the configured provider.

3. **File an upstream issue** if (1) finds a clear gateway-image bug.
   The standalone-vs-appliance traces in this doc are a self-contained
   reproducer; attach them.

4. **Diminishing-returns gate.** The 348s→136s win already shipped. Any
   further appliance cold-start work should answer "what user behavior
   does this enable that 136s doesn't?" before starting. This gap above
   exists primarily as breadcrumbs for the next person who hits an
   appliance cold-start regression and needs to re-establish a baseline.

## Probe artifacts

Uncommitted, in `.tmp/probe-trace/`:

- `supervisord.conf` — the tweaked supervisord with trace env
- `run.sh` — the bind-mount probe runner script
- `logs.txt` — full timestamped docker logs from the appliance probe run
- `gateway-only/logs.txt` — full timestamped docker logs from the
  standalone baseline run

These can be regenerated from the recipe above, but the captured logs
are the primary evidence for this note.
