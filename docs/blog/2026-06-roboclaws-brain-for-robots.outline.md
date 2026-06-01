# 大纲:roboclaws 给机器人以大脑(改版,2026-06)

> Planning artifact —— 与正文一同 commit,供 review。
> 主轴:**skills-first + 一个干净的薄抽象 + coding agent 当现成 harness**。
> 主线任务:`household-cleanup`(真实开放型任务);`photo` 降为 §3 讲分层的教具。
> 邀请重心 = **sim(尤其 MolmoSpaces)**:快、零依赖、场景够大;真机 G2 仅作"这条路通"的脚注。
> repo 全开源,demo / HTML report / SKILL.md / profile 都可公开指向。

---

## Thesis

大家默认"用大模型开机器人"是件简单事,但 GitHub 上没有一个**干净、直观**的做法。我们从第一性原理找到一个**薄到一眼能抄**的抽象:把机器人能力薄薄地提给 MCP,在上面叠几层 skill,让现成 coding agent 从顶上进来——**仿真能跑、真机也能跑**。我们没发明新东西,只是把它拼干净了,然后请你来抄、扩到你自己的机器人。

差异化 = **taste + integration**(不喊首创,喊"没看到别人这么做,所以做出来给大家看")。

写作总纪律:**show, don't claim**——展示简单(亮命令、亮工具清单、亮真实跑通),不自夸"优雅/简单"。

---

## 脊梁(6 拍)

### §0 楔子(~250 字)
一个乱房间,一句"把它收拾干净"的开放指令,coding agent 通过 MCP 自己跑通,结束时把一条经验**写回了 SKILL.md**。贴真实指令 + 结果,不解释——钩子就是"开放式任务 + 会自更新的说明书"。

### §1 but how?(~350 字)
"能让大模型驱动机器人"早不稀奇,难的是**真正完成开放式任务**,而且**没人给出干净的公开做法**。镜头挂到 Karpathy「skill issue」:能力够强之后,瓶颈转移到怎么定义任务、给上下文、造工具、跑 loop、评估、维护可复用行为。预告:我们的答案是一个干净抽象,下面先讲怎么试出来的。

### §2 我们试出来的路(~600 字)
一条逼近正确抽象的路,压成三步:
- **VLM 直驱** —— 证明"AI 能让机器人动",但只是 demo,策略写死在 Python 里,改一条规则要重启脚本。
- **OpenClaw** —— 需要 harness 才能完成真任务,我们选了当时**抽象层级最高、可用 skills 扩展、理论真能跑**的 OpenClaw(**项目名 RoboClaws 由来**)。
- **coding agent** —— 想要更快迭代、想让 loop 真正闭环,走到 Claude Code / Codex 反而更顺:它能编辑文件、调工具、反思、把 skill/MCP 自己迭代(**git history 可见**)。
- 收尾一句:做完**回接 OpenClaw 也能跑**——所以不是抛弃,是抽象做好后白拿交互层。**命名反差主动点破一句**(名字留着,引擎换了)。

### §3 那个干净抽象(自底向上)(~750 字,本文核心)
"从底往上**搭**,但让 agent 从顶上**进**。"逐层讲:
- **薄语义 MCP** —— `observe / move / turn / pick / place / open / close / done`,刻意小、刻意语义化,**绝不做 `cleanup_room()` 这种把整任务藏进一个调用的黑盒**。
- **通用能力 + capability profile** —— 导航 / 地图 / 定位等;`household_world_v1` 等是可复用"能力环境",skill 靠**要求**组合,不靠抄。
- **skill 多层 + 扩展** —— agent skill → trace-preserving routine → composite action。**借 photo 当一眼看懂的教具**:`capture-object-photo` 内部是 `locate→navigate→orient→observe→verify` 的 composite action,但**不该**升进 MCP;什么时候才升 = 晋升规则(多个 skill 都要、IO 稳定、可追溯、只用公开信息、属于能力边界),默认不升。
- **顶层 coding agent** —— 从开放式目标进来,选/造 skill,harness loop 让它自迭代。
- 亮 `just task::run <task> <driver>` 一行命令,让读者自己得出"就这?"。
- 两条暗线贯穿:**公私评估真相分离**(privileged 工具如 `scene_objects`/`goto` 被显式标记"非真机能力";private scoring/隐藏 mess 集永不进公共 metadata)+ **reviewable HTML report**(frames/maps/traces/scores,而非埋在终端)。

