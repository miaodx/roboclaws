---
phase: pre-gsd
slug: standalone-codex-operator-console
status: approved
reviewed_at: 2026-06-03T09:57:56Z
review_scope: pre-gsd artifact review
shadcn_initialized: false
preset: none
created: 2026-06-03
---

# Standalone Codex Operator Console - UI Design Contract

> Visual and interaction contract for the standalone Codex operator console.
> Generated as the design-first companion to
> `docs/plans/standalone-codex-operator-console.md`.

---

## Product Frame

This is an operator cockpit for robotics runs. It is not a report page, a
marketing page, a chat app, or a generic terminal. The first screen must let an
operator answer five questions by scanning:

1. What route am I about to run?
2. Is the backend resource available and safe to start?
3. What does the robot currently see?
4. What is Codex doing or deciding?
5. What control can I safely use right now?

Primary user posture: focused, monitoring, safety-conscious, likely local to a
GPU or robot machine.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | none for v1; use native HTML controls and small local helpers |
| Icon library | lucide icons if a frontend package is introduced; otherwise text labels plus simple status dots |
| Font | IBM Plex Sans for UI, JetBrains Mono for logs and command previews |

Implementation note: font files should be served locally if bundled. External
font CDNs are not required for v1 and must not block the console on isolated
robot networks. Browser defaults may be fallback only, not the primary contract.

---

## Layout Contract

### Desktop Primary Layout

Minimum comfortable viewport: 1280 x 800.

Use a fixed app shell with four regions:

| Region | Width / Height | Purpose |
|--------|----------------|---------|
| Top run bar | 56px high | Active run id, route, backend lock, elapsed time, global controls |
| Left route rail | 320px wide | Route cards, parameters, custom prompt, preflight gates |
| Center workspace | fluid | Live FPV/chase/map views, visual grounding overlays, active artifact |
| Right state rail | 360px wide | Phase/status, decision evidence, tool trace, checker status |
| Bottom event strip | 112px high, collapsible | Recent events, log markers, artifact links |

The center workspace is the visual anchor. The first thing the eye should find
is the live image grid, then the safety/control state, then the route form.

### Mobile / Narrow Layout

The console is not optimized for operating a real robot from a phone. Narrow
viewports must remain readable for observation and debugging:

- Top run bar stays sticky.
- Views become a single active view with segmented tabs: `FPV`, `Chase`, `Map`,
  `Grounding`.
- Route rail, state rail, and event strip become tabs.
- Start, Stop, and Emergency Stop stay reachable without horizontal scrolling.
- Minimum touch target is 44px.

### Cards And Containers

Cards are allowed only for repeated route entries and individual evidence
items. Do not put cards inside cards. Page regions are full-height panels, not
floating decorative cards.

---

## Primary Screens

### 1. Route Setup

Purpose: choose one safe Codex route and provide only supported inputs.

Focal point: the selected route card and its readiness state.

Required route cards:

| Route | Default Profile | Backend Lock | Prompt | Start State |
|-------|-----------------|--------------|--------|-------------|
| MuJoCo Cleanup | `world-labels` | `molmospaces_mujoco` | enabled | enabled when no lock is held |
| Isaac Cleanup | `world-labels` | `isaac_gpu` | enabled | disabled until Isaac preflight is accepted |
| Agibot G2 Map Build | `camera-labels` | `agibot_g2` | enabled | disabled until context and operator gates are accepted |
| MuJoCo Map Build | `world-labels` | `molmospaces_mujoco` | enabled | enabled when no lock is held |
| Isaac Map Build | `world-labels` | `isaac_gpu` | enabled | disabled until Isaac preflight is accepted |

Required disabled cards:

| Route | Disabled Copy |
|-------|---------------|
| Agibot G2 Cleanup | `Physical manipulation is blocked. Run Agibot G2 Map Build first.` |
| Direct / OpenClaw / Claude / VLM | `This console is Codex-only for v1.` |
| AI2-THOR games | `Navigation games are outside this operator console.` |

