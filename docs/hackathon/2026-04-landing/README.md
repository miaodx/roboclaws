# Hackathon 2026-04 落地赛 / 提交材料 (roboclaws)

Roboclaws 首次参加 hackathon。这个 folder 是这次落地赛的全部提交材料。

## 文件清单

| 文件 | 用途 | 推荐打开方式 |
|------|------|-------------|
| [`SUBMISSION.zh-CN.md`](./SUBMISSION.zh-CN.md) | **主提交文档** | 飞书直接粘贴；图片走 GitHub raw 链接，飞书自动渲染 |
| [`EVALUATION_GUIDE.zh-CN.md`](./EVALUATION_GUIDE.zh-CN.md) | 评委 / 同事自助验证指南 | 给评委发链接，5–15 分钟亲手摸一遍 |

## 跟 roboharness 那次落地赛的差异（一句话版）

| 维度 | roboharness 落地赛 | roboclaws 落地赛（这次）|
|---|---|---|
| Wedge | 给 agent 装"眼睛"——看见仿真画面 | 让 coding agent 自己驾驶机器人 + 闭环自我提升 |
| 卖点 | 工程师从盯仿真 3 小时 → 3 分钟 review | 工程师从调 skill 30 分钟/次 → 看 logbook 4 分钟/次 |
| 核心 artifact | PNG + JSON snapshot per checkpoint | `runs-log/<NNN>.md` per iteration |
| 主体证据 | 多视角截图 + 多 demo report | 5 个 run 同一天迭代的 ROI 曲线 |

两个项目处理的是 harness engineering 的不同维度：roboharness 在解 **observability**（agent 看不见就等于不存在），roboclaws 在解 **iteration loop**（agent 跑完没人看也等于不存在）。同一批评委同一标准的语境下，两份提交可以互相参考但 wedge 故事完全独立。

## 飞书发送时机提示

**SUBMISSION 里的图片用 `https://raw.githubusercontent.com/MiaoDX/roboclaws/main/...` 链接** —— 这意味着：
- ✅ PR 合并到 main 之后再发飞书：图片正常渲染
- ❌ PR 还没合的时候发飞书：图片 404

如果合并前急着发预览，把链接里的 `main` 替换成 `docs/hackathon-2026-04-landing` 即可（branch 名）。
