# MolmoSpaces Bounded Concurrent Cleanup Runs

**Status:** Proposed source plan
**Created:** 2026-06-09
**Source:** Maintainer discussion on relaxing the historical MolmoSpaces
single-instance guard for parallel local cleanup development, followed by an
inline `intuitive-planning-loop` pass on 2026-06-09.
**Workflow:** Pre-GSD plan. Ingest or pass to `gsd-plan-phase` before
implementation.

## Problem

Roboclaws currently treats live visual MolmoSpaces cleanup as a singleton. The
original decision was conservative: a visual cleanup run owns a MuJoCo-backed
scene, and multiple live agents starting scenes at the same time could overload
the workstation or make operator state confusing.

That guard is now a development bottleneck for batch development workflows.
Multiple cleanup variants, semantic map experiments, and coding-agent harness
rows cannot be tried in parallel even when their frame-rate requirements are
low. Cleanup agents fetch frames and tool state on demand; they do not need a
real-time simulator loop.

The interactive operator path has a different requirement. For UI E2E tests and
normal operator-console work, the safest and clearest default is still one
active MCP server backed by one visual MolmoSpaces instance. The operator
console should not become a multi-run scheduler in this phase.

The current code shape supports per-run isolation:

- each `MolmoSpacesSubprocessBackend` owns a run-local state file;
- the persistent worker is per backend instance;
- MCP server state and traces are per run;
- the singleton behavior is mostly enforced by launcher-level process checks,
  tmux session checks, port checks, and operator-console backend locks.

The useful next step is not shared mutable state. It is bounded multi-instance
operation with explicit resource slots, enabled first for batch harness and
comparison workflows while keeping interactive routes single-instance by
default.

## Local Measurement

A local no-VLM resource probe was run on 2026-06-09 using:

```text
backend=molmospaces_subprocess
include_robot=true
robot_name=rby1m
MUJOCO_GL=egl
ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER=1
scene_source=procthor-10k-val
scene_index=0
generated_mess_count=5
```

Observed on a 24-core, 31 GiB RAM workstation:

| Probe | Result |
| --- | --- |
| Single instance init | about 9.4s |
| First persistent-worker observe | about 4.9s |
| Single snapshot render | about 2.2s |
| Single robot-view render bundle | about 1.9s |
| Single warm visual worker memory | about 2.0 GiB RSS, 1.95 GiB PSS |
| Two concurrent visual instances | both completed successfully |
| Two-instance aggregate memory | about 4.0 GiB RSS, 3.86 GiB PSS |
| Two-instance render slowdown | small; robot-view bundle about 2.6s each |

Interpretation: two concurrent visual MolmoSpaces cleanup backends are
reasonable on this class of local machine. Memory grows close to linearly per
instance, so unlimited concurrency is not acceptable.

## Goal

Allow explicitly bounded concurrent local visual cleanup runs without sharing
mutable cleanup state.

The first supported shape should be:

```text
interactive/operator routes: default and first-phase max = 1
batch harness/comparison routes: opt-in max = 2
each live run owns exactly one backend slot
```

This should make parallel feature development and harness execution possible
while preserving the current safety model for normal demos and UI E2E tests.

## Decisions Locked

- Keep one MolmoSpaces backend worker per cleanup run.
- Keep one mutable cleanup state file per run.
- Keep one MCP server per live coding-agent or OpenClaw cleanup run.
- Replace the hard singleton guard with a small slot-based resource guard.
- Keep operator-console and UI E2E routes single-server by default.
- Allow batch harness and comparison entrypoints to opt into two visual backend
  slots.
- Let harnesses, not the operator console, own row scheduling, port allocation,
  and output-dir allocation when they opt into parallelism.
- Do not build a shared render service in the first implementation.
- Do not allow multiple clients to mutate the same cleanup episode.

## Non-Goals

- Do not share `MjData`, cleanup state, private scoring state, or MCP traces
  across clients.
