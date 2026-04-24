# AI2-THOR Rendering and Online Deployment Notes

Date: 2026-04-24

This note records the local rendering benchmark that changed the deployment
assumption for Roboclaws. AI2-THOR does not strictly require a discrete GPU for
this demo: it can run under Xvfb with Mesa llvmpipe CPU software rendering.
The tradeoff is large startup and frame-rendering latency.

## Current Runtime Path

The current shipped prompt view is `map-v2+chase`.

For the main examples, the runtime still constructs `MultiAgentEngine` without a
resolution override, so it uses the engine defaults:

- AI2-THOR frame size: `640x480`
- Prompt images per turn: `fpv`, `map_v2`, `chase`
- Current Linux64/X11 prompt image shapes: three `(480, 640, 3)` RGB arrays
- CloudRendering prompt image shapes observed locally: `fpv` and `map_v2` are
  RGB, while `chase` is RGBA (`(480, 640, 4)`)

Relevant code paths:

- `roboclaws/core/engine.py`: `MultiAgentEngine(..., width=640, height=480)`
- `roboclaws/core/views.py`: `render_navigation_prompt_bundle(...)`
- `examples/openclaw_nav_autonomous.py`: autonomous OpenClaw path, single agent
- `examples/openclaw_demo.py`, `examples/territory_game.py`,
  `examples/coverage_game.py`: main game/demo paths

## Local Renderer Findings

The local workstation has `DISPLAY=:1` on X11. Direct display mode used the
Intel Mesa renderer:

```text
Renderer: Mesa Intel(R) UHD Graphics (ADL-S GT1)
Vendor: Intel
Version: 4.6 (Core Profile) Mesa 25.2.8
```

Xvfb mode used CPU software rendering:

```text
Renderer: llvmpipe (LLVM 20.1.2, 256 bits)
Vendor: Mesa
Version: 4.5 (Core Profile) Mesa 25.2.8
```

So the earlier "local CPU" interpretation was only half true:

- Direct local display was not using the NVIDIA GPU, but it was using Intel GPU
  OpenGL through Mesa.
- Xvfb was true CPU software OpenGL via llvmpipe.

On this workstation, `vulkaninfo --summary` sees an Intel integrated GPU, an
NVIDIA discrete GPU, and Mesa llvmpipe as Vulkan devices. After prewarming the
separate CloudRendering build, AI2-THOR started successfully without X11 and
Unity selected Vulkan on the NVIDIA GPU:

```text
Vulkan vendor=[NVIDIA] id=[10de]
Vulkan renderer=[NVIDIA RTX 3500 Ada Generation Laptop GPU] id=[27bb]
```

## Headless iGPU Display Hypothesis

The important boundary is not whether a physical window is visible. The
important boundary is whether Unity's OpenGL context is backed by a real GPU
driver or by Mesa software rendering.

Current categories:

- **Visible desktop `DISPLAY=:1`**: GPU-backed Xorg on Intel Mesa. This is the
  fast local path measured below.
- **Xvfb**: headless virtual X server, but no hardware scanout/GPU GL in this
  local test. It fell back to Mesa llvmpipe CPU rendering.
- **Xorg dummy driver**: a virtual display, but usually still software-rendered
  unless it is explicitly wired to a real GPU driver. Do not assume this gives
  iGPU speed.
- **GPU-backed headless Xorg**: no physical monitor and no visible app window,
  but Xorg is started against the Intel/modesetting GPU driver and exposes a
  normal `DISPLAY`. This is the candidate that can plausibly match visible
  desktop performance.

The benchmark script intentionally does not auto-start a GPU-backed Xorg. That
setup is machine-specific and can conflict with the user's active desktop Xorg
or DRM master state. Instead, start the headless Xorg outside the script, then
benchmark that `DISPLAY` as `--display-backend current`.

Once a headless GPU-backed display exists, for example `DISPLAY=:121`, run:

```bash
DISPLAY=:121 python scripts/benchmark_ai2thor_rendering.py \
  --display-backend current \
  --ai2thor-platform default \
  --resolutions 320x240,640x480 \
  --steps 20 \
  --output output/benchmarks/headless-xorg-igpu.json
```

Compare against the current visible desktop:

