# Makefile — convenience targets for common local workflows.
# Requires: docker, xvfb-run, KIMI_API_KEY (or NV_API_KEY) in environment
# OR in a project-local `.env` file (auto-sourced by the openclaw-* targets).

.PHONY: openclaw-nav openclaw-territory openclaw-coverage \
        openclaw-probe-nav openclaw-probe-territory openclaw-probe-coverage \
        openclaw-gateway-up openclaw-gateway-down \
        appliance-build appliance-run \
        chat chat-xvfb chat-reuse chat-tail chat-view chat-clean \
        chat-plugin chat-nvidia \
        chat-mimo-pro chat-mimo chat-kimi \
        chat-plugin-kimi chat-plugin-mimo-pro \
        kimi-territory kimi-coverage \
        install-hooks uninstall-hooks test-fast test-integration \
        help

# Shell-side hygiene shared by every openclaw-* recipe:
#   - auto-source .env (if present) so KIMI_API_KEY is available without
#     the caller having to remember `set -a; source .env; set +a`
#   - strip ROS env vars that shadow the venv's Python + confuse pytest/pip
#     (machine-local feedback: `/opt/ros/jazzy/` hijacks sys.path otherwise)
#   - PYTHONUNBUFFERED so progress prints stream live through `| tee`
SOURCE_ENV := set -a; [ -f .env ] && . ./.env; set +a
STRIP_ROS_ENV := env -u PYTHONPATH -u AMENT_PREFIX_PATH -u COLCON_PREFIX_PATH -u ROS_DISTRO -u ROS_VERSION

help:
	@echo "OpenClaw ephemeral targets (bootstrap + run + teardown in one shot):"
	@echo "  make openclaw-nav        — navigation demo (2 agents, 10 steps, CI-parity smoke)"
	@echo "  make openclaw-territory  — territory game  (2 agents, 60 steps, aggressive/defensive)"
	@echo "  make openclaw-coverage   — coverage game   (2 agents, 60 steps, cooperative)"
	@echo ""
	@echo "OpenClaw long-running probes (200 steps, 60-min wall budget, real review artifacts):"
	@echo "  make openclaw-probe-nav        — openclaw_demo 200-step run"
	@echo "  make openclaw-probe-territory  — territory 200-step run"
	@echo "  make openclaw-probe-coverage   — coverage 200-step run"
	@echo ""
	@echo "OpenClaw gateway lifecycle (use to run multiple probes against one gateway):"
	@echo "  make openclaw-gateway-up       — bootstrap gateway, save token to .openclaw-token"
	@echo "  make openclaw-gateway-down     — tear down gateway + volume"
	@echo "  (then:  export OPENCLAW_GATEWAY_TOKEN=\$$(cat .openclaw-token)  &&  run demos)"
	@echo ""
	@echo "Railway appliance parity:"
	@echo "  make appliance-build           — build the all-in-one Railway image"
	@echo "  make appliance-run             — run it locally at http://localhost:8080"
	@echo ""
	@echo "Interactive chat (you drive the agent from the Control UI in a browser):"
	@echo "  Direct-vision (main model handles images):"
	@echo "      make chat              — MiMo V2 Omni (default)"
	@echo "      make chat-kimi         — Kimi custom (anthropic-messages)"
	@echo "      make chat-nvidia       — NVIDIA NIM (nemotron)"
	@echo "  Split-model bridge (text main + omni vision bridge):"
	@echo "      make chat-mimo-pro     — MiMo V2.5 Pro + V2 Omni bridge"
	@echo "      make chat-mimo         — MiMo V2.5 + V2 Omni bridge"
	@echo "  Anthropic/plugin API path:"
	@echo "      make chat-plugin           — default model, plugin path"
	@echo "      make chat-plugin-kimi      — Kimi stock plugin"
	@echo "      make chat-plugin-mimo-pro  — MiMo V2.5 Pro anthropic path"
	@echo "  Session control:"
	@echo "      make chat-clean        — wipe Gateway session history, then start"
	@echo "      make chat-reuse        — attach to an already-running Gateway"
	@echo "      make chat-xvfb         — remote/headless chat using Xvfb"
	@echo "  Monitoring (run in separate terminals while chat is live):"
	@echo "      make chat-tail         — pretty-tail Gateway session JSONL"
	@echo "      make chat-view         — live snapshot viewer at http://127.0.0.1:8787"
	@echo "  Custom flags: python examples/openclaw_interactive.py --help"
	@echo ""
	@echo "Direct Kimi targets (no Gateway — talks to Kimi anthropic endpoint):"
	@echo "  make kimi-territory      — territory game  (2 agents, 60 steps, aggressive/defensive)"
	@echo "  make kimi-coverage       — coverage game   (2 agents, 60 steps, cooperative)"
	@echo ""
	@echo "KIMI_API_KEY / MIMO_TP_KEY / NV_API_KEY must be set (or present in .env)."

