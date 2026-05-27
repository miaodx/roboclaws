from __future__ import annotations

import html
import json
import os
import sys
import traceback
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.subprocess_backend import MolmoSpacesSubprocessBackend

COMPARISON_SCHEMA = "molmospaces_renderer_comparison_v1"
STANDARD_LANE_ID = "standard-mujoco"
FILAMENT_LANE_ID = "molmospaces-mujoco-filament"
DEFAULT_FOCUS_SAMPLE_COUNT = 4


@dataclass(frozen=True)
class RendererLane:
    lane_id: str
    python_executable: Path
    output_subdir: str


@dataclass(frozen=True)
class RendererComparisonConfig:
    output_dir: Path
    standard_python: Path
    filament_python: Path
    seed: int = 7
    generated_mess_count: int = 10
    scene_source: str = "procthor-10k-val"
    scene_index: int = 0
    robot_name: str = "rby1m"
    focus_sample_count: int = DEFAULT_FOCUS_SAMPLE_COUNT


def run_renderer_comparison(config: RendererComparisonConfig) -> dict[str, Any]:
    """Render standard and Filament MolmoSpaces lanes into one comparison artifact."""
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    lanes = (
        RendererLane(STANDARD_LANE_ID, config.standard_python, "standard"),
        RendererLane(FILAMENT_LANE_ID, config.filament_python, "filament"),
    )
    manifest: dict[str, Any] = {
        "schema": COMPARISON_SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "scene": {
            "seed": config.seed,
            "scene_source": config.scene_source,
            "scene_index": config.scene_index,
            "include_robot": True,
            "robot_name": config.robot_name,
            "generated_mess_count": config.generated_mess_count,
        },
        "focus": {},
        "focuses": [],
        "lanes": {},
        "artifacts": {
            "comparison_manifest": "comparison_manifest.json",
            "report": "report.html",
        },
    }
    focuses: list[dict[str, str]] | None = None
    for lane in lanes:
        lane_result = _capture_lane(config, lane, focuses=focuses)
        if focuses is None and lane_result.get("focuses"):
            focuses = _string_dicts(lane_result["focuses"])
            manifest["focuses"] = [dict(focus) for focus in focuses]
            manifest["focus"] = dict(focuses[0]) if focuses else {}
        manifest["lanes"][lane.lane_id] = lane_result

    manifest_path = output_dir / "comparison_manifest.json"
    manifest_json = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    manifest_path.write_text(manifest_json, encoding="utf-8")
    render_renderer_comparison_report(manifest, output_dir=output_dir)
    return manifest