- Do not introduce a global render queue in this phase.
- Do not optimize robot-view capture or timing attribution in this phase; that
  belongs to the cleanup harness speedup plan.
- Do not make hosted CI run live MolmoSpaces visual concurrency.
- Do not weaken existing work-network, provider-key, Docker, or OpenClaw
  launch guards.
- Do not apply this policy to Isaac Lab until that backend has its own resource
  measurements.
- Do not make the operator console manage, compare, or multiplex multiple live
  cleanup runs in this phase.
- Do not require UI E2E tests to start two MCP servers.

## Implementation Sketch

### 1. Add A Visual Backend Slot Guard

Add a small helper for live visual backend leases, probably under the operator
console or launch/runtime support layer, with these semantics:

- slot count defaults to `1`;
- slot count can be raised with an explicit local override such as
  `ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS=2`;
- route policy can cap an interactive route at `1` even when a batch harness
  opts into `2`;
- each lease records run id, pid, backend, port, output dir, acquired time, and
  stale status;
- stale leases are released only when the recorded pid is no longer alive;
- leases live under an ignored output path, not in project metadata.

The guard should be shared by:

- `just molmo::cleanup` live Codex route;
- live Claude Code route;
- live OpenAI Agents route;
- live OpenClaw route where applicable;
- operator-console route readiness and launch, with an interactive cap of one
  active MolmoSpaces visual route.

### 2. Stop Treating Any MCP Server As A Global Blocker

Current launch logic rejects any existing
`roboclaws.cli.agent_server household-cleanup` process. Replace that with a
slot-aware check:

- reject when all visual backend slots are held;
- reject when the requested MCP port is already bound;
- reject when the requested output directory already belongs to an active run;
- allow another live cleanup server when a free visual backend slot and a free
  port exist.

Keep simple and explicit port behavior. The first phase may require the caller
to provide a non-default port for the second run instead of auto-selecting one.

Interactive/operator routes should continue to behave as if the singleton guard
exists: when one operator-console MolmoSpaces route is active, another
operator-console MolmoSpaces route is blocked. Batch harness routes may use the
same lower-level slot guard with a higher cap.

### 3. Add Batch Harness Parallelism

Add opt-in bounded parallelism to batch harness or comparison entrypoints that
benefit from it. The first target is the eight-case Codex cleanup harness:

```bash
just agent::harness codex-cleanup-harness8 execute parallelism=2
```

Recommended first behavior:

- `parallelism` defaults to `1`;
- `parallelism=2` sets or requires `ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS=2` for
  row execution;
- the harness assigns distinct MCP ports per active row, for example
  `18788`, `18790`;
- the harness keeps the setup semantic-map-prior row serialized before
  prior-dependent cleanup rows;
- cleanup rows may run in a worker pool of size two after prerequisites are
  satisfied;
- provider-transient retry semantics remain per row;
- the manifest records row start time, end time, assigned port, slot id if
  available, and whether the row ran under harness parallelism.

This keeps the normal single-run command simple while letting harnesses tell
the model or runner to use two slots for speed when the operator requests it.

### 4. Keep Run Artifacts Separate

Every concurrent run must have independent:

- MCP port;
- output directory;
- live status file;
- trace and run result;
- MolmoSpaces backend state file;
- persistent worker process;
- coding-agent Docker workspace;
- tmux session name when applicable.

### 5. Make State Honest

Expose active slot state in status surfaces. The user should be able to see why
a run is blocked and which run owns each slot.

For operator-console readiness, keep the message simple: another MolmoSpaces
visual route is active, so the console route is blocked until that run finishes.
For harness status, show the richer batch state: active rows, assigned ports,
slot owners, and pending rows.

### 6. Document The Limit

Update local runtime or MolmoSpaces settings docs to state:

- default interactive visual cleanup remains single-instance;
- `max=2` is a measured local batch-development setting on the tested
  workstation;
