# Agibot G2 导航与感知验证手册

这份手册用于 Agibot G2 的导航 + 感知验证。它不是“物理 cleanup 成功”
证明：当前第一验收目标应是 `semantic-map-build`，也就是让机器人在真实或
准真实地图上下文里完成导航、观察、语义地图构建和报告产出。物理拾取、放置、
开关柜门等操作仍然保持 `blocked_capability`。

## 任务选择建议

当前不要把 `household-cleanup` 当作 Agibot 真机主验收任务。原因很直接：
cleanup 的关键价值在 manipulation，而现在 manipulation 工具本来就应该被
block。用它做默认真机验收会让报告看起来像“任务失败”，但实际只是安全边界
正确生效。

推荐的任务分层是：

- **当前主任务：`semantic-map-build`**
  验证真实流程最合适。它覆盖地图上下文、waypoint、导航、观察、相机证据、
  visual grounding、Runtime Metric Map、Actionable Semantic Map Snapshot 和
  报告，不依赖 manipulation 成功。
- **当前对外 demo 形态：map evidence refresh / 开放巡检**
  不要把它说成“重新建一遍语义地图”。更好的说法是：机器人已经有一份
  语义地图，现在让 agent 基于已有地图自主选择几个最值得复核的 anchor 或
  waypoint，过去观察、记录证据、解释选择和跳过原因。工程入口仍然先复用
  `semantic-map-build`，因为它已经有导航、观察、runtime map 和报告链路。
- **辅助合约任务：`household-cleanup` dry-run / rehearsal**
  用来确认 cleanup 任务会通过 `runtime_map_prior=...` 消费同一个语义地图产物，
  并且 manipulation 被清楚地标成 blocked。不要把它描述成物理 cleanup 成功。
- **未来更自然的任务：拍照 / photo capture**
  “去给某个物体拍照”确实更适合早期真机验证，因为它只需要导航、观察、
  取景和报告，不需要抓取或放置。当前仓库里的 `photo-chairs` 主要接在
  AI2-THOR/OpenClaw/coding-agent 路线上，还没有作为 `agibot_gdk` 公共任务
  路由打通。建议后续新增一个 Agibot 版 photo/capture task，再把它作为
  `semantic-map-build` 之后的第二个真机验收任务。

因此，当前验收顺序建议是：

```text
离线 navigation_memory 转 snapshot
  -> synthetic cleanup 消费 snapshot
  -> Agibot-shaped sim map-evidence-refresh prompt rehearsal
  -> Agibot semantic-map-build dry-run
  -> Agibot semantic-map-build / map-evidence-refresh 真机 movement run
  -> 后续新增 Agibot photo/capture task
  -> 最后才考虑 physical cleanup
```

更适合对外展示的任务形态，不是固定脚本式的“先去吧台，再去冰箱，再去沙发”，
而是一个带目标和约束的开放式巡检任务。例如：

```text
请在当前地图里自主选择 3 个值得复核的家庭区域或固定物体，
依次导航过去观察并拍摄证据；
优先选择语义地图中 actionability=actionable 但还缺少当前画面证据的 anchor；
如果遇到 costmap_disagrees、needs_review 或无法观察清楚的目标，
请跳过并记录原因；
最后回到起点附近，输出你去了哪里、为什么选择这些点、每个点看到什么。
```

这个任务比纯长路线更好，因为它让机器人展示三件事：

- 使用 **Actionable Semantic Map Snapshot** 和 **Public Semantic Anchor** 做目标选择；
- 通过 **Metric Map** / waypoint 导航和 `observe` 采集当前证据；
- 在报告里解释选择、跳过和失败原因，而不是只执行一串人工写死的 waypoint。

实现上，它可以先落成 `semantic-map-build` 的一个 policy/profile，名字可以是
`inspection-tour` 或 `map-evidence-refresh`；等 Agibot 版 photo/capture task 打通后，
再把最终证据从普通 observation 升级为带标签的 photo artifact。

短期命名建议使用 `map_evidence_refresh`。它表达的是“基于已有地图刷新证据”，
而不是“从零建图”。在代码还没有新增 public task 前，命令仍然走
`semantic-map-build`。

## 前置条件

