# Roboclaws 技术设计文档

> 多个 OpenClaw Agent 在仿真环境中控制多个机器人进行对抗和协作的实验平台

## 项目定位

Roboclaws 是一个薄而精的 demo 仓库，目标是验证"多个 OpenClaw/VLM Agent 实例同时控制多个仿真机器人进行对抗和协作"的可行性。不是重框架，而是一个给好模型足够 context 就能自己跑起来的实验平台。

**核心假设：** 如果 VLM（Claude/GPT-4o）能看到仿真场景的相机画面，它就能做出合理的导航和策略决策来控制机器人。

**社区差异化：** 截至 2026 年 4 月，OpenClaw 社区没有任何人做过多个 OpenClaw 实例同时控制多个仿真机器人进行对抗/协作的公开实验。我们是第一个。

## 技术选型决策

### 为什么是 AI2-THOR（Phase 1）

经过对 MolmoSpaces、Isaac Lab、ManiSkill3、Habitat 3.0/PARTNR、MuJoCo Gymnasium 的调研后，AI2-THOR 是 Phase 1 最优选，原因：

| 方案 | 多 Agent 支持 | 场景丰富度 | 搭建时间 | 需要 GPU |
|------|-------------|-----------|---------|---------|
| **AI2-THOR (iTHOR)** | **原生支持** | 120 室内场景 | **半天** | 不需要 |
| MolmoSpaces | 不支持 | 230K 场景 | 1-2 天 | MuJoCo 后端不需要 |
| Isaac Lab | DirectMARLEnv | 需自建场景 | 1-2 周 | 需要 |
| ManiSkill3 | 支持 | 操作为主 | 3-5 天 | 需要 |
| Habitat 3.0/PARTNR | 支持 | 60 栋房子 | 1 周+ | 需要 |

关键排除理由：
- **MolmoSpaces**：最新最全（230K 场景），但不支持多 Agent，直接排除
- **Isaac Lab**：没有现成室内场景，需要自己用 USD 搭建，对 2-3 天 PoC 不现实
- **Habitat 3.0/PARTNR**：最成熟的多 Agent 方案（100K 任务），但搭建复杂度远超 PoC 要求

### 为什么不是 Isaac Lab（Phase 2 再来）

Isaac Lab 的价值在长期路线上：AGILE 框架的 G1 运动策略、COMPASS 跨形态导航、GR00T N1.6 VLA 流水线。这些能力在 Phase 2 引入。

## AI2-THOR 多 Agent 技术规格

### 初始化

```python
from ai2thor.controller import Controller

controller = Controller(
    scene="FloorPlan201",   # 客厅（FloorPlan201-230）
    agentCount=3,           # 3 个 Agent
    gridSize=0.25,          # 离散移动步长 0.25m
    snapToGrid=True,        # 网格化移动
    rotateStepDegrees=90,   # 90° 旋转步进
    fieldOfView=90,
    width=640,
    height=480,
)
```

### 控制模型

- **每次 `controller.step()` 只能移动一个 Agent**（通过 `agentId` 指定）
- 返回的 event 包含所有 Agent 的独立状态：`event.events[i]`
- Agent 之间**有物理碰撞**，不能穿过彼此
- Agent **在彼此的相机画面中可见**
- 没有内置的 Agent 间通信——需要我们自己实现

### 每个 Agent 可获取的数据

```python
agent_event = event.events[agent_id]

# 相机画面
rgb_frame = agent_event.frame                    # numpy (H, W, 3)
depth_frame = agent_event.depth_frame            # float32 米制深度

# Agent 状态
position = agent_event.metadata['agent']['position']       # {x, y, z}
rotation = agent_event.metadata['agent']['rotation']       # {x, y, z} 欧拉角
camera_horizon = agent_event.metadata['agent']['cameraHorizon']

# 可见物体
visible_objects = [o for o in agent_event.metadata['objects'] if o['visible']]

# 动作反馈
success = agent_event.metadata['lastActionSuccess']
error = agent_event.metadata['errorMessage']
```

### 俯瞰视角获取

```python
import copy

event = controller.step(action="GetMapViewCameraProperties", raise_for_failure=True)
pose = copy.deepcopy(event.metadata["actionReturn"])
pose["orthographic"] = True

controller.step(action="AddThirdPartyCamera", **pose, skyboxColor="white")
top_down_frame = controller.last_event.events[0].third_party_camera_frames[-1]
```

