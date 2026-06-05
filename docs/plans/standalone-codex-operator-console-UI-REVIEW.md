# Operator Console — UI Review

**Audited:** 2026-06-05
**Target:** `roboclaws/operator_console/static/` (index.html, styles.css, app.js)
**Baseline:** `docs/plans/standalone-codex-operator-console-UI-SPEC.md` (rewritten 2026-06-05 to the shipped agent-neutral contract)
**Screenshots:** not captured — no dev server reachable on :3000 / :5173 / :8080. Code-only audit (static CSS/JS/HTML analysis).
**Stack note:** vanilla HTML + CSS custom properties + plain JS. No Tailwind/JSX, so the auditor's Tailwind-class greps were adapted to CSS-property analysis.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Every SPEC contract string matches verbatim; agent-neutral language is consistent. |
| 2. Visuals | 3/4 | Strong hierarchy and view-mode switching, but the live view is not the largest type/visual anchor and grounding overlay boxes are unimplemented. |
| 3. Color | 4/4 | All semantic colors tokenized; accent reserved correctly; emergency distinct from stop; WCAG fix preserved. |
| 4. Typography | 3/4 | Within the 3-size / 1-weight envelope, but the 28px display size and tabular elapsed clock from the contract are not implemented. |
| 5. Spacing | 4/4 | Pure 4px/8px/16px scale; every off-scale value (2/6/12px radius+padding) is a documented exception. |
| 6. Experience Design | 3/4 | Loading/error/empty/disabled/confirm states all present, but no `aria-live` region and stop/emergency use native `window.confirm` instead of the styled dialog. |

**Overall: 21/24**

---

## Top 3 Priority Fixes

1. **Top-bar elapsed clock is not tabular** (Typography, Accessibility) — `#elapsed-status` lives in `.run-meta` (styles.css:130–138), which has no `font-variant-numeric`; `tabular-nums` is set only on `#run-state dd` (styles.css:523). The clock at index.html:18 visibly jitters its width every second as digits change. **Fix:** add `font-variant-numeric: tabular-nums;` to `.run-meta` (or a dedicated `#elapsed-status` rule).

2. **No live region for terminal state / safety blockers** (Experience, Accessibility) — the SPEC Accessibility Contract requires a live region to announce terminal status and blockers; `grep aria-live|role="status"|role="alert"` returns nothing in index.html/app.js. An operator monitoring peripherally gets no announcement when a run fails or a safety gate blocks. **Fix:** mark `#event-log` (or a dedicated node) `role="status" aria-live="polite"`, and announce terminal/blocked transitions there in `renderRunState`.

3. **Run title never reaches the contract's display size** (Typography, Visuals) — the SPEC defines a 28px/500 Display role for the run title, but `#run-title` is a `<span>` inside 12px `.run-meta` (index.html:14–15). The strongest text on the active-run screen is the 20px `.app-title` (a fixed chrome label), so the live run is not the type anchor it should be. **Fix:** promote the active run title to the 28px display size when a run is active, or restructure the top bar so run identity outranks the static app title.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)

Audited every row of the SPEC Copywriting Contract against shipped strings.

- App title `Agent Operator Console` — index.html:13 ✓
- Primary CTA `Start Agent Run` — index.html:101 ✓
- `Pause Agent` / `Stop Run` / `Emergency Stop` — index.html:22–24 ✓
- Launch confirmation CTA `Launch Run` — index.html:174, 178 ✓
- No-decision copy `No decision yet. The agent has not called a robot tool.` — index.html:150, app.js:425 ✓
- Stop confirmation and Emergency confirmation strings — app.js:93, 99 ✓ (verbatim)
- Idle hint, setup placeholder, all four empty-frame states — index.html:38, 118, 126, 130, 168 ✓

**Agent-neutral consistency:** `grep -i codex` over index.html + app.js returns nothing. The shipped UI never says "Codex" or "Claude" in shared strings — provider identity is carried per-route via `driver_label`, exactly as the rewritten contract requires. This is the one place the *old* SPEC was wrong about reality; the rewrite resolved it, and the implementation is clean.

