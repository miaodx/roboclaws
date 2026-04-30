# 评委自助验证指南 — Roboclaws AD Hackathon 2026

> 这份文件是给评委 / 同事的自助验证路径。**不需要先看完整 SUBMISSION**，也能验证主要 claim。
> 时间预算：5 分钟看懂版 / 15 分钟亲手跑版。

---

## 先按五维评分标准快速定位

```text
需求匹配度（20）
  看什么：这是不是一个真实研发痛点，而不是比赛包装
  先看：SUBMISSION 里的“这不是再做一个机器人 demo” + docs/harness-self-improvement-loop.md

落地可行性（25）
  看什么：有没有清晰命令、真实产物、公开 report、稳定运行路径
  先看：just harness::run photo-living-room + trace.jsonl + runs-log

业务价值（25）
  看什么：有没有明确的 ROI / KPI / 风险下降，而不是只有技术新奇
  先看：Run 001 → 005 的指标变化，尤其是 Run 004 物理 bug

用户体验（15）
  看什么：工程师或评委是否能低成本发起一次 run、读懂结果、决定下一步
  先看：just harness::history + runs-log/<NNN>.md + live report

可复用性（15）
  看什么：是不是单个 task 的脚本，还是一层能复用的基础设施
  先看：ARCHITECTURE.md 四个 mode + skills/ai2thor-navigator/SKILL.md + harness/tasks/*.txt
```

---

## 5 分钟看懂版（不动手）

### 1. 先看 5 次同日迭代是不是都公开了

