# 出钳吧参赛方案草案：Roboclaws

整理日期：2026-06-09

本文档是 Roboclaws 参加“出钳吧！龙虾主理人”的内部参赛规划草案，不是最终提交稿。
目标是先锁定参赛主题、业务场景、证据地图、Before/After 口径、真机材料待补项和
8 分钟决赛视频骨架。

活动规则摘录见 [chuqianba-lobster-agent-contest-notes.md](chuqianba-lobster-agent-contest-notes.md)。

## 一句话主题

**给机器人以大脑：把开放式机器人任务组织成可运行、可观察、可复盘、可迁移的 Agent Skill Loop。**

这里的“大脑”不是某个单一模型，也不是把机器人接一个聊天框；它是一套由
Coding Agent、Skill、MCP 能力工具、Runtime Map、Trace 和 Report 组成的闭环：

```text
open-ended robot goal
  -> runnable task
  -> agent skill
  -> bounded MCP capability tools
  -> simulator / real-robot backend
  -> trace / runtime map / report
  -> skill improvement
```

## 报名短描述草稿

Roboclaws 是一个“给机器人以大脑”的 Agent 工程闭环：让 Codex、Claude Code 等
Coding Agent 通过受控 MCP 工具执行机器人开放式任务，并把每次运行沉淀成可复盘的
trace、runtime map、before/after 图像、评分和 HTML report。它不是单个机器人 demo，
而是一套从仿真到真机的 task -> skill -> tool -> backend -> report 工作流。当前已经
跑通导航、拍照、语义建图、家庭清洁、Nav2 真机导航/感知 pilot 等场景，后续补充真机
运行材料后，可展示 Agent 如何从任务执行、证据复盘到技能迭代持续变好。

## Planning Loop 结论

本轮 intuitive planning loop 的判断：

- 当前主题足够支撑报名，不需要再换方向。主线应从旧 hackathon 的
  “self-improvement harness”升级为“给机器人以大脑”。
- 业务场景必须落在真实研发/验证工作流上，而不是泛泛讲家庭服务机器人。
- 表单短字段要直接可填，避免把评委带进 repo 复杂度。
- Before/After 需要两层：旧 photo task 的硬数字作为历史强证据，本次主线补
  household cleanup / semantic-map-build / 真机测试的新证据。
- 真机可以作为正式 claim，但必须分层：导航/感知、建图、仿真清洁、物理 manipulation
  分别标注，不能把仿真 pick/place 说成完整真机清洁。

后续不需要继续讨论主题方向；下一步应收敛到“补证据、写最终报名文档、准备视频素材”。

## 表单即填版

### 场景需求/痛点描述

```text
机器人接入大模型之后，做一个“会动”的 demo 并不难，真正困难的是：如何让机器人持续完成开放式任务，并让每次运行都能被复盘、被验证、被改进。

在机器人研发和验证过程中，一个任务往往横跨自然语言目标、地图、视觉观察、导航、操作工具、仿真/真机 backend 和评估报告。传统做法里，策略散落在 prompt、临时脚本、SDK 调用和人工经验里；机器人跑完以后，工程师还要手动翻日志、看截图、判断是否真的完成任务，下一轮调优也很难知道到底哪里变好了。

Roboclaws 希望解决的是“给机器人以大脑”这件事：不是简单给机器人接一个模型，而是把开放式机器人任务组织成可复用的 Agent Skill Loop。Agent 可以根据任务选择 Skill，通过受控 MCP 工具观察、建图、导航、拾取/放置，并把每次运行沉淀为 trace、runtime map、before/after 图像、评分和 HTML report。这样机器人任务不再是一次性 demo，而是一个可运行、可观察、可复盘、可迁移到真机的工程闭环。
```

### 业务价值（含前后对比数据）

