#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import importlib.metadata as importlib_metadata
import json
import math
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

import mujoco
from PIL import Image, ImageDraw

from roboclaws.household.camera_control import (
    ANCHOR_ORBIT_CAMERA_MODEL,
    CAMERA_CONTROL_API_NAME,
    CANONICAL_CAMERA_MODEL,
    load_camera_control_request,
    normalize_camera_control_request,
)
from roboclaws.household.color_management import apply_camera_color_profile
from roboclaws.household.generated_mess import (
    GENERATED_MESS_MANIFEST_SCHEMA,
    generated_mess_success_threshold,
    select_generated_mess_targets,
    targets_from_generated_mess_manifest,
)
from roboclaws.household.robot_view_camera_control import (
    robot_mounted_head_camera_control_contract,
    robot_view_display_color_profile,
)
from roboclaws.household.robot_view_pose import (
    angle_delta,
    point_inside_room_outline,
    resolve_cleanup_robot_pose,
    robot_head_pitch_for_target,
    room_for_point,
    room_outline_clearance,
)

BACKEND = "molmospaces_subprocess"
API_SEMANTIC_PROVENANCE = "api_semantic"
HELD_LOCATION_ID = "held_by_agent"
DEFAULT_RENDER_WIDTH = 540
DEFAULT_RENDER_HEIGHT = 360
_MODEL_DATA_CACHE: dict[tuple[str, str], tuple[mujoco.MjModel, mujoco.MjData]] = {}
_FILAMENT_RESOURCE_PROVIDER: _FilamentResourceProvider | None = None
_MUJOCO_FILAMENT_RUNTIME: bool | None = None


class _MjResource(ctypes.Structure):
    _fields_ = [
        ("name", ctypes.c_char_p),
        ("data", ctypes.c_void_p),
        ("vfs", ctypes.c_void_p),
        ("timestamp", ctypes.c_char * 512),
        ("provider", ctypes.c_void_p),
    ]


_OpenResourceCallback = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.POINTER(_MjResource))
_ReadResourceCallback = ctypes.CFUNCTYPE(
    ctypes.c_int,
    ctypes.POINTER(_MjResource),
    ctypes.POINTER(ctypes.c_void_p),
)
_CloseResourceCallback = ctypes.CFUNCTYPE(None, ctypes.POINTER(_MjResource))


class _MjpResourceProvider(ctypes.Structure):
    _fields_ = [
        ("prefix", ctypes.c_char_p),
        ("open", ctypes.c_void_p),
        ("read", ctypes.c_void_p),
        ("close", ctypes.c_void_p),
        ("mount", ctypes.c_void_p),
        ("unmount", ctypes.c_void_p),
        ("modified", ctypes.c_void_p),
        ("data", ctypes.c_void_p),
    ]


class _FilamentResourceProvider:
    """Keep ctypes callbacks alive while MuJoCo reads bundled Filament assets."""

    def __init__(self, assets_dir: Path) -> None:
        self.assets_dir = assets_dir
        self._buffers: dict[int, tuple[ctypes.Array[ctypes.c_char], int]] = {}
        self.open_callback = _OpenResourceCallback(self._open)
        self.read_callback = _ReadResourceCallback(self._read)
        self.close_callback = _CloseResourceCallback(self._close)
        self.provider = _MjpResourceProvider(
            prefix=b"filament",
            open=ctypes.cast(self.open_callback, ctypes.c_void_p).value,
            read=ctypes.cast(self.read_callback, ctypes.c_void_p).value,
            close=ctypes.cast(self.close_callback, ctypes.c_void_p).value,
            mount=None,
            unmount=None,
            modified=None,
            data=None,
        )

    def _key(self, resource: ctypes.POINTER(_MjResource)) -> int:
        return ctypes.addressof(resource.contents)

    def _open(self, resource: ctypes.POINTER(_MjResource)) -> int:
        resource_name = (resource.contents.name or b"").decode("utf-8", errors="replace")
        if not resource_name.startswith("filament:"):
            return 0
        relative_name = resource_name.split(":", 1)[1]
        if (
            not relative_name
            or "/" in relative_name
            or "\\" in relative_name
            or relative_name in {".", ".."}
        ):
            return 0
        asset_path = self.assets_dir / relative_name
        if not asset_path.is_file():
            return 0
        asset_bytes = asset_path.read_bytes()
        buffer = ctypes.create_string_buffer(asset_bytes, len(asset_bytes))
        self._buffers[self._key(resource)] = (buffer, len(asset_bytes))
        timestamp = str(asset_path.stat().st_mtime_ns).encode("ascii")[:511]
        resource.contents.timestamp = timestamp
        return 1

    def _read(
        self,
        resource: ctypes.POINTER(_MjResource),
        output_buffer: ctypes.POINTER(ctypes.c_void_p),
    ) -> int:
        entry = self._buffers.get(self._key(resource))
        if entry is None:
            return -1
        buffer, byte_count = entry
        output_buffer[0] = ctypes.cast(buffer, ctypes.c_void_p).value
        return byte_count

    def _close(self, resource: ctypes.POINTER(_MjResource)) -> None:
        self._buffers.pop(self._key(resource), None)


def _register_filament_resource_provider_if_available() -> None:
    """Register MuJoCo's packaged Filament assets when the sidecar wheel is active."""
    global _FILAMENT_RESOURCE_PROVIDER
    if _FILAMENT_RESOURCE_PROVIDER is not None:
        return
    assets_dir = Path(mujoco.__file__).resolve().parent / "filament" / "assets" / "data"
    if not assets_dir.is_dir():
        return
    if not (assets_dir / "pbr.filamat").is_file():
        raise RuntimeError(f"incomplete MuJoCo Filament asset directory: {assets_dir}")
    lib_path = Path(mujoco.__file__).resolve().parent / f"libmujoco.so.{mujoco.__version__}"
    if not lib_path.is_file():
        return
    lib = ctypes.CDLL(str(lib_path))
    try:
        lib.mjp_getResourceProvider.argtypes = [ctypes.c_char_p]
        lib.mjp_getResourceProvider.restype = ctypes.c_void_p
        if lib.mjp_getResourceProvider(b"filament:pbr.filamat"):
            return
        lib.mjp_registerResourceProvider.argtypes = [ctypes.POINTER(_MjpResourceProvider)]
        lib.mjp_registerResourceProvider.restype = ctypes.c_int
    except AttributeError:
        return
    provider = _FilamentResourceProvider(assets_dir)
    slot = lib.mjp_registerResourceProvider(ctypes.byref(provider.provider))
    if slot < 0:
        raise RuntimeError("failed to register MuJoCo Filament resource provider")
    _FILAMENT_RESOURCE_PROVIDER = provider


_register_filament_resource_provider_if_available()


def _is_mujoco_filament_runtime() -> bool:
    """Return true when imported ``mujoco`` is the TestPyPI Filament wheel."""
    global _MUJOCO_FILAMENT_RUNTIME
    if _MUJOCO_FILAMENT_RUNTIME is not None:
        return _MUJOCO_FILAMENT_RUNTIME
    try:
        filament_version = importlib_metadata.version("mujoco-filament")
    except importlib_metadata.PackageNotFoundError:
        _MUJOCO_FILAMENT_RUNTIME = False
        return False
    assets_dir = Path(mujoco.__file__).resolve().parent / "filament" / "assets" / "data"
    _MUJOCO_FILAMENT_RUNTIME = filament_version == mujoco.__version__ and assets_dir.is_dir()
    return _MUJOCO_FILAMENT_RUNTIME


def _mujoco_renderer_runtime_id() -> str:
    return "mujoco-filament" if _is_mujoco_filament_runtime() else "standard-mujoco"


