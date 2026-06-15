---
plan_scope: molmospaces-scene-sampler-readiness
status: First slice implemented
created: 2026-06-15
last_reviewed: 2026-06-15
implementation_allowed: true
source:
  - user request to expose a smaller UI sample set and a larger eval-harness stress set
  - discussion that current `molmospaces/val_*` samples only cover `procthor-10k-val`
  - agent-planning-loop review on 2026-06-15
  - reduce-entropy and grill-batch follow-up accepted on 2026-06-15
  - intuitive-preflight contract drafted on 2026-06-15
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - docs/plans/2026-06-14-eval-driven-architecture.md
  - docs/plans/2026-06-15-cross-environment-semantic-map-parity.md
  - roboclaws/launch/worlds.py
  - roboclaws/operator_console/routes.py
  - vendors/molmospaces/docs/assets.md
other_source_targets:
  - ithor
  - procthor-objaverse-val
  - holodeck-objaverse-val
next_flow_scope:
  - fill procthor-10k-val eval stress projection to ten admitted samples
  - add sampler readiness support for ithor
  - add sampler readiness support for procthor-objaverse-val
  - add sampler readiness support for holodeck-objaverse-val
  - turn remaining plan slices into scanner, source-prep, UI, eval, and docs work
---

# MolmoSpaces Scene Sampler Readiness

## Implementation Status

First slice implemented on 2026-06-15.

- Canonical sampler source: `roboclaws/launch/scene_sampler.py`.
  The sampler now enforces both per-source caps: exactly three UI rows when a
  source is visible, and no more than ten eval-stress rows per supported
  `scene_source`.
- Prepared selected-sample room label manifest:
  `data/molmospaces/scene_sampler_room_labels.json`.
- Operator-console UI projection: `procthor-10k-val` samples `0`, `2`, and
  `9` are visible by default.
- Preserved launch aliases: existing `molmospaces/val_0`, `val_1`, `val_2`,
  `val_3`, `val_4`, `val_5`, `val_7`, and `val_9` remain launchable as
  explicit `procthor-10k-val` aliases; non-UI aliases are hidden from the
  default console scene rail.
- Static eval stress projection: `procthor-10k-val` samples `0`, `2`, `3`,
  `5`, and `9` are admitted. The target remains ten samples, so this source is
  recorded as partial rather than complete.
- Rejected current aliases: `val_1` and `val_7` have fewer than three public
  navigation areas; `val_4` is rejected because its FPV preview is
  low-detail/non-reviewable.
- Cross-source rows for `ithor`, `procthor-objaverse-val`, and
  `holodeck-objaverse-val` are normalized `environment_blocked` rows until
  local assets and preview readiness are prepared.
- Eval harness selection now includes `scene-sampler-stress-eval-suite` for
  scene-sampler, launch-catalog, or eval-harness signals.
- Readiness artifact exporter:
  `scripts/operator_console/export_scene_sampler_readiness.py` validates the
  sampler and writes the canonical manifest, eval projection, and per-source
  readiness report without downloading assets or calling live VLMs. It also
  supports explicit UI/eval threshold checks for source-specific gates.
- Source-aware MolmoSpaces world-id parsing is now canonical in
  `roboclaws/launch/scene_sampler.py`. Legacy `molmospaces/val_N` ids parse as
  `procthor-10k-val` aliases, while new ids such as
  `molmospaces/ithor/3` and `molmospaces/holodeck-objaverse-val/12` preserve
  their explicit `scene_source`.
- Operator-console preview rendering and mess-up preview inventory loading now
  use the canonical parser, so future non-`procthor-10k-val` rows will not
  silently render or inspect the wrong scene source.
- Readiness export now includes
  `scene_sampler_source_availability.json`, a no-download/no-VLM source
  availability probe that records MolmoSpaces module, scene root, source
  directory, and candidate XML visibility per source with normalized
  `environment_blocked` reasons.
- Readiness export also includes `scene_sampler_candidate_readiness.json`, a
  no-download/no-VLM candidate packet projection for indices `0..9` per source.
  It carries existing ready/rejected `procthor-10k-val` rows and blocked
  source-aware candidate packets such as `molmospaces/ithor/0` for sources that
  still need real scene preparation.
- Readiness export also includes `scene_sampler_selection_gaps.json`, a
  deterministic scanner worklist projection that records how many UI/eval
  samples each source still needs and which source-aware world ids should be
  scanned next.
- The exporter supports `--require-selection-capacity-source <scene_source>` so
  a future scanner gate can fail when the current candidate worklist cannot
  cover the remaining UI/eval target. Today this intentionally fails for
  `procthor-10k-val` because indices `0..9` only leave two blocked scan
  candidates after the five ready and three rejected rows, while five more
  eval-ready samples are still needed.
- The exporter supports `--candidate-index` and `--candidate-range START:END`
  to expand the no-download availability, candidate-readiness, and
  selection-gap projections before a real scanner run. For example, expanding
  `procthor-10k-val` to `--candidate-range 0:19` gives enough source-aware
  candidate ids to cover the current eval-stress gap.
- Readiness export now writes a generated eval dry-run under
  `generated_eval/`: `scene_sampler_stress.json` plus one sample JSON per
  admitted eval row. These generated payloads match the committed fixtures
  today and give future scanner admission a deterministic way to materialize
  new eval rows.
- Readiness export now writes `scene_sampler_source_prep.json`, a no-download
  source-preparation artifact. It records per-source MolmoSpaces
  `get_scenes(...)` arguments, scene asset versions, candidate index-map paths,
  missing source/XML resources, next scanner world ids, recommended candidate
  ranges, per-candidate install snippets, and operator-run preparation commands
  for `procthor-10k-val`, `ithor`, `procthor-objaverse-val`, and
  `holodeck-objaverse-val`. It is intentionally a manual prep plan, not an
  implicit downloader.
- Source availability and selection-gap artifacts now use MolmoSpaces
  `get_scenes(...)` refs for candidate paths and validity, so source-specific
  numbering such as `ithor`'s `FloorPlan*_physics.xml` entries is not mistaken
  for `val_<index>.xml` availability.
- Readiness export now writes `scene_sampler_scanner_admission.json`, a
  no-download/no-backend/no-VLM dry-run of scanner admission gates. It records
  admitted, rejected, and blocked candidate rows with required gates, missing
  gates, and next actions before any real preview rendering or map-build run is
  allowed.
- MolmoSpaces subprocess backend init now resolves scene XML paths from
  MolmoSpaces `get_scenes(...)` refs before loading MuJoCo or installing scene
  assets. This removes the legacy runtime assumption that every source uses
  `get_scenes_root() / scene_source / val_<index>.xml`, so future scanner runs
  can target source-specific paths such as `ithor/FloorPlan1_physics.xml`.
- Operator-console mess-up preview inventory loading now uses the same
  source-aware scene resolution path, so future source-aware UI rows do not
  silently probe a wrong legacy `val_<index>.xml` location before launch.