- 在可信本地工作站或 Agibot GDK 机器上运行，不要在 hosted CI 里跑真机流程。
- 现场操作员负责机器人急停、人工停止和工作区安全边界。
- 机器人已经在 G02 Pad 中选中目标地图并完成重定位。
- 当前 checkout 使用仓库本地 `.venv/`：

```bash
uv sync --extra dev
```

- 如果要跑 live Codex 或 Claude 对比，需要按 [local-runtime.md](local-runtime.md)
  配置仓库本地 `.env`。不要把 key 写进日志、报告或文档。
- 运行 OpenClaw 或 coding-agent 工作流前，先检查当前网络：

```bash
just dev::network-status
```

如果显示 work network，OpenClaw 被禁止。Codex 只允许通过仓库本地 `.env`
里的 `XM_LLM_API_KEY` 路由，或显式 `CODEX_BASE_URL` + `CODEX_API_KEY` 路由。

## 无真机可跑的验证路径

没有 G2 时，也可以先做一组有价值的验证。它们能证明 map artifact 合约、
任务接线、报告形状和 dry-run 安全边界；它们不能证明物理导航、真实相机采集、
PNC 可达性、真实画面 visual grounding 或 manipulation。

### 离线地图产物转换

把已 checkout 或 vendor 里的 Agibot map folder 转换成
`actionable_semantic_map_snapshot_v1`。这个产物和在线 `semantic-map-build`
从 `runtime_metric_map_v1` 包出来的下游合约一致：

```bash
python skills/actionable-semantic-map-conversion/scripts/convert_navigation_memory.py \
  vendors/agibot_sdk/artifacts/maps/robot_map_12 \
  --output output/maps/robot_map_12/actionable_semantic_map_snapshot.json \
  --summary-json output/maps/robot_map_12/materialized_targets.json
```

如果当前 checkout 没有完整 vendor submodule，可以用仓库里的 fixture 做合约验证：

```bash
python skills/actionable-semantic-map-conversion/scripts/convert_navigation_memory.py \
  tests/fixtures/actionable_semantic_map/robot_map_12 \
  --output output/maps/robot_map_12/actionable_semantic_map_snapshot.json \
  --summary-json output/maps/robot_map_12/materialized_targets.json
```

在把 snapshot 交给下游任务前，先检查 `materialized_targets.json`：

- `sink`、`table`、`sofa` 等 actionable fixture anchor 应该出现在
  `actionable_fixture_ids`；
- bottle 这类可移动物体必须保持为 observed-object prior，状态是
  `needs_confirm`，不能变成静态 fixture candidate；
- `costmap_disagrees`、`needs_review`、`observe_only`、`projected` 等不确定状态
  必须显式保留，不能被静默提升成 actionable target。

然后运行离线合约测试：

```bash
./scripts/dev/run_pytest_standalone.sh \
  tests/contract/maps/test_actionable_semantic_map_snapshot.py -q
```

如果要跑更完整的无真机回归集：

```bash
./scripts/dev/run_pytest_standalone.sh \
  tests/contract/maps/test_actionable_semantic_map_snapshot.py \
  tests/contract/maps/test_nav2_map_bundle_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/skills/test_skill_manifests.py -q
```

### Synthetic Consumer Proof

把转换出的 snapshot 作为 `runtime_map_prior` 交给 synthetic cleanup。这个检查证明
cleanup 通过 canonical artifact path 消费语义地图，而不是新增一个 Agibot 专用
`navigation_memory.json` 分支：

```bash
just task::run household-cleanup direct world-labels \
  seed=7 \
  runtime_map_prior=output/maps/robot_map_12/actionable_semantic_map_snapshot.json \
  output_dir=output/checks/agibot-snapshot-prior-cleanup
```

检查 `output/checks/agibot-snapshot-prior-cleanup/**/run_result.json` 和
`report.html`，期望看到：

- `runtime_map_prior.loaded=true`；
- 可移动 prior row 仍然是 `freshness=prior`、`state=prior`、
  `actionability=needs_confirm`；
- prior 里的 public semantic anchor 在 `actionability=actionable` 时，可以物化为
  public navigation 或 receptacle target；
- Agent View 里没有 private cleanup truth。