- [`harness/PLAN.md` Run index](https://github.com/MiaoDX/roboclaws/blob/main/harness/PLAN.md#run-index)
- [Run 001](https://github.com/MiaoDX/roboclaws/blob/main/harness/runs-log/001-photo-living-room.md)
- [Run 004](https://github.com/MiaoDX/roboclaws/blob/main/harness/runs-log/004-photo-living-room.md)
- [Run 005](https://github.com/MiaoDX/roboclaws/blob/main/harness/runs-log/005-photo-living-room.md)

你只需要确认三件事：

```text
Run 001  127+ calls / 3-of-9 / manual interrupt
Run 004  goto 上线后在真实物理里翻车
Run 005  37 calls / 9-of-9 / done in 3.8 min
```

如果这三件事都能对上，SUBMISSION 的主线基本成立。

### 2. 看 Run 004，验证“harness 抓到了测试抓不到的 bug”

- [Run 004 详情](https://github.com/MiaoDX/roboclaws/blob/main/harness/runs-log/004-photo-living-room.md)
- [`ed6b5fb` 修复 commit](https://github.com/MiaoDX/roboclaws/commit/ed6b5fb)

这里最值得看的不是 bug 本身，而是这条因果链：

```text
FakeEngine tests 通过
→ goto 在真实 AI2-THOR 中 10/10 失败
→ harness 发现“Collided with: Floor”
→ 修复 y 坐标后，Run 005 clean done
```

如果你只看一处来判断业务价值，这一处就够了。

### 3. 看这是不是一个真的“闭环”，而不只是会跑一次

- [`docs/harness-self-improvement-loop.md`](https://github.com/MiaoDX/roboclaws/blob/main/docs/harness-self-improvement-loop.md)
- [`harness/PLAN.md`](https://github.com/MiaoDX/roboclaws/blob/main/harness/PLAN.md)

重点不是“有个脚本跑 agent”，而是下面这几件事是否同时存在：

- 有 append-only run index
- 有每轮 hypothesis vs actual
- 有 active carry-forward
- 有 raw artifacts 和 curated logbook 的分层

这决定了它是不是一个真正可持续迭代的系统。

### 4. 看它是不是已经有公开落地形态

- 站点首页：https://miaodx.com/roboclaws/
- OpenClaw demo report：https://miaodx.github.io/roboclaws/openclaw/demo/report.html
- 报告对比页：https://miaodx.github.io/roboclaws/report_compare.html
- README 架构 / 模式总览：https://github.com/MiaoDX/roboclaws/blob/main/README.md

这几页的作用不是“给人看得热闹”，而是证明：

- 它已经有 live report
- 不是只剩 markdown 文档
- 不是只有作者口头能描述的结果

---

## 15 分钟亲手跑版

### 前置环境

- macOS / Linux（Windows 用 WSL）
- Python 3.10+
- `uv` 推荐，也可纯 pip
- `just`
- 一个可用的模型 provider key（Anthropic / OpenAI / Kimi 任一）

### 第 1 步：把 repo 跑起来

```bash
git clone https://github.com/MiaoDX/roboclaws.git
cd roboclaws
uv pip install -e ".[dev,openclaw]" || python -m pip install -e ".[dev,openclaw]"
```

### 第 2 步：先确认 harness 的操作面是可用的

```bash
just harness::list-tasks
just harness::history
```

你应该能看到 `photo-living-room` 以及已有的 run history。

### 第 3 步：重跑主要任务

```bash
just harness::run photo-living-room
```

跑完以后，重点检查这些产物：

```text
harness/runs/<NNN>/metrics.txt
harness/runs/<NNN>/trace.jsonl
harness/runs/<NNN>/server.log
harness/runs-log/<NNN>-photo-living-room.md
```

### 第 4 步：你该看到什么

如果当前 skill / tool surface 没有明显漂移，预期结果应接近 Run 005：

```text
大致 37±10 calls
9/9 targets
done
wall-clock 约 4 分钟量级
```

如果你复现出来明显更差，这不是坏事，而是一个真实 regression。对这个项目来说，这恰恰说明 harness 在发挥作用。

### 第 5 步：验证 Mode 3 不是单点脚本

任选一个再跑：

```bash
python examples/coding_agent_nav_server.py
just openclaw::run photo
python examples/territory_game.py --agents 3 --scene FloorPlan201
DEMO_PASSWORD=demo just appliance::run local
```

这一步主要在验证一个 claim：

> self-improvement harness 不是悬在空中的，它是建立在一个已经有 4 个 operating mode 的代码基座之上。

---

## Claim → 证据 快速对照

```text
"Run 001: 127+ calls / 3-of-9 / manual interrupt"
  → harness/runs-log/001-photo-living-room.md

"Run 005: 37 calls / 9-of-9 / done in 3.8 min"
  → harness/runs-log/005-photo-living-room.md

"Run 004 的 goto 物理 bug 是 harness 抓出来的"
  → harness/runs-log/004-photo-living-room.md
  → commit ed6b5fb

"这是 append-only 的 self-improvement loop"
  → docs/harness-self-improvement-loop.md
  → harness/PLAN.md

"4 modes 共用同一个 MultiAgentEngine"
  → ARCHITECTURE.md#four-operating-modes

"SKILL.md 是被持续优化的真实对象"
  → skills/ai2thor-navigator/SKILL.md
  → commit 86a3a40
```

---

## 如果你想再往深一点验证

- **加一个新 task**
  在 `harness/tasks/` 下新增一个 `<name>.txt`，跑 `just harness::run <name>`。
- **重看 `goto` 修复**
  `git show ed6b5fb -- roboclaws/openclaw/mcp_server.py`
- **比较 skill 改动前后**
  看 [`86a3a40`](https://github.com/MiaoDX/roboclaws/commit/86a3a40) 对 `SKILL.md` 的修改，再对照 Run 003 / 005。
- **确认 live report 是持续发布的**
  看 `README` 里的 GitHub Pages 报告入口，验证这些不是手工导出的一次性产物。

---

## 评分时建议特别留意的两个点

### 1. 不要只看 Run 005，要连 Run 004 一起看

只有 Run 005 很容易被理解成“挑了一个最好看的结果”。

Run 004 的价值在于证明：

- 系统会失败
- 失败能被结构化暴露
- 失败之后能更快进入下一轮

这比单纯的成功案例更能支撑高分。

### 2. 把“clean spawn”当成落地能力，而不是实现细节

如果没有 clean spawn：

- baseline 不稳定
- SOUL / memory 污染下一轮
- 对比没有可比性

对这个项目来说，Mode 3 的意义不只是“通过 MCP 驾驶机器人”，而是：

> **它第一次让 repeated, comparable, clean experiment 成为默认路径。**

---

## 反馈

- 任何“我重跑数字对不上 SUBMISSION 的”
- 任何“我重读 commit history 觉得 claim 站不住的”
- 任何“我认为某个高分判断证据不够的”

都欢迎开 issue：

https://github.com/MiaoDX/roboclaws/issues

对这个项目来说，最有价值的反馈从来不是“真厉害”，而是：

> **哪一条 claim 还不够可复核。**