- Public launch resolution now accepts source-aware MolmoSpaces scanner
  candidate world ids such as `molmospaces/ithor/1` by creating hidden dynamic
  world specs with explicit `scene_source`, `scene_index`, and `map_bundle=none`
  overrides. These candidates are launchable for scanner/product smoke work but
  remain absent from the default operator-console scene rail until admitted.
- Readiness export now writes
  `scene_sampler_scanner_execution_plan.json`, a no-download/no-backend/no-VLM
  command plan for each next scanner candidate. It records per-candidate
  install commands, preview render commands, map-build product-smoke commands,
  missing paths, missing gates, and whether the candidate is currently
  `ready_for_product_smoke` or still `blocked_missing_resources`.
- Scanner execution runner:
  `scripts/operator_console/run_scene_sampler_scanner_plan.py` consumes
  `scene_sampler_scanner_execution_plan.json`, skips blocked candidates without
  side effects, and runs preview plus map-build product-smoke commands only for
  candidates marked `ready_for_product_smoke`. On this host, the current
  artifact produces `output/scene-sampler-scanner/scanner_run.json` with
  `status=no_ready_candidates`, `candidate_count=33`,
  `ready_candidate_count=0`, `executed_candidate_count=0`, and
  `skipped_candidate_count=33`.
- Eval projection metadata now records explicit per-source and aggregate
  readiness counts for the stress set: `support_status`, `ready_count`,
  `needed_count`, `partial_gap_count`, `blocked_count`, `rejected_count`, and a
  summary with complete, partial, blocked, ready, remaining, blocked-row, and
  rejected-row counts. This lets the eval suite and exported readiness
  artifacts prove `procthor-10k-val` is partial and the three other source
  targets are blocked without inferring that state from raw `blocked_rows`.
- Scanner admission gates now accept the current prepared room-label provenance
  token (`prepared_visual_label_manifest`) and reviewable preview statuses.
  That keeps future real scanner candidates from being incorrectly blocked on
  `trusted_category_provenance` or `preview_metadata` after source assets and
  preview packets are prepared.
- Scanner-run output now includes per-source summaries with candidate, ready,
  executed, skipped, and failed counts. Running the expanded `0:19` scanner
  plan on this host records `status=no_ready_candidates` with 35 candidates,
  0 ready candidates, 0 executed commands, and per-source
  `no_ready_candidates` summaries for `procthor-10k-val`, `ithor`,
  `procthor-objaverse-val`, and `holodeck-objaverse-val`.
- Source-prep install snippets now resolve MolmoSpaces `get_scenes(...)` refs
  the same way the runtime loader does: direct paths and dict refs such as
  `base` / `physics` / `ceiling` are converted to an installable scene XML
  path under `get_scenes_root()` before calling
  `install_scene_with_objects_and_grasps_from_path`. This keeps manual
  operator prep aligned with source-aware runtime resolution.
- No-download readiness artifacts now carry top-level rollups for blocked
  evidence: source availability summarizes available/blocked source counts,
  source prep summarizes missing resources by type and reason, scanner
  admission summarizes admitted/blocked/rejected rows plus missing gate counts,
  and scanner execution summarizes ready/blocked product-smoke candidates.
  The detailed per-candidate rows remain available, but future flows can read
  source/gate/resource status directly from summaries.
- Selection-gap artifacts now include a next-Flow worklist: per-source
  `selection_capacity_status`, `next_action`, UI/eval scan-candidate counts,
  and a top-level worklist/summary. This makes the remaining `procthor-10k-val`,
  `ithor`, `procthor-objaverse-val`, and `holodeck-objaverse-val` work explicit:
  expand the candidate range when capacity is insufficient, otherwise run
  source prep before scanner admission when assets are still blocked.
- Readiness export now supports `--require-scanner-ready-source <scene_source>`.
  This gate fails until a source has at least one scanner candidate marked
  `ready_for_product_smoke`, so source-prep work can prove when preview plus
  map-build product-smoke execution is actually allowed.
- Candidate-readiness artifacts now include a top-level summary for total
  candidates, ready/blocked/rejected counts, UI/eval ready counts, and
  remaining UI/eval target counts. This gives future scanner and eval-refresh
  flows the same source-level signal without parsing every candidate packet.

Verification run on 2026-06-15:

```bash
./scripts/dev/run_pytest_standalone.sh tests/unit/launch tests/unit/operator_console tests/unit/evals -q
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_cross_environment_semantic_map_parity.py tests/contract/maps/test_actionable_semantic_map_snapshot.py -q
ruff check roboclaws/launch/scene_sampler.py roboclaws/launch/worlds.py roboclaws/evals/runner.py roboclaws/operator_console/routes.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_routes.py tests/unit/operator_console/test_static_assets.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py tests/unit/evals/test_eval_harness_selector.py skills/eval-harness/scripts/select_eval_harness.py skills/eval-harness/scripts/eval_harness_rows.py
just agent::eval suite=scene_sampler_stress budget=smoke output_dir=/tmp/roboclaws-scene-sampler-eval-rerun
just agent::eval suite=map_build_consumer budget=focused output_dir=/tmp/roboclaws-map-build-consumer-eval
just agent::eval recommend plan=docs/plans/2026-06-15-molmospaces-scene-sampler-readiness.md budget=focused output_dir=/tmp/roboclaws-scene-sampler-harness
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline output_dir=/tmp/roboclaws-scene-sampler-product
./scripts/dev/run_pytest_standalone.sh tests/unit/launch tests/unit/operator_console tests/unit/evals -q
ruff check roboclaws/launch/scene_sampler.py roboclaws/operator_console/messup.py scripts/operator_console/render_scene_previews.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_messup.py
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py --output-dir /tmp/roboclaws-scene-sampler-readiness-availability --require-ui-supported-source procthor-10k-val
./scripts/dev/run_pytest_standalone.sh tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py -q
ruff check scripts/molmo_cleanup/molmospaces_subprocess_worker.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py
./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console/test_messup.py -q
ruff check roboclaws/operator_console/messup.py tests/unit/operator_console/test_messup.py
./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_scene_sampler.py tests/unit/launch/test_environment_setup_catalog.py -q
ruff check roboclaws/launch/worlds.py roboclaws/launch/catalog.py tests/unit/launch/test_scene_sampler.py
./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py -q
ruff check roboclaws/launch/scene_sampler.py scripts/operator_console/export_scene_sampler_readiness.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py --candidate-range 0:10 --no-generated-eval
./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console/test_scene_sampler_scanner_runner.py -q
ruff check scripts/operator_console/run_scene_sampler_scanner_plan.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py
.venv/bin/python scripts/operator_console/run_scene_sampler_scanner_plan.py
./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py tests/unit/evals/test_eval_models.py -q
./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py -q
ruff check roboclaws/launch/scene_sampler.py scripts/operator_console/export_scene_sampler_readiness.py scripts/operator_console/run_scene_sampler_scanner_plan.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py --output-dir /tmp/roboclaws-scene-sampler-projection-summary --no-source-availability --no-candidate-readiness --no-selection-gaps --no-source-prep --no-scanner-admission --no-scanner-execution-plan --no-generated-eval
./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py -q
ruff check roboclaws/launch/scene_sampler.py scripts/operator_console/export_scene_sampler_readiness.py scripts/operator_console/run_scene_sampler_scanner_plan.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py --output-dir /tmp/roboclaws-scene-sampler-admission-gate --no-generated-eval
./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console/test_scene_sampler_scanner_runner.py -q
ruff check scripts/operator_console/run_scene_sampler_scanner_plan.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py
.venv/bin/python scripts/operator_console/run_scene_sampler_scanner_plan.py --plan /tmp/roboclaws-scene-sampler-range-0-19/scene_sampler_scanner_execution_plan.json --output /tmp/roboclaws-scene-sampler-range-0-19/scanner_run.json
./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py -q
ruff check roboclaws/launch/scene_sampler.py scripts/operator_console/export_scene_sampler_readiness.py scripts/operator_console/run_scene_sampler_scanner_plan.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py --output-dir /tmp/roboclaws-scene-sampler-source-prep-snippets --candidate-range 0:19 --no-generated-eval
./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py -q
ruff check roboclaws/launch/scene_sampler.py scripts/operator_console/export_scene_sampler_readiness.py scripts/operator_console/run_scene_sampler_scanner_plan.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py tests/unit/operator_console/test_scene_sampler_scanner_runner.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py --output-dir /tmp/roboclaws-scene-sampler-summary-rollups --candidate-range 0:19 --no-generated-eval
./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py -q
ruff check roboclaws/launch/scene_sampler.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py --output-dir /tmp/roboclaws-scene-sampler-next-flow-worklist --candidate-range 0:19 --no-generated-eval
./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console/test_scene_sampler_readiness_export.py -q
ruff check scripts/operator_console/export_scene_sampler_readiness.py tests/unit/operator_console/test_scene_sampler_readiness_export.py
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py --output-dir /tmp/roboclaws-scene-sampler-scanner-ready-gate --candidate-range 0:19 --require-scanner-ready-source ithor --no-generated-eval
./scripts/dev/run_pytest_standalone.sh tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py -q
ruff check roboclaws/launch/scene_sampler.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_scene_sampler_readiness_export.py
```

