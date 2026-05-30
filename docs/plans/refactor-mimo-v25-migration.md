---
refactor_scope: mimo-v25-migration
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-05-30
---

# Refactor Scope: MiMo v2.5 Migration

## Status

DONE

## Target

Migrate active Roboclaws MiMo model surfaces away from deprecated v2 Omni names
to the v2.5 series before the legacy model ids expire.

Vendor notice checked 2026-05-30:

- Xiaomi MiMo docs say MiMo V2 Pro / Omni auto-routes to V2.5 at
  2026-06-01 00:00 GMT+8 and is fully deprecated by 2026-06-30.
- Xiaomi MiMo pricing/model docs list `mimo-v2.5` as the full-modal model with a
  1M context window and `mimo-v2-omni` as the older 256K full-modal model.
- Official deprecation page: <https://platform.xiaomimimo.com/docs/updates/deprecate>

Canonical target models:

- Full-modal/image route: `mimo-v2.5`.
- Text-only coding route: keep `mimo-v2.5-pro` where image input is not needed.
- Mify/internal aggregation route: `xiaomi/mimo-v2.5`.
- OpenClaw OpenAI-compatible route: `mimo_openai/mimo-v2.5`.
- OpenClaw Anthropic-compatible route: `mimo_anthropic/mimo-v2.5` only when that
  path is explicitly image-capable in the local Gateway route; otherwise keep
  `mimo-v2.5-pro` as text-only.

## Accepted Severities

- P0: Active CI, hosted report, or default local route still launches a model id
  that errors after 2026-06-30.
- P1: Provider catalog, image/text delivery guards, bridge-model defaults, or
  visual-grounding contracts still route image work to deprecated Omni ids.
- P2: Current docs, just examples, labels, and tests keep naming Omni as an
  active target instead of historical evidence.

## Accepted Cleanup Checklist

- [x] Replace active direct/provider defaults from `mimo-v2-omni` to `mimo-v2.5` in:
  - `roboclaws/core/providers/openai.py`
  - `roboclaws/core/provider_catalog.py`
  - `roboclaws/core/vlm.py`
  - `scripts/dev/coding_agent_env.sh`
  - `scripts/openclaw/openclaw-bootstrap.sh`
  - `scripts/appliance/appliance_seed_openclaw.py`
  - `scripts/dev/probe_mify_v25_image.py` (renamed from the Omni probe).
- [x] Update active live-report matrix entries:
  - Replace `mimo-v2-omni` with `mimo-v2.5`.
  - Replace `mimo-v2-omni-camera-raw` with `mimo-v2.5-camera-raw`.
  - Update labels from "MiMo v2 Omni" to "MiMo v2.5".
  - Old published report artifact names are not active CI/download targets
    after this change; historical docs keep old evidence labels.
- [x] Update apple-to-apple cleanup route ids and labels:
  - `claude-mimo-omni` -> `claude-mimo-v25` or equivalent.
  - `ROBOCLAWS_CLAUDE_MODEL=mimo-v2-omni` -> `mimo-v2.5`.
- [x] Update visual-grounding adapter contracts:
  - `mimo-v2-omni` producer/direct ids -> `mimo-v2.5`.
  - `xiaomi/mimo-v2-omni` producer ids -> `xiaomi/mimo-v2.5`.
  - Pipeline ids such as `grounding-dino+mimo-v2-omni`,
    `yoloe+mimo-v2-omni`, and `mimo-v2-omni-direct` become v2.5 equivalents.
  - Old pipeline ids remain only in historical result docs.
- [x] Update MCP/text-bridge and OpenClaw tests to expect `mimo_openai/mimo-v2.5`
  for image bridge defaults.
- [x] Update active docs and examples:
  - `README.md`
  - `just/README.md`
  - `docs/human/local-runtime.md`
  - `docs/human/coding-agent-nav-server.md`
  - `docs/human/molmospaces-settings.md`
  - `docs/human/openclaw/demo.md`
  - `docs/human/railway/deploy.md`
  - `docs/human/railway/appliance-plan.md`
  - `docs/human/model-matrix.md`
  - `skills/capture-object-photo/SKILL.md`
