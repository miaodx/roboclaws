# Map-Build Agent SDK DINO Default

Source intent: user approved making map-build closer to real robot operation via
`$intuitive-flow`, with Agent SDK preferred over coding-agent defaults and
`camera-grounded-labels` plus `grounding-dino` as the default map-build evidence
route.

Current slice: completed scoped route/test/doc changes. Household map-build now supports
`openai-agents-sdk`, product map-build docs default to DINO camera-grounded
labels, and `direct-runner` is documented as deterministic contract/eval
baseline rather than a live robot agent runtime.

Last proven evidence: orientation docs read; patched launch/eval/docs/tests.
Launch catalog already defaults map-build to `camera-grounded-labels` with
`camera_labeler=grounding-dino` when no lane is specified; eval live commands now
carry that camera labeler for camera-grounded samples. Focused tests and a clean
staged-patch verification passed.

Next proof: live/product proof with real provider, DINO sidecar, and simulator
runtime when requested.

Stop condition: if proof requires live DINO service, real provider keys, or
real robot/simulator runtime, record it as skipped local/live validation instead
of substituting a weaker claim.

No-touch scope: do not change cleanup behavior, provider registry semantics
outside map-build defaults, or real robot hardware recipes beyond route/docs
needed for map-build.