Current limits feeding the next Flow:

- This first slice does not run a live provider or implicit VLM labeler. That
  is intentional and remains a non-goal for sampler, eval, and CI paths.
- Non-`procthor-10k-val` sources are represented by blocked rows today, not
  supported UI sources. The next Flow should turn `ithor`,
  `procthor-objaverse-val`, and `holodeck-objaverse-val` from blocked rows into
  either supported source rows or explicit asset/runtime-blocked rows.
- The eval-stress target of ten samples per supported source is not complete
  yet. The next Flow should first fill `procthor-10k-val` from five to ten
  admitted eval samples, then apply the same admission rules to the other
  source targets.
- The static smoke eval verifies runtime-map artifact readiness and sampler
  admission metadata; full scene-specific runtime output remains a product-run
  or later scanner proof.
- The readiness exporter is a deterministic preparation artifact scaffold. It
  does not yet render or admit new `ithor`, `procthor-objaverse-val`, or
  `holodeck-objaverse-val` samples; those remain blocked until local assets and
  preview/map-build evidence exist.
- Run source availability and scanner prep through the repo-local runtime
  (`.venv/bin/python` or `uv run`), not the host default Python. On this host,
  the host default Python is a conda Python 3.13 that cannot import
  `molmo_spaces`, while the repo-local Python 3.12 runtime can. Under the
  repo-local runtime, the current blocker is missing candidate XML files:
  non-`procthor-10k-val` source directories exist but have no `val_<index>.xml`
  candidates, and `procthor-10k-val` does not yet have enough expanded-range
  candidate XMLs to scan/admit ten eval samples.
- The availability probe records `python_executable`, `python_version`, and
  captured MolmoSpaces import/scene-root stdout in the artifact. This keeps the
  exporter CLI stdout valid JSON even when upstream MolmoSpaces prints
  `Using SCENES_ROOT: ...` during import.

## Next Flow Development Plan

The remaining sampler work is now explicit next-Flow development scope, not a
loose parked-todo list. In this plan, "other sources" means exactly these
planned MolmoSpaces scene sources:

- `ithor`
- `procthor-objaverse-val`
- `holodeck-objaverse-val`

The next Flow should also finish the current source's stress target:

- `procthor-10k-val`: raise eval-stress coverage from five admitted samples to
  ten admitted samples while keeping the operator-console UI set at exactly
  three default-visible samples.

Recommended next Flow goal:

```text
Implement the remaining MolmoSpaces scene sampler plan: finish ten
eval-stress samples for procthor-10k-val, add source-aware readiness support
for ithor, procthor-objaverse-val, and holodeck-objaverse-val, expose exactly
three UI-ready samples per supported source, and keep partial or unavailable
sources represented by normalized blocked eval rows.
```

Next Flow implementation slices:

1. **Scanner And Candidate Preparation**
   - Backend scene resolution is now source-aware in
     `scripts/molmo_cleanup/molmospaces_subprocess_worker.py`; scanner work can
     call product/map-build routes with non-`procthor-10k-val` source ids
     without the worker silently falling back to `val_<index>.xml` paths.
   - Public launch resolution now accepts hidden source-aware candidate world
     ids such as `molmospaces/ithor/1`, so the scanner can product-smoke
     candidate ids emitted by the readiness artifacts before those ids are
     exposed in the operator console.
   - `scene_sampler_scanner_execution_plan.json` now turns those scanner
     candidates into explicit install, preview-render, and map-build product
     smoke commands while preserving current blocked status when local scene
     XML/resources are missing.
   - Turn the current static preview/readiness facts into a repeatable scanner
     or preparation command that can inspect candidate indices per
     `scene_source`, skip blocked candidates without side effects, and run
     preview plus map-build product-smoke commands only for candidates that are
     explicitly `ready_for_product_smoke`.
   - The scanner may use existing local assets and preview renderers, but must
     not download large assets or call live VLMs implicitly.
   - Output machine-readable readiness packets with preview status, public room
     count, waypoint count, category provenance, selected reason, and canonical
     `failure_class`.
   - Current scaffold: run
     `.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py`
     or `uv run python scripts/operator_console/export_scene_sampler_readiness.py`
     to write validated sampler artifacts under
     `output/scene-sampler-readiness/`.
     The export now includes no-download source availability evidence,
     candidate readiness packets, selection-gap worklists, and a
     source-preparation artifact with manual operator commands. It also writes
     a scanner-admission dry-run artifact that names missing gates before any
     backend render or live labeler is allowed. A later slice should replace or
     extend the static facts with real scanner candidate output for new source
     families after the MolmoSpaces runtime and scene assets are visible.
   - Strict threshold mode is available for gates. For example,
     `--require-ui-supported-source procthor-10k-val` should pass today, while
     `--require-eval-complete-source procthor-10k-val` should fail until the
     source reaches ten eval-stress samples.
   - Scanner-ready threshold mode is available for source-prep proof. For
     example, `--require-scanner-ready-source ithor` should fail until at least
     one `ithor` candidate has local source assets and can run preview plus
     map-build product smoke.
   - Selection-capacity threshold mode is also available. For example,
     `--require-selection-capacity-source procthor-10k-val` should fail until
     the candidate range expands beyond `0..9` or enough new candidates are
     admitted to cover the remaining eval-stress gap.
   - Candidate-range mode is available for that expansion. For example,
     `--candidate-range 0:19 --require-selection-capacity-source procthor-10k-val`
     should pass the capacity gate while still leaving actual scene admission to
     later scanner evidence.

