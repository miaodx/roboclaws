# Roboclaws — 落地赛提交（2026-04）

> **一句话 wedge：** 让普通 Claude Code / Codex agent 通过 MCP 直接驾驶仿真机器人，并把“调 navigator skill”从人工盯屏，变成可重复、可追踪、可比较的 self-improvement loop。

> **平台报名短描述（<=300字）：**
> Roboclaws 让普通 Claude Code / Codex agent 通过 MCP 直接驾驶 AI2-THOR 仿真机器人，并把 navigator skill 调试纳入可重复的 harness 闭环。系统会自动 spawn fresh agent、跑任务、写 trace 和 runs-log，工程师只需 review 结果。真实 5 次同日迭代把同一 photo task 从 127+ calls / 3-of-9 提升到 37 calls / 9-of-9 / 3.8 分钟自动 done，还抓到了单测和 code review 都没发现的 goto 物理 bug。

> **飞书排版约定：**
> 这版正文优先使用列表和 code block，不依赖 markdown 表格。
> 推荐插图位置：
> 1. 开场故事线：`assets/evolution-storyline.svg`
> 2. 演化逻辑：`assets/mode3-self-improvement-loop.svg`
> 3. “先看 Run 001 → 005”之后：`assets/run-roi-staircase.svg`
> 4. “按落地赛五维评分标准看”之前：`assets/judge-score-evidence-map.svg`
> 可选补图：
> 5. 真实系统路径：`../../assets/readme-control-paths.png`
> 6. photo task 实景截图：`../../assets/readme-photo-task.png`
> 飞书直接粘贴时，建议优先使用当前 branch raw 链接；合并到 `main` 后再统一切回 `main` raw 链接。

---

## 团队信息

- 缪东旭 / `miaodongxu` / `miaodongxu@xiaomi.com`
- 丁松 / `dingsong1` / `dingsong1@xiaomi.com`

## 项目链接

- GitHub: https://github.com/MiaoDX/roboclaws
- 在线 demo 总入口: https://miaodx.com/roboclaws/
- OpenClaw demo 报告: https://miaodx.github.io/roboclaws/openclaw/demo/report.html
- 报告对比页: https://miaodx.github.io/roboclaws/report_compare.html
- Self-improvement loop 设计文档: [`docs/harness-self-improvement-loop.md`](../../harness-self-improvement-loop.md)
- Harness logbook 总索引: [`harness/PLAN.md`](../../../harness/PLAN.md)
- 评委自助验证指南: [`EVALUATION_GUIDE.zh-CN.md`](./EVALUATION_GUIDE.zh-CN.md)

## 先看故事线：Roboclaws 不是单点 demo，而是四段式演化

```text
Phase 1  Direct VLM games       先证明“图像 + map + structured state”足够驱动机器人决策
Phase 2  OpenClaw Gateway       再证明“SOUL / memory / browser UI / named agents”可以稳定跑通
Phase 3  Mode 3 + harness       最后证明“fresh spawn + 可比较 rerun + self-improvement loop”成立
Phase 4  Railway appliance      把前面能力压成对外可访问、可传播、可复查的 hosted 形态
```

