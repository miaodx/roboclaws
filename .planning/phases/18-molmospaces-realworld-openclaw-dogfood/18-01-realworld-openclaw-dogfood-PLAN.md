# 18-01 Real-World OpenClaw Dogfood Plan

## Goal

Evaluate OpenClaw Gateway against the ADR-0003 `molmo_cleanup_realworld` MCP
surface without falling back to the current-contract `scene_objects` shortcut.

## Tasks

1. Add OpenClaw minimum-gate support to the real-world checker. The gate should
   require `policy=openclaw_agent`, `agent_driven=true`, MCP trace/report
   artifacts, no `scene_objects`, and at least one public MCP request.
2. Add a reproducible launch path for OpenClaw + the real-world cleanup skill.
   Prefer a `just` recipe if the existing Gateway scripts can support it
   cleanly; otherwise document the exact command in verification.
3. Run a local OpenClaw attempt against a synthetic ADR-0003 server first. If
   it reaches `done`, validate the artifact and record whether it passed the
   minimum or clean gate.
4. If synthetic OpenClaw is viable, decide whether to run a slower real
   MolmoSpaces/RBY1M visual attempt. Record the report artifact if run.
5. Update Phase 18 summary/verification docs and roadmap/state.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_realworld_cleanup_result.py tests/test_verify_just_recipes.py`
- `ruff check` and `ruff format --check` on changed Python files.
- OpenClaw local command or blocker log.
- Checker command against the OpenClaw artifact, if generated.

## Risks

- OpenClaw may drift to coding-agent habits if the wrong skill/profile loads.
  The launch path must point at `skills/molmo-realworld-cleanup`.
- Gateway may be slow or fail before `done`. The minimum gate should still
  distinguish "connected and used tools" from "full policy success".
- A failed OpenClaw run must not be masked by deterministic smoke or Claude
  direct-agent evidence.
