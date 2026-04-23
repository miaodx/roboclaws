# Makefile — convenience targets for common local workflows.
# Requires: docker, xvfb-run, KIMI_API_KEY (or NV_API_KEY) in environment
# OR in a project-local `.env` file (auto-sourced by the openclaw-* targets).

.PHONY: openclaw-nav openclaw-territory openclaw-coverage \
        openclaw-probe-nav openclaw-probe-territory openclaw-probe-coverage \
        openclaw-gateway-up openclaw-gateway-down \
        chat chat-reuse chat-tail chat-view chat-plugin chat-nvidia \
        kimi-territory kimi-coverage help

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
	@echo "  make chat                — bootstrap Gateway + hold AI2-THOR/MCP open (Kimi custom)"
	@echo "  make chat-plugin         — same, Kimi stock plugin (kimi/k2p5, reasoning on, slow)"
	@echo "  make chat-nvidia         — same, NVIDIA NIM (nemotron vision)"
	@echo "  make chat-reuse          — attach to an already-running Gateway"
	@echo "  make chat-tail           — pretty-tail the Gateway session JSONL (run in 2nd terminal)"
	@echo "  make chat-view           — live snapshot viewer at http://127.0.0.1:8787 (run in 3rd terminal)"
	@echo ""
	@echo "Direct Kimi targets (no Gateway — talks to Kimi anthropic endpoint):"
	@echo "  make kimi-territory      — territory game  (2 agents, 60 steps, aggressive/defensive)"
	@echo "  make kimi-coverage       — coverage game   (2 agents, 60 steps, cooperative)"
	@echo ""
	@echo "KIMI_API_KEY must be set (or present in .env for auto-sourced openclaw-* targets)."

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
# PROVIDER=kimi is pinned (mirroring openclaw-probe-* targets). Without the
# pin, bootstrap prefers nvidia whenever NV_API_KEY is set — and Kimi is what
# we actually want here because the Gateway's OpenAI→anthropic-messages
# adapter preserves tool-result images into the agent's prompt. NIM is fine
# too, but Kimi's multi-image reasoning is what every other probe target uses,
# and consistency beats a surprise provider switch.
# Chat targets deliberately DO NOT use xvfb — unlike the probe/demo targets,
# the whole point of chat is to watch the robot move in real time, so we
# want AI2-THOR's Unity window on the operator's actual X display. Every
# chat-* recipe below inherits $DISPLAY from the caller's shell. If the
# recipe fails with "Unable to open display" or similar, either $DISPLAY
# isn't set (SSH without -X / -Y, bare tmux in a headless VM) or xhost
# is locking the server — fix the shell, don't reach for xvfb-run.
# OPENCLAW_TOKEN defaults to "demo" on every chat target so the operator
# pastes it once per browser profile and it sticks across `make openclaw-
# gateway-down` + reboot cycles. Override with `OPENCLAW_TOKEN=<real>`
# if you need an unguessable token (never actually required on :127.0.0.1).
# The Gateway only binds 127.0.0.1 — no LAN risk — but don't use `demo`
# behind a reverse proxy or with HOST_IP=0.0.0.0.
chat:
	@$(SOURCE_ENV); \
	 PROVIDER=$${PROVIDER:-kimi} OPENCLAW_TOKEN=$${OPENCLAW_TOKEN:-demo} \
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
# while `make chat` is live. Mirrors to output/openclaw-interactive/latest-chat.log
# by default so the transcript survives the container being torn down.
chat-tail:
	@$(STRIP_ROS_ENV) python scripts/tail-openclaw-chat.py \
	    --log-file output/openclaw-interactive/latest-chat.log

# Live snapshot viewer. The Control UI only renders MEDIA: attachments
# from the FINAL assistant message of a turn — so on multi-step chat
# sequences (walk N steps, snapshot at each), the intermediate images
# never appear in chat. They ARE written to disk by roboclaws__snapshot
# though, and the tool updates latest.{fpv,map,chase}.png atomically on
# every call. This viewer polls those three files from a tiny local
# HTTP page at :8787 — open it in a second browser tab and watch the
# robot move frame-by-frame while the chat scrolls.
chat-view:
	@$(STRIP_ROS_ENV) python scripts/view-snapshots.py

# Chat A/B variants — same entrypoint, different provider/mode. Use these to
# diagnose image-upload drops, tool-call latency, or any provider-specific
# misbehavior. Only one Gateway can exist at a time (container name is fixed),
# so tear down the previous one before switching:  make openclaw-gateway-down
#
# chat-plugin   — stock Gateway Kimi plugin (kimi/k2p5). Reasoning mode ON →
#                 3000+ CoT tokens/turn, 60-120s per multi-image call, idle
#                 watchdog risk. Useful A/B target: different image-pipe code
#                 path (openai-completions, not anthropic-messages) inside the
#                 Gateway, so user-uploaded images may survive where the
#                 default anthropic-messages path drops them.
# chat-nvidia   — NVIDIA NIM nemotron-nano-12b-v2-vl (free tier, multi-image,
#                 tool-use OK). Fastest of the three. No reasoning tokens.
chat-plugin:
	@$(SOURCE_ENV); \
	 PROVIDER=kimi KIMI_PROVIDER_MODE=plugin OPENCLAW_TOKEN=$${OPENCLAW_TOKEN:-demo} \
	   $(STRIP_ROS_ENV) PYTHONUNBUFFERED=1 \
	   python examples/openclaw_interactive.py

chat-nvidia:
	@$(SOURCE_ENV); \
	 PROVIDER=nvidia OPENCLAW_TOKEN=$${OPENCLAW_TOKEN:-demo} \
	   $(STRIP_ROS_ENV) PYTHONUNBUFFERED=1 \
	   python examples/openclaw_interactive.py