def render_renderer_comparison_report(manifest: dict[str, Any], *, output_dir: Path) -> Path:
    """Write a small side-by-side renderer comparison report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.html"
    report_path.write_text(_report_html(manifest, output_dir=output_dir), encoding="utf-8")
    return report_path


def comparison_successful(manifest: dict[str, Any]) -> bool:
    lanes = manifest.get("lanes") or {}
    return bool(lanes) and all(
        isinstance(lane, dict) and lane.get("status") == "success" for lane in lanes.values()
    )


def failed_lane_summaries(manifest: dict[str, Any]) -> list[str]:
    summaries: list[str] = []
    for lane_id, lane in (manifest.get("lanes") or {}).items():
        if not isinstance(lane, dict) or lane.get("status") == "success":
            continue
        failure = lane.get("failure") if isinstance(lane.get("failure"), dict) else {}
        message = str(failure.get("message") or lane.get("status") or "failed")
        summaries.append(f"{lane_id}: {message}")
    return summaries


def _capture_lane(
    config: RendererComparisonConfig,
    lane: RendererLane,
    *,
    focuses: list[dict[str, str]] | None,
) -> dict[str, Any]:
    lane_dir = config.output_dir / lane.output_subdir
    lane_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "label": lane.lane_id,
        "status": "pending",
        "python_executable": str(lane.python_executable),
        "images": {},
    }
    if not lane.python_executable.is_file():
        result.update(
            {
                "status": "missing_runtime",
                "failure": {
                    "type": "MissingRuntime",
                    "message": f"MolmoSpaces runtime is missing: {lane.python_executable}",
                },
            }
        )
        return result

    backend: MolmoSpacesSubprocessBackend | None = None
    previous_persistent_worker = os.environ.get("ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER")
    try:
        os.environ["ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER"] = "0"
        backend = MolmoSpacesSubprocessBackend(
            run_dir=lane_dir,
            seed=config.seed,
            python_executable=lane.python_executable,
            scene_source=config.scene_source,
            scene_index=config.scene_index,
            include_robot=True,
            robot_name=config.robot_name,
            generated_mess_count=config.generated_mess_count,
        )
        lane_focuses = focuses or _focuses_from_backend(
            backend,
            limit=config.focus_sample_count,
        )
        if not lane_focuses:
            raise RuntimeError("no focus samples were available for renderer comparison")
        snapshot_path = lane_dir / "snapshot.png"
        snapshot = backend.write_snapshot(
            snapshot_path,
            title=f"{lane.lane_id} seed={config.seed}",
        )
        images = {
            "snapshot": _image_entry(
                output_dir=config.output_dir,
                path=snapshot,
                shape=_image_shape(snapshot),
            )
        }
        samples: list[dict[str, Any]] = []
        first_robot_view_provenance: dict[str, Any] = {}
        for index, lane_focus in enumerate(lane_focuses, start=1):
            sample_id = lane_focus.get("sample_id") or f"focus-{index:02d}"
            navigation = backend.navigate_to_object(lane_focus["object_id"])
            if not navigation.get("ok", False):
                raise RuntimeError(
                    "focus navigation failed: "
                    f"{json.dumps(navigation, sort_keys=True, ensure_ascii=False)}"
                )
            robot_views = backend.write_robot_views(
                lane_dir / "robot_views",
                label=sample_id,
                focus_object_id=lane_focus.get("object_id"),
                focus_receptacle_id=lane_focus.get("source_receptacle_id"),
            )
            if not robot_views.get("ok", False):
                raise RuntimeError(
                    "robot view capture failed: "
                    f"{json.dumps(robot_views, sort_keys=True, ensure_ascii=False)}"
                )
            view_images = _robot_view_images(
                output_dir=config.output_dir,
                robot_views=robot_views,
            )
            if not first_robot_view_provenance:
                first_robot_view_provenance = dict(robot_views.get("view_provenance", {}))
                images.update(view_images)
            samples.append(
                {
                    "sample_id": sample_id,
                    "focus": dict(lane_focus),
                    "navigation": navigation,
                    "images": view_images,
                    "robot_view_provenance": robot_views.get("view_provenance", {}),
                }
            )
        result.update(
            {
                "status": "success",
                "runtime": dict(backend.runtime),
                "model_stats": dict(backend.model_stats),
                "scene_xml": backend.scene_xml,
                "requested_generated_mess_count": backend.requested_generated_mess_count,
                "generated_mess_count": backend.generated_mess_count,
                "focus": dict(lane_focuses[0]),
                "focuses": [dict(focus) for focus in lane_focuses],
                "images": images,
                "samples": samples,
                "robot_view_provenance": first_robot_view_provenance,
            }
        )
    except Exception as exc:  # pragma: no cover - exercised by local runtime failures.
        result.update(
            {
                "status": "failed",
                "failure": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                    "traceback": traceback.format_exc(limit=8),
                },
            }
        )
    finally:
        if backend is not None:
            backend.close()
        if previous_persistent_worker is None:
            os.environ.pop("ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER", None)
        else:
            os.environ["ROBOCLAWS_MOLMOSPACES_PERSISTENT_WORKER"] = previous_persistent_worker
    return result


def _focuses_from_backend(
    backend: MolmoSpacesSubprocessBackend,
    *,
    limit: int,
) -> list[dict[str, str]]:
    locations = backend.object_locations()
    focuses = []
    for index, target in enumerate(
        backend.scenario.private_manifest.targets[: max(1, limit)],
        start=1,
    ):
        object_id = target.object_id
        focuses.append(
            {
                "sample_id": f"focus-{index:02d}",
                "object_id": object_id,
                "source_receptacle_id": locations.get(object_id, ""),
                "target_receptacle_id": target.valid_receptacle_ids[0],
            }
        )
    return focuses


def _robot_view_images(
    *,
    output_dir: Path,
    robot_views: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    images = {}
    view_paths = robot_views.get("views") if isinstance(robot_views.get("views"), dict) else {}
    shapes = robot_views.get("shapes") if isinstance(robot_views.get("shapes"), dict) else {}
    for kind in ("fpv", "chase", "verify", "map"):
        if kind not in view_paths:
            continue
        images[kind] = _image_entry(
            output_dir=output_dir,
            path=Path(str(view_paths[kind])),
            shape=shapes.get(kind),
        )
    return images


def _image_shape(path: Path) -> list[int]:
    from PIL import Image

    with Image.open(path) as image:
        width, height = image.size
        bands = image.getbands()
    return [height, width, len(bands)]


def _image_entry(*, output_dir: Path, path: Path, shape: Any) -> dict[str, Any]:
    return {
        "path": _relpath(path, output_dir),
        "dimensions": _dimensions_from_shape(shape),
    }


def _dimensions_from_shape(shape: Any) -> dict[str, int]:
    if not isinstance(shape, list) or len(shape) < 2:
        return {}
    try:
        height = int(shape[0])
        width = int(shape[1])
        dimensions = {"width": width, "height": height}
        if len(shape) >= 3:
            dimensions["channels"] = int(shape[2])
        return dimensions
    except (TypeError, ValueError):
        return {}


def _relpath(path: Path, output_dir: Path) -> str:
    try:
        return str(path.resolve().relative_to(output_dir.resolve()))
    except ValueError:
        return str(path)


def _string_dict(data: Any) -> dict[str, str]:
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if value is not None}


def _string_dicts(data: Any) -> list[dict[str, str]]:
    if not isinstance(data, list):
        return []
    return [_string_dict(item) for item in data if isinstance(item, dict)]


def _report_html(manifest: dict[str, Any], *, output_dir: Path) -> str:
    title = "MolmoSpaces Renderer Comparison"
    scene = manifest.get("scene") if isinstance(manifest.get("scene"), dict) else {}
    focus = manifest.get("focus") if isinstance(manifest.get("focus"), dict) else {}
    lanes = manifest.get("lanes") if isinstance(manifest.get("lanes"), dict) else {}
    body = "\n".join(
        [
            _summary(title, scene, focus, lanes),
            _runtime_section(lanes),
            _failure_section(lanes),
            _snapshot_section(lanes, output_dir=output_dir),
            _sample_sections(lanes, output_dir=output_dir),
        ]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      color: #20242c;
      background: #eef2f6;
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 28px 20px 48px;
    }}
    h1 {{ margin: 0; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; letter-spacing: 0; }}
    .summary {{
      background: #20242c;
      color: #f8fafc;
      border-radius: 8px;
      padding: 22px;
      box-shadow: 0 14px 34px rgba(25, 32, 44, 0.16);
    }}
    .eyebrow {{
      margin: 0 0 6px;
      color: #a7d8cf;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .summary p {{ color: #dbe5ef; max-width: 880px; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 7px 10px;
      overflow-wrap: anywhere;
    }}
    .summary .badge {{
      background: rgba(255, 255, 255, 0.09);
      border-color: rgba(255, 255, 255, 0.18);
      color: #e9edf4;
    }}
    .panel {{
      background: #ffffff;
      border: 1px solid #d8dee8;
      border-radius: 8px;
      padding: 18px;
      margin-top: 18px;
      box-shadow: 0 5px 16px rgba(25, 32, 44, 0.06);
    }}
    .note {{ color: #565f70; margin: 0 0 12px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #d9dde6; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{
      padding: 9px 10px;
      text-align: left;
      border-bottom: 1px solid #e5e8ee;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    th {{ background: #eef1f5; font-weight: 650; }}
    .image-comparison-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 12px;
    }}
    .sample-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
    }}
    .sample-header {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 0 0 12px;
    }}
    .sample-block {{
      margin-top: 18px;
      padding-top: 18px;
      border-top: 1px solid #e5e8ee;
    }}
    figure {{
      margin: 0;
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 10px;
    }}
    img {{ width: 100%; height: auto; display: block; }}
    figcaption {{
      display: grid;
      gap: 3px;
      margin-top: 8px;
      color: #565f70;
      font-size: 14px;
    }}
    figcaption strong {{ color: #20242c; }}
    figcaption span {{ color: #647083; font-size: 12px; }}
    .missing-image {{
      display: grid;
      place-items: center;
      min-height: 180px;
      border: 1px dashed #cbd5e1;
      border-radius: 6px;
      background: #f8fafc;
      color: #647083;
    }}
    @media (max-width: 640px) {{
      main {{ padding: 18px 12px 36px; }}
      .image-comparison-grid {{ grid-template-columns: 1fr; }}
      .sample-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body><main>{body}</main></body>
</html>
"""