def _normalize_renderer_frame(frame: Any) -> Any:
    if not _is_mujoco_filament_runtime():
        return frame
    import numpy as np

    return np.ascontiguousarray(np.flipud(frame))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="MolmoSpaces JSON worker for roboclaws.")
    parser.add_argument("--state-path", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--seed", type=int, default=7)
    init.add_argument("--scene-source", default="procthor-10k-val")
    init.add_argument("--scene-index", type=int, default=0)
    init.add_argument("--include-robot", action="store_true")
    init.add_argument("--robot-name", default="rby1m")
    init.add_argument("--generated-mess-count", type=int, default=5)
    init.add_argument(
        "--generated-mess-object-id",
        action="append",
        help="Private run-control object id to include in the generated mess set. Repeatable.",
    )
    init.add_argument(
        "--generated-mess-manifest-path",
        type=Path,
        help="Private backend-neutral generated mess manifest to apply during init.",
    )

    subparsers.add_parser("observe")
    subparsers.add_parser("locations")

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--output-path", type=Path, required=True)
    snapshot.add_argument("--title", default="")
    snapshot.add_argument("--render-width", type=int, default=DEFAULT_RENDER_WIDTH)
    snapshot.add_argument("--render-height", type=int, default=DEFAULT_RENDER_HEIGHT)

    robot_views = subparsers.add_parser("robot_views")
    robot_views.add_argument("--output-dir", type=Path, required=True)
    robot_views.add_argument("--label", required=True)
    robot_views.add_argument("--focus-object-id")
    robot_views.add_argument("--focus-receptacle-id")
    robot_views.add_argument("--camera-yaw-offset-deg", type=float, default=0.0)
    robot_views.add_argument("--camera-pitch-offset-deg", type=float, default=0.0)
    robot_views.add_argument("--render-width", type=int, default=DEFAULT_RENDER_WIDTH)
    robot_views.add_argument("--render-height", type=int, default=DEFAULT_RENDER_HEIGHT)

    camera_views = subparsers.add_parser("camera_views")
    camera_views.add_argument("--output-dir", type=Path, required=True)
    camera_views.add_argument("--view-specs-path", type=Path)
    camera_views.add_argument("--camera-request-path", type=Path)
    camera_views.add_argument("--render-width", type=int, default=DEFAULT_RENDER_WIDTH)
    camera_views.add_argument("--render-height", type=int, default=DEFAULT_RENDER_HEIGHT)

    navigate_object = subparsers.add_parser("navigate_to_object")
    navigate_object.add_argument("--object-id", required=True)

    navigate_waypoint = subparsers.add_parser("navigate_to_waypoint")
    navigate_waypoint.add_argument("--waypoint-json", required=True)

    navigate_receptacle = subparsers.add_parser("navigate_to_receptacle")
    navigate_receptacle.add_argument("--receptacle-id", required=True)

    frame_comparison_object_parser = subparsers.add_parser("frame_comparison_object")
    frame_comparison_object_parser.add_argument("--object-id", required=True)

    pick = subparsers.add_parser("pick")
    pick.add_argument("--object-id", required=True)

    open_receptacle_parser = subparsers.add_parser("open_receptacle")
    open_receptacle_parser.add_argument("--receptacle-id", required=True)

    close_receptacle_parser = subparsers.add_parser("close_receptacle")
    close_receptacle_parser.add_argument("--receptacle-id", required=True)

    place = subparsers.add_parser("place")
    place.add_argument("--receptacle-id", required=True)

    place_inside_parser = subparsers.add_parser("place_inside")
    place_inside_parser.add_argument("--receptacle-id", required=True)

    done = subparsers.add_parser("done")
    done.add_argument("--reason", default="")

    subparsers.add_parser("serve")

    args = parser.parse_args(argv)
    if args.command == "serve":
        serve(args.state_path)
        return
    if args.command == "init":
        result = init_state(
            state_path=args.state_path,
            seed=args.seed,
            scene_source=args.scene_source,
            scene_index=args.scene_index,
            include_robot=args.include_robot,
            robot_name=args.robot_name,
            generated_mess_count=args.generated_mess_count,
            generated_mess_object_ids=tuple(args.generated_mess_object_id or ()),
            generated_mess_manifest_path=args.generated_mess_manifest_path,
        )
    else:
        state = _read_state(args.state_path)
        if args.command == "observe":
            result = observe(state)
            _write_state(args.state_path, state)
        elif args.command == "locations":
            result = _ok("locations", final_locations=_read_locations(state))
        elif args.command == "snapshot":
            result = write_snapshot(
                state,
                args.output_path,
                args.title,
                width=args.render_width,
                height=args.render_height,
            )
        elif args.command == "robot_views":
            result = write_robot_views(
                state,
                args.output_dir,
                args.label,
                focus_object_id=args.focus_object_id,
                focus_receptacle_id=args.focus_receptacle_id,
                camera_yaw_offset_deg=args.camera_yaw_offset_deg,
                camera_pitch_offset_deg=args.camera_pitch_offset_deg,
                width=args.render_width,
                height=args.render_height,
            )
        elif args.command == "camera_views":
            camera_request = _load_camera_request_from_args(
                view_specs_path=args.view_specs_path,
                camera_request_path=args.camera_request_path,
                width=args.render_width,
                height=args.render_height,
            )
            result = write_camera_views(
                state,
                args.output_dir,
                camera_request,
                width=args.render_width,
                height=args.render_height,
            )
        elif args.command == "navigate_to_object":
            result = navigate_to_object(state, args.object_id)
            _write_state(args.state_path, state)
        elif args.command == "navigate_to_waypoint":
            result = navigate_to_waypoint(
                state,
                _json_object_from_text(args.waypoint_json),
            )
            _write_state(args.state_path, state)
        elif args.command == "navigate_to_receptacle":
            result = navigate_to_receptacle(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "frame_comparison_object":
            result = frame_comparison_object(state, args.object_id)
            _write_state(args.state_path, state)
        elif args.command == "pick":
            result = pick_object(state, args.object_id)
            _write_state(args.state_path, state)
        elif args.command == "open_receptacle":
            result = open_receptacle(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "close_receptacle":
            result = close_receptacle(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "place":
            result = place_object(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "place_inside":
            result = place_inside_object(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "done":
            result = done_cleanup(state, args.reason)
        else:
            raise AssertionError(args.command)

    print(json.dumps(result, sort_keys=True))


def serve(state_path: Path) -> None:
    """Serve JSON-line worker requests while keeping MuJoCo state warm."""
    print(json.dumps({"ok": True, "event": "ready", "tool": "serve"}, sort_keys=True), flush=True)
    for line in sys.stdin:
        if not line.strip():
            continue
        request: Any = {}
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
            request_id = request.get("id")
            command = str(request.get("command") or "")
            kwargs = request.get("kwargs") or {}
            if not isinstance(kwargs, dict):
                raise ValueError("request kwargs must be a JSON object")
            if command == "shutdown":
                response = {
                    "id": request_id,
                    "ok": True,
                    "result": _ok("shutdown"),
                }
                print(json.dumps(response, sort_keys=True), flush=True)
                break
            result = run_state_command(state_path, command, kwargs)
            response = {"id": request_id, "ok": True, "result": result}
        except Exception as exc:
            response = {
                "id": request.get("id") if isinstance(request, dict) else None,
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        print(json.dumps(response, sort_keys=True), flush=True)


def run_state_command(
    state_path: Path,
    command: str,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    state = _read_state(state_path)
    if command == "observe":
        result = observe(state)
        _write_state(state_path, state)
    elif command == "locations":
        result = _ok("locations", final_locations=_read_locations(state))
    elif command == "snapshot":
        result = write_snapshot(
            state,
            Path(str(kwargs["output_path"])),
            str(kwargs.get("title") or ""),
            width=_positive_int(kwargs.get("render_width"), DEFAULT_RENDER_WIDTH),
            height=_positive_int(kwargs.get("render_height"), DEFAULT_RENDER_HEIGHT),
        )
    elif command == "robot_views":
        result = write_robot_views(
            state,
            Path(str(kwargs["output_dir"])),
            str(kwargs["label"]),
            focus_object_id=_optional_str(kwargs.get("focus_object_id")),
            focus_receptacle_id=_optional_str(kwargs.get("focus_receptacle_id")),
            camera_yaw_offset_deg=_float_or_zero(kwargs.get("camera_yaw_offset_deg")),
            camera_pitch_offset_deg=_float_or_zero(kwargs.get("camera_pitch_offset_deg")),
            width=_positive_int(kwargs.get("render_width"), DEFAULT_RENDER_WIDTH),
            height=_positive_int(kwargs.get("render_height"), DEFAULT_RENDER_HEIGHT),
        )
    elif command == "camera_views":
        camera_request = _load_camera_request_from_kwargs(
            kwargs,
            width=_positive_int(kwargs.get("render_width"), DEFAULT_RENDER_WIDTH),
            height=_positive_int(kwargs.get("render_height"), DEFAULT_RENDER_HEIGHT),
        )
        result = write_camera_views(
            state,
            Path(str(kwargs["output_dir"])),
            camera_request,
            width=_positive_int(kwargs.get("render_width"), DEFAULT_RENDER_WIDTH),
            height=_positive_int(kwargs.get("render_height"), DEFAULT_RENDER_HEIGHT),
        )
    elif command == "navigate_to_object":
        result = navigate_to_object(state, str(kwargs["object_id"]))
        _write_state(state_path, state)
    elif command == "navigate_to_waypoint":
        result = navigate_to_waypoint(
            state,
            _json_object_from_text(str(kwargs["waypoint_json"])),
        )
        _write_state(state_path, state)
    elif command == "navigate_to_receptacle":
        result = navigate_to_receptacle(state, str(kwargs["receptacle_id"]))
        _write_state(state_path, state)
    elif command == "frame_comparison_object":
        result = frame_comparison_object(state, str(kwargs["object_id"]))
        _write_state(state_path, state)
    elif command == "pick":
        result = pick_object(state, str(kwargs["object_id"]))
        _write_state(state_path, state)
    elif command == "open_receptacle":
        result = open_receptacle(state, str(kwargs["receptacle_id"]))
        _write_state(state_path, state)
    elif command == "close_receptacle":
        result = close_receptacle(state, str(kwargs["receptacle_id"]))
        _write_state(state_path, state)
    elif command == "place":
        result = place_object(state, str(kwargs["receptacle_id"]))
        _write_state(state_path, state)
    elif command == "place_inside":
        result = place_inside_object(state, str(kwargs["receptacle_id"]))
        _write_state(state_path, state)
    elif command == "done":
        result = done_cleanup(state, str(kwargs.get("reason") or ""))
    else:
        raise ValueError(f"unknown MolmoSpaces worker command: {command!r}")
    return result


def _load_generated_mess_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"generated mess manifest must be a JSON object: {path}")
    if manifest.get("schema") != GENERATED_MESS_MANIFEST_SCHEMA:
        raise ValueError(
            "generated mess manifest schema mismatch: "
            f"{manifest.get('schema')} != {GENERATED_MESS_MANIFEST_SCHEMA}"
        )
    return manifest


def init_state(
    *,
    state_path: Path,
    seed: int,
    scene_source: str,
    scene_index: int,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    generated_mess_count: int = 5,
    generated_mess_object_ids: tuple[str, ...] = (),
    generated_mess_manifest_path: Path | None = None,
) -> dict[str, Any]:
    from molmo_spaces.molmo_spaces_constants import get_robot_path, get_scenes_root
    from molmo_spaces.utils.lazy_loading_utils import install_scene_from_source_index
    from molmo_spaces.utils.scene_metadata_utils import get_scene_metadata

    install_scene_from_source_index(scene_source, scene_index)
    scene_xml = get_scenes_root() / scene_source / f"val_{scene_index}.xml"
    if not scene_xml.is_file():
        raise FileNotFoundError(scene_xml)

    robot_xml: Path | None = None
    if include_robot:
        robot_xml = get_robot_path(robot_name) / _robot_xml_name(robot_name)
        if not robot_xml.is_file():
            raise FileNotFoundError(robot_xml)
        model, data = _load_robot_model_data(scene_xml, robot_xml)
    else:
        model, data = _load_model_data(scene_xml)
    metadata = get_scene_metadata(scene_xml)
    if metadata is None:
        raise RuntimeError(f"missing scene metadata for {scene_xml}")

    receptacles = _collect_receptacles(model, data, metadata)
    objects = _collect_dynamic_objects(model, data, metadata)
    if generated_mess_count < 1:
        raise ValueError("generated_mess_count must be >= 1")
    generated_mess_manifest = _load_generated_mess_manifest(generated_mess_manifest_path)
    if generated_mess_manifest:
        targets = targets_from_generated_mess_manifest(
            objects,
            receptacles,
            generated_mess_manifest,
            target_count=generated_mess_count,
        )
    else:
        targets = select_generated_mess_targets(
            objects,
            receptacles,
            target_count=generated_mess_count,
            seed=seed,
            object_ids=generated_mess_object_ids or None,
        )
    if len(targets) < generated_mess_count:
        raise RuntimeError(
            f"expected at least {generated_mess_count} cleanup targets, found {len(targets)}"
        )

    state = {
        "backend": BACKEND,
        "seed": seed,
        "scene_source": scene_source,
        "scene_index": scene_index,
        "scene_xml": str(scene_xml),
        "robot_included": include_robot,
        "robot_name": robot_name if include_robot else None,
        "robot_xml": str(robot_xml) if robot_xml is not None else None,
        "python_executable": sys.executable,
        "runtime": {
            "python_version": sys.version.split()[0],
            "mujoco_version": mujoco.__version__,
            "mujoco_renderer_runtime": _mujoco_renderer_runtime_id(),
        },
        "model_stats": {
            "nbody": int(model.nbody),
            "ngeom": int(model.ngeom),
            "njnt": int(model.njnt),
            "nq": int(model.nq),
        },
        "metadata_object_count": len(metadata.get("objects", {})),
        "objects": {item["object_id"]: item for item in objects},
        "receptacles": {item["receptacle_id"]: item for item in receptacles},
        "selected_object_ids": [target["object_id"] for target in targets],
        "generated_mess_manifest": generated_mess_manifest,
        "requested_generated_mess_count": generated_mess_count,
        "generated_mess_count": len(targets),
        "qpos": [float(value) for value in data.qpos],
        "held_object_id": None,
        "current_receptacle_id": None,
        "open_receptacle_ids": [],
        "mess_placement_diagnostics": [],
        "placement_diagnostics": [],
        "tool_event_counts": {},
    }
    _seed_misplaced_objects(model, data, state, targets)
    _refresh_object_positions(model, data, state)
    state["room_outlines"] = _collect_room_outlines(model, data, state)
    if include_robot:
        initial_receptacle = state["receptacles"][_target_start_receptacle_id(state, targets[0])]
        robot_pose = _robot_pose_near_receptacle(state, initial_receptacle)
        _set_robot_pose(model, data, robot_pose)
        state["robot_pose"] = robot_pose
        state["robot_trajectory"] = [robot_pose]
        state["robot_camera_names"] = _robot_camera_names(model)
        state["robot_body_name"] = "robot_0/base"
        state["robot_control_provenance"] = "semantic_robot_base_and_head_qpos"
        state["robot_view_provenance"] = {
            "fpv": "rby1m_head_camera_target_framed",
            "chase": "rby1m_follower_camera",
            "map": "public_sim_state_report",
            "verify": "public_sim_state_report_focus_camera",
        }
    state["qpos"] = [float(value) for value in data.qpos]
    state["current_receptacle_id"] = _target_start_receptacle_id(state, targets[0])
    state["private_manifest"] = {
        "scenario_id": f"molmospaces-procthor-val-{scene_index}-{seed}",
        "success_threshold": generated_mess_success_threshold(len(targets)),
        "targets": [
            {
                "object_id": target["object_id"],
                "valid_receptacle_ids": [target["target_receptacle_id"]],
            }
            for target in targets
        ],
    }
    state["scenario_public"] = _public_scenario(state)
    _write_state(state_path, state)
    return _ok(
        "init",
        backend=BACKEND,
        scenario=state["scenario_public"],
        private_manifest=state["private_manifest"],
        generated_mess_manifest=state.get("generated_mess_manifest") or None,
        requested_generated_mess_count=state["requested_generated_mess_count"],
        generated_mess_count=state["generated_mess_count"],
        scene_xml=state["scene_xml"],
        runtime=state["runtime"],
        model_stats=state["model_stats"],
        metadata_object_count=state["metadata_object_count"],
        robot=_robot_result_payload(state, model) if include_robot else None,
    )


def observe(state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "observe")
    state["scenario_public"] = _public_scenario(state)
    return _ok(
        "observe",
        backend=BACKEND,
        scenario=state["scenario_public"],
        current_receptacle_id=state.get("current_receptacle_id"),
        held_object_id=state.get("held_object_id"),
        inventory_source="molmospaces_metadata+mujoco_state",
        metadata_object_count=state["metadata_object_count"],
    )


def write_snapshot(
    state: dict[str, Any],
    output_path: Path,
    title: str,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> dict[str, Any]:
    width, height = _render_dimensions(width, height)
    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, height=height, width=width)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = [8.5, 6.5, 0.8]
    camera.distance = 9.5
    camera.azimuth = 225
    camera.elevation = -45
    renderer.update_scene(data, camera=camera)
    frame = _normalize_renderer_frame(renderer.render())
    renderer.close()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(frame).save(output_path)
    return _ok("snapshot", path=str(output_path), title=title, shape=list(frame.shape))


def write_robot_views(
    state: dict[str, Any],
    output_dir: Path,
    label: str,
    *,
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
    camera_yaw_offset_deg: float = 0.0,
    camera_pitch_offset_deg: float = 0.0,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> dict[str, Any]:
    width, height = _render_dimensions(width, height)
    _count(state, "robot_views")
    if not state.get("robot_included"):
        return _error("robot_views", "robot_not_included")
    if focus_object_id is not None and focus_object_id not in state["objects"]:
        return _error("robot_views", "stale_reference", object_id=focus_object_id)
    if focus_receptacle_id is not None and focus_receptacle_id not in state["receptacles"]:
        return _error("robot_views", "stale_reference", receptacle_id=focus_receptacle_id)
    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    camera_adjustment = _apply_robot_view_camera_offset(
        model,
        data,
        yaw_offset_deg=camera_yaw_offset_deg,
        pitch_offset_deg=camera_pitch_offset_deg,
    )
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in label)
    fpv_path = output_dir / f"{safe_label}.fpv.png"
    chase_path = output_dir / f"{safe_label}.chase.png"
    map_path = output_dir / f"{safe_label}.map.png"
    verify_path = output_dir / f"{safe_label}.verify.png"

    focus = _focus_payload(state, focus_object_id, focus_receptacle_id)
    fpv = _render_fixed_camera(model, data, "robot_0/head_camera", width=width, height=height)
    verify_camera = _focus_camera(state, focus)
    verify = _render_free_camera(model, data, verify_camera, width=width, height=height)
    chase = _render_fixed_camera(model, data, "robot_0/camera_follower", width=width, height=height)
    camera_diagnostics = {
        "schema": "mujoco_robot_view_camera_diagnostics_v1",
        "backend": BACKEND,
        "render_resolution": {"width": width, "height": height},
        "camera_adjustment": camera_adjustment,
        "views": {
            "fpv": _fixed_camera_diagnostics(model, data, "robot_0/head_camera"),
            "chase": _fixed_camera_diagnostics(model, data, "robot_0/camera_follower"),
            "verify": _free_camera_diagnostics(verify_camera),
        },
    }
    fpv_camera = "robot_0/head_camera"
    focus["fpv_visibility"] = _focus_visibility(
        model,
        data,
        fpv_camera,
        focus,
        frame=fpv,
    )
    focus["visibility"] = _focus_visibility(
        model,
        data,
        verify_camera,
        focus,
        frame=verify,
    )
    focus = _annotate_focus_visual_grounding(focus)
    if _should_use_fpv_as_verify_focus(focus):
        verify = fpv.copy()
        fallback_visibility = dict(focus["fpv_visibility"])
        fallback_visibility["fallback_source"] = "fpv_focus_visibility"
        fallback_visibility.setdefault(
            "evidence_note",
            "Verify frame reused FPV because the closeup camera missed the focused object.",
        )
        focus["visibility"] = fallback_visibility
    color_profile = robot_view_display_color_profile()
    import numpy as np

    color_management: dict[str, dict[str, Any]] = {}
    fpv, color_management["fpv"] = apply_camera_color_profile(
        fpv,
        np=np,
        profile=color_profile,
        backend=BACKEND,
        view_id="fpv",
    )
    chase, color_management["chase"] = apply_camera_color_profile(
        chase,
        np=np,
        profile=color_profile,
        backend=BACKEND,
        view_id="chase",
    )
    verify, color_management["verify"] = apply_camera_color_profile(
        verify,
        np=np,
        profile=color_profile,
        backend=BACKEND,
        view_id="verify",
    )
    camera_control_contract = robot_mounted_head_camera_control_contract(
        backend="molmospaces-mujoco",
        fpv_source="robot_0/head_camera",
        verify_source="mujoco_focus_camera",
        chase_source="robot_0/camera_follower",
        pose_source="rby1m_robot_qpos",
        lens_source="mujoco_model_camera_defaults",
        robot_pose=dict(state.get("robot_pose") or {}),
        focus=focus,
        color_profile=color_profile,
        color_management=color_management,
    )
    camera_control_contract["camera_adjustment"] = camera_adjustment
    camera_control_contract["agent_facing_fpv"]["camera_adjustment"] = camera_adjustment
    Image.fromarray(fpv).save(fpv_path)
    Image.fromarray(chase).save(chase_path)
    verify_image = Image.fromarray(verify)
    _annotate_focus_image(verify_image, focus)
    verify_image.save(verify_path)
    _render_robot_map(state, focus=focus).save(map_path)

    return _ok(
        "robot_views",
        backend=BACKEND,
        robot_name=state.get("robot_name"),
        robot_pose=state.get("robot_pose"),
        robot_trajectory=state.get("robot_trajectory", []),
        view_variant="molmospaces-rby1m-fpv-map-chase-verify",
        view_provenance=state.get("robot_view_provenance", {}),
        camera_control_contract=camera_control_contract,
        camera_diagnostics=camera_diagnostics,
        camera_adjustment=camera_adjustment,
        color_profile=color_profile,
        color_management=color_management,
        focus=focus,
        room_outline_count=len(state.get("room_outlines", [])),
        views={
            "fpv": str(fpv_path),
            "chase": str(chase_path),
            "map": str(map_path),
            "verify": str(verify_path),
        },
        shapes={
            "fpv": list(fpv.shape),
            "chase": list(chase.shape),
            "verify": list(verify.shape),
            "map": [420, 620, 3],
        },
        render_resolution={"width": width, "height": height},
    )


def _robot_view_camera_adjustment(
    *,
    camera_yaw_offset_deg: float = 0.0,
    camera_pitch_offset_deg: float = 0.0,
    applied_joints: list[str] | None = None,
    unavailable_reason: str | None = None,
) -> dict[str, Any]:
    yaw = round(float(camera_yaw_offset_deg), 3)
    pitch = round(float(camera_pitch_offset_deg), 3)
    requested = bool(yaw or pitch)
    applied_joints = list(applied_joints or [])
    applied = requested and bool(applied_joints) and unavailable_reason is None
    if not requested:
        apply_status = "not_requested"
    elif applied:
        apply_status = "robot_head_joints_render_only"
    elif unavailable_reason:
        apply_status = "unavailable"
    else:
        apply_status = "no_matching_mujoco_head_joints"
    return {
        "schema": "robot_view_camera_adjustment_v1",
        "yaw_delta_deg": yaw,
        "pitch_delta_deg": pitch,
        "requested": requested,
        "applied": applied,
        "apply_status": apply_status,
        "applied_joints": applied_joints,
        "unavailable_reason": unavailable_reason,
        "evidence_note": (
            "Camera offset requests are applied to robot head joints for this render "
            "without persisting the adjusted qpos to worker state."
        ),
    }


def write_camera_views(
    state: dict[str, Any],
    output_dir: Path,
    camera_request: dict[str, Any] | list[dict[str, Any]],
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> dict[str, Any]:
    _count(state, "camera_views")
    camera_request = normalize_camera_control_request(camera_request, width=width, height=height)
    resolution = camera_request["render_resolution"]
    width, height = _render_dimensions(resolution["width"], resolution["height"])
    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)
    return _render_camera_views_with_model_data(
        model,
        data,
        state=state,
        output_dir=output_dir,
        camera_request=camera_request,
        width=width,
        height=height,
    )


def _render_camera_views_with_model_data(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    *,
    state: dict[str, Any],
    output_dir: Path,
    camera_request: dict[str, Any] | list[dict[str, Any]],
    width: int,
    height: int,
) -> dict[str, Any]:
    camera_request = normalize_camera_control_request(camera_request, width=width, height=height)
    resolution = camera_request["render_resolution"]
    width, height = _render_dimensions(resolution["width"], resolution["height"])
    lens = camera_request.get("lens") if isinstance(camera_request.get("lens"), dict) else {}
    previous_fovy = float(model.vis.global_.fovy)
    model.vis.global_.fovy = float(lens.get("vertical_fov_deg", previous_fovy))
    output_dir.mkdir(parents=True, exist_ok=True)
    color_profile = camera_request.get("color_profile") or {}

    try:
        saved: dict[str, str] = {}
        shapes: dict[str, list[int]] = {}
        color_diagnostics: dict[str, dict[str, Any]] = {}
        views: list[dict[str, Any]] = []
        for index, raw_spec in enumerate(camera_request.get("views") or [], start=1):
            spec = _camera_view_spec(raw_spec, index=index)
            camera = _camera_from_view_spec(state, spec)
            frame = _render_free_camera(model, data, camera, width=width, height=height)
            import numpy as np

            frame, color_diagnostic = apply_camera_color_profile(
                frame,
                np=np,
                profile=color_profile,
                backend="molmospaces-mujoco",
                view_id=str(spec["view_id"]),
            )
            output_path = output_dir / f"{spec['view_id']}.png"
            Image.fromarray(frame).save(output_path)
            saved[str(spec["view_id"])] = str(output_path)
            shapes[str(spec["view_id"])] = list(frame.shape)
            color_diagnostics[str(spec["view_id"])] = color_diagnostic
            views.append(
                {
                    **spec,
                    "image_path": str(output_path),
                    "shape": list(frame.shape),
                }
            )
    finally:
        model.vis.global_.fovy = previous_fovy
    return _ok(
        "camera_views",
        backend=BACKEND,
        camera_control_api=camera_request.get("api_name") or CAMERA_CONTROL_API_NAME,
        camera_request_schema=camera_request.get("schema"),
        calibration_status=camera_request.get("calibration_status"),
        lighting_profile=camera_request.get("lighting_profile") or {},
        color_profile=color_profile,
        color_management=color_diagnostics,
        lens=camera_request.get("lens") or {},
        view_variant=_camera_request_variant(camera_request),
        visual_artifact_provenance=_camera_request_provenance(camera_request),
        views=views,
        images=saved,
        shapes=shapes,
        render_resolution={"width": width, "height": height},
    )


def navigate_to_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "navigate_to_receptacle")
    return _navigate_to_receptacle(state, receptacle_id, tool="navigate_to_receptacle")


def _navigate_to_receptacle(
    state: dict[str, Any],
    receptacle_id: str,
    *,
    tool: str,
) -> dict[str, Any]:
    if receptacle_id not in state["receptacles"]:
        return _error(tool, "stale_reference", receptacle_id=receptacle_id)
    previous = state.get("current_receptacle_id")
    state["current_receptacle_id"] = receptacle_id
    robot_pose = None
    held_object_pose = None
    qpos_changed = False
    state_mutation = "agent_pose_semantic"
    if state.get("robot_included"):
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        robot_pose = _robot_pose_near_receptacle(state, state["receptacles"][receptacle_id])
        _set_robot_pose(model, data, robot_pose)
        state["robot_pose"] = robot_pose
        state.setdefault("robot_trajectory", []).append(robot_pose)
        held_object_pose = _sync_held_object_to_robot_pose(model, data, state)
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        state["qpos"] = [float(value) for value in data.qpos]
        qpos_changed = True
        state_mutation = _robot_pose_state_mutation(held_object_pose is not None)
    return _ok(
        tool,
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        receptacle_id=receptacle_id,
        previous_receptacle_id=previous,
        state_mutation=state_mutation,
        held_object_pose=held_object_pose,
        robot_name=state.get("robot_name"),
        robot_pose=robot_pose,
        robot_control_provenance=state.get("robot_control_provenance"),
        qpos_changed=qpos_changed,
        backend=BACKEND,
    )


def navigate_to_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    _count(state, "navigate_to_object")
    if object_id not in state["objects"]:
        return _error("navigate_to_object", "stale_reference", object_id=object_id)
    if state.get("held_object_id") == object_id:
        return _error("navigate_to_object", "object_already_held", object_id=object_id)
    locations = _read_locations(state)
    source_receptacle_id = locations.get(object_id)
    if not source_receptacle_id or source_receptacle_id == HELD_LOCATION_ID:
        return _error("navigate_to_object", "object_not_at_public_location", object_id=object_id)
    previous = state.get("current_receptacle_id")
    state["current_receptacle_id"] = source_receptacle_id
    robot_pose = None
    qpos_changed = False
    state_mutation = "agent_pose_semantic"
    if state.get("robot_included"):
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        robot_pose = _robot_pose_near_object(
            state,
            state["objects"][object_id],
            source_receptacle_id=source_receptacle_id,
        )
        _set_robot_pose(model, data, robot_pose)
        mujoco.mj_forward(model, data)
        state["qpos"] = [float(value) for value in data.qpos]
        state["robot_pose"] = robot_pose
        state.setdefault("robot_trajectory", []).append(robot_pose)
        qpos_changed = True
        state_mutation = "robot_base_qpos"
    return _ok(
        "navigate_to_object",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        source_receptacle_id=source_receptacle_id,
        previous_receptacle_id=previous,
        location_id=source_receptacle_id,
        state_mutation=state_mutation,
        robot_name=state.get("robot_name"),
        robot_pose=robot_pose,
        robot_control_provenance=state.get("robot_control_provenance"),
        qpos_changed=qpos_changed,
        backend=BACKEND,
    )


def navigate_to_waypoint(state: dict[str, Any], waypoint: dict[str, Any]) -> dict[str, Any]:
    _count(state, "navigate_to_waypoint")
    waypoint_id = str(waypoint.get("waypoint_id") or "")
    room_id = str(waypoint.get("room_id") or "")
    previous = state.get("current_waypoint_id")
    state["current_waypoint_id"] = waypoint_id
    robot_pose = None
    held_object_pose = None
    qpos_changed = False
    state_mutation = "agent_pose_semantic"
    if state.get("robot_included"):
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        mujoco.mj_forward(model, data)
        target = _waypoint_target_position(state, waypoint)
        robot_pose = _robot_pose_for_waypoint(state, waypoint, target)
        _set_robot_pose(model, data, robot_pose)
        state["robot_pose"] = robot_pose
        state.setdefault("robot_trajectory", []).append(robot_pose)
        held_object_pose = _sync_held_object_to_robot_pose(model, data, state)
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        state["qpos"] = [float(value) for value in data.qpos]
        qpos_changed = True
        state_mutation = _robot_pose_state_mutation(held_object_pose is not None)
    return _ok(
        "navigate_to_waypoint",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        waypoint_id=waypoint_id,
        room_id=room_id,
        previous_waypoint_id=previous,
        state_mutation=state_mutation,
        held_object_pose=held_object_pose,
        robot_name=state.get("robot_name"),
        robot_pose=robot_pose,
        robot_control_provenance=state.get("robot_control_provenance"),
        qpos_changed=qpos_changed,
        backend=BACKEND,
    )


def frame_comparison_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    _count(state, "frame_comparison_object")
    if object_id not in state["objects"]:
        return _error("frame_comparison_object", "stale_reference", object_id=object_id)
    if not state.get("robot_included"):
        return _error("frame_comparison_object", "robot_not_included")
    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)
    robot_pose = _robot_pose_near_object(
        state,
        state["objects"][object_id],
        source_receptacle_id=None,
    )
    robot_pose["pose_source"] = "roboclaws_comparison_object_pose"
    _set_robot_pose(model, data, robot_pose)
    mujoco.mj_forward(model, data)
    state["qpos"] = [float(value) for value in data.qpos]
    state["robot_pose"] = robot_pose
    state.setdefault("robot_trajectory", []).append(robot_pose)
    return _ok(
        "frame_comparison_object",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        state_mutation="robot_base_qpos",
        robot_name=state.get("robot_name"),
        robot_pose=robot_pose,
        robot_control_provenance=state.get("robot_control_provenance"),
        qpos_changed=True,
        backend=BACKEND,
    )


def pick_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    _count(state, "pick")
    if object_id not in state["objects"]:
        return _error("pick", "stale_reference", object_id=object_id)
    if state.get("held_object_id") is not None:
        return _error("pick", "already_holding", held_object_id=state["held_object_id"])
    locations = _read_locations(state)
    qpos_changed = False
    state_mutation = "held_state_only"
    if state.get("robot_included"):
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        target_position = _held_object_position(state)
        _set_free_body_position(
            model, data, state["objects"][object_id]["body_name"], target_position
        )
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        state["qpos"] = [float(value) for value in data.qpos]
        qpos_changed = True
        state_mutation = "mujoco_freejoint_qpos_held_pose"
    state["held_object_id"] = object_id
    state["objects"][object_id]["contained_in"] = None
    state["objects"][object_id]["location_relation"] = "held"
    return _ok(
        "pick",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        previous_location_id=locations.get(object_id),
        location_id=HELD_LOCATION_ID,
        state_mutation=state_mutation,
        qpos_changed=qpos_changed,
        backend=BACKEND,
    )


def place_object(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "place")
    return _place_object_at_receptacle(state, receptacle_id, tool="place", relation="on")


def place_inside_object(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "place_inside")
    return _place_object_at_receptacle(
        state,
        receptacle_id,
        tool="place_inside",
        relation="inside",
    )


def _place_object_at_receptacle(
    state: dict[str, Any],
    receptacle_id: str,
    *,
    tool: str,
    relation: str,
) -> dict[str, Any]:
    if receptacle_id not in state["receptacles"]:
        return _error(tool, "stale_reference", receptacle_id=receptacle_id)
    object_id = state.get("held_object_id")
    if object_id is None:
        return _error(tool, "not_holding")
    receptacle = state["receptacles"][receptacle_id]
    if (
        relation == "inside"
        and _receptacle_requires_open(receptacle)
        and receptacle_id not in set(state.get("open_receptacle_ids", []))
    ):
        return _error(tool, "receptacle_closed", receptacle_id=receptacle_id)

    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    obj = state["objects"][object_id]
    placement_resolution = _resolve_placement(
        model,
        data,
        state=state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        index=state["selected_object_ids"].index(object_id),
        relation=relation,
    )
    target_position = placement_resolution["position"]
    _set_free_body_position(model, data, obj["body_name"], target_position)
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)
    diagnostic = _placement_diagnostic(
        state=state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        relation=relation,
        requested_position=target_position,
        source="cleanup_place",
        placement_resolution=placement_resolution,
    )
    state.setdefault("placement_diagnostics", []).append(diagnostic)

    state["qpos"] = [float(value) for value in data.qpos]
    state["held_object_id"] = None
    state["current_receptacle_id"] = receptacle_id
    state["objects"][object_id]["contained_in"] = receptacle_id if relation == "inside" else None
    state["objects"][object_id]["location_relation"] = relation
    final_locations = _read_locations(state)
    return _ok(
        tool,
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        receptacle_id=receptacle_id,
        location_id=final_locations.get(object_id),
        contained_in=receptacle_id if relation == "inside" else None,
        location_relation=relation,
        placement_diagnostic=diagnostic,
        placement_support_status=diagnostic["support_status"],
        mujoco_body_name=obj["body_name"],
        qpos_changed=True,
        state_mutation="mujoco_freejoint_qpos",
        backend=BACKEND,
    )


def open_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "open_receptacle")
    if receptacle_id not in state["receptacles"]:
        return _error("open_receptacle", "stale_reference", receptacle_id=receptacle_id)

    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    receptacle = state["receptacles"][receptacle_id]
    joints = _openable_receptacle_joints(model, receptacle["body_name"])
    for joint in joints:
        _set_joint_qpos(model, data, joint["joint_name"], joint["open_value"])
    robot_pose = None
    robot_pose_changed = False
    if state.get("robot_included") and joints:
        robot_pose = _robot_pose_for_open_receptacle(state, receptacle)
        _set_robot_pose(model, data, robot_pose)
        state["robot_pose"] = robot_pose
        state.setdefault("robot_trajectory", []).append(robot_pose)
        held_object_pose = _sync_held_object_to_robot_pose(model, data, state)
        robot_pose_changed = True
    else:
        held_object_pose = None
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)
    state["qpos"] = [float(value) for value in data.qpos]
    open_ids = set(state.get("open_receptacle_ids", []))
    if joints:
        open_ids.add(receptacle_id)
    state["open_receptacle_ids"] = sorted(open_ids)
    return _ok(
        "open_receptacle",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        receptacle_id=receptacle_id,
        opened=bool(joints),
        open_joints=joints,
        robot_pose=robot_pose,
        held_object_pose=held_object_pose,
        qpos_changed=bool(joints) or robot_pose_changed,
        state_mutation=_open_receptacle_state_mutation(
            bool(joints),
            robot_pose_changed,
            held_object_pose is not None,
        ),
        backend=BACKEND,
    )


def close_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "close_receptacle")
    if receptacle_id not in state["receptacles"]:
        return _error("close_receptacle", "stale_reference", receptacle_id=receptacle_id)

    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    receptacle = state["receptacles"][receptacle_id]
    joints = _openable_receptacle_joints(model, receptacle["body_name"])
    closed_joints = []
    for joint in joints:
        _set_joint_qpos(model, data, joint["joint_name"], joint["close_value"])
        closed_joints.append(joint)
    held_object_pose = _sync_held_object_to_robot_pose(model, data, state)
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)
    state["qpos"] = [float(value) for value in data.qpos]
    open_ids = set(state.get("open_receptacle_ids", []))
    was_open = receptacle_id in open_ids
    open_ids.discard(receptacle_id)
    state["open_receptacle_ids"] = sorted(open_ids)
    return _ok(
        "close_receptacle",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        receptacle_id=receptacle_id,
        closed=was_open or bool(closed_joints),
        closed_joints=closed_joints,
        held_object_pose=held_object_pose,
        qpos_changed=bool(closed_joints) or held_object_pose is not None,
        state_mutation=_close_receptacle_state_mutation(
            bool(closed_joints),
            held_object_pose is not None,
        ),
        backend=BACKEND,
    )