2. **Source Prep / Install-Plan Artifact**
   - Add a no-download artifact that lists the exact missing
     `scene_source`, `scene_index`, and XML/resource path needed for scanner
     work.
   - Include explicit operator commands or MolmoSpaces install ids for
     preparing `ithor`, `procthor-objaverse-val`,
     `holodeck-objaverse-val`, and the expanded `procthor-10k-val`
     candidate range.
   - Keep this as a prep plan, not an implicit downloader. The scanner and CI
     must continue to report normalized blocked rows until assets are actually
     present in the repo-local MolmoSpaces runtime.

3. **`procthor-10k-val` Stress Fill**
   - Scan additional non-contiguous `procthor-10k-val` candidates until ten
     samples pass eval-stress admission.
   - Keep `val_0`, `val_2`, and `val_9` as the visible UI set unless the scan
     proves a materially better three-sample set and the plan is updated with
     that reason.
   - Generate or update eval sample JSON and projection metadata from the
     scanner output.

4. **Cross-Source Readiness**
   - Add source-aware candidate rows for `ithor`,
     `procthor-objaverse-val`, and `holodeck-objaverse-val`.
   - For each source, admit three UI samples only after all UI readiness gates
     pass.
   - For each source, admit up to ten eval-stress samples only after eval gates
     pass.
   - If assets, loaders, room metadata, preview rendering, or map-build
     artifacts are unavailable, keep normalized blocked rows with exact
     asset/runtime reasons instead of silently omitting the source.

5. **World Id And Console Projection**
   - Preserve existing `molmospaces/val_N` aliases for
     `procthor-10k-val`.
   - Use explicit source-aware ids for newly visible non-`procthor-10k-val`
     worlds, such as `molmospaces/ithor/<index>` or
     `molmospaces/procthor-objaverse-val/<index>`.
   - Initial parser support is implemented in `parse_molmospaces_world_id()`
     and is already consumed by preview rendering and mess-up preview inventory
     loading. The remaining work is to feed scanner-admitted rows into
     `WORLD_SPECS` and the default console scene rail.
   - Ensure default operator-console worlds are only UI-admitted rows; hidden
     aliases or blocked rows must not appear in the default scene rail.

6. **Eval Projection And Harness**
   - Extend `scene_sampler_stress` so aggregate metadata reports ready,
     partial, and blocked counts per `scene_source`.
   - Keep static suite/sample JSON unless dynamic `sample_manifest` support
     becomes necessary during implementation.
   - Generated eval dry-run artifacts are available from the readiness exporter
     and should be used to compare or refresh committed static suite/sample JSON
     after new scanner-admitted rows exist.
   - Keep `sampler_admission` deterministic and reject heuristic category
     provenance such as `heuristic_room_label`, `heuristic_room_count`, and
     `room_area_fallback`.

7. **Docs And Status Alignment**
   - Update `docs/human/molmospaces-settings.md` and
     `docs/human/evaluation.md` after the next supported sample matrix changes.
   - Update `STATUS.md` only if the repo-level current focus or blocker changes.

Everything above is next-Flow implementation scope. Items can finish as either
admitted samples or normalized blocked rows, but they should not be left as
unclassified parked information after the next Flow runs.

Next Flow acceptance:

- `procthor-10k-val` has ten eval-stress-admitted samples, or the scanner
  records exact blocked reasons for the remaining candidates.
- Each of `ithor`, `procthor-objaverse-val`, and
  `holodeck-objaverse-val` has either three UI-ready samples and up to ten
  eval-ready samples, or normalized blocked rows that name the missing asset,
  loader, metadata, preview, waypoint, or map-build requirement.
- No default UI row is exposed for a source with fewer than three UI-ready
  samples.
- No eval source is marked complete with fewer than ten eval-ready samples.
- No sampler, eval, or CI path calls a live VLM implicitly.
- No public sampler/world/eval metadata exposes private scorer truth, generated
  mess sets, hidden target lists, or full simulator inventories.

Next Flow verification:

```bash
./scripts/dev/run_pytest_standalone.sh tests/unit/launch tests/unit/operator_console tests/unit/evals -q
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_cross_environment_semantic_map_parity.py tests/contract/maps/test_actionable_semantic_map_snapshot.py -q
ruff check roboclaws/launch/scene_sampler.py roboclaws/launch/worlds.py roboclaws/evals/runner.py roboclaws/operator_console/routes.py tests/unit/launch/test_scene_sampler.py tests/unit/operator_console/test_routes.py tests/unit/operator_console/test_static_assets.py tests/unit/evals/test_eval_models.py tests/unit/evals/test_eval_runner.py tests/unit/evals/test_eval_harness_selector.py skills/eval-harness/scripts/select_eval_harness.py skills/eval-harness/scripts/eval_harness_rows.py
just agent::eval suite=scene_sampler_stress budget=smoke
just agent::eval suite=map_build_consumer budget=focused
just agent::eval recommend plan=docs/plans/2026-06-15-molmospaces-scene-sampler-readiness.md budget=focused
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py
.venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py \
  --require-ui-supported-source procthor-10k-val
```

Run at least one product smoke for any newly UI-admitted source:

```bash
just run::surface surface=household-world world=<new-selected-ui-world> \
  backend=mujoco preset=map-build agent_engine=direct-runner \
  evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline
```

## Goal

Make Roboclaws sample MolmoSpaces scenes by explicit source identity instead of
by a small contiguous `procthor-10k-val` curated UI set. The operator console
should expose a small curated set for humans, while eval suites get a larger stress set that
proves map readiness and downstream actionability before a scene can count.

The target split is:

- operator console: 3 UI-visible samples per supported split-qualified
  `scene_source` on the primary MolmoSpaces runtime path;