```text
Roboclaws 的价值是把机器人 Agent 研发从“人工盯屏 + 经验判断”，变成“Agent 自动执行 + 结构化报告复盘 + 下一轮可量化改进”。

已有真实数据：
1. 在 photo-living-room 任务中，早期人工调试 baseline 需要 127+ 次 tool calls，只完成 3/9 个目标，最终由人工中断；引入 harness、Skill 调整和 MCP 工具改进后，同一任务收敛到 37 次 tool calls、9/9 目标完成，并在 3.8 分钟内自动 done。tool calls 减少约 71%，目标覆盖从 33% 提升到 100%。
2. 在一次工具改造中，普通单测和 code review 未发现的 goto 物理坐标 bug，被真实仿真 harness 在 5 分钟内暴露，避免问题进入更晚阶段才发现。
3. 在 household cleanup 场景中，Roboclaws 已能生成 before/after 图像、agent_view、trace、private evaluation 和 report；已有 cleanup run 达到 semantic accepted 5/5、sweep coverage 1.0，并保留私有评分与 Agent 输入的边界。
4. 在真机方向，Roboclaws 已进入真实机器人导航/感知测试阶段，Nav2 pilot 已完成 18/18 个公开 waypoint 尝试与观察点记录；后续会继续补充真机视频、日志和报告材料。

Before：一次机器人 Agent 任务跑完后，工程师需要人工盯过程、翻日志、核对截图和评分，调优主要依赖经验。
After：一条任务命令即可生成可复盘报告，包含工具调用、地图、前后对比、评分、失败原因和下一轮改进依据。它让机器人 Agent 的研发验证从“看起来能跑”变成“能证明它为什么能跑、哪里失败、下一轮如何变好”。
```

### 表单字段压缩版

如果表单长度受限，优先保留以下数字和判断：

- `127+ -> 37` tool calls，减少约 71%。
- `3/9 -> 9/9` 目标覆盖，`33% -> 100%`。
- `3.8 min` 自动 done。
- live harness 在约 5 分钟内暴露 mock/code review 未发现的物理坐标 bug。
- cleanup report 已有 `semantic accepted 5/5`、`sweep coverage 1.0`。
- 真机 Nav2 pilot 已记录 `18/18` waypoint 尝试与观察点。

## 业务场景

### 场景名称

机器人智能任务的研发验证与复盘。

### 目标用户

- 机器人算法工程师。
- 具身智能 / Agent infra 开发。
- 仿真平台和测试工程师。
- 机器人应用 demo 和评测团队。
- 未来可扩展到真实机器人 operator 和场景交付团队。

### 真实痛点

现在让 Agent 驱动机器人完成开放式任务，最贵的不是“让它动一步”，而是让一次运行变得可信、可比较、可复盘：

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

### 我们的解决方案

Roboclaws 把开放式机器人任务收敛成一套可审查的 Agent Skill Loop：

- **Runnable Task**：公开任务入口，如 `semantic-map-build`、`household-cleanup`、`ai2thor-nav`。
- **Agent Skill**：承载任务策略，描述如何观察、建图、导航、拾取、放置、失败恢复和记录证据。
- **MCP Capability Tools**：暴露受控机器人能力，如 observe、navigate、pick、place、metric_map、done，而不是一个不透明的 `cleanup_room()`。
- **Runtime Metric Map**：把当前运行中观察到的世界状态沉淀成公共地图证据。
- **Backend Variant**：同一套 task/skill/tool/report 边界可以接仿真、MolmoSpaces、Isaac、Nav2、Agibot G2 等身体。
- **Reviewable Artifacts**：每次 serious run 输出 `trace.jsonl`、`agent_view.json`、`run_result.json`、`runtime_metric_map.json`、`report.html`、before/after 图像和评分证据。

### 为什么 Agent 技术自然契合

这个场景不是为了使用 Agent 而硬套。开放式机器人任务天然需要 Agent：

- 任务目标是自然语言和长程目标，而不是固定 API 调用。
- 机器人需要在观察、地图、工具、历史证据和失败恢复之间做决策。
- 任务经验需要沉淀成可复用 Skill，而不是每次从零 prompt。
- Coding Agent 能读 trace/report、修改 skill、运行验证，形成 `run -> inspect -> edit -> rerun` 的自我改进循环。
- MCP 让机器人能力边界可控，不把智能藏进后端私有实现。

## 主 Demo 选择

推荐主线：**household-cleanup + semantic-map-build + Codex agent report**。

演示叙事：

1. 给机器人一个开放目标：整理房间 / 建立可用语义地图 / 完成导航与观察任务。
2. Agent 不是直接拿到完整答案，而是通过 `metric_map`、`observe`、`navigate`、`pick/place` 等工具逐步行动。
3. 报告展示 agent-facing view、before/after、runtime map、semantic substeps、trace、score 和 private evaluation 分离。
4. 补充真机导航/感知 pilot：说明同一合同已接入真实机器人导航和观察边界，后续材料展示真实运行证据。

辅助证据：

- 旧 hackathon 的 photo task 5 次迭代：展示 Skill Loop 如何持续变好。
- OpenClaw / operator console：展示产品入口和人机交互形态。
- Isaac / Agibot rehearsal：展示 backend 迁移路线和真实机器人前的合同验证。