### 可用动作

导航相关：`MoveAhead`, `MoveBack`, `MoveLeft`, `MoveRight`, `RotateLeft`, `RotateRight`, `LookUp`, `LookDown`, `Teleport`, `Done`

物体交互（Phase 3）：`PickupObject`, `PutObject`, `OpenObject`, `CloseObject`, `ToggleObjectOn/Off`

### 场景选择

使用 **iTHOR** 场景（不用 ProcTHOR——多 Agent 有 bug）：
- 厨房：FloorPlan1-30
- 客厅：FloorPlan201-230
- 卧室：FloorPlan301-330
- 浴室：FloorPlan401-430

推荐 Phase 1 使用客厅（201-230），空间较大，适合多 Agent 移动。

## 游戏场景设计

### 场景 A：领地争夺（对抗）

**规则：**
- 2-3 个 Agent 在同一房间
- 维护一个 grid map，记录每个格子被谁占过
- Agent 每步占领当前格子，已被占的格子别人不能再占
- 目标：走过更多格子（占更多领地）
- 策略空间：可以选择快速扩张自己的领地，也可以去堵住对手的路

**VLM 每步接收的信息：**
1. 当前 Agent 的第一人称相机画面（base64 JPEG）
2. 俯瞰 grid map（标注自己位置 ★、对手位置 ●、已占/未占区域）
3. 结构化 JSON 元数据（位置、旋转、得分、剩余步数）

**VLM 每步输出：**
```json
{"reasoning": "对手在北边，我应该先占东南角...", "action": "MoveAhead"}
```

**终止条件：** 所有可达格子被占 或 达到最大步数（如 200 步）

**评价指标：**
- 每个 Agent 占领的格子数
- 领地连通性（连成一片 vs 碎片化）
- 是否出现"堵路"等涌现策略

### 场景 B：协作覆盖（合作）

**规则：**
- 2-3 个 Agent 在同一房间/公寓
- 维护一个 coverage map，记录哪些区域被任一 Agent "看到"
- Agent 的视野范围内的格子标记为"已覆盖"
- 目标：尽快让 coverage 达到 95%

**VLM 每步接收的信息：**
1. 当前 Agent 的第一人称相机画面
2. 俯瞰 coverage map（标注自己位置、队友位置、已覆盖/未覆盖区域）
3. 队友的最后已知位置和方向

**评价指标：**
- 达到 95% coverage 的总步数
- 工作均衡度（每个 Agent 贡献的覆盖面积比例）
- 是否出现"分工"等涌现行为

## 系统架构

### Phase 1：纯 Python + VLM API（Day 1-2）

```
┌─────────────────────────────────────┐
│           Game Controller           │
│  (Python script, 游戏逻辑+状态管理)  │
│                                     │
│  ┌───────────┐  ┌───────────┐      │
│  │ Agent 0   │  │ Agent 1   │ ...  │
│  │ VLM call  │  │ VLM call  │      │
│  └─────┬─────┘  └─────┬─────┘      │
│        │              │             │
│        ▼              ▼             │
│  ┌──────────────────────────┐      │
│  │      AI2-THOR Engine     │      │
│  │  (agentCount=N, iTHOR)   │      │
│  └──────────────────────────┘      │
└─────────────────────────────────────┘

每步循环：
1. 从 AI2-THOR 获取每个 Agent 的相机画面 + 元数据
2. 更新游戏状态（grid map / coverage map）
3. 生成俯瞰可视化
4. 为每个 Agent 构造 prompt（画面 + 地图 + 状态 JSON）
5. 调用 VLM API（Claude/GPT-4o）获取动作决策
6. 解析 VLM 输出，执行 controller.step(action=..., agentId=i)
7. 记录回放数据
```

### Phase 2：接入 OpenClaw（Day 3-5）

把 Phase 1 的直接 VLM 调用包装成 OpenClaw skill：
- 每个 Agent 对应一个 OpenClaw 实例（通过 Gateway 多 Agent 路由绑定）
- 每个实例有独立的 SOUL.md（定义策略风格）和 MEMORY.md（记住地图）
- 接入 Telegram/Discord，人可以实时观察和干预