- each additional instance costs roughly 2 GiB PSS in the measured RBY1M/EGL
  cleanup path;
- operators should lower the limit when running Isaac Lab, local visual
  grounding sidecars, browser consoles, or other memory-heavy tools.

## Future Option: Shared Render Service

A shared render service is a possible later optimization, but it is out of
scope for this phase.

The safe version would share rendering capacity only. It would accept immutable
render requests such as `scene_xml`, `qpos`, and `camera_request`, then return
images. It would not own cleanup episode state and would not execute
`navigate`, `pick`, `place`, or `done`.

This is useful only if bounded multi-instance operation is still too expensive
or if semantic-map workloads need many read-only render clients. It should not
be implemented before the slot-based path proves insufficient.

## Risks

- Memory pressure can still hurt the workstation if the operator raises the
  slot count while running other heavy tools.
- Multiple live agents can make operator-console UX noisy unless active run
  state clearly identifies ports, output dirs, and lock owners.
- Port collisions are easy to create if callers reuse the default MCP port.
- Some launch scripts may still have hidden singleton assumptions after the
  primary process checks are removed.
- Parallel harness rows may compete for provider capacity. Existing
  provider-transient detection and retry should stay per row, and harness
  parallelism should remain opt-in.
- Prior-dependent harness rows can produce false failures if the setup prior is
  parallelized accidentally. Keep setup rows serialized.

## Acceptance Criteria

- With no override, live visual MolmoSpaces cleanup behavior remains
  effectively single-instance.
- Operator-console MolmoSpaces cleanup and map-build routes remain
  single-server even when batch harness parallelism exists.
- UI E2E tests can continue to use the default single MCP server path.
- With an explicit batch setting such as `parallelism=2`, two local visual
  cleanup harness rows can run with different ports and output directories.
- A third concurrent visual row is not launched while both slots are active.
- Each active run has a distinct MCP URL, output dir, backend state file, live
  status file, and persistent worker pid.
- Stale slot files are released when their owner pid is gone.
- Operator-console readiness reports the simple interactive blocker when a
  MolmoSpaces visual route is already active.
- Harness reports record row-level assigned ports, timing, and parallelism.
- Existing network/provider/Docker guards still run before launching live
  coding-agent or OpenClaw workflows.

## Verification Plan

Run focused tests for the new slot guard and launch routing:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/operator_console \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Add harness-focused tests:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_codex_cleanup_harness8.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Expected coverage:

- `parallelism=2` is accepted by `just molmo::codex-harness8` and
  `just agent::harness codex-cleanup-harness8`;
- dry-run manifests show planned distinct ports for rows that may run in
  parallel;
- setup prior rows remain serialized;
- operator-console routes still advertise one MolmoSpaces lock and block a
  second interactive run.

Run formatting and lint checks for touched files:

```bash
ruff check just/agent.just just/molmo.just roboclaws/operator_console
ruff format --check roboclaws/operator_console
```

Run local no-VLM resource smoke after implementation:

```bash
ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS=2 \
ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER=1 \
ROBOCLAWS_MOLMOSPACES_MUJOCO_GL=egl \
  <resource-probe-command>
```

Run two live local cleanup launches only after sourcing `.env` and satisfying
the existing provider/network guards. For direct command smoke, use explicit
ports and output dirs:

```bash
ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS=2 \
  just task::run household-cleanup codex evidence_lane=world-oracle-labels \
  seed=7 port=18788 output_dir=output/molmo/concurrency/seed-7

ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS=2 \
  just task::run household-cleanup codex evidence_lane=world-oracle-labels \
  seed=8 port=18790 output_dir=output/molmo/concurrency/seed-8
```

Then verify both runs produce normal artifacts and a third run is rejected while
both slots are active.

Run the intended harness path:

