# 0135. Use Sanitized Report Performance Artifacts For Speed Claims

Date: 2026-06-11

## Status

Accepted

## Context

Roboclaws live-agent reports now compare Agent SDK, Codex CLI, and Claude Code
routes under unstable provider and network conditions. Wall-clock time alone is
not a reliable speed signal: a run can be faster because it did less work,
because quality regressed, because provider latency happened to be lower, or
because backend/report-side work changed.

Existing artifacts already contain partial timing and usage evidence, but the
shape is uneven across engines. OpenAI Agents SDK spans expose rich sanitized
model telemetry, Codex events expose some usage and duration fields, and Claude
Code events currently need timing parity. Without one contract, future agents
will keep rediscovering metric rules and may treat single-run wall time as a
speedup claim.

## Decision

Roboclaws will use sanitized report-performance artifacts as the maintainer
contract for live-agent speed analysis.

`roboclaws_report_performance_metrics_v1` is a durable run-artifact contract,
not a public command surface, MCP tool contract, or external API. Breaking
schema changes should use a new version instead of silently changing `v1`.

`model_call_metrics.jsonl` is the sanitized per-call model-work artifact for
the first version. A shared extractor owns its schema and privacy filtering.
Live runners may call the extractor at run end, but SDK, Codex, and Claude
routes must not each grow independent metric contracts.

Version 1 is scoped to the current comparison problem:

- OpenAI Agents SDK;
- Codex CLI;
- Claude Code.

Other agent engines may be reported as out of scope or with explicit
`unavailable` limitations until they have compatible sanitized telemetry.
Missing usage or duration is unavailable, never zero.

Speed analysis must lead with task quality, call counts, model work, normalized
estimated model time when calibrated, and residual latency before observed wall
time. A single live run is diagnostic only. Calling a result a speedup requires
an explicit baseline or manifest, same-or-better quality, and repeat rows or an
explicit decision-packet waiver.

Calibration coefficients are not committed as authoritative repo defaults until
they come from a named calibration dataset with sample counts and error
statistics. Without that evidence, normalized model-time estimates must report
their calibration as unavailable rather than implying precision.

Artifacts and gates must keep the existing privacy boundary: no raw prompts,
model text, function inputs or outputs, full tool payload bodies, credentials,
private evaluator truth, or compact continuation packets.

## Considered Options

- Use wall-clock report time only. This is simple but creates false confidence
  when provider/network variance or behavior regressions dominate the result.
- Let each live runner write its own summary shape. This is quick for one
  route, but it keeps cross-engine comparisons asymmetric and duplicates
  privacy decisions.
- Make the performance metrics a public API. This overstates the current need;
  the contract is for maintainer analysis and report review, not external
  clients.
- Use a shared sanitized artifact contract. This keeps the comparison stable
  enough for maintainers while preserving room for versioned changes.

## Consequences

- Report-performance implementation should centralize extraction and privacy
  checks before runner-specific presentation.
- Old performance-summary output formats, hard-coded baselines, and duplicated
  SDK-only helpers may be replaced instead of preserved.
- Comparison tools should reject faster-but-worse outcomes unless the decision
  packet records the waiver.
- Live provider-backed rows still require explicit approval, credentials and
  backend availability, network preflight, and budget acknowledgement.
- The execution plan remains in
  `docs/plans/2026-06-11-report-performance-analysis-skill.md`.