No generic labels ("Submit", "OK", "Click Here") anywhere. Disabled routes carry concrete reasons (routes.py:278–326), satisfying "disabled controls must include a concrete reason in-line."

### Pillar 2: Visuals (3/4)

Strengths:
- Clear region hierarchy via the four-area grid (styles.css:99–109): top / routes / setup / workspace / state / events.
- View-mode switching genuinely changes layout — `mode-overview` uses a 2fr/1fr two-column grid with named areas (styles.css:396–401), and `no-grounding` collapses cleanly to a single row (styles.css:403–406). This was the refactor's headline P1 ("misleading view tabs") and it is correctly resolved.
- Icon-free design means no unlabeled icon-button risk; the one nav (`.view-modes`) has `aria-label="Workspace view modes"` (index.html:107) and image frames carry `alt` (app.js:479).

Gaps (−1):
- **The live robot view is not the strongest visual anchor.** The SPEC rubric target is "live robot view is the strongest anchor." But the largest type on screen is the 20px `.app-title` chrome label; image panels have no elevated focal treatment (same 1px border + 8px radius as evidence boxes). On the empty/idle state the workspace reads as equal-weight to the rails.
- **Grounding overlay boxes are not implemented.** The SPEC Live View Contract describes semantic-colored detection boxes with text labels. `grep bounding|overlay|detection` in app.js/styles.css returns nothing — grounding renders as a passive `<img>` (app.js:465, 479). This is acceptable *if* the backend bakes boxes into the image (the rewritten contract allows this), so it is a WARNING, not a BLOCKER — but it should be confirmed against backend output, and the contract's overlay rule is currently dormant.

### Pillar 3: Color (4/4)

