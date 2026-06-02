# Bring Brain To Robots: How hard can it be?

> 初稿 v1  
> 副标题候选：我们怎样用 Coding Agent 搭出一套可迭代的机器人 Brain

“有了大模型之后，给机器人加一个大脑，应该不会很难吧？”

这句话听起来很像 Top Gear 里那句经典的 **How hard can it be?**。先假设事情很简单，然后真的把车开上路，才发现真正麻烦的地方从来不是“能不能启动”，而是启动之后它能不能持续跑、坏了能不能修、换一条路还能不能跑。

机器人也是这样。

现在大家基本都相信 AI 可以控制机器人。摄像头给模型看，动作接口给模型调，中间用 MCP 或 API 接起来，看起来就是一个周末 demo。让模型看一张图，然后输出“前进、后退、左转、右转”，这件事已经不神秘了。

但 Roboclaws 这段时间真正想回答的问题不是“AI 能不能让机器人动起来”。这个问题的答案其实很快就能得到。

真正的问题是：**怎样让它持续完成开放式任务？**

它能不能知道自己缺什么信息？能不能失败以后复盘？能不能把一次运行里的经验留给下一次？能不能换一个场景、换一个 simulator、甚至换一台真实机器人以后，仍然复用之前积累出来的经验？更重要的是，它到底做了什么，能不能被人类审计？

我们现在对 “robot brain” 的理解，不是一个单独的模型，也不是某个大而全的 policy。它更像一套可以持续工作的任务执行系统：模型、skills、tools、trace、report、map 和 backend 之间形成一个循环。这个循环能运行，能失败，能留下证据，能被 coding agent 和人类一起改进。

这篇文章想讲的，就是 Roboclaws 怎么从一个“AI 控机器人”的 demo，逐步变成一套 **Skills-first、MCP-bounded、Coding-Agent-Native** 的机器人智能开发方式。

一句话总结：

**把机器人智能放进可迭代的 skill loop，而不是藏在 prompt、backend 或一次性 demo 里。**

---

## 第一步：VLM 直驱，证明“它能动起来”

Roboclaws 最早的路径很直接。

我们在 AI2-THOR 里开一个室内场景，把当前画面、agent 的位置、朝向、可见物体、已访问区域这些信息给 VLM，然后让它输出动作：MoveAhead、RotateLeft、RotateRight、LookUp、LookDown 之类。

这一步很重要。它证明了最小闭环是成立的：大模型确实可以通过视觉和工具接口控制机器人。它能在房间里移动，能转向，能做覆盖，能尝试拍照任务，也能在多 agent 的环境里做一些竞争和协作。

但我们从一开始就知道，VLM 直驱不是最终答案。

问题不在于模型够不够聪明，而在于系统形态不对。策略容易散落在 prompt template、Python loop、临时规则和手工调参里。一次失败之后，很难把经验稳定地沉淀下来。下一次换一个任务、换一个房间、换一个 backend，很多东西又要重新调。

这就是早期 demo 和真正的 brain 之间的区别。

Demo 只需要机器人“看起来会动”。Brain 需要它能持续完成任务、积累经验、被审计、被迁移。

所以 VLM 直驱解决的是第一个问题：**AI 可以控制机器人。**

但它没有解决第二个问题：**机器人智能应该怎样被开发和维护。**

---

## 为什么我们需要 Harness

机器人任务不是一次模型调用。

一个开放式任务更像这样：

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

这个循环里，每一步都需要工程系统支撑。任务怎么表达？工具边界怎么设计？模型看到什么、不看到什么？失败怎么算？运行结果怎么复盘？经验写回哪里？用户怎么介入？换 simulator 或真实机器人时，哪些东西应该保留，哪些东西应该替换？

这就是我们后来越来越重视 harness 的原因。

Harness 不是外围工程。对于 robot brain 来说，harness 本身就是智能的一部分。它决定模型能看到什么、能调用什么、失败后能不能学到东西、学到的东西能不能进入下一次运行。

如果没有 harness，机器人智能很容易退化成“一次 prompt + 一次动作序列”。它也许能跑出一个惊艳 demo，但很难成为一个持续演化的系统。

---

## 为什么我们最初选择 OpenClaw

我们最初选择 OpenClaw，是因为它非常接近我们想象中的 high-level AI harness。

