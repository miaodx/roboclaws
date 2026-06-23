# Architecture Cleanup Campaign

Source gate: `docs/plans/refactor-architecture-cleanup-campaign.md`

Latest user intent: autonomous architecture cleanup campaign with high
autonomy; continue through verified commit slices until a stop gate or two
post-HEAD discovery handoffs find no clear safe P1/P2 slice.

Current slice:

- Move model-matrix benchmark helpers to the agent/provider owner, then run a
  fresh discovery handoff after commit.

Last proven evidence:

- Fresh post-HEAD discovery shrank a medium-risk model-matrix benchmark helper
  owner move into an internal slice: keep public
  `just dev::model-matrix-benchmark` and `scripts/dev/benchmark_model_matrix.py`,
  but move catalog/dataclass/wire-format helper logic from sibling
  `scripts/dev/model_matrix_benchmark_{catalog,wire}.py` modules into
  `roboclaws.agents.model_matrix_benchmark`.
- Deleted the two old script helper modules and updated the MiMo migration
  guard to allow the package owner instead of the deleted catalog helper.
- Focused model-matrix benchmark tests and MiMo migration guard passed; stale
  helper path search returned no matches; ruff passed on touched files; and
  `git diff --check` passed.

Completed slice batch:

- Slice 1: canonicalized launch route tests on `roboclaws.launch.catalog` and
  removed one shallow compatibility module.
- Slice 2: removed one launch-plan compatibility alias while preserving public
  trace text.
- Slice 3: removed one unused launch task-spec compatibility alias.
- Slice 4: removed one duplicate root example wrapper while preserving the
  canonical nested manual wrapper.
- Slice 5: removed nine root script symlink shims while preserving canonical
  subdirectory scripts.
- Slice 6: removed the OpenClaw bootstrap's stale `SIM_SERVER_URL`
  compatibility fallback while preserving canonical `ROBOCLAWS_MCP_URL`
  defaulting and overrides.
- Slice 7: removed the empty `roboclaws.openclaw` source package and stopped
  the pre-commit hook from routing staged changes in that retired package.
- Slice 8: removed an unreferenced AI planning roadmap that conflicted with
  the current GitHub issue tracker guidance.
- Slice 9: moved operator-console wrapper/display-run id normalization to one
  state owner and updated history to call it.
- Slice 10: deleted private path-containment helpers in favor of the native
  `Path.is_relative_to(...)` interface.
- Slice 11: deleted four stale agent-only docs for retired AI2-THOR/OpenClaw
  game and refactor-harness surfaces while preserving current run guidance and
  historical planning evidence.
- Slice 12: deleted the unused provider timing proxy script wrapper and updated
  the implemented provider-timing plan to name only the module owner.
- Slice 13: replaced the stale OpenClaw image-upgrade checklist command with
  the current maintainer dispatcher route and added a contract guard.
- Slice 14: replaced stale OpenClaw doc paths in bootstrap comments,
  plugin-allowlist guidance, and OpenClaw bootstrap contract-test guidance.
- Slice 15: deleted the unused private `roboclaws.launch.context` module and
  added a focused guard.
- Slice 16: deleted the no-caller cleanup report regeneration script wrapper
  and added a focused guard while preserving the artifact-report owner.
- Slice 17: deleted the no-caller Kimi-only key checker wrapper and its
  wrapper-only tests while preserving the generic provider health-check owner.
- Slice 18: updated stale OpenClaw image-bump docs away from the missing TODO
  and retired game-script examples while preserving current OpenClaw maintainer
  routes.
- Slice 19: moved model-matrix benchmark catalog and wire helper logic from
  private script-directory modules to the `roboclaws.agents` owner while
  preserving the public dev benchmark command.

Next proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/providers/test_model_matrix_benchmark.py tests/contract/regression/test_mimo_v25_migration_guard.py
rg -n "model_matrix_benchmark_catalog|model_matrix_benchmark_wire|scripts/dev/model_matrix_benchmark_catalog.py|scripts/dev/model_matrix_benchmark_wire.py" README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md docs/human docs/agents docs/ai just scripts tests roboclaws .github pyproject.toml
.venv/bin/ruff check scripts/dev/benchmark_model_matrix.py roboclaws/agents/model_matrix_benchmark.py tests/contract/regression/test_mimo_v25_migration_guard.py
git diff --check
```

Stop condition:

- Stop for public contract migration, unavailable proof, external/hardware
  evidence, or two consecutive fresh post-HEAD no-clear-candidate handoffs.

No-touch scope:

- Do not remove historical plan/ADR evidence solely because it names retired
  surfaces.
- Do not change live simulator/provider behavior in this campaign without a
  focused proof gate.

Parked work:

- Public MolmoSpaces `world=molmospaces/val_*` alias removal needs an accepted
  public command migration; current docs still describe selected aliases as
  launchable.
- Broader cleanup demo contract tests currently fail on missing
  `agent_view.observed_objects`; resolve as a separate Agent View v2/test
  migration decision. This also blocks broad artifact-report re-render proof
  for historical run-result shells; wrapper deletions should use focused
  no-caller/importability proof unless that owner behavior is changed.
- Obsolete checker flag removal needs public checker CLI migration approval
  because it would change an actionable error into a generic unknown-flag error.
