# MolmoSpaces Filament Renderer Comparison

**Status:** Layer 1 implemented; orientation fix, high-resolution comparison, and
GPU verification generated
**Created:** 2026-05-27
**Source:** MolmoSpaces Filament renderer discussion. The current request is to
first produce a fast human comparison of FPV/chase rendering quality, then only
run a longer cleanup comparison after the renderer value is visible.
**Workflow:** `intuitive-flow` plan-backed implementation. No matching active
GSD phase existed, so this stayed as a standalone source plan instead of
creating competing `.planning/` artifacts.

## Problem

Roboclaws currently runs MolmoSpaces cleanup in the repo-local Python 3.12
`.venv/` with the standard `molmo-spaces[mujoco]` dependency. Upstream
MolmoSpaces also exposes a `mujoco-filament` extra that points at a
Filament-enabled MuJoCo wheel, but that wheel is Python 3.11-specific
(`cp311`).

The expected value is better visual quality for MolmoSpaces/RBY1M reports,
especially robot FPV, chase, and focused verification images. The risk is that
we spend time wiring a full cleanup A/B before proving the renderer output is
actually better and locally installable.

## Goals

- Add a dedicated Python 3.11 Filament sidecar environment, similar in spirit to
  `.venv-visual-grounding/`, without changing the core cleanup `.venv/`.
- First build a render-only A/B report for the current MolmoSpaces cleanup
  scene: standard MuJoCo versus MolmoSpaces Filament MuJoCo.
- Compare the exact same deterministic scene setup by seed, scene source/index,
  robot name, and generated mess count.
- Show side-by-side `snapshot`, `fpv`, `chase`, `verify`, and `map` images in a
  small `report.html` for human review.
- Only after that visual review, add or run a longer full-cleanup A/B report.

## Non-Goals

- Do not switch the default cleanup runtime to Filament in this phase.
- Do not make Python 3.11 a requirement for normal Roboclaws development.
- Do not run live Codex, Claude Code, OpenClaw, or VLM cleanup as part of the
  first render-only comparison.
- Do not silently fall back to standard MuJoCo if the Filament sidecar cannot be
  installed or imported.
- Do not attempt to build a custom Python 3.12 Filament MuJoCo wheel in the
  first implementation slice.

## Plan

### Layer 1: Render-Only Human Comparison

Create a Python 3.11 sidecar project:

```text
sidecars/molmospaces-filament/
.venv-molmospaces-filament/
```

The sidecar project should pin the same upstream MolmoSpaces revision currently
used by Roboclaws, but install the published `mujoco-filament` wheel explicitly.
The upstream Git extra references `${PROJECT_ROOT}/bin/wheels/...`, which is not
portable when resolved from the Roboclaws checkout. Setup command:

```bash
UV_PROJECT_ENVIRONMENT="$PWD/.venv-molmospaces-filament" \
  uv sync --project sidecars/molmospaces-filament \
  --python /home/mi/.local/share/uv/python/cpython-3.11.14-linux-x86_64-gnu/bin/python3.11 \
  --index-strategy unsafe-best-match

uv pip install --python .venv-molmospaces-filament/bin/python \
  --default-index https://pypi.org/simple \
  --index https://test.pypi.org/simple/ \
  --index-strategy unsafe-best-match \
  --reinstall-package mujoco-filament mujoco-filament==3.5.1
```

Add a comparison runner, for example:

```bash
just molmo::renderer-comparison seed=7 generated_mess_count=10
```

The runner should:

- render the standard lane with `.venv/bin/python`;
- render the Filament lane with `.venv-molmospaces-filament/bin/python`;
- initialize `MolmoSpacesSubprocessBackend` with the same `seed`,
  `scene_source=procthor-10k-val`, `scene_index=0`, `include_robot=true`,
  `robot_name=rby1m`, and `generated_mess_count`;
- capture the existing `write_snapshot` output;
- capture multiple `write_robot_views` outputs with FPV, chase, verify, and
  map images;