### 2. Active Run

Purpose: monitor the robot, Codex, and backend evidence while preserving safe
operator controls.

Focal point: latest robot visual evidence.

Center workspace tabs:

- `FPV` - latest first-person or policy camera frame.
- `Chase` - simulator chase view when available.
- `Map` - runtime metric map, generated waypoints, route progress.
- `Grounding` - detection boxes, labels, confidence, failure evidence.
- `Artifacts` - report, trace, run result, checker output.

Right rail sections:

1. `Run State`
   - phase
   - elapsed time
   - backend lock
   - terminal reason if finished
2. `Decision`
   - goal
   - latest observation summary
   - selected action
   - model-provided reasoning when present
   - override or blocked-capability reason
3. `Tools`
   - latest MCP tool calls
   - success/failure
   - latency
4. `Proof`
   - route checker status
   - required gates
   - report link

### 3. Finished Run

Purpose: make it obvious whether the run is usable evidence.

Focal point: terminal status and checker verdict.

Terminal states:

| State | Meaning | Primary Action |
|-------|---------|----------------|
| `passed` | checker passed | `Open Report` |
| `failed` | process or checker failed | `View Failure` |
| `stopped_by_operator` | operator stopped the run | `Open Artifacts` |
| `human_takeover_stop` | real robot safety takeover ended the run | `Review Takeover` |

---

## Interaction Contract

### Route Selection

- Selecting a route updates parameters, prompt availability, required gates,
  command preview, and start state immediately.
- Unsupported combinations remain visible but disabled.
- Disabled controls must include a concrete reason in-line, not only a tooltip.

### Prompt Input

Label: `Task prompt`

Enabled only when route metadata declares `supports_prompt=true`.

Disabled copy:

`This route cannot accept a custom prompt safely. Use the default task prompt.`

Prompt field constraints:

- Multiline textarea.
- Visible character count.
- Empty prompt uses the route default.
- Prompt text is never interpreted as shell.

### Start

Primary CTA label: `Start Codex Run`

Start opens a confirmation summary before launching:

- route
- backend
- profile
- lock name
- prompt source: custom or default
- required gates
- output directory

Confirmation CTA label: `Launch Run`

### Pause

Label: `Pause Agent`

Meaning: request cooperative pause at the next safe route checkpoint.

Pause must never imply immediate physical motion stop. If the selected backend
cannot pause, show:

`Pause is unavailable for this route. Use Stop or Emergency Stop.`

### Stop

Label: `Stop Run`

Meaning: request process/server termination, preserve artifacts, and write a
terminal operator state if possible.

Confirmation copy:

`Stop this run? The console will terminate the active process and preserve the current artifacts.`

Confirmation CTA: `Stop Run`

### Emergency Stop

Label: `Emergency Stop`

Meaning: backend-specific hard stop or visible operator instruction. Required
for Agibot G2 routes. It must be visually distinct from Stop.

Confirmation copy:

`Trigger the real-robot emergency stop path now. This ends the run and requires human takeover before another run.`

Confirmation CTA: `Trigger Emergency Stop`

### Human Takeover Stop

Human Takeover Stop is terminal in v1. The only next actions are:

- `Open Artifacts`
- `Start New Run` after gates are revalidated

Do not offer Resume after Human Takeover Stop.

---

## Spacing Scale

Declared values:

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, table cell micro-gaps |
| sm | 8px | Inline controls, compact rows |
| md | 16px | Default panel padding and form spacing |
| lg | 24px | Region gutters, grouped sections |
| xl | 32px | Major vertical breaks inside side rails |
| 2xl | 48px | Empty state vertical spacing |
| 3xl | 64px | Reserved for non-console docs, not primary app shell |

Exceptions:

- Minimum touch target: 44px.
- Top run bar height: 56px.
- Bottom event strip height: 112px.
- Route rail width: 320px.
- State rail width: 360px.

All other spacing must use the declared scale.

---

## Typography