OpenClaw 有 SOUL，可以描述 agent 的人格和行为倾向；有 Skills，可以封装能力；有 MCP，可以连接外部工具；有 Control UI，可以让用户直接和 agent 交互。它天然适合把一个能力包装成“可聊天、可控制、可产品化”的 AI 系统。

RoboClaws 这个名字也来自这里：把 robot 接进 Claws 生态，让机器人也拥有一个高层 agent harness。

这一点到现在我仍然觉得是对的。OpenClaw 是很好的用户交互层，也是一种非常完整的产品形态。它让机器人能力可以被用户看见，可以通过对话使用，可以有 personality，可以有 UI。

但在真正研发 robot brain 的过程中，我们逐渐发现，推进效果最快的地方不只是用户交互，而是另一个更底层的循环：

**skill / MCP / trace / report / failure / edit / rerun。**

也就是说，真正的难点不是“让用户能和机器人聊天”，而是“让系统能根据运行结果不断改进自己”。

这时，Claude Code、Codex 这类 coding agent 反而变成了更合适的研发核心。

---

## Coding Agent 更像一个 Robot Brain Workshop

Claude Code 和 Codex 这类 coding agent 适合做机器人研发核心，不是因为它们更会聊天，而是因为它们天然拥有一组非常适合智能系统迭代的能力。

它们会读文件，会改文件，会运行命令，会看 trace，会读 report，会根据失败修改 skill，会调整 MCP server 或 task runner，也会把一次运行里的经验写回下一次能使用的地方。

这和普通 assistant harness 很不一样。

机器人任务失败以后，最重要的不是让模型重新回答一次，而是让它进入工程系统：看 trace，找失败原因，改 skill，改 checker，改 MCP 边界，重新跑，对比 report，再把成功经验沉淀下来。

这个循环非常像软件工程里的测试、调试、回归和重构。区别只是它的 substrate 不是普通代码库，而是机器人任务。

我们在 Roboclaws 里看到过很多这样的例子。一个拍照任务，一开始可能是 agent 在房间里靠视觉试错，来回走、撞墙、漏掉目标。后来它会学到：先读取场景里的目标列表，再按目标逐个导航、观察、拍照。再后来，这些经验会进入 SKILL.md，成为下一次运行的默认策略。

这件事的关键不只是“这次跑通了”。关键是：**跑通的方法被写回了 skill。**

这也是我们现在对 coding agent 的一个更大判断：它不只是机器人控制器，更像 robot brain 的研发环境。

甚至不只机器人。接下来一段时间里，coding agent 很可能会成为很多行业构建自定义智能系统的最好平台。不是每个行业都应该从零做一个垂直 agent framework。更现实的路径可能是：把行业里的任务、工具、检查器、报告和经验沉淀进 coding-agent-native 的 loop 里，让 coding agent 成为最快的研发环境。

机器人只是这个趋势里最直观、最严格、也最能暴露问题的场景。

---

## Skills First：brain 应该沉淀在哪里？

这也是 Roboclaws 现在最核心的架构判断：**Skills first**。

Skill 不应该只是一个装饰性的 prompt 文件。它应该是机器人智能最重要的承载层。

任务策略写在 skill 里，经验沉淀在 skill 里，recovery loop 写在 skill 里，examples 和 checks 放在 skill 里。coding agent 可以直接读它、改它、运行它、根据 report 优化它。不同 backend 也可以共享同一套 skill 语义。

这解决了 VLM 直驱和早期 harness 的一个核心问题：智能不再散落在 Python loop、prompt template、backend adapter 或临时对话里，而是沉淀在一个可以被人和 agent 共同维护的 artifact 中。

Roboclaws 现在的抽象大概是这样：

```text
Open-ended goal
-> Runnable Task
-> Agent Skill
-> Capability Profile
-> MCP Capability Tools
-> Backend Variant
-> Artifacts and Reports
```

Runnable Task 负责“要跑什么”，比如 `semantic-map-build`、`household-cleanup`、`photo-chairs`。Agent Skill 负责“怎么做”。Capability Profile 说明这个 skill 可以依赖哪些能力。MCP Tools 暴露稳定的机器人能力。Backend Variant 决定具体在哪个 simulator、哪个 SDK、哪台机器人上执行。

这个分层看起来朴素，但非常重要。

因为它把“智能应该写在哪里”这件事讲清楚了。

不是每次都重写 prompt。不是把任务藏进一个巨大工具。不是每换一个机器人就重新发明一套 agent API。真正可复用、可迭代的经验，应该进入 skill。

