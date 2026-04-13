# OpenClaw + Isaac Lab: Feasibility Roadmap for LLM-Controlled Simulated Robots

> Research date: 2026-04-13
> Status: Complete. Conclusions incorporated into technical design.

## Key Finding

Connecting OpenClaw to Isaac Lab for simulated robot control is technically feasible. The community has built critical middleware: ROSClaw provides a ROS 2 bridge, ClawBody validates MuJoCo simulation integration, and DimensionalOS has run OpenClaw on a physical Unitree G1 with spatial memory. The recommended architecture is a two-level control hierarchy: OpenClaw as high-level VLM planner (1-10 Hz), with a pre-trained RL locomotion policy for joint control (50-200 Hz).

**However, Isaac Lab is not suitable for a 2-3 day PoC** — no ready-made indoor scenes, requires GPU, high setup complexity. Final decision: Phase 1 uses AI2-THOR; Isaac Lab deferred to Phase 3.

## OpenClaw Robotics Ecosystem

OpenClaw (247K+ stars) already has a mature robotics integration layer:

- **ROSClaw** (PlaiPin/rosclaw): SF OpenClaw Hackathon winner. Model-agnostic ROS 2 executive layer via rosbridge WebSocket. Deployed on 3 platform types (wheeled, quadruped, humanoid), 4 model backends. arXiv:2603.26997 documented up to 4.8× variation in out-of-policy action proposal rates across models.
- **DimensionalOS** (dimensionalOS/dimos): 365 commits. Integrated OpenClaw with Unitree G1, introducing Spatial Agent Memory — a voxel-based world model.
- **ClawBody** (tomrikert/clawbody): Reachy Mini + MuJoCo simulation, 25 Hz face tracking.
- **OpenGo** (arXiv:2604.01708): OpenClaw on Unitree Go2, three-stage skill pipeline (LLM generate → sim validate → deploy).
- **NemoClaw** (NVIDIA/NemoClaw): Sandboxed OpenClaw in NVIDIA OpenShell with managed inference.

## Isaac Lab G1 Support

Native Unitree G1 environments: `Unitree-G1-29dof-Velocity`, `Isaac-PickPlace-Locomanipulation-G1-Abs-v0`. TiledCamera returns GPU-resident PyTorch tensors encodable as base64 for VLM. ROS 2 bridge subscribes to `/cmd_vel`. Multi-robot via `DirectMARLEnv` (PettingZoo API).

## Two-Level Control Architecture

```
OpenClaw VLM (1-5 Hz) → velocity cmd (vx, vy, ωz) → RL policy (200 Hz) → joint actions
```

Precedent: NaVILA (arXiv:2412.04453) achieved 88% real-world navigation success on Unitree Go2/H1 with VILA VLM + RL policy.

## Multi-Agent Cost Concerns

Claude Code embodied agent study (arXiv:2601.20334): $0.51-$5.60 per task. Five agents at 1 Hz generates substantial API traffic. Local model deployment (Qwen-VL or VILA) strongly recommended for multi-agent.

## References

- ROSClaw: https://github.com/PlaiPin/rosclaw / arXiv:2603.26997
- DimensionalOS: https://github.com/dimensionalOS/dimos
- ClawBody: https://github.com/tomrikert/clawbody
- NemoClaw: https://github.com/NVIDIA/NemoClaw
- NaVILA: arXiv:2412.04453
- Isaac Lab: https://github.com/isaac-sim/IsaacLab / arXiv:2511.04831
- Claude Code embodied agent: arXiv:2601.20334
