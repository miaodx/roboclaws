# 0084. Use Run-Result Adapter for Cleanup Report Regeneration

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0009, ADR-0021, ADR-0036, and ADR-0050 require one Cleanup Artifact
Report underlay and the report-facing cleanup loop `nav, pick, nav, open?,
place`. The code now routes new current-contract and ADR-0003 cleanup runs
through `roboclaws/molmo_cleanup/report.py`, but old ignored artifacts such as
`output/molmo-agent-bridge-visual-codex/report.html` can still contain stale
HTML from an earlier renderer.

That made the architecture look like multiple implementations: the artifact
data was reusable, but there was no small module whose interface was "take an
existing cleanup `run_result.json` and regenerate the report through the shared
underlay." Reviewers had to know how scenario bundles, traces, snapshots,
private manifests, and robot-view steps were stored.

## Decision

Add a Cleanup Report Artifact Adapter with one primary interface:
`rerender_cleanup_report_from_run_result(run_result_path)`.

The adapter owns artifact rehydration from `run_result.json`: public scenario,
adjacent private manifest when present, trace events, snapshots, and robot-view
steps. It then delegates to `render_cleanup_report`, so regenerated
current-contract and ADR-0003 artifacts use the same visual core and semantic
subphase vocabulary as new runs.

Add a small CLI, `scripts/regenerate_molmo_cleanup_report.py`, for local-dev
artifact repair without rerunning MolmoSpaces or VLM/OpenClaw sessions.

## Consequences

- Stale cleanup artifacts can be repaired through one adapter instead of
  preserving old HTML as a parallel report implementation.
- The Cleanup Artifact Report underlay remains the only renderer for
  MolmoSpaces cleanup demos.
- The adapter is an artifact-maintenance seam, not a new report renderer.
- Regenerating a report does not change the underlying cleanup result,
  primitive provenance, ADR-0003 status, or planner-backed readiness.