**Skills first 的意思是：把机器人智能放在最容易被模型、人类和工程系统共同迭代的地方。**

---

## MCP Bounded：工具不是越大越好

MCP 很重要，但 MCP 不应该吞掉整个任务。

一个很诱人的设计是做一个大工具：

```text
cleanup_room()
```

agent 调一次，房间就被整理好了。这个接口看起来很方便，但它把智能藏起来了。agent 不知道中间发生了什么，人类也很难审计。失败以后，我们也不知道应该改 skill、改工具、改 perception、改 map，还是改 backend。

Roboclaws 更倾向于 bounded capability tools。

比如 observe、navigate、move、pick、place、open、close、done、metric_map、inspect_visible_object、declare_visual_candidates。它们不是完整任务，而是稳定、可审计、可替换的机器人能力边界。

任务本身应该留在 skill 里。skill 可以决定先观察、再建图、再找目标、再移动、再检查、再执行动作。每一步都能留下 trace。失败时，也能知道失败发生在哪个边界。

这里还有一个很重要的点：仿真里有些工具非常方便，比如 `scene_objects`、`goto`。它们可以帮助 demo、调试和 smoke test，但必须诚实标注为 privileged tools。因为真实机器人默认并没有“完整场景物体列表”，也不能直接 teleport 到目标旁边。

如果我们把这些 simulator oracle 当成真实能力，整个抽象就会污染。

所以 MCP 的价值不是把任务藏起来，而是给 skill 一个稳定、可审计、可替换的能力边界。

---

## Minimal Map：开放式任务需要世界记忆

当任务从“拍椅子”变成“整理房间”时，机器人需要的不只是当前画面。

它需要一个世界状态。

哪些区域可以走？哪些地方值得探索？刚刚观察到了哪些物体？哪些 surface 或 receptacle 可以作为 destination hint？哪些 prior 需要当前确认？哪些 map update 只是候选，不能直接写回 source map？

这就是 Runtime Metric Map 的意义。

但我们的选择不是先手写一个很丰富的 semantic map。真实机器人往往也不会一开始就有完整、干净、人工标注好的语义地图。更现实的起点是 minimal map：occupancy / free-space、pose / frame metadata、safety bounds、generated exploration candidates。

然后让 `semantic-map-build` 通过观察逐步构建 Runtime Metric Map，再让 `household-cleanup` 消费这份 evidence。

这件事对 Roboclaws 很关键。因为它说明我们不是只在做“coding agent + MCP”的玩具 demo，而是在处理开放式机器人任务里真正绕不开的问题：世界状态如何建立、如何更新、如何给 agent 使用、如何不泄露 private evaluator truth、如何从仿真过渡到真实机器人。

我个人觉得，在仿真里把这类任务做完，已经足够推广这个方向了。

MolmoSpaces 这类大规模、开放的 household 场景，本身就是一个很好的 rehearsal ground。它能承载很多接近真实落地的任务：整理、搜索、检查、拍照、盘点、房间理解、rearrangement。我们不必一开始就把所有压力都放到真机上。先在足够开放的仿真环境里，把 task、skill、map、MCP、report 这些抽象跑干净，本身就很有价值。

真正可迁移的 robot brain，不应该依赖手写完整语义地图，而应该能从 minimal map 和公开观察中逐步建立任务所需的世界记忆。

---

## Report / Trace / Map：让机器人任务可审计

机器人任务不能只输出一句 “done”。

它必须留下足够证据，让人知道：它看到了什么，调用了哪些工具，去了哪里，为什么判断任务完成，哪些信息是 agent 看到的，哪些是 private evaluator truth，哪些能力是真实执行，哪些只是 blocked 或 simulated，失败发生在哪里。

所以 Roboclaws 的每次 serious run 都尽量留下 reviewable artifacts：`trace.jsonl`、`run_result.json`、`agent_view.json`、`runtime_metric_map.json`、`report.html`，以及需要时的 robot-view images、map preview、planner proof bundle。

这不只是为了好看。

Report 和 trace 是 skill 进化的燃料。没有 report 的机器人 demo 很难让人相信；没有 trace 的 robot brain 很难持续进化。

如果一次失败只停留在“它没做好”，那下次很可能还会失败。但如果失败能变成 trace，trace 能变成 report，report 能变成 skill 修改，skill 修改能进入下一次运行，那么失败就不只是失败，它会变成系统的一部分。