```bash
python scripts/benchmark_ai2thor_rendering.py \
  --display-backend current \
  --ai2thor-platform default \
  --resolutions 320x240,640x480 \
  --steps 20 \
  --output output/benchmarks/current-display-igpu.json
```

Interpretation rule: if Unity's `Player.log` / benchmark JSON reports an Intel
Mesa renderer for both displays, the throughput should be close to the visible
desktop path. If the headless display reports `llvmpipe`, it is software
rendering and should be grouped with Xvfb, not with iGPU.

## Quick Engine Probe

This probe used `MultiAgentEngine`, overhead camera, chase camera updates, and
50 rotate steps at `320x240`. It did not include the full prompt-bundle
renderer.

| Mode | Renderer | Init | 50-step loop | Throughput |
|---|---|---:|---:|---:|
| Direct display | Intel Mesa iGPU | 3.45s | 2.27s | 22.00 steps/s |
| Xvfb | Mesa llvmpipe CPU | 18.43s | 41.95s | 1.19 steps/s |
| CloudRendering | NVIDIA Vulkan | 1.28s | 0.99s | 50.28 steps/s |

Takeaway: true CPU rendering worked, but was about 18x slower than the local
iGPU display path in this small probe. Warm-cache CloudRendering was faster
than both X11 paths and did not require a display server.

## Current Prompt-Path Benchmark

This benchmark exercises the current deployed view family more directly:

- Scene: `FloorPlan201`
- Agents: `1`
- Turns: `20`
- View path: `make_navigation_view_context(...)` +
  `render_navigation_prompt_bundle(...)`
- Per turn: render `fpv`, projected `map_v2`, `chase`, then execute one rotate
  action
- VLM/OpenClaw calls were not included

| Mode | Resolution | Prompt image shapes | Init | 20-turn loop | Throughput |
|---|---:|---|---:|---:|---:|
| Direct display, Intel Mesa | `320x240` | 3 x `(240, 320, 3)` | 3.45s | 1.06s | 18.78 turns/s |
| Direct display, Intel Mesa | `640x480` | 3 x `(480, 640, 3)` | 3.48s | 1.64s | 12.22 turns/s |
| Xvfb, llvmpipe CPU | `320x240` | 3 x `(240, 320, 3)` | 18.22s | 16.53s | 1.21 turns/s |
| Xvfb, llvmpipe CPU | `640x480` | 3 x `(480, 640, 3)` | 20.49s | 24.10s | 0.83 turns/s |
| CloudRendering, NVIDIA Vulkan | `320x240` | RGB, RGB, RGBA | 2.88s | 0.53s | 37.54 turns/s |
| CloudRendering, NVIDIA Vulkan | `640x480` | RGB, RGB, RGBA | 1.31s | 0.80s | 25.12 turns/s |

At the current `640x480` runtime size, Xvfb CPU rendering was about 15x slower
than the local display path for rendering/simulation. CloudRendering was about
2x faster than the local display path after its build was cached.

The existing JPEG encoders tolerate the CloudRendering RGBA chase frame because
they construct PIL images with `mode="RGB"`, effectively dropping alpha for
transport. If that deprecated PIL mode argument is removed later, normalize
frames to RGB explicitly before JPEG/PNG encoding.

## Rendering Path Comparison

| Path | X11 required | Expected renderer | Local status | Current verdict |
|---|---:|---|---|---|
| Visible desktop `DISPLAY=:1` | Yes | Intel Mesa iGPU | Benchmarked | Fast baseline |
| Managed Xvfb | Yes | Mesa llvmpipe CPU | Benchmarked | Works, about 15x slower at `640x480` |
| GPU-backed headless Xorg | Yes | Intel Mesa iGPU | Test slot added, not auto-started | Candidate for visible-display speed |
| Xorg dummy / Xpra / Xvnc without GPU passthrough | Yes | Usually llvmpipe CPU | Not separately benchmarked | Treat as software rendering until renderer proves otherwise |
| AI2-THOR `CloudRendering` | No | NVIDIA Vulkan | Benchmarked after cache prewarm | Fastest local path, but cold download must be managed |
| Mesa EGL surfaceless / OSMesa | No for native apps | Driver-dependent | Not tested with AI2-THOR Unity path | Not a drop-in for default Linux64 build |