- use the same deterministic focus targets in both lanes, preferably the first
  generated cleanup targets and their current source receptacles;
- write `comparison_manifest.json` with Python version, MuJoCo version,
  MolmoSpaces scene XML, image paths, dimensions, and failure status per lane;
- write `report.html` with side-by-side image grids for human review.

The report should make the first visual decision easy: whether Filament improves
the images enough to justify the longer cleanup comparison.

### Layer 2: Full Cleanup Comparison

After the render-only report is reviewed, add a second command only if useful:

```bash
just molmo::cleanup-renderer-comparison seed=7 generated_mess_count=10
```

That command should run the existing direct cleanup path twice:

- standard lane: current Python 3.12 `.venv/`;
- Filament lane: Python 3.11 sidecar runtime selected through
  `ROBOCLAWS_MOLMOSPACES_PYTHON`.

It should keep the same task, seed, map bundle, profile, robot views, and cleanup
routine across lanes, then produce a comparison index linking both full
`report.html` files. This longer layer should remain separate from the fast
render-only command so visual renderer validation does not require waiting for a
cleanup run.

## Implementation Notes

- Keep existing `just molmo::cleanup`, `review-report`, and live-agent recipes
  unchanged.
- Add `.venv-*/` to `.gitignore` so sidecar environments stay local.
- If upstream `molmo-spaces[mujoco-filament]` cannot resolve from the git
  dependency because its wheel path is local to the upstream checkout, fail with
  a clear setup message and record that as a blocker. Do not hide the failure by
  using regular `mujoco`.
- The render-only comparison can reuse the current subprocess worker and backend
  API; avoid adding a second renderer abstraction unless the current worker
  cannot run under the Filament sidecar.
- Label the runtime honestly in all artifacts: `standard-mujoco` versus
  `molmospaces-mujoco-filament`.

## Test And Acceptance

- Unit-test the comparison report renderer with fake image artifacts and a fake
  manifest; it must render side-by-side sections for snapshot, FPV, chase,
  verify, and map.
- Contract-test the `just` recipe so it checks for
  `.venv-molmospaces-filament/bin/python` and prints the setup command when
  missing.
- Local acceptance for Layer 1:

```bash
just molmo::renderer-comparison seed=7 generated_mess_count=10
```

Pass criteria:

- output contains `standard/`, `filament/`, `comparison_manifest.json`, and
  `report.html`;
- both lanes report MuJoCo/Python runtime metadata;
- both lanes produce matched snapshot, FPV, chase, verify, and map images;
- the report is useful for human visual comparison without reading JSON.

Layer 2 is accepted only after the render-only report shows enough visual value
to justify running full cleanup A/B.

## Intuitive-Flow Review Reconciliation

**Review date:** 2026-05-27
**Review route:** `intuitive-flow` inline review. The vendored gstack
`autoplan` skill document was present, but no runnable autoplan executable tree
was available in this checkout. The review decisions below were reconciled into
this plan before implementation.

Accepted decisions:

- Keep the first implementation to Layer 1 only. Full cleanup A/B stays gated
  behind a human review of the render-only report.
- Reuse `MolmoSpacesSubprocessBackend`, `write_snapshot`, and
  `write_robot_views` rather than adding a second renderer abstraction.
- Keep Python 3.11 and the Filament MuJoCo wheel in
  `.venv-molmospaces-filament/`, with `.venv-*/` ignored, so the core cleanup
  `.venv/` remains Python 3.12.
- Make the `just molmo::renderer-comparison` recipe fail before rendering when
  the Filament sidecar is missing or incomplete; do not fall back to standard
  MuJoCo.
- Test the report renderer with fake image artifacts and contract-test the
  sidecar preflight path.

Deferred decisions:

- Do not add `just molmo::cleanup-renderer-comparison` until a human has
  reviewed a successful render-only report.
