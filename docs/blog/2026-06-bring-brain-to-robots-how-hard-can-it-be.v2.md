# Bring Brain to Robots: How Hard Can It Be?

> **Why coding agents may be the simplest baseline for robot intelligence**  
> **为什么 coding agent 可能是机器人智能最简单的起点**

我很喜欢 *Top Gear* 里那种 “How hard can it be?” 的气质。

它不是说事情真的简单，也不是说一定不会翻车。恰恰相反，它的意思更像是：这个东西看起来很直观，我们大概知道会踩坑，但先把车开起来，看看它到底会坏在哪里。

做 roboclaws 的感觉也很像。

有了大模型之后，整个社区对“AI 控机器人”这件事的直觉都变了。以前我们会问：模型能不能看懂画面？能不能规划动作？能不能调用工具？能不能写代码？现在这些问题的答案都越来越接近 “yes”。VLM 能看图，LLM 能调工具，coding agent 能读代码、跑命令、改文件，MCP 又给了大家一个很自然的工具协议。

于是问题就变成了：

> 把这些东西接到机器人上，How hard can it be?

一开始我们也是这么想的。让机器人动起来并不难。让一个模型看一帧画面，输出 `MoveAhead`、`RotateLeft`、`PickObject` 这类动作，也不难。把一个 simulator 包成 MCP server，让 Claude Code 或 Codex 调工具，也不难。

真正难的是另一件事：

**怎样让机器人完成开放式任务？**

不是“向前走一步”，而是：

> “把这个房间整理一下。”  
> “给所有椅子拍照。”  
> “先探索这个空间，再告诉我哪些东西可以清理。”  
> “如果失败了，下一次要变得更好。”

这类任务要求机器人不只是会发动作。它需要知道自己有哪些能力，需要理解当前世界，需要选择策略，需要留下证据，需要从失败里复盘，需要把经验沉淀下来，还要能迁移到不同 simulator、不同 backend，甚至真实机器人上。

这才是 roboclaws 这几个月真正想回答的问题：

> **我们到底怎样给机器人以大脑？**

现在我们的答案越来越清楚：

```text
code-agent first
skills first
MCP bounded
harness verified
```

更直白一点说：

> 先把 coding agent 当成机器人智能研发的 baseline；  
> 把策略沉淀成 skills；  
> 把机器人能力收敛成边界清楚的 MCP tools；  
> 用 harness、trace、map、report 去验证每一次运行。

这不是唯一的路线。但这是我们目前找到的最直观、最简单、也最可扩展的切面。

---

## 1. 让机器人动起来不难

#REVIEW: 这里，希望像 V1 一样，提前指出来，我们很明确的知道直接完全使用 LLM 来做是没有太大意义的，因为它基本上是要从头做所有需要做的事情

roboclaws 最早的形态很直接：让 VLM 看机器人画面，然后输出动作。

在 AI2-THOR 里，我们可以把当前状态渲染成第一视角图像、地图、agent 位置、可见物体、已访问区域，再把这些信息喂给模型，让它选择下一步动作。多个 agent 可以同时跑，有的负责覆盖房间，有的做 territory game，有的比较不同模型的决策差异。

这种方式非常适合做 demo。

反馈快，改 prompt 快，接新模型也快。你可以在一个下午里看到机器人真的动起来：它会转身，会避障，会尝试靠近目标，会在房间里探索。作为第一步，这很重要。因为如果连这个都跑不起来，后面所有关于“智能”的讨论都只是空谈。

但跑多了之后，我们很快发现一个问题：

**VLM 直驱更像一个很聪明的遥控器，而不是一个会成长的机器人系统。**

它的问题不在于模型不够聪明，而在于系统形态不对。

策略写在 prompt 里，或者写在 Python loop 里。机器人失败以后，经验不会自然沉淀。你发现“它应该先扫描房间再行动”，那就去改 prompt。你发现“它总是在某个角落卡住”，那就再加一条规则。你发现“拍照任务应该先列出所有目标”，那就再改一次 system prompt。

这些改动当然有效，但它们不是一个真正的技能系统。它们没有被独立管理，没有被清楚测试，也很难被其他入口复用。

这时候我们意识到，真正的问题不是模型能不能控制机器人，而是：

> 机器人完成任务的经验，应该放在哪里？

