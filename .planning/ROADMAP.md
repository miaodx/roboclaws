# Roadmap: roboclaws

## Overview

Roboclaws delivers the first public demonstration of multiple OpenClaw
agent instances simultaneously controlling multiple simulated robots in
competition and cooperation. The journey: first prove the VLM-drives-a-robot
core hypothesis directly against AI2-THOR (Phase 1), then layer CI +
dev-topology to keep the demo continuously alive (Phase 1.5), then route
control through an OpenClaw Gateway (Phases 2 → 2.1 → 2.2), then validate
whether better map representations help a VLM win harder games (Phase 2.4)
and, in parallel, test a different architectural bet — let the agent drive
via tool calls instead of the push model (Phase 2.5 → 2.6). The next follow-up
on that autonomous branch is Phase 2.7: expose the agent's intermediate
messages in artifacts, with a streaming-first preference if the real Gateway
surface supports it cleanly. Phase 3 (Isaac Lab) is deferred indefinitely.
Phase 6 is the MolmoSpaces cleanup scaffold: a narrow, provenance-labeled
`api_semantic` cleanup loop that keeps AI2-THOR as the baseline while proving
the first room-cleanup artifact contract. Phase 7 builds on it with a
prompt-driven public-policy cleanup proof for `帮我整理这个房间`. Phase 8 moves
that proof onto a real upstream MolmoSpaces/MuJoCo scene through the isolated
Python 3.11 subprocess backend while keeping `api_semantic` provenance explicit.
Phases 9-14 add visual reviewability, semantic substeps, carried-object visual
consistency, current-contract agent bridge evidence, and the ADR-0003
public/private real-world cleanup boundary. Phase 15 scales that ADR-0003
hidden Generated Mess Set from the historical five-object fixture to the v1
lower bound of 10 generated objects. Phase 16 exposes the ADR-0003 public
cleanup contract through MCP without the current-contract `scene_objects`
shortcut. Phase 17 adds the direct coding-agent dogfood kit and clean-run
checker for that stricter MCP surface. Phase 18 proves OpenClaw Gateway can use
the same ADR-0003 MCP contract. Phase 19 closes the visual-evidence gap with
OpenClaw-labeled and live Gateway artifacts on the real MolmoSpaces/RBY1M
backend carrying the full shared report view set. Phase 20 hardens the clean
policy path by making the ADR-0003 semantic cleanup loop executable in the MCP
contract instead of prompt-only guidance. Phase 21 adds a non-authoritative
advisory scoring/model-check artifact to the same shared report pipeline.
Phase 22 starts the raw FPV-only perception branch with an evidence mode that
records camera observations without structured movable-object detections. Phase
23 adds a planner-backed manipulation provenance/proof gate so semantic cleanup
state edits cannot be confused with real RBY1M/Franka planner execution. Phase
24 adds runtime diagnostics for strict planner probe blockers. Phase 25 closes
standalone Franka planner proof with a probe-local headless renderer adapter;
Phase 26 attached that strict proof to cleanup reports while preserving
`api_semantic` cleanup-loop provenance. Phase 27 closes the per-subphase cleanup
primitive gate that future real planner-backed cleanup execution must pass.
Phase 28 closes the RBY1M/CuRobo runtime gate that must be ready before planner
primitive replacement can depend on the target robot path. Phase 29 closes the
unblocked camera-only model-policy gap by deriving observed handles from public
raw FPV observations while reusing the ADR-0003 semantic cleanup/report
underlay. Phase 30 consolidated the shared Cleanup Artifact Report presentation
so current-contract and ADR-0003 artifacts keep one visual core while rendering
their contract-specific evidence. Phase 31 closes staged RBY1M/CuRobo
warmup-readiness evidence: the local target runtime still times out at
`rby1m_config_import` during CuRobo warmup, so target execute-mode proof remains
gated. Phase 32 isolates the CuRobo/Torch extension cache for RBY1M retries and
renders extension cache state in the planner probe report; config import now
succeeds, while execute mode is blocked by the installed Warp API shape. Phase
33 makes that Warp compatibility adapter visible and probe-local; execute mode
now reaches policy run and blocks on CUDA memory pressure. Phase 34 captures
CUDA memory headroom as first-class planner probe evidence before tuning or
primitive replacement; the latest target retry shows the OOM occurs during
CuRobo trajectory planning after PyTorch reservation grows to about 9.9 GiB.
Phase 35 adds a visible probe-local low-memory CuRobo profile for the next
target execute retry; that retry now passes strict standalone RBY1M/CuRobo
planner-backed proof with nonzero robot-state movement. Phase 36 consolidated
the duplicated current-contract and ADR-0003 object cleanup loops behind one
shared semantic driver before planner-backed primitive replacement begins.
Phase 37 added explicit planner cleanup bridge-readiness evidence so reports
distinguish target RBY1M/CuRobo runtime readiness from cleanup subphases that
still remain `api_semantic`. Phase 38 added the strict planner-backed cleanup
primitive executor seam behind that shared driver. Phase 39 tightens that seam
so planner primitive evidence must bind to the exact cleanup object and target.
Phase 40 adds the probe-backed executor adapter that accepts only bound
RBY1M/CuRobo proof, keeping generic standalone target proof blocked as cleanup
primitive evidence. Phase 41 makes the actual planner probe emit sampled-task
binding and promote cleanup binding only on exact request/sample match. The
Phase 42 splits ADR-0003 observed-handle cleanup IDs from planner sampled-task
aliases so matching proof can later flow through the real cleanup primitive
executor. Phase 43 wires that executor into the shared semantic cleanup loop
for a bounded object/subphase attempt before any full multi-object replacement
claim. Phase 44 broadens that path to proof bundles so a full cleanup artifact
can select one bound proof per cleaned object before claiming bridge readiness.
Phase 45 tightens the shared report architecture by making current-contract and
ADR-0003 checkers enforce one visual-core contract and by removing the remaining
duplicated ADR-0003 MCP robot-view semantic mapping. Phase 46 closes the missing
local-dev handoff from completed cleanup artifacts to executable planner proof
requests, so real multi-proof bundle runs can be generated repeatably. Phase 47
makes those private proof requests reviewable in the shared cleanup report
without moving planner aliases into Agent View. Phase 48 adds a visual report
for the local proof-bundle runner output itself. Phase 49 adds a checker for
that runner manifest/report pair. Phase 50 removes the remaining hand-written
MCP smoke cleanup loops so current-contract and ADR-0003 smoke demos reuse the
shared semantic cleanup loop seam. Phase 51 adds a dry-run harness for the
planner proof bundle runner so the cleanup-to-proof-command handoff is
repeatable before local GPU execution. Phase 52 made cleanup rerun outputs
from executed proof-bundle runs first-class manifest/report/checker artifacts.
Phase 53 added the named local-dev gate that executes those bound proof bundles,
reruns cleanup, and checks the final planner-backed cleanup artifact. Its local
attempt proved all five RBY1M/CuRobo proofs can execute, but final cleanup
readiness remains blocked until proof probes can bind to the requested upstream
sampled tasks. Phase 54 binds those probes to the real cleanup scene XML and
requested planner aliases emitted by a `molmospaces_subprocess` cleanup run,
narrowing the blocker from random task mismatch to upstream RBY1M
cleanup-scene task feasibility and robot placement. Phase 55 makes executed
proof-bundle runner reports render per-proof result status, task-feasibility
classification, cleanup binding promotion, blockers, proof report links, and
planner views so the next fallback-selection phase has explicit bundle-level
evidence. Phase 56 adds proof request feasibility selection: local bundle runs
can consume a prior proof-result summary, skip requests already known to be
RBY1M task-feasibility blocked, and report when alternate request generation is
required. Phase 57 generates those private fallback proof requests from
existing observed-handle planner alias candidates, preserving cleanup-facing
object/target IDs while making alternate exact-scene probe commands visible in
the runner report. Phase 58 executes generated fallback proof requests as
local-dev evidence: the checker passes with required proof outputs, but all
four generated probes time out at `rby1m_config_import` before task sampling,
planner-backed proof, cleanup binding promotion, or planner views. Phase 59
aligns the shared Cleanup Artifact Report vocabulary with the original
semantic subphase discussion by making `nav`, `pick`, `nav`, optional `open`,
and `place` the primary labels while keeping role detail secondary. Phase 60
surfaces generated fallback timeout stage evidence in the shared proof-bundle
runner report, including timeout counts, execution-attempted state, last worker
stage, compact worker stage events, and stdout/stderr artifact paths. Phase 61
adds an explicit visible RBY1M/CuRobo warmup step to the proof-bundle runner so
generated fallback retries can share one output-local Torch extension cache
between config import and proof commands. Phase 62 executes that warmed
generated fallback bundle locally: warmup gets through config import and all
four generated proofs reach task sampling, where they now fail on invalid
exact-scene planner alias names instead of timeout. Phase 63 filters
upstream/display aliases out of generated fallback proof commands while keeping
them visible in runner reports; the current artifact has no executable
alternate aliases after filtering, so the next blocker is runtime alias
discovery. Phase 64 mines prior fallback `KeyError` valid-name lists for
same-family runtime aliases, renders that discovery in the runner report, and
turns it into four new generated fallback proof commands ready for local
execution. Phase 65 executes those discovered runtime-sibling fallback commands
locally with RBY1M/CuRobo warmup; they reach task sampling with no config-import
timeouts, but target-sibling aliases still fail `HouseInvalidForTask` and
object-sibling aliases fail as non-root bodies before proof, binding, or views.
Phase 66 carries that failed-candidate evidence forward so future fallback
generation filters prior non-root object aliases and prior task-feasibility
blocked object/target pairs, rendering both filtered aliases and filtered pairs
in the runner report.
Phase 67 executes the two remaining filtered fallback commands locally; both
reach task sampling without timeout but fail as non-root bodies before proof,
binding, or views.
Phase 68 carries prior filtered aliases and pairs forward so the latest executed
bundle manifest generates no duplicate fallback commands and exposes the
root-body alias derivation blocker.
Phase 69 adds an upfront pickup root-variant filter so object-side runtime
siblings with nonzero variants are filtered before local execution.
Phase 70 lets the runner merge multiple prior proof-bundle manifests so older
runtime alias discovery and newer failed-candidate memory are selected together.
Phase 71 surfaces fallback exhaustion status so no-command generated fallback
runs are visible as exhausted in the runner report and checker.
Phase 72 summarizes why those exhausted fallback pools have no remaining
commands, naming pickup root-body alias gaps, target task-feasibility-blocked
pairs, and unavailable source requests directly in the runner report.
Phase 73 normalizes non-root pickup runtime aliases to their variant-0 root
aliases, proving the current object-side aliases are already known and
narrowing the remaining fallback blocker to target-side task feasibility.

