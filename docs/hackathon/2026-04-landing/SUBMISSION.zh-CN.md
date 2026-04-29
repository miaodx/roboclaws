# Roboclaws — AD Hackathon 2026 落地赛提交

> **让一个普通 Claude Code agent 通过 MCP 直接驾驶仿真机器人，并把"调试 navigator skill"这件事扔进闭环 harness 自我提升。**
> 工程师从盯仿真改成 review logbook。

---

## 一、先看核心数字

同一个任务（"给客厅每个沙发和椅子拍照片"）、**同一天**、5 次迭代：

| Run | 配置 | Tool calls | Targets | 结束方式 | Wall |
|---|---|---:|---:|---|---:|
| 001 | manual baseline | **127+** | 3/9 | 工程师按停 | ~25 min |
| 002 | harness 托管，无代码改动 | 55 | 3/9 | done (mis-classified) | 10 min |
| 003 | + `scene_objects` + skill 改写 | 65 | **9/9** | timeout | 10 min |
| 004 | + `goto` (有 y 坐标 bug) | 23 (aborted) | 翻车 | killed | ~5 min |
| 005 | goto 修复 | **37** | **9/9** | **agent 自动 done** | **3.8 min** |

**Run 001 → Run 005**：tool calls **−71%**、coverage **3×**、人从盯着到走开。

> **怎么做到的（一句话）**：把 Claude Code 当机器人 driver（Mode 3），然后用 `just harness::run <task>` 让 harness 自己 spawn agent / 收 trace / 写 logbook，工程师只看每次迭代后约 100 行的 `runs-log/<NNN>.md`。