如果它只放在 prompt 里，系统会越来越脆。  
如果它只放在 backend 代码里，智能会被藏进工具。  
如果它只存在于某一次对话里，下一次就会丢失。

我们需要一个 harness。

---

## 2. OpenClaw 给了我们最早的形状

这也是 roboclaws 这个名字的来源之一。

我们最初非常自然地看向 OpenClaw。因为 OpenClaw 不是一个低层机器人 SDK，而是一个 high-level AI harness：它有 Skills，有 SOUL，有 MCP，有 UI，有长期运行的 daemon，也有面向用户的交互入口。

#REVIEW: 这里可以稍微补一下，OpenClaw 出现之后，其实所有做机器人研发的同事，大家都会想到，那我们直接把机器人接到 OpenClaw 里面，是不是就行了？而且社区的确也有很多在做类似尝试的。比如维他动力的狗子、地平线 kakaclaw 等，github 上也有很多相关的 repo。

这和我们想要的东西非常接近。

如果目标是“给机器人接一个大脑”，那机器人不应该只暴露一组底层动作。它应该被接进一个更高层的 agent harness 里：用户可以和它说话，agent 可以选择 skill，skill 可以调用 tools，运行过程可以被观察，结果可以被展示。

所以我们把 AI2-THOR navigator 包成 skill，通过 OpenClaw Gateway 接进来。这样研发人员就可以在浏览器里看到机器人画面，一边看一边对 agent 说话。比如机器人卡住了，可以直接告诉它：“先左转，再往前走。” 比起停掉脚本、改 prompt、重新跑，这种交互形态自然很多。

这一步让我们确认了一件事：

**机器人需要的不是更多裸动作，而是更高层的 harness。**

但真正开始做 skill 研发之后，我们又撞到了另一个问题。

OpenClaw 很适合做用户交互，也很适合做 high-level assistant 入口。但机器人任务的研发闭环，尤其是开放式任务的研发闭环，需要非常高频地做几件事：

#REVIEW: 我们最一开始其实没有发现要做下面这么多事情（trace, 改 skill， xxx），我们最一开始真的是和 claude 讨论后，写了一个最简的 MCP 以及 Skill 实现，然后直接给到 Openclaw 然后让它去执行我们进行比较开发性的任务，，它其实也能跑，但是跑得很慢，效果其实很差。这个时候我们需要去手动的改 MCP 以及实现，因为它的输入就这些嘛。但 openclaw 整个抽象层级也比较多，可观测性也不是那么容易添加，调试以及优化起来没有那么简单。

读 trace；  
看失败；  
改 skill；  
跑任务；  
看 report；  
再改 skill；  
再跑。

这件事，Claude Code / Codex 这类 coding agent 反而天然更适合。

所以我们后来对 OpenClaw 和 coding agent 的关系有了一个更清楚的判断：

> **OpenClaw gave us the shape. Coding agents gave us the loop.**

OpenClaw 让我们看到机器人应该接进一个 high-level harness。  
Coding agent 让我们看到，这个 harness 可以自己迭代 skill。

这不是说 OpenClaw 被替代了。恰恰相反，OpenClaw 仍然非常适合做人机交互、UI、长期 daemon、语音入口、用户-facing assistant。只是对于 roboclaws 当前阶段的研发来说，最快的闭环来自 coding agent。

我们可以先用 Claude Code / Codex 把 skills 打磨好，再接回 OpenClaw。这样 OpenClaw 端自然也能受益。

---

## 3. Coding agent 不只是写代码的工具

这个转折对我们很关键。

最开始，我们把 Claude Code / Codex 当成开发工具。它们帮我们写代码、改测试、看日志。这是所有人都熟悉的用法。

但后来我们发现，在机器人这个场景里，coding agent 不只是“帮我们开发 roboclaws”。它本身就可以成为机器人智能研发的 baseline。

原因很简单：coding agent 已经具备了很多机器人智能系统需要的能力。

它能读 repo。  
它能读文档。  
它能读 `SKILL.md`。  
它能调用 MCP tools。  
它能跑任务。  
它能看 `trace.jsonl`。  
它能分析失败。  
它能改 skill。  
它能重跑。  
它能把经验写回文件系统。  
它还能把这些改动变成 git diff，接受 review。

这听起来像软件开发，但机器人智能研发本质上也越来越像软件开发。