![Evolution storyline](https://raw.githubusercontent.com/MiaoDX/roboclaws/docs/hackathon-2026-04-landing/docs/hackathon/2026-04-landing/assets/evolution-storyline.svg)

第一次看这个 repo，很容易把它误读成“一个 Mode 3 + harness 的提交”。这会低估项目真正的完成度。

Roboclaws 现在同时保留 Direct VLM、OpenClaw、Mode 3、Railway appliance 四条入口，不是因为没有收敛，而是因为每一层都回答了不同的问题：

- Direct VLM 负责最低成本验证任务设计、prompt 设计、provider 行为和多 agent 游戏机制。
- OpenClaw 负责长期 agent runtime、SOUL / memory、浏览器 Control UI、photo smoke 这条更接近真实使用的链路。
- Mode 3 负责 clean spawn、append-only logbook、同任务多轮比较，这是 self-improvement loop 真正成立的关键。
- Railway appliance 负责把前面的能力压成一个可以直接展示给别人看的 hosted 形态，而不是只能作者本机演示。

如果只记一句，可以把它记成：

```text
Can move    → Phase 1  Direct VLM
Can live    → Phase 2  OpenClaw
Can improve → Phase 3  Mode 3 + harness
Can ship    → Phase 4  Railway appliance
```

![Mode 3 self-improvement loop](https://raw.githubusercontent.com/MiaoDX/roboclaws/docs/hackathon-2026-04-landing/docs/hackathon/2026-04-landing/assets/mode3-self-improvement-loop.svg)

## 评委 30 秒扫读

```text
它是什么：
面向 AI coding agent 的机器人仿真 driver + self-improvement harness

它解决什么：
agent 能跑，但“调 skill 这件事”仍然靠工程师盯 trace、盯屏幕、记经验

它怎么做：
Mode 3（MCP 直驾） + just harness::run <task> + append-only logbook

为什么值得继续看：
它不是概念 demo，而是已经有 5 次同日真实迭代、live report、可复现命令、真实 bug 案例的工程闭环
```

## 项目现在到什么程度

```text
核心 Python 源码          9,193 行 / 30 个模块
测试代码                 12,252 行 / 41 个 test 文件
operating modes          4 个（Direct VLM / OpenClaw / Mode 3 / Railway appliance）
self-improvement logbook 5 次同日连续 run
公开产物                 GitHub Pages live reports + report_compare + harness runs-log
工程护栏                 tests + ruff + GitHub Actions + append-only run index
```

这组数字的意义不是“代码很多”，而是说明这个项目已经越过了“概念 demo”的阶段：

- 有公开可点开的 live report 和 replay 产物
- 有可复现的本地命令，而不是只放视频
- 有连续 5 次迭代的 logbook，而不是只挑最好的结果展示
- 有测试、CI、trace.jsonl、runs-log 这类可复核证据在托底
- 4 个 operating modes 对应的是一条完整演化链，而不是互相竞争的平行 demo

## 这不是“再做一个机器人 demo”，而是把 agent 调试变成可测量的迭代基础设施

在这个 repo 里，我们真正想解决的问题不是“机器人能不能动”，而是：

> **一个 coding agent 跑完机器人任务以后，工程师能不能有把握地说：这次迭代真的更好了。**

如果没有 harness，这件事通常只能靠印象判断，至少有三类结构性问题：

1. **没有 baseline**
   “这次感觉快一点”没有证据。tool calls、blocked moves、target coverage、wall-clock 如果不被结构化记录，下一轮就没法比较。
2. **没有 bug-class isolation**
   某些 bug 只会在真实物理仿真里出现，mock/FakeEngine 天生抓不到。没有 live single-run，就只能靠运气撞。
3. **没有 session memory**
   上一轮踩到的坑如果只留在聊天上下文里，下一轮又会重来一遍。logbook 必须是 append-only、可被新会话直接读取的外部记忆。

Roboclaws 的 harness 把这三件事都工程化了：

```text
task.txt
  ↓
just harness::run <task>
  ↓
tmux spawn fresh Claude / Codex process
  ↓
MCP server → AI2-THOR → trace.jsonl / snapshots / metrics.txt
  ↓
runs-log/NNN-<task>.md
  ↓
下一轮只改一个变量，再比较
```

这个 loop 的核心价值不是“让 agent 更酷”，而是让每次改 skill / MCP tool / prompt 之后的结果变得**有数字、有对照、有记忆**。

## 先看最硬的一组数字：同一天、同一任务、5 次迭代

任务固定为：

> “给客厅每个沙发和椅子拍照片，确保视野中大部分都是对应的家具。”

```text
Run 001  manual baseline                         127+ calls   3/9  user interrupt
Run 002  harness 托管，无代码改动                 55 calls    3/9  done
Run 003  + scene_objects + skill 改写            65 calls    9/9  timeout @ 600s
Run 004  + goto（引入 y 坐标 bug）               aborted     —    10/10 goto failed
Run 005  修复 goto y 坐标                         37 calls    9/9  done in 3.8 min
```

这组数据最重要的不是“Run 005 很漂亮”，而是：

- **Run 001 → Run 005：tool calls 减少 71%，target coverage 从 3/9 提升到 9/9**
- **Run 004 明确暴露了一个 FakeEngine 和 code review 都没抓住的物理 bug**
- **每一轮只改一个主要变量，所以 metric delta 是可归因的**

这就是评委在落地赛里真正应该关心的点：不是 agent 是否偶尔跑通，而是这套系统是否能稳定地把下一轮做得更好。

![Run ROI staircase](https://raw.githubusercontent.com/MiaoDX/roboclaws/docs/hackathon-2026-04-landing/docs/hackathon/2026-04-landing/assets/run-roi-staircase.svg)

## 为什么最后收敛到 Mode 3，但 VLM / OpenClaw 没有消失

Roboclaws 不是一开始就冲着“Mode 3 + harness”去的。它是被真实研发问题一步步逼出来的：先要证明机器人能动，再要证明长期 agent runtime 成立，最后才会逼出“怎么 clean rerun、怎么真正持续变好”。

### Phase 1 · 直接调 VLM API：先证明“机器人可以被图像驱动”

最早的入口是 direct VLM games。`examples/single_agent_explore.py`、`examples/territory_game.py`、`examples/coverage_game.py` 这几条路径完成了最基本但最关键的一步：

- 图像 + overhead map + structured state 足够让模型做导航 / 占地 / 协作决策
- AI2-THOR 这套环境足够快，值得继续往前投工程量
- provider 切换、prompt 设计、动作空间设计这些问题，可以先用最低成本验证

但这个阶段也很快碰到上限：

- 每一步都是独立 chat completion，没有“agent 进程”的 clean lifecycle
- baseline 很难固定，同样任务每次上下文都不完全一样
- 外部 harness 很难 cleanly 重复 spawn “同一个 agent”

所以 Phase 1 的价值不是“它已经完整”，而是它先把“这条路能走”验证掉。没有这个阶段，后面的 OpenClaw 和 Mode 3 都没有扎实起点。

### Phase 2 · OpenClaw Gateway：再证明“长期 agent runtime + UI + SOUL / memory”成立

切到 OpenClaw 以后，项目第一次拥有了更接近真实 agent system 的能力：

- named agents
- SOUL / memory
- browser Control UI
- `examples/openclaw_demo.py`、`examples/openclaw_photo_task.py`
- `just chat::run` 与 `just openclaw::run photo`
- 最后还沉淀出了 Railway appliance 这条 hosted 路线

这一步对评委非常重要，因为它说明 Roboclaws 不是“脚本调用几个 VLM API”而已，而是真的把 agent runtime、tool surface、交互入口做出来了。

但它仍然不适合做“清洁、可重复、无污染”的 iteration loop：

- Gateway 是常驻服务
- agent 状态在 Gateway 进程里
- SOUL / chat history / memory 会污染下一次 run
- 长期 runtime 的优势，恰好和 benchmark / rerun 需要的 clean slate 形成张力

所以 OpenClaw 没有失败，只是它回答的是另一个问题：

> **能不能让 agent 长期在线、带人格、带记忆、可从浏览器和 hosted appliance 里被人使用。**

这个答案是肯定的，而且现在 repo 里依然完整保留着。

### Phase 3 · Mode 3 + self-improvement harness：最后证明“系统可以稳定变好”

直接让 Claude Code / Codex 通过 MCP 驾驶 AI2-THOR。关键不是模型更强，而是 process shape 终于对了：

- coding agent 本身就是一次性 CLI 进程
- 可以被 tmux clean spawn
- 可以被 harness 统一 teardown
- 每次 run 都天然 fresh
- 产物可以标准化落到 `trace.jsonl`、`metrics.txt`、`runs-log/*.md`

```text
维度                  | Phase 1: VLM 直调         | Phase 2: OpenClaw Gateway   | Phase 3: Mode 3
fresh agent spawn     | 不自然，状态分散           | 不干净，SOUL / memory 常驻   | 天然支持，一次性 CLI 进程
external harness 托管 | 难                         | 难                           | 已实现
trace 可标准化        | 分散在 chat 历史            | 分散在 Gateway log           | trace.jsonl + run_dir
多轮比较是否公平       | 不稳定                     | 易受状态污染                  | 每轮都是干净起点
```

这也是为什么现在 repo 同时保留 4 个 mode，但只有 Mode 3 成了“自我提升闭环”的主路径。不是别的 mode 没用，而是 **Mode 3 是唯一天然适合做 clean rerun 的形态**。

### 这四条路径今天各自负责什么

```text
最快验证任务 / provider / prompt            → Direct VLM
长期 agent runtime + SOUL / memory + UI    → OpenClaw
clean rerun + benchmark + self-improvement  → Mode 3 + harness
对外 demo / hosted 展示 / adoption wedge   → Railway appliance
```

这恰恰是评委应该看到的地方：Roboclaws 不是“删掉旧路线、只剩一个比赛版故事”，而是把每一层都沉淀成今天 submission 的证据链。

## 5 次迭代到底干了什么

### Run 001 — Manual baseline

工程师手动给 Claude Code 派任务，用当时 main 分支上的 navigator skill。

暴露出的 5 个真实摩擦点：

1. **yaw 约定要从零摸**
   前 30 步都在重新确认 yaw=0 对应哪个方向。
2. **物体发现是被动的**
   没看到椅子之前，agent 不知道去哪里找。
3. **L 形沙发困住 agent**
   连续 blocked，没有对象级导航信息。
4. **map PNG 只能看，不能查**
   对程序化决策帮助很弱。
5. **拍一张照片的 framing 成本很高**
   一次有效拍摄至少要 `MoveAhead → LookDown ×2 → observe`。

结果是：127+ calls 之后只拍到 3/9 个目标，工程师最终按停。

### Run 002 — Autonomous baseline（无代码改动）

同样任务，不改代码，只是把它放进 `harness::run` 里，让 agent 自己跑、自己结束。

这一步最重要的意义不是结果变好，而是 **证明 harness 本身成立**：

- 55 calls
- 3/9 targets
- `done`

换句话说：我们先验证“measurement loop 能跑”，再验证“measurement loop 能带来改进”。

### Run 003 — `scene_objects` + skill 改写

基于 Run 001 的两个核心痛点：

- 物体发现太晚
- 一张照片的 planning / framing 太贵

我们做了两个变化：

- 新增 `scene_objects(filter_types=...)` MCP tool
- 在 `SKILL.md` 里加入 inventory-first protocol

结果：

- 65 calls
- 9/9 targets
- timeout @ 600s

这轮非常关键，因为它说明：

- **skill / tool 层的改变可以直接把覆盖率从 3/9 拉到 9/9**
- 但即便覆盖率上来了，grid-step navigation 仍然太慢
- 这给下一轮 `goto` 提供了非常清晰的动机

### Run 004 — `goto` 上线，但真实物理 bug 当场翻车

Run 003 的瓶颈已经很明确：不是找不到目标，而是移动太慢。

所以新增了 `goto(object_id, distance=1.0)`，想让 agent 用 AI2-THOR 的 Teleport 直接到目标附近。

结果是：

- 10/10 `goto` 调用全部失败
- 错误为 `InvalidOperationException: Collided with: Floor`
- harness 在约 272 秒时直接中止运行

根因非常具体：

- Teleport 传入的 y 坐标用了 `target.bbox.center.y`
- 这个值对应的是椅子/沙发等目标物的 bbox 高度，而不是 agent 当前 standing y
- 于是 collision capsule 直接钻进地板，Unity 拒绝执行

这里最重要的一点不是 bug 本身，而是：

> **FakeEngine 单测没抓到这个问题，code review 也抓不到，但 harness 在真实仿真里 5 分钟内抓到了。**

这正是 self-improvement harness 的工程价值。

### Run 005 — 修复 `goto`，闭环打通

修复方式很简单，但只能在 Run 004 这种 live probe 之后才能确定：

- 从 `target.bbox.center.y` 改成读取 `agent.position.y`

重跑后：

- 37 calls
- 9/9 targets
- 0 blocked moves
- 10/10 `goto` 成功
- 3.8 分钟自动 `done`

还有一个很有意思的二级现象：

- agent 开始自己平衡 `observe` 和 `observe_archived`
- 最后形成了更偏向便宜归档版本的调用比例
- 这不是硬编码，而是 SKILL.md + tool surface 共同塑造出来的行为

换句话说，系统不只是“快了”，而是开始出现了更成熟的 agent 操作策略。

## 按落地赛五维评分标准看 Roboclaws

![Judge score evidence map](https://raw.githubusercontent.com/MiaoDX/roboclaws/docs/hackathon-2026-04-landing/docs/hackathon/2026-04-landing/assets/judge-score-evidence-map.svg)

## 1. 需求匹配度（20）

这不是一个“为了比赛造出来的炫技项目”，而是一个非常具体的研发痛点：

```text
目标用户：
机器人算法工程师、仿真平台研发、具身智能 / Agent infra 开发、测试工程师

典型场景：
改 navigator skill、改 MCP tool、改 prompt 之后，如何快速知道这轮到底更好了没有

核心痛点：
1. 没有可量化 baseline
2. 真实物理 bug 不一定能被 mock / FakeEngine 抓到
3. 上一轮的经验如果不落到 logbook，下一轮会重新踩坑
```

这三个痛点都不是抽象口号，而是都在 Run 001–005 里被实际触发过，并且都能指回真实文件：

- [`docs/harness-self-improvement-loop.md`](../../harness-self-improvement-loop.md)
- [`harness/PLAN.md`](../../../harness/PLAN.md)
- [`harness/runs-log/001-photo-living-room.md`](../../../harness/runs-log/001-photo-living-room.md)
- [`harness/runs-log/004-photo-living-room.md`](../../../harness/runs-log/004-photo-living-room.md)

对评委来说，需求匹配度的重点不该是“机器人会不会动”，而该是：

> **这个项目有没有抓住 agentic robotics 里最贵、最卡人的那一段工程摩擦。**

Roboclaws 抓住了，而且用一个非常具体的 photo task 把问题钉住了。

## 2. 落地可行性（25）

这是 Roboclaws 最容易拿高分的维度之一，因为它已经具备完整的可复核闭环。

直接可跑的命令路径：

```bash
uv pip install -e ".[dev,openclaw]" || python -m pip install -e ".[dev,openclaw]"
just harness::list-tasks
just harness::history
just harness::run photo-living-room
```

跑完不是一句“成功”，而是会得到：

```text
trace.jsonl
server.log
metrics.txt
snapshots/agent-0/*
runs-log/<NNN>-<task>.md
```

此外，repo 不是只有一条 happy path，而是已经有 4 个实际运行模式：

- Direct VLM games
- OpenClaw Gateway demos
- Mode 3 coding-agent direct driver
- Railway appliance

并且这 4 个 mode 共用同一个 `MultiAgentEngine` 核心和统一的 MCP contract。对评委来说，这意味着：

- 不是 demo 脚本堆出来的单点功能
- 不是只能作者本机跑起来的私有流程
- 不是改一处、三处不同步的 fragile 原型

最直接的证据路径：

- [`ARCHITECTURE.md`](../../../ARCHITECTURE.md)
- [`docs/coding-agent-nav-server.md`](../../coding-agent-nav-server.md)
- [`docs/openclw/openclaw-local.md`](../../openclw/openclaw-local.md)
- https://miaodx.github.io/roboclaws/openclaw/demo/report.html

## 3. 业务价值（25）

Roboclaws 的业务价值不在于“替代机器人算法本身”，而在于给 agentic robotics 的研发迭代装上了一个**低成本、可比较、可持续的验证闭环**。

当前可以明确量化的收益，不是假设性的“未来也许能省”，而是这 5 次迭代已经证明的：

```text
旧方式：一次 skill 调试 ≈ 30 分钟工程师连续盯屏
新方式：一次 run ≈ agent 后台执行 + 工程师最后几分钟 review
Run 001 → Run 005：127+ calls / 3-of-9 → 37 calls / 9-of-9 / 3.8 min
```

业务价值体现在三个层面：

1. **工程师注意力回收**
   不是让 wall-clock 归零，而是把“必须盯着的时间”压到最低。
2. **真实 bug 更早暴露**
   Run 004 那种物理 bug，如果没有 harness，往往要拖到更晚、成本更高的阶段才暴露。
3. **迭代从拍脑袋变成 measured loop**
   以后每加一个 task class，都能直接接到这套 logbook + metrics 体系上。

对团队落地路径来说，它已经有一个非常清楚的内部 adoption 顺序：

```text
Stage 1  当前：photo-living-room，证明 loop 成立
Stage 2  下一步：多房间 inventory / grasp+place，证明跨 task 泛化
Stage 3  再下一步：把 logbook 聚合、加 token / cost telemetry，进入长期团队使用
```

这不是 consumer-facing 的收入故事，而是非常典型的研发效能 / agent infra ROI 故事。对于应用落地赛，这种“能直接让一个团队更敢放手用 agent”的价值是非常实的。

## 4. 用户体验（15）

Roboclaws 的 UX 不是面向普通消费者，而是面向工程师、评委和 operator 的工作流 UX。

它的体验设计有几个明显优点：

- **入口简单**
  `just harness::run <task>` 就是主入口，task 本身是 plain-text prompt。
- **结果可读**
  `runs-log/<NNN>.md` 是 human-readable logbook，不需要翻原始 trace 才能知道发生了什么。
- **证据有层次**
  想快速看结论看 run log，想看细节看 `trace.jsonl`，想看画面看 snapshots / report。
- **评委可自助验证**
  这次提交还专门配了 [`EVALUATION_GUIDE.zh-CN.md`](./EVALUATION_GUIDE.zh-CN.md)，5 分钟和 15 分钟路径都给了。

这类工程工具的高分 UX 不一定来自最华丽的界面，而来自：

> **用户是不是能在最少的上下文切换里，完成“发起一次 run → 看结论 → 判断下一步”的整套动作。**

在这一点上，Roboclaws 的设计已经非常接近团队内部真正会长期使用的工具形态。

## 5. 可复用性（15）

Roboclaws 的可复用性来自于它不是“一个 task 的脚本”，而是一组稳定边界：

- **统一的引擎核心**
  `MultiAgentEngine` 被 4 个 operating mode 复用。
- **统一的 MCP contract**
  `observe / move / done` 是 coding agent、OpenClaw、Railway appliance 都在消费的公共表面。
- **统一的 skill 文件**
  [`skills/ai2thor-navigator/SKILL.md`](../../../skills/ai2thor-navigator/SKILL.md) 同时被 Mode 2 / 3 / 4 共享。
- **统一的 run artifact**
  `trace.jsonl`、`runs-log`、`run_dir` 这些结构，不依赖单个 task。
- **任务定义足够轻**
  新 task 只要新增一个 `harness/tasks/<name>.txt`，就能直接纳入同一套 loop。

也就是说，Roboclaws 可复用的不只是代码，而是：

```text
driver protocol
skill contract
task format
artifact schema
run-to-run comparison workflow
```

对评委来说，这意味着它不是“photo-living-room 专用项目”，而是一层能继续承载更多 embodied agent task 的基础设施。

## 三个最有说服力的真实证据

### 1. Run 003 证明“skill / tool 调整确实有价值”

- `scene_objects` + inventory-first protocol 一上，目标覆盖率立刻从 3/9 拉到 9/9
- 说明这套 loop 确实能区分“真正有效的变化”

### 2. Run 004 证明“没有 live probe 的测试套件不够”

- `goto` 的 y 坐标 bug 在 FakeEngine 里过不出问题
- 但在真实 AI2-THOR 里 10/10 Teleport 全失败
- 这是 harness 存在最硬的一条理由

### 3. Run 005 证明“闭环不是只会报错，也能收敛到 clean done”

- 37 calls
- 9/9 targets
- 0 blocked moves
- 3.8 分钟 `done`

这意味着这个 loop 不只是“找问题”，还确实能把问题推向更好的下一个状态。

## 评委最可能质疑的 3 个问题，我们先回答

### 质疑 1：只跑过一个 task class，会不会只是 lucky run？

这是目前最真实的边界，我们不回避。

但这不构成对核心 wedge 的否定，因为 Roboclaws 当前证明的不是“所有任务都 solved”，而是：

- clean rerun 成立
- 结构化比较成立
- 单变量迭代成立
- live probe 能抓到测试抓不到的问题

下一步扩任务类，是在这个已经成立的 loop 上向外扩，不是重新发明一套系统。

### 质疑 2：为什么不用 OpenClaw Gateway 路径做闭环？

因为 Gateway 的价值和 harness 的价值不同：

- Gateway 适合长期 agent runtime
- harness 适合 repeated experiment

前者要记忆和持久状态，后者要 clean spawn 和无污染比较。Roboclaws 不是否定 Gateway，而是找到了“什么时候必须不用 Gateway”。

### 质疑 3：AI2-THOR 是合成场景，会不会离真实机器人太远？

这个质疑成立一半。

是的，AI2-THOR 不是 Isaac Sim，更不是真机。但 Roboclaws 当前在解决的不是最终实物部署，而是：

> **agentic robotics 里“怎么让一次 skill 改动变成可测量、可比较、可追溯的下一轮迭代”这一层问题。**

这个 wedge 对 simulator 是相对独立的。未来是否切平台，会改变下层环境，不会改变这套 loop 的上层逻辑。

## 工程化与公开证据路径

如果评委只想抓最硬的证据，建议看这几个位置：

```text
1. harness/PLAN.md
   看 5 个 run 的索引和 headline

2. harness/runs-log/004-photo-living-room.md
   看 goto 物理 bug 是怎么被 harness 抓出来的

3. harness/runs-log/005-photo-living-room.md
   看 clean closure 的最终结果

4. docs/harness-self-improvement-loop.md
   看这套 loop 为什么不是“又一个脚本”，而是一套设计过的测量流程

5. ARCHITECTURE.md
   看 4 个 mode 如何共用同一个内核

6. skills/ai2thor-navigator/SKILL.md
   看被 harness 持续优化的真实对象是什么
```

这 6 个位置足够支撑评委对五个维度的大部分判断。

## 下一步 Roadmap（已经明确，不是空泛愿景）

从 `harness/PLAN.md` 的 active carry-forward 看，下一轮最明确的工作有四项：

- **下一个 task class**
  从 photo-living-room 扩到多房间 inventory 或 grasp+place。
- **跨 run 聚合**
  做 `harness/scripts/summarize.py`，把 trace 聚成 metrics CSV。
- **token / cost telemetry**
  把 agent 迭代成本也纳入 loop，而不是只看行为结果。
- **agent reasoning capture**
  如果下一类 bug 需要，就切到更细的 transcript capture 路径。

这组 roadmap 的特点是：它们都建立在当前 loop 已经打通的前提上，不是“如果以后有空就另起炉灶”。

## 局限（坦诚）

1. **当前只在一个 task class 上打穿闭环**
   photo-living-room 已经被跑通，但跨 task 泛化还要靠下一轮验证。
2. **AI2-THOR 仍然是合成仿真**
   对 manipulation fidelity 的上限低于 Isaac Sim / 真机。
3. **目前主要先用 Claude CLI 打通**
   Codex CLI 适配已经开始，但还没有像 Claude 那样积累完整多轮 run log。

这些局限不会推翻当前提交的价值，但会影响它在不同维度上的上限。我们选择把这点明确写出来，而不是把“已经验证”和“下一步计划”混为一谈。

## 反馈渠道

- GitHub Issues: https://github.com/MiaoDX/roboclaws/issues
- Live demos: https://miaodx.com/roboclaws/
- Harness logbook: https://github.com/MiaoDX/roboclaws/tree/main/harness/runs-log
- 评委自助验证指南: [`EVALUATION_GUIDE.zh-CN.md`](./EVALUATION_GUIDE.zh-CN.md)

如果你帮我们找出这份提交里的硬伤，比如：

- 某个数字复核后对不上
- 某个 run 的叙述与 logbook 不一致
- 某条高分判断其实证据不够

那对这个项目来说不是坏事，而是最有价值的输入。这个项目本来就是用来把“印象”换成“可复核证据”的；评审阶段也应该遵守同一套原则。
