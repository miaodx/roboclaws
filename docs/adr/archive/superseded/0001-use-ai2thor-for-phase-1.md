# 0001. Use AI2-THOR for Phase 1

Date: 2026-04-27 (extracted from the initial design doc; decision made
at project inception).

## Status

Superseded by [ADR-0137](../../0137-retire-ai2thor-and-direct-vlm-public-surfaces.md).

## Context

Roboclaws needs a simulation platform that supports:

- Multiple agents in the same scene
- Indoor environments rich enough for navigation tasks
- Fast iteration (PoC timeline: days, not weeks)
- Feasibility on a developer workstation without dedicated GPU

After surveying the major candidates as of early 2026:

| Platform | Multi-agent | Indoor scenes | Setup time | GPU required |
|----------|-------------|---------------|------------|--------------|
| **AI2-THOR (iTHOR)** | **Native** | 120 scenes | **Half day** | No |
| MolmoSpaces | Not supported | 230K scenes | 1-2 days | MuJoCo: No |
| Isaac Lab | DirectMARLEnv | Must build | 1-2 weeks | Yes |
| ManiSkill3 | Supported | Manipulation focus | 3-5 days | Yes |
| Habitat 3.0/PARTNR | Supported | 60 houses | 1 week+ | Yes |

Key exclusion reasons:

- **MolmoSpaces** — latest and largest scene set (230K), but no
  multi-agent support. Excluded immediately.
- **Isaac Lab** — no ready-made indoor scenes; building custom USD
  scenes is unrealistic for a multi-day PoC.
- **Habitat 3.0/PARTNR** — most mature multi-agent solution (100K
  tasks), but setup complexity far exceeds PoC requirements.
- **ManiSkill3** — manipulation-focused; less aligned with the
  navigation-and-strategy framing of the initial scenarios.

## Decision

Use **AI2-THOR (iTHOR scenes)** for Phase 1 and all immediate downstream
work (multi-agent games, OpenClaw integration, the direct coding-agent
driver, the Railway appliance).

Specific constraints adopted with the platform:

- **iTHOR scenes only** (FloorPlan1-430), not ProcTHOR — ProcTHOR has
  known multi-agent bugs (allenai/ai2thor #1169, #1265).
- **Default scene range**: living rooms (FloorPlan201-230) — larger
  spaces suit multi-agent movement.
- Accept the **synchronous one-agent-per-step model** (`controller.step()`
  moves one agent per call) and implement turn-based stepping in game
  logic.

## Consequences

**Easier:**

- PoC delivered in ~half a day instead of 1-2 weeks for Isaac Lab.
- Runs on a workstation without GPU; cloud sandbox can run mock pipelines.
- Direct multi-agent support — no harness shim.
- 120 ready-made scenes available out of the box.

**Harder:**

- ProcTHOR's procedurally-generated scenes are off the table until
  upstream fixes its multi-agent bugs.
- Synchronous stepping means game logic owns turn ordering, fairness,
  and per-agent budgeting.
- Long-term locomotion realism (G1 humanoid, dynamic balance, contact
  physics) needs Isaac Lab eventually — see
  [ADR-0002](../historical/0002-defer-isaac-lab-to-phase-3.md).
- AI2-THOR ships a ~1GB Unity build; first run on a fresh machine is
  slow.
