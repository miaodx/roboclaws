# Roboclaws

多个 VLM/OpenClaw Agent 控制仿真机器人进行对抗和协作的实验平台。Python 3.10+，AI2-THOR 仿真。

## 必读文档

开始写代码之前，按顺序读：
1. `CLAUDE.md`（本文件）
2. `docs/technical-design.md`（完整技术设计，包含 API 规格、游戏规则、架构图）

## Build & test

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

运行 demo（需要 AI2-THOR，自动下载 Unity build ~1GB）：
```bash
# 需要设置 VLM API key
export ANTHROPIC_API_KEY=sk-...

python examples/single_agent_explore.py
python examples/territory_game.py --agents 3
python examples/coverage_game.py --agents 3
```

## Code style

- Ruff 强制风格，不要重复 linter 规则
- Line length: 100
- Target: Python 3.10
- Type annotations on public APIs; `from __future__ import annotations` in all modules
- 中文注释可以接受，但代码本身（变量名、函数名、类名）必须英文

## Architecture

- `roboclaws/core/engine.py` — AI2-THOR controller 封装，多 Agent 管理
- `roboclaws/core/vlm.py` — VLM API 统一接口（Claude Sonnet、GPT-4o、GPT-4o-mini）
- `roboclaws/core/visualizer.py` — 俯瞰地图生成、画面拼接、GIF 输出
- `roboclaws/core/replay.py` — 游戏回放记录（帧 + 状态 JSON）
- `roboclaws/games/territory.py` — 领地争夺游戏逻辑
- `roboclaws/games/coverage.py` — 协作覆盖游戏逻辑
- `roboclaws/openclaw/` — OpenClaw Skill + Gateway 桥接（Phase 2）
- `examples/` — 可直接运行的 demo 脚本

### AI2-THOR 关键 API

```python
# 多 Agent 初始化
controller = Controller(scene="FloorPlan201", agentCount=3, gridSize=0.25)

# 控制单个 Agent（每次 step 只能动一个）
event = controller.step(action="MoveAhead", agentId=1)

# 获取每个 Agent 的独立画面和状态
frame = event.events[agent_id].frame  # numpy (H, W, 3)
pos = event.events[agent_id].metadata['agent']['position']

# 俯瞰视角
event = controller.step(action="GetMapViewCameraProperties", raise_for_failure=True)
```

**注意：**
- iTHOR 场景支持多 Agent，ProcTHOR 不支持（有 bug）
- Agent 之间有物理碰撞，不能穿越
- Agent 在彼此相机画面中可见
- 场景范围：FloorPlan1-30（厨房）、201-230（客厅）、301-330（卧室）、401-430（浴室）

### VLM 调用模式

```python
# 每步为每个 Agent 构造的 prompt 包含：
# 1. 第一人称相机画面（base64 JPEG）
# 2. 俯瞰 grid map（标注所有 Agent 位置和游戏状态）
# 3. 结构化 JSON（位置、得分、剩余步数等）
#
# VLM 返回 JSON：{"reasoning": "...", "action": "MoveAhead"}
```

## Git workflow

- Branch from `main`
- Commit messages: `type: description` (feat, fix, ci, docs, refactor)
- PR 策略：push 到 PR 的源分支做修复，不要开新 PR

## 设计原则

| 原则 | 实践 |
|------|------|
| **薄而精** | 不做重框架，给好模型足够 context 就能跑 |
| **先跑通再优化** | Day 1-2 用最简方案验证核心假设，Day 3+ 再加 OpenClaw |
| **可视化优先** | 每个功能都要能生成可看的输出（截图/GIF/视频） |
| **成本敏感** | 默认用 GPT-4o-mini 开发，正式 demo 才切 Claude/GPT-4o |

## Gotchas

- AI2-THOR 首次运行会下载 Unity build（~1GB），需要网络
- AI2-THOR 在 Linux 上需要 X server 或 headless 渲染（`ai2thor[headless]`）
- macOS 上 AI2-THOR 渲染可能需要额外配置
- VLM API 成本：3 Agent × 200 步 ≈ $0.02（GPT-4o-mini）到 $0.36（Claude Sonnet）
- `controller.step()` 是同步的，一次只能移动一个 Agent——游戏引擎用轮流制
