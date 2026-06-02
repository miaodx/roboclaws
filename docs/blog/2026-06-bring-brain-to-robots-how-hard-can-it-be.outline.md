# Bring Brain To Robots: How hard can it be? — Outline

> 对齐版大纲 v3  
> 定位：这不是一篇单纯的项目介绍，而是一篇方法论文章。Roboclaws 是 case study，用来说明我们为什么认为 **Coding-Agent-Native + Skills-first** 会是接下来一段时间内非常值得尝试的机器人智能开发方式。

## 0. 文章定位

这篇文章要推荐的是一种方法论：

**不要把机器人智能藏在一次性 demo、prompt、Python loop、simulator backend 或某个机器人 SDK 里；而是把它放进一个可以被 coding agent、人类和工程系统共同迭代的 skill loop。**

Roboclaws 的实现本身可以被 coding agent 很快搭出来，但这层抽象不是一开始就自然出现的。它来自一段时间的试错：VLM 直驱、OpenClaw harness、MCP、Coding Agent、SKILL.md、report、runtime map、backend variant 都跑过之后，我们才意识到真正重要的不是“机器人能不能动”，而是“机器人智能应该沉淀在哪里”。

## 1. 标题与副标题

主标题：

**Bring Brain To Robots: How hard can it be?**

副标题候选：

**我们怎样用 Coding Agent 搭出一套可迭代的机器人 Brain**

备选：

- 从 VLM 直驱到 Skills-first 机器人智能栈
- 一次从 OpenClaw Harness 到 Coding-Agent-Native Robot Brain 的实验
- 当机器人不只需要会动，还需要会积累经验
- 用 Skills、MCP 和 Coding Agent 给机器人搭一个可扩展的大脑

标题语气来自 Top Gear 式的 “How hard can it be?”：一开始觉得这件事应该不难，真正上手后才发现难点不在启动，而在持续运行、复盘、迭代和迁移。

## 2. Brain 的定义

文章里要尽早定义：这里说的 brain 不是一个单独的模型。

Roboclaws 里的 robot brain 指的是一套可持续工作的任务执行系统：

- 能理解开放式任务；
- 能调用 bounded robot capabilities；
- 能观察和更新世界状态；
- 能留下 trace、report、map 和 artifact；
- 能从失败中改进 skill；
- 能换 backend 后复用经验；
- 能让人类审计它做了什么、没做什么、哪些能力还没有证明。

一句话：

**Brain 不是更大的模型，而是模型、skill、tool、trace、report、map 和 backend 之间的可迭代循环。**

## 3. 核心 thesis

Roboclaws 想展示的不是一个会动的机器人 demo，而是一种机器人智能开发方式：

> 以 Skills 为中心，用 Coding Agent 做迭代，用 MCP 固定能力边界，用 reports / traces / maps 留下证据，再把这套 brain 接到不同的机器人身体上。

更强的一句话：

**把机器人智能放进可迭代的 skill loop，而不是藏在 prompt、backend 或一次性 demo 里。**

再往外推一层：

**Coding Agent 在接下来一段时间内，可能会成为很多行业构建自定义智能系统的最好平台。**

不是每个行业都应该从零造一个 agent framework。很多行业真正需要的是：把自己领域里的任务、工具、检查器、报告和知识沉淀到 coding-agent-native 的 loop 里，让 Claude Code、Codex 或后续 Agent SDK 成为最快的研发环境。

机器人只是这个趋势里最直观、最难、也最能暴露问题的场景。

---

# 正文大纲

## 0. 楔子：How hard can it be?

### 作用

建立文章语气：乐观、动手、半开玩笑地低估难度，然后一路撞墙、修正抽象。

### 内容

开头可以从这句话开始：

“有了大模型之后，给机器人加一个大脑，应该不会很难吧？”

摄像头给模型看，动作接口给模型调，MCP 或 API 负责连接，听起来就是一个周末 demo。

但真正做起来之后，会发现最麻烦的地方不是“能不能动”，而是：