def _summary(
    title: str,
    scene: dict[str, Any],
    focus: dict[str, Any],
    lanes: dict[str, Any],
) -> str:
    success_count = sum(
        1 for lane in lanes.values() if isinstance(lane, dict) and lane.get("status") == "success"
    )
    lane_count = len(lanes)
    badges = [
        ("seed", scene.get("seed", "")),
        ("scene", f"{scene.get('scene_source', '')}:{scene.get('scene_index', '')}"),
        ("robot", scene.get("robot_name", "")),
        ("mess count", scene.get("generated_mess_count", "")),
        ("focus object", focus.get("object_id", "")),
        ("source", focus.get("source_receptacle_id", "")),
        ("target", focus.get("target_receptacle_id", "")),
        ("lanes ready", f"{success_count}/{lane_count}"),
    ]
    return f"""
<section class="summary">
  <p class="eyebrow">Render-only A/B</p>
  <h1>{html.escape(title)}</h1>
  <p>
    Standard MuJoCo and MolmoSpaces Filament MuJoCo are rendered from the same
    deterministic scene setup. This report is only a visual gate; full cleanup A/B
    remains deferred until the image quality difference is worth the runtime cost.
  </p>
  <div class="badges">{_badges(badges)}</div>
</section>
"""


def _runtime_section(lanes: dict[str, Any]) -> str:
    rows = []
    for lane_id, lane in lanes.items():
        if not isinstance(lane, dict):
            continue
        runtime = lane.get("runtime") if isinstance(lane.get("runtime"), dict) else {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(lane_id))}</td>"
            f"<td>{html.escape(str(lane.get('status', 'unknown')))}</td>"
            f"<td>{html.escape(str(lane.get('python_executable', '')))}</td>"
            f"<td>{html.escape(str(runtime.get('python_version', '')))}</td>"
            f"<td>{html.escape(str(runtime.get('mujoco_version', '')))}</td>"
            f"<td>{html.escape(str(runtime.get('mujoco_renderer_runtime', '')))}</td>"
            f"<td>{html.escape(str(lane.get('scene_xml', '')))}</td>"
            "</tr>"
        )
    return f"""
<section class="panel">
  <h2>Runtime Metadata</h2>
  <div class="table-wrap">
    <table>
      <thead>
        <tr>
          <th>Lane</th><th>Status</th><th>Python</th>
          <th>Python version</th><th>MuJoCo</th><th>Renderer runtime</th><th>Scene XML</th>
        </tr>
      </thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>
</section>
"""