一次机器人任务失败，不应该只是“模型这次没做好”。它应该产生证据：它看到了什么？调用了什么？地图里有什么？哪一步失败了？这个失败是感知问题、导航问题、工具边界问题，还是 skill 策略问题？

如果这些证据都在 repo 和 artifacts 里，那么 coding agent 就可以参与这个 loop。它不只是执行者，也是维护者。

我们在 AI2-THOR photo task 里看到过一个很直观的例子。用户给机器人一个开放式任务：给房间里所有沙发和椅子拍照，要求走到正前方，确保每张图里只有一个目标。

一开始，agent 会像人类第一次进房间一样探索、试错、移动、观察。后来它发现更稳定的策略是：先拿到房间里的目标列表，再逐个导航、调整视角、拍照、归档。这个经验被沉淀进 skill 以后，同一个任务就稳定很多。

#REVIEW: 这里可以补一个 GitHub 的截图。以及一些小的 metrics 展示，我们应该是 MCP 的 two call 以及耗时这里，有很大优化

最有意思的不是某一次跑通，而是这条经验可以留下来。下一次 Claude Code 读到这份 skill 会用它，OpenClaw 端的助手读到同一份 skill 也会受益。

这就是我们现在越来越相信的一句话：

> **Don’t build a robot brain from scratch until you have beaten a coding agent with tools.**

在证明自己比 coding agent + tools 更强之前，不要急着从零重造一个机器人“大脑”。

这不是说 coding agent 永远是最终答案。未来我们可能会基于 Anthropic Agent SDK、OpenAI Agents SDK，或者自己更底层的 runtime 去做。我们也可能加语音、UI、权限、长期记忆、任务队列、多人协作。

但在今天，如果一个自研 robot brain 连 Claude Code / Codex + tools + repo artifacts 的闭环都打不过，那它大概率还不是一个更好的起点。

所以 roboclaws 当前的研发路线非常明确：

**code-agent first。**

先用 coding agent 作为 baseline。  
先让它读 skill、调工具、跑任务、看 trace、改 skill。  
如果要替换它，就拿出更好的 loop。

---

## 4. Brain 不是一个模型，而是一套技能系统

这里需要澄清一个词：brain。

我们说 “Bring Brain to Robots”，很容易让人以为 brain 指的是某个模型。比如给机器人接 Claude、接 GPT、接 Gemini，或者接一个 VLA policy。

但在 roboclaws 里，brain 不是单个模型，也不是某个 UI assistant，也不是 OpenClaw、Codex、Claude Code 或某个机器人 SDK。

我们现在更愿意这样定义：

> **Brain 是一套可以被 agent 持续维护的技能系统。**

它至少包括四层。

第一层是 **skills**。Skill 承载任务策略。比如怎样拍照，怎样清理房间，怎样探索空间，怎样从失败中恢复。Skill 里可以有说明、例子、脚本、检查逻辑、操作习惯。它不是一次性的 prompt，而是可以被读、被改、被 review、被测试的行为资产。

第二层是 **MCP capability surface**。MCP tools 承载机器人能做什么。比如 observe、move、navigate、pick、place、done。它们应该边界清楚，输入输出稳定，并且尽量不要把整个任务智能藏进去。

第三层是 **world state**。机器人不能只靠当前一帧画面做决定。它需要地图，需要观察记录，需要 runtime memory，需要知道哪些物体是刚刚看到的，哪些目标是 public evidence，哪些信息只是 evaluator private truth，不能泄漏给 agent。

第四层是 **feedback loop**。每次运行都应该留下 trace、map、report、score、failure reason。否则失败就只是失败，不能变成下一次 skill 的改进。

这四层合起来，才比较接近我们说的 robot brain。

一个模型可以很聪明，但如果它没有 skill，没有工具边界，没有世界状态，没有反馈闭环，它仍然只能像一个强大的遥控器。

反过来，一个足够好的 skill system，可以让不同模型、不同 client、不同 backend 都复用同一套经验。

这就是为什么 roboclaws 现在是 **skills first**。

---

## 5. Skills first

Skills first 的意思是：开放式任务的策略，应该优先沉淀在 skill 里，而不是散落在 prompt、backend、UI 或 simulator helper 里。

用户说：

> “clean the room”

这不应该直接变成一个巨大的 `clean_room()` MCP tool。

用户说：

> “take useful photos of all chairs and sofas”