- 它能不能理解开放式任务？
- 它能不能知道自己缺什么信息？
- 它失败以后能不能复盘？
- 它的经验能不能留给下一次？
- 它换一个场景、换一个 backend、换一台机器人以后还能不能复用？
- 它做过什么，能不能被人类审计？

### Punchline

**让机器人动起来不难；让它像一个可持续改进的系统一样工作，才是 brain 的问题。**

---

## 1. VLM 直驱：第一步确实不难

### 作用

把早期 VLM 直驱放回历史位置：它是必要起点，但不是最终答案。

### 内容

Roboclaws 最早的路径很直接：

- 给 VLM 当前画面；
- 给它结构化状态；
- 让它输出动作；
- robot 在 AI2-THOR 里移动、转向、观察、完成简单任务。

这一步的价值是验证最小闭环：AI 确实可以直接控制机器人。它能完成导航、覆盖、拍照这类 demo。

但这里要明确说：我们从一开始就知道 VLM 直驱不是最终方案。它的问题不是模型不够聪明，而是系统形态不对。

### 限制

- 策略容易藏在 prompt 或 Python loop 里；
- 失败经验不能稳定沉淀；
- 每次改进都像重新调 prompt；
- 很难形成任务级 skill；
- 很难审计每一步为什么这么做；
- 更难迁移到别的 backend 或真机。

### Punchline

**VLM 直驱能证明“AI 可以控制机器人”，但它还不能回答“机器人智能应该怎样被开发和维护”。**

---

## 2. 为什么我们需要 Harness

### 作用

把文章从“控制机器人”升级到“构造机器人智能系统”。

### 内容

机器人任务不是单次模型调用，而是一组长期运行的 loop：

```text
理解任务
-> 选择策略
-> 调用工具
-> 观察反馈
-> 记录证据
-> 判断成功/失败
-> 总结经验
-> 改进 skill
-> 下次复用
```

Harness 不是外围工程，它本身就是 brain 的一部分。

一个合格的机器人 harness 至少要解决：

- 任务怎么表达；
- skill 怎么选择和维护；
- 工具边界怎么设计；
- 运行过程怎么记录；
- 失败怎么进入下一轮改进；
- 用户怎么介入；
- backend 怎么替换；
- report 怎么让人类相信它真的做了这件事。

### Punchline

**机器人 brain 不是一个模型，而是模型、skill、tool、trace、report 和 backend 之间的循环。**

---

## 3. 为什么最初选择 OpenClaw

### 作用

解释 RoboClaws 名字和 OpenClaw 的历史位置，正面评价 OpenClaw，不把它写成失败方案。

### 内容

我们最初选择 OpenClaw，是因为它不只是当时非常 high-level 的 AI harness，即便放到今天来看，也仍然是一个完成度很高、设计很成熟的实现。

它有：

- SOUL：描述 agent 的人格和行为倾向；
- Skills：封装能力；
- MCP：连接外部工具；
- Control UI：让用户直接和 agent 交互；
- 一个天然适合把机器人能力变成“可聊天、可控制、可产品化”的 AI 系统的框架。

RoboClaws 这个名字也来自这种想法：把 robot 接进 Claws 生态，让机器人也拥有一个高层 agent harness。

### 表达边界

OpenClaw 是一个很好的用户交互层和产品化 harness。它让机器人能力可以被用户“看见”和“对话式使用”。

但在研发中，我们发现真正快速推进机器人智能效果的地方，不只是用户交互，而是 skill / MCP / report / failure 的迭代 loop。

### Punchline

**OpenClaw 让我们看到了 high-level harness 的方向，但研发 robot brain 还需要一个更强的自我迭代引擎。**

---

## 4. 转折：Coding Agent 更像一个 Robot Brain Workshop

### 作用

把 Claude Code / Codex 从“一个能调用 MCP 的 client”提升为整篇文章的关键洞察。

### 内容

Claude Code 和 Codex 这类 coding agent 很适合做机器人研发核心，不是因为它们“更会聊天”，而是因为它们天然拥有一组非常适合机器人智能迭代的能力：

