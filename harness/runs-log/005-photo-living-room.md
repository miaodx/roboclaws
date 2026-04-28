## Run 005 — 2026-04-28 — clean closure with corrected `goto`

**Task**: same.
**Model / harness**: full stack — P0a + P2 + P1 + harness fixes + goto y-coordinate fix.
**Outcome**: **done** at t=229s. **9/9 targets** captured. **0 blocked moves**. All 10 `goto` calls returned `ok`.

### Metrics
- Tool calls: **37** (vs Run 003: 65, Run 002: 55, Run 001: 127+)
- Per tool: `scene_objects=1`, `goto=10`, `observe=5`, `observe_archived=7`, `move=13`, `done=1`
- `blocked_moves: 0`
- FPV snapshots: 13
- Wall-clock: 229s (3.8 min)
- Targets: chair-1, chair-2, chair-3, chair-4, chair-5, chair-6, sofa-1, armchair-1, armchair-2 — full coverage.

### What the agent actually did
The trace.jsonl shows the exact protocol from SKILL.md being followed:

1. `observe(label="preflight")`
2. `scene_objects(filter_types="Sofa,Chair,ArmChair")` → 9 targets, sorted by `distance_xz`
3. For each of 9 targets: `goto(object_id=...)` then either `observe(label=<type>-<n>)` to verify framing OR `observe_archived(label=<type>-<n>)` to capture
4. A handful of `move` calls for fine-tuning framing after gotos (13 total — about 1.4 per target)
5. `done(reason="captured ...")`

### Friction log
**Effectively none.** This is the closure run.

Minor observation: the agent issued 5 `observe` (image-bearing) and 7 `observe_archived` (text-only). That's a 5:7 ratio in favor of the cheap variant — the SKILL.md update that says "verify framing with observe, capture with observe_archived" is being followed and saved ~5 image-token blocks of context vs always-observe.

### Cross-run summary
| Run | Setup | calls | gotos | blocks | targets | outcome | wall-clock |
|---|---|---:|---:|---:|---:|---|---|
| 001 | manual baseline | 127+ | — | many | 3/9 | user interrupt | ~25 min |
| 002 | harness, no skill changes | 55 | — | ~19 | 3/9 | done (mis-classified) | 10 min |
| 003 | + scene_objects + inventory protocol | 65 | — | 10 | 9/9 | timeout @ 600s | 10 min |
| 004 | + goto (with y-bug) | 23 partial | 10/10 ❌ | — | aborted | killed | ~5 min |
| 005 | goto fixed | **37** | 10/10 ✅ | 0 | **9/9** | **done** | **3.8 min** |

**3.4× fewer tool calls than Run 001, full target coverage, agent self-terminates.**

### What this proves about the loop
1. The harness measures *real* deltas. Each change moved a metric in the predicted direction (or surfaced an unpredicted bug like Run 004).
2. Testing-via-fake is necessary but not sufficient for tools that cross the simulator boundary. Run 004 caught a class of bug FakeEngine fundamentally cannot catch.
3. Skill changes alone (Run 002 → 003) produced a 3× target coverage gain at +18% tool cost. Code changes (Run 003 → 005) produced a further 43% reduction in tool cost.

### Carry-forward
- [ ] Two related polish items worth queuing but NOT urgent:
  - `goto` could fall back to a slightly-larger-distance cell when the chosen one collides at runtime (despite being in the reachable set), instead of returning `error`. Run 004 surfaced this; Run 005 didn't trigger it but FloorPlan201 may have edge cases.
  - Pre-commit hook should ideally run a quick smoke that exercises one round-trip of every tool against a real (small) AI2-THOR scene. That's a CI investment the loop hasn't earned yet — defer until we have ≥2 more loops.
- [ ] **Productize the harness**: with a 4-iteration trajectory of measurable improvement, this is now a proven pattern. Worth a `harness/README.md` aimed at future maintainers ("how to add a new task class, how to interpret PLAN.md, when to abort vs. iterate").
- [ ] **Pick the next task class.** The photo task is solved. Plausible next: "navigate to all rooms and report the object inventory of each", or "grasp + place" (manipulation). New task = new friction = new round of P-changes.