# ---------------------------------------------------------------------------
# Navigation demo — proves the Phase 2.1 transport end-to-end.
# ---------------------------------------------------------------------------
openclaw-nav:
	@echo "==> Bootstrapping Gateway for nav demo …"
	$(eval TOKEN := $(shell ./scripts/openclaw-bootstrap.sh))
	@echo "==> Running navigation demo …"
	OPENCLAW_GATEWAY_TOKEN=$(TOKEN) xvfb-run -a python examples/openclaw_demo.py \
		--agents 2 --steps 10 --output-dir output/openclaw/demo
	@echo "==> Stopping Gateway …"
	docker rm -f openclaw-gateway || true
	@echo "==> Done. Report: output/openclaw/demo/report.html"

# ---------------------------------------------------------------------------
# Territory game — 2 agents with aggressive + defensive SOULs.
# ---------------------------------------------------------------------------
openclaw-territory:
	@echo "==> Bootstrapping Gateway for territory game (aggressive vs defensive) …"
	$(eval TOKEN := $(shell AGENTS=2 AGENT_SOULS=aggressive,defensive ./scripts/openclaw-bootstrap.sh))
	@echo "==> Running territory game …"
	OPENCLAW_GATEWAY_TOKEN=$(TOKEN) AGENT_SOULS=aggressive,defensive \
		xvfb-run -a python examples/territory_game.py \
		--backend openclaw --agents 2 --steps 60 \
		--output-dir output/openclaw/territory
	@echo "==> Stopping Gateway …"
	docker rm -f openclaw-gateway || true
	@echo "==> Done. Report: output/openclaw/territory/report.html"

# ---------------------------------------------------------------------------
# Coverage game — 2 cooperative agents.
# ---------------------------------------------------------------------------
openclaw-coverage:
	@echo "==> Bootstrapping Gateway for coverage game (cooperative) …"
	$(eval TOKEN := $(shell AGENTS=2 AGENT_SOULS=cooperative,cooperative PERSONALITY_PROBE=0 ./scripts/openclaw-bootstrap.sh))
	@echo "==> Running coverage game …"
	OPENCLAW_GATEWAY_TOKEN=$(TOKEN) AGENT_SOULS=cooperative,cooperative \
		xvfb-run -a python examples/coverage_game.py \
		--backend openclaw --agents 2 --steps 60 \
		--output-dir output/openclaw/coverage
	@echo "==> Stopping Gateway …"
	docker rm -f openclaw-gateway || true
	@echo "==> Done. Report: output/openclaw/coverage/report.html"

# ---------------------------------------------------------------------------
# Direct-Kimi targets — bypass the Gateway (which drops images when routing
# to Kimi's anthropic-messages endpoint) and talk straight to Kimi via the
# Anthropic SDK at api.kimi.com/coding.  Per-agent SOULs are injected into
# the system prompt from AGENT_SOULS env + skills/ai2thor-navigator/souls/.
# ---------------------------------------------------------------------------
kimi-territory:
	@echo "==> Running territory game (direct Kimi, aggressive vs defensive) …"
	AGENT_SOULS=aggressive,defensive PYTHONUNBUFFERED=1 \
		xvfb-run -a python -u examples/territory_game.py \
		--backend vlm --model kimi-coding --agents 2 --steps 20 \
		--output-dir output/kimi/territory
	@echo "==> Done. Report: output/kimi/territory/report.html"

kimi-coverage:
	@echo "==> Running coverage game (direct Kimi, cooperative) …"
	AGENT_SOULS=cooperative,cooperative PYTHONUNBUFFERED=1 \
		xvfb-run -a python -u examples/coverage_game.py \
		--backend vlm --model kimi-coding --agents 2 --steps 20 \
		--output-dir output/kimi/coverage
	@echo "==> Done. Report: output/kimi/coverage/report.html"

