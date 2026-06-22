---
refactor_scope: reduce-entropy-loop
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-14
---

# Refactor Scope: Reduce Entropy Loop

## Status

DONE

## Target

Remove or quarantine stale active-looking code paths that survived the
AI2-THOR/direct-VLM and renderer cleanup work, then run a fresh reduce-entropy
discovery pass after each completed group.

## Accepted Severities

- P0: false-green gates or currently broken active routes.
- P1: stale install surfaces, public/source-of-truth drift, or live wrappers
  that keep retired routes reachable.
- P2: target-local cleanup that removes recurring rediscovery or false
  confidence around the accepted groups.

## Accepted Cleanup Checklist

- [x] Remove retired Qwen3-VL visual-grounding install surfaces from root and
  sidecar dependency metadata, lockfiles, and regression coverage.
- [x] Resolve the Genesis render-only lane: either make its opt-in status
  explicit and quarantined, or retire the lane and its backend/test/docs
  surface.
- [x] Collapse the old `molmo::cleanup` dispatcher shape behind the canonical
  `run::surface` / `agent::run` launch contract.
- [x] Quarantine OpenClaw Gateway surfaces so validation-required routes cannot
  look healthy without off-work-network Gateway proof.
- [x] Shrink visual-grounding benchmark/harness surfaces to the active
  detector-only adapter contract and park historical VLM evidence clearly.
- [x] After each group, run a fresh bounded reduce-entropy discovery pass and
  append any material follow-up candidates here.
- [x] Retire the broken Railway/OpenClaw appliance deployment surface
  (`Dockerfile.railway`, `railway.toml`, `deploy/railway/**`, and the leftover
  appliance smoke script) or prove it is still supported by a current build
  gate.
- [x] Collapse stale current-looking context and human-doc entrypoints so they
  do not present retired AI2-THOR, `task::run`, or superseded profile-model
  guidance as first-read truth.
- [x] Remove task-shaped legacy MCP profiles from the active contract registry,
  leaving only task-neutral household capability profiles as selectable MCP
  contract heads.
- [x] Remove operator-console legacy route wrappers from normal code paths,
  without preserving historical run-history interpretation.
- [x] Add a Ruff complexity plus Pylint 800-line module-size ratchet with an
  explicit baseline so new work cannot grow current complexity/size debt while
  existing large files are refactored deliberately.
- [x] Remove duplicate root-level Molmo checker/probe scripts that are
  byte-for-byte copies of the canonical `scripts/molmo_cleanup/` scripts.
- [x] Refresh stale human-facing command/profile guidance so current docs no
  longer surface `task::run`, one-axis cleanup profiles, or OpenClaw
  convenience wrappers as normal current entrypoints.
- [x] Refresh low-level test/tooling layout docs and pre-commit path inference
  after the AI2-THOR/game/appliance retirement so retired or empty domains do
  not look current.

## Parked Cross-Seam / Future Ideas

- Local untracked caches and virtualenvs such as `__pycache__`,
  `.venv-genesis`, `.venv-visual-grounding`, and the previously retired
  `sidecars/molmospaces-filament/.venv` are machine-local residue unless they
  become tracked or are referenced by live commands.

## Evidence Ladder

- L0 static: `rg` stale-surface searches and `ruff` where touched Python files
  are edited.
- L1 unit/contract: focused pytest files for each group.
- L2 contract: just recipe/catalog tests when public or maintainer command
  routing changes.
- L4+ local simulator/render/Gateway/provider gates are skipped unless a group
  explicitly requires them and the work-network/provider preflight allows it.

## Stop Condition

Stop when all accepted cleanup items are complete or explicitly recorded as
parked/no-change, focused tests pass for touched surfaces, stale active-route
searches show only historical/parked references, and a final discovery pass
returns no P0/P1 or materially useful P2 candidates in this class.

## Execution Log

