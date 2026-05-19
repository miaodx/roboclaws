# Phase 08 Plan 01 Summary - Real Subprocess Backend And Harness

Implemented the real MolmoSpaces/MuJoCo prompt-cleanup gate:

- Added an isolated Python 3.11 worker at `scripts/molmospaces_subprocess_worker.py`.
- Added `MolmoSpacesSubprocessBackend` as the Python 3.10 repo wrapper.
- Extended the cleanup demo with `--backend molmospaces_subprocess`.
- Extended public cleanup policy category mappings for real ProcTHOR object and
  receptacle categories.
- Added `just harness::molmo-real-cleanup` and
  `just verify::molmo-real-cleanup`.
- Added verification checks for backend identity, exact prompt, and public
  planner separation.

The final gate passed with `5/5` restored objects against upstream
`procthor-10k-val` scene index 0. Primitive provenance remains
`api_semantic` because the phase mutates MuJoCo state directly rather than
using RBY1M/Franka planner-backed pick/place.