这仍然是 synthetic run。它不验证 G2 localization、PNC navigation、真实相机图像
或物体操作。

### Sim-first 开放巡检 Prompt Rehearsal

可以先在 Agibot-shaped MolmoSpaces sim 里跑相同的开放巡检 prompt。这个步骤适合
快速检查：

- `prompt=` 会进入任务产物和报告；
- `semantic-map-build` 的 report shape 仍然正确；
- minimal map、runtime semantic anchors、simulated observation 和 blocked
  manipulation 边界没有被破坏。

它不能证明 Codex 在真实 G2 上真的做出了开放式选择，也不能证明 G2 PNC、真实
head camera、真实 visual grounding 或 manipulation。它是 prompt/report 形状
rehearsal。

最快的 fixture 版本：

```bash
OPEN_EVIDENCE_REFRESH_PROMPT='基于当前已有语义地图，自主选择 3 个最值得复核的 public semantic anchor 或 inspection waypoint，依次导航过去观察。优先选择 actionability=actionable、needs_review、costmap_disagrees 或缺少当前画面证据的目标；如果目标不可达或证据不清楚，跳过并记录原因。最后调用 done，总结你选择了哪里、为什么选择、每个点看到什么、哪些点被跳过。'

just task::run semantic-map-build direct camera-labels \
  backend=agibot_molmospaces_sim \
  runtime=fixture \
  rehearsal_mode=contract \
  prompt="$OPEN_EVIDENCE_REFRESH_PROMPT" \
  output_dir=output/agibot/molmospaces-sim/map-evidence-refresh
```

如果本地 MolmoSpaces runtime 已安装，并且想要更接近真实相机证据的模拟图像：

```bash
just task::run semantic-map-build direct camera-labels \
  backend=agibot_molmospaces_sim \
  runtime=molmospaces-subprocess \
  visual_grounding=grounding-dino \
  prompt="$OPEN_EVIDENCE_REFRESH_PROMPT" \
  output_dir=output/agibot/molmospaces-sim/map-evidence-refresh-camera
```

检查：

- `report.html` 的 Overview 页里有 **Map Evidence Refresh Summary**；
- `output/agibot/molmospaces-sim/map-evidence-refresh/**/run_result.json`
  里的 `task_prompt` 等于上面的开放巡检 prompt；
- `runtime/runtime_export.json` 也记录同一个 `task_prompt`；
- `runtime_metric_map.json` 存在，并且 `minimal_map_mode=true`、
  `source_map_mutated=false`；
- `report.html` 显示这是 simulated / physical_robot=false，不要把它升级成
  hardware evidence。

`Map Evidence Refresh Summary` 的读法：

- `Agent-driven=no` 表示这只是 direct sim rehearsal，不是 Codex 自主选择目标；
- `Public anchors`、`Visited anchors`、`Observed handles` 和 `Raw observations`
  说明这次 sim 产生了多少地图/观察证据；
- 目标表展示本次可复核的 map evidence target、waypoint 和 observation id；
- 如果 summary 写着 “not autonomous target choice”，就只能把它当作
  prompt/report 可读性 proof，不能作为开放式机器人 demo。

如果要测试“真正由 Codex 读 prompt 后选择目标”，仍然要走下面的
`semantic-map-build codex backend=agibot_gdk` 路线。当前 Agibot-shaped sim route
是 direct rehearsal，不启动 coding agent。

### Agibot Dry-Run Rehearsal

如果手上已有 `agibot_map_context.completed.json`，但当前没有机器人 session，
可以先用 movement disabled 的 public Agibot 路线跑 dry-run：

```bash
just task::run semantic-map-build direct camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  waypoint_id=<candidate_waypoint_id> \
  output_dir=output/agibot/semantic-map-build-dry-run
```

报告应该展示 blocked/dry-run movement evidence、public policy decisions、
skipped waypoint reasoning 和 blocked manipulation。缺少 live camera evidence 时，
应把它理解为 dry-run 边界，而不是 detector 失败。

Codex 控制路线使用 Docker-backed task surface：

```bash
just task::run semantic-map-build codex camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  output_dir=output/agibot/semantic-map-build-codex-dry-run \
  policy=map_evidence_refresh \
  prompt="$OPEN_EVIDENCE_REFRESH_PROMPT" \
  visual_grounding=grounding-dino \
  visual_grounding_timeout_s=20
```

