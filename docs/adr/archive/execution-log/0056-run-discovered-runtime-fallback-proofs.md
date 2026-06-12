# 0056. Run Discovered Runtime Fallback Proofs

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0055 added runtime alias discovery from prior exact-scene `KeyError`
valid-name lists. The runner can now generate fallback proof commands using
runtime sibling aliases instead of upstream/display aliases.

The next useful evidence is local execution of those generated commands. This
must remain an evidence phase: discovered runtime aliases are command
candidates, not planner-backed cleanup proof.

## Decision

Execute the discovered runtime-sibling fallback proof bundle locally with:

- the Phase 62 warmed generated fallback manifest as prior evidence;
- generated fallback request selection enabled;
- `--warmup-rby1m-curobo`;
- an output-local Torch extension cache;
- `--require-proof-outputs` runner validation.

The phase records the exact result even if every proof remains blocked.

## Consequences

- The proof-bundle runner now has real local evidence for discovered runtime
  aliases.
- Target-sibling fallback commands got past invalid alias sampling but still
  block with `HouseInvalidForTask`.
- Object-sibling fallback commands are valid names but fail as non-root bodies,
  so they should not be treated as viable pickup aliases without an additional
  root-body validity gate.
- Cleanup primitive binding remains unpromoted; planner-backed cleanup is still
  blocked.

## Evidence

The local Phase 65 run wrote
`output/debug-phase65-discovered-runtime-fallback-execute/report.html` and
`proof_bundle_run_manifest.json`.

The bundle selected four generated fallback requests from five discovered
runtime aliases. Warmup completed via `rby1m_curobo_config_import`, all four
proof commands attempted execution, and all four reached task sampling before
blocking:

- `proof_001_fallback_01` and `proof_002_fallback_01` used target-sibling
  aliases and blocked with `HouseInvalidForTask`.
- `proof_001_fallback_02` and `proof_002_fallback_02` used object-sibling
  aliases and blocked with `AssertionError: Object is not a root body`.

The proof result summary recorded:

- `expected_count=4`
- `result_count=4`
- `execution_attempted_count=4`
- `task_feasibility_blocked_count=4`
- `planner_backed_count=0`
- `cleanup_binding_promoted_count=0`
- `timeout_count=0`
- `rby1m_config_import_timeout_count=0`
- `view_artifact_count=0`

Validation passed with:

```bash
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py --require-proof-outputs output/debug-phase65-discovered-runtime-fallback-execute
```
