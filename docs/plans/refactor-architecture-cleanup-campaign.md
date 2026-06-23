# Refactor: Architecture Cleanup Campaign

**Status:** ACTIVE
**Created:** 2026-06-23
**Source:** `$intuitive-reduce-entropy` saturation scan,
`$improve-codebase-architecture` report-only review, `$intuitive-refactor`
ratchet campaign

## Scope

Run repeated, verified refactor slices that make the current architecture
smaller and truer. Prefer stale-surface deletion, duplicate-owner merge,
canonical-owner migration, compatibility shim removal, stale tests/docs
removal, and bounded module deepening.

## Campaign Gate

Campaign overlay: true

Current quality signal:

- Tracked first-party source has 229 Python files and about 91k lines.
- Several current tests still import compatibility owners that the public
  launch path no longer uses.
- High-noise local artifacts exist, but ignored runtime outputs are not in
  scope unless tracked references make them live.

Architecture pressure:

- Public launch axes are canonical in `roboclaws.launch`.
- Thin runtime/server adapters should not preserve obsolete wrappers.
- Tests should prove current owners instead of keeping stale import paths alive.

Verification inventory:

- Focused pytest through `./scripts/dev/run_pytest_standalone.sh ...`.
- Ruff through `.venv/bin/ruff check ...` when source Python changes.
- Stale-reference searches with `rg`.
- `git diff --check` for every slice.

Checkpoint cadence:

- Update `docs/status/active/architecture-cleanup-campaign.md` after each
  verified slice.
- Commit each verified slice atomically.

Active capsule:

- `docs/status/active/architecture-cleanup-campaign.md`

Continue criteria:

- The next slice deletes, merges, or canonicalizes a real concept.
- The slice is internal or has an accepted public migration.
- Focused proof can observe the changed behavior.

Stop/park criteria:

- Product/design decision required.
- Public CLI/import/schema/report migration lacks accepted scope.
- Hardware, credentials, manual proof, or unavailable external contract is
  required.
- Two consecutive post-HEAD discovery handoffs find no clear safe P1/P2 slice
  after shrink attempts.

Discovery source:

- Repo entropy saturation scan against current HEAD.
- Architecture report-only review using Roboclaws domain terms and architecture
  module/interface/seam vocabulary.

Surface metrics:

| Slice | Surfaces deleted | Duplicate owners merged | Callers migrated | Tests/docs updated | Public contracts |
| --- | ---: | ---: | ---: | ---: | --- |
| Delete `devtools.commands` launch shim | 1 | 1 | 2 | 2 | preserved |
| Remove `LaunchPlan.mode` alias | 1 | 1 | 4 | 2 | preserved |
| Remove `TaskSurfaceSpec.name` alias | 1 | 1 | 0 | 0 | preserved |
| Delete duplicate root cleanup example wrapper | 1 | 1 | 0 | 0 | preserved |
| Delete root script symlink shims | 9 | 9 | 0 | 0 | preserved |
| Delete `SIM_SERVER_URL` bootstrap fallback | 1 | 1 | 0 | 1 | preserved |

Low-value stop signal:

- Only ignored artifacts, wording polish, single-file neatness, or line motion
  remains.

Discovery cadence:

- Run a fresh reduce-entropy discovery handoff when the candidate queue is
  exhausted.

Consecutive no-clear-candidate passes: 0

## Candidate Queue

Fresh discovery required.

## Completed Slices

- 2026-06-23: Deleted the test-only `roboclaws.devtools.commands` launch
  compatibility module. Migrated dev-tool route tests to
  `roboclaws.launch.catalog.resolve_surface_launch` and `LaunchError`, so tests
  now prove the canonical public launch catalog directly.

  Proof:

  ```bash
  ./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py::test_surface_router_is_importable_source_of_truth tests/contract/dev_tools/test_code_just_recipes.py::test_retired_photo_task_facade_rejects_ai2thor_surface -q
  rg -n "roboclaws\.devtools\.commands|resolve_surface_run|CommandError|ResolvedCommand" roboclaws tests docs/human docs/agents just scripts .github pyproject.toml
  git diff --check
  ```

- 2026-06-23: Removed the `LaunchPlan.mode` compatibility accessor and
  migrated tracked callers/tests to the canonical `evidence_mode` field. Kept
  the public trace label `mode=...` unchanged as output text only.

  Proof:

  ```bash
  ./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py::test_surface_router_is_importable_source_of_truth tests/contract/dev_tools/test_task_agent_just_recipes.py::test_python_launch_plan_accepts_world_labels_sanitized_lane tests/unit/evals/test_eval_runner.py::test_live_surface_command_uses_current_public_launch_axes -q
  rg -n "plan\.mode|resolved\.mode|\.mode ==|\.mode\b" roboclaws tests
  git diff --check
  ```

- 2026-06-23: Removed the unused `TaskSurfaceSpec.name` compatibility accessor.
  No tracked current caller used the alias; launch task specs now expose only
  `surface_id`.

  Proof:

  ```bash
  ./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py::test_surface_router_is_importable_source_of_truth tests/contract/dev_tools/test_task_agent_just_recipes.py::test_surface_launch_plan_exposes_domain_metadata_before_dispatch tests/unit/launch/test_environment_setup_catalog.py -q
  rg -n "TaskSurfaceSpec|surface\.name|spec\.name|\.name ==|Compatibility accessor|compatibility accessor" roboclaws/launch tests/unit/launch tests/contract/dev_tools docs/human docs/agents just scripts .github pyproject.toml
  git diff --check
  ```

  Note: the first proof attempt used a nonexistent specific test selector in
  `tests/unit/launch/test_environment_setup_catalog.py` and failed during
  collection before executing tests; the corrected focused command above passed.