- 2026-06-14: Created loop gate from the accepted reduce-entropy packet.
- 2026-06-14: Removed the retired Qwen3-VL visual-grounding extras from the
  root and sidecar dependency metadata, regenerated both lockfiles, and added
  contract coverage asserting the metadata does not expose `qwen3vl` or
  `qwen-vl-utils`. Evidence:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/visual_grounding/test_visual_grounding_service.py -q`
  passed with 15 tests.
- 2026-06-14: Retired the Genesis render-only candidate lane rather than
  keeping another renderer backend in quarantine. Removed the Genesis submodule
  entry, backend worker, backend module, Genesis-specific unit/contract tests,
  scene-camera recipe switches, camera-control Genesis light overrides, and
  active report sections for Genesis visual audit, movable-object visibility,
  material response, and shadow parity. Historical Genesis documentation is now
  labeled as retired evidence. Evidence:
  `ruff check roboclaws/household/camera_control.py roboclaws/household/scene_camera_comparison.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_scene_camera_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py -q`
  passed with 92 tests.
- 2026-06-14: Ran the post-Genesis bounded high-noise summary with
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs"`.
  It surfaced the expected large historical/planning/test surfaces but no new
  P0/P1 candidate stronger than the remaining accepted checklist. Continue with
  old `molmo::cleanup` dispatcher collapse.
- 2026-06-14: Collapsed the old public-looking `molmo::cleanup` dispatcher
  shape into the private `molmo::household-cleanup-impl` runner. Public
  `run::surface` and maintainer `agent::run` now lower to that private runner,
  molmo convenience report recipes call the private implementation directly,
  and trace mode exits before any simulator/provider work. Evidence:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/dev_tools/test_verify_just_recipes.py -q`
  passed with 154 tests; `rg -n "molmo::cleanup" just tests/contract/dev_tools docs/human/molmospaces-settings.md just/README.md CLAUDE.md AGENTS.md README.md ARCHITECTURE.md roboclaws scripts skills .github`
  now finds only negative test guards.
- 2026-06-14: Ran the post-dispatcher bounded high-noise summary with
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs"`.
  It found the expected large historical/planning/test surfaces but no new
  P0/P1 candidate stronger than the remaining accepted OpenClaw quarantine and
  visual-grounding benchmark/harness shrink groups.
- 2026-06-14: Quarantined the remaining OpenClaw public discovery surface.
  `openclaw-gateway` remains registered as a validation-required maintainer
  engine, but the generic public `agent_engine` error hint and just README
  engine list no longer present it as a normal engine choice; the OpenClaw demo
  doc now says validation-required maintainer route rather than public-catalog
  parity. Evidence:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py::test_surface_launch_rejects_retired_vlm_policy_engine tests/contract/dev_tools/test_task_agent_just_recipes.py::test_public_engine_docs_quarantine_openclaw_gateway tests/contract/dev_tools/test_task_agent_just_recipes.py::test_openclaw_demo_doc_stays_validation_required tests/unit/operator_console/test_routes.py::test_openclaw_agent_engine_marks_validation_required -q`
  passed with 4 tests.
- 2026-06-14: Ran the post-OpenClaw bounded high-noise summary with
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs"`.
  It found no new P0/P1 candidate stronger than the remaining visual-grounding
  benchmark/harness shrink group.
