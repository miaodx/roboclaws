# Research Checkpoints

本目录是 `roboclaws` 生态调研的**月度快照存档**。每个 `YYYY-MM.md` 都是
一个 checkpoint 实例，永不覆盖，作为项目决策的历史档案。

**调研方向、信源白名单、隐藏假设、节奏与触发器**统一由
[`mithaq/vectors/roboclaws.md`](https://github.com/MiaoDX/mithaq/blob/main/vectors/roboclaws.md)
定义；本目录只放执行结果。新写一份 checkpoint 时按
[`mithaq` skill 的 Mode A](https://github.com/MiaoDX/mithaq/blob/main/skills/mithaq/SKILL.md#mode-a--run-a-checkpoint)
流程操作。

## 这与 `docs/research/` 的区别

| 维度 | `docs/research/` | `docs/research-checkpoints/` (本目录) |
|------|------------------|----------------------------------------|
| 形态 | 单点深度调研 | 周期性全景快照 |
| 触发 | 具体技术问题驱动 | 时间驱动（每月一次） |
| 语言 | English | 中文（内部决策导向） |
| 目标读者 | 项目内 + 外部协作者 | 项目内决策者 |
| 文件命名 | `NN-topic-slug.md` | `YYYY-MM.md` |
| 更新方式 | 一次写完，状态字段标 ongoing | 永不覆盖，每月新文件 |

两者互补：单点 research 文档处理"我们要不要做 X"这种具体问题，checkpoint
处理"现在生态长什么样、我们的判断是否需要更新"这种全景问题。

## 索引

| 期 | 文件 | 核心结论 / 主要变化 |
|----|------|--------------------|
| 2026-04 | [2026-04.md](2026-04.md) | 初次发布。建立 4 视角并列分类法，整理 44 个 OpenClaw 严格变体 + 30 个相邻项目，给出 Phase-1/2/3 取舍建议 |
| 2026-05 | [2026-05.md](2026-05.md) | 首次按 mithaq vectors 卡片做的增量 checkpoint。三条 §Triggers 触发但无一要求路线图重构。H1/H2/H3/H7 在外部证据下强化（Opus 4.7 视觉跃迁、MolmoSpaces 4 周零多智能体信号、SKILL.md 标准化加强、三家旗舰齐升级）；H4 正向（OpenClaw LTS + Managed Agents 多 agent 编排 SDK 化）；H8 维持但升级重点观察（CooperBench 给出 30% 量化反证，两轴最近邻到位） |

## 下次更新

**预定时间：2026-06-30**（按 mithaq vectors 卡片的月度节奏；触发临时调研的条件见
vectors 卡片 §Triggers for off-schedule research）。

下次应优先回答的 7 个公开问题见 [`2026-05.md` §6](2026-05.md#6-公开问题)
（包括 AAMAS 2026 论文集扫描、MolmoSpaces 第二个 4 周窗口、Kimi K3 落地、
OpenClaw LTS、Managed Agents 多 agent 编排上限、MCP next spec、substrate 动态）。

## 关于信源分级

mithaq vectors 卡片用 3 档（whitelist / grey / blacklist，blacklist 仅可作 discovery 不可引用）。
**`2026-04.md` 用的是 4 档 A/B/C/D**（C 档是聚合站的 discovery 用途）——这是历史方案，保留以
便回读，无需追溯改写。**从 2026-05 起按 mithaq 3 档来**。两套的语义对照：

- A 档 ≈ mithaq whitelist
- B 档 ≈ mithaq grey
- C 档 + D 档 ≈ mithaq blacklist（C 是"可 discovery、不可引用数据"，D 是"完全忽略"——mithaq
  把这两者并入一个 blacklist 类别，靠 "use only as discovery surfaces, never as citation sources"
  的注释来区分）
