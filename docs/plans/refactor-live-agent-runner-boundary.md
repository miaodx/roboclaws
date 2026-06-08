---
refactor_scope: live-agent-runner-boundary
status: LOCKED
accepted_severities:
  - P0
  - P1
  - P2
last_verified: null
---

# Refactor Scope: Live Agent Runner Boundary

## Status

LOCKED

## Target

Keep live Codex and Claude cleanup runners as launch, artifact, status, lock,
process, and checker wrappers. They must not become cleanup supervisors or
monitors that decide task strategy outside the coding agent.

## Accepted Severities

- P1: the live runner currently uses implicit continuation as orchestration,
  which can hide that the coding agent stopped without an explicit handoff.
- P1: `world-public-labels` has a hidden lane-specific continuation budget.
- P2: provider, idle, and tool-binding failures are reported through behavior
  paths that make launcher errors and task continuation easy to confuse.

## Locked Decisions

- Live-agent runners launch one coding-agent turn and collect artifacts/status;
  they do not automatically continue cleanup work.
- Codex and Claude Code live household cleanup surfaces are both in scope.
- `done` remains the authoritative cleanup-completion gate. Runners must not
  infer cleanup completion from logs, score, step count, or lane.
- `world-public-labels` must not receive a runner-side continuation budget.
  Its reduced public hints are a skill/MCP-contract problem, not a launcher
  policy problem.
- Tool-binding, MCP namespace, idle-timeout, and other non-provider launch
  failures fail explicitly. They are not automatic-recovery triggers.
- Provider transient failures are retryable infrastructure failures, not cleanup
  continuations. Live runners should report stable status fields such as
  `reason=provider_transient_failure`,
  `provider_reason=rate_limit|upstream_unavailable|upstream_timeout`,
  `retryable=true`, and `resume_available=<bool>`.
- Provider transient retry is intentionally narrow: rate limits, explicit
  upstream unavailable responses such as 502/503/504, provider/proxy request
  timeouts, connection resets, or upstream unavailable errors that can be
  clearly attributed to the LLM provider/proxy.
- Auth/key failures, model/config failures, context-too-long failures,
  tool-binding failures, MCP server failures, port/lock conflicts, idle
  timeouts, and unclassified coding-agent CLI failures are not provider
  transient failures.
- A batch harness may perform a bounded provider-transient retry/resume when it
  sees that explicit retryable status. The harness must not inspect cleanup
  progress, adjust task budget by lane, call `done`, or reinterpret idle/tool
  errors as retryable.
- Remove continuation-oriented live-runner knobs rather than preserving legacy
  compatibility. If a provider retry knob is needed, give it a provider-specific
  harness name such as `--provider-retry-attempts`.

## Accepted Cleanup Checklist

- [ ] Remove lane-specific magic continuation budget from the live runner.
- [ ] Remove implicit live-runner continuation for both Codex and Claude Code
      unless an explicit agent-owned handoff protocol is added in a later
      slice.
- [ ] Treat provider transient failures as explicit retryable infrastructure
      failures, not normal cleanup continuation.
- [ ] Treat idle timeouts as explicit non-retryable live-run failures.
- [ ] Treat tool-binding and MCP namespace failures as explicit non-retryable
      live-run failures.
- [ ] Keep runner artifacts and status files stable for operator console,
      status summaries, and harness tooling.
- [ ] Keep any provider retry envelope in the batch harness thin and bounded;
      it may resume/retry only from explicit retryable provider-transient
      status.
- [ ] Update tests and docs to encode the launcher boundary.

## Parked Cross-Seam / Future Ideas

- Add an agent-owned MCP checkpoint/handoff tool after the launcher boundary is
  clean.
- Consider operator-console rerun UX for provider-rate-limit failures.

## Evidence Ladder

- L1: focused unit tests for runner continuation/failure policy.
- L2: dev-tool and harness contract tests that artifact/status surfaces remain
  readable.
- L5/L6 live provider runs are not required for this boundary refactor.

## Stop Condition

The live Codex and Claude runners no longer silently start another coding-agent
turn for ordinary unfinished cleanup, lane-specific budgets, idle timeouts, or
tool-binding errors. Provider transient failures are reported as explicit
retryable infrastructure failures, and any retry/resume is a bounded harness
behavior driven only by that status. Existing artifact/status consumers still
have stable files to inspect.

## Preflight Contract

Preflight status: DRAFT

