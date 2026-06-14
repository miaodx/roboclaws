# OpenClaw Demo Status

The old OpenClaw navigation/game demo has been retired with the AI2-THOR stack.
The current OpenClaw route is a validation-required maintainer route for
household cleanup. It uses the household launch contract, but it is not part of
the normal public engine list until an off-work-network Gateway proof is green:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=openclaw-gateway evidence_lane=world-oracle-labels
```

For setup, network guard rules, and Gateway lifecycle commands, use
[`local.md`](local.md). For bootstrap internals and provider/model curation,
use [`gateway-internals.md`](gateway-internals.md).
