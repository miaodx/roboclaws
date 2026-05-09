# Architecture Decision Records

Architectural decisions for roboclaws. Each ADR captures one decision —
the context that forced it, the choice made, and the consequences
accepted. Use [Michael Nygard's format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions):
one decision per file, sequential numbering, explicit status.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](0001-use-ai2thor-for-phase-1.md) | Use AI2-THOR for Phase 1 | Accepted |
| [0002](0002-defer-isaac-lab-to-phase-3.md) | Defer Isaac Lab integration to Phase 3 | Accepted |
| [0003](0003-separate-cleanup-agent-view-from-private-evaluation.md) | Separate Cleanup Agent View From Private Evaluation | Accepted |
| [0004](0004-use-separate-mcp-servers-for-ai2thor-and-molmo-cleanup.md) | Use Separate MCP Servers For AI2-THOR And Molmo Cleanup | Accepted |
| [0005](0005-use-configurable-generated-mess-set-size.md) | Use Configurable Generated Mess Set Size | Accepted |
| [0006](0006-expose-adr-0003-cleanup-contract-through-mcp.md) | Expose ADR-0003 Cleanup Contract Through MCP | Accepted |
| [0007](0007-dogfood-adr-0003-mcp-with-clean-agent-runs.md) | Dogfood ADR-0003 MCP With Clean Agent Runs | Accepted |
| [0008](0008-evaluate-openclaw-on-adr-0003-mcp-after-direct-agent-dogfood.md) | Evaluate OpenClaw On ADR-0003 MCP After Direct Agent Dogfood | Accepted |
| [0009](0009-use-shared-molmo-cleanup-report-underlay.md) | Use Shared Molmo Cleanup Report Underlay | Accepted |
| [0010](0010-require-real-visual-openclaw-evidence-for-adr-0003-cleanup.md) | Require Real Visual OpenClaw Evidence For ADR-0003 Cleanup | Accepted |
| [0011](0011-enforce-semantic-loop-for-adr-0003-openclaw-clean-policy.md) | Enforce Semantic Loop For ADR-0003 OpenClaw Clean Policy | Accepted |
| [0012](0012-add-non-authoritative-advisory-cleanup-scoring.md) | Add Non-Authoritative Advisory Cleanup Scoring | Accepted |
| [0013](0013-add-raw-fpv-observation-mode-for-adr-0003-cleanup.md) | Add Raw FPV Observation Mode For ADR-0003 Cleanup | Accepted |
| [0014](0014-gate-planner-backed-manipulation-provenance.md) | Gate Planner-Backed Manipulation Provenance | Accepted |
| [0015](0015-capture-planner-runtime-diagnostics-before-strict-execution.md) | Capture Planner Runtime Diagnostics Before Strict Execution | Accepted |
| [0016](0016-use-probe-local-egl-renderer-adapter-for-headless-planner-proof.md) | Use Probe-Local EGL Renderer Adapter For Headless Planner Proof | Accepted |
| [0017](0017-attach-strict-planner-proof-to-cleanup-artifacts.md) | Attach Strict Planner Proof To Cleanup Artifacts | Accepted |
| [0018](0018-gate-planner-backed-cleanup-primitives.md) | Gate Planner-Backed Cleanup Primitives Per Cleanup Subphase | Accepted |
| [0019](0019-gate-rby1m-curobo-runtime-before-cleanup-primitives.md) | Gate RBY1M CuRobo Runtime Before Cleanup Primitive Replacement | Accepted |
| [0020](0020-add-camera-model-policy-mode-for-adr-0003-cleanup.md) | Add Camera Model Policy Mode For ADR-0003 Cleanup | Accepted |
| [0021](0021-use-canonical-cleanup-report-presentation.md) | Use Canonical Cleanup Report Presentation | Accepted |
| [0022](0022-capture-rby1m-curobo-warmup-readiness.md) | Capture RBY1M CuRobo Warmup Readiness | Accepted |
| [0023](0023-use-isolated-curobo-extension-cache-for-rby1m-warmup.md) | Use Isolated CuRobo Extension Cache for RBY1M Warmup | Accepted |
| [0024](0024-use-probe-local-warp-torch-compatibility-adapter.md) | Use Probe-Local Warp Torch Compatibility Adapter | Accepted |
| [0025](0025-capture-rby1m-cuda-memory-headroom.md) | Capture RBY1M CUDA Memory Headroom Evidence | Accepted |
| [0026](0026-use-visible-probe-local-curobo-memory-profile.md) | Use Visible Probe-Local CuRobo Memory Profile | Accepted |
| [0027](0027-use-shared-semantic-cleanup-loop-driver.md) | Use Shared Semantic Cleanup Loop Driver | Accepted |
| [0028](0028-add-planner-cleanup-bridge-readiness-evidence.md) | Add Planner Cleanup Bridge Readiness Evidence | Accepted |
| [0029](0029-add-planner-backed-cleanup-primitive-executor.md) | Add Planner-Backed Cleanup Primitive Executor | Accepted |
| [0030](0030-bind-planner-primitive-evidence-to-cleanup-targets.md) | Bind Planner Primitive Evidence to Cleanup Targets | Accepted |
| [0031](0031-add-probe-backed-cleanup-primitive-executor-adapter.md) | Add Probe-Backed Cleanup Primitive Executor Adapter | Accepted |
| [0032](0032-emit-cleanup-primitive-binding-from-planner-probe.md) | Emit Cleanup Primitive Binding from Planner Probe | Accepted |
| [0033](0033-bind-observed-handles-to-planner-task-names.md) | Bind Observed Handles to Planner Task Names | Accepted |
| [0034](0034-use-probe-backed-executor-for-bounded-cleanup-loop.md) | Use Probe-Backed Executor for Bounded Cleanup Loop | Accepted |
| [0035](0035-use-bound-planner-proof-bundles-for-cleanup-coverage.md) | Use Bound Planner Proof Bundles for Cleanup Coverage | Accepted |
| [0036](0036-centralize-cleanup-report-visual-core-checks.md) | Centralize Cleanup Report Visual Core Checks | Accepted |
| [0037](0037-emit-cleanup-planner-proof-request-manifests.md) | Emit Cleanup Planner Proof Request Manifests | Accepted |
| [0038](0038-render-planner-proof-requests-in-cleanup-reports.md) | Render Planner Proof Requests In Cleanup Reports | Accepted |
| [0039](0039-render-planner-proof-bundle-runner-reports.md) | Render Planner Proof Bundle Runner Reports | Accepted |
| [0040](0040-check-planner-proof-bundle-runner-artifacts.md) | Check Planner Proof Bundle Runner Artifacts | Accepted |
| [0041](0041-reuse-shared-semantic-cleanup-loop-in-mcp-smoke-demos.md) | Reuse Shared Semantic Cleanup Loop In MCP Smoke Demos | Accepted |
| [0042](0042-add-dry-run-harness-for-planner-proof-bundle-runner.md) | Add Dry-Run Harness For Planner Proof Bundle Runner | Accepted |
| [0043](0043-track-cleanup-rerun-artifacts-in-proof-bundle-runner.md) | Track Cleanup Rerun Artifacts In Proof Bundle Runner | Accepted |
| [0044](0044-add-local-gate-for-planner-proof-bundle-execution.md) | Add Local Gate For Planner Proof Bundle Execution | Accepted |
| [0045](0045-bind-proof-probes-to-real-cleanup-scenes.md) | Bind Proof Probes To Real Cleanup Scenes | Accepted |
| [0046](0046-render-proof-bundle-result-feasibility.md) | Render Proof Bundle Result Feasibility | Accepted |
| [0047](0047-select-proof-requests-by-task-feasibility.md) | Select Proof Requests By Task Feasibility | Accepted |
| [0048](0048-generate-private-fallback-proof-requests.md) | Generate Private Fallback Proof Requests | Accepted |
| [0049](0049-run-generated-fallback-proofs-as-local-dev-evidence.md) | Run Generated Fallback Proofs As Local-Dev Evidence | Accepted |
| [0050](0050-use-plain-semantic-subphase-report-labels.md) | Use Plain Semantic Subphase Report Labels | Accepted |
| [0051](0051-surface-fallback-timeout-stage-evidence.md) | Surface Fallback Timeout Stage Evidence | Accepted |
| [0052](0052-warm-rby1m-curobo-before-fallback-proofs.md) | Warm RBY1M CuRobo Before Fallback Proofs | Accepted |
| [0053](0053-run-warmed-generated-fallback-proofs.md) | Run Warmed Generated Fallback Proofs | Accepted |
| [0054](0054-filter-fallback-aliases-to-exact-scene-runtime-names.md) | Filter Fallback Aliases to Exact-Scene Runtime Names | Accepted |
| [0055](0055-discover-fallback-runtime-aliases-from-keyerrors.md) | Discover Fallback Runtime Aliases from KeyError Evidence | Accepted |
| [0056](0056-run-discovered-runtime-fallback-proofs.md) | Run Discovered Runtime Fallback Proofs | Accepted |
| [0057](0057-remember-failed-fallback-candidates.md) | Remember Failed Fallback Candidates | Accepted |
| [0058](0058-execute-filtered-fallback-proofs.md) | Execute Filtered Fallback Proofs | Accepted |
| [0059](0059-carry-forward-filtered-fallback-candidates.md) | Carry Forward Filtered Fallback Candidates | Accepted |
| [0060](0060-filter-non-root-pickup-runtime-aliases.md) | Filter Non-Root Pickup Runtime Aliases | Accepted |
| [0061](0061-merge-prior-planner-proof-evidence.md) | Merge Prior Planner Proof Evidence | Accepted |
| [0062](0062-surface-fallback-exhaustion-status.md) | Surface Fallback Exhaustion Status | Accepted |
| [0063](0063-summarize-fallback-exhaustion-blockers.md) | Summarize Fallback Exhaustion Blockers | Accepted |
| [0064](0064-normalize-pickup-root-runtime-aliases.md) | Normalize Pickup Root Runtime Aliases | Accepted |
| [0065](0065-preserve-target-feasibility-proof-links.md) | Preserve Target Feasibility Proof Links | Accepted |
| [0066](0066-render-target-feasibility-blocker-matrix.md) | Render Target Feasibility Blocker Matrix | Accepted |
| [0067](0067-preserve-task-sampler-exception-context.md) | Preserve Task Sampler Exception Context | Accepted |
| [0068](0068-capture-task-sampler-failure-diagnostics.md) | Capture Task Sampler Failure Diagnostics | Accepted |
| [0069](0069-add-task-sampler-robot-placement-profile.md) | Add Task Sampler Robot Placement Profile | Accepted |
| [0070](0070-render-placement-scene-diagnostics.md) | Render Placement Scene Diagnostics | Accepted |
| [0071](0071-add-wide-placement-profile-retry.md) | Add Wide Placement Profile Retry | Accepted |
| [0072](0072-capture-post-placement-candidate-rejections.md) | Capture Post-Placement Candidate Rejections | Accepted |

## Adding a new ADR

1. Copy the most recent ADR as a template.
2. Use the next sequential number, zero-padded to 4 digits.
3. Use kebab-case for the title slug.
4. Set status `Accepted` once the decision is taken.
5. Never rewrite a past ADR's decision body — supersede it with a new
   ADR that references the old one (and update the old one's status to
   `Superseded by ADR-NNNN`).
6. Add a row to the index table above.

## When to write an ADR vs. when not to

Write an ADR when:

- The decision is **architecturally significant** — changes the shape of
  the system or constrains future work.
- There are **real alternatives** that were considered and rejected. ADRs
  exist to capture *why not the other thing*.
- A future contributor asking "why did they do X?" would otherwise have
  to dig through commit history or guess.

Don't write an ADR for:

- Implementation details (function signatures, file layout, code style).
  These belong in [`ARCHITECTURE.md`](../../ARCHITECTURE.md) or inline
  code comments.
- Decisions that are obvious from the code (e.g., "use Python" — the
  pyproject.toml already says so).
- Reversible choices that don't constrain anything else.
