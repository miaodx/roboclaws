# 0110. Preserve Grasp Filter Intermediates And Variant Diagnostics

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0109 made MolmoSpaces rigid grasp cache generation reproducible, but the
upstream `run_rigid.py` path still left the most useful evidence transient:
after filtering, it deletes the combined mesh, simplified mesh, unfiltered
candidate JSON, and object metadata, while `perturbations_test.py` collapses
every failed candidate to `(index, None, None)`.

That made `Bread_1` look like a generic zero-transform cache failure even
though candidate generation itself was working.

## Decision

Add a repo-owned grasp-filter diagnostic runner and report.

The diagnostic runner:

- preserves combine/Manifold/simplify/candidate artifacts under the selected
  output directory;
- writes a bounded candidate subset for fast local probes;
- reruns perturbation filtering through explicit variants:
  `initial_contact`, `translation_shake`, and `upstream_like`;
- validates each generated NPZ with the same nonzero-transform rule used by the
  loader preflight;
- renders the pipeline stages, variant classifications, output NPZ paths, and
  blockers in a shared-style HTML report.

## Consequences

- Future cache-generation work can distinguish "candidate generation failed"
  from "perturbation filtering rejected every candidate".
- The current `Bread_1` blocker is narrower: a bounded local diagnostic
  generated 24 valid candidates, but all three variants, including
  no-shake/no-rotate `initial_contact`, saved zero successful transforms.
- The droid loader cache remains uninstalled until a diagnostic or replacement
  filter path produces at least one nonzero transform.

## Evidence

Implemented in Phase 119 on 2026-05-10.

Artifacts:

- `output/debug-phase119-grasp-filter-diagnostics/filter_diagnostics_result.json`
- `output/debug-phase119-grasp-filter-diagnostics/report.html`

Key results:

- `combine_meshes`: ready
- `manifold`: ready
- `simplify`: ready
- `generate_grasps`: ready, 24 candidates
- `initial_contact`: zero successful transforms
- `translation_shake`: zero successful transforms
- `upstream_like`: zero successful transforms
