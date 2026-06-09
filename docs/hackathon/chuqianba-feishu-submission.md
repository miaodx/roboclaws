# Roboclaws：给机器人以大脑

> 把开放式机器人任务组织成可运行、可观察、可复盘、可迁移的 Agent Skill Loop。

## 一句话简介

Roboclaws 是一个“给机器人以大脑”的 Agent 工程闭环：让 Codex、Claude Code 等 Coding Agent 通过受控 MCP 工具执行机器人开放式任务，并把每次运行沉淀成可复盘的 trace、runtime map、before/after 图像、评分和 HTML report。

它不是单个机器人 demo，而是一套从仿真到真机的 `task -> skill -> tool -> backend -> report` 工作流。当前已经跑通导航、拍照、语义建图、家庭清洁、Nav2 真机导航/感知 pilot 等场景，并持续补充真机运行材料。

如果只记一句话：

```text
给机器人以大脑，不是给机器人接一个模型，
而是让机器人任务能运行、能失败、能留下证据、能被改进。
```

![Roboclaws skill loop](https://raw.githubusercontent.com/MiaoDX/roboclaws/main/docs/blog/assets/robot-brain-skill-ladder.png)

## 一、场景需求 / 痛点描述

机器人接入大模型之后，做一个“会动”的 demo 并不难。真正困难的是：如何让机器人持续完成开放式任务，并让每次运行都能被复盘、被验证、被改进。

在机器人研发和验证过程中，一个任务往往横跨自然语言目标、地图、视觉观察、导航、操作工具、仿真/真机 backend 和评估报告。传统做法里，策略散落在 prompt、临时脚本、SDK 调用和人工经验里；机器人跑完以后，工程师还要手动翻日志、看截图、判断是否真的完成任务，下一轮调优也很难知道到底哪里变好了。

Roboclaws 希望解决的是“给机器人以大脑”这件事：不是简单给机器人接一个模型，而是把开放式机器人任务组织成可复用的 Agent Skill Loop。Agent 可以根据任务选择 Skill，通过受控 MCP 工具观察、建图、导航、拾取/放置，并把每次运行沉淀为 trace、runtime map、before/after 图像、评分和 HTML report。这样机器人任务不再是一次性 demo，而是一个可运行、可观察、可复盘、可迁移到真机的工程闭环。

### 目标用户

- 机器人算法工程师。
- 具身智能 / Agent infra 开发。
- 仿真平台和测试工程师。
- 机器人应用 demo 和评测团队。
- 未来可扩展到真实机器人 operator 和场景交付团队。

### 真实痛点

1. **任务经验容易散落**  
   策略分散在 prompt、临时脚本、机器人 SDK、仿真日志和人工经验里，下一轮经常重新踩坑。

2. **运行过程不可审查**  
   机器人可能完成了任务，也可能只是看起来完成了。没有结构化 trace、agent view、地图和报告时，工程师很难判断它到底做了什么。

3. **仿真到真机缺少统一合同**  
   仿真、Isaac、MolmoSpaces、Nav2、Agibot 等 backend 都有自己的原语。Agent 如果直接学习 backend API，迁移成本高，也容易混淆哪些能力真实可用。

4. **评估边界容易作弊或说不清**  
   robot task 往往有 private scoring truth、隐藏目标、真实环境限制和 report-only 证据。Agent 输入和评估证据如果不分离，就很难证明方案可靠。

5. **调优缺少 Before/After**  
   改了 Skill 或工具后，效果是“感觉更好”还是“真的更好”，需要 run-to-run 指标、失败证据和可复现 artifact 支撑。

## 二、实现方案

Roboclaws 的核心思路是：把机器人智能放到一个能运行、能留下证据、能被人和 Agent 一起改进的位置。

我们把开放式机器人任务拆成几层：

```text
open-ended robot goal
  -> runnable task
  -> agent skill
  -> bounded MCP capability tools
  -> simulator / real-robot backend
  -> trace / runtime map / report
  -> skill improvement
```

![Skill-first architecture](https://raw.githubusercontent.com/MiaoDX/roboclaws/main/docs/blog/assets/robot-brain-skill-ladder.svg)

### 1. Runnable Task：把开放目标变成可运行入口

典型任务包括：

- `semantic-map-build`：机器人从公共地图和观察出发，构建运行时语义地图。
- `household-cleanup`：机器人基于观察、地图和工具调用完成家庭清洁任务。
- `ai2thor-nav`：机器人在仿真环境里完成导航、探索、拍照等任务。

任务不是一个临时脚本，而是有输入、参数、报告和验收口径的公开运行入口。

### 2. Agent Skill：承载机器人完成任务的经验

Roboclaws 不把所有智能都塞进 prompt，也不把整件事藏进一个大工具。Skill 负责沉淀任务经验：

- 先观察什么。
- 什么时候建图。
- 什么时候导航。
- 什么时候拾取、放置。
- 失败后怎么恢复。
- 哪些证据必须写进 report。
- 哪些信息不能泄漏给 Agent。

这样每次运行的经验不会停留在某次聊天上下文里，而是进入可以复用、可以检查、可以迭代的 Skill Loop。

### 3. MCP Capability Tools：保留清晰能力边界

我们不暴露一个不透明的 `cleanup_room()`，而是让 Agent 调用受控、可审计的能力工具：

```text
observe
metric_map
navigate
pick
place
open / close
done
```

工具越大，demo 越快；边界越清楚，智能越可迁移。Roboclaws 的选择是：让 Skill 负责策略，让 MCP 工具保持稳定能力边界。

![Bounded MCP tools](https://raw.githubusercontent.com/MiaoDX/roboclaws/main/docs/blog/assets/robot-brain-mcp-bounded.png)

### 4. Runtime Map 和 Report：让每次运行都能复盘

每次 serious run 都会留下结构化证据：

```text
trace.jsonl
agent_view.json
run_result.json
runtime_metric_map.json
before / after images
report.html
```

这些 artifact 不是为了好看，而是为了回答几个关键问题：

- Agent 当时到底看到了什么？
- 它调用了哪些工具？
- 它怎么决定下一步？
- 任务有没有真的完成？
- 哪些证据是 Agent 输入，哪些只是 report-only？
- 下一轮应该改 Skill、改工具、改地图，还是改 backend？

![Runtime map evidence](https://raw.githubusercontent.com/MiaoDX/roboclaws/main/docs/blog/assets/robot-brain-runtime-map.png)

### 5. Backend Variant：同一个大脑可以换身体

Roboclaws 的 public task / skill / tool / report 边界不绑定单一仿真。当前已经覆盖或验证到：

- AI2-THOR：导航、覆盖、拍照、早期 VLM 行为验证。
- MolmoSpaces / MuJoCo：家庭清洁、before/after、report、semantic substeps。
- Isaac：更真实的 USD scene、camera、segmentation 和 robot-view evidence。
- Nav2 真机 pilot：真实机器人导航/感知边界验证。
- Agibot G2：作为后续真实机器人 backend variant 的合同和运行路径。

这里的设计原则是：

```text
backend 是身体，skill loop 才是 brain。
```

![Backend variants](https://raw.githubusercontent.com/MiaoDX/roboclaws/main/docs/blog/assets/robot-brain-backend-matrix.png)

## 三、业务价值（含 Before / After 数据）

Roboclaws 的价值是把机器人 Agent 研发从“人工盯屏 + 经验判断”，变成“Agent 自动执行 + 结构化报告复盘 + 下一轮可量化改进”。

### 1. 旧方式 vs Roboclaws

**Before：**

一次机器人 Agent 任务跑完后，工程师需要人工盯过程、翻日志、核对截图和评分，调优主要依赖经验。任务策略经常散落在 prompt、脚本和临时记录里，下一轮很难精确知道哪里变好了。

**After：**

一条任务命令即可生成可复盘报告，包含工具调用、地图、前后对比、评分、失败原因和下一轮改进依据。它让机器人 Agent 的研发验证从“看起来能跑”变成“能证明它为什么能跑、哪里失败、下一轮如何变好”。

### 2. 已有真实数据

#### Photo task：从人工盯屏到可量化闭环

在 `photo-living-room` 任务中，我们固定任务目标：“给客厅每个沙发和椅子拍照片，确保视野中大部分都是对应家具。”

同一任务的迭代结果：

| 指标 | Before | After |
| --- | --- | --- |
| tool calls | 127+ | 37 |
| 目标覆盖 | 3/9 | 9/9 |
| 目标覆盖率 | 33% | 100% |
| 完成状态 | 人工中断 | 自动 done |
| 完成时间 | 未能稳定完成 | 3.8 分钟 |

这意味着：

- tool calls 减少约 71%。
- 目标覆盖从 3/9 提升到 9/9。
- 从“人工盯屏 + 中断”收敛到“自动完成 + 可复盘”。

更重要的是，中间一次工具改造引入的 `goto` 物理坐标 bug，普通单测和 code review 没有发现，但真实仿真 harness 在约 5 分钟内暴露出来，避免问题进入更晚阶段才发现。

这证明 Roboclaws 不只是能跑出好看的结果，也能把失败结构化暴露出来，并推动下一轮变好。

![Harness verified loop](https://raw.githubusercontent.com/MiaoDX/roboclaws/main/docs/blog/assets/robot-brain-harness-loop.png)

#### Household cleanup：从单次 demo 到可审查报告

在 household cleanup 场景中，Roboclaws 已经能生成：

- before/after 图像。
- Agent 实际可见的 `agent_view`。
- 工具调用 trace。
- private evaluation。
- cleanup report。

已有 cleanup run 达到：

| 指标 | 结果 |
| --- | --- |
| semantic accepted | 5/5 |
| sweep coverage | 1.0 |
| private evaluation | 保留 |
| Agent 输入 / 评估证据边界 | 分离 |

这件事对机器人任务很关键：机器人系统最危险的地方不是失败，而是假装成功。Roboclaws 的 report 让每次任务是否成功、为什么成功、哪里失败，都能被复盘。

![Household cleanup showcase](https://raw.githubusercontent.com/MiaoDX/roboclaws/main/docs/blog/assets/household-cleanup-showcase/contact_sheet.png)

#### 真机方向：从仿真闭环走向真实机器人

Roboclaws 已进入真实机器人导航/感知测试阶段。Nav2 pilot 已记录：

| 指标 | 结果 |
| --- | --- |
| 公开 waypoint 尝试 | 18/18 |
| 观察点记录 | 18/18 |
| 任务范围 | 导航 / 感知 pilot |
| 物理 manipulation | 按实际测试结果单独标注 |

我们会继续补充真机视频、日志和报告材料，并按能力边界分层说明：

- 仿真侧：已跑通 Agent 驱动的 `semantic-map-build` / `household-cleanup` / report 闭环。
- 真机侧：已完成导航/感知 pilot 测试，正在补充可公开的真机运行材料。
- 边界：物理 manipulation 按实际测试结果单独标注，不把仿真 pick/place 伪装成真机能力。

## 四、Demo 主线

本次参赛推荐主 demo：

```text
semantic-map-build + household-cleanup + Codex agent report
```

演示逻辑：

1. 给机器人一个开放目标：整理房间，或先探索空间并建立可用语义地图。
2. Agent 不是直接拿到完整答案，而是通过 `metric_map`、`observe`、`navigate`、`pick/place` 等工具逐步行动。
3. 系统生成可复盘报告，展示 agent-facing view、before/after、runtime map、semantic substeps、trace、score 和 private evaluation 分离。
4. 补充真机导航/感知 pilot，说明同一合同已经接入真实机器人导航和观察边界。

辅助证据：

- 旧 hackathon 的 photo task 5 次迭代，展示 Skill Loop 如何持续变好。
- OpenClaw / operator console，展示产品入口和人机交互形态。
- Isaac / Agibot rehearsal，展示 backend 迁移路线和真实机器人前的合同验证。

## 五、复用性

Roboclaws 不是某一个任务的专用脚本。它可复用的是一整套机器人 Agent 工作流：

```text
driver protocol
skill contract
task format
MCP tool boundary
artifact schema
run-to-run comparison workflow
```

### 1. 任务可复用

同一套 public command grammar 可以跑不同任务：

```bash
just task::run semantic-map-build direct evidence_lane=world-oracle-labels
just task::run household-cleanup codex world-labels
just task::run ai2thor-nav openclaw visual
```

### 2. Skill 可复用

Skill 承载的是“机器人应该怎么做”的经验，而不是一次性 prompt。后续可以继续沉淀：

- 导航 Skill。
- 拍照 Skill。
- 语义建图 Skill。
- 家庭清洁 Skill。
- 真机导航/感知 Skill。

### 3. Backend 可替换

同一套 task / skill / tool / report 边界可以接不同身体：

- 仿真 backend。
- MolmoSpaces / MuJoCo backend。
- Isaac backend。
- Nav2 backend。
- Agibot G2 backend。

这让项目不是停留在一个仿真 demo，而是在为“同一个机器人 Agent 大脑如何迁移到不同身体”做工程验证。

## 六、养虾心得

### 1. 给机器人以大脑，不是接一个聊天框

一开始很容易以为：给机器人接一个 VLM / LLM，它能看图、能调用动作接口，就算有大脑了。

真正跑起来以后才发现，第一步确实不难。难的是让机器人持续完成开放任务，并且每一次失败都能留下证据，每一次改动都能被验证，每一次经验都能沉淀下来。

### 2. Brain 不是模型，是 Skill Loop

模型能力很重要，但机器人任务里的“智能”不能只停留在模型输出里。它应该进入一个能被维护的 loop：

```text
run task
-> read trace
-> inspect report
-> edit skill
-> rerun
-> compare result
```

这也是 Roboclaws 的核心体会：机器人智能应该被放在 skill loop 里，而不是散落在 prompt、backend 和一次性对话里。

### 3. MCP 不能吞掉整个任务

如果暴露一个 `cleanup_room()`，demo 会很快，但智能也会被藏起来。Agent 不知道中间发生了什么，人类也很难审计。

Roboclaws 更倾向于 bounded MCP tools。让 Skill 组合工具，让 report 保存证据。这样失败时我们才知道应该改哪里。

### 4. Report 和 harness 不是外围工程

机器人系统最危险的地方，不是失败，而是假装成功。

没有 trace，Coding Agent 不知道哪里失败；没有 report，人类不知道结果能不能相信；没有 public/private boundary，系统不知道自己有没有作弊；没有 runtime map，机器人无法把一次观察变成下一次行动的世界记忆。

所以对 robot brain 来说，report 和 harness 本身就是智能的一部分。

## 七、下一步

报名阶段，我们已经具备完整方案和历史证据。后续重点是补齐更适合复赛/决赛展示的材料：

1. 选定本次主 demo run，固化最新 `household-cleanup` 和 `semantic-map-build` artifact。
2. 补充真机测试视频、日志、report、地图和导航证据。
3. 把旧 photo task 的 Run 001 -> Run 005 压缩成一张 Before/After 图或表。
4. 录制 8 分钟以内演示视频，展示完整功能流程。
5. 在决赛材料中展示 Agent 如何读 report、调整 Skill，并让下一轮机器人表现变好。

## 八、总结

Roboclaws 要证明的不是“机器人偶尔能动起来”，而是：

```text
机器人 Agent 的开放任务，
可以被组织成可运行、可观察、可复盘、可迁移、可持续变好的工程闭环。
```

这就是我们理解的“给机器人以大脑”。

不是一个模型。

不是一个万能工具。

而是一套能让机器人任务经验真正留下来的 Agent Skill Loop。