Phases 1 → 2.2 have shipped. Phase 2.3 was evaluated and declined. Phase 2.4
is active under `.planning/phases/02.4-view-experiment-ab/`: plans
`02.4-01` through `02.4-03` are complete, the cloud-safe analysis script
for `02.4-04` is implemented, and the remaining live sweep + decision
record are explicitly blocked on local-dev issue #70. Phase 2.5 was
drafted around a curl-in-exec tool-call contract that local probing on
2026-04-21 proved structurally wrong (agent fights the Gateway's exec
allowlist instead of using native tools) — it is SUPERSEDED by Phase 2.6,
which shipped the autonomous loop on first-class MCP tools + a `minimal`
tool profile (see
`.planning/phases/02.6-openclaw-mcp-tools-integration/02.6-SPIKE-FINDINGS.md`).
Phase 2.7 is now planned as the additive observability follow-up: compare
Gateway streaming vs terminal-body capture, then persist mid-run assistant
messages into the autonomous replay artifacts. Phase 4 is now complete as a
refactor-safety tooling follow-up: critical behavior contracts are frozen and
thin capture/analyze harnesses now exist for the direct-VLM,
territory/coverage, and OpenClaw paths. Phase 3 remains deferred indefinitely.

## Milestones

- ✅ **v1.0 Core + OpenClaw** - Phases 1, 1.5, 2, 2.1, 2.2 (shipped 2026-04-16)
- ⛔ **Phase 2.3 (Digest pin)** - DECLINED 2026-04-20 (LOCKED ADR)
- ✅ **v1.1 Better Views** - Phase 2.4 (decision locked 2026-04-24; runtime standardized on `map-v2+chase` only, legacy A/B sweep superseded)
- ⛔ **Phase 2.5 (Autonomous loop v1 — curl/exec tool contract)** - SUPERSEDED 2026-04-21 by Phase 2.6 after spike proved the curl-in-exec contract is structurally wrong (see `docs/retrospectives/openclaw-kimi-provider-debug-2026-04-21.md` + spike findings)
- ✅ **v1.2 Autonomous OpenClaw Loop** - Phase 2.6 (MCP tool surface — shipped 2026-04-21)
- 📋 **v1.3 Autonomous Transcript Visibility** - Phase 2.7 (planned 2026-04-22; compare streaming vs terminal-body capture, prefer streaming if supported)
- 📋 **v1.4 Split-model navigation** - Phase 2.8 (text reasoning model + separate vision model for autonomous navigation)
- ✅ **v1.5 Refactor Regression Safety** - Phase 4 (completed 2026-04-23; deterministic fixtures + capture/analyze harnesses + first local probe evidence in `04-LOCAL-PROBE-RESULTS.md`)
- ✅ **v1.6 Iterative Codebase Simplification** - Phase 5 (completed 2026-04-23; 18 target files simplified, global pytest+ruff green, net -203 lines across targets)
- ✅ **v1.7 MolmoSpaces cleanup pilot** - Phase 6 (completed 2026-05-07; api-semantic cleanup contracts, scorer, direct MCP/demo artifacts; real planner-backed manipulation deferred)
- ✅ **v1.8 MolmoSpaces prompt cleanup** - Phase 7 (completed 2026-05-07; public-policy prompt proof for `帮我整理这个房间`; real planner-backed manipulation deferred)
- ✅ **v1.9 MolmoSpaces real subprocess cleanup** - Phase 8 (completed 2026-05-07; real upstream MolmoSpaces/MuJoCo scene, Python 3.11 subprocess runtime, public prompt loop, `api_semantic` MuJoCo state mutation)
- ✅ **v1.10 MolmoSpaces FPV room plausibility** - Phase 9 (completed 2026-05-08; target-facing FPV and same-room visual checks)
- ✅ **v1.11 MolmoSpaces semantic substeps** - Phase 10 (completed 2026-05-08; object-level semantic timeline and fridge containment)
- ✅ **v1.12 MolmoSpaces held-object visuals** - Phase 11 (completed 2026-05-08; carried-object visual consistency during navigation)
- ✅ **v1.13 MolmoSpaces current-contract agent bridge** - Phase 12 (completed 2026-05-08; Codex/Claude/OpenClaw tool viability on the current contract)
- ✅ **v1.14 MolmoSpaces agent bridge visual results** - Phase 13 (completed 2026-05-08; reviewable bridge reports)
- ✅ **v1.15 MolmoSpaces real-world cleanup harness** - Phase 14 (completed 2026-05-09; ADR-0003 public/private contract and visual parity)
- ✅ **v1.16 MolmoSpaces Generated Mess Set scale** - Phase 15 (completed 2026-05-09; ADR-0005 configurable hidden generated object count with real 10-object evidence)
- ✅ **v1.17 MolmoSpaces real-world agent MCP** - Phase 16 (completed 2026-05-09; ADR-0006 MCP surface for the ADR-0003 public contract)
- ✅ **v1.18 MolmoSpaces real-world agent dogfood** - Phase 17 (completed 2026-05-09; direct coding-agent dogfood kit for the ADR-0003 MCP surface)
- ✅ **v1.19 MolmoSpaces real-world OpenClaw dogfood** - Phase 18 (completed 2026-05-09; OpenClaw Gateway viability on the ADR-0003 MCP surface)
- ✅ **v1.20 MolmoSpaces real-world OpenClaw visual evidence** - Phase 19 (completed 2026-05-09; real MolmoSpaces/RBY1M visual report evidence for OpenClaw Gateway)
- ✅ **v1.21 MolmoSpaces real-world OpenClaw clean policy** - Phase 20 (completed 2026-05-09; executable semantic-loop ordering for clean OpenClaw policy evidence)
- ✅ **v1.22 MolmoSpaces real-world advisory scoring** - Phase 21 (completed 2026-05-09; non-authoritative advisory scoring/model-check artifact)
- ✅ **v1.23 MolmoSpaces real-world raw FPV perception** - Phase 22 (completed 2026-05-09; evidence-mode camera observations without structured movable-object detections)
- ✅ **v1.24 MolmoSpaces planner-backed manipulation proof gate** - Phase 23 (completed 2026-05-09; provenance/report/checker gate before real planner-backed cleanup claims)
- ✅ **v1.25 MolmoSpaces planner runtime diagnostics** - Phase 24 (completed 2026-05-09; dependency/crash diagnostics for strict planner probe blockers)
- ✅ **v1.26 MolmoSpaces planner headless renderer** - Phase 25 (completed 2026-05-09; probe-local EGL renderer adapter and strict Franka planner proof)
- ✅ **v1.27 MolmoSpaces cleanup planner proof attachment** - Phase 26 (completed 2026-05-09; render strict planner proof inside cleanup reports without relabeling cleanup primitives)
- ✅ **v1.28 MolmoSpaces cleanup planner-backed primitive gate** - Phase 27 (completed 2026-05-09; per-subphase evidence gate before real planner-backed cleanup primitive replacement)
- ✅ **v1.29 MolmoSpaces RBY1M CuRobo runtime gate** - Phase 28 (completed 2026-05-09; target-robot runtime readiness gate before cleanup primitive replacement)
- ✅ **v1.30 MolmoSpaces camera model policy cleanup** - Phase 29 (completed 2026-05-09; camera-derived model-policy cleanup over the ADR-0003 shared underlay)
- ✅ **v1.31 MolmoSpaces report underlay consolidation** - Phase 30 (completed 2026-05-09; canonical report visual core and semantic subphase labels)
- ✅ **v1.32 MolmoSpaces RBY1M CuRobo warmup readiness** - Phase 31 (completed 2026-05-09; staged warmup/JIT evidence before target execute-mode retry)
- ✅ **v1.33 MolmoSpaces RBY1M CuRobo cache isolation** - Phase 32 (completed 2026-05-09; isolated Torch extension cache evidence before target execute-mode retry)
- ✅ **v1.34 MolmoSpaces RBY1M Warp compatibility** - Phase 33 (completed 2026-05-09; probe-local Warp API adapter before target execute-mode retry)
- ✅ **v1.35 MolmoSpaces RBY1M CUDA memory headroom** - Phase 34 (completed 2026-05-09; stage-local CUDA memory evidence for target execute-mode OOM)
- ✅ **v1.36 MolmoSpaces RBY1M CuRobo memory profile** - Phase 35 (completed 2026-05-09; visible low-memory CuRobo retry profile and strict target proof)
- ✅ **v1.37 MolmoSpaces shared semantic cleanup loop** - Phase 36 (completed 2026-05-09; one reusable `nav -> pick -> nav -> open? -> place` driver across cleanup demos)
- ✅ **v1.38 MolmoSpaces planner cleanup bridge readiness** - Phase 37 (completed 2026-05-09; explicit bridge evidence joining target proof and cleanup subphase provenance)
- ✅ **v1.39 MolmoSpaces planner-backed cleanup primitive executor** - Phase 38 (completed 2026-05-09; strict executor seam before object-specific cleanup primitive replacement)
- ✅ **v1.40 MolmoSpaces planner primitive target binding** - Phase 39 (completed 2026-05-09; object/target-bound primitive evidence before real executor wiring)
- ✅ **v1.41 MolmoSpaces probe-backed cleanup primitive executor** - Phase 40 (completed 2026-05-09; adapter from bound RBY1M/CuRobo proof to primitive executor evidence)
- ✅ **v1.42 MolmoSpaces planner probe cleanup binding** - Phase 41 (completed 2026-05-09; sampled-task binding diagnostics and exact-match cleanup binding promotion)
- ✅ **v1.43 MolmoSpaces observed handle planner binding** - Phase 42 (completed 2026-05-09; private observed-handle to planner sampled-task alias binding)
- ✅ **v1.44 MolmoSpaces bounded planner cleanup executor** - Phase 43 (completed 2026-05-09; opt-in probe-backed executor wiring for bounded cleanup subphases)
- ✅ **v1.45 MolmoSpaces planner proof bundle cleanup** - Phase 44 (completed 2026-05-10; one bound proof per cleaned object for bridge-ready full cleanup artifacts)
- ✅ **v1.46 MolmoSpaces report visual core contract** - Phase 45 (completed 2026-05-10; shared visual-core checks and MCP robot-view semantic reuse)
- ✅ **v1.47 MolmoSpaces planner proof request manifest** - Phase 46 (completed 2026-05-10; private proof request manifest and local bundle runner)
- ✅ **v1.48 MolmoSpaces planner proof request report view** - Phase 47 (completed 2026-05-10; private proof request report section)
- ✅ **v1.49 MolmoSpaces planner proof bundle runner report** - Phase 48 (completed 2026-05-10; visual command report for local proof generation)
- ✅ **v1.50 MolmoSpaces planner proof bundle runner checker** - Phase 49 (completed 2026-05-10; gate runner manifest/report integrity)
- ✅ **v1.51 MolmoSpaces MCP smoke shared semantic loop** - Phase 50 (completed 2026-05-10; MCP smoke demos reuse the shared semantic cleanup loop)
- ✅ **v1.52 MolmoSpaces planner proof bundle runner harness** - Phase 51 (completed 2026-05-10; dry-run harness for proof-bundle runner command generation)
- ✅ **v1.53 MolmoSpaces planner proof bundle cleanup rerun artifacts** - Phase 52 (completed 2026-05-10; cleanup rerun outputs tracked in runner manifests/reports/checkers)
- ✅ **v1.54 MolmoSpaces planner proof bundle execute rerun** - Phase 53 (completed 2026-05-10; local-dev execute-rerun gate exposed sampled-task mismatch blocker)
- ✅ **v1.55 MolmoSpaces bind proof probes to cleanup scene** - Phase 54 (completed 2026-05-10; exact cleanup-scene binding exposed RBY1M task-feasibility blocker)
- ✅ **v1.56 MolmoSpaces proof bundle result feasibility report** - Phase 55 (completed 2026-05-10; executed bundle reports show per-proof feasibility, blockers, and planner views)
- ✅ **v1.57 MolmoSpaces proof request feasibility selection** - Phase 56 (completed 2026-05-10; prior infeasible requests can be excluded and fallback-required state is reported)
- ✅ **v1.58 MolmoSpaces proof request fallback generation** - Phase 57 (completed 2026-05-10; blocked requests can generate private alternate planner-alias proof commands)
- ✅ **v1.59 MolmoSpaces generated fallback proof execution** - Phase 58 (completed 2026-05-10; generated fallback requests execute locally but time out at RBY1M config import before proof/binding)
- ✅ **v1.60 MolmoSpaces plain semantic report labels** - Phase 59 (completed 2026-05-10; reports use `nav, pick, nav, open?, place` as primary labels)
- ✅ **v1.61 MolmoSpaces fallback timeout stage reporting** - Phase 60 (completed 2026-05-10; generated fallback timeout stage evidence appears in proof-bundle summaries and reports)
- ✅ **v1.62 MolmoSpaces fallback proof warmup** - Phase 61 (completed 2026-05-10; proof-bundle runner can warm RBY1M/CuRobo before generated fallback proof commands)
- ✅ **v1.63 MolmoSpaces warmed generated fallback proof execution** - Phase 62 (completed 2026-05-10; warmed generated fallbacks reach task sampling but fail on invalid planner aliases)
- ✅ **v1.64 MolmoSpaces exact-scene fallback alias validation** - Phase 63 (completed 2026-05-10; generated fallback commands filter display aliases and report skipped candidates)
- ✅ **v1.65 MolmoSpaces fallback runtime alias discovery** - Phase 64 (completed 2026-05-10; prior KeyError valid-name lists generate runtime-sibling fallback commands)
- ✅ **v1.66 MolmoSpaces discovered runtime fallback proof execution** - Phase 65 (completed 2026-05-10; discovered runtime-sibling commands execute locally but block on task feasibility or non-root bodies)
- ✅ **v1.67 MolmoSpaces fallback failed-candidate memory** - Phase 66 (completed 2026-05-10; generated fallback selection filters prior non-root aliases and blocked alias pairs)
- ✅ **v1.68 MolmoSpaces filtered fallback proof execution** - Phase 67 (completed 2026-05-10; remaining filtered fallback commands execute locally but fail as non-root bodies)
- ✅ **v1.69 MolmoSpaces fallback filter carry-forward** - Phase 68 (completed 2026-05-10; prior filtered aliases and pairs remain active filters across manifests)
- ✅ **v1.70 MolmoSpaces pickup root variant filter** - Phase 69 (completed 2026-05-10; object-side nonzero runtime variants are filtered before proof command generation)
- ✅ **v1.71 MolmoSpaces prior proof evidence merge** - Phase 70 (completed 2026-05-10; multiple prior proof-bundle manifests merge alias discovery and failed-candidate memory before selection)
- ✅ **v1.72 MolmoSpaces fallback exhaustion status** - Phase 71 (completed 2026-05-10; generated fallback selection reports exhausted no-command states in manifests and reports)
- ✅ **v1.73 MolmoSpaces fallback exhaustion blockers** - Phase 72 (completed 2026-05-10; exhausted fallback reports name root-body alias, task-feasibility pair, and no-candidate blockers)
- ✅ **v1.74 MolmoSpaces pickup root alias normalization** - Phase 73 (completed 2026-05-10; non-root pickup runtime aliases normalize to variant-0 root aliases in runner reports)
- 📋 **v2.0 Isaac Lab** - Phase 3 (deferred indefinitely)

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3, 4): Planned milestone work
- Decimal phases (2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8): Sub-phases within Milestone 2 (OpenClaw integration track)

