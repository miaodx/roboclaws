# Evaluate OpenClaw On ADR-0003 MCP After Direct Agent Dogfood

Roboclaws will evaluate OpenClaw Gateway against the ADR-0003
`molmo_cleanup_realworld` MCP surface only after direct coding-agent dogfood has
stabilized the stricter skill, launcher, checker, and artifact shape.

OpenClaw evaluation must use the same public contract as Phase 17: Metric Map,
Fixture Hints, waypoint observations, Observed Object Handles, and semantic
cleanup tools. It must not use the current-contract `scene_objects` bridge,
private manifests, hidden Generated Mess Set data, target counts, or acceptable
destination sets.

The first OpenClaw gate may be a viability gate instead of a full clean-run
gate. A useful OpenClaw result must at least prove that Gateway can load the
real-world cleanup skill, connect to `molmo_cleanup_realworld`, call public MCP
tools, avoid forbidden shortcuts, and produce trace/report artifacts. Full
ADR-0003 cleanup success remains the target outcome and should be recorded when
achieved, but the first OpenClaw phase should distinguish "tool-use viability"
from "clean policy success" so prompt/profile failures do not get hidden.