这也不应该只是一次 prompt。

它应该先进入一个 skill。Skill 决定怎么拆任务，怎么观察，怎么选择目标，怎么导航，怎么验证结果，失败时怎么恢复。Skill 可以调用 MCP tools，但 skill 自己不是一个机器人底层能力。

这个区别很重要。

如果我们把整个任务都包进 MCP tool，demo 会很快，但智能就被藏进工具里。agent 看起来完成了任务，其实只是调用了一个 opaque function。下一次想迁移 backend、想 debug 失败、想让另一个 agent 学到经验，就会变得很困难。

如果我们把策略放在 skill 里，事情就清楚很多：

task 负责“这次要跑什么”；  
skill 负责“怎么做”；  
MCP tools 负责“机器人有哪些可调用能力”；  
backend 负责“这些能力在具体环境里怎么执行”；  
report 负责“这次到底发生了什么”。

这也是 roboclaws 现在的抽象阶梯：

```text
open-ended goal
  -> runnable task
  -> agent skill
  -> capability profile
  -> MCP capability tools
  -> backend variant
  -> artifacts and reports
```

这个结构看起来很朴素，但它解决了一个非常实际的问题：

**智能应该被放在可维护、可复用、可审计的位置。**

Skill 是这个位置。

---

## 6. MCP bounded

和 skills first 配套的原则是：MCP 要 bounded。

这点我们是踩过坑之后才越来越明确的。

做 simulator demo 时，人会很自然地想给 agent 暴露一些很方便的工具。比如完整物体列表，比如直接传送到目标旁边，比如一个工具完成一整段任务。这些 helper 对 demo、debug、smoke test 都很有用。

但如果我们认真想把这套东西迁移到真实机器人，就必须诚实地区分：

什么是机器人真实可拥有的能力；  
什么是 simulator privileged helper；  
什么是 private evaluator truth；  
什么只是为了测试方便。

真实机器人没有上帝视角的 object inventory。  
真实机器人不能 teleport 到目标旁边。  
真实机器人也不应该看到 hidden acceptable destination。

所以 MCP tools 应该尽量保持为边界清楚的 capability：

observe；  
move；  
navigate；  
pick；  
place；  
open；  
close；  
done。

这些工具不应该假装自己拥有完整任务智能。它们只是机器人公开能力的边界。

至于“怎样完成开放式任务”，让 skill 去做。  
至于“怎样改进策略”，让 coding agent 在 trace 和 report 里做。  
至于“backend 具体怎么实现”，让 backend variant 去处理。

这就是 **MCP bounded**。

工具越大，demo 越快，但智能越不清楚。  
工具越清楚，skill 才越有价值，迁移也越可能成立。

---

## 7. Harness verified

机器人系统还有一个问题：它很容易骗自己。

一次任务看起来跑完了，但它到底做了什么？  
它看到的图像是什么？  
它用的是 public evidence，还是偷看了 private truth？  
它有没有真的导航到目标附近？  
它的 cleanup score 是怎么来的？  
失败是因为模型没想对，还是工具返回不稳定，还是 backend 没有实现能力？

如果这些问题没有证据，机器人 demo 就很难被认真 review。

所以 roboclaws 现在非常强调 artifacts 和 reports。我们希望每次严肃运行都留下：

trace；  
frames；  
maps；  
agent view；  
runtime state；  
score；  
failure reason；  
report.html。

这不是为了好看，而是为了让 skill 可以进化。

没有 trace，coding agent 就不知道哪里失败。  
没有 map，agent 就不知道世界状态如何变化。  
没有 public/private boundary，系统就不知道自己有没有作弊。  
没有 report，人类也无法判断这次结果能不能被相信。

这也是我们后来做 minimal map 和 Runtime Metric Map 的原因。

真实机器人通常不会一上来就拥有完整的手写语义地图。更合理的起点是一个 minimal navigation map：occupancy/free-space、pose、frame metadata、safety bounds、generated exploration candidates。它告诉机器人哪里大概能走，但不提前告诉它“这里是厨房、那里是水槽、桌上有杯子”。

然后我们让 `semantic-map-build` 这类任务去构建 Runtime Metric Map。

也就是说，机器人从 public observation evidence 里逐渐建立世界状态：它看到了什么物体，哪些地方可能是 receptacle，哪些候选目标可以后续清理，哪些语义锚点有足够证据。cleanup 再消费这个 runtime map，而不是依赖一个全知的手写语义地图。