- eval harness: 10 stress samples per supported split-qualified `scene_source`
  on the primary MolmoSpaces runtime path;
- every selected scene must pass explicit map, observation, navigation, and
  artifact-readiness gates before it enters either set.

In this plan, the primary MolmoSpaces runtime path is MuJoCo. Isaac Lab is not
required for MolmoSpaces scene sampling; it remains useful as a previous
sanity-check path and is expected to matter mostly for digital twins. Use these
scene identity fields consistently:

- `scene_family` is the broad MolmoSpaces family, such as `procthor-10k`,
  `procthor-objaverse`, `holodeck`, or `ithor`.
- `scene_split` is the dataset split, such as `train`, `val`, or `test` when the
  source has splits.
- `scene_source` is the split-qualified machine key passed to launch/runtime
  code, such as `procthor-10k-val`, `procthor-objaverse-val`,
  `holodeck-objaverse-val`, or `ithor`.

## Plan Review Mode

Direct shaping from the user request, followed by an agent-planning-loop review,
an accepted reduce-entropy / grill-batch follow-up, and an intuitive-preflight
contract on 2026-06-15.

Planning-loop scouts:

- `intuitive-reduce-entropy` plan entropy scout: found source/split naming
  drift, blocked-row policy gaps, missing offline sampler proof, world-id
  migration ambiguity, and deterministic selection tie-breaker risk.
- `grill-with-docs-batch` read-only critique scout: recommended preserving
  current `molmospaces/val_N` ids for the first slice, using one canonical
  sampler schema with UI/eval projections, reusing canonical eval
  `failure_class` values, and avoiding asset downloads as a planning
  prerequisite.

## Source Evidence

- `vendors/molmospaces/docs/assets.md` - MolmoSpaces scene families include
  `ithor`, `procthor-10k`, `procthor-objaverse`, and `holodeck`, with separate
  installable split ids.
- `vendors/molmospaces/molmo_spaces/housegen/exporter.py` - `procthor-10k`
  exporter treats train as 10,000 houses and val/test as 1,000 each.
- `roboclaws/launch/worlds.py` - current console worlds are
  `molmospaces/val_0`, `val_1`, `val_2`, `val_3`, `val_4`, `val_5`, `val_7`,
  and `val_9`, all bound to `scene_source=procthor-10k-val`.
- `docs/plans/2026-06-14-eval-driven-architecture.md` - eval suites are a
  first-class architecture layer with samples, trials, graders, and aggregate
  metrics.
- `roboclaws/evals/runner.py` and `roboclaws/evals/cli.py` - current eval suite
  execution loads static `sample_refs`; it does not accept a dynamic
  `sample_manifest` override.
- `roboclaws/evals/live_runtime.py` - absent eval launch overrides currently
  default `scene_source` to `procthor-10k-val`, so sampler-generated samples
  must carry explicit source metadata.
- `docs/plans/2026-06-15-cross-environment-semantic-map-parity.md` - semantic
  maps need explicit source-frame, polygon role, geometry source, and alignment
  status before reports or consumers can trust them.
- `roboclaws/agents/provider_registry.py` - `provider_profile=codex-env`
  defaults to `model=gpt-5.5`, requires `CODEX_BASE_URL` and `CODEX_API_KEY`,
  and declares image input capability.
- `roboclaws/maps/actionable_snapshot.py` and
  `roboclaws/household/realworld_contract.py` - current room-category fallback
  logic can infer categories from labels; sampler admission must treat that as
  candidate evidence only, not as trusted category provenance.

## Decisions Already Made

- Keep the operator console curated and small: it should show three samples per
  supported `scene_source` on the primary MolmoSpaces runtime path, not every
  scene that evals can run.
  The cap applies to world cards / scene choices, not to every derived
  intent/backend/agent-engine route row in the console matrix.
- Give eval harness broader pressure: ten samples per supported
  `scene_source` on the primary MolmoSpaces runtime path.
- Sample ids may be non-contiguous. Selection should optimize coverage and
  readiness, not make a pretty `val_0..val_9` list.
- Do not admit scenes just because they render. A scene must satisfy the map and
  actionability gates below.
- Treat current `procthor-10k-val` console samples as a curated UI set, not the
  representative MolmoSpaces coverage set.
- Use one canonical sampler schema as the source of truth, then materialize two
  projections: a curated UI manifest for `roboclaws/launch/worlds.py` and the
  operator console, and a frozen eval-stress projection as normal eval suite /
  sample JSON consumed by `roboclaws/evals/runner.py`.
- Preserve existing `molmospaces/val_N` ids as aliases or stable current
  `procthor-10k-val` ids during the first implementation slice. New
  non-`procthor-10k-val` rows should use source-aware ids, such as
  `molmospaces/procthor-objaverse-val/4`, or carry equivalent explicit
  `scene_source` metadata before they become public.
- Use canonical eval `failure_class` values from `roboclaws.evals.models` for
  persisted eval results. Human reports may summarize sampler-specific buckets,
  but the sampler should not create a second persisted failure taxonomy.
- Skip scenes that are too small to be useful for semantic-map and room-category
  evaluation. The default threshold is at least three public rooms or navigation
  areas.
- Prefer source-provided room categories. If a promising scene lacks reliable
  category metadata, environment preparation may run an explicit visual labeling
  job over preview images to produce a cached public room-category manifest with
  provenance. The sampler and eval harness consume that prepared manifest; they
  must not call live models implicitly.
- Prepared visual room labels for selected UI/eval samples should be
  repo-owned, reviewable manifests with provenance. Large raw screenshots,
  rejected candidate evidence, and exploratory labeling outputs should stay in
  ignored `output/` artifacts rather than becoming committed fixtures.
- A `scene_source` is UI-supported only after three samples pass all UI gates.
  If fewer than three samples pass, keep that source out of the default
  operator-console scene set and record blocked or partial sampler/eval packets
  with reasons.
- Eval stress support targets ten passing samples per `scene_source`. If a
  source cannot yet fill ten, eval artifacts should record blocked or partial
  rows until ten passing samples exist; do not silently downgrade the target.
- The default prepared visual room labeler is `provider_profile=codex-env` with
  `model=gpt-5.5`. The labeler remains configurable, and optional multi-model
  QA can use other vision-capable routes as cross-checks.
- Existing heuristic category derivation from room labels or room counts cannot
  satisfy the room-category provenance gate. It may seed low-confidence
  candidate evidence for review, but admission requires source metadata or a
  prepared visual-label manifest with provenance.

## Idea Shaping Decisions

