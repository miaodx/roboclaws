# Makefile — convenience targets for common local workflows.
# Requires: docker, xvfb-run, KIMI_API_KEY (or NV_API_KEY) in environment
# OR in a project-local `.env` file (auto-sourced by the openclaw-* targets).

.PHONY: openclaw-nav openclaw-territory openclaw-coverage \
        openclaw-probe-nav openclaw-probe-territory openclaw-probe-coverage \
        openclaw-gateway-up openclaw-gateway-down \
        mimo-pro mimo kimi \
        chat chat-reuse chat-tail chat-view \
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
	@echo "Interactive chat (you drive the agent from the Control UI in a browser):"
	@echo "  Two image-processing modes:"
	@echo "    direct vision  — main model handles images itself:"
	@echo "      make chat              — MiMo V2 Omni (default; vision+tools)"
	@echo "      make chat-kimi         — Kimi custom (anthropic-messages; vision)"
	@echo "      make chat-nvidia       — NVIDIA NIM (nemotron; vision)"
	@echo "    split-model bridge      — text-only main model + omni vision bridge:"
	@echo "      make chat-mimo-pro     — MiMo V2.5 Pro (text) + V2 Omni bridge"
	@echo "      make chat-mimo         — MiMo V2.5 (text) + V2 Omni bridge"
	@echo "  Anthropic-path variants (chat-plugin):"
	@echo "      make chat-plugin-kimi      — Kimi stock plugin"
	@echo "      make chat-plugin-mimo-pro  — MiMo V2.5 Pro (anthropic) + omni image"
	@echo "  Utility:"
	@echo "  make chat-reuse          — attach to an already-running Gateway"
	@echo "  make chat-tail           — pretty-tail the Gateway session JSONL (run in 2nd terminal)"
	@echo "  make chat-view           — live snapshot viewer at http://127.0.0.1:8787 (run in 3rd terminal)"
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
# Chat targets deliberately DO NOT use xvfb — the whole point is to watch the
# robot move in real time on the operator's actual X display. If the recipe
# fails with "Unable to open display", fix $DISPLAY — don't reach for xvfb-run.
# OPENCLAW_TOKEN defaults to "demo" (safe on 127.0.0.1-only Gateway).

# Provider/model defaults — overridden by selector targets via $(eval).
# Image-processing modes for OpenClaw (two distinct approaches):
#   direct vision  — main model handles images itself (mimo-omni, nvidia, kimi)
#   text-bridge    — main model is text-only; roboclaws__observe returns bridge
#                    text generated by IMAGE_MODEL (mimo-pro: v2.5-pro + omni;
#                    mimo: v2.5 + omni)
_PROVIDER        ?= mimo
_MIMO_VARIANT    ?= mimo-v2-omni
_MIMO_IMAGE_MODEL ?=
_MIMO_OBSERVE_MODE ?=

# Selector targets: run BEFORE the verb target (e.g. make mimo-pro chat).
mimo-pro:
	$(eval _PROVIDER=mimo)
	$(eval _MIMO_VARIANT=mimo-v2.5-pro)
	$(eval _MIMO_IMAGE_MODEL=mimo_openai/mimo-v2-omni)
	$(eval _MIMO_OBSERVE_MODE=text-bridge)

mimo:
	$(eval _PROVIDER=mimo)
	$(eval _MIMO_VARIANT=mimo-v2.5)
	$(eval _MIMO_IMAGE_MODEL=mimo_openai/mimo-v2-omni)
	$(eval _MIMO_OBSERVE_MODE=text-bridge)

kimi:
	$(eval _PROVIDER=kimi)

# Helpers: compose the full Gateway model ID depending on API path.
# When _PROVIDER != mimo these expand to nothing; bootstrap picks its own default.
_MIMO_OPENAI_MODEL    = $(if $(filter mimo,$(_PROVIDER)),MODEL=mimo_openai/$(_MIMO_VARIANT),)
_MIMO_ANTHROPIC_MODEL = $(if $(filter mimo,$(_PROVIDER)),MODEL=mimo_anthropic/$(_MIMO_VARIANT),)
# Pass IMAGE_MODEL only when a selector set it (text-only main model needs a bridge).
_MIMO_IMAGE_VAR       = $(if $(_MIMO_IMAGE_MODEL),IMAGE_MODEL=$(_MIMO_IMAGE_MODEL),)
_MIMO_OBSERVE_VAR     = $(if $(_MIMO_OBSERVE_MODE),ROBOCLAWS_OBSERVE_MODE=$(_MIMO_OBSERVE_MODE),)

chat:
	@$(SOURCE_ENV); \
	 PROVIDER=$(_PROVIDER) $(_MIMO_OPENAI_MODEL) $(_MIMO_IMAGE_VAR) $(_MIMO_OBSERVE_VAR) \
	   OPENCLAW_TOKEN=$${OPENCLAW_TOKEN:-demo} \
	   $(STRIP_ROS_ENV) PYTHONUNBUFFERED=1 \
	   python examples/openclaw_interactive.py

chat-reuse:
	@$(SOURCE_ENV); \
	 OPENCLAW_TOKEN=$${OPENCLAW_TOKEN:-demo} \
	   $(STRIP_ROS_ENV) PYTHONUNBUFFERED=1 \
	   python examples/openclaw_interactive.py \
	     --skip-bootstrap --keep-gateway

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

# chat-plugin: Anthropic-compatible path for MiMo; stock Kimi plugin path for kimi.
# Both KIMI_PROVIDER_MODE and MIMO_PROVIDER_MODE are passed; bootstrap ignores
# the one that doesn't match PROVIDER.
chat-plugin:
	@$(SOURCE_ENV); \
	 PROVIDER=$(_PROVIDER) $(_MIMO_ANTHROPIC_MODEL) $(_MIMO_IMAGE_VAR) $(_MIMO_OBSERVE_VAR) \
	   KIMI_PROVIDER_MODE=plugin MIMO_PROVIDER_MODE=anthropic \
	   OPENCLAW_TOKEN=$${OPENCLAW_TOKEN:-demo} \
	   $(STRIP_ROS_ENV) PYTHONUNBUFFERED=1 \
	   python examples/openclaw_interactive.py

# NVIDIA NIM — free tier, fastest, no reasoning tokens.
chat-nvidia:
	@$(SOURCE_ENV); \
	 PROVIDER=nvidia OPENCLAW_TOKEN=$${OPENCLAW_TOKEN:-demo} \
	   $(STRIP_ROS_ENV) PYTHONUNBUFFERED=1 \
	   python examples/openclaw_interactive.py

# Hyphenated aliases (tab-completion / discoverability).
chat-mimo-pro: mimo-pro chat
chat-mimo: mimo chat
chat-kimi: kimi chat
chat-plugin-kimi: kimi chat-plugin
chat-plugin-mimo-pro: mimo-pro chat-plugin

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
