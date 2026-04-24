# Railway OpenClaw Appliance Plan

Operator runbook: [`railway-deploy.md`](railway-deploy.md).

## Summary

Ship a single-instance Railway demo that runs the existing OpenClaw webchat and
Roboclaws three-view viewer from one container. This is a parity deployment
path, not a replacement for the current local workflow.

The public Railway service exposes:

- `/` - OpenClaw Control UI / webchat, protected by shared basic auth
- `/views/` - live Roboclaws FPV + map-v2 + chase-cam viewer
- `/health` - unauthenticated Railway healthcheck

The container runs one AI2-THOR session and one OpenClaw agent (`agent-0`) at a
time. The first version uses a shared session rather than per-user isolation.

## Architecture

Use `supervisord` to keep all long-running processes alive:

```text
supervisord
|-- Xvfb :99
|-- OpenClaw Gateway              127.0.0.1:18789
|-- Roboclaws MCP + AI2-THOR      127.0.0.1:18788
|-- 3-view snapshot viewer        127.0.0.1:8787
`-- nginx public proxy             0.0.0.0:$PORT
```

Why this shape:

- Gateway, MCP, viewer, and Xvfb are separate long-running processes; FastAPI
  would become a custom supervisor if it tried to own them.
- nginx is enough for the v1 public front door: route traffic, enforce a shared
  password, proxy WebSockets/SSE, and serve `/health`.
- A custom Python API can be added later if we need reset buttons, per-user
  locks, or richer session state.

## Implementation Changes

- Add `Dockerfile.railway` based on `ghcr.io/openclaw/openclaw:2026.4.14`.
  It installs Python, Xvfb/Mesa software rendering, nginx, supervisor, Apache
  htpasswd tooling, and uses `uv sync --frozen --no-dev --extra openclaw` from
  the checked-in `uv.lock` for Roboclaws dependencies.
- Add `deploy/railway/entrypoint.sh` to prepare runtime directories, seed
  OpenClaw config, generate nginx basic auth, and launch supervisord.
- Add `scripts/appliance_seed_openclaw.py` to seed `/home/node/.openclaw`
  directly. It replaces local-dev `scripts/openclaw-bootstrap.sh` for this
  appliance path because nested Docker is not available on Railway.
- Add `deploy/railway/supervisord.conf` and `deploy/railway/nginx.conf.template`.
- Add `scripts/appliance-run-interactive.sh` as the supervised Roboclaws
  process wrapper.
- Add `railway.toml` and `.dockerignore`.
- Add Make targets for local parity:
  `make appliance-build`, `make appliance-run-local`, and
  `make appliance-run-railway`.
- Add `make appliance-tail` as the appliance equivalent of `make chat-tail`.
  `make chat-tail` remains scoped to the standalone `make chat` Gateway
  container named `openclaw-gateway`.

## Runtime Configuration

Required env vars:

- `DEMO_PASSWORD` - shared basic-auth password; also becomes the OpenClaw UI
  bearer token unless `OPENCLAW_TOKEN` is explicitly set
- `MIMO_TP_KEY` - default MiMo provider key

Defaults:

- `DEMO_USERNAME=demo`
- `PROVIDER=mimo`
- `MODEL=mimo_openai/mimo-v2-omni`
- `ROBOCLAWS_TOOL_PROFILE=minimal`
- `ROBOCLAWS_MCP_URL=http://127.0.0.1:18788/mcp`
- `ROBOCLAWS_HOME=/data`
- `HOME=/data` for the supervised Roboclaws process, which makes AI2-THOR
  store Unity releases under `/data/.ai2thor`
- `ROBOCLAWS_RUN_DIR=/data/runs/current`
- `ROBOCLAWS_SNAPSHOTS_DIR=/data/runs/current/snapshots`

Optional provider overrides remain available for local probing:

- `PROVIDER=kimi` with `KIMI_API_KEY`
- `PROVIDER=nvidia` with `NV_API_KEY` or `NVIDIA_API_KEY`

## Validation

Local parity smoke:

```bash
make appliance-build
DEMO_PASSWORD=demo make appliance-run-local
```

The local appliance target bind-mounts the host `$HOME/.ai2thor` cache into
container `/data/.ai2thor`, so it reuses the same AI2-THOR Unity build as the
normal host-side `make chat` workflow without requiring a host `/data`
directory.

Railway-shape smoke:

```bash
make appliance-build
DEMO_PASSWORD=demo make appliance-run-railway
```

`make appliance-run-railway` bind-mounts host `/data` into container `/data`
and runs with `HOME=/data`, matching Railway's runtime shape. Its AI2-THOR
cache resolves to `/data/.ai2thor`. Override the host path with
`make appliance-run-railway APPLIANCE_RAILWAY_DATA_DIR=/path/to/data` if
needed.

Then verify:

- `http://localhost:8080/health` returns `ok`
- `http://localhost:8080/` shows OpenClaw Control UI after basic auth
- the Control UI accepts bearer token `demo` when `OPENCLAW_TOKEN` is unset
- `http://localhost:8080/views/` shows the three-panel viewer
- after `agent-0` calls `roboclaws__observe`, FPV/map/chase images refresh
- `make appliance-tail` tails the Gateway session JSONL from the appliance
  container

Automated checks:

- Seeded `openclaw.json` includes loopback MCP, one minimal-profile agent, and
  the expected provider model config.
- Seeded workspace has a snapshots symlink from the Gateway workspace to the
  `/data` run directory.
- Dockerfile/config files pass static checks and the new Python seeder tests.

## Assumptions

- Railway runs one replica for this demo.
- A Railway volume is mounted at `/data` so `/data/.ai2thor` and run artifacts
  can survive restarts.
- CPU Xvfb + Mesa llvmpipe is acceptable for low-concurrency debugging. If the
  live UX is too slow after real model latency is included, move the simulator
  worker to a GPU host and keep the public UI thin.
- The current local Docker bootstrap remains the preferred day-to-day developer
  workflow; the appliance is for Railway parity and hosted bug reproduction.