| # | Question | Classification | Decision | Rationale | Revisit if |
|---|----------|----------------|----------|-----------|------------|
| 1 | Should UI and eval use the same sample count? | User-owned, answered | No. UI gets 3 per supported source; eval gets up to 10 per supported source. | The user wants the UI readable and the eval harness broader. | UI review shows humans need more visual choices, or eval runtime is too expensive. |
| 2 | Should sample indices be contiguous? | User-owned, answered | No. Non-contiguous indices are allowed. | Coverage and readiness matter more than consecutive ids. | A backend installer can only cache contiguous ranges efficiently. |
| 3 | What counts as a backend here? | User-owned, answered | For MolmoSpaces sampling, default to MuJoCo. Isaac Lab is not required for these samples and is mainly a digital-twin path. | Earlier Isaac work proved it can work; this sampler should not be blocked by Isaac parity. | A future MolmoSpaces-on-Isaac product goal becomes active. |
| 4 | Which scene sources enter the first slice? | User-owned, answered | Cover multiple samples from `procthor-10k-val`, `ithor`, `procthor-objaverse-val`, and `holodeck-objaverse-val` when locally available; otherwise emit blocked rows. | The goal is representative MolmoSpaces source diversity, not multi-backend parity for one scene. | Asset availability or loader support makes a source unavailable. |
| 5 | Should scene category metadata be required? | User-owned, answered | Prefer source-provided room categories; if missing, allow an environment-preparation visual labeling job to create cached room-category labels with provenance. Skip scenes with fewer than three rooms/navigation areas. Leave uncertain rooms unlabeled instead of guessing. | There are many scenes, so tiny/simple scenes are not worth sampler slots, and fake categories are worse than missing labels with honest provenance. | Product direction requires only source-ground-truth categories. |
| 6 | Should blocked scene families appear in the UI? | Implementation default | Keep blocked/unavailable families out of the default UI card set, but keep normalized blocked rows in sampler/eval artifacts. | The user asked for a readable UI and broader eval stress coverage; disabled UI rows can be added later if useful. | Operators need to inspect unavailable families before installing assets. |
| 7 | How should eval stress samples be wired initially? | Implementation default | Generate normal eval suite/sample JSON from the sampler projection before adding any dynamic `sample_manifest` CLI. | Current `roboclaws/evals/runner.py` loads static `sample_refs`, and `roboclaws/evals/cli.py` / eval-harness do not accept `sample_manifest` today. | Dynamic manifest selection becomes a repeated workflow need. |
| 8 | How are UI/eval sample tie-breakers chosen? | Implementation default | Sort by `scene_source`, readiness status, room count threshold, category provenance quality, quality score, coverage/diversity score, then `scene_index`; persist generator version and selected reason so reruns do not churn silently. | Non-contiguous selection still needs deterministic output. | A later human curation process explicitly pins samples by hand. |
| 9 | Are prepared visual room labels committed or local-only? | User-owned, answered | Commit only the small selected-sample label manifests with provenance; keep large raw screenshots and exploratory evidence under ignored `output/`. | UI/eval curated samples need reproducible labels, but the repo should not absorb bulky generation evidence. | Label evidence becomes too large or legally sensitive to keep in repo. |
| 10 | What if a source cannot fill 3 UI or 10 eval samples? | User-owned, answered | UI exposes a source only after exactly three passing samples exist; eval records blocked/partial rows until ten passing samples exist. | Humans should not see under-ready sources as selectable defaults, while eval should preserve pressure and reasons. | The operator console gets an explicit unavailable-source inspection mode. |
| 11 | Which model route labels missing room categories by default? | User-owned, answered | Use `provider_profile=codex-env`, `model=gpt-5.5` by default; keep the route configurable and allow optional multi-model QA. | Model id alone is not enough to reproduce the route; room-category labeling benefits from stronger visual reasoning. | `codex-env` loses image capability, route health, or acceptable cost. |
| 12 | Can heuristic room-category inference pass admission? | User-owned, answered | No. Heuristics from room labels or room counts are candidate evidence only, not trusted category provenance. | Existing fallbacks are useful for rough maps but would create false confidence in curated sample gates. | Source metadata or a reviewed label manifest later encodes equivalent categories explicitly. |

## Non-Goals

- Do not make all MolmoSpaces scenes visible in the operator console.
- Do not require live providers, real robot hardware, or OpenClaw Gateway to
  select or validate samples.
- Do not promote generated fixture inventories, private scorer truth, or hidden
  task manifests into public map inputs.
- Do not make UI labels by guessing from room count. UI labels must come from
  `room_label` and trusted `category` / `room_category_hints` provenance.
- Do not treat heuristic room-label parsing as room-category ground truth for
  curated sampler admission.
- Do not block the first slice on full Objaverse or Holodeck manipulation
  parity if basic map/navigation readiness for those families needs separate
  backend work.
- Do not require the same MolmoSpaces scene to pass multiple runtime backends.
  This plan samples scene-source diversity; backend parity belongs to separate
  backend validation work.

## Target Scene Sources

First-slice source:

- `procthor-10k-val` - current Roboclaws default; generated houses with THOR
  assets.

Planned coverage sources:

- `ithor` - hand-crafted scenes with articulated assets; small but useful for
  regular room and object layouts.
- `procthor-objaverse-val` - ProcTHOR layouts with Objaverse objects; useful
  for object-category and visual diversity.
- `holodeck-objaverse-val` - LLM-generated scenes with Objaverse objects;
  useful for long-tail geometry and semantic mismatch stress.

The final support matrix should be data-driven rather than hard-coded in the
operator console. Unsupported combinations should appear as blocked eval rows
with reason packets, not silent omissions.

For UI exposure, `supported` means three samples for that `scene_source` have
passed all UI readiness gates. For eval stress, support is partial until ten
samples pass; blocked and partial rows should remain visible in eval artifacts.

## Readiness Gates

A scene can enter the UI sample set only when all UI readiness gates pass:

- installs or resolves through the MolmoSpaces resource manager without manual
  path edits;
- initializes under the target runtime backend;
- produces non-blank FPV, chase, top-down, and semantic-map preview artifacts;
- exposes public room or navigation-area rows with stable `room_id` and
  `room_label`;
- has at least three public rooms or navigation areas;
- exposes room-category hints from source metadata when available, or from a
  prepared room-category label manifest with provenance when source metadata
  does not provide reliable categories;
- does not rely on heuristic room-label or room-count category inference to pass
  the category provenance gate;
- has at least one reachable generated exploration waypoint per public
  room/navigation area;
- renders semantic map labels from map metadata, not the current room-count
  hard-coded UI fallback.

A scene can enter the eval stress set only when all UI gates pass plus:

- `preset=map-build` can write `runtime_metric_map.json` and
  `actionable_semantic_map_snapshot.json`;
- the Runtime Metric Map records polygon role, geometry source, source frame,
  and alignment status according to the cross-environment semantic-map parity
  plan;
- a deterministic cleanup or no-preset open household consumer-contract check
  can consume the map without stale room references;
- sampler admission does not require every scene to complete a full cleanup or
  open-ended task successfully; full task success is measured by downstream eval
  rows after admission;
- the checker can map failures into canonical eval `failure_class` values, with
  sampler-specific summary buckets only in human-readable reports;