- [x] Update tests that encode active model names:
  - `tests/unit/providers/test_provider_catalog.py`
  - `tests/unit/molmo_cleanup/test_ci_live_reports.py`
  - `tests/unit/molmo_cleanup/test_apple2apple_test_grid.py`
  - `tests/contract/mcp/test_mcp_text_bridge.py`
  - `tests/contract/mcp/test_mcp_server.py`
  - `tests/contract/openclaw/test_openclaw_interactive.py`
  - `tests/contract/openclaw/test_openclaw_nav_autonomous.py`
  - `tests/contract/appliance/test_appliance_seed_openclaw.py`
  - `tests/contract/visual_grounding/test_visual_grounding_service.py`
  - `tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
  - `tests/contract/dev_tools/test_task_agent_just_recipes.py`
  - `tests/contract/dev_tools/test_code_just_recipes.py`
  - `tests/regression/refactor/test_capture_refactor_regression.py`
- [x] Add or update a static guard test that fails if active code, recipes, or
  current docs still contain `mimo-v2-omni`, while excluding historical evidence
  directories such as `docs/retrospectives/`, archived plans/status notes, and
  generated output.

## Parked Cross-Seam / Future Ideas

- Do not rewrite historical retrospectives, old output artifact paths, or
  evidence tables that describe actual Omni benchmark runs. Add a short
  "historical model id" note only where the current reader could mistake the
  old id for a live recommendation.
- Do not migrate unrelated Kimi or Qwen provider defaults.
- Do not change MiMo pricing numbers beyond the rows needed to explain why v2.5
  is the active full-modal replacement.
- Do not run paid real-provider probes unless explicitly authorized.
- Do not change Gateway provider architecture beyond model-id defaults and
  catalog entries.
- Historical Omni benchmark/model rows remain in
  `docs/human/model-matrix.md` and
  `docs/human/molmospaces-visual-grounding-results.md`; the new static guard
  permits those two evidence files only.

## Evidence Ladder

- L0 static:
  - `rg -n "mimo-v2-omni|xiaomi/mimo-v2-omni|mimo-omni|MiMo v2 Omni" ...`
    over active files returns only allowed historical/deprecation mentions.
  - `ruff check` and `ruff format --check` over touched Python files.
  - `bash -n scripts/dev/coding_agent_env.sh scripts/openclaw/openclaw-bootstrap.sh`
  - Python code-intelligence/tooling status: `pyproject.toml` configures Ruff
    and Pytest for the target Python files; no repo-local Pyright/Mypy config or
    `.vscode`/`.claude` LSP settings were found.
- L1 unit/mock:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/providers/test_provider_catalog.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_apple2apple_test_grid.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/regression/test_mimo_v25_migration_guard.py`
- L2 contract:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/mcp/test_mcp_text_bridge.py tests/contract/mcp/test_mcp_server.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/openclaw/test_openclaw_interactive.py tests/contract/openclaw/test_openclaw_nav_autonomous.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/appliance/test_appliance_seed_openclaw.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/visual_grounding/test_visual_grounding_service.py tests/contract/visual_grounding/test_visual_grounding_benchmark.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/dev_tools/test_code_just_recipes.py`
- L5 local provider:
  - Optional only. Run a small MiMo `mimo-v2.5` image/tool-call smoke with
    `MIMO_TP_KEY` after code migration if paid-provider validation is approved.

## Stop Condition

Stop when all accepted active code, recipe, test, and current-doc references
use the v2.5 series as canonical; any remaining Omni references are explicitly
historical/deprecated and excluded by a documented static guard; L0-L2 evidence
passes; L5 provider validation is either green or explicitly skipped as
paid/local-only.

## Execution Log

- 2026-05-30: Created report-only migration scope after scanning current MiMo
  usages. No production code changed in this pass.
- 2026-05-30: Implemented active migration to MiMo v2.5.
  - Provider/catalog defaults now use `mimo-v2.5`; active `mimo-omni` /
    `mimo-v2-omni` aliases were removed from the catalog.
  - OpenClaw/appliance image defaults now use `mimo_openai/mimo-v2.5`; text-only
    routes keep `mimo-v2.5-pro`.
  - Mify coding-agent default now uses `xiaomi/mimo-v2.5`.
  - Molmo live CI entries now publish `mimo-v2.5` and
    `mimo-v2.5-camera-raw`.
  - Apple-to-apple route id is now `claude-mimo-v25`.
  - Visual-grounding hosted MiMo producer and pipeline ids now use v2.5.
  - Active docs/examples now use v2.5; historical Omni result docs were left as
    evidence and guarded as explicit exceptions.
  - Added `tests/contract/regression/test_mimo_v25_migration_guard.py`.
- 2026-05-30 evidence:
  - Active static search for deprecated Omni ids returns only
    `docs/human/model-matrix.md` and
    `docs/human/molmospaces-visual-grounding-results.md`, both allowed
    historical evidence files.
  - `python -m py_compile scripts/dev/probe_mify_v25_image.py` passed.
  - `ruff check` over touched Python files passed.
  - `ruff format --check` over touched Python files passed.
  - `bash -n scripts/dev/coding_agent_env.sh scripts/openclaw/openclaw-bootstrap.sh` passed.
  - Focused ladder passed: `./scripts/dev/run_pytest_standalone.sh -q
    tests/unit/providers/test_provider_catalog.py
    tests/unit/molmo_cleanup/test_ci_live_reports.py
    tests/unit/molmo_cleanup/test_apple2apple_test_grid.py
    tests/contract/regression/test_mimo_v25_migration_guard.py
    tests/contract/mcp/test_mcp_text_bridge.py
    tests/contract/mcp/test_mcp_server.py
    tests/contract/openclaw/test_openclaw_interactive.py
    tests/contract/openclaw/test_openclaw_nav_autonomous.py
    tests/contract/appliance/test_appliance_seed_openclaw.py
    tests/contract/visual_grounding/test_visual_grounding_service.py
    tests/contract/visual_grounding/test_visual_grounding_benchmark.py
    tests/contract/dev_tools/test_task_agent_just_recipes.py
    tests/contract/dev_tools/test_code_just_recipes.py` passed with 240 tests.
  - L5 paid/local provider smoke skipped; no explicit authorization to spend a
    real `MIMO_TP_KEY` call.
- 2026-05-30 final tightening:
  - Moved the `mimo-v2-omni` model-matrix row out of the active matrix and
    labeled it historical-only.
  - Updated visual-grounding recommendations and parked comparison work so
    future MiMo runs point at `mimo-v2.5` ids while preserving old Omni benchmark
    rows as evidence.
  - Corrected stale text-only wording in the coding-agent/photo-capture docs
    and OpenClaw interactive docstring.
- 2026-05-30 completion audit:
  - Renamed stale GitHub Actions step ids from `mimo_omni` wording to
    `mimo_v25`.
  - Strengthened the static guard to catch underscore-form Omni identifiers
    such as `mimo_omni` and `mimo_v2_omni`.