- All nine semantic roles are CSS custom properties (styles.css:2–10) and consumed via `var()`. The only literal colors are `#ffffff` foreground on filled accent/danger/emergency/active-tab buttons (styles.css:78, 84, 90, 381) and `#7f1d1d` as the dedicated emergency surface (styles.css:91) — both explicitly sanctioned by the rewritten contract.
- **Accent discipline:** `--accent` is used on primary CTA, active route card (`box-shadow: inset 4px 0 0` styles.css:255), active view tab (styles.css:380–384), focus ring (styles.css:53–57), and hover borders — exactly the reserved set. Not sprayed across every link.
- **Emergency distinct from Stop:** `.danger` is `--danger` (#B42318) with a 1px border; `.emergency` is the darker #7F1D1D with a 2px `--danger` border (styles.css:83–93). The two destructive tiers are unmistakably different, satisfying "must be visually distinct from Stop."
- **WCAG rationale preserved:** `--warning: #935600` (styles.css:8) carries the `FINDING-005` darkening from the contract's original #B56A00. Good — the review history stayed legible through the SPEC rewrite.
- **Color is not the only cue:** badges pair color with a word (`READY`, `LOCKED`, `NEEDS ACTION` — app.js:188–206), satisfying the accessibility "never color alone" rule.

### Pillar 4: Typography (3/4)

Size distribution (CSS): `12px ×9`, `16px ×2`, `20px ×2`. Weights: `500 ×9` only (body inherits the implicit 400 via the `body` rule, styles.css:18–25).

- **Within envelope:** three explicit sizes + body 16px = within the SPEC's "max four sizes." One non-default weight (500) + default 400 = within "max two weights." No violation of the hard caps.
- **System stack owned** (`FINDING-003`): `system-ui, -apple-system, …` for UI (styles.css:20) and `ui-monospace, …` for mono (styles.css:222) — matches the rewritten font contract. No webfont CDN.
- Mono is correctly applied to textarea/pre/`.evidence-box`/`.command-preview` (styles.css:218–223).

Gaps (−1):
- **28px Display role unused.** `grep 28px` returns nothing. The contract's 4th size (run title) is not implemented; run identity renders at 12px (`.run-meta` span). See Top Fix #3.
- **Elapsed clock not tabular.** `font-variant-numeric: tabular-nums` is present only on `#run-state dd` (styles.css:523), not on the top-bar `#elapsed-status` in `.run-meta`. The contract requires tabular numerals on the elapsed clock specifically. See Top Fix #1. (The run-state numeric values *are* tabular — partial compliance.)

### Pillar 5: Spacing (4/4)

Spacing-property px values in use: `4px ×6`, `8px ×17`, `16px ×14`, plus `2px ×1` and `12px ×4` and `6px ×1`.

- The core scale is **clean 4 / 8 / 16** — the dominant values are exactly the contract's xs/sm/md tokens. `24px` and `32px` (lg/xl) aren't needed at this density, which is fine.
- **Every off-scale value is a documented exception:**
  - `2px` — badge vertical padding (`padding: 2px 6px`, styles.css:305) and focus outline width.
  - `6px` — border-radius on inputs/buttons (styles.css:40, 44…) and badge horizontal padding, both listed radius/padding exceptions.
  - `12px` — control padding (`padding: 8px 12px`) and route-card padding (styles.css:243), within the input/control-padding exception.
- **Shell dimensions match the contract exactly:** `240px 300px minmax(520px,1fr) 300px` / `56px minmax(0,1fr) 112px` (styles.css:101–102) — the documented four-column shell with the 56px bar and 112px strip. Route-card min-height 88px and command-preview min-height 72px are both listed exceptions.
- No `!important` spacing hacks; the only `!important` is the legitimate `[hidden]` reset (styles.css:33–35).

No arbitrary/magic spacing values found.

### Pillar 6: Experience Design (3/4)

State coverage is broad:
- **Empty states:** all four image panels (app.js:462–465) plus decision/tool/proof rails (index.html:150, 153, 158) plus idle event hint — 7 distinct empty strings, all matching contract copy.
- **Loading/pending:** checker status falls back to `"pending"` (app.js:431, 486); artifact links show `pending` until a href exists (app.js:455).
- **Error states:** API error surfaces are handled at every fetch site — readiness (app.js:307), run create (app.js:377), poll (app.js:402) — each writing to an inline error node rather than failing silently.
- **Disabled gating:** Start is gated on `route.enabled && can_start` (app.js:184); pause/stop/emergency gated on `controls.*_available` from the backend (app.js:442–444); prompt disabled when `!supports_prompt` (app.js:158).
- **Destructive confirmation:** stop and emergency both confirm before acting (app.js:93–104); launch uses the styled `<dialog>` (app.js:336).

Gaps (−1):
- **No `aria-live` region.** Contract requires announcing terminal state and safety blockers; none exists. See Top Fix #2. This is the single biggest experience gap because it directly defeats the "operator monitoring peripherally" posture from the Product Frame.
- **Inconsistent confirmation surface.** Launch uses a styled, accessible `<dialog>` (`#confirm-dialog`), but Stop and Emergency — the *higher-stakes* actions — use native `window.confirm()` (app.js:94, 100), which is unstyled, not theme-aware, and visually weakest exactly where confirmation matters most. Recommend routing all three destructive confirmations through the same `<dialog>` with the contract's `Trigger Emergency Stop` / `Stop Run` CTAs.

Minor:
- The emergency confirmation copy matches the contract, but the confirmation *button* for emergency/stop is the OS default ("OK"), not the contract's `Trigger Emergency Stop` / `Stop Run` labels. Folding into the `<dialog>` fixes both at once.

---

## Registry Safety

No `components.json`, no shadcn, no third-party registries. The static bundle is
hand-authored HTML/CSS/JS with no package manager. **Registry audit: skipped (not
applicable).** No network-access, eval, or dynamic-import patterns found in
app.js (the only `fetch` calls are same-origin `/api/*` and `/artifacts/*`).

---

## Files Audited

- `roboclaws/operator_console/static/index.html` (186 lines)
- `roboclaws/operator_console/static/styles.css` (615 lines)
- `roboclaws/operator_console/static/app.js` (624 lines)
- `roboclaws/operator_console/routes.py` (route catalog — copywriting/gate cross-check)
- Baseline: `docs/plans/standalone-codex-operator-console-UI-SPEC.md` (rewritten this session)