- sample metadata records expected resource cost, known limitations, and
  blocked capabilities.

## Smallest Demo

Replace the current implicit `procthor-10k-val` UI list with a sampler manifest
that selects three non-contiguous scenes per supported `scene_source` on the
primary MuJoCo path:

```text
scene_source=procthor-10k-val        samples: 0, 4, 9
scene_source=ithor                   samples: <3 passing indices>
scene_source=procthor-objaverse-val  samples: <3 passing indices or blocked>
scene_source=holodeck-objaverse-val  samples: <3 passing indices or blocked>
```

Those exact indices are placeholders. The implementation should run the
readiness scanner and choose the first three high-quality, diverse samples that
pass gates, then write the chosen indices into the manifest.

Implemented first-slice indices differ from the placeholder because `val_4` has
a low-detail FPV preview: UI uses `0`, `2`, and `9`; eval stress uses `0`, `2`,
`3`, `5`, and `9`.

## Fuller Demo

Create a scene-sampler pipeline that produces two manifests:

```text
roboclaws/launch/worlds.py or data manifest
  -> UI curated manifest: 3 passing samples per scene_source
  -> eval stress projection: 10 passing samples per scene_source
  -> operator console routes and preview assets
  -> eval suite sample rows and blocked reason packets
```

The fuller demo should cover at least:

- `procthor-10k-val` on MuJoCo;
- `ithor` on MuJoCo when it can load cleanly;
- blocked or accepted rows for `procthor-objaverse-val` and
  `holodeck-objaverse-val`, with asset/runtime reasons if they cannot load yet.

## Acceptance Criteria

- The repo has a canonical scene sampler manifest or generator that distinguishes
  UI samples from eval stress samples.
- Operator console shows three UI samples per supported `scene_source` on the
  primary MuJoCo path, with non-contiguous indices allowed.
- Eval harness can select ten stress samples per supported
  `scene_source` through generated eval suite/sample JSON, or
  records blocked rows with normalized reasons.
- Sources with fewer than three UI-ready samples are not exposed in the default
  operator-console scene set; sources with fewer than ten eval-ready samples
  keep normalized blocked/partial eval rows.
- Every admitted scene has machine-readable readiness evidence for map,
  preview, navigation waypoint, and downstream actionability gates.
- Eval admission requires map-build artifact readiness and a deterministic
  consumer-contract check, not full cleanup/open-task success for every sample.
- Every admitted scene has at least three public rooms or navigation areas.
- Every admitted scene has room-category provenance: source metadata preferred,
  prepared visual labels allowed, uncertain labels may be omitted, fake
  room-count labels forbidden, and heuristic room-label parsing cannot satisfy
  the gate.
- Prepared visual room labels for selected samples are reproducible repo-owned
  manifests with provider profile, model id, prompt or labeler version, source
  images, view types, and confidence or uncertainty notes.
- Current `molmospaces/val_N` world ids either remain explicit
  `procthor-10k-val` aliases or migrate through a tested source-aware id path;
  no new console or eval row may rely on a source-opaque world id.
- The current hard-coded 2-room/4-room semantic label fallback is removed or
  bypassed for selected samples.
- Docs explain that `procthor-10k-val` means the `val` split of the
  `procthor-10k` family, not 10,000 val scenes.

## Verification

Planning/scanner unit gates:

```bash
./scripts/dev/run_pytest_standalone.sh \
  tests/unit/launch \
  tests/unit/operator_console \
  tests/unit/evals \
  -q
```

Map contract gates:

```bash
./scripts/dev/run_pytest_standalone.sh \
  tests/contract/maps/test_cross_environment_semantic_map_parity.py \
  tests/contract/maps/test_actionable_semantic_map_snapshot.py \
  -q
```

Product smoke gates for selected samples:

```bash
just run::surface surface=household-world world=<selected-ui-world> \
  backend=mujoco preset=map-build agent_engine=direct-runner \
  evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline
```

Eval harness gate:

```bash
just agent::eval suite=map_build_consumer budget=focused
```

Current eval execution consumes static `sample_refs`, so the first
implementation path should generate committed or generated suite/sample JSON
from the sampler eval projection. Adding `sample_manifest=<...>` support is a
separate optional slice, not an assumption of this plan.

If non-`procthor-10k-val` assets are not locally installed, verification should
emit blocked packets that name the missing asset family and exact install/cache
requirement.

The planning/scanner unit gates must include a no-download fixture that feeds
unavailable `ithor`, `procthor-objaverse-val`, or `holodeck-objaverse-val`
metadata and asserts normalized blocked packets without starting a simulator.

The planning/scanner unit gates must also assert that label-derived heuristic
categories such as fallback `room_area` do not pass the category provenance
gate unless a source metadata record or prepared label-manifest provenance is
present.

## Vertical Slices

1. **Sampler Contract**
   - Add a canonical manifest schema for `scene_family`, `scene_split`,
     `scene_source`, scene index, runtime path, UI/eval lane, room count,
     category provenance, readiness status, preview paths, selected reason,
     generator version, and blocked reason.
   - Owning layers: Worlds / Scenes, Backend Runtime / Environment Primitive,
     Eval Suites, Artifacts.

2. **Readiness Scanner**
   - Implement a scanner that tries candidate scenes, renders preview artifacts,
     inspects room/navigation-area metadata, checks waypoints, and writes
     readiness packets.
   - It should support dry-run blocked rows for unavailable asset families.
   - It consumes prepared room-category labels; it does not call live VLMs while
     scanning or during eval execution.

3. **Environment Preparation Labels**
   - Add or document an explicit scene-preparation job that can review scene
     preview images and write a cached room-category label manifest before
     sampler selection.
   - Default labeler recommendation: `provider_profile=codex-env`,
     `model=gpt-5.5`, because room category labeling benefits from stronger
     visual reasoning. Keep the labeler configurable.
   - Optional label QA may run multiple vision-capable models and keep only
     high-agreement labels; disagreements should be recorded as `unlabeled` or
     `category_uncertain`, not forced into a room category.
   - Label input should be a per-room evidence bundle, not just a whole-house
     screenshot: include the semantic-map or top-down crop for the candidate
     room, the room polygon / `room_id`, adjacent room context when useful, and
     1-3 room-facing FPV/chase preview images from reachable inspection
     waypoints.
   - The job must record provider profile, model id, prompt or labeler version,
     image artifacts and view types, confidence/evidence notes, model agreement
     when multiple models run, and `unlabeled` for uncertain rooms. It must not
     run inside normal sampler, eval, or CI gates.
   - Commit only the selected-sample room-category label manifest needed for
     reproducible UI/eval admission. Keep large raw screenshots, rejected
     candidate evidence, and exploratory labeling runs in ignored `output/`
     artifacts.

