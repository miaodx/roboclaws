# OpenClaw Gateway Local Quick Start

Use this path for local OpenClaw navigation demos. Normal users configure keys
only; command shape controls behavior.

## Prerequisites

- Docker (Linux: rootless or regular; macOS: Docker Desktop).
- A clone of `roboclaws` with the `skills/ai2thor-navigator/` directory
  present.
- A repo-local `.env` copied from `.env.example`.

Fill at least one provider key in `.env`:

```bash
KIMI_API_KEY=
MIMO_TP_KEY=
NV_API_KEY=
```

## Run

Install dependencies once:

```bash
uv sync --extra dev --extra openclaw
```

Check the network guard before starting the Gateway:

```bash
just dev::network-status
```

If the command reports `network: work`, do not run the OpenClaw Gateway path
from that network.

Start the navigation demo through the public surface/intent grammar:

```bash
just run::surface surface=ai2thor-world world=ai2thor/FloorPlan201 backend=ai2thor intent=navigate agent_engine=openclaw-gateway report=visual
```

The run writes a reviewable report under `output/openclaw/` and prints the
exact artifact path.

## Cleanup

After a run, either leave the Gateway in its minimal profile or tear it down:

```bash
docker rm -f openclaw-gateway
```

## Maintainer Details

The low-level bootstrap script, provider/model curation, Gateway config shape,
and Docker/image overrides are maintainer internals. See
[`gateway-internals.md`](gateway-internals.md) when changing
`scripts/openclaw/openclaw-bootstrap.sh` or the OpenClaw bridge.