### Phase 3：Isaac Lab 迁移（Week 2+）

- 用团队现有的 G1 velocity control 管线
- 双层架构：OpenClaw VLM 规划器（1-5 Hz）+ RL 运动策略（200 Hz）
- 通过 ROSClaw 或直接 Python 集成
- 场景使用 Omniverse USD 资产或 MolmoSpaces 转换

## VLM 调用策略

### 模型选择

| 用途 | 推荐模型 | 原因 |
|------|---------|------|
| 开发测试 | GPT-4o-mini | $0.002/100步，快速迭代 |
| 正式 demo | Claude Sonnet 4.6 / GPT-4o | 更好的空间推理能力 |
| 多 Agent 量跑 | 本地 Qwen-VL / VILA | 零边际成本 |

### Prompt 结构

```
[System] 你是一个在室内环境中导航的机器人 Agent。你在和其他 Agent 竞争/合作。
基于你看到的画面和地图信息，选择下一步动作。

[User]
<image: 第一人称相机画面>
<image: 俯瞰地图，标注你（★）和对手（●）的位置>

当前状态：
- 位置: (1.25, 0, -2.5)，朝向: 东
- 你的领地: 23 格，对手领地: 18 格
- 剩余步数: 157
- 上一步动作: MoveAhead (成功)

可选动作: MoveAhead, MoveBack, RotateLeft, RotateRight, Done

请用 JSON 回复: {"reasoning": "...", "action": "..."}
```

### 成本估算

320×240 图片 + 俯瞰图，每步 2 张图：
- GPT-4o-mini：~$0.00003/步 → 3 Agent × 200 步 = **$0.018/局**
- GPT-4o：~$0.0004/步 → 3 Agent × 200 步 = **$0.24/局**
- Claude Sonnet：~$0.0006/步 → 3 Agent × 200 步 = **$0.36/局**

## 实施计划

### Day 1：单 Agent VLM 导航闭环

**目标：** 一个 Agent 在 AI2-THOR 客厅里，VLM 看到画面后能做出合理的导航决策。

**产出：**
- `roboclaws/core/engine.py` — AI2-THOR controller 封装
- `roboclaws/core/vlm.py` — VLM API 调用封装（支持 Claude/GPT-4o/GPT-4o-mini）
- `roboclaws/core/visualizer.py` — 俯瞰图 + 第一人称画面拼接
- `examples/single_agent_explore.py` — 单 Agent 自由探索 demo

### Day 2：多 Agent 游戏逻辑

**目标：** 2-3 个 Agent 在同一场景，跑通对抗（领地争夺）和协作（覆盖探索）。

**产出：**
- `roboclaws/games/territory.py` — 领地争夺游戏逻辑
- `roboclaws/games/coverage.py` — 协作覆盖游戏逻辑
- `roboclaws/core/replay.py` — 游戏回放记录（帧序列 + 状态日志）
- `examples/territory_game.py` — 2v1 或 3 人领地争夺
- `examples/coverage_game.py` — 3 Agent 协作覆盖
- 录屏/GIF 展示涌现行为

### Day 3-5：OpenClaw 集成

**目标：** 每个 Agent 由一个 OpenClaw 实例控制，可通过 Telegram 实时交互。

**产出：**
- `roboclaws/openclaw/skill.py` — OpenClaw skill 封装
- `roboclaws/openclaw/bridge.py` — AI2-THOR ↔ OpenClaw Gateway 桥接
- `skills/ai2thor-navigator/SKILL.md` — OpenClaw 技能定义
- 每个 Agent 的 SOUL.md 模板

### Week 2+：Isaac Lab 版本

**产出：**
- `roboclaws/isaac/` — Isaac Lab 集成模块
- 双层架构（VLM 规划 + RL 运动）
- G1 velocity control 对接
- ROSClaw 桥接

## 文件结构

