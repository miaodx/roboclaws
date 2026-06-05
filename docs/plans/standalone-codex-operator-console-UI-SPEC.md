---
phase: pre-gsd
slug: standalone-codex-operator-console
status: approved
reviewed_at: 2026-06-05T00:00:00Z
review_scope: rewritten to match shipped agent-neutral implementation
shadcn_initialized: false
preset: none
created: 2026-06-03
rewritten: 2026-06-05
supersedes: codex-only v1 contract (2026-06-03)
---

# Standalone Operator Console - UI Design Contract

> Visual and interaction contract for the standalone operator console.
> Companion to `docs/plans/standalone-codex-operator-console.md`.
>
> **Rewrite note (2026-06-05):** The original v1 contract was Codex-only
> ("Codex Operator Console", "Start Codex Run"). The
> `docs/plans/refactor-operator-console-ui.md` refactor deliberately made the
> console **agent-provider neutral** — routes now carry `driver_label` of either
> `Codex` or `Claude Code`, and the shipped shell uses a four-column layout that
> splits route selection from setup. This contract has been rewritten to
> describe that shipped reality and to set the *intended* design targets the
> audit measures against. Where the contract states a target the current code
> does not yet meet, that gap is a real audit finding, not a contract error.
> Rationale carried forward from the `FINDING-001..008` design commits is noted
> inline.

---

## Product Frame

This is an operator cockpit for robotics runs driven by a local coding agent
(Codex or Claude Code). It is not a report page, a marketing page, a chat app,
or a generic terminal. The first screen must let an operator answer five
questions by scanning:

1. What route am I about to run, and which agent driver backs it?
2. Is the backend resource available and safe to start?
3. What does the robot currently see?
4. What is the agent doing or deciding?
5. What control can I safely use right now?

Primary user posture: focused, monitoring, safety-conscious, likely local to a
GPU or robot machine.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none |
| Preset | not applicable |
| Component library | none; native HTML controls plus small local JS helpers |
| Icon library | none for v1; text labels plus status badges (no icon fonts) |
| Font | Owned system stack — `system-ui` for UI, `ui-monospace` for logs and command previews |

**Font note (carries `FINDING-003`):** The original contract named IBM Plex Sans
and JetBrains Mono. Those webfonts were never bundled, so the console shipped a
bare system fallback that did not match the contract. The accepted resolution is
to **own the system stack as the contract**: `system-ui, -apple-system,
BlinkMacSystemFont, "Segoe UI", sans-serif` for UI and `ui-monospace,
SFMono-Regular, Menlo, Consolas, monospace` for monospace. No external font CDN —
the console must not block on isolated robot networks.

---

## Layout Contract

### Desktop Primary Layout

Minimum comfortable viewport: 1280 x 800. The fixed-column shell engages above
**1360px**; at or below that width the layout stacks (carries `FINDING-001` /
`FINDING-002`).

The shipped app shell is a **four-column** grid with a top bar and bottom strip:

```
grid-template-columns: 240px 300px minmax(520px, 1fr) 300px
grid-template-rows:    56px  minmax(0, 1fr)            112px
grid-template-areas:
  "top    top    top        top"
  "routes setup  workspace  state"
  "events events events     events"
```

| Region | Width / Height | Purpose |
|--------|----------------|---------|
| Top run bar | 56px high | App title, active run id, route status, backend lock, elapsed time, global controls |
| Route rail | 240px wide | Route cards with per-route readiness badge |
| Setup panel | 300px wide | Selected-route summary, parameters, gates, custom prompt, command preview, Start |
| Center workspace | `minmax(520px, 1fr)` | View-mode tabs and the live image grid (the visual anchor) |
| State rail | 300px wide | Run state, decision evidence, tool trace, checker proof, raw logs |
| Bottom event strip | 112px high | Recent events and log markers |

**Why four columns, not three:** the refactor split "choose a route" (route rail)
from "configure the selected route" (setup panel) so they read as two adjacent
operator steps instead of one long left rail. This supersedes the original
three-region (320 / fluid / 360) layout.

The center workspace is the visual anchor. The eye should find the live image
grid first, then the safety/control state, then the route form.

### Narrow Layout (≤ 1360px)

The console is not optimized for operating a real robot from a phone. Narrow
viewports must remain readable for observation and debugging:

- The shell stacks to a single column in the order: top, routes, setup,
  workspace, state, events.