- 会读文件；
- 会改文件；
- 会运行命令；
- 会看 trace；
- 会读 report；
- 会根据失败修改 skill；
- 会调整 MCP server 或 task runner；
- 会把一次运行的经验写回下一次运行可以使用的地方。

这和普通 assistant harness 很不一样。机器人任务失败以后，最重要的不是让模型重新回答一次，而是让它能进入工程系统：

```text
失败
-> 看 trace
-> 找原因
-> 改 skill / MCP / checker
-> 重新跑
-> 对比 report
-> 把成功经验沉淀下来
```

### 可以用的例子

- photo task 从直接 trial-and-error 到先读取对象列表、再按对象执行；
- SKILL.md 被模型自己修改；
- trace/report 反过来成为下一轮 skill 改进依据；
- Git commit history 能看到 coding agent 参与了大量迭代；
- 可以补 Git 截图、trace 截图、数值优化总结。

### 更大的判断

Coding agent 不只是机器人控制器。它可能是很多行业未来一段时间内最好的自定义智能开发平台。

很多行业不一定需要从零做一个垂直 agent framework。更现实的路径可能是：把领域任务、工具、检查器、报告和经验沉淀进 coding-agent-native 的 loop 里，让 coding agent 做研发和优化。

### Punchline

**Coding agent 不只是机器人控制器，它更像 robot brain 的研发环境。**

---

## 5. Skills First：brain 应该沉淀在哪里？

### 作用

进入本文最重要的架构思想：Skills first。

### 内容

在 Roboclaws 里，skill 不是一个装饰性的 prompt 文件。它是机器人智能最重要的承载层：

- 任务策略写在 skill 里；
- 经验沉淀在 skill 里；
- recovery loop 写在 skill 里；
- examples 和 checks 放在 skill 里；
- 不同 backend 共享同一套 skill 语义；
- coding agent 可以直接修改和维护 skill。

这解决了 VLM 直驱和早期 harness 的一个核心问题：智能不再散落在 Python loop、prompt template、backend adapter 或临时对话里，而是沉淀在可以被人和 agent 共同维护的 skill artifact 中。

### 设计原则

- Runnable Task 负责“要跑什么”；
- Agent Skill 负责“怎么做”；
- Capability Profile 负责“这个 skill 可以依赖哪些能力”；
- MCP Tool 负责“稳定暴露哪些机器人能力”；
- Backend Variant 负责“具体在哪个环境执行”。

### Punchline

**Skills first 的意思是：把机器人智能放在最容易被模型、人类和工程系统共同迭代的地方。**

---

## 6. MCP Bounded：工具不是越大越好

### 作用

解释 Roboclaws 的 MCP 设计观，避免读者误以为“把任务都包成 MCP 工具”就是答案。

### 内容

MCP 很重要，但 MCP 不应该吞掉整个任务。

反例：

```text
cleanup_room()
```

这样看起来方便，但智能被藏起来了。agent 不知道中间发生了什么，人类也很难审计，失败后也不知道该改 skill、改工具还是改 backend。

Roboclaws 更倾向于 bounded capability tools：

- observe
- navigate / move
- pick / place
- open / close
- done
- metric_map
- inspect_visible_object
- declare_visual_candidates

这些工具的边界相对稳定，能够留下 trace，也能在不同 backend 之间复用。

像 `scene_objects`、`goto` 这种在仿真里很方便的工具，要诚实标注为 privileged / demo helper。它们可以帮助研发和 smoke test，但不能被包装成真实机器人也默认拥有的能力。

### Punchline

**MCP 的价值不是把任务藏起来，而是给 skill 一个稳定、可审计、可替换的能力边界。**

---

## 7. Minimal Map：开放式任务需要世界记忆

### 作用

作为当前项目的第二核心。它说明 Roboclaws 不是只做 coding-agent + MCP，而是在处理真实机器人任务里非常关键的世界状态问题。

### 内容

当任务从“拍椅子”变成“整理房间”时，机器人需要的不只是当前画面。它需要一个世界状态：