def _robot_pose_state_mutation(held_object_changed: bool) -> str:
    parts = ["robot_base_qpos"]
    if held_object_changed:
        parts.append("held_object_freejoint_qpos")
    return "+".join(parts)


def _open_receptacle_state_mutation(
    joints_changed: bool,
    robot_pose_changed: bool,
    held_object_changed: bool,
) -> str:
    parts = []
    if joints_changed:
        parts.append("mujoco_receptacle_joint_qpos")
    if robot_pose_changed:
        parts.append("robot_base_qpos")
    if held_object_changed:
        parts.append("held_object_freejoint_qpos")
    return "+".join(parts) if parts else "no_openable_joint"


def _close_receptacle_state_mutation(
    joints_changed: bool,
    held_object_changed: bool,
) -> str:
    parts = []
    if joints_changed:
        parts.append("mujoco_receptacle_joint_qpos")
    if held_object_changed:
        parts.append("held_object_freejoint_qpos")
    return "+".join(parts) if parts else "no_openable_joint"


def done_cleanup(state: dict[str, Any], reason: str) -> dict[str, Any]:
    _count(state, "done")
    final_locations = _read_locations(state)
    score = _score(final_locations, state["private_manifest"])
    return _ok(
        "done",
        reason=reason,
        cleanup_status=score["status"],
        score=score,
        final_locations=final_locations,
        final_containment=_read_containment(state),
        tool_event_counts=state["tool_event_counts"],
        backend=BACKEND,
    )


def _collect_dynamic_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    items = []
    for name, info in metadata.get("objects", {}).items():
        body_name = _primary_body_name(info, fallback=name)
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        if body_id < 0 or int(model.body_jntnum[body_id]) == 0:
            continue
        joint_id = int(model.body_jntadr[body_id])
        if int(model.jnt_type[joint_id]) != int(mujoco.mjtJoint.mjJNT_FREE):
            continue
        category = str(info.get("category", "Object"))
        items.append(
            {
                "object_id": name,
                "name": _friendly_name(category, info.get("object_id", name)),
                "category": category,
                "location_id": "",
                "pickupable": True,
                "body_name": body_name,
                "upstream_object_id": info.get("object_id", name),
                "position": _xyz(data.xpos[body_id]),
            }
        )
    return sorted(items, key=lambda item: (item["category"], item["object_id"]))


def _collect_receptacles(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    wanted = {
        "Sink",
        "ShelvingUnit",
        "Desk",
        "Fridge",
        "TVStand",
        "Bed",
        "Sofa",
        "DiningTable",
        "CounterTop",
    }
    items = []
    for name, info in metadata.get("objects", {}).items():
        category = str(info.get("category", ""))
        if category not in wanted:
            continue
        body_name = _primary_body_name(info, fallback=name)
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        if body_id < 0:
            continue
        support_surfaces = _receptacle_support_surfaces(model, data, body_name)
        items.append(
            {
                "receptacle_id": name,
                "name": _friendly_name(category, info.get("object_id", name)),
                "category": category,
                "room_area": f"room_{info.get('room_id', 'unknown')}",
                "kind": "receptacle",
                "body_name": body_name,
                "upstream_object_id": info.get("object_id", name),
                "position": _xyz(data.xpos[body_id]),
                "support_surfaces": support_surfaces,
                "support_top_z": _support_top_z(support_surfaces),
            }
        )
    return sorted(items, key=lambda item: (item["category"], item["receptacle_id"]))


def _seed_misplaced_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
    targets: list[dict[str, Any]],
) -> None:
    manifest_targets = _manifest_target_by_object_id(state)
    target_receptacle_ids = {
        _target_receptacle_id(target, manifest_targets.get(str(target["object_id"])))
        for target in targets
    }
    wrong_pool = [
        item
        for item in state["receptacles"].values()
        if item["receptacle_id"] not in target_receptacle_ids
        and not _receptacle_requires_open(item)
    ]
    if not wrong_pool:
        wrong_pool = [
            item
            for item in state["receptacles"].values()
            if item["receptacle_id"] not in target_receptacle_ids
        ]
    if not wrong_pool:
        wrong_pool = list(state["receptacles"].values())
    for index, target in enumerate(targets):
        manifest_target = manifest_targets.get(str(target["object_id"]))
        target_receptacle_id = _target_receptacle_id(target, manifest_target)
        placement_index = _target_placement_index(index, manifest_target)
        wrong = _target_start_receptacle(state, target, wrong_pool, index, manifest_target)
        state["objects"][target["object_id"]]["target_receptacle_id"] = target_receptacle_id
        state["objects"][target["object_id"]]["seeded_start_receptacle_id"] = wrong["receptacle_id"]
        relation = _target_relation(wrong, manifest_target)
        state["objects"][target["object_id"]]["contained_in"] = (
            wrong["receptacle_id"] if relation == "inside" else None
        )
        state["objects"][target["object_id"]]["location_relation"] = relation
        placement_resolution = _resolve_placement(
            model,
            data,
            state=state,
            object_id=target["object_id"],
            receptacle_id=wrong["receptacle_id"],
            index=placement_index,
            relation=relation,
        )
        placement_position = placement_resolution["position"]
        _set_free_body_position(
            model,
            data,
            target["body_name"],
            placement_position,
        )
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        diagnostic = _placement_diagnostic(
            state=state,
            object_id=target["object_id"],
            receptacle_id=wrong["receptacle_id"],
            relation=relation,
            requested_position=placement_position,
            source="canonical_mess_manifest" if manifest_target else "mess_seed",
            placement_index=placement_index,
            placement_resolution=placement_resolution,
        )
        state.setdefault("mess_placement_diagnostics", []).append(diagnostic)
    mujoco.mj_forward(model, data)


