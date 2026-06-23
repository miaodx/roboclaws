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

## Parked Candidates

None yet.