# ---------------------------------------------------------------------------
# Long-running local review probes — 200-step cap, 60-min wall budget,
# auto-convergence enforced, full report artifacts. Mirrors what was
# live-probed on 2026-04-20 to verify the openclaw_demo auto-convergence
# and games' wall-clock fix. Each probe bootstraps a fresh gateway, runs,
# and tears down so runs don't pollute each other.
# ---------------------------------------------------------------------------
openclaw-probe-nav:
	@echo "==> Bootstrapping Gateway for 200-step nav probe …"
	@$(SOURCE_ENV); \
	 TOKEN=$$(PROVIDER=kimi AGENTS=2 ./scripts/openclaw-bootstrap.sh) && \
	 [ -n "$$TOKEN" ] || { echo "bootstrap failed — no token"; exit 1; }; \
	 echo "==> Running navigation demo (200 steps, auto-convergence) …"; \
	 $(STRIP_ROS_ENV) OPENCLAW_GATEWAY_TOKEN=$$TOKEN PYTHONUNBUFFERED=1 \
	   xvfb-run -a python examples/openclaw_demo.py \
	   --agents 2 --steps 200 \
	   --output-dir output/openclaw-probe/nav; \
	 echo "==> Stopping Gateway …"; \
	 docker rm -f openclaw-gateway || true; \
	 docker volume rm openclaw-gateway-config || true; \
	 echo "==> Done. Report: output/openclaw-probe/nav/report.html"

openclaw-probe-territory:
	@echo "==> Bootstrapping Gateway for 200-step territory probe …"
	@$(SOURCE_ENV); \
	 TOKEN=$$(PROVIDER=kimi AGENTS=2 AGENT_SOULS=aggressive,defensive ./scripts/openclaw-bootstrap.sh) && \
	 [ -n "$$TOKEN" ] || { echo "bootstrap failed — no token"; exit 1; }; \
	 echo "==> Running territory game (200 steps, 60-min wall) …"; \
	 $(STRIP_ROS_ENV) OPENCLAW_GATEWAY_TOKEN=$$TOKEN AGENT_SOULS=aggressive,defensive PYTHONUNBUFFERED=1 \
	   xvfb-run -a python examples/territory_game.py \
	   --backend openclaw --agents 2 --steps 200 --max-wall-seconds 3600 \
	   --output-dir output/openclaw-probe/territory; \
	 echo "==> Stopping Gateway …"; \
	 docker rm -f openclaw-gateway || true; \
	 docker volume rm openclaw-gateway-config || true; \
	 echo "==> Done. Report: output/openclaw-probe/territory/report.html"

openclaw-probe-coverage:
	@echo "==> Bootstrapping Gateway for 200-step coverage probe …"
	@$(SOURCE_ENV); \
	 TOKEN=$$(PROVIDER=kimi AGENTS=2 AGENT_SOULS=cooperative,cooperative PERSONALITY_PROBE=0 ./scripts/openclaw-bootstrap.sh) && \
	 [ -n "$$TOKEN" ] || { echo "bootstrap failed — no token"; exit 1; }; \
	 echo "==> Running coverage game (200 steps, 60-min wall) …"; \
	 $(STRIP_ROS_ENV) OPENCLAW_GATEWAY_TOKEN=$$TOKEN AGENT_SOULS=cooperative,cooperative PYTHONUNBUFFERED=1 \
	   xvfb-run -a python examples/coverage_game.py \
	   --backend openclaw --agents 2 --steps 200 --max-wall-seconds 3600 \
	   --output-dir output/openclaw-probe/coverage; \
	 echo "==> Stopping Gateway …"; \
	 docker rm -f openclaw-gateway || true; \
	 docker volume rm openclaw-gateway-config || true; \
	 echo "==> Done. Report: output/openclaw-probe/coverage/report.html"