这件事把“机器人智能”从动作控制推进到了世界理解。

如果说 skill 解决的是“怎么做”，Runtime Metric Map 解决的就是“我现在知道这个世界什么”。

如果说 MCP 解决的是“我能调用哪些能力”，report 解决的就是“我凭什么相信这次真的做了”。

这就是 **harness verified**。

---

## 8. Backend 只是落点，不应该污染智能抽象

当 skill、MCP、runtime map、report 的边界稳定以后，backend 就变成了可替换的执行层。

这件事对 roboclaws 很重要。

最早我们在 AI2-THOR 里做导航、拍照、多 agent demo。后来我们开始做 MolmoSpaces household cleanup，因为它更接近真实 household manipulation 场景。再后来，我们接 Isaac Lab，希望获得更真实的 USD scene、camera、segmentation、robot-view evidence。再往后，Agibot G2、ROS2/Nav2、真实机器人都可以作为 backend variant 接进来。

但关键不在于“支持了多少 backend”。

关键在于：**agent-facing 的智能抽象不应该因为 backend 变化而完全重写。**

同样是 `semantic-map-build`，后面可以是 simulator，也可以是真机。  
同样是 `household-cleanup`，后面可以是 MuJoCo，也可以是 Isaac，也可以是未来的真实 robot backend。  
同样是 skill，它应该依赖 capability profile，而不是直接学习某个 simulator 的私有 API。  
同样是 report，它应该清楚告诉我们这次 evidence 来自哪里，哪些能力是真的，哪些能力仍然 blocked。

这也是我们对真实机器人的态度。

以 Agibot G2 为例，它很适合作为 real-robot navigation + perception pilot。但我们不会因为它有自己的 GDK，就给 agent 暴露一堆 Agibot-specific tools。更合理的做法是：让 G2 成为 backend variant，继续复用 `metric_map`、`observe`、`navigate_to_waypoint` 这类公共形状。GDK map id、PNC primitives、operator relocalization、safety gates，都应该留在 backend 和 report evidence 里，而不是泄漏成 agent 的新语言。

这听起来保守，但它是可扩展的基础。

机器人系统最危险的地方，不是失败，而是假装成功。  
所以 backend 可以越来越多，但 claim boundary 必须越来越清楚。

---

## 9. OpenClaw、Agent SDK、语音和 UI 都可以接回来

如果 coding agent 是当前研发路线的核心，那 OpenClaw、Agent SDK、语音、UI 还重要吗？

重要。

只是它们处在不同层。

Coding agent 最强的是研发闭环：读文件、改 skill、跑任务、看 trace、复盘失败。它非常适合做 skill iteration，也非常适合帮我们把机器人智能系统像软件一样维护起来。

但用户交互不一定永远长得像 coding agent。

用户可能希望在手机上或者直接面对面对机器人交互。  
可能希望用语音控制。  
可能希望有一个长期在线的 assistant。  
可能希望机器人有 personality，有记忆，有权限，有家庭成员区分。  
可能希望它接进 OpenClaw，或者某个基于 Agent SDK 的应用。

这些都合理。

但我们现在的判断是：这些交互层最好建立在已经验证过的 skill system 之上，而不是重新发明一套机器人智能。

也就是说：

先用 coding agent 打磨 skills。  
用 trace 和 report 验证 skills。  
让 MCP capability surface 保持干净。  
让 backend variant 承载具体执行。  
然后把这套能力接回 OpenClaw、语音、UI、Agent SDK 或真实机器人。

这样，用户体验层可以变化，但机器人能力不会散掉。

这也是为什么我们不把 OpenClaw 和 coding agent 看成互斥路线。

OpenClaw 给了我们 high-level harness 和用户交互的形状。  
Coding agent 给了我们最快的研发 loop。  
Skills-first 让两者可以共享同一套行为资产。

---


#REVIEW：不然我们直接移除 10 吧，好像和主线有些偏离
## 10. 多 agent 是自然延伸，但不是这篇文章的主角

roboclaws 这个名字里的复数，一开始确实和多 agent 有关。

我们最早做过多个 agent 在同一个 AI2-THOR scene 里竞争、覆盖、协作。这个方向仍然很有意思。多个 coding agent、多个 robot、共享地图、共享或竞争目标，这里面有很多值得研究的问题。

