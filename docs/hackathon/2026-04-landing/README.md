# Hackathon 2026-04 落地赛 / 提交材料（roboclaws）

Roboclaws 首次参加 hackathon。这个目录是这次落地赛的完整材料包。

## 文件清单

```text
SUBMISSION.zh-CN.md         主提交文档，飞书正文主稿
EVALUATION_GUIDE.zh-CN.md   评委 / 同事自助验证指南
assets/*.svg                飞书插图：总览、ROI、评分证据地图
```

## 这次材料主打什么

- 主线故事不再是“agent 能不能驱动机器人”，而是“工程师能不能放心让它自己跑完，再回来 review”
- 核心证据不是单个 demo，而是 **同一天、同一任务、5 次连续迭代**
- 文档结构已经按落地赛五维评分标准整理，评委可以直接按维度抓证据
- 飞书正文尽量使用列表和 code block，减少 markdown 表格粘贴失真

## 跟 roboharness 那次落地赛的差异（一句话版）

```text
roboharness：
  解的是 observability —— agent 看不见仿真画面，就等于不存在

roboclaws：
  解的是 iteration loop —— agent 跑完以后，如果没人能快速判断下一步，就等于没形成闭环

roboharness 的主证据：
  多视角截图、contract、approval report、可复核 evidence pack

roboclaws 的主证据：
  5 次同日 run、append-only logbook、trace.jsonl、真实 bug 被 harness 抓住
```

两个项目可以互相参照，但 wedge 完全不同。评委如果同时看两份提交，应该把它们理解成：

- `roboharness` 在解决 “看见”
- `roboclaws` 在解决 “怎么持续变好”

## 飞书插图建议

推荐插图顺序：

1. `assets/mode3-self-improvement-loop.svg`
2. `assets/run-roi-staircase.svg`
3. `assets/judge-score-evidence-map.svg`

可选补图：

4. `../../assets/readme-control-paths.png`
5. `../../assets/readme-photo-task.png`

## 飞书发送时机提示

如果直接用 GitHub raw 链接发飞书：

- `main` 链接适合合并之后长期保留
- 当前 branch 预览可以把链接里的 `main` 替换成 `docs/hackathon-2026-04-landing`

换句话说：

```text
合并前发预览：用 branch raw URL
合并后发正式版：切回 main raw URL
```

## 评委如果只看两个文件，先看哪两个

```text
1. SUBMISSION.zh-CN.md
   看主线叙事、评分维度、业务价值

2. EVALUATION_GUIDE.zh-CN.md
   看 5 分钟 / 15 分钟验证路径，确认这不是 PPT
```