def _failure_section(lanes: dict[str, Any]) -> str:
    rows = []
    for lane_id, lane in lanes.items():
        if not isinstance(lane, dict) or lane.get("status") == "success":
            continue
        failure = lane.get("failure") if isinstance(lane.get("failure"), dict) else {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(lane_id))}</td>"
            f"<td>{html.escape(str(lane.get('status', 'unknown')))}</td>"
            f"<td>{html.escape(str(failure.get('type', '')))}</td>"
            f"<td>{html.escape(str(failure.get('message', '')))}</td>"
            "</tr>"
        )
    if not rows:
        return ""
    return f"""
<section class="panel">
  <h2>Lane Failures</h2>
  <p class="note">Failures are explicit. The Filament lane does not fall back to regular MuJoCo.</p>
  <div class="table-wrap">
    <table>
      <thead><tr><th>Lane</th><th>Status</th><th>Error type</th><th>Message</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>
</section>
"""


def _snapshot_section(lanes: dict[str, Any], *, output_dir: Path) -> str:
    figures = []
    for lane_id, lane in lanes.items():
        if not isinstance(lane, dict):
            continue
        image = _lane_image(lane, "snapshot")
        figures.append(
            _figure(lane_id=str(lane_id), kind="snapshot", image=image, output_dir=output_dir)
        )
    return f"""
<section class="panel" data-view-kind="snapshot">
  <h2>Snapshot Comparison</h2>
  <div class="image-comparison-grid">{"".join(figures)}</div>
</section>
"""


