# roboclaws:给机器人以大脑——一层薄薄的 MCP,几层 skill,然后让 coding agent 进来

> 发布:2026 年 6 月
> 项目:[github.com/MiaoDX/roboclaws](https://github.com/MiaoDX/roboclaws)(全开源,下面提到的每个 demo、report、SKILL.md 都能点进去看)

---

## 楔子

仿真器里有一个被随机弄乱的房间——几个本该在桌上的杯子滚到了地上、海绵掉在水槽外、椅子歪着。我给一个 coding agent 发了一句很普通的话:

> 把这个房间收拾干净。

没有别的。没告诉它房间里有什么、东西该放哪、先做哪个。它自己看了一圈(`observe`),自己规划路线、走过去、识别、搬运,最后调用 `done`,输出了一份它干了什么的报告。

更有意思的是结尾那一步:跑完之后,它把这一趟踩到的一条经验——"先从 occupancy 把可走区域和候选点扫出来,再决定去哪,不要对着墙试探"——**自己写回了 SKILL.md**。下一个 agent 读到这份 skill,起手就不会再去撞那堵墙了。

这就是 roboclaws 现在的样子。这篇想讲的,是我们怎么一步步走到这一步的——以及为什么走到最后,发现答案小得有点不好意思。

<!-- IMG: 留位 — household-cleanup 一次真实跑通的 report 截图(从 miaodx.com/roboclaws/molmo/live/ 拿),作者补 -->

## 1. 大家都说能开机器人,但 how?

"用大模型驱动机器人"这件事,2026 年已经不算新闻了。VLA 一路把成功率刷得很高,coding agent 控仿真机器人也有人做(后面会提)。让一个机器人**动起来**、跟着指令走两步,今天真的不难。

难的是另一件事:**让它真正去完成一个开放式任务**。"把房间收拾干净"没有标准答案——房间每次都不一样、"干净"是模糊的、要先看清楚再决定顺序、中途还会卡住要重来。这种任务才是机器人真正要面对的世界。

而我去 GitHub 上找的时候,意外地发现:**没有一个干净、直观的公开做法**。大家要么在卷端到端的模型,要么在造越来越重的 agent 框架。Andrej Karpathy 在 No Priors 上有个说法叫「skill issue」——当模型本身已经足够强,瓶颈就不在模型了,而在于你怎么定义任务、怎么给上下文、怎么造工具、怎么把 loop 跑起来、怎么评估、怎么把可复用的行为沉淀下来。这话放到机器人上同样成立。

我们的答案,是从第一性原理找到的一个**薄到一眼能抄**的抽象。但在把它摆出来之前,先讲讲我们是怎么试出来的——因为这条路本身,就是这个抽象为什么长这样的理由。

## 2. 我们试出来的路

**第一步,VLM 直驱。** 最早的 roboclaws 就是把仿真画面 + 一段状态文本丢给 VLM,让它吐一个动作 token。它确实能动,多个 agent 还能并行跑领地、覆盖这些游戏。但它只是个 demo:**所有"怎么决策"的逻辑都写死在 Python 里**。想让 agent 学会"先扫一遍再行动"这种新策略,得改 system prompt、重启脚本。VLM 自己不会去改自己的提示词。

**第二步,选了 OpenClaw 当 harness。** 要完成真任务,光有 VLM 不够,得有一层 harness 把"行为"独立出来。我们选了 OpenClaw——它是当时**抽象层级最高**的 agent harness:有 SOUL、有 Skills、有 MCP、有现成的浏览器交互界面,而且**真的能用 skills 扩展出很多东西**。我们一度觉得它就是中心。项目叫 RoboClaws,名字就是从这儿来的(robot + claws,和 OpenClaw 同族)。

**第三步,走到 coding agent,反而更顺。** 真正想要"边跑边改、快速迭代"的时候,我们发现现成的 coding agent(Claude Code / Codex)更合适。它本来就是为长程任务设计的:能编辑文件、能调工具、能反思、能把 loop 真正闭起来。我们把仿真器包成一个 MCP server,让它直接接进来——结果它不光能开机器人,**还能把自己读的那份 skill、那套 MCP 工具自己迭代**。这一点在我们的 git history 里看得清清楚楚:好几次 SKILL.md 的演化,是 agent 自己提的。

**第四步,回头一接,OpenClaw 也能跑。** 把 skill 和 MCP 这套抽象在 coding agent 上打磨好之后,我们顺手接回 OpenClaw——也能跑。所以这不是"OpenClaw 失败了我们换掉",而是反过来:**抽象做对了,上层换谁都行,OpenClaw 那套现成的用户交互界面是白拿的**。

说一句不影响结论的实话:项目还叫 RoboClaws,但今天真正的引擎已经是 coding agent 了。名字留着,引擎换了。

## 3. 那个干净抽象

走到这里,答案就浮出来了。一句话:**从底往上搭,但让 agent 从顶上进来。**

<!-- IMG: blog-2026-06-stack.svg — 自底向上那摞(本文镇文图) -->
![从 backend 到 coding agent 的抽象阶梯](../assets/blog-2026-06-stack.svg)

**最底下是一层薄薄的、语义化的 MCP。** 它只暴露小而干净的机器人能力:`observe`、`move`、`turn`、`pick`、`place`、`open`、`close`、`done`。就这些。它刻意**不**提供 `cleanup_room()` 这种把整个任务藏进一个调用的黑盒——因为一旦那么做,agent 干的活就再也看不见了,而我们要的恰恰是每一步都可审计。

**往上一层,是通用机器人能力。** 导航、地图、定位、搜索、搬运这些,只有当它们的边界足够稳定,才从底层"晋升"上来。这一层旁边长着 capability profile——比如 `household_world_v1`,描述一个可复用的"能力环境"。skill 通过**声明它需要哪些 profile** 来组合能力,而不是把别人的工具列表抄一份再加料。`household-cleanup` 要操作物体,就额外组合一个 manipulation 能力,而不是另造一个把整个 world profile 复制进去的胖 profile。

**再往上,是 skill,而且 skill 是分层的。** 最外面是 agent skill(像 `capture-object-photo`、`cleanup-generated-mess`),每个带一份给 agent 看的 `SKILL.md` 和一份给人和测试看的 `skill.json` manifest。skill 内部可以是一段 trace-preserving 的执行例程,再往里是 composite action——一个老实记录自己每一步的复合动作。

这里借 photo 这个简单任务当例子最清楚:`capture-object-photo` 内部其实是 `locate → navigate → orient → observe → verify` 一串动作。但它**不该**被提升成一个 MCP 工具——它是 agent 的策略,不是机器人的原子能力。什么时候才该把行为升进 MCP?我们定了条规矩:多个 skill 都要、输入输出稳定、子步骤可追溯、只用公开信息、且确实属于机器人能力边界——五条全满足才升,**默认不升**。这条"默认不升"是整套东西能保持薄的关键。

**最顶上,coding agent 从开放式目标进来。** 它拿到"把房间收拾干净",自己去 skill 库里选或者现造一个 skill,然后调下面那层语义工具去干。运行方式就一行,而且全开源,你现在就能跑:

```bash
just task::run household-cleanup claude world-labels seed=7 generated_mess_count=5
```

`<task>` `<driver>` 两个位置,driver 换成 `codex`、`vlm`、`openclaw` 都行。读到这儿你大概会有个反应:就这?——对,就这。我们没藏别的。

最后说两条贯穿整摞的暗线,它们是这套东西"诚实"的来源:

- **公私评估真相分离。** 像 `scene_objects`(直接吐出仿真器里全部物体清单)、`goto`(目标相对传送)这类工具很好用,但它们被显式标成 privileged——**不是真机会有的能力**,默认关掉,demo 要用得自己 opt-in。而私有的评估真相(隐藏的脏乱集合、可接受的归置位置、打分标准)**永远不进**公开的 profile metadata,也不进给 agent 看的 skill 输入。
- **一切可审计。** 每次跑完,画面、地图、工具调用轨迹、得分,全渲染成一份静态 HTML report,而不是埋在终端日志里。我们的 [live reports 站点](https://miaodx.com/roboclaws/)上挂着一堆,点进去就能看 agent 到底干了什么。

诚实交代一句:**用 MCP 控机器人这件事,2026 年已经不 novel 了**——Brian Tsui 的 FAEA、Stanford/Berkeley 的 CaP-X、Anthropic 的 Project Fetch 都做过。我们没发明这个。我们赌的是**把它收拾干净这件事本身**:薄到能抄、skill 分层、sim 到真机一条链、公私评估分离。是 integration 和 taste,不是某个组件。

## 4. 抽象立住之后,白拿到的

把这摞搭对了,有几样东西几乎是免费拿到的。

**(a) 一份会自己更新的 SKILL.md。** 就是楔子里那一幕:agent 失败的时候不只是失败,它会读自己的 trace,看出"前几次 `goto` 都撞墙",然后打开 SKILL.md 加一条经验,下次同任务就带着这条经验起跑。一份 markdown 从"研究员手写的提示词"变成了一份**会自己积累经验的说明书**。这套 self-improvement loop 的实数(同一个任务怎么从 127 次工具调用压到 37 次)留到下一篇专门讲,这里点到为止。

<!-- IMG: blog-2026-06-skill-loop.svg — harness loop + SKILL.md 自演化 -->
![SKILL.md 自演化循环](../assets/blog-2026-06-skill-loop.svg)

**(b) 一份 skill,底下的 backend 可以随便换——而且我们最想让你玩的是仿真。** 同一摞抽象,backend 在最底下换:mock、AI2-THOR、Isaac(还在 in progress,本地 GPU 上已经打通单物体 cleanup 的对齐)、还有 **MolmoSpaces**。

重点说 MolmoSpaces。它是 Allen AI 在 2026 年 2 月发布的 AI2-THOR 精神继承者:23 万+ 室内场景、13 万+ 物体、4200 万抓取标注,够大、够真,跑"把房间收拾干净"这种开放型任务**绰绰有余**。而且它**快、零依赖**——你不需要一台真机器人、不需要任何硬件,装好就能跑。这才是我们真正希望大家上手的地方。

<!-- IMG: blog-2026-06-backend-swap.svg — 上层 skill/MCP 契约不变,底层 backend 并存 -->
![一份契约,多个 backend 并存](../assets/blog-2026-06-backend-swap.svg)

这里还有个我们挺喜欢的细节:**minimal map**。默认情况下我们不把"作者标好的房间真相"喂给 agent,而是只给它 occupancy 几何 + 一些探索候选点,让它自己跑一趟 `semantic-map-build`、自己建出一份 `runtime_metric_map`,再拿这份自己建的地图去做 cleanup。开放型任务本该如此——机器人自己搞清楚世界长什么样,而不是被喂答案。

<!-- IMG: blog-2026-06-minimal-map.svg — occupancy → semantic-map-build → runtime_metric_map → cleanup -->

**(c) 真机也接上了。** 同一摞抽象,换一个 backend variant,我们也把它接到了真机(AGIbot G2):导航的 pilot 跑通了,抓取目前还是 blocked。它证明了**在仿真里调好的东西,真的能往真机迁**。但真机不是这篇的重点——它太慢、依赖太多——所以就一句话带过,我们还是把话题拉回仿真。

## 5. 更大的赌注,以及——来抄

退一步看,这套东西真正想说的,可能比"我们做了个机器人 demo"要大。

**骑现成的 coding agent 做扩展,也许是接下来很长一段时间非常值得做的方向。** 而且不止机器人——几乎所有自定义的智能开发,都可以先在 coding agent 上面做。它已经把文件编辑、工具调用、反思、长上下文这些都给你了,你不需要从零造一个 agent 框架。我们的态度是:**先骑着跑,跑得足够好了再考虑精简**,而不是反过来。

那精简往哪走?两条路都开着:一条是**往下沉**,等抽象稳了,把它落到更底层的 Agent SDK(Anthropic 或 OpenAI 的),再补上我们自己的东西,比如语音控制;另一条是**往上交**,如果 profile 和抽象做得足够好,直接交给 OpenClaw 这种上层助手,所有用户交互就白拿了。多 agent(让多个 coding agent 同时驱动多个机器人)我们也还在赌,但那是另一个故事,这篇先不展开。

回到最实在的一句。这套东西的门槛低到不讲道理:**repo 全开源,你现在就能在仿真里——尤其是 MolmoSpaces 里——干净地复刻一遍,零依赖,不需要任何硬件。** 而一旦你用 coding agent 跑起来、看着它自己改 SKILL.md 一次次变好,那种快速迭代的爽感大概会让你上瘾。

所以这篇没有什么宏大的收尾。就是一句邀请:

**来抄。然后把它扩到你自己的任务、你自己的机器人上。**

[github.com/MiaoDX/roboclaws](https://github.com/MiaoDX/roboclaws) —— Let's bring brain to robots.

---

## 参考(稀疏,详见仓库)

- Andrej Karpathy on No Priors —「skill issue」框架:能力够强后,瓶颈转到任务定义 / 上下文 / 工具 / loop / 评估 / 可复用行为。
- Coding agent 控机器人对照系(说明"MCP 控机器人不 novel"):Brian Y. Tsui, *Demonstration-Free Robotic Control via LLM Agents* (FAEA);CaP-X(coding agent 控操作 benchmark);Anthropic *Project Fetch*。
- Allen AI **MolmoSpaces**(2026-02)—— AI2-THOR 精神继承者,23 万+ 场景 / 13 万+ 物体 / 4200 万抓取标注,USD 导出 MuJoCo / Isaac。
- Anthropic Skills / Model Context Protocol —— SKILL.md 与 MCP 的打包标准。
- roboclaws 姊妹项目:[roboharness](https://github.com/MiaoDX/roboharness)(公众号 001)、[robowbc](https://github.com/MiaoDX/robowbc);上层助手 [OpenClaw](https://github.com/openclaw/openclaw)。

<!-- 文末备注(commit 时可删):
撰写日期: 2026-06
配图清单(4 张 SVG 待出 + 截图待作者补):
  - blog-2026-06-stack.svg(镇文图)
  - blog-2026-06-skill-loop.svg
  - blog-2026-06-backend-swap.svg
  - blog-2026-06-minimal-map.svg
  - §0 / §4: household-cleanup 真实 report 截图(从 live reports 拿)
关联大纲: 2026-06-roboclaws-brain-for-robots.outline.md
预估字数: ~3200 字
-->