- Top run bar stays sticky.
- View modes wrap; the active view shows a single workspace panel set.
- Start, Stop, and Emergency Stop stay reachable without horizontal scrolling.
- Minimum touch target is 44px.

### Cards And Containers

Cards are allowed only for repeated route entries and individual evidence items.
Do not put cards inside cards. Page regions are full-height panels, not floating
decorative cards.

---

## Primary Screens

### 1. Route Setup

Purpose: choose one safe agent route and provide only supported inputs.

Focal point: the selected route card and its readiness state.

Routes are agent-neutral — each carries a `driver_label` of `Codex` or
`Claude Code`. Enabled routes:

| Route | Driver | Backend Lock | Prompt | Start State |
|-------|--------|--------------|--------|-------------|
| MuJoCo Cleanup | Codex / Claude Code | `molmospaces_mujoco` | enabled | enabled when no lock is held |
| Isaac Cleanup | Codex | `isaac_gpu` | enabled | disabled until Isaac preflight is accepted |
| Agibot G2 Map Build | Codex | `agibot_g2` | enabled | disabled until context and operator gates are accepted |
| MuJoCo Map Build | Codex | `molmospaces_mujoco` | enabled | enabled when no lock is held |
| Isaac Map Build | Codex | `isaac_gpu` | enabled | disabled until Isaac preflight is accepted |

Required disabled cards, each with a concrete in-line reason:

| Route | Disabled Copy |
|-------|---------------|
| Agibot G2 Cleanup | `Physical manipulation is blocked. Run Agibot G2 Map Build first.` |
| Direct / OpenClaw / VLM | `This console supports local coding-agent drivers only.` |
| Claude Map Build | `semantic-map-build does not support the Claude driver yet.` |
| AI2-THOR games | `Navigation games are outside this operator console.` |

### 2. Active Run

Purpose: monitor the robot, the agent, and backend evidence while preserving
safe operator controls.

Focal point: latest robot visual evidence.

