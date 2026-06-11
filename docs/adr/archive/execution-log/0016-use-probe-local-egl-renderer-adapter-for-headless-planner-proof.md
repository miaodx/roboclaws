# 0016. Use Probe-Local EGL Renderer Adapter For Headless Planner Proof

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0015 made planner probe blockers actionable. The Franka execute-mode probe
now shows two renderer-specific blockers before any planner-backed proof can be
claimed:

- Default rendering terminates with `SIGSEGV` in `glfw.create_window`.
- Setting `MUJOCO_GL=egl` and `PYOPENGL_PLATFORM=egl` avoids the segfault path
  but exposes an upstream MolmoSpaces bug: the renderer still marks the context
  as CGL and imports `/System/Library/Frameworks/OpenGL.framework/OpenGL`, which
  fails on Linux.

The strict planner-backed proof gate should not depend on an interactive display
or on patching files inside the upstream MolmoSpaces checkout.

## Decision

Add a probe-local headless renderer adapter for planner execute-mode probes:

- Keep the default config-import probe unchanged.
- Add an explicit renderer-device override for execute-mode probes.
- In the worker process only, patch the MolmoSpaces environment module's
  renderer constructor so it passes `device_id=0` to `MjOpenGLRenderer`.
- Set EGL environment variables for that worker path.
- Record the renderer override in runtime diagnostics and artifacts.
- Keep the strict `--require-planner-backed` checker unchanged: the adapter may
  make execution possible, but only real planner steps with nonzero robot-state
  movement and no blockers can pass.

## Consequences

- The workaround is localized to the Roboclaws probe harness and can be removed
  if upstream MolmoSpaces fixes renderer device selection.
- The probe remains honest: renderer setup is not planner proof, and the strict
  checker still decides proof eligibility.
- If the renderer override reaches a later planner or policy blocker, that
  blocker should be recorded as the next phase rather than hidden.
