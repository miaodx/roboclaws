# Research Checkpoints

本目录是 `roboclaws` 生态调研的**月度快照存档**。每个 `YYYY-MM.md` 都是
一个 checkpoint 实例，永不覆盖，作为项目决策的历史档案。
这些 checkpoint 不是当前产品路线图；当前支持面以根 `README.md`、
`ARCHITECTURE.md` 和 `STATUS.md` 为准。

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

- [2026-04.md](2026-04.md)
- [2026-05.md](2026-05.md)

## 下次更新

**预定时间：2026-06-30**（按 mithaq vectors 卡片的月度节奏；触发临时调研的条件见
vectors 卡片 §Triggers for off-schedule research）。

下次应优先回答的问题见 [`2026-05.md` §6](2026-05.md#6-公开问题)。

## 关于信源分级

mithaq vectors 卡片用 3 档（whitelist / grey / blacklist，blacklist 仅可作 discovery 不可引用）。
**`2026-04.md` 用的是 4 档 A/B/C/D**（C 档是聚合站的 discovery 用途）——这是历史方案，保留以
便回读，无需追溯改写。**从 2026-05 起按 mithaq 3 档来**。两套的语义对照：

- A 档 ≈ mithaq whitelist
- B 档 ≈ mithaq grey
- C 档 + D 档 ≈ mithaq blacklist（C 是"可 discovery、不可引用数据"，D 是"完全忽略"——mithaq
  把这两者并入一个 blacklist 类别，靠 "use only as discovery surfaces, never as citation sources"
  的注释来区分）