# ---------------------------------------------------------------------------
# Gateway lifecycle — use when you want to run several probes back-to-back
# against one long-lived gateway (saves the ~30s bootstrap per run).
# Token is persisted to .openclaw-token (gitignored); source it before running
# demos manually.  Tear down with `make openclaw-gateway-down` when finished.
# ---------------------------------------------------------------------------
openclaw-gateway-up:
	@echo "==> Bootstrapping gateway (2 agents, Kimi, TIMEOUT_SECONDS=600) …"
	@$(SOURCE_ENV); \
	 PROVIDER=kimi AGENTS=2 ./scripts/openclaw-bootstrap.sh > .openclaw-token && \
	 echo "==> Token saved to .openclaw-token"; \
	 echo ""; \
	 echo "Next steps:"; \
	 echo "  export OPENCLAW_GATEWAY_TOKEN=\$$(cat .openclaw-token)"; \
	 echo "  source .venv/bin/activate"; \
	 echo "  $(STRIP_ROS_ENV) PYTHONUNBUFFERED=1 python examples/territory_game.py \\"; \
	 echo "    --backend openclaw --agents 2 --steps 200 --max-wall-seconds 3600 \\"; \
	 echo "    --output-dir output/territory-probe"

openclaw-gateway-down:
	@echo "==> Tearing down gateway …"
	docker rm -f openclaw-gateway || true
	docker volume rm openclaw-gateway-config || true
	rm -f .openclaw-token
	@echo "==> Done."

# ---------------------------------------------------------------------------
# Railway appliance parity — one container with Gateway + Xvfb + Roboclaws MCP
# + three-view viewer + nginx. This mirrors the hosted Railway shape and does
# not replace the faster local `make chat` workflow.
# ---------------------------------------------------------------------------
appliance-build:
	docker build -f Dockerfile.railway -t roboclaws-appliance .

appliance-run:
	@$(SOURCE_ENV); \
	 ENV_FILE_ARG=""; \
	 [ -f .env ] && ENV_FILE_ARG="--env-file .env"; \
	 docker run --rm $$ENV_FILE_ARG \
	   -e PORT=8080 \
	   -e HOME=/data/home \
	   -e ROBOCLAWS_HOME=/data/home \
	   -e DEMO_PASSWORD="$${DEMO_PASSWORD:-demo}" \
	   -p 8080:8080 \
	   -v roboclaws-appliance-data:/data \
	   roboclaws-appliance

# ---------------------------------------------------------------------------
# Interactive chat — you drive the agent from the Gateway Control UI.
#
# `make chat` bootstraps a fresh Gateway (tears it down on Ctrl-C) and holds
# AI2-THOR + the Roboclaws MCP server open. The script prints the Control UI
# URL + bearer token; open the URL in a browser, paste the token on the
# Overview tab, switch to the Chat tab, pick agent-0, and talk.
#
# `make chat-reuse` attaches to an already-running Gateway (no rebuild, no
# teardown on exit). Reads the bearer token from OPENCLAW_GATEWAY_TOKEN if
# set, else pulls it out of the running container's openclaw.json.
# ---------------------------------------------------------------------------
#
# Provider selector targets (set Make vars, no side effects):
#
#   Image mode A — direct vision (main model handles images):
#     (default)   → mimo-v2-omni   vision+tools          (probed 2026-04-23)
#     kimi        → Kimi custom    vision via anthropic-messages
#     nvidia      → nemotron-nano  vision via openai-completions
#
#   Image mode B — split-model bridge (text main + omni describe bridge):
#     mimo-pro    → mimo-v2.5-pro as main + mimo-v2-omni as IMAGE_MODEL/bridge
#     mimo        → mimo-v2.5     as main + mimo-v2-omni as IMAGE_MODEL/bridge
#
# Usage: put the selector BEFORE the verb target so the eval fires first.
#   make chat               # default: mimo-omni (direct vision)
#   make mimo-pro chat      # split-model bridge: v2.5-pro + omni bridge
#   make mimo chat          # split-model bridge: v2.5 + omni bridge
#   make kimi chat          # Kimi custom (direct vision)
#   make kimi chat-plugin   # Kimi stock plugin
#   make mimo-pro chat-plugin  # mimo-v2-omni (Anthropic path)
#
# Hyphenated aliases exist for tab-completion:
#   chat-mimo-pro / chat-mimo / chat-kimi / chat-plugin-kimi / chat-plugin-mimo-pro
#
# Chat targets deliberately DO NOT use xvfb by default — the whole point is to
# watch the robot move in real time on the operator's actual X display. If the
# local recipe fails with "Unable to open display", fix $DISPLAY — don't reach
# for xvfb-run. `make chat-xvfb` is the explicit remote/headless exception for
# first-pass tests on machines without a physical/display-forwarded X server.
# OPENCLAW_TOKEN defaults to "demo" (safe on 127.0.0.1-only Gateway).
#
# All provider/model selection is now handled by openclaw_interactive.py flags.
# Run  python examples/openclaw_interactive.py --help  to see all options.

