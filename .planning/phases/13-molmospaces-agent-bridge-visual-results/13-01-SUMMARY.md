# Phase 13 Plan 01 Summary - Agent Bridge Visual Results

Completed on 2026-05-08.

## What Changed

- Added opt-in robot-view recording to `MolmoCleanupMCPServer` so agent bridge
  runs can emit the same RBY1M FPV/chase/map/verification timeline as the
  Molmo visual harness.
- Added `--backend`, `--include-robot`, `--robot-name`, and
  `--record-robot-views` flags to the direct bridge server and smoke runner.
- Extended the bridge checker with `--expect-backend`, `--expect-robot`, and
  `--require-robot-views`.
- Added `just harness::molmo-agent-bridge-visual` and
  `just verify::molmo-agent-bridge-visual`.
- Hardened the Molmo cleanup skill and observe instruction around pickupable
  object IDs, non-empty `location_id`, receptacles as targets only, and
  same-category receptacle tie-breaking.

## Verification

See `13-VERIFICATION.md`.

Key evidence:

- Public-rule visual baseline:
  `output/molmo-agent-bridge-visual-rule/run_result.json` -> `success`, 5/5
  restored, 25 robot-view timeline steps.
- Contract smoke visual harness:
  `output/molmo-agent-bridge-visual-harness/run_result.json` -> `success`,
  5/5 restored, 25 robot-view timeline steps.
- Codex direct visual MCP:
  `output/molmo-agent-bridge-visual-codex/run_result.json` -> `success`, 4/5
  restored, 25 robot-view timeline steps.
- Claude Code direct visual MCP:
  `output/molmo-agent-bridge-visual-claude/run_result.json` -> `success`, 4/5
  restored, 25 robot-view timeline steps.
- OpenClaw Gateway visual MCP:
  `output/molmo-agent-bridge-visual-openclaw/run_result.json` -> `success`,
  3/5 restored, 25 robot-view timeline steps.

## Boundary

The missing images and semantic mid-phase rows are fixed for agent bridge
reports. The remaining score gaps are current-contract behavior: agents choose
from public `scene_objects` without seeing the scorer-only private target map.
This still does not satisfy ADR-0003 or planner-backed robot manipulation.
