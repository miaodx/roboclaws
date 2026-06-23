# Architecture Cleanup Campaign

Source gate: `docs/plans/refactor-architecture-cleanup-campaign.md`

Latest user intent: autonomous architecture cleanup campaign with high
autonomy; continue through verified commit slices until a stop gate or two
post-HEAD discovery handoffs find no clear safe P1/P2 slice.

Current slice:

- Delete unused launch context holder, then run a fresh discovery handoff.

Last proven evidence:

- Deleted four duplicate private `_is_relative_to` helpers and used Python
  3.12's native `Path.is_relative_to(...)` in the current operator-console and
  Pages-prune call sites.
- Focused artifact-serving, scene-preview, and Pages-prune tests passed; ruff
  passed on touched modules; stale-helper search found no remaining
  `_is_relative_to` helpers; and `git diff --check` passed.
- Current post-HEAD discovery found four stale `docs/ai` pages describing
  retired AI2-THOR/OpenClaw game, refactor-regression, and navigator harness
  scripts whose source files no longer exist.
- Follow-up discovery found `scripts/dev/provider_timing_proxy.py`, an unused
  private wrapper around the canonical module CLI that the live runner already
  launches directly.
- Follow-up discovery found `docs/ai/openclaw/update.md` still named the
  removed `just openclaw::run photo` private command; the checklist now uses
  the current `agent::run` maintainer dispatcher and has a trace-mode contract
  guard.
- Follow-up discovery found OpenClaw scripts and contract-test guidance still
  pointing readers at removed `docs/openclw/` and root `docs/model-matrix.md`
  paths; those now point to current `docs/human/openclaw/`,
  `docs/ai/openclaw/`, and `docs/human/model-matrix.md` owners.
- Follow-up discovery found `roboclaws.launch.context.LaunchContext`, an
  unexported launch context holder with no tracked current callers after launch
  routing standardized on `LaunchPlan` and `resolve_surface_launch(...)`.

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

Next proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/launch/test_environment_setup_catalog.py::test_launch_package_does_not_keep_unused_context_holder tests/unit/launch/test_environment_setup_catalog.py::test_launch_backend_catalog_exposes_private_implementation_choices tests/contract/dev_tools/test_task_agent_just_recipes.py::test_surface_router_is_importable_source_of_truth
test ! -e roboclaws/launch/context.py && python - <<'PY'
import importlib.util
spec = importlib.util.find_spec('roboclaws.launch.context')
assert spec is None, spec
PY
rg -n "LaunchContext|roboclaws\.launch\.context|launch/context\.py|launch\.context" README.md ARCHITECTURE.md STATUS.md AGENTS.md CLAUDE.md docs/human docs/agents docs/ai just scripts tests roboclaws .github pyproject.toml
.venv/bin/ruff check tests/unit/launch/test_environment_setup_catalog.py roboclaws/launch
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
  migration decision.
- Obsolete checker flag removal needs public checker CLI migration approval
  because it would change an actionable error into a generic unknown-flag error.
