# Thoughts

Ideas, parked work, and possible future directions that should not affect the
current development roadmap until reviewed.

This is scratch/backlog context, not current project status. For current focus,
next action, and active source links, read [`STATUS.md`](STATUS.md).

Use this file as the backlog for random ideas. If an item becomes concrete and
worth doing soon, promote it to [`TODOS.md`](TODOS.md) with acceptance criteria
and a clear queue position.

---

## Current architecture baseline

### Architecture review follow-ons landed

Status as of 2026-05-07: the 2026-04-30 architecture-review follow-ons are no
longer TODOs. They landed as one commit per issue:

- `#83` / `14bcaed`: OpenClaw navigation now requires exactly three prompt
  images in normal runtime paths: FPV, `map_v2`, and chase camera. Diagnostic
  replay paths may synthesize missing views, but normal provider calls should
  not preserve two-image compatibility.
- `#84` / `2ceb2ae`: territory and coverage examples share
  `render_game_prompt_bundle()` from `roboclaws/core/views.py`.
- `#85` / `1eb0af5`: territory and coverage decision/execution flow share
  `roboclaws/games/turns.py`.
- `#86` / `ecc00f6`: provider action parsing flows through
  `roboclaws/core/action_decision.py`; the shared safe fallback is
  `RotateRight`.
- `#87` / `2f29815`: replay manifests, MCP trace/frame/snapshot shapes, run
  results, transcript extraction, and autonomous report summaries share
  `roboclaws/core/run_artifacts.py`.
- `#88` / `bb91fc3`: model aliases, OpenClaw model IDs, image capability, and
  required env metadata live in `roboclaws/core/provider_catalog.py`.
- `#89` / `2c7b5cb`: world-cell conversion, reachable-position normalization,
  object footprints, and world bounding boxes live in
  `roboclaws/core/scene_grid.py`.

Future architecture work should start from those modules instead of adding new
parallel schema/action/grid/provider helpers. The post-refactor validation gate
was `ruff check .`, `ruff format --check .`, `git diff --check`, and
`./scripts/run_pytest_standalone.sh -q`.

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

### Real robot navigation-stack integration

Source: user request, 2026-04-30.

Investigate the best way to integrate existing robot navigation stacks such as
ROS 2 Nav2, EasyNavigation, or similar systems into this repo instead of
hand-rolling long-horizon navigation. The goal is to let roboclaws use real
grid / occupancy maps and navigation contracts that can transfer from
simulation to physical robots.

Questions to answer before promoting this: which stack has the cleanest bridge
from the current `MultiAgentEngine` / MCP tool surface, how to represent map
inputs and robot poses consistently across AI2-THOR, future simulators, and
real robots, what real `.pgm` / `.yaml` occupancy maps or SLAM outputs should
be used for testing, and which acceptance tests prove the same high-level task
can run in both sim and the real-world robot deployment path.

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

### Supported access to encrypted model reasoning

Source: user request, 2026-04-30, after adding Claude Code / Codex JSONL
parsing to `report.html`.

Codex session JSONL can record reasoning events as encrypted-only payloads
(`encrypted_content`) with no plaintext summary. Those events are useful for
enhanced behavior analysis of the coding agent, especially when aligning model
intent with observations and tool calls. The desired outcome is a user-owned,
explicitly opted-in way to inspect or export this reasoning for local harness
analysis, rather than having behavior analysis blocked by the AI coding agent
runtime itself.

Before promoting this, investigate first-party / authorized mechanisms only:
a Codex CLI setting, API export mode, debug transcript option, or provider
feature request that can emit plaintext reasoning summaries or decryptable
local artifacts with explicit user consent. Do not implement local encryption
bypass, key extraction, or report-side decryption against provider-protected
private reasoning. If no supported path exists, improve the report by
aggregating encrypted-only reasoning counts and asking the executor to emit
explicit public reasoning summaries during the run.

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