```bash
ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS=2 \
  just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/parallel-smoke \
  row=direct-world-oracle-labels,direct-world-public-labels \
  parallelism=2
```

The harness should run at most two visual rows concurrently and record the
assigned ports and row timing in `codex_cleanup_harness8.json`.

## Preflight Contract

**Preflight status:** DRAFT

**Task source:** Maintainer request plus this plan.

**Canonical source:** `docs/plans/molmospaces-bounded-concurrent-cleanup.md`

**Route:** durable `$intuitive-flow`. This is a plan-backed, multi-surface
runtime change touching `just` routing, live-run locking, operator-console
readiness, and the Codex harness.

### Goal

Implement bounded two-slot MolmoSpaces visual concurrency for batch harness and
comparison workflows while preserving the single-server operator-console and UI
E2E path.

### Scope

- Add a reusable visual backend slot guard for live MolmoSpaces subprocess
  routes.
- Keep default live MolmoSpaces behavior single-instance when no batch
  parallelism is requested.
- Preserve operator-console MolmoSpaces routes as interactive single-server
  routes.
- Add opt-in batch parallelism for `codex-cleanup-harness8`, starting with
  `parallelism=2`.
- Ensure harness parallel rows receive distinct MCP ports and output
  directories.
- Keep semantic-map-prior setup rows serialized before prior-dependent cleanup
  rows.
- Record row-level parallelism metadata in the harness manifest.
- Update docs and tests for the new interactive-vs-batch policy.

### Non-Goals

- Do not build a shared render service.
- Do not share mutable cleanup state, `MjData`, private scoring state, MCP
  trace files, or persistent workers across runs.
- Do not make the operator console a multi-run scheduler.
- Do not require UI E2E tests to start or coordinate two MCP servers.
- Do not apply the slot policy to Isaac Lab or physical robot backends.
- Do not remove existing network, provider, Docker, OpenClaw, or work-network
  guards.

### Context Package

Must read before implementation:

- `docs/plans/molmospaces-bounded-concurrent-cleanup.md`
- `just/molmo.just`
- `just/agent.just`
- `just/harness.just`
- `scripts/molmo_cleanup/run_codex_cleanup_harness8.py`
- `roboclaws/operator_console/locks.py`
- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/routes.py`
- `scripts/molmo_cleanup/run_live_codex_cleanup.py`
- `scripts/molmo_cleanup/run_live_claude_cleanup.py`
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `tests/unit/molmo_cleanup/test_codex_cleanup_harness8.py`
- `tests/unit/operator_console/test_operator_console.py`
- `tests/unit/operator_console/test_routes.py`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`

Useful evidence:

- The 2026-06-09 local resource probe recorded in this plan.
- `docs/human/codex-cleanup-harness8.md`
- `docs/human/molmospaces-settings.md`
- `docs/human/local-runtime.md`

Do not read unless needed:

- Isaac Lab plans and retrospectives.
- Shipped MolmoSpaces retrospectives under `docs/retrospectives/`.
- Visual grounding model-comparison corpora or large local `output/` artifacts.

### Definition Of Done / Acceptance Criteria

SUCCESS only if:

- Default live visual MolmoSpaces cleanup still behaves as single-instance.
- Operator-console MolmoSpaces cleanup and map-build routes block a second
  interactive MolmoSpaces visual run.
- UI E2E can continue using the default one-MCP-server path.
- `just agent::harness codex-cleanup-harness8 execute parallelism=2 ...`
  routes through the harness with at most two concurrent visual cleanup rows.
- Harness rows running in parallel have distinct MCP ports, output dirs, live
  status files, backend state files, and persistent worker pids.
- A third concurrent visual row is not launched when two batch slots are held.
- Harness manifests record assigned port, timing, and parallelism metadata.
- Stale slot records are cleaned up only when their recorded owner pid is gone.
- Existing work-network, provider, Docker, and OpenClaw guards still run.

PARTIAL if:

- Slot guard and operator-console single-instance behavior are implemented and
  tested, but harness `parallelism=2` remains a documented follow-up.
- Harness accepts `parallelism=2` and plans ports, but local live Codex proof is
  not run in the current environment; execution must report the missing local
  proof explicitly.

BLOCKED_NEEDS_DECISION if:

- Implementation requires changing the public `just task::run` grammar beyond
  adding harness-specific `parallelism`.
- The first implementation cannot keep operator-console routes single-server.
- Provider or Docker constraints make the required local live proof impossible
  and no delegated local-validation path is accepted.
- Resource measurements contradict the two-slot assumption on the target local
  machine.

Must not regress:

- Existing single-run `just task::run household-cleanup codex ...` behavior.
- `just console::run` route readiness and launch behavior for one MolmoSpaces
  route.
- `codex-cleanup-harness8` dry-run manifest generation with no parallelism
  override.
- Provider-transient retry semantics in the harness.
- Public/private cleanup evidence separation.

### Verification

Required deterministic gates:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/operator_console \
  tests/unit/molmo_cleanup/test_codex_cleanup_harness8.py \
  tests/contract/dev_tools/test_task_agent_just_recipes.py
```

```bash
ruff check just/agent.just just/molmo.just just/harness.just \
  roboclaws/operator_console \
  scripts/molmo_cleanup/run_codex_cleanup_harness8.py \
  scripts/molmo_cleanup/run_live_codex_cleanup.py \
  scripts/molmo_cleanup/run_live_claude_cleanup.py \
  scripts/molmo_cleanup/run_live_openai_agents_cleanup.py
ruff format --check roboclaws/operator_console \
  scripts/molmo_cleanup/run_codex_cleanup_harness8.py \
  scripts/molmo_cleanup/run_live_codex_cleanup.py \
  scripts/molmo_cleanup/run_live_claude_cleanup.py \
  scripts/molmo_cleanup/run_live_openai_agents_cleanup.py
```

Required routing dry-runs:

```bash
ROBOCLAWS_JUST_TRACE=1 \
  just agent::harness codex-cleanup-harness8 dry-run parallelism=2
```

```bash
just molmo::codex-harness8 dry-run \
  output_dir=output/molmo/codex-harness8/preflight-dry-run \
  row=direct-world-oracle-labels,direct-world-public-labels \
  parallelism=2
```

Required local/live acceptance gates:

```bash
ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS=2 \
  just agent::harness codex-cleanup-harness8 execute \
  output_dir=output/molmo/codex-harness8/parallel-smoke \
  row=direct-world-oracle-labels,direct-world-public-labels \
  parallelism=2
```

This live gate requires repo-local provider credentials, Docker-backed Codex,
and local MolmoSpaces/MuJoCo runtime. If unavailable, execution must mark the
result PARTIAL and state that local live validation is delegated or pending.

Optional exploratory gate:

```bash
ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS=2 \
ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER=1 \
ROBOCLAWS_MOLMOSPACES_MUJOCO_GL=egl \
  <resource-probe-command>
```

This is useful to remeasure memory on the target machine, but it is not a
substitute for the live harness proof.

### Execution Surface

- Main session: root supervisor; owns route control, review, and final
  complete/partial/blocked judgment.
- Worker: none required by default. A worker may be used if execution is run
  through `skill-runner`, but the worker must treat this plan as the canonical
  source.
- Worker-local goal: none unless a separate worker is explicitly launched.

### Main-Session Goal Prompt

```text
/goal execute docs/plans/molmospaces-bounded-concurrent-cleanup.md with intuitive-flow
```

### To Execute

```text
/goal execute docs/plans/molmospaces-bounded-concurrent-cleanup.md with intuitive-flow
```

### Approval Gate

Reply `LGTM`, `approve`, or `go ahead` to approve this preflight contract. To
start durable execution from the main session, use the exact `To Execute`
command above.
