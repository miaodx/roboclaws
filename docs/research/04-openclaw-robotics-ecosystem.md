# OpenClaw 机器人生态系统全景

> 调研日期：2026-04-13
> 状态：已完成，持续跟踪中

## 概述

OpenClaw（356K+ star）在 4 个月内从零发展出至少 6 个活跃的机器人集成 repo、2 篇 arXiv 论文、NVIDIA 平台支持和一个专属社区站点。但**多 Agent 物理机器人协调仍是空白**——这是我们项目的差异化机会。

## 核心仓库

### PlaiPin/rosclaw — ROS 2 桥接（最重要）

- **Stars:** 2 | **Commits:** 22 | **论文:** arXiv:2603.26997
- SF OpenClaw Hackathon 第一名
- 模型无关的 ROS 2 执行层，通过 rosbridge WebSocket 连接
- 8 个工具：topic publish, service call, action goal, camera capture
- 已部署在 3 种平台（轮式、四足、人形）、4 种模型后端
- 发现不同模型间 4.8× 越界动作提议率差异
- 正在进行重大重构，拆分成独立包
- **注意：** ros-claw/rosclaw 是另一个同名但不同的项目（只有 README，无实现）

### dimensionalOS/dimos — 物理空间操作系统（最成熟）

- **Stars:** ~38-95 | **Commits:** 365 | **Issues:** 145 open | **PRs:** 42 open
- 创建者：Stash Pomichter（MIT）
- 自称"物理空间的 agentic 操作系统"
- 支持 Unitree Go2（稳定）、G1（beta）、B1（实验）、XArm（beta）、AgileX Piper（beta）、MAVLink/DJI 无人机（alpha）
- 核心特性：**空间代理记忆**——持久化时空模型，链接房间布局、物体位置、时间事件
- 伴侣 repo: dimensionalOS/roboclaw（OpenClaw 插件桥接）
- 支持 MuJoCo 仿真、ROS 2、兼容 OpenClaw 和 Claude Code

### EvolvingAgentsLabs/RoClaw — 双脑机器人

- **Stars:** 0 | **Commits:** 28
- 20cm 3D 打印立方体机器人，双步进电机 + 摄像头 + ESP32-S3
- "大脑皮层"（OpenClaw）做高层规划，"小脑"（Qwen3-VL-2B via Ollama）做实时视觉运动控制
- 自定义十六进制字节码指令集（`AA 01 64 64 CB FF`）
- 包含知识蒸馏管线：Gemini（教师）→ Qwen（学生）via Unsloth LoRA
- MuJoCo 仿真支持
- 创建者自称"永久 alpha"

### tomrikert/clawbody — Reachy Mini 身体

- **Stars:** 1
- Reachy Mini 人形 + MuJoCo 仿真
- MediaPipe/YOLO 人脸追踪（25 Hz）
- OpenAI Realtime API 语音对话
- 支持 SSH 连接真实硬件

### unitree-robot skill — 社区技能

- OpenClaw 技能生态内的社区贡献
- 文字控制 Unitree G1/H1/Go1/Go2（"前进 1 米"、"左转 45°"）
- 支持 RGB-D 相机快照获取

### OpenGo — Go2 技能切换（仅论文）

- arXiv:2604.01708
- Unitree Go2 + OpenClaw，三阶段技能流水线
- 通过飞书做人机交互
- **无公开代码**

## NVIDIA 的参与

### NemoClaw

- github.com/NVIDIA/NemoClaw | ~19K stars, 2.3K forks
- **不是 Isaac Sim 机器人集成**——是安全沙箱层
- 在 NVIDIA OpenShell 中安全运行 OpenClaw，带 Nemotron 推理
- GTC 2025 发布，2026.03.16 早期预览

### Jetson 硬件支持

National Robotics Week 2026 演示了 OpenClaw 在 Jetson Thor 上本地运行，配合 Nemotron + vLLM，Isaac Sim 相机流做 hardware-in-the-loop 测试。