```
roboclaws/
├── README.md
├── CLAUDE.md
├── AGENTS.md
├── LICENSE
├── pyproject.toml
├── docs/
│   ├── technical-design.md          # 本文档
│   ├── openclaw-ecosystem.md        # OpenClaw 机器人生态调研
│   ├── simulation-platforms.md      # 仿真平台对比
│   └── references.md               # 参考链接汇总
├── roboclaws/
│   ├── __init__.py
│   ├── core/
│   │   ├── engine.py               # AI2-THOR controller 封装
│   │   ├── vlm.py                  # VLM API 调用（Claude/GPT）
│   │   ├── visualizer.py           # 俯瞰图生成、画面拼接
│   │   └── replay.py               # 游戏回放
│   ├── games/
│   │   ├── territory.py            # 领地争夺
│   │   └── coverage.py             # 协作覆盖
│   └── openclaw/
│       ├── skill.py                # OpenClaw skill 封装
│       └── bridge.py               # Gateway 桥接
├── examples/
│   ├── single_agent_explore.py
│   ├── territory_game.py
│   └── coverage_game.py
├── skills/
│   └── ai2thor-navigator/
│       └── SKILL.md
└── tests/
    └── ...
```

## 参考链接

### AI2-THOR
- AI2-THOR 官方：https://ai2thor.allenai.org/
- GitHub：https://github.com/allenai/ai2thor
- 多 Agent 示例：https://allenai.github.io/ai2thor-v2.1.0-documentation/examples
- iTHOR 场景列表：FloorPlan1-30（厨房）、201-230（客厅）、301-330（卧室）、401-430（浴室）
- MAP-THOR 多 Agent 基准：https://openreview.net/pdf?id=ZygZN5egzy

### OpenClaw
- OpenClaw 官方：https://openclaw.ai/ / https://github.com/openclaw/openclaw
- ROSClaw（ROS 2 桥接）：https://github.com/PlaiPin/rosclaw / arXiv:2603.26997
- DimensionalOS（G1 集成）：https://github.com/dimensionalOS/dimos
- ClawBody（MuJoCo 仿真）：https://github.com/tomrikert/clawbody
- RoClaw（双脑架构）：https://github.com/EvolvingAgentsLabs/RoClaw
- OpenGo（Go2 技能切换）：arXiv:2604.01708
- NemoClaw（NVIDIA 安全层）：https://github.com/NVIDIA/NemoClaw
- 多 Agent 路由文档：https://docs.openclaw.ai/concepts/multi-agent
- Skill 开发文档：https://docs.openclaw.ai/tools/skills
- Gateway 协议文档：https://openclawcn.com/en/docs/gateway/protocol/

### 仿真平台
- MolmoSpaces：https://github.com/allenai/molmospaces / arXiv:2602.11337
- Isaac Lab：https://github.com/isaac-sim/IsaacLab / arXiv:2511.04831
- AGILE（G1 运动）：https://github.com/nvidia-isaac/WBC-AGILE
- COMPASS（跨形态导航）：https://github.com/NVlabs/COMPASS
- GR00T N1.6：https://github.com/NVIDIA/Isaac-GR00T
- GR00T WBC：https://github.com/NVlabs/GR00T-WholeBodyControl
- ManiSkill3：https://github.com/haosulab/ManiSkill
- Habitat 3.0/PARTNR：https://github.com/facebookresearch/partnr-planner

### VLM 导航
- ImagineNav（ICLR 2025）：VLM 视角选择导航
- SayNav：LLM + 3D 场景图导航 / arXiv:2309.04077
- NaVILA：VLM + RL 双层导航 / arXiv:2412.04453
- SPF (See-Point-Fly)：VLM 像素坐标导航，100% 成功率（Gemini 2.5 Pro）

### 多 Agent 协作
- RoCo：多机器人 LLM 对话协作 / arXiv:2307.04738
- CoELA（ICLR 2024）：认知模块化 LLM 协作 Agent
- FurnMove（ECCV 2020）：AI2-THOR 双 Agent 家具搬运
- LLaMAR（NeurIPS 2024）：LLM 长时域多 Agent 规划
- Neural MMO：领地竞争驱动探索
- Voyager：LLM 开放世界终身学习 Agent
- Concordia：Game Master/Player 分离架构

### 相关项目
- Roboharness：https://github.com/MiaoDX/roboharness
- Robowbc：https://github.com/MiaoDX/robowbc
- NASA ROSA：https://github.com/nasa-jpl/rosa
- Claude Code 具身 Agent：arXiv:2601.20334
- Project Fetch（Anthropic）：Claude 控制 Unitree Go2
