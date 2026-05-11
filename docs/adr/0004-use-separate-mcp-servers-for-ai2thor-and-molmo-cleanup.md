# Use Separate MCP Servers For AI2-THOR And Molmo Cleanup

Roboclaws will use separate FastMCP server classes for AI2-THOR navigation and
MolmoSpaces cleanup. The existing AI2-THOR `RoboclawsMCPServer` is coupled to
`MultiAgentEngine`, navigation views, movement/goto semantics, and frozen
navigation trace metrics, while Molmo cleanup is centered on semantic cleanup
tools, MuJoCo state mutation, cleanup reports, and agent-driven object
substeps. Shared binding/readiness/trace helper patterns are allowed, but a
generic cross-backend MCP server abstraction is deferred until both tool
contracts have stabilized.
