# 2026 仿真平台全景：LLM 控制多 Agent 机器人的技术选型

> 调研日期：2026-04-13
> 状态：已完成，选型结论已纳入技术设计

## MolmoSpaces（Allen AI, 2026.02）

Allen AI 最新仿真生态，AI2-THOR 的物理精确后继者。

**规模：** 230K+ 室内场景，130K+ 物体模型，42M+ 标注抓取姿态。

**场景来源：**

| 数据集 | 来源 | 数量 |
|--------|------|------|
| MSCrafted (iTHOR) | 手工精制 | 120 场景 |
| MSProc (ProcTHOR-10K) | 程序化生成 | 12,000 场景 |
| MSProcObja (ProcTHOR-Objaverse) | 程序化 + Objaverse 资产 | ~218,000 场景 |
| MSMultiType (Holodeck) | LLM 生成 | 多种 |

**仿真器后端：** 原生 MJCF（MuJoCo），USD 导出支持 Isaac Lab/Isaac Sim，自定义 loader 支持 ManiSkill。但截至 2026 年 4 月，**数据生成和基准测试只在 MuJoCo 上跑通**。

**关键限制：不支持多 Agent。** 所有基准任务为单机器人。这直接排除了它作为我们 demo 平台的可能性。

**Sim-to-Real：** 配套的 MolmoBot VLM 策略在桌面抓取上达到 79.2% 零样本 sim-to-real 成功率（R=0.96 相关系数），超过了在真实数据上训练的 π0.5。

**安装：** `pip install -e ".[mujoco]"`，GitHub: github.com/allenai/molmospaces

## Habitat 3.0 / PARTNR

多 Agent 人机协作的最成熟方案。

**PARTNR（ICLR 2025）：** 100K 自然语言任务，60 栋房子，5,819 物体。原生支持人形 + Boston Dynamics Spot 协作。内置 LLM 评估（Llama-3.1-8B, GPT-4o, o3-mini, DeepSeek R1）。四类约束任务（自由、空间、时间、异构）。1,191 FPS。

**现实结论：** 人类 93% 成功率 vs 最强 LLM 30%——差距巨大。

**适用性：** 功能完备但搭建复杂度远超 2-3 天 PoC。适合长期学术研究。

## ManiSkill3

GPU 并行仿真最快的方案——30,000+ FPS，比 Isaac Lab 少 2-3x GPU 显存。

**多 Agent：** 明确支持，12 个任务类别之一。RoboFactory（ICML 2025 挑战赛）基于 ManiSkill3 构建多 Agent 协作操作。

**导航：** 通过 ManiSkill-Hab 支持 ReplicaCAD 和 AI2-THOR 场景的移动操作。

**异构仿真：** 独特能力——每个并行环境可以包含不同物体和布局。

**适用性：** 操作为主，室内导航支持有限。适合 Phase 3 操作技能阶段。

## Isaac Lab 人形导航栈

NVIDIA 的完整人形机器人流水线。

### 导航环境

层级 RL 架构：高层 command policy + 预训练低层 locomotion policy。参考实现用 ANYmal-C，同样模式适用于人形。

G1 相关环境：
- `Isaac-Velocity-Flat-G1-v0` / `Isaac-Velocity-Rough-G1-v0`
- `Isaac-PickPlace-Locomanipulation-G1-Abs-v0`

### AGILE 框架

NVIDIA 官方人形控制流水线（github.com/nvidia-isaac/WBC-AGILE）。解耦上下体：下体 RL 速度跟踪，上体 IK/模仿/随机。预训练 G1 和 Booster T1 策略。命令空间：`(vx, vy, wz, h)`。

### COMPASS

跨形态导航策略（github.com/NVlabs/COMPASS）。三阶段：模仿学习预训练 → 残差 RL 微调 → 策略蒸馏。G1, H1, Carter, Spot 通用。比纯 IL 基线高 5x 成功率。零样本 sim-to-real。

### GR00T N1.6

最新 VLA 基础模型（github.com/NVIDIA/Isaac-GR00T）。Cosmos-Reason-2B VLM + 32 层 diffusion transformer。完整 Isaac Lab → GR00T 管线：WBC RL 训练 → COMPASS 导航轨迹 → GR00T 微调。包含 PointNav 示例。

### 场景资产

Isaac Sim 内置：Simple Room、仓库、医院、办公室。可从 Omniverse 导入任意 USD 场景。MolmoSpaces 提供 USD 导出。程序化生成可用 Infinigen 或 Scene Synthesizer。

### Isaac Lab 的限制（对我们的项目）

- **没有现成的丰富室内场景**——需要自己搭建或导入
- **需要 GPU**——纯 CPU 无法运行
- **多 Agent 支持存在但不成熟**（DirectMARLEnv）
- **搭建周期：1-2 周**，不适合快速 PoC

## Sim-to-Real 路径

AI2-THOR/ProcTHOR 有最强的室内导航 sim-to-real 记录：

- **SPOC（CVPR 2024）**：ProcTHOR-Objaverse 训练，零样本部署到 Stretch RE-1
- **PoliFormer（CoRL 2024 Outstanding Paper）**：sim 85.5% 成功，真实世界 +33.3% 提升
- **FLaRe（ICRA 2025 Best Paper Finalist）**：79.5% 未知环境成功率
- **RING**：单策略跨 4 个真实平台（Stretch, LoCoBot, Go1, RB-Y1）

关键技术：激进域随机化（光照、纹理、物体、相机、物理）、DINOv2 视觉骨干、SIGLIP 多模态编码。

**ROSClaw** 的三层语义-物理架构 + 数字孪生引擎可做 sim-to-real 桥接。已验证平台：TurtleBot3, Unitree Go2 Pro, Unitree G1。

## 选型总结

| 平台 | 多 Agent | 室内场景 | GPU | 搭建时间 | Phase |
|------|---------|---------|-----|---------|-------|
| **AI2-THOR (iTHOR)** | ✅ 原生 | ✅ 120 场景 | ❌ | 半天 | **Phase 1** |
| MolmoSpaces | ❌ | ✅ 230K | ❌ (MuJoCo) | 1-2 天 | 场景资产来源 |
| Isaac Lab | ⚠️ 基础 | ❌ 需自建 | ✅ | 1-2 周 | **Phase 3** |
| Habitat 3.0 | ✅ 成熟 | ✅ 60 栋 | ✅ | 1 周+ | 学术对比 |
| ManiSkill3 | ✅ | ⚠️ 有限 | ✅ | 3-5 天 | Phase 3 操作 |

## 参考链接

- MolmoSpaces: https://github.com/allenai/molmospaces / arXiv:2602.11337
- MolmoSpaces 博客: https://allenai.org/blog/molmospaces
- MolmoBot: arXiv:2603.16861
- Habitat 3.0/PARTNR: https://github.com/facebookresearch/partnr-planner
- ManiSkill3: https://github.com/haosulab/ManiSkill
- Isaac Lab: https://github.com/isaac-sim/IsaacLab / arXiv:2511.04831
- AGILE: https://github.com/nvidia-isaac/WBC-AGILE
- COMPASS: https://github.com/NVlabs/COMPASS / arXiv:2502.16372
- GR00T N1.6: https://github.com/NVIDIA/Isaac-GR00T
- GR00T WBC: https://github.com/NVlabs/GR00T-WholeBodyControl
- SPOC: https://spoc-robot.github.io/
- PoliFormer: https://poliformer.allen.ai/
- FLaRe: https://robot-flare.github.io/
- RING: arXiv:2412.14401
- ROSClaw 多 Agent: arXiv:2604.04664
- RoboCasa365: ICLR 2026