def _sample_sections(lanes: dict[str, Any], *, output_dir: Path) -> str:
    sample_ids = _sample_ids(lanes)
    if not sample_ids:
        return "\n".join(
            _legacy_image_section(kind, lanes, output_dir=output_dir)
            for kind in ("fpv", "chase", "verify", "map")
        )
    blocks = []
    for sample_id in sample_ids:
        focus = _sample_focus(lanes, sample_id)
        badges = _badges(
            [
                ("sample", sample_id),
                ("focus object", focus.get("object_id", "")),
                ("source", focus.get("source_receptacle_id", "")),
                ("target", focus.get("target_receptacle_id", "")),
            ]
        )
        kind_blocks = []
        for kind in ("fpv", "chase", "verify", "map"):
            figures = []
            for lane_id, lane in lanes.items():
                if not isinstance(lane, dict):
                    continue
                sample = _lane_sample(lane, sample_id)
                image = _sample_image(sample, kind)
                figures.append(
                    _figure(
                        lane_id=str(lane_id),
                        kind=f"{sample_id} {kind}",
                        image=image,
                        output_dir=output_dir,
                    )
                )
            title = "FPV" if kind == "fpv" else kind.title()
            kind_blocks.append(
                f"""
<h3>{html.escape(title)}</h3>
<div class="sample-grid">{"".join(figures)}</div>
"""
            )
        blocks.append(
            f"""
<div class="sample-block" data-sample-id="{html.escape(sample_id)}">
  <div class="sample-header">{badges}</div>
  {"".join(kind_blocks)}
</div>
"""
        )
    return f"""
<section class="panel">
  <h2>Robot View Samples</h2>
  <p class="note">
    Each sample navigates the robot to a different generated cleanup object before
    rendering FPV, chase, verify, and map views.
  </p>
  {"".join(blocks)}
</section>
"""


def _legacy_image_section(kind: str, lanes: dict[str, Any], *, output_dir: Path) -> str:
    figures = []
    for lane_id, lane in lanes.items():
        if not isinstance(lane, dict):
            continue
        image = _lane_image(lane, kind)
        figures.append(_figure(lane_id=str(lane_id), kind=kind, image=image, output_dir=output_dir))
    title = "FPV" if kind == "fpv" else kind.title()
    return f"""
<section class="panel" data-view-kind="{html.escape(kind)}">
  <h2>{html.escape(title)} Comparison</h2>
  <div class="image-comparison-grid">{"".join(figures)}</div>
</section>
"""


