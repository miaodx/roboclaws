# GitHub Issues Roadmap

This file documents the planned issues for the roboclaws project.
Use this as reference when creating or triaging issues.

## P0 — Core (CI-verifiable)

### Issue 1: AI2-THOR multi-agent engine wrapper
- **Labels:** `P0`, `feat`, `core`
- **Description:** Create `roboclaws/core/engine.py` wrapping AI2-THOR Controller for multi-agent management. Support iTHOR scenes (FloorPlan1-430), configurable agentCount, grid-based movement. Expose per-agent frame, metadata, position, rotation. Include overhead camera via GetMapViewCameraProperties + AddThirdPartyCamera. Handle action failures gracefully.
- **Acceptance:** `pytest` passes with a test that initializes 2+ agents, moves them, reads frames.

### Issue 2: Pluggable VLM provider
- **Labels:** `P0`, `feat`, `core`
- **Description:** Create `roboclaws/core/vlm.py` with a `VLMProvider` protocol and implementations for Kimi (Moonshot API, OpenAI-compatible), OpenAI (GPT-4o, GPT-4o-mini), and a MockProvider (returns random valid actions). All providers accept base64 images + structured state JSON, return `{"reasoning": "...", "action": "..."}`. Add `--model` CLI flag support. Log cumulative API cost per session. Anthropic provider is optional/deferred.
- **Acceptance:** MockProvider works in CI. Real providers work locally with API keys.

### Issue 3: Overhead map visualizer
- **Labels:** `P0`, `feat`, `core`
- **Description:** Create `roboclaws/core/visualizer.py`. Generate a 2D overhead grid map from AI2-THOR scene data showing agent positions (colored markers), claimed/unclaimed cells (for territory), covered/uncovered areas (for coverage). Composite first-person frames from all agents side-by-side with the overhead map. Output as PIL Image or numpy array. Support saving as PNG/GIF.
- **Acceptance:** Given mock game state, produces correct overhead visualization.

### Issue 4: Territory control game
- **Labels:** `P0`, `feat`, `game`
- **Description:** Create `roboclaws/games/territory.py`. Implement grid-based territory claiming: each agent claims cells it visits, claimed cells are locked. Track per-agent score (cells claimed), territory connectivity. Turn-based stepping (round-robin across agents). Configurable max steps and scene. Compute metrics: cells per agent, connectivity ratio, blocking events detected. Termination when all reachable cells claimed or max steps reached.
- **Acceptance:** Game runs with MockProvider, produces correct state transitions and final scores.

### Issue 5: Cooperative coverage game
- **Labels:** `P0`, `feat`, `game`
- **Description:** Create `roboclaws/games/coverage.py`. Track which grid cells have been within any agent's field of view. Expose coverage percentage, per-agent contribution ratio, work balance metric. Termination when 95% coverage or max steps. Provide teammate positions and coverage map to each agent's prompt.
- **Acceptance:** Game runs with MockProvider, coverage increases monotonically, metrics computed correctly.

### Issue 6: Game replay recorder
- **Labels:** `P0`, `feat`, `core`
- **Description:** Create `roboclaws/core/replay.py`. Record per-step data: all agent frames, overhead map, game state JSON, VLM prompts and responses. Save as a directory of numbered frames + a `replay.json` manifest. Support generating GIF from frame sequence via imageio. Support generating a summary report (final scores, total cost, step count).
- **Acceptance:** Replay directory structure is correct, GIF generation works.

### Issue 7: GitHub Actions CI with AI2-THOR headless
- **Labels:** `P0`, `ci`
- **Description:** Set up `.github/workflows/ci.yml`: install Xvfb + ai2thor, cache `~/.ai2thor/` for Unity build (~1GB), run ruff lint + format check, run pytest with MockProvider. AI2-THOR tests use `xvfb-run`. Add basic smoke test: initialize multi-agent scene, step each agent, verify frames are non-empty numpy arrays.
- **Acceptance:** CI passes green on push to main.

## P1 — Examples (local verification)

### Issue 8: Single-agent exploration example
- **Labels:** `P1`, `feat`, `example`
- **Description:** Create `examples/single_agent_explore.py`. One agent explores a living room scene using VLM decisions. CLI flags: `--scene`, `--steps`, `--model`, `--output-dir`. Produces a GIF of the exploration + overhead map trail. Prints cumulative VLM cost.
- **Depends on:** Issues 1, 2, 3, 6

### Issue 9: Multi-agent territory game example
- **Labels:** `P1`, `feat`, `example`
- **Description:** Create `examples/territory_game.py`. 2-3 agents play territory control. CLI flags: `--agents`, `--scene`, `--steps`, `--model`, `--output-dir`. Produces: replay GIF, per-agent score summary, overhead territory map at game end. Document any emergent strategies observed.
- **Depends on:** Issues 1, 2, 3, 4, 6

### Issue 10: Multi-agent coverage game example
- **Labels:** `P1`, `feat`, `example`
- **Description:** Create `examples/coverage_game.py`. 2-3 agents cooperate on area coverage. Same CLI flags as Issue 9. Produces: replay GIF, coverage progression chart, final coverage map, work balance report.
- **Depends on:** Issues 1, 2, 3, 5, 6

## P2 — OpenClaw Integration (Phase 2)

### Issue 11: OpenClaw skill wrapper
- **Labels:** `P2`, `feat`, `openclaw`
- **Description:** Create `roboclaws/openclaw/skill.py` and `skills/ai2thor-navigator/SKILL.md`. Package the VLM navigation loop as an OpenClaw skill. Define per-agent SOUL.md templates for different play styles (aggressive, defensive, cooperative).
- **Depends on:** Issues 1-6 complete

### Issue 12: OpenClaw Gateway bridge
- **Labels:** `P2`, `feat`, `openclaw`
- **Description:** Create `roboclaws/openclaw/bridge.py`. Connect AI2-THOR sim to OpenClaw Gateway via WebSocket. Map each simulation agent to an OpenClaw agent instance via multi-agent routing bindings. Forward camera frames as images, receive action decisions.
- **Depends on:** Issue 11

### Issue 13: Cloud relay for sim↔OpenClaw transport
- **Labels:** `P2`, `feat`, `infra`
- **Description:** Lightweight cloud relay server (FastAPI + WebSocket) for bridging local sim to cloud OpenClaw instances. Sim pushes frames via outbound WebSocket, OpenClaw connects and receives frames / sends commands. No inbound connections to local network required. Deployable on Railway or any VPS.
- **Depends on:** Issue 12
