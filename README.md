# Roboclaws 🦞🤖

**多个 OpenClaw Agent 控制多个仿真机器人：对抗与协作实验平台**

> 社区首个 OpenClaw 多 Agent 仿真机器人对抗/协作 demo

## 这是什么

Roboclaws 让多个 VLM/OpenClaw Agent 实例同时控制仿真环境中的多个机器人，进行对抗（领地争夺）和协作（区域覆盖）的实验。每个机器人由独立的 AI Agent 驱动，通过第一人称相机画面做出导航决策。

## 两个游戏场景

**🗺️ 领地争夺（对抗）** — 2-3 个机器人在室内场景中竞争。走过的格子归你，别人不能再走。可以选择快速扩张，也可以去堵住对手的路。

**📸 协作覆盖（合作）** — 2-3 个机器人协同探索整个房间。目标是尽快让 95% 的区域被至少一个机器人"看到"。机器人需要自主判断谁去哪里。

## 快速开始

```bash
pip install -e ".[dev]"

# 单 Agent 探索
python examples/single_agent_explore.py

# 领地争夺（3 Agent）
python examples/territory_game.py --agents 3 --scene FloorPlan201

# 协作覆盖（3 Agent）
python examples/coverage_game.py --agents 3 --scene FloorPlan201
```

需要设置 VLM API key：
```bash
export ANTHROPIC_API_KEY=sk-...    # Claude
# 或
export OPENAI_API_KEY=sk-...       # GPT-4o / GPT-4o-mini
```

## 架构

```
VLM Agent 0 ──┐
VLM Agent 1 ──┤── Game Controller ── AI2-THOR (多 Agent 仿真)
VLM Agent 2 ──┘

每步循环：
截图 → 生成俯瞰地图 → 构造 prompt → VLM 决策 → 执行动作 → 记录回放
```

Phase 1 直接调用 VLM API（Claude/GPT-4o），Phase 2 接入 OpenClaw Gateway 实现持久化 Agent 记忆和多渠道通信。

## 路线图

- [x] **Phase 0**: 技术调研与设计（本文档）
- [ ] **Phase 1**: AI2-THOR + VLM API 多 Agent 对抗/协作 demo
- [ ] **Phase 2**: OpenClaw 集成（Skill + Gateway + 记忆）
- [ ] **Phase 3**: Isaac Lab 迁移（G1 人形机器人 + RL 运动策略）

## 相关项目

- [Roboharness](https://github.com/MiaoDX/roboharness) — AI Coding Agent 的机器人仿真视觉测试工具
- [Robowbc](https://github.com/MiaoDX/robowbc) — 全身控制（Whole Body Control）实验
- [OpenClaw](https://github.com/openclaw/openclaw) — 开源个人 AI 助手
- [ROSClaw](https://github.com/PlaiPin/rosclaw) — OpenClaw ↔ ROS 2 桥接
- [AI2-THOR](https://github.com/allenai/ai2thor) — 交互式 3D 室内仿真环境

## License

MIT