def _manifest_target_by_object_id(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = state.get("generated_mess_manifest")
    if not isinstance(manifest, dict):
        return {}
    targets: dict[str, dict[str, Any]] = {}
    for raw_target in manifest.get("targets", []):
        if not isinstance(raw_target, dict):
            continue
        object_id = str(raw_target.get("object_id") or "")
        if object_id:
            targets[object_id] = dict(raw_target)
    return targets


def _target_receptacle_id(
    target: dict[str, Any],
    manifest_target: dict[str, Any] | None,
) -> str:
    if manifest_target:
        valid_ids = [
            str(item)
            for item in (
                manifest_target.get("valid_receptacle_ids")
                or [manifest_target.get("target_receptacle_id")]
            )
            if str(item)
        ]
        if valid_ids:
            return valid_ids[0]
    return str(target["target_receptacle_id"])


def _target_start_receptacle(
    state: dict[str, Any],
    target: dict[str, Any],
    wrong_pool: list[dict[str, Any]],
    index: int,
    manifest_target: dict[str, Any] | None,
) -> dict[str, Any]:
    if manifest_target:
        start_receptacle_id = str(manifest_target.get("start_receptacle_id") or "")
        if start_receptacle_id:
            receptacle = state["receptacles"].get(start_receptacle_id)
            if receptacle is None:
                raise ValueError(
                    "generated mess manifest start receptacle id is unavailable: "
                    f"{target['object_id']} -> {start_receptacle_id}"
                )
            return receptacle
    wrong = wrong_pool[index % len(wrong_pool)]
    if wrong["receptacle_id"] == target["target_receptacle_id"]:
        wrong = wrong_pool[(index + 1) % len(wrong_pool)]
    return wrong


def _target_start_receptacle_id(state: dict[str, Any], target: dict[str, Any]) -> str:
    manifest_target = _manifest_target_by_object_id(state).get(str(target["object_id"]))
    if manifest_target:
        start_receptacle_id = str(manifest_target.get("start_receptacle_id") or "")
        if start_receptacle_id:
            return start_receptacle_id
    return _first_wrong_receptacle(state, target)


def _target_relation(
    receptacle: dict[str, Any],
    manifest_target: dict[str, Any] | None,
) -> str:
    if manifest_target:
        relation = str(manifest_target.get("relation") or "")
        if relation in {"on", "inside"}:
            return relation
    return "inside" if _receptacle_prefers_inside(receptacle) else "on"


def _target_placement_index(index: int, manifest_target: dict[str, Any] | None) -> int:
    if not manifest_target:
        return index
    try:
        return int(manifest_target.get("placement_index"))
    except (TypeError, ValueError):
        return index


def _public_scenario(state: dict[str, Any]) -> dict[str, Any]:
    locations = _read_locations(state)
    selected_ids = set(state["selected_object_ids"])
    selected = []
    distractors = []
    for obj in state["objects"].values():
        public = {
            "object_id": obj["object_id"],
            "name": obj["name"],
            "category": obj["category"],
            "location_id": locations.get(obj["object_id"], ""),
            "pickupable": obj.get("pickupable", True),
            "upstream_object_id": obj.get("upstream_object_id"),
            "contained_in": obj.get("contained_in"),
            "location_relation": obj.get("location_relation", "on"),
        }
        if obj["object_id"] in selected_ids:
            selected.append(public)
        elif obj["category"] not in {"Cup", "Mug", "Plate", "Bowl", "Book", "Apple"}:
            distractors.append(public)
    objects = selected + distractors[:8]
    return {
        "scenario_id": state["private_manifest"]["scenario_id"]
        if "private_manifest" in state
        else f"molmospaces-procthor-val-{state['scene_index']}-{state['seed']}",
        "task": "Clean up this real MolmoSpaces room by putting misplaced objects away.",
        "seed": state["seed"],
        "backend": BACKEND,
        "scene_source": state["scene_source"],
        "scene_index": state["scene_index"],
        "scene_xml": state["scene_xml"],
        "inventory_source": "molmospaces_metadata+mujoco_state",
        "metadata_object_count": state["metadata_object_count"],
        "objects": objects,
        "receptacles": [
            {
                "receptacle_id": item["receptacle_id"],
                "name": item["name"],
                "category": item["category"],
                "room_area": item["room_area"],
                "kind": item["kind"],
                "upstream_object_id": item["upstream_object_id"],
            }
            for item in state["receptacles"].values()
        ],
    }


def _read_locations(state: dict[str, Any]) -> dict[str, str]:
    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    receptacles = list(state["receptacles"].values())
    locations = {}
    for object_id in state["selected_object_ids"]:
        if object_id == state.get("held_object_id"):
            locations[object_id] = HELD_LOCATION_ID
            continue
        obj = state["objects"][object_id]
        if obj.get("contained_in"):
            locations[object_id] = str(obj["contained_in"])
            continue
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, obj["body_name"])
        if body_id < 0:
            continue
        locations[object_id] = _nearest_receptacle(_xyz(data.xpos[body_id]), receptacles)
    return locations


def _read_containment(state: dict[str, Any]) -> dict[str, dict[str, str]]:
    containment = {}
    for object_id in state.get("selected_object_ids", []):
        obj = state["objects"][object_id]
        if obj.get("contained_in") or obj.get("location_relation"):
            containment[object_id] = {
                "contained_in": obj.get("contained_in"),
                "location_relation": obj.get("location_relation", "on"),
            }
    return containment


def _score(final_locations: dict[str, str], manifest: dict[str, Any]) -> dict[str, Any]:
    restored = []
    missed = []
    object_results = []
    for target in manifest["targets"]:
        object_id = target["object_id"]
        actual = final_locations.get(object_id)
        is_restored = actual in set(target["valid_receptacle_ids"])
        if is_restored:
            restored.append(object_id)
        else:
            missed.append(object_id)
        object_results.append(
            {
                "object_id": object_id,
                "actual_location_id": actual,
                "restored": is_restored,
            }
        )
    status = "success" if len(restored) >= manifest["success_threshold"] else "failed"
    if status == "failed" and restored:
        status = "partial_success"
    return {
        "status": status,
        "restored_count": len(restored),
        "total_targets": len(manifest["targets"]),
        "success_threshold": manifest["success_threshold"],
        "restored_object_ids": restored,
        "missed_object_ids": missed,
        "object_results": object_results,
    }


def _nearest_receptacle(position: list[float], receptacles: list[dict[str, Any]]) -> str:
    return min(
        receptacles,
        key=lambda item: math.dist(position[:2], item["position"][:2]),
    )["receptacle_id"]


def _first_wrong_receptacle(state: dict[str, Any], target: dict[str, Any]) -> str:
    for receptacle_id in state["receptacles"]:
        if receptacle_id != target["target_receptacle_id"]:
            return receptacle_id
    return target["target_receptacle_id"]


def _set_free_body_position(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_name: str,
    position: list[float],
) -> None:
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if body_id < 0:
        raise ValueError(f"unknown body: {body_name}")
    joint_id = int(model.body_jntadr[body_id])
    if joint_id < 0 or int(model.jnt_type[joint_id]) != int(mujoco.mjtJoint.mjJNT_FREE):
        raise ValueError(f"body does not have a free joint: {body_name}")
    qposadr = int(model.jnt_qposadr[joint_id])
    data.qpos[qposadr : qposadr + 3] = position


def _refresh_object_positions(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> None:
    for obj in state.get("objects", {}).values():
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, obj["body_name"])
        if body_id >= 0:
            obj["position"] = _xyz(data.xpos[body_id])


def _refresh_runtime_render_state(state: dict[str, Any]) -> None:
    try:
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        mujoco.mj_forward(model, data)
    except Exception as exc:
        state["runtime_render_state"] = {
            "schema": "molmospaces_runtime_render_state_v1",
            "status": "unavailable",
            "unavailable_reason": f"{type(exc).__name__}: {exc}",
        }
        return
    state["runtime_render_state"] = _runtime_render_state(model, data, state)


def _runtime_render_state(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> dict[str, Any]:
    objects = {}
    articulated_count = 0
    try:
        for object_id, obj in sorted((state.get("objects") or {}).items()):
            if not isinstance(obj, dict):
                continue
            body_name = str(obj.get("body_name") or "")
            body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
            if body_id < 0:
                continue
            joints = _runtime_subtree_joints(
                model,
                data,
                body_name,
                exclude_root_freejoint=True,
            )
            if joints:
                articulated_count += 1
            objects[str(object_id)] = {
                "object_key": str(object_id),
                "category": obj.get("category") or "",
                "body_name": body_name,
                "upstream_object_id": obj.get("upstream_object_id") or obj.get("object_id") or "",
                "position": _xyz(data.xpos[body_id]),
                "subtree_joint_count": len(joints),
                "articulation_status": "articulated" if joints else "rigid_or_free_body",
                "articulation_joints": joints,
            }
    except Exception as exc:
        return {
            "schema": "molmospaces_runtime_render_state_v1",
            "status": "unavailable",
            "unavailable_reason": f"{type(exc).__name__}: {exc}",
        }
    return {
        "schema": "molmospaces_runtime_render_state_v1",
        "status": "computed",
        "source": "mujoco_live_model_data_qpos",
        "qpos_length": len(state.get("qpos") or []),
        "object_count": len(objects),
        "articulated_object_count": articulated_count,
        "objects": objects,
    }


def _runtime_subtree_joints(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_name: str,
    *,
    exclude_root_freejoint: bool,
) -> list[dict[str, Any]]:
    root_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if root_body_id < 0:
        return []
    joints = []
    for body_id in _subtree_body_ids(model, body_name):
        joint_count = int(model.body_jntnum[body_id])
        if joint_count <= 0:
            continue
        body_joint_start = int(model.body_jntadr[body_id])
        for offset in range(joint_count):
            joint_id = body_joint_start + offset
            joint_type = int(model.jnt_type[joint_id])
            if (
                exclude_root_freejoint
                and body_id == root_body_id
                and offset == 0
                and joint_type == int(mujoco.mjtJoint.mjJNT_FREE)
            ):
                continue
            joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
            if not joint_name:
                continue
            qposadr = int(model.jnt_qposadr[joint_id])
            qpos_width = _joint_qpos_width(model, joint_id)
            joints.append(
                {
                    "joint_name": joint_name,
                    "body_name": mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id) or "",
                    "joint_type": _joint_type_name(model, joint_id),
                    "qposadr": qposadr,
                    "qpos": [
                        round(float(value), 6)
                        for value in data.qpos[qposadr : qposadr + qpos_width]
                    ],
                    "range": [
                        round(float(model.jnt_range[joint_id][0]), 6),
                        round(float(model.jnt_range[joint_id][1]), 6),
                    ]
                    if bool(model.jnt_limited[joint_id])
                    else [],
                }
            )
    return joints


def _joint_qpos_width(model: mujoco.MjModel, joint_id: int) -> int:
    joint_type = int(model.jnt_type[joint_id])
    if joint_type == int(mujoco.mjtJoint.mjJNT_FREE):
        return 7
    if joint_type == int(mujoco.mjtJoint.mjJNT_BALL):
        return 4
    return 1


def _joint_type_name(model: mujoco.MjModel, joint_id: int) -> str:
    joint_type = int(model.jnt_type[joint_id])
    if joint_type == int(mujoco.mjtJoint.mjJNT_FREE):
        return "free"
    if joint_type == int(mujoco.mjtJoint.mjJNT_BALL):
        return "ball"
    if joint_type == int(mujoco.mjtJoint.mjJNT_SLIDE):
        return "slide"
    if joint_type == int(mujoco.mjtJoint.mjJNT_HINGE):
        return "hinge"
    return str(joint_type)


def _resolve_placement(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    *,
    state: dict[str, Any],
    object_id: str,
    receptacle_id: str,
    index: int,
    relation: str,
) -> dict[str, Any]:
    """Return a nonblocking placement pose plus support-quality evidence."""
    obj = state["objects"][object_id]
    receptacle = state["receptacles"][receptacle_id]
    object_category = obj.get("category")
    if relation == "on":
        direct = _direct_support_placement(
            model,
            data,
            state,
            obj,
            receptacle,
            index=index,
        )
        if direct is not None:
            return direct
    position = _placement_position(
        receptacle,
        index=index,
        relation=relation,
        object_category=object_category,
    )
    support_status = (
        "semantic_contained_in_receptacle" if relation == "inside" else "degraded_elevated"
    )
    contact_proof = (
        "semantic_containment" if relation == "inside" else "degraded_no_direct_support_surface"
    )
    return {
        "position": position,
        "support_status": support_status,
        "contact_proof": contact_proof,
        "resolution_source": "category_fallback",
        "candidate_count": 0,
        "degraded": relation == "on",
    }


def _direct_support_placement(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
    obj: dict[str, Any],
    receptacle: dict[str, Any],
    *,
    index: int,
) -> dict[str, Any] | None:
    surfaces = list(receptacle.get("support_surfaces") or [])
    if not surfaces:
        surfaces = _receptacle_support_surfaces(model, data, str(receptacle.get("body_name") or ""))
    surfaces = [surface for surface in surfaces if float(surface.get("area_m2") or 0.0) > 0.0]
    if not surfaces:
        return None
    footprint = _object_footprint_half_extents(model, data, obj)
    bottom_offset = _object_bottom_offset(model, data, obj)
    clearance = _direct_support_clearance(obj, receptacle)
    candidate_count = 0
    for surface in sorted(
        surfaces,
        key=lambda item: (
            float(item.get("area_m2") or 0.0),
            float(item.get("top_z") or 0.0),
        ),
        reverse=True,
    ):
        for candidate in _surface_candidate_positions(
            surface,
            footprint=footprint,
            bottom_offset=bottom_offset,
            clearance=clearance,
            index=index,
        ):
            candidate_count += 1
            if not _candidate_has_direct_support(candidate, surface, footprint):
                continue
            if not _candidate_is_clear_of_dynamic_objects(
                model,
                data,
                state,
                obj,
                candidate,
                footprint=footprint,
                bottom_offset=bottom_offset,
            ):
                continue
            return {
                "position": candidate,
                "support_status": "direct_support",
                "contact_proof": "geometry_direct_support",
                "resolution_source": "receptacle_support_surface",
                "candidate_count": candidate_count,
                "degraded": False,
                "support_surface": surface,
                "object_bottom_offset_m": round(float(bottom_offset), 6),
                "support_clearance_m": round(float(clearance), 6),
                "object_footprint_half_extents_m": [
                    round(float(footprint[0]), 6),
                    round(float(footprint[1]), 6),
                ],
            }
    return {
        "position": _elevated_position_over_surface(
            surfaces[0],
            bottom_offset=bottom_offset,
        ),
        "support_status": "degraded_elevated",
        "contact_proof": "degraded_no_candidate_inside_support_surface",
        "resolution_source": "support_surface_elevated_fallback",
        "candidate_count": candidate_count,
        "degraded": True,
        "support_surface": surfaces[0],
        "object_bottom_offset_m": round(float(bottom_offset), 6),
        "support_clearance_m": round(float(clearance), 6),
        "object_footprint_half_extents_m": [
            round(float(footprint[0]), 6),
            round(float(footprint[1]), 6),
        ],
    }


def _surface_candidate_positions(
    surface: dict[str, Any],
    *,
    footprint: tuple[float, float],
    bottom_offset: float,
    clearance: float,
    index: int,
) -> list[list[float]]:
    center = surface["center"]
    half_extents = surface["half_extents"]
    margin_x = float(footprint[0]) + 0.04
    margin_y = float(footprint[1]) + 0.04
    available_x = max(float(half_extents[0]) - margin_x, 0.0)
    available_y = max(float(half_extents[1]) - margin_y, 0.0)
    slot_x = min(available_x * 0.55, 0.28)
    slot_y = min(available_y * 0.55, 0.28)
    offsets = [
        (0.0, 0.0),
        (-slot_x, 0.0),
        (slot_x, 0.0),
        (0.0, -slot_y),
        (0.0, slot_y),
        (-slot_x, -slot_y),
        (slot_x, -slot_y),
        (-slot_x, slot_y),
        (slot_x, slot_y),
    ]
    if len(offsets) > 1:
        shift = index % len(offsets)
        offsets = offsets[shift:] + offsets[:shift]
    z = float(surface["top_z"]) + float(bottom_offset) + float(clearance)
    return [
        [
            round(float(center[0]) + float(dx), 6),
            round(float(center[1]) + float(dy), 6),
            round(z, 6),
        ]
        for dx, dy in offsets
    ]


def _candidate_has_direct_support(
    position: list[float],
    surface: dict[str, Any],
    footprint: tuple[float, float],
) -> bool:
    center = surface["center"]
    half_extents = surface["half_extents"]
    margin_x = float(footprint[0]) + 0.015
    margin_y = float(footprint[1]) + 0.015
    return abs(float(position[0]) - float(center[0])) + margin_x <= float(half_extents[0]) and abs(
        float(position[1]) - float(center[1])
    ) + margin_y <= float(half_extents[1])