这也是 coding agent 为什么适合这件事。它可以直接消费这些 artifact，然后改系统。

---

## OpenClaw 回到正确位置

经过这些尝试后，OpenClaw 在 Roboclaws 里的位置反而更清楚了。

OpenClaw 很适合作为用户交互层。它适合承载 Control UI、SOUL、对话入口和用户体验。当 skill、MCP、profile 这些抽象稳定之后，OpenClaw 可以直接接进来，复用 coding agent 研发出的 skills 和 capability boundary。

但日常研发、效果迭代、failure analysis、skill evolution，更适合放在 coding agent loop 里。

所以这不是 OpenClaw 和 coding agent 谁替代谁的问题。它们更像两层：OpenClaw 是很好的产品入口和交互层，Coding Agent 是更高效的 brain workshop。

这个分工对我们很重要。因为它让 Roboclaws 既可以继续利用 OpenClaw 这种 high-level harness 的产品形态，也可以用 coding agent 快速打磨底层 skills 和 MCP 能力边界。

---

## 一个经验：最强模型做开发，快模型跑任务

这里还有一个很实用的 takeaway，但我不想把它写成严格 benchmark。它更多是我们目前的工程经验。

我们现在更倾向于把模型使用分成两层。

开发和优化阶段，尤其是 MCP、Skill、Checker、Report、Task Runner 的设计与优化，更推荐使用 Claude Code 或 Codex 搭配官方最强模型。

因为这一阶段最重要的是修改能力和长期推理能力。模型需要读代码、改代码、读 trace、看 report、理解失败边界。尤其是 Skill 优化，需要模型真的理解任务结构和失败原因。这里的优化结果会沉淀到 repo、skill、MCP contract、checker 和 report 里，可以被后续更快模型复用。

但真正运行任务时，不一定每次都需要最强、最贵、最慢的模型重新发明策略。

当 skill 已经被强模型优化过以后，我们更推荐使用更快、足够强、具备视觉理解能力的模型来跑任务，比如 Claude 或 Codex harness 搭配 Kimi、MiMo 这类更快的模型路线。

好的 skill 已经把关键经验、约束、工具使用方式写清楚。快模型可以更高频地执行、观察、调用工具，成本和速度更适合大量 episode、仿真任务和后续真实机器人测试。只要 skill 和工具边界足够好，运行效果仍然可以足够稳定。

简单说：**用最强的 coding agent 优化 skill，用更快的视觉模型执行任务。**

这不是全文最核心的论点，但我觉得是一个很实用的工程经验。

---

## 同一个 brain，多个身体

当 task、skill、profile、MCP、report boundary 稳定后，backend 就可以替换。

AI2-THOR 可以证明导航、覆盖、拍照。MolmoSpaces / MuJoCo 可以证明 household cleanup。Isaac 可以提供更真实的 USD scene、renderer、segmentation、semantic pose evidence。Agibot G2、Nav2、Unitree G1 或其他机器人，也都可以作为 physical backend variant 接进来。

关键不是“我们支持了很多 backend”。

关键是：**backend 只是身体，skill / MCP / report loop 才是 brain。**

这也是我们为什么一直强调 backend variant，而不是为每台机器人重新发明一套 agent-facing API。

真实机器人当然会带来更多边界：安全门、定位、地图、感知失败、运动控制、急停、operator gate。这些都不能被忽略。但它们应该通过 provenance、blocked capability 和 report evidence 诚实表达，而不是污染 task 和 skill 的形状。

如果大家手里有智元 G2、宇树 G1 或其他机器人，其实可以尝试把它作为 backend variant 接进来。理想情况下，你修改的是 backend adapter，而不是重写整个 task、skill、MCP 和 report 系统。

这里要讲清楚边界：仿真 proof 不等于 hardware proof，semantic pose 不等于真实 manipulation。真机是非常重要的下一步，但这篇文章的重点不是宣称某台机器已经完成了完整 cleanup，而是说明这套抽象为什么有机会自然走向真机。

可扩展性的核心不是多接几个 backend，而是让 backend 永远处在可替换层。

---

## 这不是替代底层 robotics

这里也需要主动划清一个边界。

Roboclaws 不是要替代 VLA、RL、motion planning、whole-body control、robot SDK 或底层控制系统。

我们现在关心的是开放式任务层：任务理解、skill 选择和改进、bounded tool calling、世界证据、report / trace、simulator / hardware contract parity、backend-replaceable task execution。

