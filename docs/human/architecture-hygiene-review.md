# Architecture Hygiene Review

Roboclaws should stay a clean, inspectable robotics architecture, not a pile of
magic tweaks that only make the latest agent run look better.

Use this note as a weekly or pre-ship review checklist whenever cleanup behavior,
agent prompts, MCP tools, scoring, reports, or run wrappers change. The goal is
not to block practical fixes. The goal is to make sure each fix lands at the
right layer and strengthens the public architecture instead of bypassing it.

## Core Principle

One behavior should have one honest home:

- public task surfaces own command shape, parameters, reports, and acceptance
  gates;
- agent skills own strategy, prompt guidance, examples, scripts, and reusable
  routines;
- MCP tools own bounded public robot capabilities;
- backend adapters own environment-specific execution;
- reports and scoring own evaluation, with private truth kept out of agent
  inputs.

When a change does not clearly belong to one of these homes, treat it as
architecture debt until it is simplified, moved, or documented as temporary.

## Review Questions

Ask these questions for every behavior-changing patch:

1. Does this change preserve the public/private boundary?
2. Is it a general capability, a skill strategy, a task acceptance rule, or a
   backend workaround?
3. Would the same rule still make sense for another agent, another seed, or a
   real-robot backend?
4. Does the change improve the contract, or does it only steer one agent away
   from one recent failure mode?
5. Can the behavior be expressed as data, a public tool response, or a reusable
   skill routine instead of a prompt-only instruction?
6. Does the report make the behavior visible enough for a human to audit?
7. Is there a deletion or simplification plan if this is temporary?

If the answer is unclear, keep the change small and record the uncertainty in
the PR or status note.

## Layer Placement

Prefer these destinations:

| Need | Preferred home | Warning sign |
| --- | --- | --- |
| Hide evaluator truth from agents | Public/private contract | The agent can infer private targets from profile metadata. |
| Explain how to use existing tools | Skill doc or kickoff prompt | The same instruction is duplicated in several prompts. |
| Enforce valid tool order | MCP contract response | Prompt text is the only thing preventing invalid calls. |
| Recover from a provider/runtime glitch | Run wrapper | The workaround changes task semantics. |
| Score or explain an outcome | Scoring/report layer | Agent inputs depend on private score rows. |
| Repeated multi-tool behavior | Skill routine first | A new MCP tool hides important substeps too early. |

## Magic Tweak Smells

Treat these as review triggers:

- profile-specific prompt rules that duplicate server state or tool responses;
- continuation prompts that inspect traces and tell the agent one exact next
  move;
- seed-specific, fixture-specific, or benchmark-specific ordering rules;
- acceptance thresholds that change without a matching task contract reason;
- retries that silently alter policy rather than only recovering infrastructure;
- private evaluator fields repackaged as public hints;
- multiple places encoding the same cleanup or closeout rule;
- code whose main justification is "this improved the latest run" rather than
  "this clarifies a public contract."

These are not always wrong. They need an explicit reason and a cleanup path.

## Cleanup Profile Guidance

For household cleanup lanes, keep the distinction sharp:

- `world-labels` may expose public structured labels and public semantic
  candidate guidance, but navigation still requires source-FPV confirmation.
- `world-labels-sanitized` may expose public detections and public destination
  policy, but must not expose private acceptable destinations, oracle cleanup
  decisions, or navigation authorization before source-FPV confirmation.
- Semantic acceptance and private exact restoration are different evaluation
  views. Do not tune public policy only to chase private exact restoration
  unless that becomes the explicit product goal.

Public destination policy is acceptable when it describes general category and
fixture affordances. It becomes a magic tweak when it encodes hidden target
identity, seed-specific ordering, or one-off agent recovery behavior.

## Weekly Review Checklist

During the review, sample the current diff and the most recent cleanup run:

1. List all new or changed profile-specific branches.
2. List all new or changed prompt or continuation instructions.
3. List all new recovery paths in run wrappers.
4. Mark each item as one of:
   - `contract`: belongs in the public capability or task contract;
   - `skill`: belongs in reusable agent strategy;
   - `backend`: belongs in environment/runtime plumbing;
   - `eval`: belongs in scoring or reporting;
   - `temporary`: needs an owner and removal condition.
5. Remove or merge duplicated rules.
6. Prefer server/tool responses over prompt-only enforcement when correctness
   matters.
7. Prefer report visibility over hidden automatic correction.
8. Decide whether any temporary item should be deleted before the next
   comparison run.

The review is successful when each special case has a clear architectural home
or a clear reason to remove it.

## Decision Log Format

For small reviews, use this compact format in a PR note or active status file:

```text
Architecture hygiene review YYYY-MM-DD

Changed special cases:
- <item>: contract | skill | backend | eval | temporary

Kept:
- <item> because <architectural reason>

Removed or simplified:
- <item> because <reason>

Follow-up:
- <item> with removal/review condition
```

Do not turn this checklist into another blocking process. Use it to keep the
system understandable while the demo evolves.
