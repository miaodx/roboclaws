# Operator Handoff Resume Contract

Source plan: `docs/plans/2026-06-23-operator-handoff-resume-contract.md`

Latest user intent: continue implementing/testing via `$intuitive-flow`, using
the default repo `.env` provider route from `/home/mi/ws/gogo/roboclaws/.env`.

Current slice: complete. Deterministic implementation and local/live
MolmoSpaces operator-console handoff/resume proof passed for Codex CLI and
OpenAI Agents SDK.

Last proven evidence:

- `node --check roboclaws/operator_console/static/app.js`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `ruff check roboclaws/operator_console scripts/molmo_cleanup tests/unit/operator_console tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_operator_console.py::test_operator_console_resume_endpoint_records_paused_handoff_request`

Live proof:

- Codex CLI:
  `output/operator-console/runs/20260623-154952-molmospaces-procthor-objaverse-val-0-mujoco-open-task-codex-cli-world-public-labels/0623_1549/seed-7`
  reached `live_status.phase=finished`, `exit_status=0`, consumed
  `operator_resume_requests.jsonl`, wrote
  `operator_handoff_resume_attempts.json`, wrote
  `codex-events.resume-1.jsonl`, and reached `done`; `checker.log` reports
  `molmo-realworld-cleanup ok`.
- OpenAI Agents SDK:
  `output/operator-console/runs/20260623-161108-molmospaces-procthor-objaverse-val-0-mujoco-open-task-openai-agents-sdk-world-public-labels/0623_1611/seed-7`
  reached `live_status.phase=finished`, `exit_status=0`, consumed
  `operator_resume_requests.jsonl`, wrote
  `operator_handoff_resume_attempts.json`, and reached `done`; `checker.log`
  reports `molmo-realworld-cleanup ok`.

Completed summary:

- Added `operator_handoff_paused`, UI resume-control booleans, and raw live
  `resume_available` visibility.
- Paused handoff no longer exposes delayed `Steer`; active autonomous steering
  still uses `operator_messages.jsonl` and MCP `check_operator_messages`.
- Added route metadata for `supports_paused_handoff_resume`; Codex CLI and
  OpenAI Agents SDK routes advertise it, Claude Code routes do not.
- Added `Resume With Prompt` API/UI and public-only
  `operator_resume_requests.jsonl` evidence.
- Codex CLI and OpenAI Agents SDK runners poll the resume request artifact
  during operator handoff, run a distinct same-run resume turn, and write
  `operator_handoff_resume_attempts.json`.
- Claude Code is classified as not advertising paused-handoff resume.
- Live dogfood exposed a missing console server `/api/runs/<run_id>/resume`
  action parser entry. Fixed it and added
  `test_operator_console_resume_endpoint_records_paused_handoff_request`.

Next proof:

- None required for the source plan. Optional follow-up only: decide whether
  OpenAI Agents SDK should write a route-specific `openai-agents-events.resume-*`
  artifact name; current live proof records the resume attempt and trace, but
  the SDK route's event artifacts remain continuation-named.

Blocker fingerprint:

- blocker_kind: none
- root_cause_classification: source plan complete
- last_decision_delta: live proof passed after using default repo `.env`; first
  SDK dogfood also proved resume behavior but hit an unrelated checker gate
  after using `navigate_to_relative_pose`, so the accepted SDK proof is the
  later `navigate_to_waypoint` run.

Stop condition:

- Stop. Full plan is complete after Codex CLI and OpenAI Agents SDK local/live
  handoff/resume proofs passed.

No-touch scope:

- Do not reinterpret paused queued `Steer` as resume input.
- Do not add Claude resume support unless a runner-owned path is proven.
- Do not substitute linked child runs for same-run resume without human approval.