## Deployment Implications

Railway/Render-style CPU containers are plausible for a public demo if the goal
is low-concurrency try-it-now access and each run is driven by real VLM calls.
The VLM/OpenClaw turn latency will often dominate the AI2-THOR render latency.
For pure visual stepping, batch experiments, or multiple concurrent users, CPU
software rendering is not enough.

Recommended CPU-container shape:

- One active AI2-THOR session per container.
- Run Xvfb inside the container when no hardware-accelerated display is
  detected.
- Use Mesa llvmpipe packages for CPU OpenGL.
- Prewarm or persist `~/.ai2thor` so the Unity build is not downloaded on first
  user request.
- Keep OpenClaw Gateway and Roboclaws MCP/API private on loopback.
- Expose only a narrow demo API or web UI.

In a single-container deployment, the OpenClaw MCP URL should be loopback:

```text
ROBOCLAWS_MCP_URL=http://127.0.0.1:18788/mcp
```

That differs from local Docker development, where the Gateway container reaches
the host-side MCP server through:

```text
http://host.docker.internal:18788/mcp
```

## Single-Container Architecture

For a deployable demo appliance, a single image can run all local services under
`supervisord`:

```text
supervisord
|-- Xvfb :99
|-- OpenClaw Gateway on 127.0.0.1:18789
|-- Roboclaws MCP server on 127.0.0.1:18788
`-- Roboclaws web/API process on 0.0.0.0:$PORT
```

The public process should own session admission, queueing, and artifact serving.
Do not expose the Gateway port directly.

The existing `scripts/openclaw-bootstrap.sh` is local-dev oriented and assumes
host Docker, Docker volumes, bind mounts, and `host.docker.internal`. A
container appliance should use a different entrypoint that:

- Seeds `/home/node/.openclaw` directly.
- Copies or mounts `skills/ai2thor-navigator` into each agent workspace.
- Writes `openclaw.json` before Gateway startup.
- Sets `ROBOCLAWS_TOOL_PROFILE=minimal`.
- Sets `ROBOCLAWS_MCP_URL=http://127.0.0.1:18788/mcp`.
- Starts Gateway as a child process, not via `docker run`.

## Platform Recommendation

For easiest public access:

- Use Railway/Render/Vercel for the marketing page or lightweight frontend.
- Use a CPU Railway/Render service only if accepting one slow session at a time.
- Use RunPod, Cloud Run GPU, or another GPU container platform if concurrent
  live sessions or fast visual stepping matter.

Given the measured numbers, the first hosted experiment should be a CPU
single-container prototype, with explicit queueing and timeouts. If the UX feels
slow after real VLM latency is included, move the simulator worker to a GPU
container platform while keeping the frontend on a normal web host.

## Reproduce the Benchmark

Use the checked-in benchmark script:

```bash
python scripts/benchmark_ai2thor_rendering.py \
  --display-backend current \
  --resolutions 320x240,640x480 \
  --steps 20
```

The script does not need API keys. It writes JSON under `output/benchmarks/`
by default and prints a compact table to stdout.

`--display-backend auto` prefers a hardware-accelerated current `DISPLAY` only
when `glxinfo -B` can verify it. If no display is present, or the current
display is software-rendered, or `glxinfo` is missing, it starts Xvfb directly.
Use `--display-backend current` only when you deliberately want to benchmark an
already-known local display.

Run the same probe under managed Xvfb CPU software rendering:

```bash
python scripts/benchmark_ai2thor_rendering.py \
  --display-backend xvfb \
  --resolutions 320x240,640x480 \
  --steps 20
```

Use `--display-backend auto` for hosted containers: it uses detected hardware
when available and otherwise starts Xvfb itself.

For CI, add a throughput gate:

```bash
python scripts/benchmark_ai2thor_rendering.py \
  --display-backend auto \
  --ai2thor-platform default \
  --resolutions 320x240 \
  --steps 5 \
  --fail-under-turns-per-sec 0.2 \
  --output output/benchmarks/ci-ai2thor-rendering.json
```

After each run, inspect Unity's renderer:

```bash
grep -E 'Renderer:|Vendor:|Version:' \
  "$HOME/.config/unity3d/Allen Institute for Artificial Intelligence/AI2-THOR/Player.log"
```

## Hosted Platform Smoke Commands

Install the OS packages first in CPU containers:

```bash
apt-get update
apt-get install -y xvfb libgl1 libglib2.0-0 mesa-utils
```

Then run:

```bash
python scripts/benchmark_ai2thor_rendering.py \
  --display-backend auto \
  --ai2thor-platform default \
  --suite prompt \
  --resolutions 320x240,640x480 \
  --steps 20 \
  --output output/benchmarks/ai2thor-rendering.json
```

For GitHub Actions, keep the first gate small because the first AI2-THOR Unity
download can dominate the job:

```yaml
- name: Install AI2-THOR render deps
  run: |
    sudo apt-get update
    sudo apt-get install -y xvfb libgl1 libglib2.0-0 mesa-utils

- name: AI2-THOR rendering benchmark
  run: |
    python scripts/benchmark_ai2thor_rendering.py \
      --display-backend auto \
      --ai2thor-platform default \
      --resolutions 320x240 \
      --steps 5 \
      --fail-under-turns-per-sec 0.2 \
      --output output/benchmarks/ci-ai2thor-rendering.json
```

For Railway, GCP Cloud Run, or a plain Docker service, prefer baking the
AI2-THOR Unity cache into the image or mounting a persistent cache volume. If
the benchmark spends most of its time downloading `~/.ai2thor`, it is measuring
cold-start distribution, not render throughput.

To test AI2-THOR's no-X CloudRendering path on a platform with Vulkan support:

```bash
apt-get update
apt-get install -y libvulkan1 vulkan-tools

vulkaninfo --summary

python scripts/benchmark_ai2thor_rendering.py \
  --ai2thor-platform cloud \
  --display-backend auto \
  --resolutions 320x240 \
  --steps 5 \
  --output output/benchmarks/cloudrendering.json
```

When `--ai2thor-platform cloud` is selected, the script does not start Xvfb and
records `effective_backend: none` in the display-selection JSON.

Local CloudRendering status on 2026-04-24: the first platform probe was stopped
during cold download because AI2-THOR's built-in downloader was only moving
about `0.20 MiB/s` and cannot resume partial zips. A manual S3 range prewarm
downloaded, SHA-verified, and installed the 835,983,275-byte build in
`1247.1s` at about `0.64 MiB/s`. After that cache warm, CloudRendering started
successfully and produced the benchmark rows above.

### CloudRendering Cold-Download Optimization

AI2-THOR's built-in downloader is convenient but weak for slow links:

- It uses Python `requests.get(..., stream=True)` and reads the full zip into
  memory before unzip.
- It does not write a partial zip to disk, so interrupted downloads cannot
  resume.
- An interrupted run can leave a stale lock under `~/.ai2thor/tmp/`.
- The public S3 object supports byte ranges, so external tools can resume or
  parallelize the cold download.

The CloudRendering build observed locally:

```text
Build: thor-CloudRendering-f0825767cd50d69f666c7f282e54abfe58f1e917
Zip size: 835,983,275 bytes
Zip URL: http://s3-us-west-2.amazonaws.com/ai2-thor-public/builds/thor-CloudRendering-f0825767cd50d69f666c7f282e54abfe58f1e917.zip
SHA URL: http://s3-us-west-2.amazonaws.com/ai2-thor-public/builds/thor-CloudRendering-f0825767cd50d69f666c7f282e54abfe58f1e917.sha256
SHA256: 1fd5f998644a6dd522a4cf6604c05360a75a5c27f450a7486c20e52dc2b67bb9
```

Important detail: the checksum URL is `<build>.sha256`, not
`<build>.zip.sha256`; AI2-THOR computes it by replacing the `.zip` extension.

If the Python downloader is slow or was interrupted, prewarm the cache manually:

```bash
BUILD=thor-CloudRendering-f0825767cd50d69f666c7f282e54abfe58f1e917
BASE=http://s3-us-west-2.amazonaws.com/ai2-thor-public/builds
CACHE="$HOME/.ai2thor"
ZIP="$CACHE/downloads/$BUILD.zip"
SHA="$CACHE/downloads/$BUILD.sha256"
RELEASE="$CACHE/releases/$BUILD"
EXTRACT="$CACHE/tmp/$BUILD.extract"

mkdir -p "$CACHE/downloads" "$CACHE/releases" "$CACHE/tmp"

# Only remove this lock after confirming no AI2-THOR downloader is running.
rm -f "$CACHE/tmp/$BUILD.lock"

# Resume-capable single-connection download. Replace with aria2c if available.
curl -L -C - --retry 5 --retry-delay 5 \
  -o "$ZIP" \
  "$BASE/$BUILD.zip"

curl -fsSL -o "$SHA" "$BASE/$BUILD.sha256"
echo "$(cat "$SHA")  $ZIP" | sha256sum -c -

rm -rf "$EXTRACT"
mkdir -p "$EXTRACT"
unzip -q "$ZIP" -d "$EXTRACT"
chmod +x "$EXTRACT/$BUILD"

# Keep the final move atomic so AI2-THOR never sees a partial release dir.
test ! -e "$RELEASE"
mv "$EXTRACT" "$RELEASE"
```

If `aria2c` is available, use it instead of `curl` for multi-connection range
downloads:

```bash
aria2c -x 8 -s 8 -c -d "$CACHE/downloads" -o "$BUILD.zip" "$BASE/$BUILD.zip"
```

After this cache prewarm, `Controller(platform=CloudRendering)` should skip the
download and go straight to Unity/Vulkan startup.

## Software Rendering Alternatives

For this repo, the proven software path is **Xvfb + Mesa llvmpipe**. There are
other Linux software-rendering shapes, but they are not equally useful for
AI2-THOR:

- **Xvfb + llvmpipe**: best default for CI and CPU PaaS containers. It provides
  the X11/GLX surface Unity expects and Mesa supplies CPU OpenGL.
- **Xorg with the dummy video driver + llvmpipe**: similar software-rendering
  backend, heavier setup. Useful when an app behaves differently under Xvfb
  than a real X server, but not expected to match iGPU speed.
- **GPU-backed headless Xorg**: the right test for "headless but as fast as
  visible DISPLAY." It still exposes X/GLX to Unity, but the renderer must be
  verified as Intel Mesa or another hardware GPU renderer before treating it as
  accelerated.
- **Xpra, Xvnc, or VNC-backed X servers**: useful for remote visual debugging,
  but not faster. They still usually rely on Mesa software rendering unless
  paired with real GPU passthrough.
- **Mesa EGL surfaceless / OSMesa**: valid headless OpenGL techniques in
  native apps, but not a drop-in replacement for this AI2-THOR path because the
  current Unity player path expects an X/GLX-style environment unless using
  AI2-THOR `CloudRendering`.
- **AI2-THOR `CloudRendering`**: AI2-THOR's off-screen mode. It is a separate
  Unity build and requires Vulkan support (`libvulkan1`, working
  `vulkaninfo`). It was not validated here; use the benchmark script's
  `--ai2thor-platform cloud` mode as a future spike, not the first hosted CPU
  path.
- **SwiftShader or Vulkan software stacks**: theoretically relevant for
  Vulkan/off-screen rendering, but unproven with this repo's AI2-THOR build.

The practical recommendation remains: start with Xvfb + llvmpipe for CPU
platforms, use a hardware display only when the benchmark proves it, and move to
a GPU worker if render latency becomes user-visible after real VLM latency is
included.

## External References

- AI2-THOR iTHOR documentation
  (`https://ai2thor.allenai.org/ithor/documentation`): headless mode uses
  `ai2thor.platform.CloudRendering`; normal Linux mode requires an X server with
  GLX.
- Mesa llvmpipe documentation
  (`https://docs.mesa3d.org/drivers/llvmpipe.html`): llvmpipe is Mesa's
  LLVM-based software rasterizer, so it should be treated as CPU rendering.
- Mesa EGL documentation (`https://docs.mesa3d.org/egl.html`): Mesa supports
  EGL platforms such as X11, DRM, Wayland, and surfaceless, but that does not
  make them drop-in replacements for AI2-THOR's default Unity/X11 path.
