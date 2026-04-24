#!/usr/bin/env python3
"""Benchmark AI2-THOR rendering for local, CI, and hosted-container runs.

The benchmark does not call OpenClaw or any VLM provider. It exercises the
simulation/rendering side only, including the current `map-v2+chase` prompt
bundle used by the autonomous OpenClaw path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import select
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_PLAYER_LOG = (
    Path.home()
    / ".config"
    / "unity3d"
    / "Allen Institute for Artificial Intelligence"
    / "AI2-THOR"
    / "Player.log"
)
_DEFAULT_RESOLUTIONS = "320x240,640x480"
_DEFAULT_OUTPUT_DIR = Path("output/benchmarks")
_SOFTWARE_RENDERER_MARKERS = (
    "llvmpipe",
    "softpipe",
    "swrast",
    "software rasterizer",
    "swiftshader",
)
_DISPLAY_SELECTION: dict[str, Any] = {}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark AI2-THOR display/Xvfb rendering and prompt-bundle throughput.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--scene", default="FloorPlan201")
    parser.add_argument("--agents", type=int, default=1)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument(
        "--suite",
        choices=["prompt", "engine", "all"],
        default="prompt",
        help="'prompt' exercises current map-v2+chase prompt rendering; "
        "'engine' measures raw engine/overhead/chase stepping; 'all' runs both.",
    )
    parser.add_argument(
        "--resolutions",
        default=_DEFAULT_RESOLUTIONS,
        help="Comma-separated WIDTHxHEIGHT list.",
    )
    parser.add_argument(
        "--display-backend",
        choices=["auto", "current", "xvfb"],
        default="auto",
        help="auto uses a detected hardware-accelerated DISPLAY, otherwise starts Xvfb. "
        "Install mesa-utils for glxinfo-based hardware detection.",
    )
    parser.add_argument(
        "--ai2thor-platform",
        choices=["default", "cloud"],
        default="default",
        help="'default' uses AI2-THOR's Linux64/X11 build. 'cloud' uses "
        "ai2thor.platform.CloudRendering and does not start or require Xvfb.",
    )
    parser.add_argument(
        "--xvfb-display",
        default="auto",
        help="X display for managed Xvfb, or 'auto' to pick :99..:119.",
    )
    parser.add_argument("--xvfb-screen", default="1280x1024x24")
    parser.add_argument("--thor-server-timeout", type=float, default=100.0)
    parser.add_argument("--thor-server-start-timeout", type=float, default=300.0)
    parser.add_argument(
        "--output",
        default=None,
        help="JSON output path. Defaults to output/benchmarks/ai2thor-rendering-<stamp>.json.",
    )
    parser.add_argument(
        "--fail-under-turns-per-sec",
        type=float,
        default=None,
        help="Exit non-zero if any successful benchmark result is below this throughput.",
    )
    return parser.parse_args(argv)


def _parse_resolutions(raw: str) -> list[tuple[int, int]]:
    resolutions: list[tuple[int, int]] = []
    for item in raw.split(","):
        value = item.strip().lower()
        if not value:
            continue
        if "x" not in value:
            raise ValueError(f"Invalid resolution {item!r}; expected WIDTHxHEIGHT")
        left, right = value.split("x", 1)
        width = int(left)
        height = int(right)
        if width <= 0 or height <= 0:
            raise ValueError(f"Invalid resolution {item!r}; dimensions must be positive")
        resolutions.append((width, height))
    if not resolutions:
        raise ValueError("At least one resolution is required")
    return resolutions


def _selected_suites(raw: str) -> list[str]:
    return ["engine", "prompt"] if raw == "all" else [raw]


def _default_output_path() -> Path:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return _DEFAULT_OUTPUT_DIR / f"ai2thor-rendering-{stamp}.json"


def _controller_platform_kwargs(ai2thor_platform: str) -> dict[str, Any]:
    if ai2thor_platform == "default":
        return {}
    if ai2thor_platform == "cloud":
        from ai2thor.platform import CloudRendering

        return {"platform": CloudRendering}
    raise ValueError(f"Unknown AI2-THOR platform: {ai2thor_platform}")


def _probe_display(display: str | None) -> dict[str, Any]:
    if not display:
        return {"display": None, "acceleration": "none", "reason": "DISPLAY is not set"}

    glxinfo = shutil.which("glxinfo")
    if glxinfo is None:
        return {
            "display": display,
            "acceleration": "unknown",
            "reason": "glxinfo not found; install mesa-utils or use --display-backend current",
        }

    env = dict(os.environ)
    env["DISPLAY"] = display
    try:
        result = subprocess.run(
            [glxinfo, "-B"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "display": display,
            "acceleration": "unknown",
            "reason": f"glxinfo probe failed: {exc}",
        }

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        return {
            "display": display,
            "acceleration": "unknown",
            "reason": "glxinfo returned non-zero",
            "detail": detail[-1] if detail else "",
        }

    parsed: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        parsed[key.strip().lower().replace(" ", "_")] = value.strip()

    renderer = parsed.get("opengl_renderer_string", "")
    vendor = parsed.get("opengl_vendor_string", "")
    haystack = f"{renderer} {vendor}".lower()
    acceleration = (
        "software"
        if any(marker in haystack for marker in _SOFTWARE_RENDERER_MARKERS)
        else "hardware"
    )
    return {
        "display": display,
        "acceleration": acceleration,
        "renderer": renderer,
        "vendor": vendor,
        "direct_rendering": parsed.get("direct_rendering", ""),
        "reason": "glxinfo -B",
    }


@contextmanager
def _managed_display(
    backend: str,
    xvfb_display: str,
    xvfb_screen: str,
    *,
    ai2thor_platform: str,
) -> Iterator[str]:
    """Yield the effective display backend and manage Xvfb when requested."""
    if ai2thor_platform == "cloud":
        _DISPLAY_SELECTION.clear()
        _DISPLAY_SELECTION.update(
            {
                "requested_backend": backend,
                "effective_backend": "none",
                "reason": "CloudRendering does not use X11/Xvfb",
            }
        )
        yield "none"
        return

    original_display = os.environ.get("DISPLAY")
    original_probe = _probe_display(original_display)
    should_start_xvfb = backend == "xvfb"
    if backend == "auto":
        should_start_xvfb = original_probe.get("acceleration") != "hardware"

    if not should_start_xvfb:
        if backend == "current" and not original_display:
            raise RuntimeError("DISPLAY is not set; use --display-backend xvfb or auto")
        _DISPLAY_SELECTION.clear()
        _DISPLAY_SELECTION.update(
            {
                "requested_backend": backend,
                "effective_backend": "current",
                "original_display": original_display,
                "current_display_probe": original_probe,
            }
        )
        yield "current"
        return

    xvfb = shutil.which("Xvfb")
    if xvfb is None:
        raise RuntimeError(
            "Xvfb not found. Install it first, e.g. `apt-get install -y xvfb libgl1 libglib2.0-0`."
        )

    if xvfb_display == "auto":
        read_fd, write_fd = os.pipe()
        cmd = [xvfb, "-displayfd", str(write_fd), "-screen", "0", xvfb_screen, "-nolisten", "tcp"]
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            pass_fds=(write_fd,),
            text=True,
        )
        os.close(write_fd)
        try:
            ready, _, _ = select.select([read_fd], [], [], 5.0)
            if not ready:
                stderr = (
                    proc.stderr.read()
                    if proc.stderr is not None and proc.poll() is not None
                    else ""
                )
                proc.terminate()
                proc.wait(timeout=5)
                raise RuntimeError(f"Xvfb did not report a display within 5s: {stderr.strip()}")
            display_number = os.read(read_fd, 32).decode("utf-8", "replace").strip()
        finally:
            os.close(read_fd)
        if not display_number:
            stderr = proc.stderr.read() if proc.stderr is not None else ""
            proc.terminate()
            proc.wait(timeout=5)
            raise RuntimeError(f"Xvfb did not report a display: {stderr.strip()}")
        display = f":{display_number}"
    else:
        display = xvfb_display
        cmd = [xvfb, display, "-screen", "0", xvfb_screen, "-nolisten", "tcp"]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    os.environ["DISPLAY"] = display
    try:
        time.sleep(0.5)
        if proc.poll() is not None:
            stderr = proc.stderr.read() if proc.stderr is not None else ""
            raise RuntimeError(f"Xvfb exited early on {display}: {stderr.strip()}")
        _DISPLAY_SELECTION.clear()
        _DISPLAY_SELECTION.update(
            {
                "requested_backend": backend,
                "effective_backend": "xvfb",
                "original_display": original_display,
                "xvfb_display": display,
                "current_display_probe": original_probe,
            }
        )
        yield "xvfb"
    finally:
        if original_display is None:
            os.environ.pop("DISPLAY", None)
        else:
            os.environ["DISPLAY"] = original_display
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _renderer_info() -> dict[str, str]:
    info: dict[str, str] = {}
    if not _PLAYER_LOG.exists():
        return info
    for line in _PLAYER_LOG.read_text(errors="ignore").splitlines():
        stripped = line.strip()
        for key in ("Renderer", "Vendor", "Version"):
            prefix = f"{key}:"
            if stripped.startswith(prefix):
                info[key.lower()] = stripped[len(prefix) :].strip()
        if stripped.startswith("Vulkan vendor="):
            info["vendor"] = _bracket_value(stripped) or stripped
        elif stripped.startswith("Vulkan renderer="):
            info["renderer"] = _bracket_value(stripped) or stripped
        elif stripped.startswith("Vulkan API version"):
            info["version"] = stripped
    return info


def _bracket_value(text: str) -> str:
    start = text.find("[")
    end = text.find("]", start + 1)
    if start == -1 or end == -1:
        return ""
    return text[start + 1 : end]


def _prompt_shapes(frames: list[Any]) -> list[list[int]]:
    return [list(frame.shape) for frame in frames]


def _run_engine_suite(
    *,
    scene: str,
    agents: int,
    width: int,
    height: int,
    steps: int,
    server_timeout: float,
    server_start_timeout: float,
    ai2thor_platform: str,
) -> dict[str, Any]:
    from roboclaws.core.engine import MultiAgentEngine

    controller_kwargs = _controller_platform_kwargs(ai2thor_platform)
    started = time.perf_counter()
    engine = MultiAgentEngine(
        scene=scene,
        agent_count=agents,
        width=width,
        height=height,
        server_timeout=server_timeout,
        server_start_timeout=server_start_timeout,
        **controller_kwargs,
    )
    init_seconds = time.perf_counter() - started
    try:
        loop_started = time.perf_counter()
        for turn in range(steps):
            agent_id = turn % agents
            engine.add_chase_cam(agent_id)
            engine.update_chase_cam(agent_id)
            _ = engine.get_overhead_frame()
            _ = engine.get_chase_cam_frame(agent_id)
            engine.step(agent_id, "RotateRight" if turn % 2 == 0 else "RotateLeft")
        loop_seconds = time.perf_counter() - loop_started
        return {
            "suite": "engine",
            "status": "ok",
            "scene": scene,
            "agents": agents,
            "width": width,
            "height": height,
            "steps": steps,
            "ai2thor_platform": ai2thor_platform,
            "init_seconds": round(init_seconds, 4),
            "loop_seconds": round(loop_seconds, 4),
            "turns_per_second": round(steps / loop_seconds, 4) if loop_seconds > 0 else 0.0,
            "renderer": _renderer_info(),
        }
    finally:
        engine.close()


def _run_prompt_suite(
    *,
    scene: str,
    agents: int,
    width: int,
    height: int,
    steps: int,
    server_timeout: float,
    server_start_timeout: float,
    ai2thor_platform: str,
) -> dict[str, Any]:
    from roboclaws.core.engine import MultiAgentEngine
    from roboclaws.core.views import make_navigation_view_context, render_navigation_prompt_bundle

    controller_kwargs = _controller_platform_kwargs(ai2thor_platform)
    started = time.perf_counter()
    engine = MultiAgentEngine(
        scene=scene,
        agent_count=agents,
        width=width,
        height=height,
        server_timeout=server_timeout,
        server_start_timeout=server_start_timeout,
        **controller_kwargs,
    )
    init_seconds = time.perf_counter() - started
    try:
        context = make_navigation_view_context(engine, agent_count=agents)
        shapes: list[list[int]] = []
        loop_started = time.perf_counter()
        for turn in range(steps):
            agent_id = turn % agents
            states = engine.get_all_agent_states()
            bundle = render_navigation_prompt_bundle(
                engine=engine,
                context=context,
                agent_states=states,
                current_agent=agent_id,
            )
            shapes = _prompt_shapes(bundle.prompt_images)
            engine.step(agent_id, "RotateRight" if turn % 2 == 0 else "RotateLeft")
        loop_seconds = time.perf_counter() - loop_started
        return {
            "suite": "prompt",
            "status": "ok",
            "scene": scene,
            "agents": agents,
            "width": width,
            "height": height,
            "steps": steps,
            "ai2thor_platform": ai2thor_platform,
            "view_variant": "map-v2+chase",
            "prompt_image_shapes": shapes,
            "init_seconds": round(init_seconds, 4),
            "loop_seconds": round(loop_seconds, 4),
            "turns_per_second": round(steps / loop_seconds, 4) if loop_seconds > 0 else 0.0,
            "renderer": _renderer_info(),
        }
    finally:
        engine.close()


def _run_one(
    *,
    suite: str,
    scene: str,
    agents: int,
    width: int,
    height: int,
    steps: int,
    server_timeout: float,
    server_start_timeout: float,
    ai2thor_platform: str,
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        runner = _run_engine_suite if suite == "engine" else _run_prompt_suite
        return runner(
            scene=scene,
            agents=agents,
            width=width,
            height=height,
            steps=steps,
            server_timeout=server_timeout,
            server_start_timeout=server_start_timeout,
            ai2thor_platform=ai2thor_platform,
        )
    except Exception as exc:  # noqa: BLE001 - benchmark should report failures as data
        return {
            "suite": suite,
            "status": "error",
            "scene": scene,
            "agents": agents,
            "width": width,
            "height": height,
            "steps": steps,
            "ai2thor_platform": ai2thor_platform,
            "wallclock_seconds": round(time.perf_counter() - started, 4),
            "error_kind": exc.__class__.__name__,
            "error": str(exc),
            "renderer": _renderer_info(),
        }


def _environment(display_backend: str) -> dict[str, Any]:
    try:
        import ai2thor

        ai2thor_version = ai2thor.__version__
    except Exception:  # noqa: BLE001 - report unavailable versions without failing early
        ai2thor_version = "unknown"
    return {
        "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "machine": platform.machine(),
        "ai2thor": ai2thor_version,
        "display": os.environ.get("DISPLAY"),
        "display_backend": display_backend,
        "display_selection": dict(_DISPLAY_SELECTION),
        "xvfb_available": shutil.which("Xvfb") is not None,
        "glxinfo_available": shutil.which("glxinfo") is not None,
        "player_log": str(_PLAYER_LOG),
    }


def _print_table(results: list[dict[str, Any]]) -> None:
    print("suite   status  size     init_s  loop_s  turns/s  renderer")
    print("------  ------  -------  ------  ------  -------  --------")
    for result in results:
        size = f"{result['width']}x{result['height']}"
        renderer = result.get("renderer", {}).get("renderer", "")
        if result["status"] == "ok":
            print(
                f"{result['suite']:<6}  {result['status']:<6}  {size:<7}  "
                f"{result['init_seconds']:>6.2f}  {result['loop_seconds']:>6.2f}  "
                f"{result['turns_per_second']:>7.2f}  {renderer}"
            )
        else:
            print(
                f"{result['suite']:<6}  {result['status']:<6}  {size:<7}  "
                f"{'-':>6}  {'-':>6}  {'-':>7}  {result.get('error_kind')}: "
                f"{result.get('error')}"
            )


def _threshold_failed(results: list[dict[str, Any]], threshold: float | None) -> bool:
    if threshold is None:
        return False
    for result in results:
        if result.get("status") == "ok" and float(result.get("turns_per_second", 0.0)) < threshold:
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    output_path = Path(args.output) if args.output else _default_output_path()
    try:
        resolutions = _parse_resolutions(args.resolutions)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        with _managed_display(
            args.display_backend,
            args.xvfb_display,
            args.xvfb_screen,
            ai2thor_platform=args.ai2thor_platform,
        ) as backend:
            results = [
                _run_one(
                    suite=suite,
                    scene=args.scene,
                    agents=args.agents,
                    width=width,
                    height=height,
                    steps=args.steps,
                    server_timeout=args.thor_server_timeout,
                    server_start_timeout=args.thor_server_start_timeout,
                    ai2thor_platform=args.ai2thor_platform,
                )
                for suite in _selected_suites(args.suite)
                for width, height in resolutions
            ]
            payload = {
                "environment": _environment(backend),
                "config": {
                    "scene": args.scene,
                    "agents": args.agents,
                    "steps": args.steps,
                    "suite": args.suite,
                    "ai2thor_platform": args.ai2thor_platform,
                    "resolutions": [[width, height] for width, height in resolutions],
                },
                "results": results,
            }
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _print_table(results)
    print(f"\njson: {output_path}")

    had_errors = any(result.get("status") != "ok" for result in results)
    if _threshold_failed(results, args.fail_under_turns_per_sec):
        print(
            f"error: one or more results fell below {args.fail_under_turns_per_sec:.2f} turns/s",
            file=sys.stderr,
        )
        return 1
    return 1 if had_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