只有在真实机器人可用、operator gate 已记录、live camera artifact 存在且
`real_movement_enabled=true` 的同一路线重跑通过后，才能把 dry-run 产物升级为
hardware evidence。

## 采集地图上下文

在 Agibot GDK 机器上采集 map、pose 和 camera evidence：

```bash
.venv/bin/python scripts/agibot/capture_map_context_views.py \
  --output-dir output/agibot/map-context/<stamp> \
  --cameras head_color
```

minimal-map 路径下，完成后的 context 必须包含 safety bounds，以及生成或采样得到
的 free-space exploration candidates。它不能依赖手写 room、fixture 或 semantic
waypoint。

任何 real-movement run 前，都要在 `agibot_map_context.completed.json` 里加入
operator gate evidence。G2 暴露稳定定位信息时，可以记录操作员配置的 confidence
和 state 阈值：

```json
{
  "operator_localization_gate": {
    "selected_map_confirmed": true,
    "g02_pad_relocalized": true,
    "localization_ready": true,
    "localization_confidence": 0.92,
    "min_localization_confidence": 0.9,
    "localization_state": "localized",
    "accepted_localization_states": ["localized", "tracking"],
    "operator": "<operator>",
    "confirmed_at": "<iso8601>"
  },
  "operator_run_enablement_gate": {
    "enabled": true,
    "scope": "session",
    "operator": "<operator>",
    "confirmed_at": "<iso8601>"
  }
}
```

也可以记录可选的 bounded local nudge limit 作为 review evidence。它不会启用
agent-facing nudge tool；当前 Agibot map-build 仍然禁用 `relative_move` execution。
如果提供，数值必须由操作员确认，并且不能比保守默认值更宽松：

```json
{
  "operator_bounded_local_nudge": {
    "operator_configured": true,
    "max_distance_m": 0.12,
    "max_yaw_rad": 0.2,
    "timeout_s": 1.5,
    "source": "operator_safety_review"
  }
}
```

如果 nudge 配置过宽或未确认，adapter 会回退到
`max_distance_m=0.25`、`max_yaw_rad=0.35`、`timeout_s=3.0`，并在报告证据里标记
该配置无效。

本地生成 Roboclaws Agent View 和预览图：

```bash
.venv/bin/python scripts/agibot/generate_metric_map_from_context.py \
  output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  --output-dir output/agibot/map-context/<stamp>/generated_metric_map
```

检查 `agent_view.json`、`metric_map.json`、`fixture_hints.json` 和
`semantic_preview.png`。Agent-facing map 不能暴露原始 Agibot map source、GDK
内部细节或 PNC verification payload。

## 验证 Waypoints

Waypoint verification 会移动机器人。只有操作员确认 map、localization、safety
bounds 和 stop access 之后才能运行：

```bash
.venv/bin/python scripts/agibot/verify_waypoints_with_pnc.py \
  output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  --all \
  --yes
```

verification evidence 应把 candidate status 规范化为 `verified`、`blocked` 或
`timeout`。成功 PNC 证据应包含 `navigation_backend=agibot_gdk` 和
`primitive_provenance=agibot_gdk_normal_navi`。

## Dry-Run 报告

开启 movement 前，先用 public task route 跑 dry-run：

```bash
just task::run semantic-map-build direct camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  waypoint_id=<verified_waypoint_id> \
  output_dir=output/agibot/semantic-map-build-dry-run
```

它应该产出 `run_result.json`、`trace.jsonl`、subphase reports 和 `report.html`。
报告应展示 dry-run movement-gate block、可见 policy decision、skipped waypoint
reasoning 和 blocked manipulation。

Codex 控制的 `semantic-map-build` lane 使用 Agibot-specific MCP server route：

```bash
just task::run semantic-map-build codex camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  output_dir=output/agibot/semantic-map-build-codex-dry-run \
  policy=map_evidence_refresh \
  prompt="$OPEN_EVIDENCE_REFRESH_PROMPT" \
  visual_grounding=grounding-dino \
  visual_grounding_timeout_s=20
```