5 次完整 run 的 logbook 公开可查：[`harness/runs-log/`](https://github.com/MiaoDX/roboclaws/tree/main/harness/runs-log)

![Roboclaws hero](https://raw.githubusercontent.com/MiaoDX/roboclaws/main/docs/assets/readme-hero.png)

---

## 二、故事演进：我们是怎么走到这里的

roboclaws 这个 repo 做了三轮方案，不是一次想到 Mode 3 + harness 的。每一轮都是"看起来更聪明 → 实际跑起来发现是中间商"。

### Phase 1 · 直接调 VLM API
最早让 GPT-4V / Claude 看截图直接决定下一步 action。VLM-as-driver 跑通了简单导航和 territory game。

**遇到的边界**：每一步是独立的 chat completion，agent 没有 process 这个概念——给它装"长期记忆"得自己拼工具链；调试时同样的 prompt 因为 chat 历史不同而行为不同；想让外部脚本"重复跑同一个 task 看看改动有没有效"，每次 baseline 都不一样。

### Phase 2 · OpenClaw Gateway（带 SOUL / skill 抽象）
切到 OpenClaw 这种 personal AI 框架做 agent runtime——能持久化 agent 状态、有 chat memory、能挂 skill / SOUL。`examples/openclaw_*.py` 就是这一波成果，跑通了 territory game、coverage game、photo task，[Railway appliance](https://github.com/MiaoDX/roboclaws/blob/main/docs/railway-deploy.md) 一键部署也是这一阶段。

**遇到的边界**：Gateway 是常驻服务、agent 状态在它进程里。想让外部 harness 起一个"干净的"agent 重复跑同一 task → 没办法，Gateway 的 SOUL 是 stateful 的、persistent 的、没法 clean spawn。"调试一个 skill"这件事仍然只能人盯。

### Phase 3 · Mode 3 + Self-improvement harness（现在）
直接让 Claude Code / Codex 通过 MCP 协议驾驶 AI2-THOR。Coding agent 是同质、一次性、可以在 tmux 里 spawn 然后 cleanup 的进程。**不是更"高级"的 agent，而是最适合放进闭环的形态。**

为什么这个区分重要：

| 维度 | Phase 1: VLM 直调 | Phase 2: Gateway | Phase 3: Mode 3 |
|---|---|---|---|
| Agent 可重复 spawn? | 每次 fresh，但状态分散 | 状态在 Gateway 内部 | tmux + claude CLI 一次性进程 |
| 外部 harness 可托管? | 难（无 process lifecycle）| 难（SOUL 状态污染）| **可以，已实现** |
| 一次 run 的 trace? | 散在 chat 历史 | 散在 Gateway log | `trace.jsonl` + `run_dir/` 标准化 |
| 调试反复跑同 task? | 每次条件不同 | 每次 SOUL 不同 | **每次 spawn 都干净** |

**不是说 VLM / Gateway 没用** —— `examples/` 里那些 mode 现在都还能跑、Railway 部署还在线。但要做"自我提升闭环"，**Mode 3 是唯一可行路径**。

---

## 三、5 次迭代干了什么（ROI 拆解）

### Run 001 — Manual baseline
工程师手动给 Claude Code 派任务（中文原句："麻烦给这个屋子里面的每个沙发和椅子拍个照片，确保视野中大部分都是对应的家具"），用当时 main 分支的 navigator skill。

5 个真实痛点（来自 trace.jsonl）：
1. **yaw 约定要从零摸**：前 30 步在测 yaw=0 是 +Z 还是 +X，skill 没写
2. **物体发现是被动的**：丢了 ~40 步在没椅子的区域瞎走，因为只能"走到看见才知道"
3. **L 形沙发把 agent 困在凹角里**：连续 9 次 blocked，没有 bbox 查询接口
4. **map PNG 只能看不能查**：障碍物 grid agent 程序读不到，等于装饰
5. **每张照片要 4 个 tool calls**：`MoveAhead → LookDown ×2 → observe`

结果：127+ calls 后只拍到 3/9 个目标（4 把餐椅根本没找到），工程师按停。

### Run 002 — Autonomous baseline（无代码改动）
把 Run 001 的 task 扔进 `harness::run`，**不改代码**，让 Claude Code 自己跑、自己 done。
- 55 calls / 3 of 9 / 自动 done（10 分钟）
- **harness 托管验证通过**，但目标覆盖率没变 —— 因为问题不在执行，在工具

### Run 003 — `scene_objects` + skill 改写
基于 Run 001 痛点 #2 + #5，新增 [`scene_objects(filter_types=...)` MCP tool](https://github.com/MiaoDX/roboclaws/commit/5729536) 让 agent 一次拿到所有 chair/sofa 的 position + bbox；SKILL.md 加 ["inventory-first protocol"](https://github.com/MiaoDX/roboclaws/commit/86a3a40)。
- 65 calls / **9/9 targets** / timeout @ 600s
- **覆盖率从 3/9 → 9/9（3×）**，但仍在 grid-step 移动，超时

### Run 004 — `goto` 加上了，但翻车
基于 Run 003 超时，加 [`goto(object_id, distance=1.0)` MCP tool](https://github.com/MiaoDX/roboclaws/commit/8cb1700)（用 AI2-THOR 的 Teleport 直接到目标附近）。
- **All 10 goto calls failed**：`InvalidOperationException: Collided with: Floor`
- Bug：传给 Teleport 的 y 坐标用了 target 的 bbox center y（~0.5m，椅子座面高度），agent 的 collision capsule 钻进地板，Unity 拒绝
- **关键**：FakeEngine 单元测试**没抓到**这个 bug —— FakeEngine 只 snap `_position` 不跑物理

> **harness 在 5 分钟内抓到了这个 bug。任何代码 review 都抓不到。**

修复：[commit `ed6b5fb`](https://github.com/MiaoDX/roboclaws/commit/ed6b5fb)，从 target.y 改成读 agent 当前 y。

### Run 005 — 干净结束
重跑修复后的 goto。
- **37 calls / 9-of-9 / 0 blocked moves / 3.8 分钟自动 done**
- agent 还自己学会了 `observe` vs `observe_archived` 的成本权衡：5:7 比例倾向便宜的 archived 版本，省 image token 占用 —— **这是 SKILL.md 改动让 agent 学会的，不是写死规则**

---

## 四、为什么这是 ROI 故事（评委关心的点）

### 之前 vs 现在

**之前**：调一次 navigator skill = 工程师本地起 AI2-THOR + 起 Gateway + 派任务 + 盯 trace + 试参数 + 重启 + 再盯。一次完整迭代成本：**~30 分钟工程师注意力**。

**现在**：`just harness::run photo-living-room` → tmux spawn fresh Claude Code → 自己跑 → 自己写 trace.jsonl + run_result.json → 自己 done → harness 把 metrics 写进 logbook。工程师只在结束后看 `runs-log/<NNN>.md`（约 100 行 markdown），决定接受 / fix / 改 skill 再跑。

### 时间换算

5 次迭代：
- 之前模式：5 × 30 min = **2.5 小时盯屏**
- 现在模式：5 × 3.8 min ≈ **20 分钟 review**（agent 跑的时候人在做别的事）

**~7× 工程师注意力回收**。这个倍数会随 task 难度增加而扩大 —— task 越难、单次 wall-clock 越长，"agent 跑的时候人能做别的事"的杠杆越大。

### 这不只是省时间：harness 抓到了 review 抓不到的 bug

Run 004 的 goto y 坐标 bug 是真实工程价值 —— FakeEngine 测试通过、code review 找不出，但 harness 在 5 分钟实际仿真中暴露了它。

这不是巧合：**带物理引擎的 bug 必须在物理引擎里发现**。harness 提供的就是这个低成本"在物理引擎里跑一遍"的渠道，相当于把"集成测试"从 CI 偶尔跑提升到了"每次改完 skill 立刻跑"。

---

## 五、Mode 3 让闭环成为可能（回扣 Phase 1/2）

`just harness::run <task>` 内部做的事：
1. tmux 起一个 fresh shell
2. `claude --dangerously-skip-permissions -p "$(cat tasks/<task>.txt)"` 启动 coding agent
3. agent 通过 MCP 连 AI2-THOR
4. trace.jsonl 写 metrics
5. agent 调 `done` 后，harness 杀 shell + 收 metrics

**Phase 1 (VLM 直调)** 做不到 step 1-2：没有"agent 进程"概念，每个 chat completion 是独立 API 调用。
**Phase 2 (OpenClaw Gateway)** 做不到 step 1：Gateway 是常驻服务，状态在它进程里，外部 spawn 不出"干净的 agent"——之前的对话历史 / SOUL state 会污染下一次 run。

Mode 3 因为 **coding agent ≡ 一次性 CLI 进程**（claude / codex CLI 都是这样设计的），天然适配 tmux spawn / cleanup 模型。**这是产品形态决定的能力，不是我们更聪明。**

---

## 六、工程化指标

- **代码量**：约 7,700 行核心 Python（30 个模块）+ 41 个 test 文件
- **测试**：mock-heavy 单测 + integration guards（refactor regression、photo-task smoke、MCP 契约）
- **CI**：GitHub Actions main badge 持续绿
- **部署**：4 modes 共享同一 `MultiAgentEngine` 核心 —— Direct VLM games / OpenClaw Gateway / Mode 3 直驾 / Railway appliance
- **Live demos**：[https://miaodx.com/roboclaws/](https://miaodx.com/roboclaws/) （CI 自动发布）
- **Skill artifact**：[`skills/ai2thor-navigator/SKILL.md`](https://github.com/MiaoDX/roboclaws/blob/main/skills/ai2thor-navigator/SKILL.md) —— 同一份文件被 Mode 2/3/4 共享，是 Mode 3 自我提升的"被改对象"
- **Harness logbook**：[`harness/PLAN.md`](https://github.com/MiaoDX/roboclaws/blob/main/harness/PLAN.md) + [`harness/runs-log/*.md`](https://github.com/MiaoDX/roboclaws/tree/main/harness/runs-log) —— 5 个 run 完整公开

![Roboclaws control paths](https://raw.githubusercontent.com/MiaoDX/roboclaws/main/docs/assets/readme-control-paths.png)

---

## 七、Roadmap

### 已锁定（下一轮 harness 要解的）
- [ ] **下一个 task class**：从 photo-living-room → 多房间 object inventory，或 grasp+place 操作。新 task = 新 friction = 新一轮 P-changes
- [ ] **`harness/scripts/summarize.py`**：跨 run 把 trace.jsonl 聚合成 metrics CSV，cross-run 比较从 bash glue 升级为标准 artifact
- [ ] **token / cost telemetry**：每次 `claude` 调用花真金白银，harness 现在没追算 budget。包一层日志

### Watch（不投入精力）
- Habitat / ManiSkill 接入：生态分散度高、wedge 不在那
- 多 coding agent 并行驱动多机器人：无成熟先例，先把单 agent 闭环打深

---

## 八、局限（坦诚）

1. **只跑过一个 task class**（photo-living-room）。现在 ROI 数字是 1 个 task 5 次迭代，跨 task 的泛化性还没验证 —— 下一步加第二个 task 才能说"这是 pattern not lucky"
2. **AI2-THOR 是合成场景**：物理 fidelity 比 Isaac Sim 低，对 manipulation 类 task 不够。短期不会切走，因为换平台会让 Mode 3 + harness 这条线先停下来
3. **Claude CLI 锁定**：harness 现在用 claude CLI 起 agent；Codex CLI 在适配中（[commit `dd16d73`](https://github.com/MiaoDX/roboclaws/commit/dd16d73) 已支持 `--yolo` 模式）但还没用它跑过完整 run

---

## 九、反馈渠道

- **GitHub Issues**：https://github.com/MiaoDX/roboclaws/issues
- **Live demos**：https://miaodx.com/roboclaws/
- **Logbook**（5 个 run 完整记录）：https://github.com/MiaoDX/roboclaws/tree/main/harness/runs-log
- **评委自助验证指南**：[`EVALUATION_GUIDE.zh-CN.md`](./EVALUATION_GUIDE.zh-CN.md)（5–15 分钟亲手跑一遍）

如果你帮我们找出这份提交里的硬伤 —— 比如某个数字算错了、Run X 的细节我们记反了、claim 跟 commit history 对不上 —— **这是项目最大的福利。**