- Do not promote Filament as a default cleanup runtime in this phase.

## Implementation Notes 2026-05-27

Implemented artifacts:

- `sidecars/molmospaces-filament/pyproject.toml`
- `roboclaws/molmo_cleanup/renderer_comparison.py`
- `scripts/molmo_cleanup/run_molmospaces_renderer_comparison.py`
- `scripts/molmo_cleanup/molmospaces_subprocess_worker.py`
- `just molmo::renderer-comparison`
- `tests/contract/molmo_cleanup/test_renderer_comparison.py`
- `tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py`

Local verification passed:

```bash
uv sync --extra dev --extra molmospaces
.venv/bin/python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"
set -a && source .env && set +a && .venv/bin/python -c "import os; assert os.environ.get('KIMI_API_KEY') or os.environ.get('MIMO_TP_KEY') or os.environ.get('NV_API_KEY') or os.environ.get('XM_LLM_API_KEY') or os.environ.get('CODEX_API_KEY')"
./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_renderer_comparison.py -q
.venv/bin/python -m ruff check roboclaws/molmo_cleanup/renderer_comparison.py scripts/molmo_cleanup/run_molmospaces_renderer_comparison.py tests/contract/molmo_cleanup/test_renderer_comparison.py
./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_renderer_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py -q
.venv/bin/python -m ruff check roboclaws/molmo_cleanup/renderer_comparison.py scripts/molmo_cleanup/run_molmospaces_renderer_comparison.py scripts/molmo_cleanup/molmospaces_subprocess_worker.py tests/contract/molmo_cleanup/test_renderer_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py
just --summary
just -f just/molmo.just --summary
```

Sidecar sync evidence:

- The original `molmo-spaces[mujoco-filament]` Git extra failed because uv
  resolved upstream `${PROJECT_ROOT}/bin/wheels/...` relative to this checkout:
  `Distribution not found at:
  file:///home/mi/ws/gogo/roboclaws/bin/wheels/mujoco-3.7.1-cp311...whl`.
- A standalone probe proved `mujoco-filament==3.5.1` installs from TestPyPI
  with PyPI build dependencies when using `--index-strategy unsafe-best-match`,
  and imports as `mujoco` version `3.5.1`.
- The checked-in sidecar now declares `mujoco-filament==3.5.1` explicitly from
  the `testpypi` uv index instead of using the non-portable upstream extra.
- `mujoco-mjx` pulls regular `mujoco` transitively. Because both packages own
  the top-level `mujoco` module, setup must reinstall `mujoco-filament` after
  `uv sync`. The recipe checks that imported `mujoco.__version__` matches the
  installed `mujoco-filament` distribution before rendering.
- MuJoCo Filament loads built-in material assets through `filament:*` resources,
  but the Python wheel does not register that resource provider on import. The
  subprocess worker now registers a narrow `filament` URI provider when bundled
  Filament assets are present, and the comparison runner disables the persistent
  worker for each lane so Filament engine stdout diagnostics cannot corrupt
  JSON-line responses.

Local Layer 1 acceptance:

```text
just molmo::renderer-comparison seed=7 generated_mess_count=10
```

generated:

```text
output/molmo/renderer-comparison/0527_1630/comparison_manifest.json
output/molmo/renderer-comparison/0527_1630/report.html
```

Both lanes reported success and produced matched `snapshot`, `fpv`, `chase`,
`verify`, and `map` images. Runtime metadata reported the standard lane as
Python `3.12.3` with MuJoCo `3.4.0`, and the Filament lane as Python `3.11.14`
with MuJoCo `3.5.1`. The Filament lane now renders with the imported
`mujoco-filament` distribution instead of falling back to regular MuJoCo.

Human review of this first report found two issues: Filament frames appeared
vertically flipped compared with standard MuJoCo, and one focus position was
too weak for judging whether the renderer was actually clearer.

## Follow-up Fix 2026-05-27

