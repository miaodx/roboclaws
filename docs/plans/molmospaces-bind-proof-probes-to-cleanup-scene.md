# MolmoSpaces Bind Proof Probes To Cleanup Scene

## Goal

Make proof-bundle execution use the same real MolmoSpaces scene and requested
planner aliases as the cleanup artifact before judging cleanup primitive
readiness.

## Scope

- Add cleanup-scene metadata to planner proof request manifests when available.
- Pass the cleanup scene into generated planner probe commands.
- Make the planner probe sample from that cleanup scene and requested
  pickup/target aliases.
- Move the local execute-rerun gate from synthetic cleanup aliases to the real
  `molmospaces_subprocess` cleanup backend with robot views.
- Preserve the synthetic dry-run harness for cheap command/report checks.

## Acceptance

- Focused tests prove proof requests, proof-bundle runner commands, probe exact
  task config, report rendering, and recipe shape.
- A real subprocess cleanup artifact produces proof-bundle commands containing
  `--cleanup-scene-xml`.
- A short local exact-scene RBY1M probe reaches the real cleanup-scene task
  sampling path. If upstream task sampling rejects the object, the blocker is
  recorded as task feasibility, not alias mismatch.

## Out Of Scope

- Making every ADR-0003 cleanup object RBY1M-planner-feasible.
- Replacing the semantic cleanup primitive executor with live planner actions.
- Running the full local execute-rerun gate to success.