Maximum four sizes and two weights.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Label / meta | 12px | 500 | 1.35 |
| Body | 16px | 400 | 1.5 |
| Heading | 20px | 500 | 1.25 |
| Display / run title | 28px | 500 | 1.15 |

Rules:

- Use tabular numerals for elapsed time, counts, metrics, and route latencies.
- Use JetBrains Mono at 12px or 14px for command previews and raw log excerpts.
- Do not use all-caps paragraph labels. Short uppercase badges are allowed only
  for route status such as `LOCKED`, `READY`, `BLOCKED`, `PASSED`.
- Body text must not drop below 16px.
- Long file paths and command previews must wrap or truncate with a copy action.

---

## Color

The console uses a quiet light operational palette with high-contrast safety
states. Avoid purple/blue gradients, decorative glows, and one-note dark
dashboard styling.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#F4F6F3` | App background and inactive panel background |
| Secondary (30%) | `#FFFFFF` | Main panels, tables, form surfaces |
| Accent (10%) | `#1F8A70` | Primary CTA, active route, active tab, focus ring |
| Text | `#1F2522` | Main text |
| Muted text | `#66736D` | Meta, timestamps, secondary evidence |
| Border | `#CED8D1` | Panel boundaries and table rules |
| Warning | `#B56A00` | Preflight needed, lock held, degraded route |
| Destructive | `#B42318` | Stop, Emergency Stop, destructive confirmations |
| Success | `#287D3C` | Checker passed, gate ready |

Accent reserved for:

- `Start Codex Run`
- active selected route
- active view tab
- keyboard focus ring
- current run progress marker

Destructive reserved for:

- `Stop Run`
- `Emergency Stop`
- Human Takeover Stop
- failed safety gate

Do not use accent for every link or every interactive element. Secondary
buttons use neutral borders.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| App title | `Codex Operator Console` |
| Primary CTA | `Start Codex Run` |
| Launch confirmation CTA | `Launch Run` |
| Pause CTA | `Pause Agent` |
| Stop CTA | `Stop Run` |
| Emergency CTA | `Emergency Stop` |
| Empty state heading | `No run selected` |
| Empty state body | `Choose a Codex route on the left. The console will show required gates before launch.` |
| No visual frame state | `No frame yet. Waiting for the first observation artifact.` |
| No decision state | `No decision yet. Codex has not called a robot tool.` |
| Route locked error | `Backend lock is held by another run. Open that run or wait for it to finish.` |
| Isaac preflight error | `Isaac preflight has not passed. Run the preflight gate before launch.` |
| Agibot gate error | `Agibot operator gates are incomplete. Attach context, localization, run enablement, and E-stop readiness evidence.` |
| Prompt disabled | `This route cannot accept a custom prompt safely. Use the default task prompt.` |
| Generic run failure | `The run failed before producing passing evidence. Open artifacts for the failure reason.` |
| Stop confirmation | `Stop this run? The console will terminate the active process and preserve the current artifacts.` |
| Emergency confirmation | `Trigger the real-robot emergency stop path now. This ends the run and requires human takeover before another run.` |

Button labels must include a verb and noun except short safety labels that are
already conventional: `Stop Run`, `Emergency Stop`.

---

## Route Gate Contract

| Route | Required Gates Before Start | Passing Evidence |
|-------|-----------------------------|------------------|
| MuJoCo Cleanup | no active `molmospaces_mujoco` lock; provider key route present | cleanup checker passes; report exists |
| MuJoCo Map Build | no active `molmospaces_mujoco` lock; provider key route present | runtime metric map checker passes; report exists |
| Isaac Cleanup | no active `isaac_gpu` lock; accepted preflight/runtime-smoke artifact | strict Isaac checker passes; report exists |
| Isaac Map Build | no active `isaac_gpu` lock; accepted preflight/runtime-smoke artifact | runtime metric map checker passes; report exists |
| Agibot G2 Map Build | no active `agibot_g2` lock; `context_json`; localization gate; run enablement; E-stop readiness | Agibot semantic-map-build checker passes; runtime metric map exists |

