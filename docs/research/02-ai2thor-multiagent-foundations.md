# AI2-THOR 多 Agent API 与 OpenClaw 集成技术细节

> 调研日期：2026-04-13
> 状态：已完成，关键规格已纳入技术设计

## AI2-THOR 多 Agent API

### 初始化与控制

通过 `agentCount` 初始化多 Agent，通过 `agentId` 分别控制。每次 `controller.step()` 只能移动一个 Agent（同步轮流制）。返回的 event 包含所有 Agent 的独立 Event 对象。

### 每个 Agent 的独立数据

- `event.events[i].frame`：独立的第一人称 RGB numpy 数组
- `event.events[i].depth_frame`：深度图（float32，米制）
- `event.events[i].metadata['agent']`：位置、旋转、cameraHorizon
- `event.events[i].metadata['objects']`：带 per-agent `visible` 标记的物体列表
- `event.events[i].metadata['lastActionSuccess']`：动作是否成功

### 碰撞与可见性

Agent 是 Unity 物理实体，**不能穿过彼此**。碰撞时动作失败（`lastActionSuccess=False`）。Agent **在彼此相机画面中可见**（作为胶囊体/角色模型）。FurnMove 基准明确要求 Agent "视觉预判碰撞"和"处理遮挡"。

### 移动模式

- **网格化**（默认）：`snapToGrid=True`，按 `gridSize` 步进，`rotateStepDegrees` 旋转
- **连续**：`snapToGrid=False`，任意距离/角度移动，支持噪声模拟

### 俯瞰视角

`GetMapViewCameraProperties` + `AddThirdPartyCamera` 获取正交俯瞰图。支持语义分割俯瞰。第三方相机可动态更新。

### ProcTHOR 多 Agent Bug

GitHub Issues #1169 和 #1265 记录：ProcTHOR 初始化 `agentCount=2` 只返回一个 event，控制 `agentId=1` 抛 TimeoutError。两个 issue 均未修复。**必须使用 iTHOR 场景。**

### 已知限制

- 无原生同时动作（只能轮流）
- 无内置 Agent 间通信
- 无 agentCount 上限文档，但渲染开销线性增长
- 多 Agent 文档稀少，实用指导来自 GitHub Issues 和学术论文
- 无可变形物体

## OpenClaw 架构

### SKILL.md 格式

YAML frontmatter（name, description, version, requirements）+ Markdown body（When to Use, How to Use, Rules, Examples）。存放在 `~/.openclaw/workspace/skills/<skill-name>/`。自动重载。可发布到 ClawHub（5,400+ 社区技能）。

### Gateway API

WebSocket 服务器（默认 `ws://127.0.0.1:18789`），JSON-RPC 2.0 风格。两种角色：operator（控制面）和 node（能力宿主）。支持 Tailscale/SSH/VPN 远程访问。

### 多 Agent 路由

单个 Gateway 进程内运行多个完全隔离的 Agent。通过 bindings 确定性路由：匹配 channel, accountId, peer, guild/team ID。最具体的 binding 优先。每个 Agent 有独立的 workspace, SOUL.md, MEMORY.md, skills。

### SOUL.md 和 MEMORY.md

- **SOUL.md**：Agent 人设（"角色卡"），注入每次会话上下文开头
- **MEMORY.md**：Agent 自己写的长期记忆，三层：Tier 1（始终加载，~100 行）→ Tier 2（日期记忆，自动加载今天+昨天）→ Tier 3（深度知识，语义搜索检索）
- 单文件截断限制 20,000 字符，聚合上限 150,000 字符

### 图像处理

独立 `imageModel` 配置，原生多模态模型（Claude Sonnet, GPT-4o）直接传原图。自动缩放到 JPEG 2048px。`detectImageReferences` 扫描文件路径和标注。

## VLM 导航 Prompt 策略

### 五种已验证方法（按效果排序）

1. **空间锚定（SPF/See-Point-Fly）**：VLM 在图像上输出像素坐标。Gemini 2.5 Pro 和 GPT-4.1 达到 100% 成功率。
2. **视角选择（ImagineNav, ICLR 2025）**：VLM 从候选视角中选最佳方向。GPT-4o-mini，HM3D 62% 成功。
3. **程序化状态（ProgPrompt）**：环境格式化为 Python 代码。
4. **3D 场景图（SayNav）**：子图转文本 prompt。
5. **拓扑地图（Guide-LLM）**：文本节点表示位置。

### Token 成本

320×240 图片：

| 模型 | Tokens/图 | 100 步成本 |
|------|----------|-----------|
| GPT-4o-mini (low detail) | 85 | $0.002 |
| GPT-4o (low detail) | 85 | $0.03 |
| Claude Haiku 4.5 | ~102 | $0.012 |
| Claude Sonnet 4.6 | ~102 | $0.037 |

3 Agent × 1000 步的总成本：$0.04（GPT-4o-mini）到 $0.74（Claude Sonnet）。

## MAP-THOR 与多 Agent AI2-THOR 生态

### MAP-THOR（NeurIPS 2024）

45 任务 × 5 楼层平面 = 225 对。支持 1-5 Agent。配套 LLaMAR 认知架构（Plan-Act-Correct-Verify），比先前方法高 30% 成功率。

### FurnMove（ECCV 2020）

2 Agent 在 AI2-THOR 客厅搬家具。SYNC-policies + CORDIAL loss，58% 完成率（比去中心化基线高 25 个百分点）。

### 其他

- **CoELA（ICLR 2024）**：5 模块认知架构，GPT-4 Agent 效率提升 40%+
- **COMBO（ICLR 2025）**：组合世界模型 + 树搜索
- **PARTNR（ICLR 2025, Habitat 3.0）**：100K 人机协作任务，LLM 仅 30% vs 人类 93%

## 灵感项目

- **Neural MMO**：128+ Agent 竞争自然驱动领地分化
- **OpenAI Hide-and-Seek**：简单竞争目标产生 6 阶段涌现策略
- **Voyager**：LLM 终身学习，自动课程 + 技能库 + 自验证
- **Concordia**：Game Master / Player 分离架构
- **Stanford Generative Agents**：观察 → 反思 → 规划的记忆架构

## 参考链接

- AI2-THOR: https://ai2thor.allenai.org/ / https://github.com/allenai/ai2thor
- 多 Agent 示例: https://allenai.github.io/ai2thor-v2.1.0-documentation/examples
- MAP-THOR: https://openreview.net/pdf?id=ZygZN5egzy
- LLaMAR: https://github.com/nsidn98/LLaMAR
- FurnMove: https://www.ecva.net/papers/eccv_2020/papers_ECCV/papers/123500460.pdf
- CoELA: https://umass-embodied-agi.github.io/CoELA/
- PARTNR: https://github.com/facebookresearch/partnr-planner
- ImagineNav (ICLR 2025): arXiv:2410.09874
- SayNav: arXiv:2309.04077
- SPF (See-Point-Fly): https://spf-web.pages.dev/
- Neural MMO: https://openai.com/index/neural-mmo/
- Voyager: https://voyager.minedojo.org/
- Concordia (DeepMind): Game Master/Player 架构
- OpenClaw 多 Agent 路由: https://docs.openclaw.ai/concepts/multi-agent
- OpenClaw Skill 文档: https://docs.openclaw.ai/tools/skills
- Gateway 协议: https://openclawcn.com/en/docs/gateway/protocol/
