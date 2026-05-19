## Conflict Detection Report

> **UPDATE 2026-05-14:** Merge ingest for
> `docs/retrospectives/plans/generic-mcp-entrypoint-semantic-capabilities.md` used the
> manifest
> `docs/retrospectives/plans/generic-mcp-entrypoint-semantic-capabilities.ingest.yaml`.
> Autoplan evidence was already reconciled in the PRD. Repo search found no
> existing phase for this exact generic MCP profile/router scope, so the merge
> created Phase 136 as one coherent phase. No LOCKED decision contradiction,
> warning, or blocker was found. The phase explicitly excludes ROS/Nav2,
> Docker Gateway, GPU, live VLM, paid API, and real-robot validation.

---

> **UPDATE 2026-04-20 (same day):** Both WARNINGs below were found to be
> **stale** when verified against the live code and issue tracker.
> Root cause: `docs/research/05-real-model-smoke-validation.md` is a
> dated validation report from 2026-04-14; the issues it describes were
> fixed the next day. The doc-synthesizer reasoned over the doc bundle
> and treated the dated report as current state. Both WARNINGs are
> **RESOLVED — no blockers for Phase 2.4.**
>
> Evidence:
> - Commit `ddfb523` (2026-04-15 10:55) — "feat: improve multi-agent
>   VLM game decisions" — wired `images=prompt_images` through
>   `game.decide()` in `examples/territory_game.py:316` and
>   `examples/coverage_game.py:357`.
> - `roboclaws/games/coverage.py:185-211` uses field-of-view
>   accounting (yaw + half-FOV angle math), not visited-cells.
> - Issue #52 **CLOSED** 2026-04-15T05:13:18Z.
>
> Lesson captured under `feedback_verify_ingest_claims` in
> `~/.claude/projects/-home-mi-ws-gogo-roboclaws/memory/` — always
> cross-check synthesizer claims about "current broken state"
> against git log + live code.

---

Generated: 2026-04-20 (new-mode bootstrap)
Precedence: ADR > SPEC > PRD > DOC
Scope: 18 classified docs — 1 ADR (LOCKED), 2 SPECs, 15 DOCs.

Cycle-detection pass: cross_refs graph traversed (max depth 50);
no cycles detected among content-bearing docs. Most cross-refs point to
source files under `roboclaws/` / `examples/` / `skills/` — not back to
other classified docs — so the doc graph is an unrooted forest, not a
cyclic mesh.

UNKNOWN / low-confidence pass: zero UNKNOWN-type classifications and
zero `low` confidence classifications. No blockers from this pass.

LOCKED-vs-LOCKED pass: only one LOCKED ADR in the ingest set
(`docs/retrospectives/phase-2.3.md`). No contradiction possible in
new-mode with a single locked doc.

### BLOCKERS (0)

No hard blockers. Synthesis is safe to consume for routing.

### WARNINGS (2 — both RESOLVED on verification, see UPDATE above)

[WARNING — RESOLVED 2026-04-20] Competing acceptance variants for REQ-coverage-game — field-of-view vs visited-cells
  Found:
    - source: docs/technical-design.md § Scenario B Cooperative Coverage
      requires "cells within an agent's field of view are marked as
      covered" and "reach 95% coverage as fast as possible" (termination
      at 95%).
    - source: docs/research/05-real-model-smoke-validation.md § Findings
      documents the shipped implementation as visited-cells based; after
      100 steps on real AI2-THOR + real Kimi, coverage reached 21/234
      (8.97%) and terminated via `max_steps` — never 95%.
  Precedence: SPEC > DOC would normally pick the SPEC, but the DOC here
    is a post-hoc validation report that explicitly flags the SPEC vs
    shipped behavior as an unresolved design question. The validation
    report (05) says the follow-up (issue #52) must decide ONE coherent
    story: either field-of-view + feed images, or visited-cells + revise
    docs + smoke expectations.
  Impact: Synthesis cannot pick without losing intent. Phase 2.4
    (view-experiment A/B) treats coverage as a measured game and will
    produce meaningless results if the coverage semantics are unresolved
    — the "primary metric" for coverage in the A/B is
    `coverage_fraction`, which means different things under the two
    variants.
  → Resolve by routing issue #52 to a decision before Phase 2.4's
    T35 local-dev sweep runs. Options: (a) update coverage.py to
    field-of-view accounting and feed images, keep the 95% target,
    update smoke expectations only if needed; (b) keep visited-cells,
    revise docs/technical-design.md and the README smoke-expectation
    narrative to match.

[WARNING — RESOLVED 2026-04-20] Competing acceptance variants for the territory/coverage VLM image-payload contract
  Found:
    - source: docs/technical-design.md § VLM Strategy § Prompt Structure
      and § Scenario A/B VLM-receives-per-step: both games feed the VLM
      two images per step — first-person camera frame (base64 JPEG) and
      overhead grid/coverage map.
    - source: docs/research/05-real-model-smoke-validation.md § Likely
      Cause Of Failure: the shipped game loops in
      `roboclaws/games/territory.py` and `roboclaws/games/coverage.py`
      call `provider.get_action(images=[], state=game_state)` — state-
      only, no images fed. The provider API supports images; the game
      loops don't use them yet.
  Precedence: SPEC > DOC would pick the SPEC (images in prompt), but the
    DOC is reporting observed 2026-04-14 production behavior and is the
    cited source for issue #52 scope.
  Impact: The view-experiment A/B in PLAN.md § Phase 2.4 wires
    `view-builder → provider.get_action(images=prompt_images, ...)` with
    2 or 3 images per variant. If the underlying territory/coverage game
    loops are still stripping images on the way to `get_action`, the
    entire Phase 2.4 sweep measures noise — every variant sees the same
    (empty) image list.
  → Resolve before Phase 2.4 execution. Either (a) fix the game loops
    to pass `images` through to `provider.get_action` (the view-builder
    in PLAN T32 assumes this), or (b) treat "pass images through" as an
    explicit Phase 2.4 prerequisite task and add it to the T29a…T37
    sequence.

### INFO (1)

[INFO] Auto-resolved: LOCKED ADR subsumes three non-locked sources on Gateway image pinning
  Note: docs/retrospectives/phase-2.3.md (LOCKED) declines digest
    pinning and keeps `ghcr.io/openclaw/openclaw:2026.4.14`. Three
    non-locked sources align with this decision:
      - docs/retrospectives/phase-2.md Task 4 / A3 (pin
        `:2026.4.14`, keep `OPENCLAW_IMAGE` override for forks)
      - docs/openclaw-local.md § env-var table IMAGE default
      - TODOS.md § Declined section (Phase 2.3 digest pin declined)
    All four agree: pin the date-shaped tag, digest override via repo
    variable. The LOCKED ADR in `decisions.md` is the authoritative
    source; `constraints.md § CONSTR-openclaw-image-pin` derives from
    the ADR. No action needed — recorded for transparency.
