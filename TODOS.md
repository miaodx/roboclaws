# TODOs

Deferred work that a future maintainer can pick up without rereading the whole
history. This is a parked-work list, not current project status. For current
focus, next action, and active source links, read [`STATUS.md`](STATUS.md).

One entry = one self-contained missing item. Shipped phases are tracked under
`docs/retrospectives/`, not here.

## Missing Work

- **Autonomous-nav `report.html` parity with VLM report**
  Add per-step reasoning, if Gateway exposes or the agent emits a public reason
  tag, and add frame-by-frame navigation controls to
  `scripts/render_autonomous_replay.py`.

- **Phase 2.6 deferred-items sweep**
  Re-check
  `.planning/milestones/v1.98-phases/02.6-openclaw-mcp-tools-integration/deferred-items.md`.
  Close it with evidence if the Kimi-era / Phase 2.2 lint drift is already
  obsolete.

- **OpenClaw `minimal+alsoAllow:[bundle-mcp]` vs `coding` profile benchmark**
  Compare photo and territory probes under both profiles, then update
  `docs/openclw/openclaw-tool-profiles.md` with the verdict.

- **OpenClaw cold-start remaining gap**
  Reopen only if a future image bump regresses cold start past the current
  baseline. Start from
  `docs/retrospectives/openclaw-cold-start-2026-04-28.md`.

- **LeRobotDataset rollout export**
  Map current replay fields to LeRobotDataset concepts and identify missing
  action/state/camera metadata before implementation.

- **Multi-agent coding-agent harness expansion**
  Explore lock/context/state isolation, generated skill transfer, SOUL
  overfitting, shared simulation state, and scoring for multiple coding agents.

- **Real robot navigation-stack integration**
  Investigate a bridge from current MCP/navigation contracts to ROS 2 Nav2,
  EasyNavigation, or another real navigation stack.

- **Async route perception during cleanup navigation**
  After the waypoint-honest cleanup flow is stable, add support for perception
  events observed while moving between task locations, such as carrying an
  object from room A to a target fixture in room B and noticing another cleanup
  candidate along the route. The first implementation should define how
  in-transit observations update the observed-handle worklist without
  interrupting a held-object delivery, and how the report distinguishes route
  observations from deliberate waypoint/fixture observations. Reference design
  for a dedicated edge-side Perception Producer feeding ADR-0126 model-declared
  observations lives in
  `docs/plans/visual-grounding-perception-producer.md`.

- **Memory-depth ablation for territory control**
  Measure whether SOUL / MEMORY / FTS / vector memory helps short-horizon
  territory tasks across a small fixed configuration set.

- **Supported access to encrypted model reasoning**
  Investigate first-party, user-consented ways to export plaintext reasoning
  summaries for local harness analysis. Do not implement decryption bypasses.

- **Weekly coding-agent model/settings benchmark**
  Define a small stable demo suite that recommends the current default
  coding-agent model and reasoning setting.

_If this list empties, next work should come from a new plan or issue._
