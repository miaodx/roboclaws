# 2026 Simulation Platforms Landscape for LLM-Controlled Multi-Agent Robotics

> Research date: 2026-04-13
> Status: Complete. Selection rationale incorporated into technical design.

## MolmoSpaces (Allen AI, Feb 2026)

AI2-THOR's physics-accurate successor. Fully open-source (Apache 2.0).

**Scale:** 230K+ indoor scenes, 130K+ object models, 42M+ annotated grasps.

**Scene sources:** MSCrafted/iTHOR (120 hand-crafted), MSProc/ProcTHOR-10K (12,000 procedural), MSProcObja (218,000 with Objaverse assets), MSMultiType/Holodeck (LLM-generated).

**Simulator backends:** Native MJCF (MuJoCo), USD exports for Isaac Lab/Sim, ManiSkill loader. As of April 2026, **data generation and benchmarking only work on MuJoCo**.

**Critical limitation: No multi-agent support.** All benchmarks are single-robot. Directly excludes it as our demo platform.

**Sim-to-real:** Companion MolmoBot VLM achieves 79.2% zero-shot sim-to-real success on tabletop pick-and-place (R=0.96 correlation), outperforming π0.5 trained on real data.

**Install:** `pip install -e ".[mujoco]"` / GitHub: github.com/allenai/molmospaces

## Habitat 3.0 / PARTNR

Most mature multi-agent human-robot collaboration platform.

**PARTNR (ICLR 2025):** 100K NL tasks, 60 houses, 5,819 objects. Native humanoid + Spot cooperation. Built-in LLM evaluation (Llama-3.1-8B, GPT-4o, o3-mini, DeepSeek R1). Four constraint types. 1,191 FPS.

**Sobering result:** Humans 93% success vs best LLMs 30%.

**For us:** Feature-complete but setup complexity far exceeds 2-3 day PoC. Better for long-term academic work.

## ManiSkill3

Fastest GPU-parallel simulation: 30,000+ FPS, 2-3× less VRAM than Isaac Lab.

**Multi-agent:** Explicitly supported. RoboFactory (ICML 2025) built on ManiSkill3 for multi-agent collaborative manipulation.

**Navigation:** Via ManiSkill-Hab with ReplicaCAD and AI2-THOR scenes.

**For us:** Manipulation-focused. Useful for Phase 3 manipulation skills.

## Isaac Lab Humanoid Navigation Stack

### Navigation Environments

Hierarchical RL: high-level command policy + pre-trained low-level locomotion. G1 envs: `Isaac-Velocity-Flat-G1-v0`, `Isaac-Velocity-Rough-G1-v0`, `Isaac-PickPlace-Locomanipulation-G1-Abs-v0`.

### AGILE Framework

Official humanoid control pipeline (github.com/nvidia-isaac/WBC-AGILE). Decoupled upper/lower body: lower via RL velocity tracking, upper via IK/imitation. Pre-trained G1 policies shipped. Command space: `(vx, vy, wz, h)`.

### COMPASS

Cross-embodiment navigation (github.com/NVlabs/COMPASS). Three stages: IL pre-training → residual RL → policy distillation. G1/H1/Carter/Spot universal. 5× success over pure IL. Zero-shot sim-to-real.

### GR00T N1.6

Latest VLA foundation model (github.com/NVIDIA/Isaac-GR00T). Cosmos-Reason-2B VLM + 32-layer diffusion transformer. Full pipeline: WBC RL training → COMPASS navigation → GR00T fine-tuning. Includes PointNav example.

### Scene Assets

Built-in: Simple Room, warehouse, hospital, office. Any Omniverse USD scene importable. MolmoSpaces provides USD exports. Procedural generation via Infinigen or Scene Synthesizer.

### Isaac Lab Limitations (for our project)

- No rich indoor scenes out-of-box — must build or import
- Requires GPU
- Multi-agent support exists but immature (DirectMARLEnv)
- Setup: 1-2 weeks, not suitable for quick PoC

## Sim-to-Real Pathway

AI2-THOR/ProcTHOR has the strongest indoor navigation sim-to-real track record:

- **SPOC (CVPR 2024):** ProcTHOR-trained, zero-shot to Stretch RE-1, RGB-only
- **PoliFormer (CoRL 2024 Outstanding Paper):** 85.5% sim success, +33.3% real-world
- **FLaRe (ICRA 2025 Best Paper Finalist):** 79.5% in unseen environments
- **RING:** Single policy across 4 real platforms (Stretch, LoCoBot, Go1, RB-Y1)

Key technique: aggressive domain randomization + DINOv2 visual backbone.

**ROSClaw** bridges sim-to-real with three-layer semantic-physical architecture + digital twin engine. Validated on TurtleBot3, Go2 Pro, G1.

## Selection Summary

| Platform | Multi-agent | Indoor scenes | GPU | Setup | Phase |
|----------|------------|---------------|-----|-------|-------|
| **AI2-THOR (iTHOR)** | ✅ Native | ✅ 120 | ❌ | Half day | **Phase 1** |
| MolmoSpaces | ❌ | ✅ 230K | ❌ (MuJoCo) | 1-2 days | Scene assets |
| Isaac Lab | ⚠️ Basic | ❌ Must build | ✅ | 1-2 weeks | **Phase 3** |
| Habitat 3.0 | ✅ Mature | ✅ 60 houses | ✅ | 1 week+ | Academic |
| ManiSkill3 | ✅ | ⚠️ Limited | ✅ | 3-5 days | Phase 3 manipulation |

## References

- MolmoSpaces: https://github.com/allenai/molmospaces / arXiv:2602.11337
- Habitat 3.0/PARTNR: https://github.com/facebookresearch/partnr-planner
- ManiSkill3: https://github.com/haosulab/ManiSkill
- Isaac Lab: https://github.com/isaac-sim/IsaacLab
- AGILE: https://github.com/nvidia-isaac/WBC-AGILE
- COMPASS: https://github.com/NVlabs/COMPASS / arXiv:2502.16372
- GR00T N1.6: https://github.com/NVIDIA/Isaac-GR00T
- SPOC: https://spoc-robot.github.io/
- PoliFormer: https://poliformer.allen.ai/
- RING: arXiv:2412.14401
- ROSClaw multi-agent: arXiv:2604.04664
