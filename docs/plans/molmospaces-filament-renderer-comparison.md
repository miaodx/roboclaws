# MolmoSpaces Filament Renderer Comparison

**Status:** Retired experiment  
**Created:** 2026-05-27  
**Retired:** 2026-06-13

Roboclaws briefly evaluated a Python 3.11 MolmoSpaces sidecar using the
`mujoco-filament` renderer. The goal was to see whether Filament produced
clearer RBY1M FPV, chase, verification, and snapshot images than the standard
MuJoCo renderer used by the household cleanup path.

The experiment produced render-only comparison reports at normal cleanup
resolution and at 1280x720. After orientation fixes and high-resolution reruns,
Filament still appeared darker, softer, and more shadow-heavy than standard
MuJoCo for the task evidence Roboclaws needs. It did not justify becoming the
default renderer or remaining as an actively supported alternate runtime.

To keep the repository easier to maintain, the active Filament code path was
removed: the sidecar project, comparison runner, `just` recipe, dedicated tests,
and worker-level Filament resource/flip handling are no longer part of the
current codebase. Standard MolmoSpaces/MuJoCo remains the supported household
visual runtime, while broader visual parity work continues through the
MuJoCo/Isaac/Genesis scene-camera comparison paths.