- 2026-06-23: Deleted the duplicate root
  `examples/molmospaces_realworld_cleanup.py` wrapper. The canonical manual
  wrapper remains at `examples/molmo_cleanup/molmospaces_realworld_cleanup.py`,
  and current tracked callers already use that nested path.

  Proof:

  ```bash
  ./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py::test_checker_rejects_legacy_canonical_robot_view_camera_control_flag -q
  python examples/molmo_cleanup/molmospaces_realworld_cleanup.py --help
  rg -n "examples/molmospaces_realworld_cleanup|examples/molmo_cleanup/molmospaces_realworld_cleanup|molmospaces_realworld_cleanup.py" README.md ARCHITECTURE.md STATUS.md docs/human docs/agents just scripts tests roboclaws .github pyproject.toml examples
  git diff --check
  ```

  Note: a broader proof attempt against
  `tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py` exposed
  unrelated current artifact-shape failures around missing
  `agent_view.observed_objects`. The wrapper deletion was narrowed to
  stale-reference and canonical-wrapper proof.

- 2026-06-23: Deleted nine unreferenced root `scripts/*` symlink shims:
  `check_kimi_key.py`, `control_ui_watcher.py`, `network_status.sh`,
  `openclaw-bootstrap.sh`, `openclaw-defaults.env`,
  `openclaw_plugin_allowlist.py`, `regenerate_molmo_cleanup_report.py`,
  `run_pytest_standalone.sh`, and `write_pages_index.py`. Current tracked
  docs, tests, and recipes already use canonical subdirectory paths such as
  `scripts/dev/run_pytest_standalone.sh` and
  `scripts/openclaw/openclaw-bootstrap.sh`.

  Proof:

  ```bash
  ./scripts/dev/run_pytest_standalone.sh tests/unit/providers/test_check_kimi_key.py tests/unit/openclaw/test_control_ui_watcher.py tests/unit/scripts/test_network_status_guard.py tests/contract/openclaw/test_openclaw_bootstrap.py::test_plugins_allow_seeded_from_canonical_allowlist tests/contract/openclaw/test_openclaw_bootstrap.py::test_bootstrap_reads_canonical_plugin_allowlist -q
  rg -n "scripts/(check_kimi_key\.py|control_ui_watcher\.py|network_status\.sh|openclaw-bootstrap\.sh|openclaw-defaults\.env|openclaw_plugin_allowlist\.py|regenerate_molmo_cleanup_report\.py|run_pytest_standalone\.sh|write_pages_index\.py)" README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md docs/human docs/agents just scripts tests roboclaws .github pyproject.toml
  for p in scripts/dev/check_kimi_key.py scripts/openclaw/control_ui_watcher.py scripts/dev/network_status.sh scripts/openclaw/openclaw-bootstrap.sh scripts/openclaw/openclaw-defaults.env scripts/openclaw/openclaw_plugin_allowlist.py scripts/reports/regenerate_molmo_cleanup_report.py scripts/dev/run_pytest_standalone.sh scripts/reports/write_pages_index.py; do test -e "$p"; done
  git diff --check
  ```

  Note: two earlier OpenClaw proof attempts used nonexistent specific test
  selectors; the corrected command above passed.

- 2026-06-23: Removed the stale `SIM_SERVER_URL` translate-and-warn fallback
  from `scripts/openclaw/openclaw-bootstrap.sh`. The bootstrap interface now
  names only `ROBOCLAWS_MCP_URL`, while the default
  `http://host.docker.internal:18788/mcp` and explicit override behavior are
  preserved. Added a contract guard so the old HTTP sim-server owner does not
  return as a compatibility path.

  Proof:

  ```bash
  ./scripts/dev/run_pytest_standalone.sh tests/contract/openclaw/test_openclaw_bootstrap.py::test_mcp_seeds_server_transport_and_url tests/contract/openclaw/test_openclaw_bootstrap.py::test_mcp_url_env_override_honored tests/contract/openclaw/test_openclaw_bootstrap.py::test_bootstrap_has_no_sim_server_url_compatibility_path -q
  bash -n scripts/openclaw/openclaw-bootstrap.sh
  .venv/bin/ruff check tests/contract/openclaw/test_openclaw_bootstrap.py
  rg -n -F "SIM_SERVER_URL" scripts/openclaw tests/contract/openclaw just/openclaw.just just/chat.just just/molmo.just roboclaws/cli/household_agent_server.py docs/human/openclaw README.md ARCHITECTURE.md AGENTS.md CLAUDE.md
  git diff --check
  ```

  Note: the stale-reference search now returns only the intentional regression
  guard in `tests/contract/openclaw/test_openclaw_bootstrap.py`; production
  bootstrap, recipes, current docs, and runtime adapters no longer reference
  the legacy variable.

## Parked Candidates

- Public MolmoSpaces `world=molmospaces/val_*` alias removal: current human
  docs still describe selected aliases as launchable. Removing or renaming that
  public surface needs an accepted public command migration. A safe internal
  slice may still rename implementation helpers if it preserves public world ids.
- `tests/contract/molmo_cleanup/test_molmospaces_realworld_cleanup.py`
  current artifact-shape failures: four tests still expect
  `agent_view.observed_objects`. Unblock by deciding whether those tests should
  migrate to Agent View v2 sections or whether the cleanup artifact producer
  should restore a documented compatibility field.
- Obsolete checker flag
  `--require-canonical-robot-view-camera-control`: the checker currently
  recognizes this public flag only to emit an actionable obsolete-flag error
  pointing at `--require-robot-head-camera-fpv`. Removing it would change a
  public checker error path to a generic argparse unknown-flag error. Unblock
  with an accepted public checker CLI migration decision.