## 证据地图

| 评审关注点 | 当前 repo 证据 | 待补证据 |
| --- | --- | --- |
| 好问题、大问题 | `README.md`、`ARCHITECTURE.md`、blog V3、旧 hackathon submission | 把“给机器人以大脑”压缩成报名文档开场故事 |
| Agent 真实场景 | `household-cleanup`、`semantic-map-build`、`ai2thor-nav`、Codex/Claude/OpenClaw routes | 选一条主 demo 重新跑并记录最新 artifact |
| Before/After | 旧 hackathon Run 001 -> Run 005；cleanup report 的 before/after 图片和 score | 新增本次报名用量化表，不只复用旧 photo task |
| 可落地性 | `just task::run ...`、report artifacts、Codex cleanup harness8、local proof docs | 录制 3-5 分钟主 demo 操作视频草稿 |
| 真机测试 | real robot Nav2 pilot status、physical navigation/perception readiness、Agibot G2 plan | 补充最新真机测试报告、视频、日志和实际边界说明 |
| 多 Agent / 主动智能 | Coding Agent + Skill + MCP + report loop；OpenClaw + operator console | 决赛材料里展示“Agent 读报告后改 Skill/下一轮更好”的过程 |
| 可复用性 | task/skill/profile/backend layering；MCP profiles；runtime map snapshot | 列出可迁移到其他机器人任务的模板和命令 |

## 证据优先级

报名阶段不要平均展示所有 repo 能力。推荐证据优先级：

1. **P0：表单必须出现**
   - 业务痛点：开放式机器人任务的复盘、验证和迁移。
   - 旧 photo task 数字：`127+ -> 37 calls`、`3/9 -> 9/9`、`3.8 min done`。
   - household cleanup report 能力：before/after、trace、agent_view、score、private evaluation。
   - 真机导航/感知 pilot 已进入验证阶段，后续补视频和报告。
2. **P1：报名文档正文展开**
   - `semantic-map-build` 和 Runtime Metric Map。
   - task/skill/profile/MCP/backend/report 分层。
   - OpenClaw/operator console 作为产品入口。
3. **P2：决赛或问答时再展开**
   - Isaac segmentation/scene parity。
   - Agibot contract rehearsal。
   - Codex cleanup harness8 多 evidence lane。
   - physical manipulation 细节，只有在补齐真实证据后再提升优先级。

当前最容易过度展开的是 backend 细节。表单和入围文档里只需要说明：

```text
同一套 brain loop 可以换身体；仿真、Nav2、Agibot、Isaac 是 backend variant，
不是四个互相割裂的 demo。
```

## 接受标准

这份参赛计划进入“可写最终报名文档”状态，需要满足：

- [x] 主题明确：给机器人以大脑，不是单点机器人 demo。
- [x] 业务场景明确：机器人智能任务的研发验证与复盘。
- [x] 表单两项已有可直接填写版本。
- [x] Before/After 已有历史硬数据，且列出本次主线待补数据。
- [x] 真机 claim 有分层写法，避免混淆仿真和物理操作。
- [ ] 主 demo run 目录确定。
- [ ] 最新 household cleanup / semantic-map-build artifact 链接确定。
- [ ] 真机测试材料路径确定。
- [ ] 最终报名文档正文完成。

## Before/After 指标口径

报名阶段可以先使用“已有证据 + 待补实测”的组合。决赛前必须把待补项换成真实数据。

### 旧 hackathon 历史强证据

Photo task self-improvement loop：

| 指标 | Before | After | 说明 |
| --- | --- | --- | --- |
| 任务覆盖 | 3/9 | 9/9 | 同一 photo-living-room task |
| tool calls | 127+ | 37 | 从人工盯屏到 harness 托管闭环 |
| 完成状态 | user interrupt | done in 3.8 min | Run 001 -> Run 005 |
| bug 发现 | FakeEngine/code review 未发现 | live harness 5 分钟内暴露 goto 物理 bug | 证明真实运行证据价值 |

### 本次主线建议补齐的指标

Household cleanup / semantic-map-build：

| 指标 | Before 口径 | After 口径 | 需要补的数据 |
| --- | --- | --- | --- |
| 人工复盘耗时 | 手工翻日志、截图、评分文件的时间 | 打开 `report.html` 和摘要判断结果的时间 | 计时一次真实复盘 |
| 证据完整度 | 散落日志 / 临时截图 / 口头说明 | `trace.jsonl`、`agent_view.json`、`runtime_metric_map.json`、before/after、score、report | 列 artifact 字段数和示例 |
| 任务完成度 | 无统一评分或人工判断 | semantic accepted count、sweep coverage、disturbance count、private evaluation | 最新主 demo run result |
| 复用成本 | 新任务需要重写脚本和 prompt | 新 runnable task/skill/profile/backend 组合 | 选一个已有任务迁移案例 |
| 真机过渡成本 | backend 原语各说各话 | 同一 public task/tool/report 边界接 Nav2/Agibot | 补真机运行报告和边界说明 |

