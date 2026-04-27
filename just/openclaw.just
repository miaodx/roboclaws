# OpenClaw Gateway recipes — bootstrap → run → teardown.
#
# Smoke recipes (nav, territory, coverage) cap at 60 steps and are the
# CI-parity confidence check. Probe recipes (probe-*) cap at 200 steps with
# a 60-min wall budget — used to gather real review artifacts.
#
# `gateway-up` / `gateway-down` are the lifecycle escape hatch when you want
# to drive several runs against one long-lived gateway and skip the ~30s
# bootstrap each time.

set working-directory := '..'

strip_ros_env := "env -u PYTHONPATH -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH -u ROS_DISTRO -u ROS_VERSION"

# Default: list module recipes (avoids accidentally booting a Gateway).
default:
    @just --list openclaw

# Ensure the configured OpenClaw Gateway image is present in local Docker cache.
# Useful if you want a fast first bootstrap in a tight loop.
[group('gateway')]
pull-image:
    #!/usr/bin/env bash
    set -euo pipefail

    OPENCLAW_DEFAULT_IMAGE="$(awk -F= '$1=="OPENCLAW_IMAGE_DEFAULT"{print $2}' scripts/openclaw-defaults.env | tr -d '"')"
    if [[ -z "$OPENCLAW_DEFAULT_IMAGE" ]]; then
      echo "error: missing OPENCLAW_IMAGE_DEFAULT in scripts/openclaw-defaults.env" >&2
      exit 1
    fi

    OPENCLAW_IMG="${OPENCLAW_IMG:-${IMAGE:-${OPENCLAW_IMAGE:-$OPENCLAW_DEFAULT_IMAGE}}}"

    if ! command -v docker >/dev/null 2>&1; then
      echo "error: docker not found in PATH" >&2
      exit 1
    fi

    if ! docker image inspect "$OPENCLAW_IMG" >/dev/null 2>&1; then
      echo "==> pulling $OPENCLAW_IMG"
      docker pull "$OPENCLAW_IMG"
    else
      echo "==> already cached: $OPENCLAW_IMG"
    fi

# ---------------------------------------------------------------------------
# Smoke runs (60 steps, fresh gateway each time)
# ---------------------------------------------------------------------------

# Navigation demo (2 agents, 10 steps, CI-parity smoke).
[group('smoke')]
nav:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Bootstrapping Gateway for nav demo …"
    TOKEN=$(./scripts/openclaw-bootstrap.sh)
    echo "==> Running navigation demo …"
    OPENCLAW_GATEWAY_TOKEN=$TOKEN xvfb-run -a python examples/openclaw_demo.py \
      --agents 2 --steps 10 --output-dir output/openclaw/demo
    echo "==> Stopping Gateway …"
    docker rm -f openclaw-gateway || true
    echo "==> Done. Report: output/openclaw/demo/report.html"

# Territory game (2 agents, 60 steps, aggressive vs defensive).
[group('smoke')]
territory:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Bootstrapping Gateway for territory game (aggressive vs defensive) …"
    TOKEN=$(AGENTS=2 AGENT_SOULS=aggressive,defensive ./scripts/openclaw-bootstrap.sh)
    echo "==> Running territory game …"
    OPENCLAW_GATEWAY_TOKEN=$TOKEN AGENT_SOULS=aggressive,defensive \
      xvfb-run -a python examples/territory_game.py \
      --backend openclaw --agents 2 --steps 60 \
      --output-dir output/openclaw/territory
    echo "==> Stopping Gateway …"
    docker rm -f openclaw-gateway || true
    echo "==> Done. Report: output/openclaw/territory/report.html"

# Coverage game (2 cooperative agents, 60 steps).
[group('smoke')]
coverage:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Bootstrapping Gateway for coverage game (cooperative) …"
    TOKEN=$(AGENTS=2 AGENT_SOULS=cooperative,cooperative PERSONALITY_PROBE=0 ./scripts/openclaw-bootstrap.sh)
    echo "==> Running coverage game …"
    OPENCLAW_GATEWAY_TOKEN=$TOKEN AGENT_SOULS=cooperative,cooperative \
      xvfb-run -a python examples/coverage_game.py \
      --backend openclaw --agents 2 --steps 60 \
      --output-dir output/openclaw/coverage
    echo "==> Stopping Gateway …"
    docker rm -f openclaw-gateway || true
    echo "==> Done. Report: output/openclaw/coverage/report.html"

# ---------------------------------------------------------------------------
# Probes (200 steps, 60-min wall, real review artifacts)
# ---------------------------------------------------------------------------

