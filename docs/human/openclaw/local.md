# OpenClaw Gateway Local Quick Start

OpenClaw remains a local/maintainer route for household MCP runs. It is not a
separate public robot surface; use it as an agent engine for
`surface=household-world` when you need Gateway behavior.

Current status: validation-required. The household OpenClaw path is kept for
maintainer use, but the current household-world contract has not been recently
proved off the work network. Treat the route as degraded until a dated
off-work-network Gateway run produces a cleanup report and trace.

## Prerequisites

- Docker.
- A repo-local `.env` copied from `.env.example`.
- A host-side household MCP server URL, usually
  `http://host.docker.internal:18788/mcp`.

Fill at least one supported provider key:

```bash
KIMI_API_KEY=
MIMO_TP_KEY=
NV_API_KEY=
```

Check the network guard before starting the Gateway:

```bash
just dev::network-status
```

If it reports `network: work`, do not run the OpenClaw Gateway path from that
network.

## Run A Household Cleanup Route

The validation-required route shape is:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=openclaw-gateway evidence_lane=world-oracle-labels
```

For lower-level Gateway debugging, start the household MCP server and then the
Gateway:

```bash
just agent::mcp up household-world.cleanup 127.0.0.1 18788 output/openclaw/household-mcp
export ROBOCLAWS_MCP_URL=http://host.docker.internal:18788/mcp
just openclaw::gateway up
```

The bootstrap mounts `skills/molmo-realworld-cleanup` by default and seeds the
Gateway with the Roboclaws MCP server before first start.

## Cleanup

After a run, either leave the Gateway in its minimal profile for a follow-up or
tear it down:

```bash
just openclaw::gateway down
just mcp::down
```

## Maintainer Details

The low-level bootstrap script, provider/model curation, plugin allow-list,
Gateway config shape, and Docker/image overrides are maintainer internals. See
[`gateway-internals.md`](gateway-internals.md) when changing
`scripts/openclaw/openclaw-bootstrap.sh` or the OpenClaw Gateway setup.