- 哪些区域可以走；
- 哪些地方值得探索；
- 哪些物体是刚刚观察到的；
- 哪些 fixture / receptacle 可以作为 destination hints；
- 哪些 prior 需要当前确认；
- 哪些 map update 只是候选，还不能写回 source map。

这就是 Runtime Metric Map 的意义。

Roboclaws 的选择不是先手写一个很丰富的 semantic map，而是从 minimal map 开始：

- occupancy / free-space；
- pose / frame metadata；
- safety bounds；
- generated exploration candidates；
- runtime observations；
- public semantic anchors。

然后让 `semantic-map-build` 通过观察逐步构建 Runtime Metric Map。`household-cleanup` 再消费这份 evidence。

### 仿真优先的表达

在仿真里把这个任务跑完，已经足够说明方法论的价值。MolmoSpaces 这类大规模、开放 household 场景可以承载非常多接近真实落地的任务 rehearsal。

真机很重要，但在本文里放到后面作为 backend-replaceable 的延伸，不让它抢走主线。

### Punchline

**真正可迁移的 robot brain 不应该依赖手写完整语义地图，而应该能从 minimal map 和公开观察中逐步建立任务所需的世界记忆。**

---

## 8. Report / Trace / Map：让机器人任务可审计

### 作用

把 “brain” 和 “可审计证据” 连接起来。这也是 Roboclaws 和普通 demo repo 的差异。

### 内容

机器人任务不能只输出一句 “done”。它必须留下足够证据，让人知道：

- 它看到了什么；
- 它调用了哪些工具；
- 它去了哪里；
- 它为什么判断任务完成；
- 哪些信息是 agent 看到的；
- 哪些是 private evaluator truth；
- 哪些能力是真实执行；
- 哪些能力只是 blocked 或 simulated；
- 失败在哪里发生。

所以 Roboclaws 的每次 serious run 都应该产出：

- `trace.jsonl`
- `run_result.json`
- `agent_view.json`
- `runtime_metric_map.json`
- `report.html`
- 需要时还有 robot-view images、map preview、planner proof bundle 等。

### Punchline

**没有 report 的机器人 demo 很难让人相信；没有 trace 的机器人 brain 很难持续进化。**

---

## 9. OpenClaw 回到正确位置：交互层，而不是唯一研发核心

### 作用

把 OpenClaw 与 coding agent 的关系讲清楚。

### 内容

经过这些尝试后，OpenClaw 在 Roboclaws 里的位置变得更清楚：

- OpenClaw 很适合作为用户交互层；
- 它适合承载 Control UI、SOUL、对话入口、用户体验；
- 当 skill / MCP / profile 抽象稳定之后，OpenClaw 可以直接接进来；
- 它可以复用 coding agent 研发出的 skills 和 capability boundary。

但日常研发、效果迭代、failure analysis、skill evolution，更适合放在 coding agent loop 里。

### Punchline

**OpenClaw 是很好的产品入口；Coding Agent 是更高效的 brain workshop。两者不是替代关系，而是分工关系。**

---

## 10. Model Takeaway：最强模型做开发，快模型跑任务

### 作用

给读者一个经验性 takeaway。它不是全文重点，不写成严格 benchmark，只写成当前工程经验。

### 内容

我们现在更倾向于把模型使用分成两层。

### A. 开发 / 优化阶段

用于 MCP、Skill、Checker、Report、Task Runner 的设计与优化时，更推荐使用 Claude Code 或 Codex 搭配官方最强模型。

原因是：

- 这一阶段最重要的是修改能力和长期推理能力；
- 模型需要读代码、改代码、读 trace、看 report、理解失败边界；
- 尤其是 Skill 优化，需要模型真的理解任务结构和失败原因；
- 这里的优化结果会沉淀到 repo、skill、MCP contract、checker 和 report 里，可以被后续更快模型复用。

### B. 真正运行 / 执行阶段

