# 公众号文章大纲: roboclaws 给机器人以大脑

> Planning artifact —— 这是为 `2026-05-roboclaws-brain-for-robots.md` 起草过程中沉淀下来的大纲与决策记录,与正文一同 commit,方便后续 review。

## 工作内部代号

`roboclaws: 给机器人以大脑`

## 最终标题

**roboclaws:给机器人以大脑——从 VLM 直驱到一份会自己更新的 SKILL.md**

(候选标题对比详见 commit 历史中的讨论。)

## Thesis(经过两轮调研后修订的版本)

把 Codex / Claude Code 这类商业 coding agent 当 in-the-loop robot controller 这件事,2026 年已经不再是冷门——FAEA、CaP-X、Project Fetch 把它推到了主流视野。**真正未被填满的具体形态**是:

- AI2-THOR(室内房间级语义任务)
- + MCP(开放协议 + 主流 client 都能接)
- + 主流 coding agent 直驱(不是裸 API 也不是自造 framework)
- + SKILL.md 自演化(harness/ 循环把策略经验固化进 markdown)
- + 多 agent(领地控制 / 协同覆盖)

截至 2026-04-28,**多 coding-agent 同时驱动多个仿真机器人**这条组合在公开记录里没有第二个样本(checkpoint §1 第 6 条)。这是 roboclaws 真正的差异化主张。

## 叙事结构 (递进式 7 节)

| § | 标题 | 论点 | 字数 |
|---|------|------|------|
| 0 | 楔子 | 一段真实 photo task 跑通的体验,引出 SKILL.md 自演化的钩子 | ~250 |
| 1 | 项目定位 | 是什么、名称由来、4 mode 总览 | ~280 |
| 2 | Mode 1 — VLM 直驱 game | 起手式,最快迭代,但策略写死在 Python 里 | ~380 |
| 3 | Mode 2 — OpenClaw Gateway | 引入 OpenClaw(顺势介绍这个仍火的框架),解决"对着 episode 说话",但撞到 skill 迭代慢 + 阵营变化 | ~640 |
| 4 | Mode 3 — Coding agent 自己进仿真器 | harness engineering 主线给的视角,把仿真器 wrap 成 MCP 让 coding agent 自驱;数字硬碰硬(127→37 calls);诚实姿态:MCP 不 novel,多 agent 应用才 novel | ~660 |
| 5 | harness/ 自我改进循环 + meta-optimization | SKILL.md 变成会自己更新的可执行说明书;同一份被 Mode 2/3/4 共享 → Mode 3 优化反哺 OpenClaw | ~640 |
| 6 | 平台迁移 + 真机(合并) | AI2-THOR → MolmoSpaces → 真机,MCP+SKILL.md 抽象层不变 | ~620 |
| 7 | 收束 | "多 coding-agent + sim 没有公开案例,我们在走" + 邀请 | ~250 |

**预估总字数**:~3700 字(公众号长文区间,前两篇 ~3000 字)

## 关键设计决策

### 为什么 §6 §7 合并

最初版大纲 §6 是平台迁移,§7 是真机 future work。两者本质都在讲"抽象层不变 + backend 可换"这一件事——平台之间换 sim 是一次,sim 到真机是又一次。合并后叙事更紧、避免读者两次重复"MCP+SKILL.md 让迁移变便宜"这个论点。

### OpenClaw 的处理策略

§3 用作"引入框架 + 撞墙"的承重墙。具体处理:
- 客观介绍(36 万 stars、SOUL/Skills/MCP/Control UI)——它仍然火,值得读者了解
- 诚实点出 2026 这一年发生的事(创始人加入 OpenAI、CVE-2026-25253、阵营变化)——一句话带过,不展开
- 不说"OpenClaw 失败了我们换",改说"我们重新想清楚了 OpenClaw 该处在什么位置"——这符合 checkpoint §6.1 实际判断