### 命名冲突注意

清华/中科院的"OpenClaw"是一个开源五指灵巧手（12-DOF，<$1000，Isaac Gym 仿真），与 Steinberger 的 AI 助手是完全不同的项目。

## 多 Agent 机器人：空白地带

OpenClaw 原生支持单 Gateway 内多个隔离 Agent：独立 workspace, SOUL.md, MEMORY.md, skills。通信通过 `sessions_spawn`, `sessions_send`, `agentToAgent`。

已有的多 Agent 模板：
- raulvidis/openclaw-multi-agent-kit：10 Agent Telegram 超级群组模板
- win4r/ClawTeam-OpenClaw：编码 Agent 群，git worktree 隔离

**但没有发现任何人将多个 OpenClaw 实例同时控制多个物理/仿真机器人。** Chris Dietrich 在 openclawrobotics.com 探索舰队管理/农业/应急场景，DimensionalOS 有多 Agent 蓝图但未实现。GitHub Issue #64435 提议的 "Octopus Orchestrator" 也未实现。

## 社区动态

- **openclawrobotics.com**：独立社区站点，聚集 Tom Rikert（ClawBody）、Chris Matthew（Intel RealSense + Qwen VLM）等人
- **SF OpenClaw Hackathon**（2026.02）：ROSClaw 获第一名
- **SURGE × OpenClaw Hackathon**：DroneOS（PX4 SITL + Gazebo 无人机控制）
- **Global Unhackathon**（2026.02）：24 城同步

## 非 OpenClaw 的对标项目

| 项目 | 定位 | 差异 |
|------|------|------|
| NASA ROSA | Langchain ROS 1/2 Agent | 研究框架，非消费级 |
| SMART-LLM | LLM 多机器人任务规划 | AI2-THOR，程序化 prompt |
| LLM2Swarm | LLM 机器人群 | ARGoS 仿真器，首个系统性探索 |
| MALMM | 3 LLM Agent 零样本操作 | CoppeliaSim |
| Code as Policies | LLM 生成机器人策略代码 | Google，开创性工作 |
| SayCan | LLM + affordance 机器人规划 | Google，现实可行性评分 |
| Project Fetch | Claude 控制 Go2 | Anthropic 官方演示 |

**OpenClaw 的独特定位：** 消息优先架构。ROSA/SMART-LLM 需要程序化接口，OpenClaw 让用户通过 WhatsApp/Telegram/Discord 控制机器人——大幅降低人机交互门槛。

## 对我们项目的启示

1. **多 Agent 仿真机器人控制是明确的空白**——做出来就是社区第一个
2. **DimensionalOS 是最接近的竞品**——但它专注真实硬件，我们专注仿真游戏
3. **ROSClaw 是 Phase 3 Isaac Lab 集成时的关键依赖**
4. **OpenClaw Robotics 社区（openclawrobotics.com）是传播渠道**

## 参考链接

- ROSClaw: https://github.com/PlaiPin/rosclaw / arXiv:2603.26997
- DimensionalOS: https://github.com/dimensionalOS/dimos
- RoClaw: https://github.com/EvolvingAgentsLabs/RoClaw
- ClawBody: https://github.com/tomrikert/clawbody
- NemoClaw: https://github.com/NVIDIA/NemoClaw
- OpenGo: arXiv:2604.01708
- OpenClaw Robotics 社区: https://www.openclawrobotics.com/
- openclaw-multi-agent-kit: https://github.com/raulvidis/openclaw-multi-agent-kit
- ClawTeam: https://github.com/win4r/ClawTeam-OpenClaw
- NASA ROSA: https://github.com/nasa-jpl/rosa / arXiv:2410.06472
- SMART-LLM: https://github.com/SMARTlab-Purdue/SMART-LLM
- MALMM: https://malmm1.github.io/
- LLM2Swarm: arXiv:2410.11387
- SwarmGPT: arXiv:2412.08428
- Claude Mars Rover: https://www.anthropic.com/mars
