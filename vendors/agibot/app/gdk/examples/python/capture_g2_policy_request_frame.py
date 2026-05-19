#!/usr/bin/env python3
"""Capture one live robot frame as a G2 policy websocket request directory.

The output layout matches examples/step_0000:

step_0000/
  prompt.txt
  state.npy      # gripper-adjusted model input
  state_ori.npy  # original robot observation state
  head_color.jpg
  hand_left_color.jpg
  hand_right_color.jpg
  meta.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from robot_observation_collector import RobotObservationCollector
from robot_observation_collector import _ensure_gdk


CAMERA_NAMES = ["head_color", "hand_left_color", "hand_right_color"]
STATE_DIM = 26
DEFAULT_OUTPUT_ROOT = Path(__file__).resolve().parents[2] / "g2_requests"
DEFAULT_OUTPUT_DIR = DEFAULT_OUTPUT_ROOT / "current"
DEFAULT_PROMPT = (
    "Phase: grasp. Mode: single_arm. Active hand: right_hand. "
    "Target: Coca-Cola. Grasp the Coca-Cola with the right hand."
)
DEFAULT_RAW_GRIPPER_MIN = -0.91
DEFAULT_RAW_GRIPPER_MAX = 0.0
DEFAULT_MACHINE_GRIPPER_MIN = -0.785
DEFAULT_MACHINE_GRIPPER_MAX = 0.0


def _load_default_prompt() -> str:
    return DEFAULT_PROMPT


def _build_state_vectors(
    observation: dict[str, Any],
    args: argparse.Namespace,
) -> tuple[np.ndarray, np.ndarray]:
    """Build gripper-adjusted and original 26-D G2 policy state vectors."""
    robot_position = observation["robot_position"]
    arm_ori = np.asarray(robot_position["arm_joint_position"], dtype=np.float32).reshape(14)
    gripper_ori = np.asarray(observation["gripper_position"], dtype=np.float32).reshape(2)
    waist = np.asarray(robot_position["waist_joint_position"], dtype=np.float32).reshape(5)

    slam_pose = observation.get("slam_pose") or {}
    position = np.asarray(slam_pose.get("position", [0.0, 0.0, 0.0]), dtype=np.float32).reshape(3)
    orientation = np.asarray(
        slam_pose.get("orientation", [0.0, 0.0, 0.0, 1.0]),
        dtype=np.float32,
    ).reshape(4)

    state_ori = _pack_state_vector(arm_ori, gripper_ori, waist, position, orientation)

    arm = arm_ori.copy()
    gripper = gripper_ori.copy()
    if not args.no_reverse_gripper:
        gripper[0] = _reverse_gripper_value(
            float(gripper[0]),
            raw_min=args.raw_gripper_min,
            raw_max=args.raw_gripper_max,
            machine_min=args.machine_gripper_min,
            machine_max=args.machine_gripper_max,
        )
        gripper[1] = _reverse_gripper_value(
            float(gripper[1]),
            raw_min=args.raw_gripper_min,
            raw_max=args.raw_gripper_max,
            machine_min=args.machine_gripper_min,
            machine_max=args.machine_gripper_max,
        )

    state = _pack_state_vector(arm, gripper, waist, position, orientation)
    return state, state_ori


def _pack_state_vector(
    arm: np.ndarray,
    gripper: np.ndarray,
    waist: np.ndarray,
    position: np.ndarray,
    orientation: np.ndarray,
) -> np.ndarray:
    state = np.concatenate(
        [
            arm[:7],
            gripper[:1],
            arm[7:14],
            gripper[1:2],
            waist,
            position,
            orientation[2:4],
        ]
    )
    if state.shape != (STATE_DIM,):
        raise RuntimeError(f"state shape {state.shape} != ({STATE_DIM},)")
    return state.astype(np.float32, copy=False)


def _reverse_gripper_value(
    value: float,
    *,
    raw_min: float,
    raw_max: float,
    machine_min: float,
    machine_max: float,
) -> float:
    clipped = _clamp(value, machine_min, machine_max)
    unflipped = machine_min + machine_max - clipped
    raw = _scale(
        unflipped,
        input_min=machine_min,
        input_max=machine_max,
        output_min=raw_min,
        output_max=raw_max,
    )
    return _clamp(raw, raw_min, raw_max)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _scale(
    value: float,
    *,
    input_min: float,
    input_max: float,
    output_min: float,
    output_max: float,
) -> float:
    ratio = (value - input_min) / (input_max - input_min)
    return output_min + ratio * (output_max - output_min)


def _next_step_dir(output_root: Path) -> Path:
    output_root.mkdir(parents=True, exist_ok=True)
    used: set[int] = set()
    for path in output_root.iterdir():
        if not path.is_dir() or not path.name.startswith("step_"):
            continue
        suffix = path.name.removeprefix("step_")
        if suffix.isdigit():
            used.add(int(suffix))
    index = 0
    while index in used:
        index += 1
    return output_root / f"step_{index:04d}"


def _write_camera_jpgs(observation: dict[str, Any], output_dir: Path) -> dict[str, str]:
    cameras = observation.get("camera") or {}
    image_paths: dict[str, str] = {}
    missing = [name for name in CAMERA_NAMES if name not in cameras]
    if missing:
        raise RuntimeError(f"missing required camera(s): {', '.join(missing)}")

    for name in CAMERA_NAMES:
        camera = cameras[name]
        encoding = str(camera.get("encoding") or "").upper()
        if encoding != "JPEG":
            raise RuntimeError(f"camera {name} must be JPEG after collection, got {encoding!r}")
        filename = f"{name}.jpg"
        path = output_dir / filename
        path.write_bytes(_bytes_from_camera_data(camera.get("data")))
        image_paths[name] = filename
    return image_paths


def _bytes_from_camera_data(data: Any) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    if hasattr(data, "tobytes"):
        return data.tobytes()
    return bytes(data)


def _observation_summary(observation: dict[str, Any]) -> dict[str, Any]:
    robot_position = observation.get("robot_position") or {}
    cameras = observation.get("camera") or {}
    return {
        "timestamp": observation.get("timestamp"),
        "arm_joint_len": len(robot_position.get("arm_joint_position") or []),
        "head_joint_len": len(robot_position.get("head_joint_position") or []),
        "waist_joint_len": len(robot_position.get("waist_joint_position") or []),
        "gripper_position": observation.get("gripper_position"),
        "slam_pose_available": observation.get("slam_pose") is not None,
        "cameras": {
            name: {
                "width": camera.get("width"),
                "height": camera.get("height"),
                "timestamp_ns": camera.get("timestamp_ns"),
                "encoding": camera.get("encoding"),
                "color_format": camera.get("color_format"),
                "bytes": len(_bytes_from_camera_data(camera.get("data"))),
            }
            for name, camera in cameras.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture one robot observation as a G2 websocket policy request directory.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help=f"Directory that will contain step_XXXX folders. Default: {DEFAULT_OUTPUT_ROOT}",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=(
            "Exact output directory. If omitted, writes the reusable current request "
            f"directory: {DEFAULT_OUTPUT_DIR}"
        ),
    )
    parser.add_argument("--prompt", help="Prompt text to write to prompt.txt.")
    parser.add_argument("--prompt-file", help="Read prompt text from this file.")
    parser.add_argument("--camera-config", help="Optional GDK camera config path.")
    parser.add_argument("--timeout-ms", type=float, default=100.0, help="Camera image timeout.")
    parser.add_argument("--init-wait-s", type=float, default=2.0, help="DDS/camera warm-up wait.")
    parser.add_argument(
        "--raw-gripper-min",
        type=float,
        default=DEFAULT_RAW_GRIPPER_MIN,
        help="Raw gripper minimum after reverse conversion. Default: -0.91.",
    )
    parser.add_argument(
        "--raw-gripper-max",
        type=float,
        default=DEFAULT_RAW_GRIPPER_MAX,
        help="Raw gripper maximum after reverse conversion. Default: 0.0.",
    )
    parser.add_argument(
        "--machine-gripper-min",
        type=float,
        default=DEFAULT_MACHINE_GRIPPER_MIN,
        help="Machine gripper minimum before reverse conversion. Default: -0.785.",
    )
    parser.add_argument(
        "--machine-gripper-max",
        type=float,
        default=DEFAULT_MACHINE_GRIPPER_MAX,
        help="Machine gripper maximum before reverse conversion. Default: 0.0.",
    )
    parser.add_argument(
        "--no-reverse-gripper",
        action="store_true",
        help="Do not reverse gripper values in state.npy.",
    )
    parser.add_argument(
        "--sync-camera",
        action="store_true",
        help="Use nearest camera frame to robot timestamp instead of latest frame.",
    )
    parser.add_argument("--strict", action="store_true", help="Raise on any missing sub-signal.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Remove --output-dir first if it already exists.",
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce status logs.")
    return parser.parse_args()


def _resolve_prompt(args: argparse.Namespace) -> str:
    if args.prompt_file:
        return Path(args.prompt_file).read_text(encoding="utf-8").strip()
    if args.prompt:
        return str(args.prompt).strip()
    return _load_default_prompt()


def _prepare_output_dir(args: argparse.Namespace) -> Path:
    if args.output_dir:
        output_dir = Path(args.output_dir).expanduser().resolve()
        if output_dir.exists():
            if args.overwrite:
                shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir
    output_dir = _next_step_dir(Path(args.output_root).expanduser().resolve())
    output_dir.mkdir(parents=True)
    return output_dir


def main() -> int:
    args = parse_args()
    if args.raw_gripper_min >= args.raw_gripper_max:
        print("--raw-gripper-min must be < --raw-gripper-max", file=sys.stderr)
        return 2
    if args.machine_gripper_min >= args.machine_gripper_max:
        print("--machine-gripper-min must be < --machine-gripper-max", file=sys.stderr)
        return 2

    prompt = _resolve_prompt(args)
    output_dir = _prepare_output_dir(args)

    gdk = _ensure_gdk()
    if gdk.gdk_init() != gdk.GDKRes.kSuccess:
        print("failed to initialize GDK", file=sys.stderr)
        return 1

    collector: RobotObservationCollector | None = None
    try:
        collector = RobotObservationCollector(
            CAMERA_NAMES,
            image_timeout_ms=args.timeout_ms,
            init_wait_s=args.init_wait_s,
            camera_config=args.camera_config,
            include_cameras=True,
            strict=args.strict,
            sync_cameras_to_robot_timestamp=args.sync_camera,
            log_status=not args.quiet,
        )
        observation = collector.collect()
        state, state_ori = _build_state_vectors(observation, args)
        image_paths = _write_camera_jpgs(observation, output_dir)

        np.save(output_dir / "state.npy", state)
        np.save(output_dir / "state_ori.npy", state_ori)
        (output_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

        meta = {
            "created_at_ns": time.time_ns(),
            "prompt": prompt,
            "state_path": "state.npy",
            "state_ori_path": "state_ori.npy",
            "image_paths": image_paths,
            "observation_summary": _observation_summary(observation),
            "source": "live_robot_observation",
            "camera_names": CAMERA_NAMES,
            "state_transform": {
                "state.npy": "gripper_reverse_adjusted",
                "state_ori.npy": "original_robot_observation",
                "reverse_gripper": not args.no_reverse_gripper,
                "raw_gripper_range": [args.raw_gripper_min, args.raw_gripper_max],
                "machine_gripper_range": [
                    args.machine_gripper_min,
                    args.machine_gripper_max,
                ],
            },
            "state_layout": {
                "0_6": "left arm joints",
                "7": "left gripper",
                "8_14": "right arm joints",
                "15": "right gripper",
                "16_20": "waist joints",
                "21_23": "slam position xyz",
                "24_25": "slam orientation z,w",
            },
        }
        (output_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        print(str(output_dir))
        if not args.quiet:
            print(f"saved request directory: {output_dir}", file=sys.stderr)
            print(f"state shape={state.shape} dtype={state.dtype}", file=sys.stderr)
            print(f"state_ori shape={state_ori.shape} dtype={state_ori.dtype}", file=sys.stderr)
            for name, filename in image_paths.items():
                print(f"image {name}: {output_dir / filename}", file=sys.stderr)
        return 0
    finally:
        if collector is not None:
            collector.close()
        if gdk.gdk_release() != gdk.GDKRes.kSuccess:
            print("failed to release GDK", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