### FAEA / CaP-X / Project Fetch 的引用强度

正文只在 §4 用一句话点过去(对照"MCP 控机器人不 novel"的诚实姿态),详细引用全部下放参考文献。这是作者明确要求的:正文引用少,文末参考多。

### 真正的 novelty punchline 放哪

放 §7 收束。"多 coding-agent + sim 这条组合截至 2026-04-28 没有公开案例"是 checkpoint §1 第 6 条的原话,作为收尾比作为开场更稳——开场说"这是新地带"容易显大,放收束反而让前面的工程描述自己证明这件事是 substantial。

### 配图策略

3 张原创 SVG,放在 `docs/assets/blog-2026-05-*.svg`:

1. **modes.svg** — 四个 mode 共享 MultiAgentEngine 内核 + 一份 SKILL.md。Mode 3 高亮 + harness/ 旁注。展示 Mode 1 直驱 vs Mode 2/3/4 走 MCP 的差异。
2. **skill-loop.svg** — harness 启动 → Claude Code 跑任务 → trace.jsonl 揭示失败 → agent 改 SKILL.md → 同一份 SKILL.md 反哺 Mode 2 / Mode 4。
3. **migration.svg** — 顶层 SKILL.md + MCP 契约不变,底层 backend 从 AI2-THOR → MolmoSpaces → 真机(LeRobot/ros-mcp/Reachy)。

可复用的现有素材:

- `docs/assets/readme-hero.png` — 项目 hero(可放 §1)
- `docs/assets/readme-photo-task.png` — photo task 真实输出(可放 §0 或 §4)
- `docs/preview/territory.gif` / `coverage.gif` — 多 agent 跑动 demo(可放 §1 或 §2)

需要作者后期补充的素材(已在文中留 placeholder 注释):

- 一段 SKILL.md 真实演化 diff(§5)
- Run 005 trace.jsonl 节选截图(§4 或 §5)
- Photo task 9 张拍出来的 chair/sofa 缩略图阵列(§0 或 §4 hero)

## 参考文献编排

正文引用风格:**项目名级 + 一句话定位**,不展开 URL 和 arXiv 编号。

参考文献区分组:

- A. Harness Engineering 主线(Hashimoto / Anthropic / OpenAI / Cursor)
- B. Coding Agent as Robot Controller(FAEA / CaP-X / Project Fetch)
- C. MCP × Robotics(MCP / ros-mcp-server / isaac-sim-mcp / Reachy-Mini MCP / robot_MCP)
- D. VLA / 端到端(OpenVLA / π₀.₅ / GR00T N1.7 / Gemini Robotics ER)
- E. 仿真平台(AI2-THOR / MolmoSpaces / ManiSkill3 / Isaac Lab)
- F. Sim-to-Real(LeRobot / MolmoBot)
- G. roboclaws 自身相关项目

## 与前两篇公众号的关系

公众号 001(roboharness):让 robotics agent 看见仿真画面 — 视觉反馈
公众号 002(routines):让 cloud agent 自主跑、自己解 issue — 工作流自动化
公众号 003(本篇):让 coding agent 进仿真器 + 优化 SKILL.md — controller × meta-optimization

三篇连成一条 narrative:**让 agent 看见 → 让 agent 自主跑 → 让 agent 进仿真做事 + 改自己的说明书**。

下一篇(004)会聚焦 §5 这一节里只点了一笔的 self-improvement loop 本身,把 5 次 iteration 的实数(127→37 calls)展开讲。

## 已知未填的坑(留给后续 issue)

1. SKILL.md 演化 diff 的具体 3-5 行需要从 git log 里挑(harness 005 commits 时间窗内)
2. 文章发表时需要复核 Claude Code / Codex / Cursor 的最新版本号
3. MolmoSpaces 迁移 spike 完成后,§6 的 MolmoSpaces 段落可以从"即将"改成"已完成 spike,数据如下"