Workspace view modes (each must actually switch the visible layout — carries
`FINDING` from the refactor's "misleading view tabs" P1):

- `Overview` — default. Two columns: left `FPV` (+ optional `Grounding` below),
  right `Map`. Routes without grounding show `FPV` and `Map` as equal columns
  with no empty grounding panel.
- `FPV` — latest first-person or policy camera frame, focused.
- `Map` — runtime metric map, generated waypoints, route progress.
- `Grounding` — detection result frame.
- `Chase` — simulator chase view when the backend provides one.
- `Outputs` — report, trace, run result, checker output (renamed from
  "Artifacts" per the refactor).

Right state rail sections:

1. `Run State` — phase, backend lock, terminal reason.
2. `Decision` — latest action, observation summary, model-provided reasoning,
   blocked-capability reason.
3. `Tools` — latest MCP tool call payload.
4. `Proof` — route checker status and log.
5. `Raw Logs` — collapsed by default; expands redacted driver log.

### 3. Finished Run

Purpose: make it obvious whether the run is usable evidence.

Focal point: terminal status and checker verdict.

| State | Meaning | Primary Action |
|-------|---------|----------------|
| `passed` | checker passed | `Open Report` |
| `failed` | process or checker failed | `View Failure` |
| `stopped_by_operator` | operator stopped the run | `Open Artifacts` |
| `human_takeover_stop` | real-robot safety takeover ended the run | `Review Takeover` |

---

## Interaction Contract

### Route Selection

- Selecting a route updates parameters, prompt availability, required gates,
  command preview, and start state immediately.
- Route-specific field groups (Isaac, Agibot) are hidden unless the selected
  route declares them (carries the refactor's "irrelevant backend controls" P1).
- Unsupported routes remain visible but disabled with a concrete in-line reason.

### Prompt Input

Label: `Task prompt`. Enabled only when the route declares `supports_prompt`.

Disabled copy: `This route cannot accept a custom prompt safely. Use the default task prompt.`

Constraints: multiline textarea, visible character count, empty prompt uses the
route default, prompt text is never interpreted as shell.

### Start

Primary CTA label: **`Start Agent Run`** (agent-neutral; supersedes
"Start Codex Run").

Start opens a confirmation summary before launching: route, driver, backend,
profile, lock name, movement mode for Agibot, prompt source, output directory.

Confirmation CTA label: `Launch Run`.

### Pause

Label: `Pause Agent`. Request cooperative pause at the next safe checkpoint.
Never implies immediate physical motion stop. Disabled unless the run reports
`pause_available`.

### Stop

Label: `Stop Run`. Confirmation copy:
`Stop this run? The console will terminate the active process and preserve the current artifacts.`

### Emergency Stop

Label: `Emergency Stop`. Visually distinct from Stop (darker red, thicker
border). Confirmation copy:
`Trigger the real-robot emergency stop path now. This ends the run and requires human takeover before another run.`

### Human Takeover Stop

Terminal in v1. Only next actions: `Open Artifacts`, `Start New Run` after gates
revalidate. Do not offer Resume.

---

## Spacing Scale

Declared values (4px base):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, micro-gaps, label/field gaps |
| sm | 8px | Inline controls, compact rows, button padding |
| md | 16px | Default panel padding and form spacing |
| lg | 24px | Region gutters, grouped sections |
| xl | 32px | Major vertical breaks inside side rails |

Documented exceptions:

- Border radius: 4px / 6px / 8px (control / input / panel).
- Minimum touch target / button min-height: 44px.
- Panel-header button min-height: 32px.
- Top run bar height: 56px.
- Bottom event strip height: 112px.
- Route card min-height: 88px.
- Command-preview min-height: 72px.
- Shell column widths: 240 / 300 / `minmax(520,1fr)` / 300px.

All other spacing must use the 4px scale. A bare `6px` or `12px` is allowed only
where listed above (radius, input/control padding); new arbitrary values are
findings.

---

## Typography

Maximum four sizes and two weights.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Label / meta / mono | 12px | 500 | 1.35 |
| Body | 16px | 400 | 1.5 |
| Heading | 20px | 500 | 1.25 |
| Display / run title | 28px | 500 | 1.15 |

Rules:

- Use tabular numerals for elapsed time, counts, and metrics. The top-bar
  elapsed clock and any numeric run-state value must set
  `font-variant-numeric: tabular-nums`.
- Use the monospace stack at 12px for command previews and raw log excerpts.
- No all-caps paragraph labels. Short uppercase badges allowed only for route
  status (`LOCKED`, `READY`, `BLOCKED`, `PASSED`, `UNAVAILABLE`,
  `NEEDS ACTION`).
- Body text must not drop below 16px (meta/labels at 12px are exempt).
- Long file paths and command previews must wrap with a copy action.

---

## Color

A quiet light operational palette with high-contrast safety states. No
purple/blue gradients, decorative glows, or one-note dark dashboard styling.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#F4F6F3` | App background and inactive panel background |
| Secondary (30%) | `#FFFFFF` | Main panels, tables, form surfaces |
| Accent (10%) | `#1F8A70` | Primary CTA, active route, active tab, focus ring, hover border |
| Text | `#1F2522` | Main text |
| Muted text | `#66736D` | Meta, timestamps, secondary evidence |
| Border | `#CED8D1` | Panel boundaries and rules |
| Warning | `#935600` | Preflight needed, lock held, degraded route |
| Destructive | `#B42318` | Stop, failed safety gate |
| Emergency surface | `#7F1D1D` | Emergency Stop button fill (distinct from Stop) |
| Success | `#287D3C` | Checker passed, gate ready |

**Warning value note (carries `FINDING-005`):** darkened from the original
`#B56A00` to `#935600` to pass WCAG AA contrast on the light background.

`#FFFFFF` foreground text is permitted only as the label color on filled
accent / destructive / emergency / active-tab buttons.

Accent is reserved for: `Start Agent Run`, active selected route, active view
tab, keyboard focus ring, hover affordance border. Do not use accent for every
link or interactive element. Secondary buttons use neutral borders.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| App title | `Agent Operator Console` |
| Primary CTA | `Start Agent Run` |
| Launch confirmation CTA | `Launch Run` |
| Pause CTA | `Pause Agent` |
| Stop CTA | `Stop Run` |
| Emergency CTA | `Emergency Stop` |
| Empty run state | `No run selected` |
| Idle event hint | `Choose an agent route on the left. The console will show required gates before launch.` |
| Setup placeholder | `Choose a route to configure its parameters and gates.` |
| No visual frame | `No frame yet. Waiting for the first observation artifact.` |
| No decision | `No decision yet. The agent has not called a robot tool.` |
| No tool calls | `No tool calls yet.` |
| No checker result | `No checker result yet.` |
| Route locked error | `Backend lock is held by another run. Open that run or wait for it to finish.` |
| Prompt enabled help | `Empty prompt uses the route default. Prompt text is never interpreted as shell.` |
| Prompt disabled | `This route cannot accept a custom prompt safely. Use the default task prompt.` |
| Stop confirmation | `Stop this run? The console will terminate the active process and preserve the current artifacts.` |
| Emergency confirmation | `Trigger the real-robot emergency stop path now. This ends the run and requires human takeover before another run.` |

All agent-facing copy is provider-neutral: say "the agent", never "Codex" or
"Claude" in shared UI strings. Per-route driver identity is carried by the
`driver_label` field shown on the route card.

---

## Live View Contract

| Panel | Aspect Ratio | Empty State |
|-------|--------------|-------------|
| FPV | 4:3 | `No frame yet. Waiting for the first observation artifact.` |
| Chase | 16:9 | `Chase view unavailable for this backend.` |
| Map | (fills) | `Map artifact has not been written yet.` |
| Grounding | 4:3 | `No grounding result yet.` |

Each image panel must preserve stable dimensions so new frames do not resize the
layout. Frames render as `object-fit: contain` images with an `alt`.

**Grounding overlay:** when the console renders detection boxes itself (rather
than consuming a pre-rendered grounding image), boxes use semantic color —
accent for selected target, warning for candidate, destructive for
rejected/failed — and every box carries a visible text label. Color is never the
only cue. (If the backend bakes boxes into the grounding image, the console
shows that image as-is and this overlay rule does not apply.)

---

## Decision Evidence Contract

The right rail distinguishes public decision evidence from raw logs.

Default visible: latest action, observation summary, model reasoning when
present, blocked/override reason, phase, backend lock, terminal reason, latest
tool call, checker status.

Expandable raw evidence (collapsed by default): redacted driver log. Raw
evidence must pass secret redaction before rendering — API keys, bearer tokens,
Authorization headers, secret base URLs, `.env` values.

---

## States

| UI State | Required Visual |
|----------|-----------------|
| Idle | route rail active, center empty state, controls disabled |
| Preflight / Gates Needed | selected route visible, gate checklist with `Needs Action`, Start disabled, inline blocker |
| Ready | Start enabled, command preview visible |
| Running | top run bar active, visual panels update, controls enabled by route |
| Paused | Pause reflects `pause_available`; never implies motion stop |
| Stopping | controls reflect availability; terminal-state wait |
| Passed | green checker status, Open Report primary |
| Failed | red checker/process status, View Failure primary |
| Human Takeover Stop | red safety state, Resume hidden, Open Artifacts primary |

---

## Accessibility Contract

- All controls reachable by keyboard.
- Focus ring uses accent color with at least 2px visible outline via
  `:focus-visible` (carries `FINDING-004`).
- No icon-only control without an accessible name. View-mode nav has an
  `aria-label`; image frames have `alt`.
- Touch targets at least 44px on narrow layouts.
- Text contrast meets WCAG AA: 4.5:1 body, 3:1 large text and UI components.
- Color is never the only state cue — pair with text and shape (badges carry a
  word, not just a color).
- A live region announces terminal state changes and safety blockers so an
  operator monitoring peripherally is alerted without watching the rail.
- Destructive actions require confirmation.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none | not required |
| third-party registries | none | not applicable |

No third-party visual registry blocks. No frontend package manager; the static
bundle is hand-authored HTML/CSS/JS.

---

## Design Review Rubric Targets

| Dimension | Target |
|-----------|--------|
| Visual hierarchy | Live robot view is the strongest anchor; safety controls second; route form third. |
| Typography | Up to four sizes, two weights; readable dense app UI; tabular numerals on metrics. |
| Color | Neutral operational palette; accent sparing; destructive and emergency unmistakable and distinct from each other. |
| Spacing | 4px scale plus documented shell exceptions only. |
| Interaction | Route selection, gates, start, pause, stop, and report handoff obvious without docs. |
| AI slop avoidance | No hero, no gradients, no feature grids, no icon bubbles, no centered marketing sections. |
| DX | Add a route by editing route metadata (`field_groups`, `view_modes`, `driver_label`) without touching layout code. |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS (agent-neutral)
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved as the rewritten baseline describing the shipped
agent-neutral console.

Review scope: this contract describes the implemented console and sets intended
design targets. It is not itself a rendered audit — the live 6-pillar audit
runs against this baseline in `*-UI-REVIEW.md`.
