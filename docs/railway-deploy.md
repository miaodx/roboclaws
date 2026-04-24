# Railway Deployment Runbook

This runbook deploys the single-container Roboclaws appliance to Railway.
The appliance runs OpenClaw webchat, Roboclaws MCP, AI2-THOR, the three-view
HTML viewer, Xvfb, and nginx in one Railway service.

Public routes:

- `/` - OpenClaw Control UI / webchat, behind basic auth
- `/views/` - Roboclaws FPV + map-v2 + chase-cam viewer
- `/health` - unauthenticated Railway healthcheck

## Before Deploying

From a local checkout, validate the image once:

```bash
make appliance-build
DEMO_PASSWORD=demo make appliance-run-local
```

Then open:

- `http://127.0.0.1:8080/health`
- `http://127.0.0.1:8080/`
- `http://127.0.0.1:8080/views/`

For local appliance chat logs:

```bash
make appliance-tail
```

`make appliance-run-local` reuses the host `$HOME/.ai2thor` cache by mounting
it into container `/data/.ai2thor`, so it should not redownload the AI2-THOR
Unity build if `make chat` already downloaded it.

## Railway Setup

1. Push the branch you want to deploy to GitHub.

2. In Railway, create a new project from the GitHub repo.

3. Select the repo root as the service root. The repo already includes:

   ```toml
   [build]
   dockerfilePath = "Dockerfile.railway"

   [deploy]
   healthcheckPath = "/health"
   healthcheckTimeout = 300
   restartPolicyType = "ON_FAILURE"
   ```

   Railway should therefore build `Dockerfile.railway` automatically through
   config-as-code. If the dashboard does not pick it up, set service variable
   `RAILWAY_DOCKERFILE_PATH=Dockerfile.railway`.

4. Add a Railway volume to the service.

   Mount path:

   ```text
   /data
   ```

   This persists:

   - `/data/.ai2thor` - AI2-THOR Unity release cache
   - `/data/runs/current` - traces and viewer snapshots
   - `/data/appliance/runtime.env` - generated runtime handoff env

5. Add service variables.

   Required:

   ```bash
   DEMO_PASSWORD=<shared-basic-auth-password>
   MIMO_TP_KEY=<mimo-provider-key>
   ```

   Optional:

   ```bash
   DEMO_USERNAME=demo
   OPENCLAW_TOKEN=<separate-openclaw-bearer-token>
   PROVIDER=mimo
   MODEL=mimo_openai/mimo-v2-omni
   IMAGE_MODEL=mimo_openai/mimo-v2-omni
   ROBOCLAWS_OBSERVE_MODE=auto
   ```

   Do not set `PORT` unless debugging Railway networking. Railway provides
   `PORT`, and nginx listens on that value.

6. Deploy the service.

7. Generate a public domain:

   Service -> Settings -> Networking -> Public Networking -> Generate Domain

8. Open the deployed app.

   ```text
   https://<railway-domain>/health
   https://<railway-domain>/
   https://<railway-domain>/views/
   ```

## Login And Tokens

Basic auth username:

```text
demo
```

Override it with `DEMO_USERNAME` if needed.

Credential behavior:

- `DEMO_PASSWORD` only:
  - basic auth username = `DEMO_USERNAME` or `demo`
  - basic auth password = `DEMO_PASSWORD`
  - OpenClaw bearer token = `DEMO_PASSWORD`

- `OPENCLAW_TOKEN` only:
  - basic auth username = `DEMO_USERNAME` or `demo`
  - basic auth password = `OPENCLAW_TOKEN`
  - OpenClaw bearer token = `OPENCLAW_TOKEN`

- both:
  - basic auth username = `DEMO_USERNAME` or `demo`
  - basic auth password = `DEMO_PASSWORD`
  - OpenClaw bearer token = `OPENCLAW_TOKEN`

- neither:
  - container exits immediately with `ERROR: set DEMO_PASSWORD or OPENCLAW_TOKEN`

In the OpenClaw UI, paste the bearer token on the Overview tab, then open the
Chat tab and select `agent-0`.

## Expected First Boot Behavior

The first real AI2-THOR startup downloads a Linux Unity build, for example:

```text
thor-Linux64-f0825767cd50d69f666c7f282e54abfe58f1e917.zip ... of 769.MB
```

That is the AI2-THOR Unity player build, not a scene file. With the `/data`
volume mounted, it is cached at `/data/.ai2thor` and should survive restarts
and redeploys.

The app can pass `/health` before AI2-THOR has finished downloading and
starting. Use deployment logs to confirm the `roboclaws-interactive` process
has entered `RUNNING` and the banner shows the Railway public URL.

## Troubleshooting

### Build Does Not Use The Railway Dockerfile

Check that `railway.toml` is in the service root. If needed, set:

```bash
RAILWAY_DOCKERFILE_PATH=Dockerfile.railway
```

### Healthcheck Fails

Confirm nginx is listening on Railway's `PORT`. Do not hardcode `PORT` in the
Railway variables unless intentionally debugging. The repo config uses:

```toml
healthcheckPath = "/health"
healthcheckTimeout = 300
```

### AI2-THOR Redownloads Every Deploy

Confirm the Railway volume is mounted at `/data`. AI2-THOR resolves its cache
from `HOME`; the appliance sets `HOME=/data`, so the cache path is
`/data/.ai2thor`.

### The Viewer Is Blank

Open `/views/` and ask the chat agent to observe, for example:

```text
show me what you see
```

The viewer updates after `roboclaws__observe` writes
`latest.fpv.png`, `latest.map.png`, and `latest.chase.png` under the run
snapshot directory.

### `make chat-tail` Fails Locally

`make chat-tail` is for the standalone `make chat` Gateway container named
`openclaw-gateway`.

For the appliance container, use:

```bash
make appliance-tail
```

On Railway, inspect the service deployment logs instead.

## Local Target Summary

Use these when validating before pushing:

```bash
make appliance-build
DEMO_PASSWORD=demo make appliance-run-local
make appliance-tail
```

Use this only when you explicitly want local `/data` parity with Railway:

```bash
DEMO_PASSWORD=demo make appliance-run-railway
```

`make appliance-run-railway` bind-mounts host `/data` into container `/data`.
If that path is inconvenient, override it:

```bash
DEMO_PASSWORD=demo make appliance-run-railway APPLIANCE_RAILWAY_DATA_DIR=/path/to/data
```

## References

- Railway Dockerfile builds and custom Dockerfile paths:
  https://docs.railway.com/builds/dockerfiles
- Railway public networking and `PORT`:
  https://docs.railway.com/public-networking
- Railway variables and `RAILWAY_PUBLIC_DOMAIN`:
  https://docs.railway.com/reference/variables
- Railway volumes:
  https://docs.railway.com/volumes
- Railway healthchecks:
  https://docs.railway.com/deployments/healthchecks