The subprocess worker now detects the active `mujoco-filament` runtime and
normalizes rendered frames with a vertical flip at the Roboclaws worker boundary.
The fix applies consistently to `snapshot`, FPV, chase, verify, segmentation,
and color frames so the rendered image and focus boxes use the same orientation.

The comparison runner now captures four deterministic focus samples by default.
For each sample, both lanes navigate the robot to the same generated cleanup
object before rendering FPV, chase, verify, and map views. The report keeps the
snapshot comparison at the top, then groups robot views by `focus-01` through
`focus-04`.

Local follow-up verification passed:

```bash
./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_renderer_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py -q
.venv/bin/python -m ruff check roboclaws/molmo_cleanup/renderer_comparison.py scripts/molmo_cleanup/molmospaces_subprocess_worker.py tests/contract/molmo_cleanup/test_renderer_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py
.venv/bin/python -m ruff format --check roboclaws/molmo_cleanup/renderer_comparison.py scripts/molmo_cleanup/molmospaces_subprocess_worker.py tests/contract/molmo_cleanup/test_renderer_comparison.py tests/unit/molmo_cleanup/test_molmo_cleanup_subprocess_backend.py
just molmo::renderer-comparison seed=7 generated_mess_count=10
```

The updated report is:

```text
output/molmo/renderer-comparison/0527_1731/comparison_manifest.json
output/molmo/renderer-comparison/0527_1731/report.html
```

The updated manifest reports four samples in both lanes. All standard and
Filament robot-view images have matched dimensions: FPV/chase/verify are
`540 x 360`, and maps are `620 x 420`. A pixel-difference sanity check confirmed
the corrected Filament images are closer to standard MuJoCo in their saved
orientation than after applying another vertical flip.

## High-Resolution Follow-up 2026-05-27

The comparison path now accepts explicit robot-view render dimensions. The
default remains `540 x 360` so existing RAW_FPV visual-grounding corpora and
cleanup reports stay comparable, but operator runs can request higher
resolution when judging renderer quality:

```bash
just molmo::renderer-comparison 7 10 output/molmo/renderer-comparison-1280x720 procthor-10k-val 0 rby1m 8 1280 720
```

Notes for `just` usage: `molmo::renderer-comparison` is a positional recipe.
When overriding only late parameters such as render width/height, pass the
intermediate arguments too; otherwise `just` shifts the values into earlier
slots.

The high-resolution run generated:

```text
output/molmo/renderer-comparison-1280x720/0527_1833/comparison_manifest.json
output/molmo/renderer-comparison-1280x720/0527_1833/report.html
```

Both lanes succeeded across eight deterministic focus samples. Snapshot, FPV,
chase, and verify images are `1280 x 720`; map images remain `620 x 420` because
the map renderer is a separate report artifact. The scene's MuJoCo offscreen
framebuffer reported `offwidth=1280` and `offheight=720`, matching the requested
maximum for this scene. Higher resolutions may require larger MuJoCo offscreen
buffer settings before `mujoco.Renderer` will accept them.

GPU verification:

```text
standard lane: vendor=NVIDIA Corporation, renderer=NVIDIA RTX 3500 Ada Generation Laptop GPU/PCIe/SSE2
filament lane: vendor=NVIDIA Corporation, renderer=NVIDIA RTX 3500 Ada Generation Laptop GPU/PCIe/SSE2
```

The `HandleAllocator arena is full` diagnostic is emitted by Filament's OpenGL
handle allocator and says it is using a slower system heap. It does not indicate
that MuJoCo fell back to CPU rendering.

Human readout: Filament is no longer vertically flipped, but it still appears
darker, softer, and more shadow-heavy than standard MuJoCo in the 1280x720
report. Increasing resolution improves both lanes, but it does not make
Filament obviously clearer for robot FPV or focused verification. Keep standard
MuJoCo as the default cleanup renderer until a later report shows that Filament
improves task evidence, not only screenshot aesthetics.
