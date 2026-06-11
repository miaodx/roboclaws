# Architecture Decision Records

This directory is the canonical durable architecture decision log for
Roboclaws. Each ADR captures one decision: the context that forced it, the
choice made, meaningful rejected alternatives, and the consequences accepted.

Keep this surface small and high-signal. ADRs are not phase logs, proof-run
notes, retry records, implementation checklists, or local verification
handoffs. Those belong in dated plans, `docs/status/active/`,
`docs/retrospectives/`, or run artifacts.

Historical ADR-shaped execution records from an earlier long-running goal were
archived under [`archive/execution-log/`](archive/execution-log/) on
2026-06-11. They remain available for traceability, but they are not part of
the default architecture decision surface.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](0001-use-ai2thor-for-phase-1.md) | Use AI2-THOR for Phase 1 | Accepted |
| [0002](0002-defer-isaac-lab-to-phase-3.md) | Defer Isaac Lab integration to Phase 3 | Accepted |
| [0003](0003-separate-cleanup-agent-view-from-private-evaluation.md) | Separate Cleanup Agent View From Private Evaluation | Accepted |
| [0004](0004-use-separate-mcp-servers-for-ai2thor-and-molmo-cleanup.md) | Use Separate MCP Servers For AI2-THOR And Molmo Cleanup | Accepted |
| [0005](0005-use-configurable-generated-mess-set-size.md) | Use Configurable Generated Mess Set Size | Accepted |
| [0006](0006-expose-adr-0003-cleanup-contract-through-mcp.md) | Expose ADR-0003 Cleanup Contract Through MCP | Accepted |
| [0009](0009-use-shared-molmo-cleanup-report-underlay.md) | Use Shared Molmo Cleanup Report Underlay | Accepted |
| [0010](0010-require-real-visual-openclaw-evidence-for-adr-0003-cleanup.md) | Require Real Visual OpenClaw Evidence For ADR-0003 Cleanup | Accepted |
| [0011](0011-enforce-semantic-loop-for-adr-0003-openclaw-clean-policy.md) | Enforce Semantic Loop For ADR-0003 OpenClaw Clean Policy | Accepted |
| [0012](0012-add-non-authoritative-advisory-cleanup-scoring.md) | Add Non-Authoritative Advisory Cleanup Scoring | Accepted |
| [0013](0013-add-raw-fpv-observation-mode-for-adr-0003-cleanup.md) | Add Raw FPV Observation Mode For ADR-0003 Cleanup | Accepted |
| [0014](0014-gate-planner-backed-manipulation-provenance.md) | Gate Planner-Backed Manipulation Provenance | Accepted |
| [0017](0017-attach-strict-planner-proof-to-cleanup-artifacts.md) | Attach Strict Planner Proof To Cleanup Artifacts | Accepted |
| [0018](0018-gate-planner-backed-cleanup-primitives.md) | Gate Planner-Backed Cleanup Primitives Per Cleanup Subphase | Accepted |
| [0020](0020-add-camera-model-policy-mode-for-adr-0003-cleanup.md) | Add Camera Model Policy Mode For ADR-0003 Cleanup | Accepted |
| [0021](0021-use-canonical-cleanup-report-presentation.md) | Use Canonical Cleanup Report Presentation | Accepted |
| [0027](0027-use-shared-semantic-cleanup-loop-driver.md) | Use Shared Semantic Cleanup Loop Driver | Accepted |
| [0029](0029-add-planner-backed-cleanup-primitive-executor.md) | Add Planner-Backed Cleanup Primitive Executor | Accepted |
| [0035](0035-use-bound-planner-proof-bundles-for-cleanup-coverage.md) | Use Bound Planner Proof Bundles for Cleanup Coverage | Accepted |
| [0037](0037-emit-cleanup-planner-proof-request-manifests.md) | Emit Cleanup Planner Proof Request Manifests | Accepted |
| [0050](0050-use-plain-semantic-subphase-report-labels.md) | Use Plain Semantic Subphase Report Labels | Accepted |
| [0106](0106-centralize-semantic-cleanup-vocabulary.md) | Centralize Semantic Cleanup Vocabulary | Accepted |
| [0126](0126-bridge-camera-evidence-to-cleanup-handles-with-model-declared-observations.md) | Bridge Camera Evidence To Cleanup Handles With Model-Declared Observations | Accepted |
| [0127](0127-use-direct-nav2-adapter-before-rosclaw.md) | Use Direct Nav2 Adapter Before ROSClaw | Accepted |
| [0128](0128-add-real-robot-cleanup-profile.md) | Add Real Robot Cleanup Profile | Accepted |
| [0129](0129-use-nav2-map-artifacts-for-simulator-hardware-parity.md) | Use Nav2 Map Artifacts For Simulator Hardware Parity | Accepted |
| [0130](0130-default-composition-to-trace-preserving-skill-routines.md) | Default Composition To Trace-Preserving Skill Routines | Accepted; Updated by ADR-0132 |
| [0131](0131-use-agibot-sdk-runner-as-real-robot-cleanup-backend.md) | Use Agibot SDK Runner As Real Robot Cleanup Backend | Accepted |
| [0132](0132-keep-cleanup-memory-skill-first-and-remove-promoted-composite.md) | Keep Cleanup Memory Skill-First And Remove Promoted Composite | Accepted |
| [0133](0133-use-http-visual-grounding-service-for-real-camera-labels.md) | Use HTTP Visual Grounding Service For Real Camera Labels | Accepted |
| [0134](0134-use-public-done-readiness-gates.md) | Use Public Done Readiness Gates | Accepted |
| [0135](0135-use-sanitized-report-performance-artifacts-for-speed-claims.md) | Use Sanitized Report Performance Artifacts For Speed Claims | Accepted |
| [0136](0136-use-base-navigation-map-and-first-class-household-launch-contracts.md) | Use Base Navigation Map And First-Class Household Launch Contracts | Accepted |

## Adding A New ADR

1. Write an ADR only when the decision is durable and constrains future work.
2. Use the next number above the highest ADR-shaped record in the repo. Do not
   fill gaps left by archived records.
3. Use kebab-case for the title slug: `NNNN-short-decision.md`.
4. Set status `Accepted` only once the decision is taken.
5. Keep the ADR short. Link to a plan for phases, commands, tests, gates, and
   implementation sequencing.
6. Never rewrite a past ADR's decision body. Supersede it with a new ADR that
   references the old one, then update the old ADR's status line or index row.
7. Add a row to the index above.

## When To Write An ADR

Write an ADR when:

- The decision changes the shape of the system or constrains future work.
- The decision defines a public API, MCP/tool contract, command surface,
  private-data boundary, safety policy, cost/model infrastructure boundary, or
  architecture layer.
- Real alternatives were considered and rejected, and future maintainers need
  to know why.
- A future contributor would otherwise have to infer a non-obvious boundary
  from code or commit history.

Do not write an ADR for:

- proof loops, reruns, local-dev evidence, benchmarks, or one-off gates;
- implementation sequencing, phase checklists, or task status;
- report wording, visual polish, or local artifact regeneration;
- reversible implementation details such as function signatures or file layout;
- decisions already obvious from code or root documentation.

For those, use:

- `docs/plans/YYYY-MM-DD-short-topic.md` for new execution plans;
- `docs/status/active/` for current standalone work;
- `.planning/` for GSD-owned execution;
- `docs/retrospectives/` for shipped history and verification evidence.