当 skill 已经被强模型优化过以后，真正运行任务时可以使用更快、足够强、具备视觉理解能力的模型，例如 Claude / Codex harness 搭配 Kimi、MiMo 等模型路线。

原因是：

- 运行阶段不一定每次都需要最强模型重新发明策略；
- 好的 skill 已经把关键经验、约束、工具使用方式写清楚；
- 快模型可以更高频地执行、观察、调用工具；
- 成本和速度更适合大量 episode、仿真任务和后续真实机器人测试；
- 只要 skill 和工具边界足够好，运行效果仍然可以足够稳定。

### Punchline

**用最强的 coding agent 优化 skill，用更快的视觉模型执行任务。这是我们目前最实用的 robot brain 工程经验之一。**

---

## 11. Backend 可换：同一个 brain，多个身体

### 作用

把 MolmoSpaces、Isaac、Agibot G2、Unitree G1 等放进来，但作为架构证明，而不是功能清单。

### 内容

当 task / skill / profile / MCP / report boundary 稳定后，backend 就可以替换：

- AI2-THOR 可以证明导航、覆盖、拍照；
- MolmoSpaces / MuJoCo 可以证明 household cleanup；
- Isaac 可以提供更真实的 USD scene、renderer、segmentation、semantic pose evidence；
- Agibot G2 / Nav2 / Unitree G1 等可以作为 physical backend variant；
- 未来还可以接更多机器人或 simulator。

关键不是“我们支持了很多 backend”，而是：

**backend 只是身体，skill / MCP / report loop 才是 brain。**

### 真机表达边界

真机放后面提，不抢主线。

可以表达为：

- 如果大家手里有智元 G2、宇树 G1 或其他机器人，可以尝试把它作为 backend variant 接进来；
- 理想情况下，只需要改 backend adapter，而不是重写 task / skill / MCP / report；
- 真机会引入安全门、定位、地图、感知失败、运动控制、急停、operator gate 等额外边界；
- 这些边界应该通过 provenance、blocked capability 和 report evidence 诚实表达。

避免使用：

- “G2 真机 cleanup 已经跑通”；
- “simulation proof 等价于 hardware proof”；
- “semantic pose 等价于真实 manipulation”。

### Punchline

**可扩展性的核心不是多接几个 backend，而是让 backend 永远处在可替换层。**

---

## 12. 不是替代底层 robotics

### 作用

主动划清边界，避免专业 robotics 读者误解。

### 内容

Roboclaws 不是要替代 VLA、RL、motion planning、whole-body control、robot SDK 或底层控制系统。

它关注的是开放式任务层：

- 任务理解；
- skill 选择和改进；
- bounded tool calling；
- 世界证据；
- report / trace；
- simulator / hardware contract parity；
- backend-replaceable task execution。

底层 policy、controller、planner、robot SDK 仍然是 backend 的一部分。Roboclaws 想做的是让上层智能能够以干净、可审计、可迁移的方式调用这些能力。

### Punchline

**我们不是替代底层控制，而是在为开放式机器人任务搭一个可迭代、可审计的智能层。**

---

## 13. 最后轻轻带到 Multi-Agent

### 作用

回应 Roboclaws 早期多 agent 定位，但不让它成为主线。

### 内容

多 agent 是 Roboclaws 的自然延伸，因为一旦单个 robot brain 的 task / skill / tool / report 抽象稳定，就可以开始研究：

- 多个机器人如何共享 map evidence；
- 多个 agent 如何分工；
- 竞争和协作任务如何审计；
- 一个 agent 的 skill 改进如何影响整个团队；
- 多 agent 是否需要共享 skill library 或独立 personality。

但这篇文章不展开多 agent。它只作为结尾的方向之一。

### Punchline

**先把一个 robot brain 的开发 loop 做干净，多 agent 才有稳定的地基。**

---

## 14. What’s next：我们希望大家一起做什么

### 作用

把文章从“我们做了什么”转成“社区可以一起做什么”，同时自然邀请 PR、任务尝试、backend 接入和真实机器人适配。

### CTA 顺序

### 1. 在 MolmoSpaces 里定义复杂任务