底层 policy、controller、planner、robot SDK 仍然是 backend 的一部分。Roboclaws 想做的是让上层智能能够以干净、可审计、可迁移的方式调用这些能力。

换句话说，我们不是替代底层控制，而是在为开放式机器人任务搭一个可迭代、可审计的智能层。

---

## 多 Agent 是自然延伸，但不是这篇的主线

Roboclaws 早期其实有很强的 multi-agent 色彩。多个机器人在同一个场景里竞争、协作、覆盖、分工，这仍然是我们很感兴趣的方向。

但这篇文章不想把多 agent 作为主线。

原因很简单：先把一个 robot brain 的开发 loop 做干净，多 agent 才有稳定的地基。

一旦单个 robot brain 的 task、skill、tool、report 抽象稳定，就可以自然扩展到多个机器人如何共享 map evidence，多个 agent 如何分工，竞争和协作任务如何审计，一个 agent 的 skill 改进如何影响整个团队，以及多 agent 是否需要共享 skill library 或独立 personality。

这些都值得做，但它们是下一层复杂度。

---

## What’s next：我们希望大家一起做什么

如果你对这个方向感兴趣，我最希望大家先从仿真里的复杂任务开始。

MolmoSpaces 是一个很大、很开放、很适合机器人落地前 rehearsal 的场景集合。它不应该只被用来跑一个固定 benchmark。我们更希望大家把它当成一个开放世界任务沙盒：自己定义复杂 household task，尝试 inspection、search、cleanup、rearrangement、photo capture、inventory、room understanding 等任务。

这些任务会很快暴露出真正重要的问题：哪些任务只靠 skill 和 MCP 就能解决？哪些任务需要新的 public capability？哪些任务暴露了 map、perception、planning、report 的新边界？

第二件我们非常欢迎大家一起做的事，是优化 Skills。

很多 robot intelligence 的改进不会来自某个巨大工具，而会来自很多小的 skill 改进：更好的任务分解，更好的观察策略，更好的失败恢复，更好的 map 使用方式，更好的 object / receptacle reasoning，更好的 runtime evidence 写法，更好的 checker 和 report gate。

这些东西看起来不像传统 robotics paper 里的“大算法”，但它们会直接决定一个 agent 能不能稳定完成开放式任务。

第三件事，是支持更多机器人和 backend。

如果你手里有智元 G2、宇树 G1 或其他机器人，可以尝试把它作为 backend variant 接进来。我们希望新的机器人不需要重写一整套 agent API，而是尽量复用同一套 task、skill、profile、MCP 和 report boundary。

第四件事，是从仿真迁移到实机。

如果 task / skill / MCP / report boundary 做得足够干净，从仿真到实机不应该是重写整个系统，而应该是替换 backend。当然，真实机器人会引入更多安全和物理边界，但这些边界应该进入 backend provenance 和 report evidence，而不是让 agent-facing task 变得混乱。

如果你想尝试“用 coding agent 驱动一个真实系统”，机器人是一个非常好的压力测试场。如果你想尝试“给机器人加 brain”，Roboclaws 希望成为一个足够简单、足够透明、足够可扩展的起点。

---

## How hard can it be?

回到标题。

“给机器人加一个大脑”这件事，第一步确实没有想象中难。让模型看图、调用动作接口、在仿真里移动起来，很快就能看到效果。

但真正难的是把它做成一个系统：能理解开放式任务，能选择和改进 skill，能通过 bounded tools 调用机器人能力，能记录 trace 和 report，能从失败中学习，能从仿真迁移到更真实的 backend，能最终接到真实机器人，也能让人类相信它做了什么、没做什么、哪里还没有证明。

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

我们不认为这套方案只适用于机器人。机器人只是一个非常直观、非常严格的测试场：它有空间、有动作、有失败、有安全边界、有真实世界约束。

如果 coding agent 可以在这里帮助我们构造、迭代、审计一套 robot brain，那么类似的方法也可能适用于更多开放式智能系统：实验室自动化、浏览器操作、数据分析 pipeline、生产系统运维，甚至任何需要长期运行、持续改进、可审计工具调用的智能工作流。

**How hard can it be?**

比想象中难。但也比想象中更清楚。

答案也许不是从零造一个新的行业 agent framework，也不是把智能藏进一次性 demo，而是把行业知识、任务经验和工具边界放进一个能持续迭代的 skill loop 里。

这就是 Roboclaws 现在正在尝试的方向。