Gate visuals:

- `Ready` - green status dot and enabled gate row.
- `Needs Action` - amber status dot, disabled Start, inline fix.
- `Blocked` - red status dot, disabled Start, inline blocker.
- `Running` - accent status dot, lock owner displayed.

---

## Live View Contract

### Image Panels

Each image panel must preserve stable dimensions so new frames do not resize the
layout.

| Panel | Aspect Ratio | Empty State |
|-------|--------------|-------------|
| FPV | 4:3 | `No frame yet. Waiting for the first observation artifact.` |
| Chase | 16:9 | `Chase view unavailable for this backend.` |
| Map | 1:1 | `Map artifact has not been written yet.` |
| Grounding | 4:3 | `No grounding result yet.` |

Panel controls:

- open full view
- copy artifact path
- freeze latest frame
- show timestamp

### Visual Grounding Overlay

Bounding boxes use semantic color by status:

- selected target: accent
- candidate: warning
- rejected/failed: destructive

Every box needs a visible label outside the box when possible. Do not rely on
color alone.

---

## Decision Evidence Contract

The right rail must distinguish public decision evidence from raw logs.

Default visible fields:

- current goal
- latest observation summary
- selected route phase
- latest tool call
- selected action
- model-provided reasoning field when present
- blocked or override reason
- provider health

Expandable raw evidence:

- `codex-events.jsonl`
- `trace.jsonl`
- prompt state excerpts
- stderr excerpts

Raw evidence must pass secret redaction before rendering. Redaction covers API
keys, bearer tokens, Authorization headers, provider base URLs when configured
as secrets, and `.env` values.

---

## States

| UI State | Required Visual |
|----------|-----------------|
| Idle | route rail active, center empty state, right rail hidden or empty |
| Preflight Needed | selected route visible, gate checklist prominent, Start disabled |
| Ready | Start enabled, command preview visible |
| Starting | Start disabled, spinner in route card, log strip opens |
| Running | top run bar active, visual panels update, controls enabled by route |
| Paused | amber paused banner, Resume available only if route supports it |
| Stopping | Stop disabled, terminal-state wait indicator |
| Passed | green checker status, Open Report primary |
| Failed | red checker or process status, View Failure primary |
| Human Takeover Stop | red safety banner, Resume hidden, Open Artifacts primary |

---

## Accessibility Contract

- All controls must be reachable by keyboard.
- Focus ring uses accent color and at least 2px visible outline.
- No icon-only control without an accessible name and visible tooltip.
- Touch targets are at least 44px on narrow layouts.
- Text contrast must meet WCAG AA: 4.5:1 for body, 3:1 for large text and UI
  components.
- Color is never the only state cue. Pair color with text and shape.
- Live regions announce terminal state changes and safety blockers.
- Destructive actions require confirmation.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party registries | none | not applicable |

No third-party visual registry blocks are approved for v1. If a frontend package
is introduced later, component sources must be reviewed before entering this
contract.

---

## Design Review Rubric Targets

| Dimension | Target |
|-----------|--------|
| Visual hierarchy | The live robot view is the strongest visual anchor; safety controls are second. |
| Typography | Four sizes, two weights, readable dense app UI. |
| Color | Neutral operational palette; accent used sparingly; destructive states unmistakable. |
| Spacing | 4px scale plus documented shell exceptions only. |
| Interaction | Route selection, preflight, start, pause, stop, and report handoff are obvious without reading docs. |
| AI slop avoidance | No hero, no decorative gradients, no feature grids, no icon bubbles, no centered marketing sections. |
| DX | A developer can add a route by editing route metadata and an adapter, without touching layout code. |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved for pre-GSD planning.

Review scope: this approval covers the UI design contract and documented route
gates only. It is not a rendered UI audit; after implementation, run live
browser QA with desktop and narrow viewport screenshots before treating the
console as visually approved.
