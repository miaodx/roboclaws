# Architecture Cleanup Campaign

Source gate: `docs/plans/refactor-architecture-cleanup-campaign.md`

Latest user intent: autonomous architecture cleanup campaign with high
autonomy; continue through verified commit slices until a stop gate or two
post-HEAD discovery handoffs find no clear safe P1/P2 slice.

Current slice:

- Visual-grounding runtime-parameter owner merge complete. Continue with fresh post-HEAD
  discovery after committing this slice; remaining quality-ratchet output is
  broader oversized-module baseline drift in other owners.

Last proven evidence:

- Fresh post-HEAD discovery found `scripts/reports/prune_pages_site.py`, a
  pure pass-through wrapper around the existing
  `roboclaws.devtools.pages_site` owner. The only tracked caller was the GitHub
  Pages workflow.
- Migrated `.github/workflows/ci.yml` to
  `python3 -m roboclaws.devtools.pages_site site`, deleted the wrapper, added a
  canonical module entrypoint, and added a subprocess regression test proving
  the module CLI prunes an unreferenced file.
- Focused Pages prune tests passed; `python -m roboclaws.devtools.pages_site
  --help` printed CLI help; stale wrapper path search returns only the
  intentional removal guard; ruff passed on touched files; and `git diff
  --check` passed.
- Post-`90e2c0d8` discovery checked current script wrappers, current package
  micro-modules, active docs/tests/recipes, and stale names from previous
  slices. No clear safe P1/P2 slice remained after shrink attempts.
- Post-`9c70b796` discovery repeated the high-noise summary, stale-token scan,
  tiny wrapper scan, active script path scan, and previous stale-owner checks.
  It found no new material safe slice.
- Report-only architecture review artifact:
  `/tmp/architecture-review-20260623_095651.html`.
- Fresh post-HEAD discovery after `39846ccb` found a current false-confidence
  candidate: `.venv/bin/python scripts/dev/check_python_quality_ratchet.py`
  fails on current source. The first safe vertical slice moved
  provider-registry command dispatch behind private helpers; focused provider
  catalog tests, Ruff, and `git diff --check` passed, and the quality-ratchet
  output no longer lists `roboclaws/agents/provider_registry.py`.
- The second safe vertical slice moved cleanup MCP server initialization setup
  into same-owner helpers and deleted shallow one-call/no-call helpers; focused
  MCP contract tests, Ruff, and `git diff --check` passed, and the
  quality-ratchet output no longer lists
  `RealWorldMolmoCleanupMCPServer.__init__` or
  `roboclaws/household/realworld_mcp_server.py` module-size growth.
- The third safe vertical slice simplified
  `LiveOpenAIAgentsCleanupRunner._run_sdk_agent` status writing without adding
  helper surface or growing the file; focused live-runtime tests, Ruff, and
  `git diff --check` passed, and the quality-ratchet output no longer lists
  that method.
- The fourth safe vertical slice moved repeated Agibot contract-test artifact
  reads and identity assertions into same-file helpers. Focused PLR0915 Ruff,
  focused contract tests, touched-file Ruff, and `git diff --check` passed;
  the quality-ratchet output no longer lists the two overlong Agibot contract
  tests and now reports only broader oversized-module baseline drift.
- The fifth safe vertical slice moved live-agent timing breakdown, MCP trace
  timing, control-plane metrics, timeline construction, and compact metric
  grouping from the Molmo cleanup launcher script to the agent-layer
  `roboclaws.agents.live_timing` owner. Focused timing tests, touched-file
  Ruff, and `git diff --check` passed; the quality-ratchet output no longer
  lists `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`.
- The sixth safe vertical slice moved Agibot operator localization,
  run-enablement, bounded-local-nudge, and human-takeover-stop gate logic from
  the SDK subprocess adapter into the household operator-gates owner. Focused
  SDK runner source tests, focused physical Agibot contract tests, touched-file
  Ruff, and `git diff --check` passed; the quality-ratchet output no longer
  lists `roboclaws/household/agibot_sdk_runner.py` or
  `tests/contract/molmo_cleanup/test_physical_agibot_pilot.py`.
- Fresh post-`4bb038bc` discovery found a shrinkable duplicate-owner candidate
  in visual grounding: both the sidecar adapter and benchmark runner sanitized
  runtime parameters locally while the request/response contract owner existed
  in `roboclaws.household.visual_grounding`. The safe vertical slice merged
  sanitizer ownership into that contract module and migrated both callers.
  Focused visual-grounding unit/contract tests, touched-file Ruff, and
  `git diff --check` passed; the quality-ratchet output no longer lists
  `scripts/visual_grounding/adapters.py` or
  `scripts/visual_grounding/run_visual_grounding_benchmark.py`.

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
- Slice 20: deleted the Pages prune script wrapper and migrated CI to the
  `roboclaws.devtools.pages_site` module CLI.
- Slice 21: deepened provider-registry CLI dispatch so `_main(...)` is no
  longer the command formatting owner.
- Slice 22: deepened cleanup MCP server initialization while reducing the
  module size below its previous line count.
- Slice 23: simplified OpenAI Agents runner status-loop control flow without
  changing the public live-runner script.
- Slice 24: extracted test-local Agibot artifact-read and run-identity helpers
  so two contract tests no longer exceed the PLR0915 quality-ratchet threshold.
- Slice 25: moved reusable OpenAI Agents live timing interpretation out of the
  Molmo cleanup launcher script and into the agent runtime layer.
- Slice 26: moved Agibot operator safety-gate interpretation out of the SDK
  subprocess adapter and into the household operator-gates owner.
- Slice 27: merged visual-grounding runtime-parameter sanitization into the
  visual-grounding contract owner and removed two duplicate private helpers.

Next proof:

```bash
./scripts/dev/run_pytest_standalone.sh <focused next-slice tests> -q
.venv/bin/ruff check <touched files>
.venv/bin/python scripts/dev/check_python_quality_ratchet.py
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
- `scripts/molmo_cleanup/run_molmospaces_scene_camera_comparison.py` remains
  parked: it is a pass-through module CLI wrapper, but it is still the path
  used by `just/molmo.just` and covered by a CLI contract test. Removing it
  safely would need a separate recipe/test migration around a simulator-heavy
  surface.
- No-clear pass 1 parked `scripts/maps/check_bundle.py`,
  `scripts/maps/export_agibot_map_bundle.py`, and
  `scripts/molmo_cleanup/prepare_molmospaces_room.py` because they still own
  real CLI argument/default behavior instead of pure pass-through wrapper
  behavior.
- Remaining current quality-ratchet queue: broader oversized-module baseline
  drift across Agibot, Molmo, visual-grounding, and test files. Treat as
  architecture pressure and try safe owner-local shrink slices before
  considering a baseline refresh.