# Long-running navigation probe (200 steps, auto-convergence).
[group('probe')]
probe-nav:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Bootstrapping Gateway for 200-step nav probe …"
    TOKEN=$(PROVIDER=kimi AGENTS=2 ./scripts/openclaw-bootstrap.sh)
    [ -n "$TOKEN" ] || { echo "bootstrap failed — no token"; exit 1; }
    echo "==> Running navigation demo (200 steps, auto-convergence) …"
    {{strip_ros_env}} OPENCLAW_GATEWAY_TOKEN=$TOKEN PYTHONUNBUFFERED=1 \
      xvfb-run -a python examples/openclaw_demo.py \
      --agents 2 --steps 200 \
      --output-dir output/openclaw-probe/nav
    echo "==> Stopping Gateway …"
    docker rm -f openclaw-gateway || true
    docker volume rm openclaw-gateway-config || true
    echo "==> Done. Report: output/openclaw-probe/nav/report.html"

# Long-running territory probe (200 steps, 60-min wall).
[group('probe')]
probe-territory:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Bootstrapping Gateway for 200-step territory probe …"
    TOKEN=$(PROVIDER=kimi AGENTS=2 AGENT_SOULS=aggressive,defensive ./scripts/openclaw-bootstrap.sh)
    [ -n "$TOKEN" ] || { echo "bootstrap failed — no token"; exit 1; }
    echo "==> Running territory game (200 steps, 60-min wall) …"
    {{strip_ros_env}} OPENCLAW_GATEWAY_TOKEN=$TOKEN AGENT_SOULS=aggressive,defensive PYTHONUNBUFFERED=1 \
      xvfb-run -a python examples/territory_game.py \
      --backend openclaw --agents 2 --steps 200 --max-wall-seconds 3600 \
      --output-dir output/openclaw-probe/territory
    echo "==> Stopping Gateway …"
    docker rm -f openclaw-gateway || true
    docker volume rm openclaw-gateway-config || true
    echo "==> Done. Report: output/openclaw-probe/territory/report.html"

# Long-running coverage probe (200 steps, 60-min wall).
[group('probe')]
probe-coverage:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Bootstrapping Gateway for 200-step coverage probe …"
    TOKEN=$(PROVIDER=kimi AGENTS=2 AGENT_SOULS=cooperative,cooperative PERSONALITY_PROBE=0 ./scripts/openclaw-bootstrap.sh)
    [ -n "$TOKEN" ] || { echo "bootstrap failed — no token"; exit 1; }
    echo "==> Running coverage game (200 steps, 60-min wall) …"
    {{strip_ros_env}} OPENCLAW_GATEWAY_TOKEN=$TOKEN AGENT_SOULS=cooperative,cooperative PYTHONUNBUFFERED=1 \
      xvfb-run -a python examples/coverage_game.py \
      --backend openclaw --agents 2 --steps 200 --max-wall-seconds 3600 \
      --output-dir output/openclaw-probe/coverage
    echo "==> Stopping Gateway …"
    docker rm -f openclaw-gateway || true
    docker volume rm openclaw-gateway-config || true
    echo "==> Done. Report: output/openclaw-probe/coverage/report.html"

# Self-bootstraps the Gateway via examples/openclaw_photo_task.py — no
# `gateway-up` needed beforehand.
# Photograph-each-chair task (single agent, FloorPlan201, ~15 min wall budget).
[group('probe')]
photo:
    #!/usr/bin/env bash
    set -euo pipefail
    RUN_DIR="output/openclaw-photo-task/$(date +%Y%m%d%H%M)"
    echo "==> Photo-task smoke (single agent, FloorPlan201, ~15 min wall budget)"
    {{strip_ros_env}} PROVIDER=kimi PYTHONUNBUFFERED=1 \
      xvfb-run -a python examples/openclaw_photo_task.py \
      --output-dir "$RUN_DIR" \
      --max-moves 200 --wall-budget 900
    echo "==> Scoring with check_photo_task.py …"
    {{strip_ros_env}} python scripts/check_photo_task.py --run-dir "$RUN_DIR"

# ---------------------------------------------------------------------------
# Gateway lifecycle (use to run several probes against one long-lived gateway)
# ---------------------------------------------------------------------------

# Bootstrap a gateway and write the token to .openclaw-token.
[group('gateway')]
gateway-up:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "==> Bootstrapping gateway (2 agents, Kimi, TIMEOUT_SECONDS=600) …"
    PROVIDER=kimi AGENTS=2 ./scripts/openclaw-bootstrap.sh > .openclaw-token
    echo "==> Token saved to .openclaw-token"
    echo ""
    echo "Next steps:"
    echo "  export OPENCLAW_GATEWAY_TOKEN=\$(cat .openclaw-token)"
    echo "  source .venv/bin/activate"
    echo "  {{strip_ros_env}} PYTHONUNBUFFERED=1 python examples/territory_game.py \\"
    echo "    --backend openclaw --agents 2 --steps 200 --max-wall-seconds 3600 \\"
    echo "    --output-dir output/territory-probe"

# Tear down the gateway + volume + token file.
[group('gateway')]
gateway-down:
    @echo "==> Tearing down gateway …"
    -docker rm -f openclaw-gateway
    -docker volume rm openclaw-gateway-config
    -rm -f .openclaw-token
    @echo "==> Done."