- [x] **Phase 1: Core simulation + games** - Direct-VLM multi-agent territory + coverage on AI2-THOR (shipped)
- [x] **Phase 1.5: CI + dev topology** - Three-layer demo matrix + cloud/local workflow (shipped)
- [x] **Phase 2: OpenClaw Gateway bridge (original)** - First Gateway integration via standalone demo (shipped)
- [x] **Phase 2.1: Transport correction** - `/v1/chat/completions` + named-agent routing + inline base64 (shipped)
- [x] **Phase 2.2: Long-running OpenClaw games** - Per-agent SOULs + SOUL overlay + territory/coverage through Gateway (shipped)
- [⛔] **Phase 2.3: Gateway digest pin** - DECLINED; keep date-shaped `:2026.4.14` tag (LOCKED)
- [x] **Phase 2.4: Better Views** - Runtime standardized on `map-v2+chase` only; legacy `baseline` / `map-v2` experiment superseded on 2026-04-24
- [⛔] **Phase 2.5: Autonomous OpenClaw loop (v1 — curl/exec contract)** - SUPERSEDED 2026-04-21 by Phase 2.6. Plans drafted but never executed; contract was "agent curls our HTTP server from the exec tool," spike proved Gateway's exec allowlist + generic image tool fight this architecture. Kept as a lesson — do not resurrect.
- [x] **Phase 2.6: Autonomous OpenClaw loop (v2 — MCP tool surface)** - Same goal as 2.5 (single-agent nav + human steer), correct architecture: `observe`/`move`/`done` as first-class MCP tools over streamable-http; agent runs under `profile: minimal` (no exec, no curl, no generic `image`); spike-proven 2026-04-21; **shipped 2026-04-21** — see `docs/retrospectives/phase-2.6.md`
- [ ] **Phase 2.7: Autonomous OpenClaw intermediate-message capture** - Add mid-run assistant transcript visibility to the shipped MCP loop. Compare streaming vs terminal-body capture first, prefer streaming if the real Gateway surface supports it, then persist the chosen path into `trace.jsonl`, `run_result.json`, and `report.html`.
- [ ] **Phase 2.8: Split-model navigation** - Enable text-only reasoning models (mimo-v2.5-pro, mimo-v2.5) to drive autonomous navigation by intercepting image-bearing MCP tool results and converting them to text descriptions via a vision model (mimo-v2-omni) before the main model sees them. Also explore whether OpenClaw's tool-profile system can expose the `image` tool alongside `roboclaws__*` without exec/curl drift.
- [x] **Phase 4: Refactor regression harnesses for VLM, territory/coverage, and OpenClaw** - Deterministic fixtures + capture/analyze harnesses that make large refactors safer across the direct-VLM and OpenClaw paths. Completed 2026-04-23 with real local evidence in `04-LOCAL-PROBE-RESULTS.md`.
- [x] **Phase 5: Iterative codebase simplification** - Run /simplify iteratively over major source files (transport.py, mcp_server.py, bridge.py, reporter.py, and others) to reduce complexity, remove dead code, and improve readability. Final worktree verification passed on 2026-04-23 with a net -203 targeted-line reduction.
- [x] **Phase 6: MolmoSpaces api-semantic cleanup pilot** - Direct coding-agent cleanup demo over a fake/MolmoSpaces-shaped backend, private scorer, provenance-labeled artifacts, and harness gate. Completed 2026-05-07; cleanup-loop primitives remain `api_semantic` even after the later Phase 25 standalone Franka proof.
- [x] **Phase 7: MolmoSpaces prompt-driven cleanup demo** - Prompt `帮我整理这个房间` drives a public-only cleanup policy through the cleanup tool loop, without private-manifest planner access. Completed 2026-05-07; primitive execution remains `api_semantic`.
- [x] **Phase 8: MolmoSpaces real subprocess cleanup** - Prompt `帮我整理这个房间` runs through the public cleanup loop against upstream `procthor-10k-val` scene 0 loaded by the isolated Python 3.11 MolmoSpaces runtime. Completed 2026-05-07; `backend=molmospaces_subprocess`, primitive execution remains `api_semantic`; later Phase 25 proves standalone Franka planner execution but not cleanup-loop integration.
- [x] **Phase 9: MolmoSpaces FPV room plausibility** - Target-facing RBY1M FPV and same-room visual gates for focused manipulation steps. Completed 2026-05-08.
- [x] **Phase 10: MolmoSpaces semantic substeps** - Object-level cleanup substeps, fridge open/place-inside semantics, and report timeline improvements. Completed 2026-05-08.
- [x] **Phase 11: MolmoSpaces held-object carry visuals** - Held objects visually travel with RBY1M during semantic cleanup navigation. Completed 2026-05-08.
- [x] **Phase 12: MolmoSpaces current-contract agent bridge** - FastMCP bridge for Codex, Claude Code, and OpenClaw Gateway on the current five-object cleanup contract. Completed 2026-05-08.
- [x] **Phase 13: MolmoSpaces agent bridge visual results** - Current-contract agent bridge reports include robot-view images and semantic mid-phase rows. Completed 2026-05-08.
- [x] **Phase 14: MolmoSpaces real-world cleanup harness** - ADR-0003 public/private contract with Agent View, Private Evaluation, deterministic sweep baseline, and visual parity. Completed 2026-05-09.
- [x] **Phase 15: MolmoSpaces Generated Mess Set scale** - ADR-0005 configurable hidden Generated Mess Set size; default ADR-0003 real-world evidence to at least 10 generated objects and score the whole set. Completed 2026-05-09.
- [x] **Phase 16: MolmoSpaces real-world agent MCP** - ADR-0006 MCP surface for the ADR-0003 public cleanup contract; no global `scene_objects` shortcut. Completed 2026-05-09.
- [x] **Phase 17: MolmoSpaces real-world agent dogfood** - ADR-0007 direct coding-agent dogfood kit and clean-run checker for the ADR-0003 MCP surface. Completed 2026-05-09.
- [x] **Phase 18: MolmoSpaces real-world OpenClaw dogfood** - ADR-0008 OpenClaw Gateway viability on the ADR-0003 MCP surface. Completed 2026-05-09 with a synthetic Gateway clean run; real visual Gateway evidence remains a follow-up.
- [x] **Phase 19: MolmoSpaces real-world OpenClaw visual evidence** - ADR-0010 real MolmoSpaces/RBY1M visual report evidence for OpenClaw Gateway on the ADR-0003 MCP surface. Completed 2026-05-09; live Gateway evidence is minimum visual, not clean policy success.
- [x] **Phase 20: MolmoSpaces real-world OpenClaw clean policy** - ADR-0011 executable semantic-loop ordering for clean ADR-0003 OpenClaw policy evidence. Completed 2026-05-09.
- [x] **Phase 21: MolmoSpaces real-world advisory scoring** - ADR-0012 non-authoritative advisory scoring/model-check artifact for ADR-0003 cleanup reports. Completed 2026-05-09.
- [x] **Phase 22: MolmoSpaces real-world raw FPV perception** - ADR-0013 raw FPV-only observation evidence mode for ADR-0003 cleanup reports. Completed 2026-05-09.
- [x] **Phase 23: MolmoSpaces planner-backed manipulation proof gate** - ADR-0014 provenance/report/checker boundary for real planner-backed manipulation evidence. Completed 2026-05-09.
- [x] **Phase 24: MolmoSpaces planner runtime diagnostics** - ADR-0015 dependency/crash diagnostics for strict planner probe blockers. Completed 2026-05-09.
- [x] **Phase 25: MolmoSpaces planner headless renderer** - ADR-0016 probe-local EGL renderer adapter for strict Franka planner proof. Completed 2026-05-09.
- [x] **Phase 26: MolmoSpaces cleanup planner proof attachment** - ADR-0017 render strict standalone planner proof inside ADR-0003 cleanup reports while preserving `api_semantic` cleanup primitive provenance. Completed 2026-05-09.
- [x] **Phase 27: MolmoSpaces cleanup planner-backed primitive gate** - ADR-0018 per-subphase gate for real planner-backed cleanup primitive evidence before replacement work. Completed 2026-05-09.
- [x] **Phase 28: MolmoSpaces RBY1M CuRobo runtime gate** - ADR-0019 target-robot runtime readiness gate before planner-backed cleanup primitive replacement. Completed 2026-05-09.
- [x] **Phase 29: MolmoSpaces camera model policy cleanup** - ADR-0020 camera-derived model-policy cleanup over public raw FPV observations and the shared ADR-0003 report underlay. Completed 2026-05-09.
- [x] **Phase 30: MolmoSpaces report underlay consolidation** - ADR-0021 canonical report visual core and semantic subphase labels across MolmoSpaces cleanup demos. Completed 2026-05-09.
- [x] **Phase 31: MolmoSpaces RBY1M CuRobo warmup readiness** - ADR-0022 staged worker evidence for RBY1M/CuRobo JIT/config warmup before target execute-mode retry. Completed 2026-05-09; the local artifact remains blocked at `rby1m_config_import`.
- [x] **Phase 32: MolmoSpaces RBY1M CuRobo cache isolation** - ADR-0023 isolated Torch extension cache evidence for RBY1M/CuRobo warmup retries. Completed 2026-05-09; config import succeeds, execute mode blocks at `warp.torch`.
- [x] **Phase 33: MolmoSpaces RBY1M Warp compatibility** - ADR-0024 probe-local Warp API adapter and visible compatibility evidence before target execute-mode retry. Completed 2026-05-09; execute mode reaches `execute_policy_run` and blocks on CUDA OOM.
- [x] **Phase 34: MolmoSpaces RBY1M CUDA memory headroom** - ADR-0025 stage-local CUDA/PyTorch memory evidence for target execute-mode OOM before planner memory tuning or cleanup primitive replacement. Completed 2026-05-09; execute mode still blocks inside CuRobo trajectory planning before robot-state movement.
- [x] **Phase 35: MolmoSpaces RBY1M CuRobo memory profile** - ADR-0026 visible probe-local low-memory CuRobo retry profile for target execute-mode OOM. Completed 2026-05-09; strict standalone RBY1M/CuRobo planner-backed proof passes under the visible low-memory profile.
- [x] **Phase 36: MolmoSpaces shared semantic cleanup loop** - ADR-0027 shared object-level cleanup loop driver for current-contract and ADR-0003 demos before planner-backed primitive replacement. Completed 2026-05-09.
- [x] **Phase 37: MolmoSpaces planner cleanup bridge readiness** - ADR-0028 bridge evidence for target RBY1M/CuRobo proof plus cleanup primitive subphase provenance before actual primitive replacement. Completed 2026-05-09.
- [x] **Phase 38: MolmoSpaces planner-backed cleanup primitive executor** - ADR-0029 strict per-call executor seam for planner-backed cleanup subphases behind the shared semantic cleanup loop. Completed 2026-05-09.
- [x] **Phase 39: MolmoSpaces planner primitive target binding** - ADR-0030 object/target binding for planner primitive evidence before real object-specific executor wiring. Completed 2026-05-09.
- [x] **Phase 40: MolmoSpaces probe-backed cleanup primitive executor** - ADR-0031 adapter that converts only bound target RBY1M/CuRobo proof into cleanup primitive executor evidence. Completed 2026-05-09.
- [x] **Phase 41: MolmoSpaces planner probe cleanup binding** - ADR-0032 sampled-task binding diagnostics and exact-match cleanup primitive binding promotion in planner probe artifacts. Completed 2026-05-09.
- [x] **Phase 42: MolmoSpaces observed handle planner binding** - ADR-0033 private mapping from ADR-0003 observed handles to planner sampled-task aliases while preserving cleanup-facing IDs for executor matching. Completed 2026-05-09.
- [x] **Phase 43: MolmoSpaces bounded planner cleanup executor** - ADR-0034 opt-in wiring that lets a matching probe-backed proof drive bounded shared-loop cleanup subphases. Completed 2026-05-09; default and mismatched-proof runs remain `api_semantic`, and full multi-object planner-backed cleanup remains a follow-up.
- [x] **Phase 44: MolmoSpaces planner proof bundle cleanup** - ADR-0035 multiple bound proof attachments selected per observed handle/target so a full cleanup artifact can pass the existing planner primitive and bridge gates. Completed 2026-05-10; this proves artifact proof coverage, not live generation of every proof.
- [x] **Phase 45: MolmoSpaces report visual core contract** - ADR-0036 shared report visual-core checker plus ADR-0003 MCP robot-view semantic mapping reuse. Completed 2026-05-10; stale ignored reports now fail until regenerated with the shared visual core.
- [x] **Phase 46: MolmoSpaces planner proof request manifest** - ADR-0037 private manifest and local runner that turn completed ADR-0003 cleanup artifacts into executable bound planner proof requests. Completed 2026-05-10.
- [x] **Phase 47: MolmoSpaces planner proof request report view** - ADR-0038 shared report section that renders private planner proof requests while keeping Agent View clean. Completed 2026-05-10.
- [x] **Phase 48: MolmoSpaces planner proof bundle runner report** - ADR-0039 visual `report.html` for local proof-bundle runner command manifests. Completed 2026-05-10.
- [x] **Phase 49: MolmoSpaces planner proof bundle runner checker** - ADR-0040 checker for local proof-bundle runner manifest/report integrity. Completed 2026-05-10.
- [x] **Phase 50: MolmoSpaces MCP smoke shared semantic loop** - ADR-0041 current-contract and ADR-0003 MCP smoke demos reuse the shared semantic cleanup loop. Completed 2026-05-10.
- [x] **Phase 51: MolmoSpaces planner proof bundle runner harness** - ADR-0042 dry-run harness and verification recipe for repeatable proof-bundle runner command generation. Completed 2026-05-10.
- [x] **Phase 52: MolmoSpaces planner proof bundle cleanup rerun artifacts** - ADR-0043 cleanup rerun outputs are first-class runner manifest/report/checker artifacts. Completed 2026-05-10.
- [x] **Phase 53: MolmoSpaces planner proof bundle execute rerun** - ADR-0044 local-dev gate for executing proof bundles, rerunning cleanup, and checking final planner-backed cleanup readiness. Completed 2026-05-10 with explicit blocker: executed proofs do not yet promote cleanup primitive binding because sampled upstream tasks differ from requested cleanup aliases.
- [x] **Phase 54: MolmoSpaces bind proof probes to cleanup scene** - ADR-0045 proof-bundle commands carry the real cleanup scene XML and requested planner aliases into exact-scene probe sampling. Completed 2026-05-10 with explicit blocker: upstream RBY1M task sampling rejects the real cleanup objects with `HouseInvalidForTask` / robot placement infeasibility.
- [x] **Phase 55: MolmoSpaces proof bundle result feasibility report** - ADR-0046 executed proof-bundle runner manifests/reports summarize proof status, task-feasibility classification, cleanup binding promotion, blockers, proof report links, and planner views. Completed 2026-05-10; fallback selection for RBY1M-feasible cleanup objects remains next.
- [x] **Phase 56: MolmoSpaces proof request feasibility selection** - ADR-0047 proof-bundle runner can consume a prior result summary, skip requests already known task-feasibility blocked, and report fallback-required state. Completed 2026-05-10; fallback generation closed in Phase 57.
- [x] **Phase 57: MolmoSpaces proof request fallback generation** - ADR-0048 proof-bundle runner can generate private alternate planner-alias proof requests from prior task-feasibility-blocked source requests while keeping cleanup-facing IDs stable. Completed 2026-05-10; local execution of generated fallback requests remains next.
- [x] **Phase 58: MolmoSpaces generated fallback proof execution** - ADR-0049 generated fallback proof requests execute as local-dev evidence. Completed 2026-05-10; four generated probes produced required proof outputs but all timed out at `rby1m_config_import`, so planner-backed cleanup readiness remains blocked.
- [x] **Phase 59: MolmoSpaces plain semantic report labels** - ADR-0050 makes `nav, pick, nav, open?, place` the primary Cleanup Artifact Report vocabulary while preserving object/target/surface/inside as secondary role detail. Completed 2026-05-10.
- [x] **Phase 60: MolmoSpaces fallback timeout stage reporting** - ADR-0051 surfaces generated fallback timeout-stage evidence in proof-bundle result summaries, reports, and checker coverage. Completed 2026-05-10.
- [x] **Phase 61: MolmoSpaces fallback proof warmup** - ADR-0052 adds a visible RBY1M/CuRobo config-import warmup step to proof-bundle runner manifests, reports, and checker coverage. Completed 2026-05-10.
- [x] **Phase 62: MolmoSpaces warmed generated fallback proof execution** - ADR-0053 records local warmed generated fallback execution. Completed 2026-05-10; warmup gets through config import, and generated proofs now fail at task sampling with invalid planner alias names instead of timeout.
- [x] **Phase 63: MolmoSpaces exact-scene fallback alias validation** - ADR-0054 filters upstream/display aliases out of generated fallback proof commands while preserving skipped-alias evidence in runner manifests, reports, and checker coverage. Completed 2026-05-10.
- [x] **Phase 64: MolmoSpaces fallback runtime alias discovery** - ADR-0055 derives same-family runtime aliases from prior fallback KeyError valid-name lists and renders discovered aliases in proof-bundle runner reports. Completed 2026-05-10; local execution followed in Phase 65.
- [x] **Phase 65: MolmoSpaces discovered runtime fallback proof execution** - ADR-0056 executes discovered runtime-sibling fallback commands locally with RBY1M/CuRobo warmup. Completed 2026-05-10; all four commands reach task sampling, but none promote cleanup binding or emit planner views.
- [x] **Phase 66: MolmoSpaces fallback failed-candidate memory** - ADR-0057 carries prior discovered aliases forward while filtering prior non-root object aliases and task-feasibility-blocked alias pairs before generating new fallback proof commands. Completed 2026-05-10.
- [x] **Phase 67: MolmoSpaces filtered fallback proof execution** - ADR-0058 executes the remaining failed-candidate-filtered fallback commands locally. Completed 2026-05-10; both commands reach task sampling and fail as non-root bodies.
- [x] **Phase 68: MolmoSpaces fallback filter carry-forward** - ADR-0059 carries prior filtered aliases and filtered pairs forward so later runner passes do not regenerate known-bad candidates. Completed 2026-05-10.
- [x] **Phase 69: MolmoSpaces pickup root variant filter** - ADR-0060 filters object-side runtime aliases with nonzero variants before generating fallback proof commands. Completed 2026-05-10.
- [x] **Phase 70: MolmoSpaces prior proof evidence merge** - ADR-0061 lets the proof-bundle runner merge multiple prior manifests so alias discovery and failed-candidate memory are consumed together. Completed 2026-05-10.
- [x] **Phase 71: MolmoSpaces fallback exhaustion status** - ADR-0062 renders and checks generated fallback status, including exhausted no-command states. Completed 2026-05-10.
- [x] **Phase 72: MolmoSpaces fallback exhaustion blockers** - ADR-0063 renders and checks blocker summaries for exhausted generated fallback pools. Completed 2026-05-10.
- [x] **Phase 73: MolmoSpaces pickup root alias normalization** - ADR-0064 normalizes non-root object runtime aliases to variant-0 pickup root aliases before blocker classification. Completed 2026-05-10.
- [ ] **Phase 3: Isaac Lab migration** - Humanoid + multi-embodiment nav via VLM → RL locomotion (deferred indefinitely)

