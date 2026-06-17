# Open-Ended Household Default Architecture

Current blocker: no-preset OpenAI Agents SDK product proof is blocked on the
configured `codex-env` provider route returning upstream 502 before robot
action.

Blocker fingerprint: provider_transient_failure / OpenAI Agents SDK
`codex-env` upstream 502 (`bad_response_status_code`).

Last proven evidence: deterministic tests, lint/format, validation-matrix
recommendation, direct `preset=cleanup` and `preset=map-build` product gates,
and no-preset Codex open-task product gate all passed. Codex open-task report:
`output/agent-validation-matrix/20260612T182533Z/gates/codex-open-task-world-oracle/run/0613_0235/seed-7/report.html`.

Next hypothesis: the OpenAI Agents SDK no-preset route should pass without code
changes once the `codex-env` provider route stops returning upstream 502.

Next command/artifact: re-run
`just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=openai-agents-sdk provider_profile=codex-env evidence_lane=world-oracle-labels prompt="我渴了，帮我找些解渴的东西"`
with `.env` sourced and provider route healthy; inspect
`output/agent-validation-matrix/20260612T182533Z/gates/openai-agents-sdk-open-task/run/0613_0239/seed-7/live_status.json`
for the blocked attempt.

Stop condition: the plan acceptance checklist is either verified, or required
provider/local product proof is blocked and recorded as local validation.

No-touch scope: `vendors/agibot_sdk`, OpenClaw Gateway proof, generated
`output/` artifacts unless verification commands create them.

Parked work: full cleanup-shaped runtime/server rename; full cleanup artifact
schema replacement; OpenClaw default route proof.
