# OpenClaw Demo Guide

Fastest path to the OpenClaw navigation demo:
[`examples/openclaw_demo.py`](../../../examples/openclaw_demo.py).

If you only want to prove "OpenClaw can drive the robot end-to-end", start
here. If you want the broader local matrix (territory, coverage, interactive
chat, autonomous MCP, provider/model comparisons), use
[`local.md`](local.md).

## Prerequisites

- Docker
- `xvfb-run`
- A repo-local `.env` or exported API key:
  - `KIMI_API_KEY` for Kimi
  - or `NV_API_KEY` for NVIDIA NIM
  - or `MIMO_TP_KEY` for MiMo
- AI2-THOR available in the repo environment

Recommended first-run prep:

```bash
cd /home/mi/ws/gogo/roboclaws
uv pip install -e ".[dev,openclaw]"
.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"
```

## One-Shot Demo

This is the shortest route. It bootstraps the Gateway, runs the CI-parity
navigation smoke (`2` agents, `10` steps), and tears the Gateway down when
the run ends. The justfile auto-loads repo-local `.env` if present.

```bash
cd /home/mi/ws/gogo/roboclaws
just openclaw::run nav
```
`just openclaw::run nav` is the canonical command.

Artifacts for the default `just openclaw::run nav` recipe:

- `output/openclaw/nav/replay.gif`
- `output/openclaw/nav/report.html`

The CI/manual examples below still pass `--output-dir output/openclaw/demo`
explicitly, so those runs write to `output/openclaw/demo/`.

## Manual Flow

Use this when you want to control the provider explicitly, run longer than the
smoke target, or keep the bearer token around for repeated runs.

### 1. Bootstrap the Gateway

Kimi:

```bash
cd /home/mi/ws/gogo/roboclaws
set -a && source .env && set +a
docker rm -f openclaw-gateway 2>/dev/null || true
TOKEN=$(PROVIDER=kimi AGENTS=2 ./scripts/openclaw-bootstrap.sh)
```

NVIDIA:

```bash
cd /home/mi/ws/gogo/roboclaws
set -a && source .env && set +a
docker rm -f openclaw-gateway 2>/dev/null || true
TOKEN=$(PROVIDER=nvidia AGENTS=2 ./scripts/openclaw-bootstrap.sh)
```

MiMo direct vision:

```bash
cd /home/mi/ws/gogo/roboclaws
set -a && source .env && set +a
docker rm -f openclaw-gateway 2>/dev/null || true
TOKEN=$(PROVIDER=mimo MODEL=mimo_openai/mimo-v2-omni AGENTS=2 ./scripts/openclaw-bootstrap.sh)
```

`openclaw_demo.py` sends images directly in the chat-completions turn, so the
main model still needs image support here. Text-only MiMo variants such as
`mimo-v2.5-pro` belong in the autonomous MCP path, not this demo path.

### 2. Run the Demo

```bash
cd /home/mi/ws/gogo/roboclaws
OPENCLAW_GATEWAY_TOKEN="$TOKEN" \
  xvfb-run -a python examples/openclaw_demo.py \
  --agents 2 \
  --steps 20 \
  --output-dir output/openclaw/demo
```

Then open `output/openclaw/demo/report.html`.

### 3. Clean Up

```bash
docker rm -f openclaw-gateway
docker volume rm openclaw-gateway-config
```

## What Good Looks Like

- `report.html` loads and shows per-step first-person frames
- `replay.gif` shows visible movement
- the run writes `replay.json` under `output/openclaw/demo/`

## Troubleshooting

Port already in use:

```bash
ss -ltnp '( sport = :18788 or sport = :18789 )'
docker rm -f openclaw-gateway 2>/dev/null || true
```

No key loaded:

```bash
set -a && source .env && set +a
env | rg 'KIMI_API_KEY|NV_API_KEY|MIMO_TP_KEY'
```

First run is slow:

- AI2-THOR may download a Unity build (~1 GB)
- Docker may need to pull `ghcr.io/openclaw/openclaw:2026.4.14`

## Next Steps

- Longer OpenClaw game demos: `just openclaw::run territory`, `just openclaw::run coverage`
- Full local guide: [`local.md`](local.md)
- Autonomous MCP loop and split-model MiMo: `python examples/openclaw_nav_autonomous.py ...`