## Phase Details

<details>
<summary>✅ Phase 1: Core simulation + games — SHIPPED</summary>

### Phase 1: Core simulation + games
**Goal**: Validate the core hypothesis — a VLM with FPV + overhead + structured state can navigate and play competition/cooperation games on real AI2-THOR scenes.
**Depends on**: Nothing (first phase)
**Requirements**: CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06
**Success Criteria** (what must be TRUE):
  1. A user can run `python examples/single_agent_explore.py` and see a VLM-driven agent produce a GIF of movement through `FloorPlan201`.
  2. A user can run `python examples/territory_game.py --agents 3` and watch three VLM-driven agents compete for grid cells, with a final report showing per-agent scores and a GIF.
  3. A user can run `python examples/coverage_game.py --agents 3` and watch agents cooperatively explore a scene, with coverage fraction and per-agent contribution in the final report.
  4. Replay artifacts (numbered frames + `replay.json` + summary report) are produced deterministically for every run.
**Plans**: 6 plans (historical, retrofit from issues 1–6 in `docs/issues-roadmap.md`)

Plans:
- [x] 01-01: AI2-THOR multi-agent engine wrapper (`roboclaws/core/engine.py`)
- [x] 01-02: Pluggable VLM provider protocol (`roboclaws/core/vlm.py`) — Mock / OpenAI / Anthropic / Kimi
- [x] 01-03: Overhead visualizer + frame composite (`roboclaws/core/visualizer.py`)
- [x] 01-04: Territory game (`roboclaws/games/territory.py`, `examples/territory_game.py`)
- [x] 01-05: Coverage game (`roboclaws/games/coverage.py`, `examples/coverage_game.py`)
- [x] 01-06: Game replay recorder (`roboclaws/core/replay.py`)
**UI hint**: yes

