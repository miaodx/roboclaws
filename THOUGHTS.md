# Thoughts

Ideas, parked work, and possible future directions that should not affect the
current development roadmap until reviewed.

Use this file as the backlog for random ideas. If an item becomes concrete and
worth doing soon, promote it to [`TODOS.md`](TODOS.md) with acceptance criteria
and a clear queue position.

---

## Possible future work

### LeRobotDataset rollout export

Source: `docs/research-checkpoints/2026-04.md` §6.3 item 8.

Replay data may eventually export in LeRobotDataset format for future GR00T /
openpi / VLA work. Before implementing, map current replay fields to
LeRobotDataset v3.0 concepts, identify missing action/state/camera metadata,
and decide whether this should wait until after the MolmoSpaces substrate
spike.

### Multi-agent harness expansion

Source: checkpoint §6.3 item 9 and §7 Q2/Q15.

Explore what breaks when `harness/` moves from one coding agent driving one
robot to multiple coding agents driving multiple robots in the same sim. Likely
questions: lock/context/state isolation, generated skill transfer across
agents, SOUL overfitting, shared sim state, and scoring.

### Memory-depth ablation for territory control

Source: checkpoint §7 Q3.

Measure whether the full SOUL → MEMORY → FTS → vector memory stack helps
short-horizon high-frequency territory tasks. This needs repeated trials across
at least three memory configurations, so it should stay out of the main roadmap
until there is appetite for experimental runs.

### Autonomous-nav `report.html` parity with VLM report

Flagged 2026-04-21 while reviewing Phase 2.6 Probe 4 artifact.

The VLM report has per-step reasoning and frame back/forward controls. The
OpenClaw autonomous-nav report lacks both because Gateway reasoning is opaque
and the current layout is a single scroll. If promoted, start by diffing
`scripts/render_autonomous_replay.py` against `roboclaws/core/visualizer.py`,
then pick a report contract that works despite Gateway opacity.

### OpenClaw tool-profile simplification

Flagged 2026-04-27 while fixing the OpenClaw 2026.4.25-beta.11 MCP regression.

Current choice keeps `minimal` and splices `bundle-mcp` through `alsoAllow`.
The `coding` profile might simplify bootstrap but broadens the tool surface.
If promoted, compare photo and territory probes under both profiles, measure
success rate/action diversity/tool-misuse errors, then update
`docs/openclw/openclaw-tool-profiles.md` with the verdict.

### Weekly coding-agent model/settings benchmark

Coding-agent demos can vary across model families and runtime settings:
Claude Opus / Sonnet / Haiku, GPT-5.5, GPT-5.3-Codex, Kimi, Xiaomi MiMo, and
others; reasoning effort can also vary across low / medium / high / xhigh
profiles.

Possible benchmark: run a small fixed coding-agent robot demo suite once per
week and publish a compact leaderboard for "best current demo configuration."
Compare task success, number of tool calls, elapsed time, cost, trace quality,
stuck recovery, and whether the agent produces useful labeled observations.

If promoted, keep the benchmark intentionally small and stable so weekly runs
are comparable. The output should recommend a default model + reasoning setting
for the coding-agent demo path, not try to exhaustively rank every possible
provider.

---

## Parked until triggered

### OpenClaw cold-start: remaining gap

Flagged 2026-04-28 after shipping commit `bd5037b`, which cut 348s to 136s.

Per-phase trace in
`docs/retrospectives/openclaw-cold-start-2026-04-28.md` shows the remaining
cost is `sidecars.session-locks` (65s) + `sidecars.channels` (39.5s). Open
this only if a future image bump regresses cold-start past 136s; otherwise
leave parked.