这是最适合大多数人的入口。

MolmoSpaces 是一个很大、很开放、很适合机器人落地前 rehearsal 的场景集合。它不应该只被用来跑一个固定 benchmark。

我们更希望大家把它当成一个开放世界任务沙盒：

- 自己定义复杂 household task；
- 尝试 inspection、search、cleanup、rearrangement、photo capture、inventory、room understanding 等任务；
- 检查哪些任务可以只靠 skill 和 MCP 解决；
- 检查哪些任务需要新的 public capability；
- 检查哪些任务暴露了 map、perception、planning、report 的新边界。

### 2. 一起优化 Skills

Roboclaws 的一个核心判断是：很多 robot intelligence 的改进不会来自某个巨大工具，而会来自很多小的 skill 改进：

- 更好的任务分解；
- 更好的观察策略；
- 更好的失败恢复；
- 更好的 map 使用方式；
- 更好的 object / receptacle reasoning；
- 更好的 runtime evidence 写法；
- 更好的 checker 和 report gate。

这些东西看起来不像传统 robotics paper 里的“大算法”，但它们会直接决定一个 agent 能不能稳定完成开放式任务。

### 3. 支持更多机器人 / backend

我们也非常欢迎大家一起尝试接入更多机器人。

理想状态是：

- 新机器人只需要加一个 backend variant；
- agent-facing 的 task、skill、profile 不大改；
- report 仍然能诚实展示 provenance、blocked capability 和失败边界；
- 真机能力逐步从 navigation + perception 扩展到 manipulation。

如果大家手头有智元 G2、宇树 G1 或其他机器人，可以尝试稍微修改 backend adapter 来接入。

### 4. 从仿真迁移到实机

如果 task / skill / MCP / report boundary 做得足够干净，从仿真到实机不应该是重写整个系统，而应该是替换 backend。

真实机器人会引入安全门、定位、地图、感知失败、运动控制、急停、operator gate 等额外边界。但这些边界应该体现在 backend provenance 和 report evidence 里，而不是污染 agent-facing task 形状。

### Punchline

**如果你想尝试“用 coding agent 驱动一个真实系统”，机器人是一个非常好的压力测试场；如果你想尝试“给机器人加 brain”，Roboclaws 希望成为一个足够简单、足够透明、足够可扩展的起点。**

---

## 15. 收束：How hard can it be?

### 作用

回到标题，给出最终答案。

### 内容

“给机器人加一个大脑”这件事，第一步确实没有想象中难。让模型看图、调用动作接口、在仿真里移动起来，很快就能看到效果。

但真正难的是把它做成一个系统：

- 能理解开放式任务；
- 能选择和改进 skill；
- 能通过 bounded tools 调用机器人能力；
- 能记录 trace 和 report；
- 能从失败中学习；
- 能从仿真迁移到更真实的 backend；
- 能最终接到真实机器人；
- 能让人类相信它做了什么、没做什么、哪里还没有证明。

Roboclaws 现在的答案是：

```text
Skills first
+ Coding Agent loop
+ MCP bounded capability surface
+ Runtime map / world evidence
+ Reviewable reports
+ Backend variants
= A practical path to bring brain to robots
```

### 最后一段

我们不认为这套方案只适用于机器人。机器人只是一个非常直观、非常严格的测试场：它有空间、有动作、有失败、有安全边界、有真实世界约束。

如果 coding agent 可以在这里帮助我们构造、迭代、审计一套 robot brain，那么类似的方法也可能适用于更多开放式智能系统：实验室自动化、浏览器操作、数据分析 pipeline、生产系统运维，甚至任何需要长期运行、持续改进、可审计工具调用的智能工作流。

### 最终 punchline

**How hard can it be?**

比想象中难。但也比想象中更清楚。

答案也许不是从零造一个新的行业 agent framework，也不是把智能藏进一次性 demo，而是把行业知识、任务经验和工具边界放进一个能持续迭代的 skill loop 里。

这就是 Roboclaws 现在正在尝试的方向。