def _candidate_is_clear_of_dynamic_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
    obj: dict[str, Any],
    position: list[float],
    *,
    footprint: tuple[float, float],
    bottom_offset: float,
) -> bool:
    object_id = str(obj.get("object_id") or "")
    candidate_bottom = float(position[2]) - float(bottom_offset)
    candidate_height = max(_object_height(model, data, obj), 0.04)
    candidate_top = candidate_bottom + candidate_height
    candidate_min_x = float(position[0]) - float(footprint[0])
    candidate_max_x = float(position[0]) + float(footprint[0])
    candidate_min_y = float(position[1]) - float(footprint[1])
    candidate_max_y = float(position[1]) + float(footprint[1])
    for other in state.get("objects", {}).values():
        if str(other.get("object_id") or "") == object_id:
            continue
        if other.get("location_relation") == "held":
            continue
        other_aabb = _object_world_aabb(model, data, other)
        if other_aabb is None:
            continue
        if not _aabb_xy_overlaps(
            (candidate_min_x, candidate_max_x, candidate_min_y, candidate_max_y),
            other_aabb,
            margin=0.02,
        ):
            continue
        if other_aabb["max_z"] < candidate_bottom - 0.03:
            continue
        if other_aabb["min_z"] > candidate_top + 0.12:
            continue
        return False
    return True


def _elevated_position_over_surface(
    surface: dict[str, Any],
    *,
    bottom_offset: float,
) -> list[float]:
    center = surface["center"]
    return [
        round(float(center[0]), 6),
        round(float(center[1]), 6),
        round(float(surface["top_z"]) + float(bottom_offset) + 0.08, 6),
    ]


def _placement_position(
    receptacle: dict[str, Any],
    *,
    index: int,
    relation: str = "on",
    object_category: str | None = None,
) -> list[float]:
    """Legacy nonblocking fallback pose when direct support cannot be resolved."""
    base = receptacle["position"]
    if receptacle.get("category") == "Fridge" and relation == "inside":
        return [float(base[0]) + 0.08, float(base[1]) - 0.16, float(base[2]) + 0.35]
    if receptacle.get("category") == "Fridge":
        return [float(base[0]) + 0.25, float(base[1]) + 0.5, float(base[2]) + 0.55]
    offset = ((index % 3) - 1) * 0.12
    y_offset = 0.08 * (index % 2)
    if object_category == "Apple":
        y_offset = 0.16
    elif object_category == "RemoteControl":
        if receptacle.get("category") == "TVStand":
            tv_slots = (-0.18, 0.18, 0.0)
            offset = tv_slots[index % len(tv_slots)]
            y_offset = -0.28
        else:
            offset = 0.0
            y_offset = 0.34
    if object_category == "Apple":
        height = 0.58
    elif object_category == "RemoteControl":
        height = 0.49 if receptacle.get("category") == "TVStand" else 0.45
    else:
        height = 0.35
    if (
        relation == "on"
        and receptacle.get("category") == "DiningTable"
        and receptacle.get("support_top_z") is not None
    ):
        height = (
            float(receptacle["support_top_z"])
            - float(base[2])
            + _object_surface_lift(object_category)
        )
    return [float(base[0]) + offset, float(base[1]) + y_offset, float(base[2]) + height]


def _object_surface_lift(object_category: str | None) -> float:
    if object_category in {"Book", "Plate", "RemoteControl"}:
        return 0.04
    if object_category in {"Apple", "Potato"}:
        return 0.08
    if object_category == "Pillow":
        return 0.12
    return 0.06


def _direct_support_clearance(obj: dict[str, Any], receptacle: dict[str, Any]) -> float:
    object_category = obj.get("category")
    receptacle_category = receptacle.get("category")
    if receptacle_category in {"Bed", "Sofa"}:
        return 0.035
    if object_category in {"Book", "Plate", "RemoteControl"}:
        return 0.02
    return 0.015


def _receptacle_support_surfaces(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_name: str,
) -> list[dict[str, Any]]:
    geom_ids = _subtree_geom_ids(model, body_name)
    collision_ids = [
        geom_id
        for geom_id in geom_ids
        if "collision"
        in (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id) or "").lower()
    ]
    candidate_ids = collision_ids or [
        geom_id
        for geom_id in geom_ids
        if "visual"
        not in (mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id) or "").lower()
    ]
    surfaces = []
    for geom_id in candidate_ids:
        surface = _support_surface_from_geom(model, data, geom_id)
        if surface is not None:
            surfaces.append(surface)
    return sorted(
        surfaces,
        key=lambda item: (float(item["top_z"]), float(item["area_m2"])),
        reverse=True,
    )


def _support_surface_from_geom(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    geom_id: int,
) -> dict[str, Any] | None:
    half_extents = _geom_world_half_extents(model, data, geom_id)
    if half_extents is None:
        return None
    half_x, half_y, half_z = half_extents
    if half_x < 0.06 or half_y < 0.06:
        return None
    area = 4.0 * half_x * half_y
    if area < 0.03:
        return None
    if not _geom_has_upward_support_normal(data, geom_id):
        return None
    center = _xyz(data.geom_xpos[geom_id])
    geom_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id) or f"geom_{geom_id}"
    return {
        "surface_id": geom_name,
        "geom_id": int(geom_id),
        "center": [center[0], center[1]],
        "top_z": round(float(center[2]) + float(half_z), 6),
        "half_extents": [round(float(half_x), 6), round(float(half_y), 6)],
        "area_m2": round(float(area), 6),
        "source": "mujoco_collision_geom",
    }


def _geom_has_upward_support_normal(data: mujoco.MjData, geom_id: int) -> bool:
    xmat = data.geom_xmat[geom_id]
    local_axis_world_z = max(abs(float(xmat[6])), abs(float(xmat[7])), abs(float(xmat[8])))
    return local_axis_world_z >= 0.75


def _geom_world_half_extents(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    geom_id: int,
) -> tuple[float, float, float] | None:
    geom_type = int(model.geom_type[geom_id])
    size = model.geom_size[geom_id]
    if geom_type == int(mujoco.mjtGeom.mjGEOM_BOX):
        local = (float(size[0]), float(size[1]), float(size[2]))
    elif geom_type in {
        int(mujoco.mjtGeom.mjGEOM_CYLINDER),
        int(mujoco.mjtGeom.mjGEOM_CAPSULE),
    }:
        local = (float(size[0]), float(size[0]), float(size[1]))
    elif geom_type == int(mujoco.mjtGeom.mjGEOM_SPHERE):
        local = (float(size[0]), float(size[0]), float(size[0]))
    elif geom_type == int(mujoco.mjtGeom.mjGEOM_ELLIPSOID):
        local = (float(size[0]), float(size[1]), float(size[2]))
    else:
        return None
    return _oriented_half_extents(data.geom_xmat[geom_id], local)


def _oriented_half_extents(
    xmat: Any,
    local: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        abs(float(xmat[0])) * local[0]
        + abs(float(xmat[1])) * local[1]
        + abs(float(xmat[2])) * local[2],
        abs(float(xmat[3])) * local[0]
        + abs(float(xmat[4])) * local[1]
        + abs(float(xmat[5])) * local[2],
        abs(float(xmat[6])) * local[0]
        + abs(float(xmat[7])) * local[1]
        + abs(float(xmat[8])) * local[2],
    )


def _support_top_z(surfaces: list[dict[str, Any]]) -> float | None:
    if not surfaces:
        return None
    return round(max(float(surface["top_z"]) for surface in surfaces), 6)


def _object_bottom_offset(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    obj: dict[str, Any],
) -> float:
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, str(obj.get("body_name") or ""))
    if body_id < 0:
        return _object_surface_lift(obj.get("category"))
    bottoms = []
    for geom_id in _subtree_geom_ids(model, str(obj.get("body_name") or "")):
        half_extents = _geom_world_half_extents(model, data, geom_id)
        if half_extents is None:
            continue
        bottoms.append(float(data.geom_xpos[geom_id][2]) - float(half_extents[2]))
    if not bottoms:
        return _object_surface_lift(obj.get("category"))
    offset = float(data.xpos[body_id][2]) - min(bottoms)
    if offset <= 0.0 or offset > 1.0:
        return _object_surface_lift(obj.get("category"))
    return max(offset, 0.01)


def _object_height(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    obj: dict[str, Any],
) -> float:
    aabb = _object_world_aabb(model, data, obj)
    if aabb is None:
        return _object_surface_lift(obj.get("category"))
    return max(float(aabb["max_z"]) - float(aabb["min_z"]), 0.01)


def _object_world_aabb(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    obj: dict[str, Any],
) -> dict[str, float] | None:
    geom_ids = _subtree_geom_ids(model, str(obj.get("body_name") or ""))
    if not geom_ids:
        return None
    min_x = min_y = min_z = math.inf
    max_x = max_y = max_z = -math.inf
    for geom_id in geom_ids:
        half_extents = _geom_world_half_extents(model, data, geom_id)
        if half_extents is None:
            continue
        center = data.geom_xpos[geom_id]
        min_x = min(min_x, float(center[0]) - float(half_extents[0]))
        max_x = max(max_x, float(center[0]) + float(half_extents[0]))
        min_y = min(min_y, float(center[1]) - float(half_extents[1]))
        max_y = max(max_y, float(center[1]) + float(half_extents[1]))
        min_z = min(min_z, float(center[2]) - float(half_extents[2]))
        max_z = max(max_z, float(center[2]) + float(half_extents[2]))
    if not math.isfinite(min_x):
        return None
    return {
        "min_x": min_x,
        "max_x": max_x,
        "min_y": min_y,
        "max_y": max_y,
        "min_z": min_z,
        "max_z": max_z,
    }


def _aabb_xy_overlaps(
    first: tuple[float, float, float, float],
    second: dict[str, float],
    *,
    margin: float,
) -> bool:
    min_x, max_x, min_y, max_y = first
    return (
        min_x - margin <= float(second["max_x"])
        and max_x + margin >= float(second["min_x"])
        and min_y - margin <= float(second["max_y"])
        and max_y + margin >= float(second["min_y"])
    )


def _object_footprint_half_extents(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    obj: dict[str, Any],
) -> tuple[float, float]:
    half_x = 0.0
    half_y = 0.0
    for geom_id in _subtree_geom_ids(model, str(obj.get("body_name") or "")):
        half_extents = _geom_world_half_extents(model, data, geom_id)
        if half_extents is None:
            continue
        half_x = max(half_x, float(half_extents[0]))
        half_y = max(half_y, float(half_extents[1]))
    if half_x > 0.0 and half_y > 0.0:
        return (max(half_x, 0.025), max(half_y, 0.025))
    category = obj.get("category")
    if category == "RemoteControl":
        return (0.09, 0.045)
    if category == "Plate":
        return (0.13, 0.13)
    if category in {"Apple", "Potato"}:
        return (0.065, 0.065)
    if category == "Book":
        return (0.12, 0.08)
    if category == "Pillow":
        return (0.22, 0.16)
    return (0.08, 0.08)


def _receptacle_requires_open(receptacle: dict[str, Any]) -> bool:
    text = _receptacle_text(receptacle)
    return "fridge" in text or "refrigerator" in text


def _receptacle_prefers_inside(receptacle: dict[str, Any]) -> bool:
    return _receptacle_requires_open(receptacle) or _receptacle_is_open_container(receptacle)


def _receptacle_is_open_container(receptacle: dict[str, Any]) -> bool:
    text = _receptacle_text(receptacle)
    return any(term in text for term in ("shelvingunit", "bookshelf", "bookcase", "shelf"))


def _receptacle_text(receptacle: dict[str, Any]) -> str:
    return f"{receptacle.get('name', '')} {receptacle.get('category', '')}".lower()


def _placement_diagnostic(
    *,
    state: dict[str, Any],
    object_id: str,
    receptacle_id: str,
    relation: str,
    requested_position: list[float],
    source: str,
    placement_index: int | None = None,
    placement_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    obj = state["objects"][object_id]
    receptacle = state["receptacles"][receptacle_id]
    object_position = [float(value) for value in obj.get("position", requested_position)]
    receptacle_position = [float(value) for value in receptacle.get("position", [0.0, 0.0, 0.0])]
    xy_distance = math.dist(object_position[:2], receptacle_position[:2])
    z_delta = object_position[2] - receptacle_position[2]
    placement_resolution = placement_resolution or {}
    default_support_status = (
        "semantic_contained_in_receptacle" if relation == "inside" else "semantic_on_receptacle"
    )
    support_status = str(placement_resolution.get("support_status") or default_support_status)
    diagnostic = {
        "schema": "molmospaces_semantic_placement_diagnostic_v1",
        "status": support_status,
        "object_id": object_id,
        "object_category": obj.get("category"),
        "object_body_name": obj.get("body_name"),
        "receptacle_id": receptacle_id,
        "receptacle_category": receptacle.get("category"),
        "receptacle_body_name": receptacle.get("body_name"),
        "relation": relation,
        "placement_index": placement_index,
        "requested_position": [round(float(value), 6) for value in requested_position],
        "object_position": [round(float(value), 6) for value in object_position],
        "receptacle_position": [round(float(value), 6) for value in receptacle_position],
        "xy_distance_m": round(float(xy_distance), 6),
        "z_delta_m": round(float(z_delta), 6),
        "support_status": support_status,
        "placement_support_status": support_status,
        "contact_proof": str(
            placement_resolution.get("contact_proof") or "not_measured_mujoco_freejoint_qpos"
        ),
        "diagnostic_source": source,
        "resolution_source": placement_resolution.get("resolution_source", "legacy_semantic"),
        "candidate_count": int(placement_resolution.get("candidate_count") or 0),
        "degraded": bool(placement_resolution.get("degraded", False)),
    }
    support_surface = placement_resolution.get("support_surface")
    if isinstance(support_surface, dict):
        diagnostic["support_surface_id"] = support_surface.get("surface_id")
        diagnostic["support_surface_center"] = support_surface.get("center")
        diagnostic["support_surface_half_extents"] = support_surface.get("half_extents")
        diagnostic["support_surface_top_z"] = support_surface.get("top_z")
    if placement_resolution.get("object_bottom_offset_m") is not None:
        diagnostic["object_bottom_offset_m"] = placement_resolution["object_bottom_offset_m"]
    if placement_resolution.get("support_clearance_m") is not None:
        diagnostic["support_clearance_m"] = placement_resolution["support_clearance_m"]
    if placement_resolution.get("object_footprint_half_extents_m") is not None:
        diagnostic["object_footprint_half_extents_m"] = placement_resolution[
            "object_footprint_half_extents_m"
        ]
    return diagnostic


def _load_model_data(scene_xml: Path) -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(scene_xml))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


def _load_model_data_for_state(state: dict[str, Any]) -> tuple[mujoco.MjModel, mujoco.MjData]:
    scene_xml = str(state["scene_xml"])
    if state.get("robot_included"):
        robot_xml = state.get("robot_xml")
        if not robot_xml:
            raise ValueError("robot_included state missing robot_xml")
        cache_key = (scene_xml, str(robot_xml))
        cached = _MODEL_DATA_CACHE.get(cache_key)
        if cached is None:
            cached = _load_robot_model_data(Path(scene_xml), Path(robot_xml))
            _MODEL_DATA_CACHE[cache_key] = cached
        return cached
    cache_key = (scene_xml, "")
    cached = _MODEL_DATA_CACHE.get(cache_key)
    if cached is None:
        cached = _load_model_data(Path(scene_xml))
        _MODEL_DATA_CACHE[cache_key] = cached
    return cached


def _load_robot_model_data(
    scene_xml: Path,
    robot_xml: Path,
) -> tuple[mujoco.MjModel, mujoco.MjData]:
    xml_content = scene_xml.read_text(encoding="utf-8")
    mujoco_tag_end = xml_content.find(">") + 1
    include_line = f'\n  <include file="{robot_xml}"/>\n'
    modified_xml = xml_content[:mujoco_tag_end] + include_line + xml_content[mujoco_tag_end:]
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            suffix=".xml",
            prefix="roboclaws_robot_scene_",
            dir=str(scene_xml.parent),
            delete=False,
            encoding="utf-8",
        ) as temp:
            temp.write(modified_xml)
            temp_path = Path(temp.name)
        return _load_model_data(temp_path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _robot_xml_name(robot_name: str) -> str:
    if robot_name == "rby1m":
        return "rby1_v1.2_site_control.xml"
    if robot_name == "rby1":
        return "rby1_site_control.xml"
    raise ValueError(f"unsupported robot for visual cleanup demo: {robot_name}")


def _robot_camera_names(model: mujoco.MjModel) -> list[str]:
    names = []
    for camera_id in range(model.ncam):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_CAMERA, camera_id)
        if name and name.startswith("robot_0/"):
            names.append(name)
    return names


def _robot_result_payload(state: dict[str, Any], model: mujoco.MjModel) -> dict[str, Any]:
    return {
        "robot_included": True,
        "robot_name": state.get("robot_name"),
        "robot_xml": state.get("robot_xml"),
        "robot_body_name": state.get("robot_body_name"),
        "robot_camera_names": state.get("robot_camera_names") or _robot_camera_names(model),
        "robot_control_provenance": state.get("robot_control_provenance"),
        "robot_view_provenance": state.get("robot_view_provenance"),
        "robot_pose": state.get("robot_pose"),
        "room_outline_count": len(state.get("room_outlines", [])),
        "robot_model_stats": {
            "nbody": int(model.nbody),
            "ngeom": int(model.ngeom),
            "njnt": int(model.njnt),
            "nq": int(model.nq),
            "nu": int(model.nu),
        },
    }


