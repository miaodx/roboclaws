# 0002. Defer Isaac Lab integration to Phase 3

Date: 2026-04-27 (extracted from the initial design doc; decision made
at project inception).

## Status

Accepted.

## Context

Isaac Lab is the more powerful long-term platform for embodied agents:

- AGILE framework for G1 locomotion
- COMPASS cross-embodiment navigation
- GR00T N1.6 VLA pipeline
- High-fidelity physics, photorealistic rendering, GPU acceleration

Cost of adopting it now:

- 1-2 weeks of setup for an MARL-capable environment
- No ready-made indoor scenes — must build custom USD scenes
- GPU dependency (rules out cloud sandbox CI for real-render runs)
- Steep learning curve for OmniGraph / Replicator / Isaac Sim conventions

Phase 1 of roboclaws needs to validate "VLM can drive a simulated robot"
in days, not weeks. Phase 2 layers OpenClaw on top of that. Phase 3 is
when locomotion realism becomes the next interesting thing.

## Decision

Defer Isaac Lab integration until Phase 3 (Week 2+). Phases 1-2 use
AI2-THOR (see [ADR-0001](../superseded/0001-use-ai2thor-for-phase-1.md)) exclusively.

When Phase 3 starts, the integration shape is two-level:

- OpenClaw VLM planner at 1-5 Hz (slow, semantic reasoning).
- RL locomotion policy at 200 Hz (fast, control-loop).
- Bridge via ROSClaw or direct Python integration.
- Scenes from Omniverse USD assets or MolmoSpaces conversion.

## Consequences

**Easier (now):**

- Phase 1 PoC delivered fast on AI2-THOR.
- No GPU dependency for cloud / dev sandbox.
- Validate VLM capability before investing in physics realism.

**Harder (later):**

- Phase 3 will require porting game logic to Isaac Lab's MARL
  environment shape.
- Asset migration: convert iTHOR scenes (or use new USD scenes); the
  roboclaws view system (FPV / map-v2 / chase-cam) needs Isaac
  equivalents.
- Operational: GPU instance, longer dev cycles, more complex deploy
  story.

## Triggers for revisiting

This decision should be revisited if any of the following happen:

- Upstream Isaac Lab adds ready-made indoor scenes, lowering setup cost
  meaningfully.
- AI2-THOR proves insufficient for the navigation tasks the project
  takes on (e.g., contact-rich manipulation, dynamic balance).
- Phase 1-2 success criteria are met:
  - VLM-driven navigation has been validated end-to-end on AI2-THOR.
  - OpenClaw multi-agent integration has shipped.
  - Demand emerges for realistic locomotion (G1 humanoid, etc.).