- 2026-06-14: Shrank visual-grounding benchmark/harness output to the active
  detector-only adapter contract. The benchmark result now emits
  `detector_probe_recommendation` with schema
  `visual_grounding_detector_probe_recommendation_v1`; report/checker/test
  wording no longer exposes a promotion recommendation contract, and retired
  direct/refiner slot protections are collapsed into generic retired-slot key
  guards. Evidence: `ruff check scripts/visual_grounding/run_visual_grounding_benchmark.py scripts/visual_grounding/check_visual_grounding_benchmark_result.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
  passed; `./scripts/dev/run_pytest_standalone.sh tests/contract/visual_grounding/test_visual_grounding_benchmark.py -q`
  passed with 13 tests; `./scripts/dev/run_pytest_standalone.sh tests/contract/visual_grounding/test_visual_grounding_service.py -q`
  passed with 15 tests; `./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_visual_grounding.py -q`
  passed with 5 tests. The active search
  `rg -n "promotion_recommendation|visual_grounding_promotion|requires_real_stage_provenance_before_promotion|before promotion|best_direct_vlm_pipeline_id|best_proposer_plus_refiner_pipeline_id|max_direct_vlm_pipelines|max_proposer_plus_refiner_pipelines" scripts/visual_grounding tests/contract/visual_grounding docs/human/molmospaces-settings.md just/README.md roboclaws/household/visual_grounding.py`
  returned no matches.
- 2026-06-14: Ran the final saturation audit. The bounded high-noise summary
  still reports the expected large historical/planning/test surfaces but no new
  P0/P1 or materially useful P2 candidate in this cleanup class. Additional
  targeted searches confirmed the removed/retired active contracts are gone or
  only present as explicit validation-required maintainer wording, historical
  documentation, or negative tests. Final focused verification:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/dev_tools/test_verify_just_recipes.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py tests/contract/visual_grounding/test_visual_grounding_service.py tests/unit/molmo_cleanup/test_visual_grounding.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py -q`
  passed with 281 tests.
- 2026-06-14: Reopened discovery after a repo-size/complexity quality-gate
  question. Bounded probes found that enabling Ruff `C901`, `PLR0912`, and
  `PLR0915` at default thresholds would currently produce 265 failures, while
  a Pylint `too-many-lines` gate at `max-module-lines=800` would hit 60 tracked
  Python files. This makes a baseline/ratchet gate the viable entropy-reduction
  direction rather than an immediate full-repo refactor. Additional targeted
  scans found five byte-for-byte duplicate root-level Molmo scripts whose live
  references use the canonical `scripts/molmo_cleanup/` copies, stale
  human-facing command/profile guidance in the superseded cleanup-profile doc
  and Molmo settings, the already-accepted legacy MCP profile and
  operator-console route wrapper cleanup targets, and a smaller test/tooling
  layout drift after retired AI2-THOR/game/appliance surfaces. The materiality
  gate accepted all six candidates.
- 2026-06-14: Retired the broken Railway/OpenClaw appliance deployment surface.
  Removed the Railway Docker/config/deploy files and leftover appliance smoke
  scripts, updated OpenClaw docs to point at the canonical plugin allowlist, and
  changed OpenClaw/network-status tests to guard against appliance surface
  revival. Evidence:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/openclaw/test_openclaw_bootstrap.py::test_retired_railway_appliance_surface_stays_removed tests/contract/openclaw/test_openclaw_bootstrap.py::test_bootstrap_reads_canonical_plugin_allowlist tests/contract/openclaw/test_openclaw_bootstrap.py::test_plugins_allow_seeded_from_canonical_allowlist tests/unit/scripts/test_network_status_guard.py::test_claude_and_openclaw_just_recipes_use_network_guard -q`
  passed.
- 2026-06-14: Collapsed stale current-looking context and human-doc entrypoints.
  `CONTEXT.md` now uses the current planner-proof example and current map /
  perception plan links; `docs/human/README.md` moves the superseded cleanup
  mode architecture doc out of the read-first path.
- 2026-06-14: Removed task-shaped legacy MCP profiles from the active contract
  registry. `contract_profile_names()` now exposes only
  `household_world_v1`, `household_manipulation_v1`, and
  `household_episode_v1`; old cleanup-shaped ids remain outside the active
  registry only as artifact metadata. Evidence:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/mcp/test_semantic_profiles.py tests/contract/skills/test_skill_manifests.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_registered_tools_match_profile_public_surface -q`
  passed.