Task source: this plan plus the 2026-06-08 discussion.

Canonical source: `docs/plans/refactor-live-agent-runner-boundary.md`.

Route: `$intuitive-refactor`.

Goal: refactor live Codex and Claude household cleanup runners so they act as
launcher/artifact wrappers, while provider-transient failures get a narrow
bounded harness retry path instead of cleanup continuation.

Scope:

- Remove live-runner continuation policy from Codex and Claude cleanup routes.
- Remove lane-specific `world-public-labels` continuation budget.
- Remove continuation-oriented knobs such as `--codex-max-continuations` and
  `ROBOCLAWS_CODEX_MAX_CONTINUATIONS` where they affect live runner behavior.
- Add stable status classification for provider-transient failures:
  `reason=provider_transient_failure`,
  `provider_reason=rate_limit|upstream_unavailable|upstream_timeout`,
  `retryable=true`, and `resume_available=<bool>`.
- Keep provider-transient retry narrow: 429/rate limit, 502/503/504 upstream
  unavailable, provider/proxy timeout, connection reset, or clearly
  provider/proxy-attributed upstream unavailable.
- Keep bounded provider retry/resume in the batch harness only, driven by
  explicit retryable status.
- Update tests and docs for Codex and Claude runner boundary plus harness retry
  semantics.

Non-goals:

- No agent-owned checkpoint/handoff MCP tool in this slice.
- No cleanup strategy changes inside the skill.
- No new `done` readiness tool; `done` remains the authoritative completion
  gate.
- No backward compatibility for removed continuation knobs.
- No live provider validation required.

Context package:

- Must read:
  - `docs/plans/refactor-live-agent-runner-boundary.md`
  - `scripts/molmo_cleanup/run_live_codex_cleanup.py`
  - `scripts/molmo_cleanup/run_live_claude_cleanup.py`
  - `scripts/molmo_cleanup/run_codex_cleanup_harness8.py`
  - `just/molmo.just`
  - `tests/unit/molmo_cleanup/test_ci_live_reports.py`
  - `tests/unit/molmo_cleanup/test_codex_cleanup_harness8.py`
- Useful evidence:
  - `just/README.md`
  - `skills/molmo-realworld-cleanup/SKILL.md`
  - `docs/human/mcp-skills-and-semantic-profiles.md`
- Do not read unless needed:
  - historical retrospectives, large generated reports, live run outputs.

Definition of done / acceptance criteria:

- SUCCESS only if Codex and Claude live runners do not automatically start
  another agent turn for unfinished cleanup, idle timeout, tool-binding/MCP
  namespace errors, or lane-specific budgets.
- SUCCESS only if provider-transient failures are explicitly classified and
  retryable without being treated as cleanup progress control.
- SUCCESS only if harness retry is bounded and activates only from explicit
  provider-transient status.
- SUCCESS only if existing artifact/status consumers remain readable.
- SUCCESS only if focused tests pass.
- PARTIAL if Codex boundary is fixed but Claude remains old behavior, or
  provider status exists but harness retry is not updated.
- BLOCKED_NEEDS_DECISION if implementation cannot reliably distinguish
  provider-transient from auth/config/context/tool failures without adding
  broad log guessing.
- Must not regress public `just task::run household-cleanup codex|claude ...`
  route shape except removed continuation knobs.
- Must not regress operator console artifact/status visibility.
- Must not regress `done` as the cleanup completion gate.

Verification:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_codex_cleanup_harness8.py`
- `ruff check` on touched Python files if implementation edits Python.
- No live Codex/Claude provider run required.

Execution surface:

- Main session: root supervisor, keeps plan/contract aligned.
- Worker: none by default.
- Worker-local goal: none.

Main-session `/goal` prompt:

```text
/goal execute docs/plans/refactor-live-agent-runner-boundary.md with intuitive-flow
```

To execute:

```text
/goal execute docs/plans/refactor-live-agent-runner-boundary.md with intuitive-flow
```

## Execution Log

- 2026-06-08: Scope accepted in discussion. User explicitly requested no
  backward-compatibility behavior.
- 2026-06-08: Grill batch locked Codex and Claude Code in scope, kept `done` as
  the only cleanup-completion gate, and separated provider-rate-limit retry from
  cleanup continuation.
- 2026-06-08: Provider retry scope widened from rate-limit-only to narrow
  provider-transient failures while excluding auth, config, context, MCP, idle,
  and unclassified CLI failures.
