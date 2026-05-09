# 0047. Select Proof Requests By Task Feasibility

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0046 makes executed proof-bundle results visible at bundle level. The next
problem is operational: once a request is known to fail exact-scene RBY1M task
sampling with `HouseInvalidForTask` / robot placement infeasibility, rerunning
the same request wastes local GPU time and obscures whether any remaining
request is worth probing.

The runner needs a small selection layer before fallback generation becomes
more ambitious. It should not invent new cleanup objects yet. It should
consume prior proof-result evidence, select only requests that are not already
known task-feasibility blocked, and make an explicit fallback-required report
when every ready request has been excluded.

## Decision

Proof-bundle runner manifests will include a proof request selection section.
By default the selection includes every ready proof request. When the operator
passes a prior proof-bundle manifest with task-feasibility results and enables
task-feasibility exclusion, the runner will skip ready requests whose prior
result is `task_feasibility_status=blocked`.

The runner report and checker will render/validate selected and excluded
requests, exclusion reasons, prior blockers, and whether fallback selection is
required before another exact proof run is useful.

## Consequences

- Local proof-bundle execution can avoid known infeasible exact-scene requests.
- If all ready requests are infeasible, the artifact says fallback selection is
  required instead of silently generating zero commands.
- This does not generate alternate cleanup objects or claim planner-backed
  cleanup success. It creates the bounded selection seam that future fallback
  generation will use.