def _set_robot_pose(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    pose: dict[str, float],
) -> None:
    _set_joint_qpos(model, data, "robot_0/base_x", pose["x"])
    _set_joint_qpos(model, data, "robot_0/base_y", pose["y"])
    _set_joint_qpos(model, data, "robot_0/base_theta", pose["theta"])
    if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "robot_0/head_0") >= 0:
        _set_joint_qpos(model, data, "robot_0/head_0", float(pose.get("head_yaw", 0.0)))
    if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "robot_0/head_1") >= 0:
        _set_joint_qpos(model, data, "robot_0/head_1", float(pose.get("head_pitch", 0.0)))


def _apply_robot_view_camera_offset(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    *,
    yaw_offset_deg: float = 0.0,
    pitch_offset_deg: float = 0.0,
) -> dict[str, Any]:
    applied_joints: list[str] = []
    unavailable_reason = None
    if yaw_offset_deg:
        try:
            if _add_joint_qpos_if_present(
                model,
                data,
                "robot_0/head_0",
                math.radians(float(yaw_offset_deg)),
            ):
                applied_joints.append("robot_0/head_0")
        except TypeError as exc:
            unavailable_reason = f"{type(exc).__name__}: {exc}"
    if pitch_offset_deg:
        try:
            if _add_joint_qpos_if_present(
                model,
                data,
                "robot_0/head_1",
                math.radians(float(pitch_offset_deg)),
            ):
                applied_joints.append("robot_0/head_1")
        except TypeError as exc:
            unavailable_reason = f"{type(exc).__name__}: {exc}"
    return _robot_view_camera_adjustment(
        camera_yaw_offset_deg=yaw_offset_deg,
        camera_pitch_offset_deg=pitch_offset_deg,
        applied_joints=applied_joints,
        unavailable_reason=unavailable_reason,
    )


def _add_joint_qpos_if_present(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    joint_name: str,
    delta: float,
) -> bool:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        return False
    qposadr = int(model.jnt_qposadr[joint_id])
    data.qpos[qposadr] = float(data.qpos[qposadr]) + float(delta)
    return True


def _set_joint_qpos(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    joint_name: str,
    value: float,
) -> None:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        raise ValueError(f"missing robot joint: {joint_name}")
    qposadr = int(model.jnt_qposadr[joint_id])
    data.qpos[qposadr] = float(value)


def _sync_held_object_to_robot_pose(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    object_id = state.get("held_object_id")
    if not object_id:
        return None
    obj = state["objects"].get(str(object_id))
    if obj is None:
        return None
    target_position = _held_object_position(state)
    _set_free_body_position(model, data, obj["body_name"], target_position)
    obj["position"] = target_position
    return {
        "object_id": object_id,
        "position": target_position,
        "position_source": "robot_relative_held_pose",
    }


def _held_object_position(state: dict[str, Any]) -> list[float]:
    pose = state.get("robot_pose") or {}
    if "x" not in pose or "y" not in pose or "theta" not in pose:
        return [0.0, 0.0, 1.0]
    theta = float(pose["theta"])
    distance_m = 0.8
    return [
        round(float(pose["x"]) + math.cos(theta) * distance_m, 6),
        round(float(pose["y"]) + math.sin(theta) * distance_m, 6),
        1.22,
    ]


def _openable_receptacle_joints(
    model: mujoco.MjModel,
    body_name: str,
) -> list[dict[str, Any]]:
    joints = []
    for body_id in _subtree_body_ids(model, body_name):
        joint_count = int(model.body_jntnum[body_id])
        if joint_count <= 0:
            continue
        for offset in range(joint_count):
            joint_id = int(model.body_jntadr[body_id]) + offset
            joint_type = int(model.jnt_type[joint_id])
            if joint_type not in {
                int(mujoco.mjtJoint.mjJNT_HINGE),
                int(mujoco.mjtJoint.mjJNT_SLIDE),
            }:
                continue
            joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
            if not joint_name:
                continue
            open_value = float(model.jnt_range[joint_id][1])
            close_value = float(model.jnt_range[joint_id][0])
            joints.append(
                {
                    "joint_name": joint_name,
                    "joint_type": "hinge"
                    if joint_type == int(mujoco.mjtJoint.mjJNT_HINGE)
                    else "slide",
                    "open_value": round(open_value, 6),
                    "close_value": round(close_value, 6),
                }
            )
    return joints


def _robot_pose_near_receptacle(
    state: dict[str, Any],
    receptacle: dict[str, Any],
) -> dict[str, float]:
    target = receptacle["position"]
    target_room_id = _target_room_id(state, receptacle)
    pose = _robot_pose_near_position(
        state,
        target,
        target_room_id=target_room_id,
        target_receptacle_id=receptacle["receptacle_id"],
    )
    pose["robot_room_id"] = pose.get("robot_room_id")
    pose.update(_room_relation_payload(state, receptacle, [pose["x"], pose["y"]]))
    return pose


def _robot_pose_for_open_receptacle(
    state: dict[str, Any],
    receptacle: dict[str, Any],
) -> dict[str, float]:
    if receptacle.get("category") != "Fridge":
        return _robot_pose_near_receptacle(state, receptacle)

    base = receptacle["position"]
    target_room_id = _target_room_id(state, receptacle)
    candidates = [
        (float(base[0]) - 0.76, float(base[1]) + 0.20),
        (float(base[0]) - 0.72, float(base[1]) + 0.36),
        (float(base[0]) - 0.90, float(base[1]) + 0.08),
    ]
    x, y = _first_same_room_point(state, candidates, target_room_id)
    target = [float(base[0]), float(base[1]), float(base[2]) + 0.35]
    theta = math.atan2(target[1] - y, target[0] - x)
    pose = {
        "x": round(float(x), 6),
        "y": round(float(y), 6),
        "z": 0.0,
        "theta": round(float(theta), 6),
        "theta_source": "opened_receptacle_access_yaw",
        "head_yaw": 0.0,
        "head_yaw_source": "base_yaw_handles_target_bearing",
        "head_pitch": _robot_head_pitch_for_target(target, [x, y]),
        "head_pitch_source": "target_framing_head_pitch",
        "target_receptacle_id": receptacle["receptacle_id"],
        "robot_room_id": _room_for_point(state, [x, y]) or target_room_id,
    }
    pose.update(_room_relation_payload(state, receptacle, [pose["x"], pose["y"]]))
    return {key: value for key, value in pose.items() if value is not None}


def _first_same_room_point(
    state: dict[str, Any],
    candidates: list[tuple[float, float]],
    target_room_id: str | None,
) -> tuple[float, float]:
    for x, y in candidates:
        if _room_for_point(state, [x, y]) == target_room_id:
            return x, y
    return candidates[0]


def _robot_pose_near_object(
    state: dict[str, Any],
    obj: dict[str, Any],
    *,
    source_receptacle_id: str | None = None,
) -> dict[str, float]:
    target = obj["position"]
    source_receptacle = state["receptacles"].get(
        source_receptacle_id or obj.get("seeded_start_receptacle_id", "")
    )
    source_room_id = _target_room_id(state, source_receptacle) if source_receptacle else None
    target_room_id = _room_for_point(state, target) or source_room_id
    pose = _robot_pose_near_position(
        state,
        target,
        target_room_id=target_room_id,
        target_object_id=obj["object_id"],
    )
    robot_room_id = pose.get("robot_room_id")
    pose.update(
        {
            "target_room_id": target_room_id,
            "same_room_as_target": robot_room_id == target_room_id,
            "room_plausibility": "same_room"
            if robot_room_id == target_room_id
            else "room_mismatch",
        }
    )
    return pose


def _robot_pose_for_waypoint(
    state: dict[str, Any],
    waypoint: dict[str, Any],
    target: list[float],
) -> dict[str, float]:
    room_id = str(waypoint.get("room_id") or "")
    room_outline = _room_outline_for_id(state, room_id)
    scene_focus = _room_outline_center_xy(room_outline) or _scene_center(
        list(state["receptacles"].values())
    )
    theta = math.atan2(float(scene_focus[1]) - target[1], float(scene_focus[0]) - target[0])
    head_target = [float(scene_focus[0]), float(scene_focus[1]), 1.2]
    robot_room_id = _room_for_point(state, target) or room_id
    return {
        "x": round(target[0], 6),
        "y": round(target[1], 6),
        "z": 0.0,
        "theta": round(float(theta), 6),
        "theta_source": "waypoint_room_outline_focus_yaw",
        "head_yaw": 0.0,
        "head_yaw_source": "base_yaw_handles_waypoint_focus",
        "head_pitch": _robot_head_pitch_for_target(head_target, [target[0], target[1]]),
        "head_pitch_source": "room_center_framing_head_pitch",
        "target_waypoint_id": str(waypoint.get("waypoint_id") or ""),
        "target_room_id": room_id,
        "robot_room_id": robot_room_id,
        "same_room_as_target": robot_room_id == room_id,
        "room_plausibility": "same_room" if robot_room_id == room_id else "room_mismatch",
        "pose_source": "waypoint_room_outline_projection",
        "target_position": [round(target[0], 6), round(target[1], 6), round(target[2], 6)],
        "pose_request": {
            "schema": "cleanup_waypoint_pose_request_v1",
            "waypoint_id": str(waypoint.get("waypoint_id") or ""),
            "room_id": room_id,
            "waypoint_xy": [float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0))],
            "source_room_bounds": waypoint.get("source_room_bounds") or {},
            "room_outline": room_outline or {},
            "resolver": "roboclaws.cleanup_robot_pose.waypoint_room_projection_v1",
        },
    }


def _waypoint_target_position(
    state: dict[str, Any],
    waypoint: dict[str, Any],
) -> list[float]:
    room_id = str(waypoint.get("room_id") or "")
    outline = _room_outline_for_id(state, room_id)
    if outline is None:
        return [float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0)), 0.0]
    center = outline.get("center") or [0.0, 0.0]
    half_extents = outline.get("half_extents") or [1.0, 1.0]
    bounds = waypoint.get("source_room_bounds") or {}
    source_min_x = _float_or_zero(bounds.get("min_x"))
    source_max_x = _float_or_zero(bounds.get("max_x"))
    source_min_y = _float_or_zero(bounds.get("min_y"))
    source_max_y = _float_or_zero(bounds.get("max_y"))
    source_width = source_max_x - source_min_x
    source_height = source_max_y - source_min_y
    if source_width <= 0.001 or source_height <= 0.001:
        nx = 0.5
        ny = 0.5
    else:
        nx = (float(waypoint.get("x", 0.0)) - source_min_x) / source_width
        ny = (float(waypoint.get("y", 0.0)) - source_min_y) / source_height
    nx = min(max(nx, 0.08), 0.92)
    ny = min(max(ny, 0.08), 0.92)
    margin = 0.35
    half_x = max(float(half_extents[0]) - margin, 0.1)
    half_y = max(float(half_extents[1]) - margin, 0.1)
    x = float(center[0]) + (nx - 0.5) * 2.0 * half_x
    y = float(center[1]) + (ny - 0.5) * 2.0 * half_y
    return [round(x, 6), round(y, 6), 0.0]


def _room_outline_center_xy(outline: dict[str, Any] | None) -> tuple[float, float] | None:
    if outline is None:
        return None
    center = outline.get("center")
    if not isinstance(center, list | tuple) or len(center) < 2:
        return None
    return (float(center[0]), float(center[1]))


def _robot_pose_near_position(
    state: dict[str, Any],
    target: list[float],
    *,
    target_room_id: str | None,
    target_receptacle_id: str | None = None,
    target_object_id: str | None = None,
) -> dict[str, float]:
    stand_off = _robot_stand_off_for_target(state, target_object_id)
    pose = resolve_cleanup_robot_pose(
        target_position=target,
        target_room_id=target_room_id,
        target_receptacle_id=target_receptacle_id,
        target_object_id=target_object_id,
        room_outlines=state.get("room_outlines") or [],
        scene_center=_scene_center(list(state["receptacles"].values())),
        stand_off_m=stand_off,
    )
    return {key: value for key, value in pose.items() if value is not None}


def _robot_stand_off_for_target(state: dict[str, Any], target_object_id: str | None) -> float:
    obj = state.get("objects", {}).get(target_object_id or "")
    if not obj:
        return 1.15
    if obj.get("category") == "RemoteControl":
        return 0.85
    if obj.get("category") == "Apple":
        return 1.0
    return 1.15


def _robot_head_pitch_for_target(target: list[float], robot_xy: list[float]) -> float:
    return robot_head_pitch_for_target(target, robot_xy)


def _scene_center(items: list[dict[str, Any]]) -> tuple[float, float]:
    if not items:
        return (0.0, 0.0)
    return (
        sum(float(item["position"][0]) for item in items) / len(items),
        sum(float(item["position"][1]) for item in items) / len(items),
    )


