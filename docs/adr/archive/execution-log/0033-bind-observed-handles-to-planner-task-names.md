# 0033. Bind Observed Handles to Planner Task Names

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0032 made the planner probe emit sampled pickup/place task binding and
promote cleanup primitive binding on exact request/sample match. That closes the
probe-source gap, but it exposes a naming mismatch before ADR-0003 cleanup
subphases can use the real executor path.

The ADR-0003 cleanup loop must use public Observed Object Handles such as
`observed_001`. The upstream MolmoSpaces planner task may sample MuJoCo body
names or upstream task names instead. If the proof binding stores only the
planner name, the probe-backed cleanup primitive executor will reject the
cleanup subphase because the semantic cleanup request uses the observed handle.
If the proof binding stores only the observed handle, the probe cannot prove it
matched the sampled upstream planner task.

## Decision

Introduce an Observed Handle Planner Binding as private runtime evidence. It
keeps the cleanup-facing object and target IDs as ADR-0003 observed/public IDs,
while carrying planner-facing pickup/place names used only for exact sampled
task matching.

The binding should:

- resolve an observed handle to the internal cleanup object ID only after the
  object has been observed;
- derive planner-facing pickup/place candidate names from the backend runtime
  when available;
- let the planner probe compare sampled task names against planner-facing
  aliases while emitting cleanup primitive binding for the observed handle;
- keep the mapping out of the Cleanup Agent's public Agent View.

## Consequences

- Probe-backed executor evidence can match ADR-0003 cleanup subphase requests
  by observed handle.
- Planner sampled-task matching remains strict and auditable.
- The next real executor slice can route matching proof into the shared semantic
  cleanup loop without leaking private handle mappings to the agent.
