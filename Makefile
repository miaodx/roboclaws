# Makefile — convenience targets for common local workflows.
# Requires: docker, xvfb-run, KIMI_API_KEY (or NV_API_KEY) in environment.

.PHONY: openclaw-nav openclaw-territory openclaw-coverage help

help:
	@echo "Layer 3 OpenClaw targets (requires a running Gateway):"
	@echo "  make openclaw-nav        — navigation demo (2 agents, 10 steps)"
	@echo "  make openclaw-territory  — territory game  (2 agents, 60 steps, aggressive/defensive)"
	@echo "  make openclaw-coverage   — coverage game   (2 agents, 60 steps, cooperative)"
	@echo ""
	@echo "Each target bootstraps the Gateway, runs the game, and tears down."
	@echo "KIMI_API_KEY (or NV_API_KEY) must be set."

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