def _sample_ids(lanes: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for lane in lanes.values():
        if not isinstance(lane, dict):
            continue
        for sample in lane.get("samples") or []:
            if not isinstance(sample, dict):
                continue
            sample_id = str(sample.get("sample_id") or "")
            if sample_id and sample_id not in ids:
                ids.append(sample_id)
    return ids


def _lane_sample(lane: dict[str, Any], sample_id: str) -> dict[str, Any] | None:
    samples = lane.get("samples")
    if not isinstance(samples, list):
        return None
    for sample in samples:
        if isinstance(sample, dict) and str(sample.get("sample_id")) == sample_id:
            return sample
    return None


def _sample_focus(lanes: dict[str, Any], sample_id: str) -> dict[str, Any]:
    for lane in lanes.values():
        if not isinstance(lane, dict):
            continue
        sample = _lane_sample(lane, sample_id)
        if isinstance(sample, dict) and isinstance(sample.get("focus"), dict):
            return sample["focus"]
    return {}


def _sample_image(sample: dict[str, Any] | None, kind: str) -> dict[str, Any] | None:
    if not isinstance(sample, dict):
        return None
    images = sample.get("images")
    if not isinstance(images, dict):
        return None
    image = images.get(kind)
    return image if isinstance(image, dict) else None


def _lane_image(lane: dict[str, Any], kind: str) -> dict[str, Any] | None:
    images = lane.get("images")
    if not isinstance(images, dict):
        return None
    image = images.get(kind)
    return image if isinstance(image, dict) else None


def _figure(
    *,
    lane_id: str,
    kind: str,
    image: dict[str, Any] | None,
    output_dir: Path,
) -> str:
    if not image:
        return (
            f'<figure><div class="missing-image">No {html.escape(kind)} image</div>'
            f"<figcaption><strong>{html.escape(lane_id)}</strong>"
            f"<span>{html.escape(kind)}</span></figcaption></figure>"
        )
    path = str(image.get("path", ""))
    dimensions = image.get("dimensions") if isinstance(image.get("dimensions"), dict) else {}
    detail = _dimension_text(dimensions)
    image_path = output_dir / path
    missing = "" if image_path.is_file() else " (missing on disk)"
    return (
        f'<figure><img src="{html.escape(path, quote=True)}" '
        f'alt="{html.escape(lane_id)} {html.escape(kind)} render">'
        f"<figcaption><strong>{html.escape(lane_id)}</strong>"
        f"<span>{html.escape(detail + missing)}</span></figcaption></figure>"
    )


def _dimension_text(dimensions: dict[str, Any]) -> str:
    width = dimensions.get("width")
    height = dimensions.get("height")
    if not width or not height:
        return "dimensions unavailable"
    channels = dimensions.get("channels")
    suffix = f", {channels} channels" if channels else ""
    return f"{width} x {height}{suffix}"


def _badges(items: list[tuple[str, Any]]) -> str:
    parts = []
    for label, value in items:
        if value is None or value == "":
            continue
        parts.append(
            f'<span class="badge">{html.escape(str(label))}: '
            f"<strong>{html.escape(str(value))}</strong></span>"
        )
    return "".join(parts)


def default_output_dir() -> Path:
    stamp = datetime.now().astimezone().strftime("%m%d_%H%M")
    return Path("output/molmo/renderer-comparison") / stamp


def setup_command() -> str:
    python311 = "/home/mi/.local/share/uv/python/cpython-3.11.14-linux-x86_64-gnu/bin/python3.11"
    return (
        'UV_PROJECT_ENVIRONMENT="$PWD/.venv-molmospaces-filament" \\\n'
        "  uv sync --project sidecars/molmospaces-filament \\\n"
        f"  --python {python311}"
    )


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Compare MolmoSpaces MuJoCo renderers.")
    parser.add_argument("--output-dir", type=Path, default=default_output_dir())
    parser.add_argument("--standard-python", type=Path, default=Path(".venv/bin/python"))
    parser.add_argument(
        "--filament-python",
        type=Path,
        default=Path(".venv-molmospaces-filament/bin/python"),
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--generated-mess-count", type=int, default=10)
    parser.add_argument("--scene-source", default="procthor-10k-val")
    parser.add_argument("--scene-index", type=int, default=0)
    parser.add_argument("--robot-name", default="rby1m")
    parser.add_argument("--focus-sample-count", type=int, default=DEFAULT_FOCUS_SAMPLE_COUNT)
    args = parser.parse_args(argv)

    manifest = run_renderer_comparison(
        RendererComparisonConfig(
            output_dir=args.output_dir,
            standard_python=args.standard_python,
            filament_python=args.filament_python,
            seed=args.seed,
            generated_mess_count=args.generated_mess_count,
            scene_source=args.scene_source,
            scene_index=args.scene_index,
            robot_name=args.robot_name,
            focus_sample_count=args.focus_sample_count,
        )
    )
    print(f"renderer comparison manifest: {args.output_dir / 'comparison_manifest.json'}")
    print(f"renderer comparison report: {args.output_dir / 'report.html'}")
    if comparison_successful(manifest):
        return 0
    print("renderer comparison failed:", file=sys.stderr)
    for summary in failed_lane_summaries(manifest):
        print(f"  {summary}", file=sys.stderr)
    if any("MolmoSpaces runtime is missing" in item for item in failed_lane_summaries(manifest)):
        print("Filament sidecar setup command:", file=sys.stderr)
        print(setup_command(), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