4. **Operator Console Integration**
   - Replace current hard-coded `MOLMOSPACES_CONSOLE_SCENE_INDICES` with curated
     sampler rows.
   - Keep the visible set to three passing samples per `scene_source`.
   - Do not expose a `scene_source` in the default scene set until three passing
     UI samples exist.
   - Preserve existing `molmospaces/val_N` entries as explicit current
     `procthor-10k-val` ids or aliases during the first slice.
   - Remove or bypass semantic label guesses based on room count or room-label
     heuristics for selected samples.

5. **Eval Harness Integration**
   - Feed ten stress samples per `scene_source` into
     `map_build_consumer` and related household eval suites by generating normal
     eval suite/sample JSON first.
   - Keep blocked or partial rows when a source has fewer than ten passing
     samples; do not silently treat the source as complete.
   - Aggregate by scene family and split-qualified `scene_source`, so
     regressions show whether they are source-family-specific.
   - Treat dynamic eval `sample_manifest` support as optional follow-up unless
     implementation proves static suite/sample JSON cannot cover the workflow.

6. **Cross-Source Expansion**
   - Add `ithor`, `procthor-objaverse-val`, and `holodeck-objaverse-val`
     candidates after the first `procthor-10k-val` scanner path is green.
   - Commit blocked reasons where assets or backend loaders are not available.

7. **Docs And Status**
   - Update README / human docs only after a supported sample matrix exists.
   - Clarify `procthor-10k-val` naming and current coverage limits.

## Risks And Assumptions

- Asset availability may dominate implementation time. The scanner must produce
  blocked rows rather than forcing developers to download every family.
- `ithor`, `procthor-objaverse`, and `holodeck` may expose different room
  metadata shapes. The sampler should normalize provenance, not force fake
  categories.
- Isaac Lab is not a MolmoSpaces sampler requirement. Keep Isaac-specific
  validation separate unless a future digital-twin or MolmoSpaces-on-Isaac goal
  explicitly needs it.
- The current world id shape `molmospaces/val_N` is too narrow once multiple
  scene sources are visible. The implementation may need ids such as
  `molmospaces/procthor-10k-val/4`.
- Eval runtime can grow quickly: ten samples per source should be a stress tier,
  not a default CI gate.

## Preflight Contract

Preflight status: DRAFT
Task source: plan path
Canonical source: `docs/plans/2026-06-15-molmospaces-scene-sampler-readiness.md`
Route: durable `$intuitive-flow`
Goal: Implement source-aware MolmoSpaces scene sampling so UI gets three curated
samples per supported `scene_source`, while each supported source gets up to ten
eval stress samples or blocked/partial evidence.

Scope:

- Add a canonical sampler manifest/generator for `scene_family`,
  `scene_split`, `scene_source`, index, runtime path, UI/eval lane, readiness,
  category provenance, previews, selected reason, generator version, and
  blocked reason.
- Add a readiness scanner for MuJoCo MolmoSpaces scenes.
- Add an explicit environment-preparation label manifest flow using
  `provider_profile=codex-env`, `model=gpt-5.5` by default.
- Integrate a 3-sample UI projection with world/operator-console metadata.
- Integrate a per-supported-source 10-sample eval projection through generated
  static eval suite/sample JSON.
- Preserve current `molmospaces/val_N` aliases for the first
  `procthor-10k-val` slice.
- Add tests preventing heuristic room-label or room-count category fallback
  from passing admission.

Non-goals:

- No IsaacLab requirement for the MolmoSpaces sampler.
- No live VLM calls inside sampler, eval, or CI.
- No full cleanup/open-task success requirement for sample admission.
- No dynamic `sample_manifest` eval CLI unless static JSON proves insufficient.
- No exposing under-ready scene sources in the default UI.

Context:

- Must read: this plan, `ARCHITECTURE.md`, `roboclaws/launch/worlds.py`,
  `roboclaws/operator_console/routes.py`, `roboclaws/evals/models.py`,
  `roboclaws/evals/runner.py`, `roboclaws/evals/live_runtime.py`,
  `roboclaws/agents/provider_registry.py`,
  `roboclaws/maps/actionable_snapshot.py`,
  `roboclaws/household/realworld_contract.py`, and
  `vendors/molmospaces/docs/assets.md`.
- Useful: `docs/plans/2026-06-15-cross-environment-semantic-map-parity.md`,
  `docs/human/model-route-verdicts.yaml`, and
  `docs/human/local-runtime.md`.
- Avoid unless needed: `output/`, historical ADR execution logs, and broad
  MolmoSpaces vendor internals beyond loader/resource-manager touchpoints.

Acceptance:

- Success: source-aware sampler produces UI and eval projections; UI exposes
  exactly three passing samples per supported source; each complete supported
  source has at most ten and exactly ten passing eval-stress samples, while
  incomplete sources keep normalized blocked/partial rows.
- `BLOCKED_NEEDS_DECISION`: none currently.
- `BLOCKED_NEEDS_LOCAL_VALIDATION`: required if local assets/runtime cannot
  exercise selected non-`procthor-10k-val` sources; blocked packets are
  acceptable only for unavailable sources, not for a broken
  `procthor-10k-val` baseline.
- `INTERMEDIATE_ONLY`: acceptable only if the first slice lands
  `procthor-10k-val` scanner, schema, and tests with cross-source expansion
  explicitly still blocked.
- No regressions: existing `molmospaces/val_N` launch paths remain usable as
  explicit `procthor-10k-val` aliases.

Verification:

- Deterministic:
  `./scripts/dev/run_pytest_standalone.sh tests/unit/launch tests/unit/operator_console tests/unit/evals -q`
- Integration:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_cross_environment_semantic_map_parity.py tests/contract/maps/test_actionable_semantic_map_snapshot.py -q`
- Product run:
  `just run::surface surface=household-world world=<selected-ui-world> backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline`
- Eval:
  `just agent::eval suite=map_build_consumer budget=focused`
- Local/live/manual: run the scanner against installed MolmoSpaces assets and
  verify non-blank previews plus blocked packets for unavailable sources.
- Optional: multi-model label QA for prepared room labels.

Execution:

- Main supervisor: protect public/private map boundaries, supervise the durable
  run, and decide blocked versus complete.
- Worker route: durable `$intuitive-flow`; use subworkers only for read-heavy
  scanner/eval/UI splits if the execution route chooses them.
- Worker goal: implement the sampler readiness plan without changing unrelated
  operator-console background-task work.

To execute:

```text
/goal execute docs/plans/2026-06-15-molmospaces-scene-sampler-readiness.md with intuitive-flow
```

## GSD Handoff Trigger

The 2026-06-15 planning loop completed the pre-implementation unknown-unknown
review. Before implementation, refresh that review only if local asset
availability or the target source list changes materially.

```text
missing planning or phase: manifest + gsd-ingest-docs, then
gsd-plan-phase --prd docs/plans/2026-06-15-molmospaces-scene-sampler-readiness.md
```