def _render_fixed_camera(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera_name: str,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Any:
    width, height = _render_dimensions(width, height)
    _ensure_offscreen_framebuffer(model, width=width, height=height)
    renderer = mujoco.Renderer(model, height=height, width=width, max_geom=20000)
    renderer.update_scene(data, camera=camera_name)
    frame = _normalize_renderer_frame(renderer.render())
    renderer.close()
    return frame


def _fixed_camera_diagnostics(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera_name: str,
) -> dict[str, Any]:
    try:
        camera_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, camera_name)
        if camera_id < 0:
            return {
                "schema": "mujoco_fixed_camera_diagnostics_v1",
                "status": "missing_camera",
                "camera_name": camera_name,
            }
        world_position = _array_row(getattr(data, "cam_xpos"), camera_id, 3)
        world_xmat = _array_row(getattr(data, "cam_xmat"), camera_id, 9)
        return {
            "schema": "mujoco_fixed_camera_diagnostics_v1",
            "status": "ready",
            "camera_name": camera_name,
            "camera_id": int(camera_id),
            "camera_type": "fixed",
            "world_position": world_position,
            "world_xmat_rowmajor": world_xmat,
            "fovy_deg": _array_scalar(getattr(model, "cam_fovy", None), camera_id),
            "model_pos": _array_row(getattr(model, "cam_pos"), camera_id, 3),
            "model_quat_wxyz": _array_row(getattr(model, "cam_quat"), camera_id, 4),
            "znear": _optional_float(getattr(getattr(model, "vis", None), "map", None), "znear"),
            "zfar": _optional_float(getattr(getattr(model, "vis", None), "map", None), "zfar"),
        }
    except Exception as exc:
        return {
            "schema": "mujoco_fixed_camera_diagnostics_v1",
            "status": "unavailable",
            "camera_name": camera_name,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def _free_camera_diagnostics(camera: mujoco.MjvCamera) -> dict[str, Any]:
    try:
        return {
            "schema": "mujoco_free_camera_diagnostics_v1",
            "status": "ready",
            "camera_type": "free",
            "lookat": [round(float(value), 6) for value in camera.lookat],
            "distance": round(float(camera.distance), 6),
            "azimuth": round(float(camera.azimuth), 6),
            "elevation": round(float(camera.elevation), 6),
        }
    except Exception as exc:
        return {
            "schema": "mujoco_free_camera_diagnostics_v1",
            "status": "unavailable",
            "reason": f"{type(exc).__name__}: {exc}",
        }


def _array_row(array: Any, index: int, length: int) -> list[float]:
    return [round(float(value), 6) for value in array[index][:length]]


def _array_scalar(array: Any, index: int) -> float | None:
    if array is None:
        return None
    return round(float(array[index]), 6)


def _optional_float(parent: Any, attribute: str) -> float | None:
    if parent is None or not hasattr(parent, attribute):
        return None
    try:
        return round(float(getattr(parent, attribute)), 6)
    except (TypeError, ValueError):
        return None


def _focus_camera(state: dict[str, Any], focus: dict[str, Any]) -> mujoco.MjvCamera:
    focus_position = focus.get("focus_position") or _scene_focus_position(state)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = [
        float(focus_position[0]),
        float(focus_position[1]),
        float(focus_position[2]) + 0.35,
    ]
    if focus.get("focus_mode") == "object_closeup":
        camera.lookat[:] = [
            float(focus_position[0]),
            float(focus_position[1]),
            float(focus_position[2]) + 0.05,
        ]
        camera.distance = 1.8
        camera.elevation = -65
    else:
        camera.distance = 4.0 if focus.get("has_focus") else 7.5
        camera.elevation = -68 if focus.get("has_focus") else -45
    camera.azimuth = _focus_camera_azimuth(state, focus_position, focus)
    return camera


def _render_free_camera(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Any:
    width, height = _render_dimensions(width, height)
    _ensure_offscreen_framebuffer(model, width=width, height=height)
    renderer = mujoco.Renderer(model, height=height, width=width, max_geom=20000)
    renderer.update_scene(data, camera=camera)
    frame = _normalize_renderer_frame(renderer.render())
    renderer.close()
    return frame


def _load_rendered_robot_view_image(camera_views: dict[str, Any], *, role: str) -> Any:
    for item in camera_views.get("views") or []:
        if not isinstance(item, dict) or item.get("robot_view_role") != role:
            continue
        image_path = Path(str(item.get("image_path") or ""))
        if not image_path.is_file():
            raise RuntimeError(f"missing rendered {role} camera-control image: {image_path}")
        return _image_to_array(image_path)
    raise RuntimeError(f"missing rendered {role} camera-control view")


def _image_to_array(path: Path) -> Any:
    import numpy as np

    with Image.open(path) as image:
        return np.asarray(image.convert("RGB")).copy()


def _load_camera_view_specs(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_views = payload.get("views") if isinstance(payload, dict) else payload
    if not isinstance(raw_views, list):
        raise ValueError("camera view spec must be a list or an object with a views list")
    return [dict(item) for item in raw_views if isinstance(item, dict)]


def _load_camera_request_from_args(
    *,
    view_specs_path: Path | None,
    camera_request_path: Path | None,
    width: int,
    height: int,
) -> dict[str, Any]:
    if camera_request_path is not None:
        return load_camera_control_request(camera_request_path, width=width, height=height)
    if view_specs_path is not None:
        return normalize_camera_control_request(
            _load_camera_view_specs(view_specs_path),
            width=width,
            height=height,
        )
    raise ValueError("camera_views requires --camera-request-path or --view-specs-path")


def _load_camera_request_from_kwargs(
    kwargs: dict[str, Any],
    *,
    width: int,
    height: int,
) -> dict[str, Any]:
    camera_request_path = kwargs.get("camera_request_path")
    if camera_request_path:
        return load_camera_control_request(
            Path(str(camera_request_path)), width=width, height=height
        )
    view_specs_path = kwargs.get("view_specs_path")
    if view_specs_path:
        return normalize_camera_control_request(
            _load_camera_view_specs(Path(str(view_specs_path))),
            width=width,
            height=height,
        )
    raise ValueError("camera_views requires camera_request_path or view_specs_path")


def _camera_view_spec(raw_spec: dict[str, Any], *, index: int) -> dict[str, Any]:
    view_id = str(raw_spec.get("view_id") or raw_spec.get("id") or f"view_{index:02d}")
    safe_view_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in view_id)
    lookat = _camera_vec3(raw_spec.get("lookat") or raw_spec.get("target"), default=[0, 0, 0])
    camera_orbit = _lane_camera_orbit(raw_spec, "molmospaces-mujoco")
    lens = raw_spec.get("lens") if isinstance(raw_spec.get("lens"), dict) else {}
    if "eye" in raw_spec and raw_spec.get("eye") is not None:
        eye = _camera_vec3(
            raw_spec.get("eye"), default=[lookat[0], lookat[1] - 4.0, lookat[2] + 2.0]
        )
        dx = eye[0] - lookat[0]
        dy = eye[1] - lookat[1]
        dz = eye[2] - lookat[2]
        distance = max(math.sqrt(dx * dx + dy * dy + dz * dz), 0.01)
        horizontal = math.hypot(dx, dy)
        if horizontal > 1e-9:
            azimuth = math.degrees(math.atan2(-dy, -dx))
        else:
            azimuth = float(camera_orbit.get("azimuth_deg", raw_spec.get("azimuth", 0.0)))
        elevation = -math.degrees(math.asin(dz / distance))
    else:
        distance = float(camera_orbit.get("distance_m", raw_spec.get("distance", 4.0)))
        azimuth = float(camera_orbit.get("azimuth_deg", raw_spec.get("azimuth", 225.0)))
        elevation = -abs(float(camera_orbit.get("elevation_deg", raw_spec.get("elevation", 35.0))))
        eye = _eye_from_mujoco_free_camera(
            lookat=lookat,
            distance=distance,
            azimuth=azimuth,
            elevation=elevation,
        )
    return {
        "view_id": safe_view_id,
        "label": str(raw_spec.get("label") or view_id),
        "anchor_id": str(raw_spec.get("anchor_id") or ""),
        "anchor_kind": str(raw_spec.get("anchor_kind") or ""),
        "robot_view_role": str(raw_spec.get("robot_view_role") or ""),
        "camera_basis": str(raw_spec.get("camera_basis") or ""),
        "camera_mode": str(raw_spec.get("camera_mode") or "free_camera"),
        "focus_receptacle_id": str(raw_spec.get("focus_receptacle_id") or ""),
        "robot_pose": dict(raw_spec["robot_pose"])
        if isinstance(raw_spec.get("robot_pose"), dict)
        else {},
        "lookat": lookat,
        "target": lookat,
        "eye": eye,
        "backend_eye": eye,
        "backend_target": lookat,
        "distance": distance,
        "azimuth": azimuth,
        "elevation": elevation,
        "camera_model": str(raw_spec.get("camera_model") or ANCHOR_ORBIT_CAMERA_MODEL),
        "coordinate_frame": str(raw_spec.get("coordinate_frame") or ""),
        "camera_orbit": dict(camera_orbit),
        "lens": dict(lens),
        "calibration_status": str(raw_spec.get("calibration_status") or ""),
        "coordinate_convention": str(raw_spec.get("coordinate_convention") or ""),
    }


def _lane_camera_orbit(raw_spec: dict[str, Any], lane_id: str) -> dict[str, Any]:
    lane_orbits = raw_spec.get("lane_camera_orbits")
    if isinstance(lane_orbits, dict):
        lane_orbit = lane_orbits.get(lane_id)
        if isinstance(lane_orbit, dict):
            return lane_orbit
    camera_orbit = raw_spec.get("camera_orbit")
    return camera_orbit if isinstance(camera_orbit, dict) else {}


def _camera_request_variant(camera_request: dict[str, Any]) -> str:
    if camera_request.get("camera_model") == CANONICAL_CAMERA_MODEL:
        return "molmospaces-canonical-eye-target-camera-control-v1"
    return "molmospaces-anchor-orbit-camera-control-v1"


def _camera_request_provenance(camera_request: dict[str, Any]) -> str:
    if camera_request.get("camera_model") == CANONICAL_CAMERA_MODEL:
        return "mujoco_camera_control_canonical_eye_target"
    return "mujoco_camera_control_anchor_orbit"


def _camera_vec3(value: Any, *, default: list[float]) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return [float(default[0]), float(default[1]), float(default[2])]
    return [float(value[0]), float(value[1]), float(value[2])]


def _eye_from_mujoco_free_camera(
    *,
    lookat: list[float],
    distance: float,
    azimuth: float,
    elevation: float,
) -> list[float]:
    azimuth_rad = math.radians(azimuth)
    elevation_rad = math.radians(elevation)
    horizontal = math.cos(elevation_rad) * distance
    return [
        float(lookat[0]) - math.cos(azimuth_rad) * horizontal,
        float(lookat[1]) - math.sin(azimuth_rad) * horizontal,
        float(lookat[2]) - math.sin(elevation_rad) * distance,
    ]


def _free_camera_from_lookat_spec(spec: dict[str, Any]) -> mujoco.MjvCamera:
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = spec["lookat"]
    camera.distance = float(spec["distance"])
    camera.azimuth = float(spec["azimuth"])
    camera.elevation = float(spec["elevation"])
    return camera


def _camera_from_view_spec(state: dict[str, Any], spec: dict[str, Any]) -> mujoco.MjvCamera:
    if spec.get("camera_mode") != "focus_receptacle":
        return _free_camera_from_lookat_spec(spec)
    focus_receptacle_id = str(spec.get("focus_receptacle_id") or spec.get("anchor_id") or "")
    if spec.get("camera_model") == ANCHOR_ORBIT_CAMERA_MODEL:
        spec["camera_mode"] = "anchor_orbit"
        spec["focus_receptacle_id"] = focus_receptacle_id
        return _free_camera_from_lookat_spec(spec)
    state_for_camera = dict(state)
    if isinstance(spec.get("robot_pose"), dict):
        state_for_camera["robot_pose"] = dict(spec["robot_pose"])
    focus = _focus_payload(
        state_for_camera,
        None,
        focus_receptacle_id,
    )
    camera = _focus_camera(state_for_camera, focus)
    spec["lookat"] = [float(value) for value in camera.lookat]
    spec["distance"] = float(camera.distance)
    spec["azimuth"] = float(camera.azimuth)
    spec["elevation"] = float(camera.elevation)
    spec["camera_model"] = "mujoco_focus_receptacle_camera"
    if isinstance(spec.get("robot_pose"), dict):
        spec["virtual_robot_pose"] = dict(spec["robot_pose"])
    return camera


def _annotate_focus_image(image: Image.Image, focus: dict[str, Any]) -> None:
    if not focus.get("has_focus"):
        return
    draw = ImageDraw.Draw(image)
    object_label = str(focus.get("object_label") or "object")
    receptacle_label = str(focus.get("receptacle_label") or "target")
    label = f"Object: {object_label}   Target: {receptacle_label}"
    draw.rectangle((0, 0, image.width, 28), fill=(15, 23, 42))
    draw.text((10, 8), label, fill=(248, 250, 252))
    visibility = focus.get("visibility") or {}
    for box in visibility.get("boxes", []):
        left, top, right, bottom = box["bbox"]
        color = tuple(box["color"])
        draw.rectangle((left, top, right, bottom), outline=color, width=4)
        draw.text((left, max(30, top - 14)), box["label"], fill=color)


def _focus_camera_azimuth(
    state: dict[str, Any],
    focus_position: list[float],
    focus: dict[str, Any] | None = None,
) -> float:
    if (
        focus is not None
        and focus.get("receptacle_category") == "Fridge"
        and focus.get("focus_mode") != "object_closeup"
        and focus.get("object_contained_in") != focus.get("receptacle_id")
    ):
        return 45.0
    pose = state.get("robot_pose") or {}
    if "x" not in pose or "y" not in pose:
        return 225.0
    dx = float(focus_position[0]) - float(pose["x"])
    dy = float(focus_position[1]) - float(pose["y"])
    if math.hypot(dx, dy) < 0.001:
        return 225.0
    return math.degrees(math.atan2(dx, dy))


def _focus_payload(
    state: dict[str, Any],
    focus_object_id: str | None,
    focus_receptacle_id: str | None,
) -> dict[str, Any]:
    obj = state["objects"].get(focus_object_id) if focus_object_id else None
    receptacle = state["receptacles"].get(focus_receptacle_id) if focus_receptacle_id else None
    positions = []
    if obj is not None:
        positions.append(obj["position"])
    if receptacle is not None:
        positions.append(receptacle["position"])
    if obj is not None and receptacle is not None:
        object_position = obj["position"]
        receptacle_position = receptacle["position"]
        if obj.get("location_relation") == "held":
            focus_position = object_position
            focus_mode = "object_closeup"
        elif receptacle.get("category") == "Fridge" and obj.get("contained_in") == receptacle.get(
            "receptacle_id"
        ):
            focus_position = receptacle_position
            focus_mode = "receptacle_context"
        elif math.dist(object_position[:2], receptacle_position[:2]) > 1.2:
            focus_position = receptacle_position
            focus_mode = "receptacle_context"
        else:
            focus_position = object_position
            focus_mode = "object_closeup"
    else:
        focus_position = _average_position(positions) if positions else _scene_focus_position(state)
        focus_mode = "receptacle_context" if receptacle is not None else "scene_context"
    return {
        "has_focus": obj is not None or receptacle is not None,
        "object_id": focus_object_id,
        "object_label": _item_label(obj, "object_id") if obj is not None else None,
        "object_category": obj.get("category") if obj is not None else None,
        "object_position": obj.get("position") if obj is not None else None,
        "object_body_name": obj.get("body_name") if obj is not None else None,
        "object_contained_in": obj.get("contained_in") if obj is not None else None,
        "object_location_relation": obj.get("location_relation") if obj is not None else None,
        "receptacle_id": focus_receptacle_id,
        "receptacle_label": _item_label(receptacle, "receptacle_id")
        if receptacle is not None
        else None,
        "receptacle_category": receptacle.get("category") if receptacle is not None else None,
        "receptacle_position": receptacle.get("position") if receptacle is not None else None,
        "receptacle_body_name": receptacle.get("body_name") if receptacle is not None else None,
        "focus_position": focus_position,
        "focus_mode": focus_mode,
        "provenance": "public_mujoco_state_report_aid",
    }


def _average_position(positions: list[list[float]]) -> list[float]:
    return [
        round(sum(float(position[index]) for position in positions) / len(positions), 6)
        for index in range(3)
    ]


def _scene_focus_position(state: dict[str, Any]) -> list[float]:
    points = [item["position"] for item in state["receptacles"].values()]
    if not points:
        return [0.0, 0.0, 0.0]
    return _average_position(points)


def _item_label(item: dict[str, Any] | None, id_key: str) -> str:
    if item is None:
        return ""
    category = str(item.get("category") or item.get("kind") or "item")
    identifier = str(item.get(id_key, ""))
    short_id = identifier.split("_", 1)[0]
    return f"{category} {short_id}"


def _focus_visibility(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
    focus: dict[str, Any],
    *,
    frame: Any | None = None,
) -> dict[str, Any]:
    boxes = []
    object_pixels = 0
    receptacle_pixels = 0
    try:
        render_shape = frame.shape if frame is not None and hasattr(frame, "shape") else None
        segmentation = _render_segmentation(
            model,
            data,
            camera,
            width=_shape_width(render_shape),
            height=_shape_height(render_shape),
        )
    except Exception as exc:  # pragma: no cover - depends on MuJoCo renderer internals
        return {
            "status": "segmentation_unavailable",
            "error": type(exc).__name__,
            "object_pixels": 0,
            "receptacle_pixels": 0,
            "boxes": [],
        }
    if focus.get("object_body_name"):
        box = _segmentation_box(
            model,
            segmentation,
            focus["object_body_name"],
            label=str(focus.get("object_label") or "object"),
            color=[239, 68, 68],
        )
        if focus.get("object_category") == "RemoteControl" and (
            box is None or int(box.get("pixels") or 0) < 20
        ):
            highlight_box = _highlight_diff_box(
                model,
                data,
                camera,
                focus["object_body_name"],
                label=str(focus.get("object_label") or "object"),
                color=[239, 68, 68],
                frame=frame,
            )
            if highlight_box is not None and (
                box is None or int(highlight_box.get("pixels") or 0) > int(box.get("pixels") or 0)
            ):
                box = highlight_box
        if box is not None:
            object_pixels = int(box["pixels"])
            boxes.append(box)
    if focus.get("receptacle_body_name"):
        box = _segmentation_box(
            model,
            segmentation,
            focus["receptacle_body_name"],
            label=str(focus.get("receptacle_label") or "target"),
            color=[8, 145, 178],
        )
        if box is not None:
            receptacle_pixels = int(box["pixels"])
            boxes.append(box)
    return {
        "status": "ok",
        "object_pixels": object_pixels,
        "receptacle_pixels": receptacle_pixels,
        "boxes": boxes,
    }


def _annotate_focus_visual_grounding(focus: dict[str, Any]) -> dict[str, Any]:
    if not focus.get("has_focus"):
        return focus
    annotated = dict(focus)
    for key in ("fpv_visibility", "visibility"):
        visibility = annotated.get(key)
        if not isinstance(visibility, dict):
            continue
        updated = dict(visibility)
        if updated.get("status") != "segmentation_unavailable":
            status = _visual_grounding_status(annotated, updated)
            updated["status"] = status
            updated["visual_grounding_status"] = status
            if status == "weak_object_visibility":
                updated.setdefault(
                    "evidence_note",
                    "Focused object has zero pixels in this robot-view frame.",
                )
            elif status == "contained_inside":
                updated.setdefault(
                    "evidence_note",
                    "Object is semantically contained inside the focused receptacle.",
                )
        annotated[key] = updated
    return annotated


def _should_use_fpv_as_verify_focus(focus: dict[str, Any]) -> bool:
    fpv_visibility = focus.get("fpv_visibility") or {}
    verify_visibility = focus.get("visibility") or {}
    fpv_grounded = _focus_visibility_is_grounded(fpv_visibility, focus)
    verify_grounded = _focus_visibility_is_grounded(verify_visibility, focus)
    return fpv_grounded and not verify_grounded


def _focus_visibility_is_grounded(
    visibility: dict[str, Any],
    focus: dict[str, Any],
) -> bool:
    status = visibility.get("status")
    if status == "contained_inside":
        return True
    if status != "ok":
        return False
    if not (focus.get("object_id") or focus.get("object_body_name") or focus.get("object_label")):
        return True
    return int(visibility.get("object_pixels") or 0) > 0


def _visual_grounding_status(focus: dict[str, Any], visibility: dict[str, Any]) -> str:
    receptacle_id = focus.get("receptacle_id")
    if (
        receptacle_id
        and focus.get("object_contained_in") == receptacle_id
        and focus.get("object_location_relation") == "inside"
        and _focus_receptacle_can_hide_contents(focus)
    ):
        return "contained_inside"
    if not (focus.get("object_id") or focus.get("object_body_name") or focus.get("object_label")):
        return "ok"
    return "ok" if int(visibility.get("object_pixels") or 0) > 0 else "weak_object_visibility"


def _focus_receptacle_can_hide_contents(focus: dict[str, Any]) -> bool:
    text = f"{focus.get('receptacle_label', '')} {focus.get('receptacle_category', '')}".lower()
    return "fridge" in text or "refrigerator" in text


def _render_segmentation(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Any:
    width, height = _render_dimensions(width, height)
    _ensure_offscreen_framebuffer(model, width=width, height=height)
    renderer = mujoco.Renderer(model, height=height, width=width, max_geom=20000)
    renderer.update_scene(data, camera=camera)
    renderer.render()
    renderer.enable_segmentation_rendering()
    renderer.update_scene(data, camera=camera)
    segmentation = _normalize_renderer_frame(renderer.render())
    renderer.close()
    return segmentation


def _segmentation_box(
    model: mujoco.MjModel,
    segmentation: Any,
    body_name: str,
    *,
    label: str,
    color: list[int],
) -> dict[str, Any] | None:
    geom_ids = _subtree_geom_ids(model, body_name)
    if not geom_ids:
        return None
    import numpy as np

    mask = np.isin(segmentation[:, :, 0], geom_ids) & (
        segmentation[:, :, 1] == int(mujoco.mjtObj.mjOBJ_GEOM)
    )
    pixels = int(mask.sum())
    if pixels <= 0:
        return None
    ys, xs = np.where(mask)
    left, right = int(xs.min()), int(xs.max())
    top, bottom = int(ys.min()), int(ys.max())
    left, top, right, bottom = _inflate_bbox(left, top, right, bottom, segmentation.shape)
    return {
        "label": label,
        "bbox": [left, top, right, bottom],
        "pixels": pixels,
        "color": color,
        "source": "segmentation",
    }


def _highlight_diff_box(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
    body_name: str,
    *,
    label: str,
    color: list[int],
    frame: Any | None,
) -> dict[str, Any] | None:
    geom_ids = _subtree_geom_ids(model, body_name)
    if not geom_ids:
        return None
    import numpy as np

    render_shape = frame.shape if frame is not None and hasattr(frame, "shape") else None
    baseline = frame if frame is not None else _render_color_frame(model, data, camera)
    baseline = np.asarray(baseline)
    previous_rgba = model.geom_rgba[geom_ids].copy()
    previous_matid = model.geom_matid[geom_ids].copy()
    try:
        for geom_id in geom_ids:
            model.geom_rgba[geom_id] = np.array([1.0, 0.0, 1.0, 1.0])
            model.geom_matid[geom_id] = -1
        highlighted = _render_color_frame(
            model,
            data,
            camera,
            width=_shape_width(render_shape or baseline.shape),
            height=_shape_height(render_shape or baseline.shape),
        )
    finally:
        model.geom_rgba[geom_ids] = previous_rgba
        model.geom_matid[geom_ids] = previous_matid
    diff = np.abs(np.asarray(highlighted, dtype=np.int16) - baseline.astype(np.int16)).max(axis=2)
    mask = diff > 35
    pixels = int(mask.sum())
    if pixels <= 0:
        return None
    ys, xs = np.where(mask)
    left, right = int(xs.min()), int(xs.max())
    top, bottom = int(ys.min()), int(ys.max())
    left, top, right, bottom = _inflate_bbox(left, top, right, bottom, baseline.shape)
    return {
        "label": label,
        "bbox": [left, top, right, bottom],
        "pixels": pixels,
        "color": color,
        "source": "highlight_diff",
    }


def _render_color_frame(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Any:
    width, height = _render_dimensions(width, height)
    _ensure_offscreen_framebuffer(model, width=width, height=height)
    renderer = mujoco.Renderer(model, height=height, width=width, max_geom=20000)
    renderer.update_scene(data, camera=camera)
    frame = _normalize_renderer_frame(renderer.render())
    renderer.close()
    return frame


def _ensure_offscreen_framebuffer(
    model: mujoco.MjModel,
    *,
    width: int,
    height: int,
) -> None:
    """Grow MuJoCo's offscreen buffer so requested high-res renders are valid."""
    global_settings = getattr(getattr(model, "vis", None), "global_", None)
    if global_settings is None:
        return
    if int(getattr(global_settings, "offwidth", 0) or 0) < int(width):
        global_settings.offwidth = int(width)
    if int(getattr(global_settings, "offheight", 0) or 0) < int(height):
        global_settings.offheight = int(height)


def _subtree_geom_ids(model: mujoco.MjModel, body_name: str) -> list[int]:
    body_ids = _subtree_body_ids(model, body_name)
    return [
        geom_id
        for geom_id in range(model.ngeom)
        if int(model.geom_bodyid[geom_id]) in set(body_ids)
    ]


def _subtree_body_ids(model: mujoco.MjModel, body_name: str) -> list[int]:
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if body_id < 0:
        return []
    body_ids = []
    for candidate_id in range(model.nbody):
        current_id = candidate_id
        while current_id > 0:
            if current_id == body_id:
                body_ids.append(candidate_id)
                break
            current_id = int(model.body_parentid[current_id])
    return body_ids


def _inflate_bbox(
    left: int,
    top: int,
    right: int,
    bottom: int,
    shape: Any,
    *,
    min_size: int = 32,
    pad: int = 8,
) -> tuple[int, int, int, int]:
    height, width = int(shape[0]), int(shape[1])
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    half_width = max((right - left) // 2 + pad, min_size // 2)
    half_height = max((bottom - top) // 2 + pad, min_size // 2)
    return (
        max(0, center_x - half_width),
        max(29, center_y - half_height),
        min(width - 1, center_x + half_width),
        min(height - 1, center_y + half_height),
    )


def _render_robot_map(state: dict[str, Any], *, focus: dict[str, Any] | None = None) -> Image.Image:
    width, height = 620, 420
    margin = 34
    image = Image.new("RGB", (width, height), (247, 248, 250))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, width - 12, height - 12), outline=(187, 193, 204), width=2)

    focus = focus or {}
    points = _map_points(state, focus)
    min_x, max_x, min_y, max_y = _map_bounds(points)

    def project(x: float, y: float) -> tuple[int, int]:
        px = margin + (x - min_x) / max(max_x - min_x, 0.001) * (width - 2 * margin)
        py = height - margin - (y - min_y) / max(max_y - min_y, 0.001) * (height - 2 * margin)
        return (int(round(px)), int(round(py)))

    for outline in state.get("room_outlines", []):
        center = outline["center"]
        half_x, half_y = outline["half_extents"]
        x1, y1 = project(float(center[0]) - float(half_x), float(center[1]) - float(half_y))
        x2, y2 = project(float(center[0]) + float(half_x), float(center[1]) + float(half_y))
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        draw.rectangle((left, top, right, bottom), outline=(148, 163, 184), width=2)
        draw.text((left + 5, top + 5), str(outline.get("label", "room")), fill=(71, 85, 105))

    focus_receptacle_id = focus.get("receptacle_id")
    focus_object_id = focus.get("object_id")
    if focus_receptacle_id in state["receptacles"]:
        receptacle = state["receptacles"][focus_receptacle_id]
        x, y = project(float(receptacle["position"][0]), float(receptacle["position"][1]))
        draw.rounded_rectangle(
            (x - 13, y - 13, x + 13, y + 13),
            radius=5,
            outline=(8, 145, 178),
            width=4,
        )
        draw.text(
            (x + 10, y - 20),
            _item_label(receptacle, "receptacle_id"),
            fill=(8, 92, 116),
        )

    for receptacle in state["receptacles"].values():
        x, y = project(float(receptacle["position"][0]), float(receptacle["position"][1]))
        draw.rounded_rectangle((x - 5, y - 5, x + 5, y + 5), radius=2, fill=(99, 116, 139))

    for object_id in state["selected_object_ids"]:
        obj = state["objects"][object_id]
        x, y = project(float(obj["position"][0]), float(obj["position"][1]))
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(192, 88, 68))
        if object_id == focus_object_id:
            draw.ellipse((x - 11, y - 11, x + 11, y + 11), outline=(220, 38, 38), width=4)
            draw.text((x + 10, y + 4), _item_label(obj, "object_id"), fill=(153, 27, 27))

    trajectory = state.get("robot_trajectory", [])
    projected_path = [project(float(pose["x"]), float(pose["y"])) for pose in trajectory]
    if len(projected_path) >= 2:
        draw.line(projected_path, fill=(37, 99, 235), width=3)
    for index, (x, y) in enumerate(projected_path):
        radius = 5 if index == len(projected_path) - 1 else 3
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(37, 99, 235))
    if trajectory:
        pose = trajectory[-1]
        x, y = projected_path[-1]
        heading = float(pose["theta"])
        tip = (int(round(x + math.cos(heading) * 18)), int(round(y - math.sin(heading) * 18)))
        left = (
            int(round(x + math.cos(heading + 2.45) * 10)),
            int(round(y - math.sin(heading + 2.45) * 10)),
        )
        right = (
            int(round(x + math.cos(heading - 2.45) * 10)),
            int(round(y - math.sin(heading - 2.45) * 10)),
        )
        draw.polygon([tip, left, right], fill=(15, 23, 42))

    draw.text((24, 22), "RBY1M map", fill=(31, 41, 55))
    draw.text(
        (24, height - 30),
        "blue: robot path  gray: receptacles  red: objects  cyan/red rings: focus",
        fill=(75, 85, 99),
    )
    return image


def _map_points(state: dict[str, Any], focus: dict[str, Any]) -> list[list[float]]:
    points = [item["position"] for item in state["receptacles"].values()]
    points += [state["objects"][oid]["position"] for oid in state["selected_object_ids"]]
    points += [[pose["x"], pose["y"], 0.0] for pose in state.get("robot_trajectory", [])]
    if focus.get("focus_position"):
        points.append(focus["focus_position"])
    for outline in state.get("room_outlines", []):
        center = outline["center"]
        half_x, half_y = outline["half_extents"]
        points.extend(
            [
                [float(center[0]) - float(half_x), float(center[1]) - float(half_y), 0.0],
                [float(center[0]) + float(half_x), float(center[1]) + float(half_y), 0.0],
            ]
        )
    return points


def _room_relation_payload(
    state: dict[str, Any],
    receptacle: dict[str, Any],
    robot_point: list[float],
) -> dict[str, Any]:
    target_room_id = _target_room_id(state, receptacle)
    robot_room_id = _room_for_point(state, robot_point)
    same_room = robot_room_id == target_room_id
    return {
        "target_room_id": target_room_id,
        "same_room_as_target": same_room,
        "room_relation_source": "mujoco_room_outline",
        "room_plausibility": "same_room" if same_room else "room_mismatch",
    }


def _target_room_id(state: dict[str, Any], receptacle: dict[str, Any]) -> str:
    return _room_for_point(state, receptacle["position"]) or str(
        receptacle.get("room_area") or "room_unknown"
    )


def _room_outline_for_id(
    state: dict[str, Any],
    room_id: Any,
) -> dict[str, Any] | None:
    if room_id is None:
        return None
    for outline in state.get("room_outlines", []):
        if str(outline.get("room_id") or "") == str(room_id):
            return outline
    return None


def _room_for_point(state: dict[str, Any], point: list[float]) -> str | None:
    return room_for_point(state.get("room_outlines") or [], point)


def _point_inside_outline(
    point: list[float],
    outline: dict[str, Any],
    *,
    margin: float,
) -> bool:
    return point_inside_room_outline(point, outline, margin=margin)


def _outline_clearance(point: list[float], outline: dict[str, Any] | None) -> float:
    return room_outline_clearance(point, outline)


def _angle_delta(a: float, b: float) -> float:
    return angle_delta(a, b)


def _collect_room_outlines(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    outlines: list[dict[str, Any]] = []
    seen: set[str] = set()
    for geom_id in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
        if name is None:
            continue
        match = re.match(r"^(room_\d+)_visual", name)
        if match is None:
            continue
        room_id = match.group(1)
        if room_id in seen:
            continue
        bounds = _geom_xy_bounds(model, data, geom_id)
        if bounds is None:
            continue
        min_xy, max_xy = bounds
        half_extents = [
            (float(max_xy[0]) - float(min_xy[0])) / 2.0,
            (float(max_xy[1]) - float(min_xy[1])) / 2.0,
        ]
        if min(half_extents) < 0.25:
            continue
        center = [
            (float(min_xy[0]) + float(max_xy[0])) / 2.0,
            (float(min_xy[1]) + float(max_xy[1])) / 2.0,
        ]
        outlines.append(
            {
                "room_id": room_id,
                "label": room_id.replace("_", " ").title(),
                "center": [round(center[0], 6), round(center[1], 6)],
                "half_extents": [round(half_extents[0], 6), round(half_extents[1], 6)],
                "provenance": "mujoco_room_mesh_world_bounds",
            }
        )
        seen.add(room_id)
    if outlines:
        return sorted(outlines, key=lambda item: item["room_id"])
    return _fallback_room_outlines(state)


def _geom_xy_bounds(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    geom_id: int,
) -> tuple[list[float], list[float]] | None:
    geom_type = int(model.geom_type[geom_id])
    if geom_type == int(mujoco.mjtGeom.mjGEOM_MESH):
        mesh_id = int(model.geom_dataid[geom_id])
        if mesh_id < 0:
            return None
        vertex_start = int(model.mesh_vertadr[mesh_id])
        vertex_count = int(model.mesh_vertnum[mesh_id])
        if vertex_count <= 0:
            return None
        vertices = model.mesh_vert[vertex_start : vertex_start + vertex_count]
        matrix = data.geom_xmat[geom_id].reshape(3, 3)
        position = data.geom_xpos[geom_id]
        world_vertices = vertices @ matrix.T + position
        min_xy = [float(world_vertices[:, 0].min()), float(world_vertices[:, 1].min())]
        max_xy = [float(world_vertices[:, 0].max()), float(world_vertices[:, 1].max())]
        return min_xy, max_xy

    center = _xyz(data.geom_xpos[geom_id])
    size = [float(value) for value in model.geom_size[geom_id]]
    radius_x = abs(size[0]) if size else 0.0
    radius_y = abs(size[1]) if len(size) > 1 else radius_x
    return [center[0] - radius_x, center[1] - radius_y], [
        center[0] + radius_x,
        center[1] + radius_y,
    ]


def _fallback_room_outlines(state: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[list[float]]] = {}
    for receptacle in state["receptacles"].values():
        grouped.setdefault(str(receptacle.get("room_area", "room_unknown")), []).append(
            receptacle["position"]
        )
    for obj in state["objects"].values():
        location_id = obj.get("seeded_start_receptacle_id") or obj.get("target_receptacle_id")
        receptacle = state["receptacles"].get(location_id)
        if receptacle is None:
            continue
        grouped.setdefault(str(receptacle.get("room_area", "room_unknown")), []).append(
            obj["position"]
        )
    outlines = []
    for room_id, points in grouped.items():
        if not points:
            continue
        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
        center = [round((min(xs) + max(xs)) / 2.0, 6), round((min(ys) + max(ys)) / 2.0, 6)]
        half_extents = [
            round(max((max(xs) - min(xs)) / 2.0, 0.8), 6),
            round(max((max(ys) - min(ys)) / 2.0, 0.8), 6),
        ]
        outlines.append(
            {
                "room_id": room_id,
                "label": room_id.replace("_", " ").title(),
                "center": center,
                "half_extents": half_extents,
                "provenance": "public_object_room_area_bounds",
            }
        )
    return sorted(outlines, key=lambda item: item["room_id"])


def _map_bounds(points: list[list[float]]) -> tuple[float, float, float, float]:
    if not points:
        return (0.0, 1.0, 0.0, 1.0)
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    pad = 0.8
    return (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)


def _apply_qpos(data: mujoco.MjData, qpos: list[float]) -> None:
    data.qpos[:] = qpos


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _json_object_from_text(text: str) -> dict[str, Any]:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("expected JSON object")
    return payload


def _render_dimensions(width: int, height: int) -> tuple[int, int]:
    return (
        _positive_int(width, DEFAULT_RENDER_WIDTH),
        _positive_int(height, DEFAULT_RENDER_HEIGHT),
    )


def _shape_width(shape: Any) -> int:
    if isinstance(shape, (tuple, list)) and len(shape) >= 2:
        return _positive_int(shape[1], DEFAULT_RENDER_WIDTH)
    return DEFAULT_RENDER_WIDTH


def _shape_height(shape: Any) -> int:
    if isinstance(shape, (tuple, list)) and len(shape) >= 1:
        return _positive_int(shape[0], DEFAULT_RENDER_HEIGHT)
    return DEFAULT_RENDER_HEIGHT


def _primary_body_name(info: dict[str, Any], *, fallback: str) -> str:
    bodies = info.get("name_map", {}).get("bodies", {})
    return next(iter(bodies), fallback)


def _friendly_name(category: str, upstream_id: Any) -> str:
    return f"{category} ({upstream_id})"


def _xyz(values: Any) -> list[float]:
    return [round(float(values[0]), 6), round(float(values[1]), 6), round(float(values[2]), 6)]


def _read_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(path: Path, state: dict[str, Any]) -> None:
    _refresh_runtime_render_state(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _count(state: dict[str, Any], tool: str) -> None:
    counts = state.setdefault("tool_event_counts", {})
    key = f"{tool}:request"
    counts[key] = int(counts.get(key, 0)) + 1


def _ok(tool: str, **payload: Any) -> dict[str, Any]:
    return {"ok": True, "tool": tool, "status": "ok", **payload}


def _error(tool: str, error_reason: str, **payload: Any) -> dict[str, Any]:
    return {"ok": False, "tool": tool, "status": "error", "error_reason": error_reason, **payload}


if __name__ == "__main__":
    main()