### 真机材料待补指标

| 指标 | 需要记录 |
| --- | --- |
| 机器人平台 | 机型、地图、场地、运行日期、操作者 |
| 任务范围 | 导航/感知/建图/清洁操作分别是否实机完成 |
| 成功标准 | 到达 waypoint 数、观察点数、地图/报告 artifact、是否需要人工接管 |
| 安全边界 | 急停、operator gate、blocked manipulation、失败处理 |
| Artifact | 视频、report、run_result、trace、地图 bundle、关键截图 |

## 真机 Claim 写法

当前参赛材料可以直接说：

> Roboclaws 已经进入真机测试阶段，并有真实机器人导航/感知 pilot 证据；后续提交会补充真机运行视频、日志和报告。我们会按能力边界分层说明：哪些是实机已完成，哪些是仿真完成，哪些是物理操作/清洁动作的后续验证。

不要写成：

> 已完整解决真实家庭清洁机器人。

推荐写法：

```text
仿真侧：已经跑通 Agent 驱动的 semantic-map-build / household-cleanup / report 闭环。
真机侧：已经完成导航/感知 pilot 测试，正在补充可公开的真机运行材料。
边界：物理 manipulation 按实际测试结果单独标注，不把仿真 pick/place 伪装成真机能力。
```

## 8 分钟决赛视频骨架

1. **0:00-0:45 问题开场**  
   “给机器人以大脑”不是接模型，而是让机器人能完成开放任务、留下证据、下一轮变好。
2. **0:45-1:45 业务痛点**  
   传统机器人 Agent demo 可见性差、复盘慢、经验不沉淀、仿真到真机边界不清。
3. **1:45-3:00 架构解释**  
   Task -> Skill -> MCP Tools -> Backend -> Trace/Map/Report -> Skill improvement。
4. **3:00-5:00 主 demo**  
   展示 household-cleanup 或 semantic-map-build：agent view、工具调用、before/after、runtime map、score。
5. **5:00-6:00 Before/After 数据**  
   用旧 photo task 证明 loop 能提升；用最新 cleanup/真机数据证明当前主线可落地。
6. **6:00-7:00 真机与可迁移性**  
   展示 Nav2/Agibot/Isaac 等 backend 作为身体，同一套 brain loop 不绑定单一仿真。
7. **7:00-8:00 总结和下一步**  
   Roboclaws 的价值是把机器人智能放到能运行、能失败、能复盘、能改进的位置。

## 报名文档结构草案

1. 标题：给机器人以大脑：可复盘、可迁移的机器人 Agent Skill Loop。
2. 一句话简介。
3. 场景需求/痛点。
4. 方案概览：不是单个模型，而是 task/skill/MCP/backend/report 闭环。
5. 已落地功能：
   - AI2-THOR / OpenClaw / Coding Agent 导航。
   - `semantic-map-build`。
   - `household-cleanup`。
   - report / trace / runtime map。
   - 真机导航/感知 pilot。
6. Before/After 数据。
7. 复用性：
   - 同一 task grammar。
   - 同一 skill/profile/tool 边界。
   - 多 backend variant。
8. 养虾心得：
   - brain 不是模型，是可迭代 skill loop。
   - MCP 不能吞掉任务，边界越清楚越能迁移。
   - report 和 harness 不是外围工程，是机器人智能的一部分。
9. 下一步：
   - 补真机材料。
   - 扩展真实物理 manipulation 证据。
   - 做更多开放任务。

## 待办清单

- [ ] 选定本次报名主 demo run 目录。
- [ ] 生成或挑选最新 `household-cleanup` report。
- [ ] 生成或挑选最新 `semantic-map-build` runtime map report。
- [ ] 补充真机测试材料：视频、report、run_result、trace、地图/导航证据。
- [ ] 统计本次主线的 Before/After 数据。
- [ ] 把旧 hackathon 的 Run 001 -> Run 005 作为历史证据精简成一张图或一张表。
- [ ] 写最终报名文档正文。
- [ ] 准备决赛 8 分钟视频脚本和录屏素材。