### §4 抽象立住后白拿到的(~650 字)
回到 cleanup 主线,讲这套抽象一旦立住、几乎免费拿到的东西。**内部权重:sim/MolmoSpaces 是主角,真机只一句脚注。**
- **(a) 会自更新的 SKILL.md** —— agent 从 trace 看出自己卡哪、改 SKILL.md、下次受益。**点到为止 + 举一个例子**;实数(127→37、5 次 iteration)留 004。
- **(b) 一份 skill 横跨多 backend,落点在 sim(本节主角)** —— 同一摞,backend 在底下换:AI2-THOR / Isaac(写成 **in progress,本地 GPU 已打通单物体 cleanup parity**,不写"已支持")/ **MolmoSpaces**。重点抬 MolmoSpaces:**够大、够真,跑 cleanup 这种开放型任务绰绰有余**,而且**快、零依赖**——这才是我们想让大家上手的地方。**minimal map**:robot 自己从 occupancy 建 `runtime_metric_map`,而不是被喂 authored 真相——开放型任务本该如此。
- **(c) 真机 AGIbot G2 —— 缩成一句脚注** —— "同一摞抽象换个 backend variant 也接到了真机(G2,导航 pilot 通、抓取还 blocked),证明 sim 调好的东西真能往真机迁。"as-is 诚实,但**不展开、不强调**,马上把读者拉回 sim。

### §5 更大的赌注 + 来抄(~400 字)
- 骑现成 coding agent 做扩展,可能是接下来很长一段时间**非常值得做**的方向——**不止机器人**,所有自定义智能开发都能在它上面做。
- 不急着从头造框架:跑得够好了再考虑**下沉**(到 Anthropic / OpenAI 的 Agent SDK)+ 补自己的东西(语音控制等);或者抽象做得足够好,**直接交给 OpenClaw,所有用户交互白拿**。
- 多 agent 一笔带过(还在赌,不是本文重点)。
- **高潮 = 你现在就能在 sim(尤其 MolmoSpaces)里干净复刻、零依赖上手,coding agent 的快速迭代会让你上瘾——来抄,扩到你自己的任务和机器人。** 邀请重心是 sim,不是真机。邀请 + 主仓链接收束。

---

## 写作约定

- 中英混排,保持项目内一贯风格。
- 引用稀疏:正文项目名级 + 一句话;文末放少量关键引用(写正文时再定具体几条,不预设大分类表)。
- 保留一句诚实姿态:"MCP 控机器人 2026 已不 novel(FAEA / CaP-X / Project Fetch),我们赌的是这套**集成与品味**"。
- 全开源:show-don't-claim 可直接指向真实可点的东西——`just task::run household-cleanup ...`、公开 HTML report、SKILL.md 本体、profile 定义。"就这?"由读者自己点进去看到,而非作者描述。
- 配图:4 张 SVG 由我重画——**stack(镇文图)/ skill-loop / backend-swap(并存非线性)/ minimal-map**;正文阶段一起出。真实跑通的命令/report 截图留 placeholder 给作者补。

---

## 待作者复核(发表前)

1. show-don't-claim 要亮的具体命令/工具清单是否可公开(privileged 工具是否出现在示例)。
2. 真机 G2 段落措辞对齐 status 最新 as-of。
3. Claude Code / Codex / Opus / GPT 版本号发表时复核,避免写死过期。
