# Require Real Visual OpenClaw Evidence For ADR-0003 Cleanup

Roboclaws will treat OpenClaw Gateway support on the ADR-0003 cleanup contract
as fully reviewable only after a real MolmoSpaces/RBY1M visual run produces the
shared cleanup report with robot-view evidence.

Phase 18 proved Gateway tool-use viability on the synthetic ADR-0003 backend.
That was a valid first gate, but it did not record RBY1M FPV, chase, map, and
verification images. The next OpenClaw cleanup slice must therefore run Gateway
against `backend=molmospaces_subprocess` with `--include-robot` and
`--record-robot-views`, then validate the artifact with both the OpenClaw
minimum gate and the robot-view report gate.

Acceptance is evidence-based:

- artifact metadata is `policy=openclaw_agent`,
  `contract=realworld_cleanup_v1`, and
  `mcp_server=molmo_cleanup_realworld`;
- the trace contains public ADR-0003 MCP tool requests and no `scene_objects`
  requests;
- the report includes Agent View, Private Evaluation, Score, Semantic
  Substeps, and Robot View Timeline;
- the Robot View Timeline references FPV, chase, map, and verification images
  generated from the RBY1M MolmoSpaces/MuJoCo scene;
- the report uses the shared cleanup report underlay from ADR-0009.

The first visual Gateway run may still be judged separately as minimum
viability or clean cleanup success, but missing robot views is no longer an
acceptable OpenClaw visual-evidence outcome.