_CHAT = $(SOURCE_ENV); $(STRIP_ROS_ENV) OPENCLAW_TOKEN=$${OPENCLAW_TOKEN:-demo} PYTHONUNBUFFERED=1 python examples/openclaw_interactive.py
CHAT_XVFB_PYTHON ?= .venv/bin/python
CHAT_XVFB_SCREEN ?= 1280x1024x24
CHAT_XVFB_ARGS ?=
_CHAT_XVFB = $(SOURCE_ENV); $(STRIP_ROS_ENV) OPENCLAW_TOKEN=$${OPENCLAW_TOKEN:-demo} PYTHONUNBUFFERED=1 xvfb-run -a -s "-screen 0 $(CHAT_XVFB_SCREEN) -nolisten tcp" $(CHAT_XVFB_PYTHON) examples/openclaw_interactive.py

chat:
	@$(_CHAT)

chat-xvfb:
	@$(_CHAT_XVFB) $(CHAT_XVFB_ARGS)

chat-kimi:
	@$(_CHAT) --provider kimi

chat-nvidia:
	@$(_CHAT) --provider nvidia

chat-mimo-pro:
	@$(_CHAT) --model mimo_openai/mimo-v2.5-pro --image-model mimo_openai/mimo-v2-omni --observe-mode text-bridge

chat-mimo:
	@$(_CHAT) --model mimo_openai/mimo-v2.5 --image-model mimo_openai/mimo-v2-omni --observe-mode text-bridge

chat-plugin:
	@$(_CHAT) --plugin

chat-plugin-kimi:
	@$(_CHAT) --provider kimi --plugin

chat-plugin-mimo-pro:
	@$(_CHAT) --model mimo_anthropic/mimo-v2.5-pro --image-model mimo_openai/mimo-v2-omni --observe-mode text-bridge --plugin

chat-clean:
	@$(_CHAT) --clean

chat-reuse:
	@$(_CHAT) --skip-bootstrap --keep-gateway

# Pretty-tail whatever the user is typing in the Control UI chat tab.
# Our host-side trace.jsonl only records the agent's tool-call side; the
# Gateway keeps the user turn + assistant reply + tool round-trips in a
# per-session JSONL inside the container. Run this in a second terminal
# while `make chat` is live.
#
# Default output: output/openclaw-interactive/<latest-run>/chat.log
# Plus symlink : output/openclaw-interactive/latest-chat.log → above
chat-tail:
	@$(STRIP_ROS_ENV) python scripts/tail-openclaw-chat.py

# Live snapshot viewer — polls latest.{fpv,map,chase}.png at :8787.
# Open in a second browser tab while `make chat` is live.
chat-view:
	@-fuser -k 8787/tcp 2>/dev/null; true
	@$(STRIP_ROS_ENV) python scripts/view-snapshots.py

# ---------------------------------------------------------------------------
# Git hooks + test split
# ---------------------------------------------------------------------------
# - `install-hooks`        : point `core.hooksPath` at `.githooks/`.
# - `test-fast`            : what the pre-commit hook runs (no Docker,
#                            no real provider API calls).
# - `test-integration`     : what the post-merge hook runs in background
#                            (Docker-gated tests + anything touching a
#                            real model provider).
# Invariant: integration tests should never fire on every `git commit`.
# They live behind `@pytest.mark.integration`.

install-hooks:
	@git config core.hooksPath .githooks
	@echo "==> git hooks installed (core.hooksPath = .githooks)"
	@echo "    pre-commit : ruff + fast pytest"
	@echo "    post-merge : integration tests, backgrounded, log in .git/integration-last.log"
	@echo "    bypass     : git commit --no-verify   or   SKIP_TESTS=1 git commit"

uninstall-hooks:
	@git config --unset core.hooksPath || true
	@echo "==> git hooks uninstalled (core.hooksPath reset)"

test-fast:
	@$(STRIP_ROS_ENV) .venv/bin/pytest -m "not integration" -q --durations=5

test-integration:
	@$(STRIP_ROS_ENV) .venv/bin/pytest -m integration -q --durations=10
