# OpenClaw Demo Status

The old OpenClaw navigation/game demo has been retired with the AI2-THOR stack.
The current OpenClaw route is household cleanup through the same public launch
catalog used by Codex and Claude Code:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=openclaw-gateway evidence_lane=world-oracle-labels
```

For setup, network guard rules, and Gateway lifecycle commands, use
[`local.md`](local.md). For bootstrap internals and provider/model curation,
use [`gateway-internals.md`](gateway-internals.md).
