from __future__ import annotations

from pathlib import Path
from typing import Any

from roboclaws.core.json_sources import read_json_object


def load_scene_metadata(scene_usd_path: Path) -> dict[str, dict[str, Any]]:
    metadata_path = scene_usd_path.parent / "scene_metadata.json"
    if not metadata_path.is_file():
        return {}
    try:
        payload = read_json_object(metadata_path, label="scene metadata JSON")
    except ValueError as exc:
        message = str(exc)
        if "source must contain valid JSON object" in message:
            raise RuntimeError(f"malformed scene metadata JSON: {metadata_path}") from exc
        if "source must contain a JSON object" in message:
            raise RuntimeError(
                f"scene metadata JSON must be a JSON object: {metadata_path}"
            ) from exc
        raise
    objects = payload.get("objects")
    if not isinstance(objects, dict):
        raise RuntimeError(f"scene metadata JSON objects must be a JSON object: {metadata_path}")
    invalid_object = next(
        (value for value in objects.values() if not isinstance(value, dict)),
        None,
    )
    if invalid_object is not None:
        raise RuntimeError(
            "scene metadata JSON objects values must be JSON objects: "
            f"{metadata_path} entry_type={type(invalid_object).__name__}"
        )
    return {str(key): dict(value) for key, value in objects.items()}


def load_local_isaac_scene_index(scene_usd_path: Path) -> dict[str, Any]:
    """Load the newest nearby Isaac scene index for USD prim path hints.

    Any support poses in this artifact are deliberately ignored by the camera
    comparison; Isaac targets are resolved from USD prim world bounds instead.
    """

    root = scene_usd_path.parents[2] if len(scene_usd_path.parents) > 2 else Path("output/isaaclab")
    candidates = sorted(
        root.glob("cleanup-smoke/*/isaac_scene_index.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        payload = _read_optional_scene_index(candidate)
        if not payload:
            continue
        if str(payload.get("scene_usd") or "") != str(scene_usd_path):
            continue
        return payload
    return {}


def _read_optional_scene_index(path: Path) -> dict[str, Any]:
    try:
        return read_json_object(path, label="local Isaac scene index")
    except (OSError, ValueError):
        return {}


def isaac_scene_index_entry(anchor_id: str, scene_index: dict[str, Any]) -> dict[str, Any]:
    receptacles = scene_index.get("receptacle_index") if isinstance(scene_index, dict) else None
    if not isinstance(receptacles, dict):
        return {}
    raw = receptacles.get(anchor_id)
    return dict(raw) if isinstance(raw, dict) else {}


def support_pose_position(value: Any) -> list[float] | None:
    if not isinstance(value, dict):
        return None
    try:
        return [
            float(value["x"]),
            float(value["y"]),
            float(value.get("z", 0.0)),
        ]
    except (KeyError, TypeError, ValueError):
        return None
