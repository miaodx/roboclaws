# OpenClaw Robotics Ecosystem Mapping

> Research date: 2026-04-13
> Status: Complete. Tracking ongoing.

## Overview

OpenClaw (356K+ stars) has spawned at least 6 active robotics integration repos, 2 arXiv papers, NVIDIA platform support, and a dedicated community site in ~4 months. **Multi-agent physical robot coordination remains a clear gap** — our project's differentiation opportunity.

## Core Repositories

| Repository | Stars | Commits | Target | Multi-agent | Maturity |
|---|---|---|---|---|---|
| PlaiPin/rosclaw | 2 | 22 | Any ROS 2 robot | No | Prototype (re-architecting) |
| dimensionalOS/dimos | ~38-95 | 365 | G1/Go2/B1/XArm/drones | Planned | Active development |
| EvolvingAgentsLabs/RoClaw | 0 | 28 | Custom cube + MuJoCo | No | Permanent alpha |
| tomrikert/clawbody | 1 | — | Reachy Mini + MuJoCo | No | Prototype |
| dimensionalOS/roboclaw | — | — | OpenClaw↔DimOS bridge | No | Plugin |
| unitree-robot skill | N/A | N/A | G1/H1/Go1/Go2 | No | Community skill |

### ROSClaw — Most architecturally significant

SF OpenClaw Hackathon winner (Feb 2026). arXiv:2603.26997. Model-agnostic ROS 2 executive layer via rosbridge WebSocket. 8 tools (topic publish, service call, action goal, camera capture). Deployed on 3 platform types, 4 model backends. Found up to 4.8× variation in out-of-policy action rates across models. Currently re-architecting into separate packages.

**Note:** ros-claw/rosclaw is a separate project ("AUTOSAR + Android for Embodied AI") with README only, no implementation.

### DimensionalOS — Most mature framework

365 commits, 145 open issues, 42 open PRs. "Agentic OS for physical space." Supports Unitree Go2 (stable), G1 (beta), B1 (experimental), XArm (beta), AgileX Piper (beta), MAVLink/DJI drones (alpha). Signature feature: **Spatial Agent Memory** — persistent spatiotemporal model. Supports MuJoCo sim, ROS 2, compatible with both OpenClaw and Claude Code.

### RoClaw — Dual-brain architecture

20cm 3D-printed cube robot. "Cortex" (OpenClaw) for planning, "Cerebellum" (Qwen3-VL-2B via Ollama) for real-time vision-motor control via custom hex-bytecode. Includes knowledge distillation pipeline (Gemini → Qwen via Unsloth LoRA). MuJoCo simulation. Creators self-label "permanent alpha."

### ClawBody — Reachy Mini embodiment

Reachy Mini humanoid + MuJoCo simulation. MediaPipe/YOLO face tracking at 25 Hz. OpenAI Realtime API for voice. SSH for real hardware.

### OpenGo — Paper only

arXiv:2604.01708. Unitree Go2 with real-time skill switching. Three-stage pipeline (LLM generate → sim validate → deploy). Uses Feishu for HRI. **No public code.**

## NVIDIA Involvement

### NemoClaw (~19K stars)

**Not a robotics integration** — it's a security/sandboxing layer for running OpenClaw in NVIDIA OpenShell with managed Nemotron inference. GTC 2025 announcement, early preview since March 2026.

### Jetson Hardware

National Robotics Week 2026: OpenClaw running locally on Jetson Thor with Nemotron + vLLM, Isaac Sim camera streams for hardware-in-the-loop.

### Naming Collision

Chinese researchers (Tsinghua/CAS) developed an unrelated "OpenClaw" — a 12-DOF open-source five-fingered robotic hand (<$1000, Isaac Gym sim). Entirely different project from Steinberger's AI assistant.

## Multi-Agent Robot Coordination: The Gap

OpenClaw natively supports multiple isolated agents in one Gateway (independent workspace, SOUL.md, MEMORY.md, skills). Communication via `sessions_spawn`, `sessions_send`, `agentToAgent`.

Existing multi-agent templates: openclaw-multi-agent-kit (10 agents via Telegram), ClawTeam (coding agent swarms with git worktrees).

**However: no production deployment of multiple OpenClaw instances controlling multiple physical/simulated robots simultaneously was found.** Chris Dietrich (openclawrobotics.com) explores fleet management scenarios. DimensionalOS has multi-agent blueprints but unimplemented. Proposed "Octopus Orchestrator" (Issue #64435) not built.

## Comparable Projects (Non-OpenClaw)

| Project | Approach | Difference from OpenClaw |
|---------|----------|-------------------------|
| NASA ROSA | Langchain ROS 1/2 agent | Research framework, not consumer-grade |
| SMART-LLM | Programmatic LLM multi-robot planning | AI2-THOR, academic |
| LLM2Swarm | LLM robot swarms | ARGoS simulator, first systematic exploration |
| MALMM | 3 LLM agents for zero-shot manipulation | CoppeliaSim |
| Code as Policies | LLM generates robot policy code | Google, foundational work |
| SayCan | LLM + affordance robot planning | Google, real-world feasibility scoring |
| Project Fetch | Claude controls Go2 | Anthropic official demo |

**OpenClaw's unique positioning:** Messaging-first architecture. ROSA/SMART-LLM require programmatic interfaces; OpenClaw lets users control robots via WhatsApp/Telegram/Discord.

## Implications for Our Project

1. **Multi-agent sim robot control is a clear gap** — first to demo it
2. **DimensionalOS is closest competitor** — but focused on real hardware, we focus on sim games
3. **ROSClaw is key dependency for Phase 3** Isaac Lab integration
4. **OpenClaw Robotics community (openclawrobotics.com) is the distribution channel**

## References

- ROSClaw: https://github.com/PlaiPin/rosclaw / arXiv:2603.26997
- DimensionalOS: https://github.com/dimensionalOS/dimos
- RoClaw: https://github.com/EvolvingAgentsLabs/RoClaw
- ClawBody: https://github.com/tomrikert/clawbody
- NemoClaw: https://github.com/NVIDIA/NemoClaw
- OpenGo: arXiv:2604.01708
- OpenClaw Robotics community: https://www.openclawrobotics.com/
- openclaw-multi-agent-kit: https://github.com/raulvidis/openclaw-multi-agent-kit
- ClawTeam: https://github.com/win4r/ClawTeam-OpenClaw
- NASA ROSA: https://github.com/nasa-jpl/rosa / arXiv:2410.06472
- SMART-LLM: https://github.com/SMARTlab-Purdue/SMART-LLM
- MALMM: https://malmm1.github.io/
- Claude Mars Rover: https://www.anthropic.com/mars
