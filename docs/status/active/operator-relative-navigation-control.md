# Operator Relative Navigation Control

Current blocker: none; implementation and required local dogfood are complete
for `docs/plans/2026-06-16-operator-relative-navigation-control.md`.

Blocker fingerprint:

- blocker_kind: none
- root_cause_classification: not blocked
- last_decision_delta: MolmoSpaces/MuJoCo and B1 Map 12 Isaac console-control
  dogfoods both passed with operator-attributed `navigate_to_relative_pose`
  and `observe` calls.

Last proven evidence:

- `navigate_to_relative_pose` is implemented through MCP semantic tools,
  `household_world` profile metadata, `RealWorldCleanupContract`,
  `CleanupBackendSession`, MolmoSpaces/MuJoCo worker routing, and B1 Isaac
  worker routing.
- Operator Console `/api/runs/<run_id>/control` is implemented with an
  allowlist, console-side limits, MCP endpoint state, operator-control rows,
  `operator_interventions.json`, and Manual Control UI buttons.
- Focused deterministic gates passed:
  `node --check roboclaws/operator_console/static/app.js`;
  `.venv/bin/python -m py_compile roboclaws/household/realworld_contract.py scripts/molmo_cleanup/molmospaces_worker_state.py roboclaws/operator_console/control.py roboclaws/operator_console/server.py roboclaws/operator_console/state.py roboclaws/operator_console/routes.py`;
  focused `ruff check` over the touched Python implementation/test set;
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/unit/molmo_cleanup/test_molmospaces_worker_state.py tests/unit/molmo_cleanup/test_relative_navigation_worker_routing.py`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/mcp/test_semantic_profiles.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`;
  and the control-specific operator console/static tests.
- MolmoSpaces live dogfood passed:
  `output/operator-console/runs/20260616-191632-molmospaces-val_0-mujoco-open-task-codex-cli-world-public-labels`.
  `operator_control.jsonl` records operator `navigate_to_relative_pose` and
  `observe` request/response rows; `operator_interventions.json` has
  `count=2`, `assisted=true`, and `autonomous_behavior_proof=false`; nested
  `0616_1916/seed-7/trace.jsonl` contains two `navigate_to_relative_pose`
  events and two `observe` events.
- B1 Isaac live dogfood passed:
  `output/operator-console/runs/20260616-191804-b1-map12-isaaclab-open-task-codex-cli-world-public-labels`.
  `operator_control.jsonl` records operator `navigate_to_relative_pose` and
  `observe` request/response rows; `operator_interventions.json` has
  `count=2`, `assisted=true`, and `autonomous_behavior_proof=false`; nested
  `0616_1918/seed-7/trace.jsonl` contains two `navigate_to_relative_pose`
  events and two `observe` events.
- Dogfood cleanup state is clean: `output/operator-console/locks/` is empty,
  and no process is listening on `127.0.0.1:8765`.

Verification caveat:

- Full `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console`
  still fails in
  `test_operator_console_routes_endpoint_exposes_evidence_lane_matrix` on an
  existing route evidence-lane matrix expectation unrelated to relative
  navigation control. The control-specific console tests pass.

Next command/artifact: none for this task; ready for closeout.

Stop condition: met.

No-touch scope:

- Do not revert unrelated dirty work already present in the checkout.
- Do not add waypoint picker, hidden waypoint shim, generic MCP proxy,
  continuous joystick control, or physical/Agibot relative movement enablement.

Parked work:

- Physical robot relative movement gates and continuous joystick/WebSocket
  driving remain out of scope.
- Arbitrary browser-to-MCP proxying remains rejected by ADR-0144.