该路线会启动 Docker-backed Codex runtime，连接 `agibot_semantic_map_build` MCP
server，并写出 `run_result.json`、`trace.jsonl`、`runtime_metric_map.json` 和
`report.html`。在 `camera-labels` 下，报告会记录
`perception_mode=camera_model_policy`、请求的 visual-grounding pipeline，以及明确的
no-live-camera failure boundary，不会伪造 camera labels。这个 route 有 mock
contract coverage，也跑过 fixture dry-run；真实 G2 hardware validation 仍然是独立
未跑 gate。

cleanup-shaped contract rehearsal 可以用同一个 backend route，但 manipulation 必须
保持 blocked：

```bash
just task::run household-cleanup direct camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  waypoint_id=<verified_waypoint_id> \
  output_dir=output/agibot/household-cleanup-dry-run
```

不要把这个报告描述成 physical cleanup success。

## Movement Run

只有 operator 确认 run-level gate 后，才设置 `real_movement_enabled=true`。当前第一
hardware target 是 `semantic-map-build`：

```bash
just task::run semantic-map-build direct camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  waypoint_id=<verified_waypoint_id> \
  output_dir=output/agibot/semantic-map-build-hardware \
  real_movement_enabled=true
```

SDK-backed direct CLI boundary 是最小硬件 bring-up 路线。Codex MCP route 也已经支持
`semantic-map-build backend=agibot_gdk`，但不要把 mock contract test、direct-run
report 或 dry-run Codex report 说成真实 G2 hardware evidence。hardware acceptance
claim 必须来自真实 G2、operator gate enabled、报告 label 诚实的 run。

Codex-controlled hardware acceptance 使用同一个 public route，只是在 operator gate
之后开启 movement：

```bash
just task::run semantic-map-build codex camera-labels \
  backend=agibot_gdk \
  context_json=output/agibot/map-context/<stamp>/agibot_map_context.completed.json \
  output_dir=output/agibot/semantic-map-build-hardware \
  policy=map_evidence_refresh \
  prompt="$OPEN_EVIDENCE_REFRESH_PROMPT" \
  visual_grounding=grounding-dino \
  visual_grounding_timeout_s=20 \
  real_movement_enabled=true
```

Codex hardware run 之后，用 hardware-only gate 验证产物：

```bash
.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  output/agibot/semantic-map-build-hardware/<stamp>/seed-7/run_result.json \
  --expect-backend agibot_gdk \
  --expect-mcp-server agibot_semantic_map_build \
  --require-agent-driven \
  --require-camera-model-policy \
  --expect-visual-grounding-pipeline grounding-dino \
  --require-runtime-metric-map \
  --require-semantic-sweep \
  --require-agibot-g2-hardware \
  --min-generated-mess-count 0 \
  --min-sweep-coverage 1.0 \
  --allow-partial-cleanup
```

这个 gate 会拒绝 dry-run rehearsal artifact。它要求有 `real_movement_enabled`
证据、成功的 `agibot_gdk_normal_navi` 导航、带 image artifact 的 live
`agibot_gdk_head_color_camera` observation、没有 Human Takeover Stop，以及成功的
External Visual Grounding Service 输出。

## Review Checklist

只有 `report.html` 和 `run_result.json` 同时满足以下条件时，才接受 pilot：

- `cleanup_profile=real_robot_cleanup_v1`
- `backend_variant=agibot_gdk`
- `physical_navigation_pilot=true`
- `physical_cleanup_ready=false`
- `agent_view.policy_view.policy_observation_camera=head_color`
- real movement 的 navigation evidence 是 `agibot_gdk_normal_navi`；dry-run 或 gate
  failure 下是 `blocked_capability`
- real hardware acceptance 的 `camera-labels` 有成功的 External Visual Grounding
  Service evidence
- `cleanup_policy_trace.agent_reasoning_visible=true`
- visited 和 skipped public waypoint 都包含 decision、progress 和 reason
- manipulation tools 保持 blocked
- 任何失败都会进入 Human Takeover Stop evidence，而不是隐藏 fallback

在真实 G2 上完成 operator-supervised movement 并满足这份 checklist 之前，真实
Agibot hardware validation 仍然是未完成状态。