- 2026-06-14: Removed operator-console legacy route wrappers from normal code
  paths with no historical compatibility mapping. Deleted `ConsoleRoute`,
  `get_route()`, `list_console_routes()`, and the legacy route-id registry;
  launcher/history/state/interactions/server/static paths now use canonical
  `ConsoleLaunchSelection` ids or launch axes only. Next-goal and latest-run
  payloads no longer emit legacy `route_id`, and tests now assert the old route
  API stays absent. Evidence:
  `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console -q`
  passed; `ruff check roboclaws/operator_console tests/unit/operator_console`
  passed; `rg -n "ConsoleRoute|get_route\\(|list_console_routes|legacy_route_id|route_id" roboclaws/operator_console tests/unit/operator_console README.md ARCHITECTURE.md docs/human just scripts -g '!*.pyc'`
  finds only negative tests, local variable names, and unrelated provider-route
  health-check terminology.
- 2026-06-14: Added the Python quality ratchet. `just verify::static` and the
  pre-commit hook now run `scripts/dev/check_python_quality_ratchet.py`, which
  compares Ruff `C901`, `PLR0912`, and `PLR0915` diagnostics plus
  Pylint-compatible `max-module-lines=800` module sizes against
  `scripts/dev/python_quality_baseline.json`. Existing debt is explicit while
  new complexity violations, growth in existing violations, new oversized
  modules, or line-count growth in oversized modules fail deterministically.
  Current baseline after root Molmo shim removal: 217 Ruff complexity
  violations and 61 oversized modules. Evidence:
  `.venv/bin/python scripts/dev/check_python_quality_ratchet.py` passed;
  `./scripts/dev/run_pytest_standalone.sh tests/unit/scripts/test_python_quality_ratchet.py tests/contract/dev_tools/test_verify_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  passed.
- 2026-06-14: Removed root-level Molmo checker/probe compatibility shims that
  duplicated canonical scripts under `scripts/molmo_cleanup/`. The current
  code, just recipes, tests, and human docs already reference the canonical
  paths, and a dev-tools contract test now keeps those root shims removed.
  Evidence: targeted symlink scan over `scripts/*.py` finds no symlink whose
  target is `scripts/molmo_cleanup/`.
- 2026-06-14: Refreshed stale command/profile guidance. The superseded cleanup
  profile architecture doc now presents one-axis cleanup profiles only as
  legacy/historical results and no longer contains copyable `just task::run` or
  `profile=...` current command examples. `docs/human/molmospaces-settings.md`
  removes OpenClaw smoke/live wrappers from normal report recipes and labels
  OpenClaw reports as maintainer-only validation routes. `just/molmo.just`
  marks the OpenClaw Molmo report wrappers private. Evidence: active search for
  `task::run`, `profile=world-labels`, `profile=world-labels-sanitized`,
  `profile=camera-raw`, `profile=camera-labels`, `openclaw-smoke-report`, and
  `just molmo::openclaw-report` in human/root/just docs now returns only
  retirement wording and negative tests.
- 2026-06-14: Refreshed low-level tooling layout after retired AI2-THOR/game
  surfaces. The pre-commit scoped-test inference no longer maps
  `roboclaws/ai2thor/*` or `roboclaws/games/*` to empty retired test domains,
  and contract coverage asserts those retired path rules stay absent. Evidence:
  `rg -n -F -e 'roboclaws/ai2thor' -e 'roboclaws/games' -e 'tests/unit/games' .githooks/pre-commit tests/contract/dev_tools docs/human README.md ARCHITECTURE.md just/README.md AGENTS.md CLAUDE.md`
  finds only negative tests.
- 2026-06-14: Marked the reduce-entropy loop DONE after the accepted checklist
  reached zero open items. Final verification:
  `just verify::static` passed; `./scripts/dev/run_pytest_standalone.sh tests/unit/scripts/test_python_quality_ratchet.py tests/contract/dev_tools/test_verify_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
  passed. Final saturation audit:
  `node "$HOME/.codex/skills/intuitive-reduce-entropy/scripts/high-noise-summary.mjs"`
  surfaced only the expected historical/planning/generated/test surfaces and
  no new P0/P1 or materially useful P2 candidate in this cleanup class.