但如果今天重新讲 roboclaws，我不想先把多 agent 放在最前面。

因为多 agent 是放大器，不是基础。

如果一个 robot 的 skill、tool boundary、runtime map、report 都没有做好，多 agent 只会把混乱放大。反过来，如果单 agent 的智能抽象足够干净，多 agent 就会成为很自然的扩展：多个 agent 可以共享 skill，可以共享或隔离 runtime map，可以通过 report 比较策略，可以在同一套 backend variant 上运行。

所以多 agent 仍然重要，但它不是本文的核心。

本文更想讲的是底层判断：

> 先把一个机器人如何拥有可迭代的技能系统讲清楚，再讨论多个机器人如何协作或竞争。

---

## 11. 这不只是机器人

写到这里，我越来越觉得 roboclaws 不是只在回答机器人问题。

机器人只是一个特别难糊弄的场景。

在普通软件里，一个 agent 说“我完成了”，你有时还可以靠日志、测试、用户反馈慢慢判断。

但机器人不一样。它要么走到了，要么没走到。它要么看见了，要么没看见。它要么把物体放对了，要么报告里会暴露失败。现实世界和仿真世界都会很诚实。

所以机器人迫使我们把很多抽象讲清楚：

开放式任务和 runnable task 的区别；  
skill 和 tool 的区别；  
public evidence 和 private truth 的区别；  
backend primitive 和 agent-facing capability 的区别；  
demo helper 和真实能力的区别；  
一次运行成功和可持续研发之间的区别。

这些区别并不只适用于机器人。

任何想让 AI 做开放式任务的行业，最后可能都会遇到类似问题：

你需要 skills；  
你需要 tools；  
你需要 world state；  
你需要 trace；  
你需要 report；  
你需要 eval；  
你需要失败复盘；  
你需要一个能持续改进系统的 harness。

从这个角度看，coding agent 可能不只是机器人智能的 baseline，也可能是很多智能系统的 baseline。

因为它已经拥有一个非常强的默认环境：repo、文件系统、命令行、测试、日志、diff、review。

如果一个行业想做自己的 agent runtime，一个很朴素的标准是：

> 它有没有打过 coding agent + tools？

如果没有，也许第一步不是重造 agent，而是先把自己的 domain tools、skills、reports 做到 coding agent 能用。

这就是 roboclaws 目前选择的切面。

我们并不觉得这是唯一答案。你可以从 VLA 出发，从 ROS 出发，从 OpenClaw 出发，从 Agent SDK 出发，从 simulator benchmark 出发，最后都可能走到类似的地方。

你需要把策略沉淀下来。  
你需要保持工具边界清楚。  
你需要把运行证据留下来。  
你需要让失败能变成下一次的改进。  
你需要让 backend 可以替换，而不是污染智能本身。

roboclaws 只是选择从 coding agent 这个切面往前试。

它不神秘，也不复杂。它只是非常直接：

既然 coding agent 已经会读 repo、改 repo、跑任务、看 trace、修失败，那就先让它成为机器人智能研发的起点。

---

## 12. How hard can it be?

回到题目。

Bring Brain to Robots: How Hard Can It Be?

如果只是让机器人动一下，真的不难。

如果要让机器人完成开放式任务，很难。

如果要让它失败后变得更好，更难。

如果要让同一套智能迁移到 AI2-THOR、MolmoSpaces、Isaac、Agibot G2 或未来更多真实机器人 backend，同时还能保持证据诚实、边界清楚、能力可审计，那就更难。

但这件事并不是神秘的。

我们现在越来越相信，它可以被拆成一套很直观的工程抽象：

```text
code-agent first
skills first
MCP bounded
harness verified
```

先对标 coding agent。  
把任务策略放进 skill。  
把工具边界收敛到 MCP。  
把世界状态放进 runtime map。  
把每次运行变成 report。  
把失败变成下一次 skill 的改进。  
把 OpenClaw、语音、UI、Agent SDK、真实机器人 backend 接在这套抽象之后。

这就是 roboclaws 现在想探索的方向。

给机器人以大脑，不是接一个聊天框。  
也不是把所有任务都包成一个万能 tool。  
更不是从零造一个神秘的 robot brain。

它更像是建立一套会成长的技能系统。

而在今天，我们认为最简单的起点，是 coding agent。