### Phase 1.5: CI + dev topology
**Goal**: Keep the demo continuously alive on GitHub Pages and codify the cloud-vs-local developer workflow.
**Depends on**: Phase 1
**Requirements**: CI-01, CI-02
**Success Criteria** (what must be TRUE):
  1. Every push to `main` publishes fresh Layer 1 + Layer 2 GIFs + reports to `miaodx.github.io/roboclaws/`.
  2. `lint-and-mock` runs on every push + PR and gates merges on ruff + format + pytest + mock-engine HTML demo.
  3. Contributors can tell at a glance from `CLAUDE.md` whether a task belongs in a cloud session or a local `local-dev` session.
**Plans**: 2 plans (historical, retrofit)

Plans:
- [x] 015-01: Headless-AI2-THOR CI workflow (`.github/workflows/ci.yml`) with Xvfb + `~/.ai2thor/` cache + `publish-pages` job
- [x] 015-02: Cloud-vs-local workflow documentation (CLAUDE.md § Cloud vs local, `docs/contributing.md`, `local-dev` issue template in #50)
**UI hint**: yes

### Phase 2: OpenClaw Gateway bridge (original)
**Goal**: Route one simulated agent through a local OpenClaw Gateway and prove the end-to-end path produces a visible artifact.
**Depends on**: Phase 1.5
**Requirements**: OC-01 (initial transport attempt — corrected in Phase 2.1)
**Success Criteria** (what must be TRUE):
  1. A contributor can run `scripts/openclaw-bootstrap.sh` followed by `examples/openclaw_demo.py` on a workstation and get a report.html for one OpenClaw-driven agent.
  2. A dedicated `openclaw-smoke` CI job publishes a `report-openclaw` artifact to `miaodx.github.io/roboclaws/openclaw/demo/` on push to main.
  3. The Gateway image is pinned to `ghcr.io/openclaw/openclaw:2026.4.14` (date-shaped tag, `OPENCLAW_IMAGE` override available).
**Plans**: Historical — superseded by Phase 2.1 transport correction.

Plans:
- [x] 02-01: First-pass OpenClaw bridge (used `/tools/invoke` — wrong endpoint, see Phase 2.1 retrospective)
- [x] 02-02: Standalone `examples/openclaw_demo.py` + `scripts/openclaw-bootstrap.sh` + `openclaw-smoke` CI job
- [x] 02-03: Pin Gateway image to `:2026.4.14` (DEC-phase-2-gateway-pinned-image)

### Phase 2.1: Transport correction (INSERTED)
**Goal**: Replace the wrong-endpoint `/tools/invoke` transport with the actually-working OpenAI-compatible `/v1/chat/completions`, plus per-agent isolation via named-agent routing.
**Depends on**: Phase 2
**Requirements**: OC-01 (corrected)
**Success Criteria** (what must be TRUE):
  1. `OpenClawProvider.get_action` routes to `model = "openclaw/<agentId>"` and the request hits `POST /v1/chat/completions`.
  2. Each named Gateway agent owns its own workspace, `SOUL.md`, `auth-profiles.json`, and MEMORY — no cross-agent leakage.
  3. Frames flow inline as base64 `data:` URLs with no bind mount; the Railway/remote-Gateway path is no longer bind-mount-bound.
**Plans**: Historical — see `docs/retrospectives/phase-2.1.md` (7 tasks T1–T7).

Plans:
- [x] 021-01: Swap transport to `/v1/chat/completions` with `model="openclaw/<agentId>"` routing (DEC-phase-2.1-transport-is-chat-completions, DEC-phase-2.1-named-agent-routing)
- [x] 021-02: Inline base64 image transport — remove bind mount, remove `.openclaw-tmp` (DEC-phase-2-inline-image-transport)
- [x] 021-03: Add real-upstream probe pre-merge (live-probe gate hardened into `feedback_live_probe_gate.md`)

### Phase 2.2: Long-running OpenClaw games
**Goal**: Run the territory and coverage games end-to-end through the Gateway with per-agent SOULs for visible personality differentiation.
**Depends on**: Phase 2.1
**Requirements**: OC-02, OC-03
**Success Criteria** (what must be TRUE):
  1. `make openclaw-territory` produces a GIF where agent trails are visibly tinted by SOUL color (aggressive=red, defensive=blue).
  2. `make openclaw-coverage` runs cleanly with `AGENT_SOULS=cooperative,cooperative` + `PERSONALITY_PROBE=0` and publishes a coverage report.
  3. Two new CI jobs (`territory-openclaw-smoke`, `coverage-openclaw-smoke`) publish Layer 3 tiles to `miaodx.github.io/roboclaws/openclaw/{territory,coverage}/`.
  4. Bootstrap's personality-divergence probe fails fast (exit 5) when two named agents report the same strategy hash, unless explicitly skipped.
**Plans**: Historical — see `docs/retrospectives/phase-2.2.md` (tasks T17–T27).

Plans:
- [x] 022-01: `AGENT_SOULS` distribution in `scripts/openclaw-bootstrap.sh` with fail-fast validation + personality probe
- [x] 022-02: SOUL overlay in visualizer (badges + tinted trails) with `tests/test_visualizer_soul_overlay.py`
- [x] 022-03: Add `territory-openclaw-smoke` + `coverage-openclaw-smoke` CI jobs + Layer 3 tiles in README
**UI hint**: yes

### Phase 2.3: Gateway digest pin — DECLINED
**Goal**: *Evaluate* whether to pin the Gateway image by `sha256:` digest instead of `:2026.4.14` tag.
**Depends on**: Phase 2.2
**Requirements**: none (pure ops decision)
**Success Criteria** (what must be TRUE):
  1. A documented decision exists on record (either "pin by digest" + PR, or "decline with rationale" + ADR).
**Outcome**: DECLINED 2026-04-20. Keep date-shaped `:2026.4.14`. LOCKED ADR recorded in `PROJECT.md` as `DEC-phase-2.3-decline-digest-pin`. One-click rollback digest preserved for emergency use:
`sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`
**Plans**: 1 plan

Plans:
- [x] 023-01: Write + record LOCKED ADR declining digest pin (`docs/retrospectives/phase-2.3.md`)

</details>

#### ✅ v1.1 Better Views (Phase 2.4) — Closed by Decision

**Milestone Goal:** Decide whether a richer per-step view (structured
grid-overhead, optionally plus chase-cam) produces measurably better VLM
play across territory / coverage / navigation, with defensible statistics
and ≤$20 spend.

### Phase 2.4: Better Views
**Goal**: Standardize the runtime on `map-v2+chase` and treat the earlier `baseline` / `map-v2` / `map-v2+chase` A/B study as historical planning context rather than an active execution requirement.
**Depends on**: Phase 2.2. Issue #52 prereqs (image-payload contract + coverage semantics) were shipped pre-ingest in commit `ddfb523` (2026-04-15); both initial ingest WARNINGs verified stale and resolved 2026-04-20 — see `.planning/INGEST-CONFLICTS.md` "UPDATE 2026-04-20" header.
**Requirements**: A-03, A-04 (A-01 and A-02 shipped pre-ingest, marked Complete in REQUIREMENTS.md traceability)
**Update (2026-04-24):** The multi-variant experiment plan is now historical only. Product/runtime direction is locked to `map-v2+chase`; `baseline` and `map-v2` are no longer supported runtime modes on the main examples.
**Success Criteria** (what must be TRUE):
  1. The main example drivers (`openclaw_demo.py`, `territory_game.py`, `coverage_game.py`) use a fixed FPV + structured-overhead + chase-cam prompt contract with no user-facing `--views` selection.
  2. Shared view helpers and the shipped Phase 2.6 autonomous path continue to use the same `map-v2+chase` family.
  3. `docs/view-experiment-2026-04.md` records that the old A/B/C sweep was superseded and that the supported runtime variant is now `map-v2+chase`.
**Plans**: 4 plans. Phase 2.4 was ingested into GSD on 2026-04-21. Plans `02.4-01` through `02.4-03` landed the shared view system; `02.4-04` is now historical because the product decision was made directly.

Plans:
- [x] 02.4-01: Shared view primitives + `examples/openclaw_demo.py --views ...` rollout (single-agent OpenClaw first)
- [x] 02.4-02: Territory + coverage rollout onto the shared view builder
- [x] 02.4-03: `NvidiaProvider` + `examples/view_experiment.py` harness with wallet gates
- [⛔] 02.4-04: Analysis script + local-dev sweep + `docs/view-experiment-2026-04.md` decision record — superseded 2026-04-24 when runtime direction was locked to `map-v2+chase` only

**Status update (2026-04-24):** The repo had already drifted toward `map-v2+chase` as the only real runtime path, including the shipped Phase 2.6 autonomous flow. Rather than keep reviving `baseline` / `map-v2` just to satisfy the old study, the product direction is now explicit: the supported prompt family is `map-v2+chase` only. The analysis tooling remains in-tree for historical data, but the old multi-variant sweep is no longer an active phase gate.
**UI hint**: yes

#### ⛔ v1.2 Autonomous OpenClaw Loop — Phase 2.5 SUPERSEDED by Phase 2.6

### Phase 2.5: Autonomous OpenClaw loop (v1 — curl/exec contract) — SUPERSEDED
**Status**: SUPERSEDED 2026-04-21 by Phase 2.6. Plans were drafted in `docs/plans/phase-2.5-autonomous-nav.md` and the 8 plan files exist under `.planning/phases/02.5-.../`, but none were executed. Kept as a lesson — **do not resurrect**.
**Why superseded**: The contract was "agent calls `observe`/`move`/`done` by shelling out to `curl http://host.docker.internal:18788/...` from the Gateway's `exec` tool, and uses the generic `image` tool for frames." Local probing on 2026-04-21 (see `docs/retrospectives/openclaw-kimi-provider-debug-2026-04-21.md` + the Phase 2.6 spike findings) proved this architecture is structurally wrong:
  - Gateway's `exec` allowlist rejects the `curl | python3 decode.py` patterns the agent naturally emits (`exec preflight: complex interpreter invocation detected`)
  - Generic `image` tool aborts on workspace-local media paths and rejects `/tmp/...`
  - Prompt-level steering ("don't use exec", "don't use /tmp") doesn't hold under long runs — the agent drifts back to coding-agent defaults
  - Both `custom` and `plugin` Kimi paths ended on Gateway `read_timeout` (wall_clock)
**Replacement**: Phase 2.6 rebuilds the same user-visible goal on a first-class MCP tool surface + `profile: minimal` tool allowlist. See below.
**Original goal (preserved for reference)**: Invert the OpenClaw integration. Instead of pushing FPV/overhead into the agent per step, let the agent drive — one kickoff call with a long wall-clock budget, and the agent pulls `observe`/`move`/`done` as needed. Add stdin-based human interjection.
**Original plans (archived, not executed)**:
- [⛔] 025-01 (T49): Pre-build spike — long-poll + tool-format de-risk — **superseded by 2.6 MCP spike (2026-04-21)**
- [⛔] 025-02 (T50): `roboclaws/openclaw/sim_server.py` — HTTP tool server — **superseded by 2.6 MCP server**
- [⛔] 025-03 (T51): `skills/ai2thor-navigator/SKILL.md` tool declarations (curl recipes) — **superseded by 2.6 thin SKILL.md**
- [⛔] 025-04 (T52): `OpenClawBridge.start_run(...)` — kickoff + blocking wait — **carries forward into 2.6 with minor adjustments**
- [⛔] 025-05 (T53): `examples/openclaw_nav_autonomous.py` — stdin reader + SIGINT teardown — **carries forward into 2.6; drop curl prompt block**
- [⛔] 025-06 (T53-bis): `scripts/openclaw-bootstrap.sh` updates (SIM_SERVER_URL, --add-host) — **superseded by 2.6 bootstrap that seeds `mcp.servers` + `tools.profile = "minimal"` before first start**
- [⛔] 025-07 (T54): `scripts/render_autonomous_replay.py` — replay.gif + report.html — **carries forward into 2.6 unchanged**
- [⛔] 025-08 (T55): Local-dev validation (6 probes) — **carries forward into 2.6 as live-probe gate**

#### ✅ v1.2 Autonomous OpenClaw Loop (Phase 2.6) — Shipped

### Phase 2.6: Autonomous OpenClaw loop (v2 — MCP tool surface)
**Goal**: Same user-visible outcome as superseded Phase 2.5 (single-agent autonomous nav + human steer), rebuilt on the architecture the 2026-04-21 spike proved works: `observe` / `move` / `done` as first-class MCP tools served over streamable-http, agent running under Gateway tool `profile: minimal` so it literally cannot fall back to `exec`/`curl`/generic-`image`.
**Depends on**: Phase 2.2 (OpenClawBridge + skill infra). Runs in parallel to Phase 2.4 — different architectural bet; does not share code paths.
**Requirements**: A-06 (agent-driven tool loop — see REQUIREMENTS.md)
**Source**: `.planning/phases/02.6-openclaw-mcp-tools-integration/02.6-CONTEXT.md` + `02.6-SPIKE-FINDINGS.md`
**Success Criteria** (what must be TRUE):
  1. `python examples/openclaw_nav_autonomous.py --scene FloorPlan201 --max-moves 50 --wall-budget 300` runs end-to-end locally; agent calls the MCP `observe` tool within 30 s of kickoff, takes at least one `move`, terminates via `done` or wall-clock, produces `replay.gif` + `report.html`.
  2. Gateway log for the run shows **zero** `exec`, `curl`, or generic `image`-tool calls from the agent; only `<server-prefix>__observe` / `__move` / `__done` calls appear.
  3. Human interjection (stdin line) appears in `trace.jsonl` on a tool response, in `report.html`'s tool-call log, and the agent's subsequent reasoning references it.
  4. The autonomous run's per-turn prompt-token overhead is materially smaller than under the coding profile (target ≤ 60% of coding profile). Revised 2026-04-21 from ≤50% after Probe 6 measured 0.568 against Gateway image `:2026.4.14`; spike's 0.408 was measured against an earlier Gateway config whose `coding` profile was 26% larger (15,396 vs 11,335 tokens). The 43% reduction shown by the live probe is still a real, material win — the revised threshold tracks actual Gateway reality rather than the spike baseline.
  5. `scripts/openclaw-bootstrap.sh` seeds `mcp.servers.<name>` and `agents.list[<n>].tools.profile = "minimal"` **before first container start**, so no post-start SIGUSR1 restart is required to enable the tool surface.
  6. Back-to-back runs against a long-lived Gateway show a fresh agent state on the second run (per-run workspace reset works — regression guard for `[fixed-session-prefix-leaks-memory]`).
**Plans**: 7 plans (drafted 2026-04-21 after spike; renamed to `-PLAN.md` suffix and executed same day).

**Follow-up (2026-04-22):** The Phase 2.4 `baseline` / `map-v2` / `map-v2+chase` view family now also runs through the shipped autonomous MCP path. Local Kimi + AI2-THOR smoke artifacts:
- `output/openclaw-autonomous-mapv2chase-smoke-rerun/` — real 3-move `done` run with shared view bundle
- `output/openclaw-autonomous-mapv2chase-summaryfix-smoke/` — post-trace-fix smoke confirming `summary.json` reports `observe/move/done` counts correctly

**Remaining artifact gap (tracked in Phase 2.7):** Current autonomous artifacts persist tool traffic and the final assistant message, but not the intermediate assistant transcript from the Gateway run.

Plans:
- [x] 02.6-01: In-process FastMCP server (`roboclaws/openclaw/mcp_server.py`) with observe/move/done over streamable-http
- [x] 02.6-02: `scripts/openclaw-bootstrap.sh` seeds MCP server + `profile: minimal` pre-`docker run`
- [x] 02.6-03: Shrink `skills/ai2thor-navigator/SKILL.md` to MCP-era form (no curl/exec/generic-image advice)
- [x] 02.6-04: Rewire `examples/openclaw_nav_autonomous.py` to MCP contract
- [x] 02.6-05: Delete superseded HTTP sim_server + its tests
- [x] 02.6-06: Live-probe gate — 5/6 probes PASS; Probe 6 ratio 0.568 (SC#4 threshold revised to ≤0.60; see Probe 6 notes in `02.6-LOCAL-PROBE-RESULTS.md`)
- [x] 02.6-07: Docs update — retrospective + `docs/openclaw-local.md` + `docs/openclaw-gateway-internals.md`
**UI hint**: yes

#### 📋 v1.3 Autonomous Transcript Visibility (Phase 2.7) — Planned

### Phase 2.7: Autonomous OpenClaw intermediate-message capture
**Goal**: Preserve and display the assistant's mid-run messages in the shipped autonomous MCP loop so `report.html` shows not just tool traffic and the terminal answer, but the in-between reasoning/messages as they happen. Compare both acquisition paths first: true Gateway streaming vs terminal-body/fallback capture. Prefer streaming if the real Gateway surface supports it cleanly and reliably.
**Depends on**: Phase 2.6 (shipped MCP tool loop). Additive follow-up; does not replace the tool surface or reopen the Phase 2.5 curl/exec dead end.
**Requirements**: Follow-up to A-06 (same autonomous loop, improved transcript visibility for operators)
**Source**: `.planning/phases/02.7-openclaw-intermediate-message-capture/02.7-CONTEXT.md`
**Success Criteria** (what must be TRUE):
  1. A real-Gateway probe records the exact behavior of both routes on 2026-04-22-or-later: whether `/v1/chat/completions` streaming emits usable intermediate assistant text/events, and what terminal-body-only capture can recover if streaming is unavailable. The decision is written down with concrete payload evidence.
  2. `examples/openclaw_nav_autonomous.py` persists a step-aligned assistant transcript into artifacts for the chosen primary route, with an additive schema change only: old traces remain renderable and new traces include intermediate assistant messages with timestamps and source metadata (`stream` vs `terminal-body`).
  3. `scripts/render_autonomous_replay.py` + `report.html` show the transcript alongside tool traffic so an operator can step through the run and see what the assistant said between `observe` / `move` / `done`.
  4. Local validation against a real Gateway + real Kimi confirms the transcript path works on a live run, and the write-up records whether streaming is production-viable or whether the repo should stay on a fallback capture path for now.
**Plans**: 4 plans. Plan 01 is deliberately a capability spike before implementation; do not assume the streaming surface exists just because the user prefers it.

Plans:
- [ ] 02.7-01: Real-Gateway capability spike — compare streaming events vs terminal-body-only capture and lock the acquisition strategy
- [ ] 02.7-02: Bridge/runtime persistence — capture intermediate assistant messages additively into `trace.jsonl` + `run_result.json`
- [ ] 02.7-03: Replay/report surfacing — render transcript panels and message/timestamp audit in `report.html`
- [ ] 02.7-04: Local-dev validation + write-up — confirm live behavior and document the chosen path
**UI hint**: yes

#### 📋 v1.4 Split-model navigation (Phase 2.8) — Planned

### Phase 2.8: Split-model navigation
**Goal**: Enable text-only reasoning models (e.g. mimo-v2.5-pro, mimo-v2.5) to navigate autonomously in OpenClaw by intercepting image-bearing `roboclaws__observe` tool results at the MCP server layer, converting them to text descriptions via a vision model (mimo-v2-omni), and forwarding only text to the text-only main model. Bonus path: probe whether OpenClaw's tool-profile system can expose the generic `image` tool alongside `roboclaws__*` without the exec/curl drift risk seen in Phase 2.5.
**Depends on**: Phase 2.6 (shipped MCP tool loop + `profile: minimal`). Phase 2.8 is additive; it does not reopen the push-model or exec/curl contracts.
**Requirements**: A-07
**Success Criteria** (what must be TRUE):
  1. An autonomous navigation run completes successfully with a text-only main model (mimo-v2.5-pro or mimo-v2.5) as `MODEL` and mimo-v2-omni as the vision intermediary — the agent calls `roboclaws__observe`, receives a text description of the scene, and uses it to choose `roboclaws__move` actions without ever receiving raw image bytes.
  2. The MCP server (or a thin wrapper) performs the vision→text conversion transparently: the agent's tool surface is unchanged (`observe`/`move`/`done`), but observe now returns text when the caller is a text-only model.
  3. `make mimo-pro chat` and `make mimo chat` produce working interactive sessions where navigation is demonstrably driven by the text description path.
  4. `docs/openclaw-local.md` is updated to document the split-model configuration with a verified-on probe entry.
  5. (Stretch) Probe whether `profile: coding` with a constrained prompt or a custom `alsoAllow` profile can expose `image` without exec/curl drift — write-up included regardless of outcome.
**Plans**: TBD

Plans:
- [ ] 02.8-01: Capability spike — profile probe (`messaging` / `alsoAllow`) + MCP intercept design decision
- [ ] 02.8-02: MCP vision-bridge — implement image→text intercept in `roboclaws__observe`
- [ ] 02.8-03: Makefile + bootstrap wiring — `make mimo-pro chat` / `make mimo chat` end-to-end
- [ ] 02.8-04: Local-dev validation + doc update
**UI hint**: no

#### ✅ v1.6 Iterative Codebase Simplification (Phase 5) — Completed

### Phase 5: Iterative codebase simplification
**Goal**: Run `/simplify` iteratively over the major source files to reduce complexity, remove dead code, and make the codebase more intuitive. Each file pass is reviewed and committed atomically; tests must stay green after every commit.
**Depends on**: Phase 4 (regression harnesses provide the safety net for structural changes)
**Requirements**: None (quality/maintainability work)
**Success Criteria** (what must be TRUE):
  1. All targeted files pass `/simplify` review with no high-severity findings remaining.
  2. Every per-file commit is atomic and `pytest` stays green throughout.
  3. No behavioral regressions — existing example runners and CI jobs continue to pass.
  4. Net line count across targeted files is reduced or held flat (no new abstractions added beyond what simplification requires).
**Plans**: 9 plans

Plans:
- [x] 05-01-PLAN.md — Simplify roboclaws/core/visualizer.py
- [x] 05-02-PLAN.md — Simplify roboclaws/openclaw/mcp_server.py
- [x] 05-03-PLAN.md — Simplify roboclaws/core/reporter.py
- [x] 05-04-PLAN.md — Simplify roboclaws/openclaw/transport.py (already-leaner pass)
- [x] 05-05-PLAN.md — Simplify roboclaws/games/coverage.py and territory.py
- [x] 05-06-PLAN.md — Simplify roboclaws/core/vlm.py, providers/kimi.py, and providers/openai.py
- [x] 05-07-PLAN.md — Simplify bridge.py, vision_bridge.py, views.py, and replay.py
- [x] 05-08-PLAN.md — Simplify examples/openclaw_demo.py, openclaw_interactive.py, and openclaw_nav_autonomous.py
- [x] 05-09-PLAN.md — Simplify examples/coverage_game.py and territory_game.py
**UI hint**: no

#### 📋 v2.0 Isaac Lab (Phase 3) — Deferred indefinitely

### Phase 3: Isaac Lab migration
**Goal**: Migrate from AI2-THOR to Isaac Lab for humanoid (Unitree G1) and multi-embodiment navigation, with a two-level architecture (OpenClaw VLM planner at 1–5 Hz producing `(vx, vy, ωz)` consumed by a pre-trained RL locomotion policy at 200 Hz).
**Depends on**: Phase 2.4 (decision record from view-experiment A/B — the winning view variant informs what Phase-3 scenes need to render) **and** availability of indoor USD scenes + GPU hardware + 1–2 weeks of ramp-up time. (Original dep on old-Phase-2.5 "ship winning view" is obsolete — that phase was replaced by the autonomous-nav track; the underlying decision record still lives in Phase 2.4.)
**Requirements**: P3-01, P3-02, P3-03, P3-04, P3-05 (v2 requirements)
**Success Criteria** (what must be TRUE):
  1. A contributor can run an Isaac Lab demo of one Unitree G1 navigating an indoor USD scene under OpenClaw-VLM high-level control + a pre-trained RL locomotion policy.
  2. The ROSClaw (or equivalent direct-Python) bridge carries `(vx, vy, ωz)` commands from the VLM planner to the locomotion policy at a verified rate (≥1 Hz planner, ≥200 Hz locomotion).
  3. The published Layer 3 demo matrix adds a Phase-3 tile showing the Isaac Lab run alongside the AI2-THOR tiles.
**Plans**: TBD — explicitly deferred per `docs/technical-design.md` § Phase 3. Revisit when GPU + indoor USD scenes are available.

Plans:
- [ ] 03-01: Ramp Isaac Lab toolchain (AGILE, COMPASS, GR00T N1.6) on target GPU
- [ ] 03-02: Build or source an indoor USD scene compatible with G1 navigation
- [ ] 03-03: Wire OpenClaw VLM planner ↔ RL locomotion bridge
- [ ] 03-04: Integrate object-interaction action set (P3-05)
- [ ] 03-05: Publish Phase-3 tile in the live demo matrix

#### ✅ v1.5 Refactor Regression Safety (Phase 4) — Complete

### Phase 4: Refactor regression harnesses for VLM, territory/coverage, and OpenClaw
**Goal**: Make large refactors safer by adding behavior-regression harnesses at three layers: deterministic contract fixtures, capture-style run harnesses, and threshold-based analyzers for the direct VLM path, the territory/coverage games, and the shipped OpenClaw paths.
**Depends on**: Phase 2.4 (current root `PLAN.md` remains the source draft for harness patterns and validation expectations) and Phase 2.6 (shipped MCP/trace/report contracts). Phase 3 is unrelated and remains deferred.
**Requirements**: A-08
**Source**: `PLAN.md`, `.planning/STATE.md`, `examples/view_experiment.py`, `scripts/analyze_view_experiment.py`, `scripts/generate_demo_report.py`, `tests/fixtures/trace_schema_reference.json`
**Success Criteria** (what must be TRUE):
  1. Cloud-safe deterministic regression coverage freezes the critical contracts: game termination semantics, prompt image counts/order, replay summary shape, OpenClaw trace/schema key-sets, and transport/runtime invariants.
  2. A thin capture harness writes append-only `results.jsonl` rows plus full replay dirs for named suites covering direct-VLM territory/coverage and OpenClaw demo/game paths, reusing existing example runners rather than reimplementing loops.
  3. A separate compare/analyze harness can diff a baseline run set against a candidate refactor run set, pairing on stable coordinates (`suite`, `scene`, `seed`, `game`, `backend`) and failing on threshold breaches instead of exact step-by-step equality.
  4. The harness surface follows the repo's current best practices: small CLI runners, separate analyzers, monkeypatchable suite registries for tests, and tiny committed reference fixtures only.
**Plans**: 4 plans

Plans:
- [x] 04-01: Contract fixtures + suite scaffold
- [x] 04-02: Direct-VLM and game capture suites
- [x] 04-03: OpenClaw capture suites
- [x] 04-04: Compare/analyze thresholds + operator workflow
**Status update (2026-04-23):** `roboclaws/regression.py`, `scripts/capture_refactor_regression.py`, `scripts/analyze_refactor_regression.py`, `docs/refactor-regression.md`, and the Phase 4 contract/analyzer tests are implemented. Real local captures now exist for `explore-vlm`, `openclaw-demo`, and `openclaw-autonomous`; the first probe cycle and threshold/harness adjustments are recorded in `.planning/phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md`.

#### ✅ v1.7 MolmoSpaces Cleanup Pilot (Phase 6) — Complete

### Phase 6: MolmoSpaces api-semantic cleanup pilot
**Goal**: Prove the first `帮我收拾这个房间` artifact loop without overstating robotics capability: a direct coding-agent MCP/demo path can inspect a messy room, move objects through `api_semantic` operations, score against a private manifest, and render trace/report/run-result artifacts that clearly label primitive provenance.
**Depends on**: `docs/plans/molmospaces-manipulation-spike.md` local capability spike (2026-05-07), Phase 2.6 MCP/trace/report lessons, and Phase 4 harness conventions.
**Scope**: fake/MolmoSpaces-shaped backend contracts, private scoring manifest, `api_semantic` cleanup primitives, deterministic scripted demo, report rendering, and harness/verify gates. No top-level MolmoSpaces import; no repo Python upgrade; no claim of real planner-backed manipulation.
**Plans**: `.planning/phases/06-molmospaces-api-semantic-cleanup/`

- [x] 06-01: Scenario contracts, private manifest, scorer
- [x] 06-02: API-semantic backend and direct MCP-style tool contract
- [x] 06-03: Demo runner, report rendering, harness recipe
- [x] 06-04: Verification, provenance write-up, and shipped-state update
**Status update (2026-05-07):** Phase 6 is implemented and verified. The new
`roboclaws/molmo_cleanup/` package, `examples/molmospaces_cleanup_demo.py`, and
`just harness::molmo-cleanup` produce a deterministic cleanup artifact with
`cleanup_status=success`, `restored_count=5/5`, and
`primitive_provenance=api_semantic`. Verification evidence is recorded in
`.planning/phases/06-molmospaces-api-semantic-cleanup/06-VERIFICATION.md`.
**UI hint**: no

#### ✅ v1.8 MolmoSpaces Prompt Cleanup (Phase 7) — Complete

### Phase 7: MolmoSpaces prompt-driven cleanup demo
**Goal**: Prove `帮我整理这个房间` can drive the cleanup loop from public room state and tool responses rather than private-manifest scripted targets.
**Depends on**: Phase 6 cleanup scaffold.
**Scope**: public cleanup policy, prompt-mode demo runner, prompt harness/verify gate, and source-plan update. Primitive execution remains `api_semantic`; no real robot planner, OpenClaw, or top-level MolmoSpaces import.
**Plans**: `.planning/phases/07-molmospaces-prompt-driven-cleanup-demo/`

- [x] 07-01: Public cleanup policy
- [x] 07-02: Prompt demo harness and verify gate
**Status update (2026-05-07):** `just harness::molmo-prompt-cleanup` runs
`examples/molmospaces_cleanup_demo.py --planner public_heuristic --task
"帮我整理这个房间"` and produces `cleanup_status=success`,
`restored_count=5/5`, `planner=public_heuristic`, and
`planner_uses_private_manifest=false`. Verification evidence is recorded in
`.planning/phases/07-molmospaces-prompt-driven-cleanup-demo/07-VERIFICATION.md`.
**UI hint**: no

## Progress

**Execution Order:**
Active/planned chain: 1 → 1.5 → 2 → 2.1 → 2.2 → 2.3 → 2.4 → 2.6 → 2.7 → 2.8 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14 → 15 → 16 → 17 → 18 → 19 → 20 → 21 → 22 → 23 → 24 → 25 → 26 → 27 → 28
(Phase 2.5 superseded 2026-04-21 — skipped in execution order; Phase 3 remains explicitly deferred and is not on the near-term chain.)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Core simulation + games | v1.0 | 6/6 | Complete | 2026-04 (pre-Phase-2) |
| 1.5. CI + dev topology | v1.0 | 2/2 | Complete | 2026-04 (pre-Phase-2) |
| 2. OpenClaw Gateway bridge (original) | v1.0 | 3/3 | Complete | 2026-04 |
| 2.1. Transport correction | v1.0 | 3/3 | Complete | 2026-04 |
| 2.2. Long-running OpenClaw games | v1.0 | 3/3 | Complete | 2026-04-16 |
| 2.3. Gateway digest pin | — | 1/1 | Declined | 2026-04-20 |
| 2.4. View-experiment A/B | v1.1 | 3/4 | Active; local-dev sweep + decision record pending (#70) | - |
| 2.5. Autonomous OpenClaw loop (v1 curl/exec) | v1.2 | 0/8 | Superseded by 2.6 | 2026-04-21 |
| 2.6. Autonomous OpenClaw loop (v2 MCP) | v1.2 | 7/7 | Complete | 2026-04-21 |
| 2.7. Autonomous OpenClaw intermediate-message capture | v1.3 | 0/4 | Planned | - |
| 2.8. Split-model navigation | v1.4 | 0/TBD | Planned | - |
| 4. Refactor regression harnesses for VLM, territory/coverage, and OpenClaw | v1.5 | 4/4 | Complete | 2026-04-23 |
| 5. Iterative codebase simplification | v1.6 | 9/9 | Complete | 2026-04-23 |
| 6. MolmoSpaces api-semantic cleanup pilot | v1.7 | 4/4 | Complete | 2026-05-07 |
| 7. MolmoSpaces prompt-driven cleanup demo | v1.8 | 2/2 | Complete | 2026-05-07 |
| 8. MolmoSpaces real subprocess cleanup | v1.9 | 1/1 | Complete | 2026-05-07 |
| 9. MolmoSpaces FPV room plausibility | v1.10 | 1/1 | Complete | 2026-05-08 |
| 10. MolmoSpaces semantic substeps | v1.11 | 1/1 | Complete | 2026-05-08 |
| 11. MolmoSpaces held-object carry visuals | v1.12 | 1/1 | Complete | 2026-05-08 |
| 12. MolmoSpaces current-contract agent bridge | v1.13 | 1/1 | Complete | 2026-05-08 |
| 13. MolmoSpaces agent bridge visual results | v1.14 | 1/1 | Complete | 2026-05-08 |
| 14. MolmoSpaces real-world cleanup harness | v1.15 | 1/1 | Complete | 2026-05-09 |
| 15. MolmoSpaces Generated Mess Set scale | v1.16 | 1/1 | Complete | 2026-05-09 |
| 16. MolmoSpaces real-world agent MCP | v1.17 | 1/1 | Complete | 2026-05-09 |
| 17. MolmoSpaces real-world agent dogfood | v1.18 | 1/1 | Complete | 2026-05-09 |
| 18. MolmoSpaces real-world OpenClaw dogfood | v1.19 | 1/1 | Complete | 2026-05-09 |
| 19. MolmoSpaces real-world OpenClaw visual evidence | v1.20 | 1/1 | Complete | 2026-05-09 |
| 20. MolmoSpaces real-world OpenClaw clean policy | v1.21 | 1/1 | Complete | 2026-05-09 |
| 21. MolmoSpaces real-world advisory scoring | v1.22 | 1/1 | Complete | 2026-05-09 |
| 22. MolmoSpaces real-world raw FPV perception | v1.23 | 1/1 | Complete | 2026-05-09 |
| 23. MolmoSpaces planner-backed manipulation proof gate | v1.24 | 1/1 | Complete | 2026-05-09 |
| 24. MolmoSpaces planner runtime diagnostics | v1.25 | 1/1 | Complete | 2026-05-09 |
| 25. MolmoSpaces planner headless renderer | v1.26 | 1/1 | Complete | 2026-05-09 |
| 26. MolmoSpaces cleanup planner proof attachment | v1.27 | 1/1 | Complete | 2026-05-09 |
| 27. MolmoSpaces cleanup planner-backed primitive gate | v1.28 | 1/1 | Complete | 2026-05-09 |
| 28. MolmoSpaces RBY1M CuRobo runtime gate | v1.29 | 1/1 | Complete | 2026-05-09 |
| 29. MolmoSpaces camera model policy cleanup | v1.30 | 1/1 | Complete | 2026-05-09 |
| 30. MolmoSpaces report underlay consolidation | v1.31 | 1/1 | Complete | 2026-05-09 |
| 31. MolmoSpaces RBY1M CuRobo warmup readiness | v1.32 | 1/1 | Complete | 2026-05-09 |
| 32. MolmoSpaces RBY1M CuRobo cache isolation | v1.33 | 1/1 | Complete | 2026-05-09 |
| 33. MolmoSpaces RBY1M Warp compatibility | v1.34 | 1/1 | Complete | 2026-05-09 |
| 3. Isaac Lab migration | v2.0 | 0/5 | Deferred | - |
