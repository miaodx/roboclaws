# 评委自助验证指南 — Roboclaws AD Hackathon 2026

> 这份文件是给评委 / 同事的自助验证路径。**不需要看完 SUBMISSION** 也能验主提交里的关键 claim。
> 时间预算：5 分钟看懂版 / 15 分钟亲手跑版。

---

## 5 分钟看懂版（不动手）

只需点开这几个 URL，所有数字 / artifact 都是 commit 进 main、CI 自动发布的：

### 1. 核心 ROI 数字直接看 logbook
- [`harness/PLAN.md` Run index](https://github.com/MiaoDX/roboclaws/blob/main/harness/PLAN.md#run-index) —— 5 个 run 一表对比，hypothesis vs actual 格式
- [Run 005 详情](https://github.com/MiaoDX/roboclaws/blob/main/harness/runs-log/005-photo-living-room.md) —— 完整指标 + 跨 run 总结表
- [Run 004 详情](https://github.com/MiaoDX/roboclaws/blob/main/harness/runs-log/004-photo-living-room.md) —— **goto y 坐标 bug 被 harness 抓到的现场**，"Why FakeEngine didn't catch this" 一节是关键

### 2. SUBMISSION 里引用的 commit 全都可点
- [`5729536` add scene_objects MCP tool](https://github.com/MiaoDX/roboclaws/commit/5729536) — Run 003 改动
- [`8cb1700` add goto for target-relative navigation](https://github.com/MiaoDX/roboclaws/commit/8cb1700) — Run 004 引入
- [`ed6b5fb` goto must teleport to AGENT y, not target bbox-center y](https://github.com/MiaoDX/roboclaws/commit/ed6b5fb) — Run 004 → 005 的修复
- [`373454c` self-improvement loop scaffold](https://github.com/MiaoDX/roboclaws/commit/373454c) — harness 本身的引入

### 3. Live demos
- 站点首页：[https://miaodx.com/roboclaws/](https://miaodx.com/roboclaws/) （CI 在每次 push main 后自动重发布）
- README 里所有图都是 GitHub raw 链接，点开即看

### 4. SKILL.md 是真实"被改对象"
- 当前版本：[`skills/ai2thor-navigator/SKILL.md`](https://github.com/MiaoDX/roboclaws/blob/main/skills/ai2thor-navigator/SKILL.md)
- "inventory-first protocol" 改动：[commit `86a3a40`](https://github.com/MiaoDX/roboclaws/commit/86a3a40) 之前 vs 之后
- 这份 markdown 同时被 OpenClaw Gateway / Mode 3 直驾 / Railway appliance 三种部署消费 —— 改一次三处生效

---

## 15 分钟亲手跑版

### 前置
- macOS / Linux （Windows 用 WSL）
- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) 推荐 / 也可纯 pip
- [`just`](https://github.com/casey/just) （任务编排）—— 不装也能直接跑底层脚本
- 一个 LLM provider key（Anthropic 或 OpenAI 任一）

### 跑通 Mode 1（最快验证 repo 没坏）

```bash
git clone https://github.com/MiaoDX/roboclaws.git
cd roboclaws
uv pip install -e ".[dev,openclaw]" || python -m pip install -e ".[dev,openclaw]"
just openclaw::run nav   # 或 examples/territory_game.py 直跑
```

打开浏览器看 Control UI，能看到 agent 在 AI2-THOR 场景里走 = 整套环境跑通。

### 验证 self-improvement harness（**主要落地证据**）

```bash
# 列出可跑的 task
just harness::list-tasks
# 看现有 5 个 run 的简表
just harness::history
# 重跑 photo-living-room（重现 Run 005 那次 3.8 分钟 9/9 的成绩）
just harness::run photo-living-room
```

跑完会在 `harness/runs/<NNN>/` 看到 raw 产出（metrics.txt / trace.jsonl / server.log）。

**预期**：在 SKILL.md / MCP tool surface 不变的情况下，重跑结果应该接近 Run 005（37±10 calls / 9-of-9 / 4 分钟内 done）。如果你的复现明显偏离，**这是真实可报告的 bug**，请开 issue。

### 验证 Run 004 那个 goto bug 真的存在过

```bash
git show ed6b5fb -- roboclaws/mcp/server.py
```

看 commit message 和 diff —— 修复就是把 y 坐标从 target.bbox.center.y 改成 agent.position.y。Run 004 的 [logbook](https://github.com/MiaoDX/roboclaws/blob/main/harness/runs-log/004-photo-living-room.md) 描述的就是这个 bug 在仿真里翻车的现场。

### 验证三种 mode 都还能跑（不只是 Mode 3）

| Mode | 一行验证 |
|---|---|
| Mode 1: Direct VLM | `python examples/territory_game.py` |
| Mode 2: OpenClaw Gateway | `just openclaw::run photo` |
| Mode 3: Coding agent 直驾 | `python examples/coding_agent_nav_server.py` 然后另一窗口 `claude --dangerously-skip-permissions -p "..."` |
| Mode 4: Railway appliance | `DEMO_PASSWORD=demo just appliance::run local` |

**SUBMISSION 里讲的"演进性"是真的，不是事后包装** —— 三种 mode 的代码都还在 `examples/` 和 `deploy/` 里活着。

---

## KPI Cheat Sheet（直接核对 SUBMISSION 数字）

| Claim in SUBMISSION | 怎么核对 |
|---|---|
| "Run 001: 127+ calls, 3-of-9, 工程师按停" | [`harness/runs-log/001-photo-living-room.md`](https://github.com/MiaoDX/roboclaws/blob/main/harness/runs-log/001-photo-living-room.md) Metrics 节 |
| "Run 005: 37 calls, 9/9, 3.8 min, 自动 done" | [`harness/runs-log/005-photo-living-room.md`](https://github.com/MiaoDX/roboclaws/blob/main/harness/runs-log/005-photo-living-room.md) Metrics 节 |
| "5 次迭代同一天" | git log: `git log --pretty=format:"%h %ad %s" --date=short -- harness/runs-log/` |
| "~7,700 行核心 Python / 30 modules" | `find roboclaws -name '*.py' \| xargs wc -l \| tail -1` |
| "41 个 test 文件" | `find tests -name '*.py' \| wc -l` |
| "4 modes 共享同一 MultiAgentEngine" | [`ARCHITECTURE.md`](https://github.com/MiaoDX/roboclaws/blob/main/ARCHITECTURE.md#four-operating-modes) |
| "skills/ai2thor-navigator/SKILL.md 是被改对象" | git history: `git log --oneline -- skills/ai2thor-navigator/SKILL.md` |

---

## 如果你想做更深的集成 / 验证

- **加一个新 task**：在 `harness/tasks/` 下新建 `<name>.txt`（一段中文 prompt 即可），跑 `just harness::run <name>` —— 这是验证"框架能扩展到新 task"最直接的路径
- **挂自己的 MCP tool**：在 `roboclaws/mcp/server.py` 加一个 tool，FakeEngine 测试在 `tests/test_mcp_server.py`，参考 `goto` 的 PR 看完整 flow
- **改 SKILL.md 看效果**：直接编辑 `skills/ai2thor-navigator/SKILL.md`，再 `harness::run` —— 跨两次 run 比较 metrics

---

## 反馈

- 任何"我重跑数字对不上 SUBMISSION 的"或者"我重读 commit history 觉得 claim 站不住的" —— 都欢迎开 [GitHub issue](https://github.com/MiaoDX/roboclaws/issues)，**这是评审环节我们最看重的反馈**
- 若有内部联系需要：见 SUBMISSION 末尾联系方式
