# Dogfood ADR-0003 MCP With Clean Agent Runs

Roboclaws will treat the ADR-0003 MCP surface as ready for model-policy work
only after it has an agent dogfood loop that is separate from the deterministic
smoke baseline.

The dogfood loop must launch an external cleanup policy against
`molmo_cleanup_realworld`, provide instructions that describe only the
ADR-0003 public contract, and validate the resulting artifact as a clean
agent-driven cleanup run. It must not reintroduce `scene_objects`, private
Generated Mess Set data, hidden target counts, acceptable destination sets,
or private scoring truth.

Clean-run validation for this phase means:

- the artifact is `contract=realworld_cleanup_v1`;
- `mcp_server=molmo_cleanup_realworld`;
- `agent_driven=true`;
- `policy_uses_private_truth=false`;
- no `scene_objects` tool appears in the trace;
- the run satisfies the ADR-0003 pass thresholds;
- the report keeps Agent View, Private Evaluation, Score, Cleanup Trace, and
  Robot View Timeline when robot-view recording is enabled.

Direct coding-agent dogfood should be proven before OpenClaw Gateway dogfood.
OpenClaw remains the right follow-up once the stricter skill, tool descriptions,
checker, and direct-agent run shape are stable.
