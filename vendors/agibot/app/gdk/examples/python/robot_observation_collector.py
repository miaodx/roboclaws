#!/usr/bin/env python3
"""Collect one robot observation in a Python dict with raw image bytes.

The returned dict follows this shape:

{
    "timestamp": int,
    "robot_position": {
        "arm_joint_position": list[float],   # left arm 7 + right arm 7
        "head_joint_position": list[float],  # 3
        "waist_joint_position": list[float], # 5
        "left_end_position": list[float],    # metres, base_link frame
        "left_end_orientation": list[float], # [x, y, z, w]
        "right_end_position": list[float],
        "right_end_orientation": list[float],
    },
    "camera": {
        "<camera_name>": {
            "width": int,
            "height": int,
            "timestamp_ns": int,
            "data": bytes,
            "encoding": str,
            "color_format": str,
        }
    },
    "gripper_position": list[float],         # [left, right]
    "slam_pose": dict | None,
}
"""

from __future__ import annotations

import argparse
import math
import pickle
import sys
import time
from pathlib import Path
from typing import Any, Iterable

from robot_observation_viewer import RobotObservationWebViewer

agibot_gdk: Any | None = None


WAIST_JOINT_NAMES = [
    "idx01_body_joint1",
    "idx02_body_joint2",
    "idx03_body_joint3",
    "idx04_body_joint4",
    "idx05_body_joint5",
]

HEAD_JOINT_NAMES = [
    "idx11_head_joint1",
    "idx12_head_joint2",
    "idx13_head_joint3",
]

LEFT_ARM_JOINT_NAMES = [
    "idx21_arm_l_joint1",
    "idx22_arm_l_joint2",
    "idx23_arm_l_joint3",
    "idx24_arm_l_joint4",
    "idx25_arm_l_joint5",
    "idx26_arm_l_joint6",
    "idx27_arm_l_joint7",
]

RIGHT_ARM_JOINT_NAMES = [
    "idx61_arm_r_joint1",
    "idx62_arm_r_joint2",
    "idx63_arm_r_joint3",
    "idx64_arm_r_joint4",
    "idx65_arm_r_joint5",
    "idx66_arm_r_joint6",
    "idx67_arm_r_joint7",
]

ARM_JOINT_NAMES = LEFT_ARM_JOINT_NAMES + RIGHT_ARM_JOINT_NAMES

DEFAULT_CAMERA_NAMES = [
    "head_stereo_left",
    "head_stereo_right",
    "hand_left_color",
    "hand_right_color",
    "head_depth",
    "head_color",
]

DEFAULT_HZ = 30.0
DEFAULT_IMAGE_TIMEOUT_MS = 34.0
DEFAULT_INIT_WAIT_S = 2.0
DEFAULT_SAMPLE_COUNT = 1

CAMERA_NAME_CHOICES = [
    "head_back_fisheye",
    "head_left_fisheye",
    "head_right_fisheye",
    "head_stereo_left",
    "head_stereo_right",
    "hand_left_color",
    "hand_right_color",
    "head_color",
    "head_depth",
    "hand_left_depth",
    "hand_right_depth",
    "hand_left_upper_color",
    "hand_right_upper_color",
    "hand_left_lower_color",
    "hand_right_lower_color",
    "hand_left_upper_depth",
    "hand_right_upper_depth",
    "hand_left_lower_depth",
    "hand_right_lower_depth",
]


def _ensure_gdk() -> Any:
    global agibot_gdk
    if agibot_gdk is None:
        import agibot_gdk as loaded_gdk

        agibot_gdk = loaded_gdk
    return agibot_gdk


def _camera_name_to_type() -> dict[str, Any]:
    gdk = _ensure_gdk()
    return {
        "head_back_fisheye": gdk.CameraType.kHeadBackFisheye,
        "head_left_fisheye": gdk.CameraType.kHeadLeftFisheye,
        "head_right_fisheye": gdk.CameraType.kHeadRightFisheye,
        "head_stereo_left": gdk.CameraType.kHeadStereoLeft,
        "head_stereo_right": gdk.CameraType.kHeadStereoRight,
        "hand_left_color": gdk.CameraType.kHandLeftColor,
        "hand_right_color": gdk.CameraType.kHandRightColor,
        "head_color": gdk.CameraType.kHeadColor,
        "head_depth": gdk.CameraType.kHeadDepth,
        "hand_left_depth": gdk.CameraType.kHandLeftDepth,
        "hand_right_depth": gdk.CameraType.kHandRightDepth,
        "hand_left_upper_color": gdk.CameraType.kHandLeftUpperColor,
        "hand_right_upper_color": gdk.CameraType.kHandRightUpperColor,
        "hand_left_lower_color": gdk.CameraType.kHandLeftLowerColor,
        "hand_right_lower_color": gdk.CameraType.kHandRightLowerColor,
        "hand_left_upper_depth": gdk.CameraType.kHandLeftUpperDepth,
        "hand_right_upper_depth": gdk.CameraType.kHandRightUpperDepth,
        "hand_left_lower_depth": gdk.CameraType.kHandLeftLowerDepth,
        "hand_right_lower_depth": gdk.CameraType.kHandRightLowerDepth,
    }


def _warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def _status_line(ok: bool, name: str, detail: str) -> None:
    state = "OK" if ok else "FAIL"
    print(f"[{state}] {name}: {detail}", file=sys.stderr)


def _enum_name(value: Any) -> str:
    name = getattr(value, "name", None)
    if name:
        return str(name)
    text = str(value)
    return text.rsplit(".", 1)[-1]


def _vector3_to_list(vector: Any) -> list[float]:
    return [float(vector.x), float(vector.y), float(vector.z)]


def _quat_to_list(quat: Any) -> list[float]:
    return [float(quat.x), float(quat.y), float(quat.z), float(quat.w)]


def _pose_to_dict(pose: Any) -> dict[str, list[float]]:
    return {
        "position": _vector3_to_list(pose.position),
        "orientation": _quat_to_list(pose.orientation),
    }


def _transform_to_pose_lists(transform: Any) -> tuple[list[float], list[float]]:
    return _vector3_to_list(transform.translation), _quat_to_list(transform.rotation)


def _empty_pose_lists() -> tuple[list[float], list[float]]:
    return [math.nan, math.nan, math.nan], [math.nan, math.nan, math.nan, math.nan]


def _finite_count(values: Iterable[float]) -> int:
    return sum(1 for value in values if math.isfinite(value))


def _image_bytes(image: Any) -> bytes:
    data = image.data
    if hasattr(data, "tobytes"):
        return data.tobytes()
    return bytes(data)


def _is_depth_camera(camera_name: str) -> bool:
    return "depth" in camera_name.lower()


def _color_image_to_jpeg_bytes(image: Any, raw_data: bytes) -> bytes:
    if _enum_name(image.encoding) == "JPEG":
        return raw_data

    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise RuntimeError(
            "color image is not JPEG and cv2/numpy are required to encode it"
        ) from exc

    encoding = _enum_name(image.encoding)
    color_format = _enum_name(image.color_format)
    width = int(image.width)
    height = int(image.height)

    if encoding in ("JPEG", "PNG"):
        encoded = np.frombuffer(raw_data, dtype=np.uint8)
        bgr_image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if bgr_image is None:
            raise RuntimeError(f"failed to decode {encoding} image")
    elif encoding == "UNCOMPRESSED":
        if color_format == "RGB":
            rgb_image = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 3))
            bgr_image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
        elif color_format == "BGR":
            bgr_image = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 3))
        elif color_format == "RGBA":
            rgba_image = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 4))
            bgr_image = cv2.cvtColor(rgba_image, cv2.COLOR_RGBA2BGR)
        elif color_format == "BGRA":
            bgra_image = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 4))
            bgr_image = cv2.cvtColor(bgra_image, cv2.COLOR_BGRA2BGR)
        elif color_format == "GRAY8":
            bgr_image = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width))
        else:
            raise RuntimeError(
                f"unsupported uncompressed color image format: {color_format}"
            )
    else:
        raise RuntimeError(f"unsupported color image encoding: {encoding}")

    ok, jpeg = cv2.imencode(".jpg", bgr_image)
    if not ok:
        raise RuntimeError("failed to encode color image as JPEG")
    return jpeg.tobytes()


def _depth_image_to_z16_bytes(image: Any, raw_data: bytes) -> bytes:
    encoding = _enum_name(image.encoding)
    color_format = _enum_name(image.color_format)
    expected_size = int(image.width) * int(image.height) * 2

    if encoding != "UNCOMPRESSED":
        raise RuntimeError(f"depth image must be UNCOMPRESSED, got {encoding}")

    if color_format != "RS2_FORMAT_Z16":
        raise RuntimeError(f"depth image must be RS2_FORMAT_Z16, got {color_format}")

    if len(raw_data) != expected_size:
        raise RuntimeError(
            "depth image must be raw Z16 bytes "
            f"({expected_size} bytes), got format={color_format}, size={len(raw_data)}"
        )

    return raw_data


def _format_camera_image(camera_name: str, image: Any) -> dict[str, Any]:
    raw_data = _image_bytes(image)

    if _is_depth_camera(camera_name):
        return {
            "width": int(image.width),
            "height": int(image.height),
            "timestamp_ns": int(image.timestamp_ns),
            "data": _depth_image_to_z16_bytes(image, raw_data),
            "encoding": "UNCOMPRESSED",
            "color_format": "RS2_FORMAT_Z16",
        }

    return {
        "width": int(image.width),
        "height": int(image.height),
        "timestamp_ns": int(image.timestamp_ns),
        "data": _color_image_to_jpeg_bytes(image, raw_data),
        "encoding": "JPEG",
        "color_format": "RGB",
    }


class RobotObservationCollector:
    """Small wrapper around the GDK read-only state APIs."""

    def __init__(
        self,
        camera_names: Iterable[str] | None = None,
        *,
        image_timeout_ms: float = DEFAULT_IMAGE_TIMEOUT_MS,
        init_wait_s: float = DEFAULT_INIT_WAIT_S,
        camera_config: str | None = None,
        include_cameras: bool = True,
        strict: bool = False,
        sync_cameras_to_robot_timestamp: bool = False,
        base_frame: str = "base_link",
        log_status: bool = True,
    ) -> None:
        gdk = _ensure_gdk()
        self.image_timeout_ms = image_timeout_ms
        self.strict = strict
        self.sync_cameras_to_robot_timestamp = sync_cameras_to_robot_timestamp
        self.base_frame = base_frame
        self.log_status = log_status
        self.camera_name_to_type = _camera_name_to_type()

        selected_camera_names = list(camera_names or DEFAULT_CAMERA_NAMES)
        unknown = [name for name in selected_camera_names if name not in self.camera_name_to_type]
        if unknown:
            raise ValueError(f"unknown camera name(s): {', '.join(unknown)}")
        self.camera_names = selected_camera_names

        self.robot = gdk.Robot()
        self.tf = gdk.TF()
        self.slam = gdk.Slam()
        self.camera = gdk.Camera() if include_cameras else None

        time.sleep(init_wait_s)

        if camera_config and self.camera is not None:
            self.camera.set_dev_camera_config(camera_config)
            self._log_status(True, "camera_config", camera_config)

    def _log_status(self, ok: bool, name: str, detail: str) -> None:
        if self.log_status:
            _status_line(ok, name, detail)

    def close(self) -> None:
        if self.camera is not None:
            try:
                self.camera.close_camera()
            except Exception as exc:  # noqa: BLE001 - best-effort cleanup
                _warn(f"failed to close camera: {exc}")

    def show_web(
        self,
        *,
        host: str = "0.0.0.0",
        port: int = 5000,
        refresh_ms: int = 500,
    ) -> RobotObservationWebViewer:
        """Start a local web UI that calls this collector for fresh data."""
        viewer = RobotObservationWebViewer(
            self,
            host=host,
            port=port,
            refresh_ms=refresh_ms,
        )
        viewer.run()
        return viewer

    def collect(self) -> dict[str, Any]:
        joint_states = self.robot.get_joint_states()
        timestamp_ns = int(joint_states.get("timestamp") or time.time_ns())
        joint_by_name = {state["name"]: state for state in joint_states["states"]}
        self._log_status(
            True,
            "joint_states",
            f"timestamp={timestamp_ns} total={len(joint_by_name)}",
        )

        end_state = self.robot.get_end_state()
        self._log_status(
            True,
            "end_state",
            (
                f"left_motors={len(end_state.get('left_end_state', {}).get('end_states') or [])} "
                f"right_motors={len(end_state.get('right_end_state', {}).get('end_states') or [])}"
            ),
        )

        left_pos, left_quat = self._get_end_pose("arm_l_end_link")
        right_pos, right_quat = self._get_end_pose("arm_r_end_link")
        arm_joint_position = self._ordered_joint_positions(joint_by_name, ARM_JOINT_NAMES)
        head_joint_position = self._ordered_joint_positions(joint_by_name, HEAD_JOINT_NAMES)
        waist_joint_position = self._ordered_joint_positions(joint_by_name, WAIST_JOINT_NAMES)
        left_gripper = self._extract_gripper_position(end_state.get("left_end_state", {}), "left")
        right_gripper = self._extract_gripper_position(end_state.get("right_end_state", {}), "right")
        cameras = self._collect_cameras(timestamp_ns)
        slam_pose = self._get_slam_pose()

        self._log_vector_status("arm_joint_position", arm_joint_position, len(ARM_JOINT_NAMES))
        self._log_vector_status("head_joint_position", head_joint_position, len(HEAD_JOINT_NAMES))
        self._log_vector_status("waist_joint_position", waist_joint_position, len(WAIST_JOINT_NAMES))
        self._log_vector_status("left_end_position", left_pos, 3)
        self._log_vector_status("left_end_orientation", left_quat, 4)
        self._log_vector_status("right_end_position", right_pos, 3)
        self._log_vector_status("right_end_orientation", right_quat, 4)

        return {
            "timestamp": timestamp_ns,
            "robot_position": {
                "arm_joint_position": arm_joint_position,
                "head_joint_position": head_joint_position,
                "waist_joint_position": waist_joint_position,
                "left_end_position": left_pos,
                "left_end_orientation": left_quat,
                "right_end_position": right_pos,
                "right_end_orientation": right_quat,
            },
            "camera": cameras,
            "gripper_position": [left_gripper, right_gripper],
            "slam_pose": slam_pose,
        }

    def _log_vector_status(self, name: str, values: list[float], expected_len: int) -> None:
        valid = _finite_count(values)
        self._log_status(
            valid == expected_len and len(values) == expected_len,
            name,
            f"valid={valid}/{expected_len} len={len(values)}",
        )

    def _ordered_joint_positions(
        self,
        joint_by_name: dict[str, dict[str, Any]],
        joint_names: Iterable[str],
    ) -> list[float]:
        positions: list[float] = []
        for name in joint_names:
            state = joint_by_name.get(name)
            if state is None:
                message = f"joint {name!r} missing from get_joint_states()"
                if self.strict:
                    raise RuntimeError(message)
                _warn(message)
                positions.append(math.nan)
                continue
            positions.append(float(state["position"]))
        return positions

    def _get_end_pose(self, child_frame: str) -> tuple[list[float], list[float]]:
        try:
            transform, _ = self.tf.lookup_transform_latest(
                self.base_frame,
                child_frame,
                return_timestamp=True,
            )
            self._log_status(True, f"tf:{child_frame}", "source=lookup_transform_latest")
            return _transform_to_pose_lists(transform)
        except Exception as tf_exc:  # noqa: BLE001 - use fallback below
            try:
                transform = self.tf.get_tf_from_base_link(child_frame)
                self._log_status(True, f"tf:{child_frame}", "source=get_tf_from_base_link")
                return _transform_to_pose_lists(transform)
            except Exception as base_exc:  # noqa: BLE001
                fallback = self._get_end_pose_from_motion_status(child_frame)
                if fallback is not None:
                    self._log_status(True, f"tf:{child_frame}", "source=motion_control_status")
                    return fallback
                message = (
                    f"failed to get pose for {child_frame}: "
                    f"lookup={tf_exc}; base_link={base_exc}"
                )
                if self.strict:
                    raise RuntimeError(message) from base_exc
                self._log_status(False, f"tf:{child_frame}", "pose unavailable")
                _warn(message)
                return _empty_pose_lists()

    def _get_end_pose_from_motion_status(
        self,
        frame_name: str,
    ) -> tuple[list[float], list[float]] | None:
        try:
            status = self.robot.get_motion_control_status()
            index = list(status.frame_names).index(frame_name)
            pose = status.frame_poses[index]
            return _vector3_to_list(pose.position), _quat_to_list(pose.orientation)
        except Exception:
            return None

    def _extract_gripper_position(self, side_state: dict[str, Any], side: str) -> float:
        states = list(side_state.get("end_states") or [])
        if not states:
            message = f"{side} end effector has no motor state"
            if self.strict:
                raise RuntimeError(message)
            self._log_status(False, f"gripper:{side}", "no motor state")
            _warn(message)
            return math.nan

        names = [str(name).lower() for name in side_state.get("names") or []]
        preferred_index = 0
        for index, name in enumerate(names):
            if any(token in name for token in ("gripper", "picker", "finger", "joint1")):
                preferred_index = index
                break

        if preferred_index >= len(states):
            preferred_index = 0
        position = float(states[preferred_index]["position"])
        self._log_status(
            True,
            f"gripper:{side}",
            f"position={position:.6f} motor_index={preferred_index}",
        )
        return position

    def _collect_cameras(self, timestamp_ns: int) -> dict[str, dict[str, Any]]:
        if self.camera is None:
            self._log_status(True, "camera", "disabled")
            return {}

        cameras: dict[str, dict[str, Any]] = {}
        for name in self.camera_names:
            camera_type = self.camera_name_to_type[name]
            try:
                if self.sync_cameras_to_robot_timestamp:
                    try:
                        image = self.camera.get_nearest_image(
                            camera_type,
                            timestamp_ns,
                            self.image_timeout_ms,
                        )
                    except Exception as nearest_exc:  # noqa: BLE001
                        _warn(
                            f"nearest frame failed for {name}, falling back to latest: "
                            f"{nearest_exc}"
                        )
                        image = self.camera.get_latest_image(camera_type, self.image_timeout_ms)
                else:
                    image = self.camera.get_latest_image(camera_type, self.image_timeout_ms)
                cameras[name] = _format_camera_image(name, image)
                camera_data = cameras[name]
                self._log_status(
                    True,
                    f"camera:{name}",
                    (
                        f"{camera_data['width']}x{camera_data['height']} "
                        f"{camera_data['encoding']} {camera_data['color_format']} "
                        f"bytes={len(camera_data['data'])} ts={camera_data['timestamp_ns']}"
                    ),
                )
            except Exception as exc:  # noqa: BLE001
                message = f"failed to collect camera {name}: {exc}"
                if self.strict:
                    raise RuntimeError(message) from exc
                self._log_status(False, f"camera:{name}", str(exc))
                _warn(message)
        return cameras

    def _get_slam_pose(self) -> dict[str, list[float]] | None:
        try:
            pose = self.slam.get_curr_pose()
            slam_pose = _pose_to_dict(pose)
            self._log_status(
                True,
                "slam_pose",
                (
                    f"position={slam_pose['position']} "
                    f"orientation={slam_pose['orientation']}"
                ),
            )
            return slam_pose
        except Exception as exc:  # noqa: BLE001
            if self.strict:
                raise RuntimeError(f"failed to get slam pose: {exc}") from exc
            self._log_status(False, "slam_pose", str(exc))
            _warn(f"failed to get slam pose: {exc}")
            return None


def print_summary(observation: dict[str, Any]) -> None:
    robot_position = observation["robot_position"]
    print(f"timestamp: {observation['timestamp']}")
    print(f"arm joints: {len(robot_position['arm_joint_position'])}")
    print(f"head joints: {len(robot_position['head_joint_position'])}")
    print(f"waist joints: {len(robot_position['waist_joint_position'])}")
    print(f"gripper_position: {observation['gripper_position']}")
    print(f"slam_pose: {'yes' if observation['slam_pose'] else 'None'}")
    print(f"cameras: {len(observation['camera'])}")
    for name, image in observation["camera"].items():
        print(
            f"  {name}: {image['width']}x{image['height']} "
            f"{image['encoding']} {image['color_format']} "
            f"{len(image['data'])} bytes ts={image['timestamp_ns']}"
        )


def parse_args() -> argparse.Namespace:
    camera_names = sorted(CAMERA_NAME_CHOICES)
    parser = argparse.ArgumentParser(
        description="Collect robot state, camera bytes, gripper position, and SLAM pose.",
    )
    parser.add_argument(
        "--camera",
        action="append",
        choices=["default", "all", *camera_names],
        help=(
            "Camera to collect. Repeat this option for multiple cameras. "
            "Use default if omitted."
        ),
    )
    parser.add_argument("--no-camera", action="store_true", help="Do not collect camera images.")
    parser.add_argument(
        "--timeout-ms",
        type=float,
        default=DEFAULT_IMAGE_TIMEOUT_MS,
        help="Image wait timeout. Default is one 30Hz frame period.",
    )
    parser.add_argument(
        "--init-wait-s",
        type=float,
        default=DEFAULT_INIT_WAIT_S,
        help="DDS warm-up wait.",
    )
    parser.add_argument("--camera-config", help="Optional camera config path.")
    parser.add_argument(
        "--latest-camera",
        action="store_true",
        default=True,
        help="Use latest camera frame. This is the default for 30Hz collection.",
    )
    parser.add_argument(
        "--sync-camera",
        dest="latest_camera",
        action="store_false",
        help="Use nearest camera frame to robot timestamp instead of latest frame.",
    )
    parser.add_argument("--strict", action="store_true", help="Raise on any missing sub-signal.")
    parser.add_argument("--quiet", action="store_true", help="Disable status logs and summary output.")
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_SAMPLE_COUNT,
        help="Number of samples to collect.",
    )
    parser.add_argument(
        "--hz",
        type=float,
        default=DEFAULT_HZ,
        help="Target sampling frequency. Default is 30Hz.",
    )
    parser.add_argument("--interval-s", type=float, default=0.0, help="Sleep between samples.")
    parser.add_argument(
        "--output",
        help="Pickle output path. A single sample is stored as dict; count>1 as list[dict].",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start a local web UI for continuously displaying observations.",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Web UI bind address. Default: 0.0.0.0.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Web UI port. Default: 5000.",
    )
    parser.add_argument(
        "--refresh-ms",
        type=int,
        default=500,
        help="Web UI refresh interval in milliseconds. Default: 500.",
    )
    return parser.parse_args()


def resolve_camera_names(selected: list[str] | None) -> list[str]:
    if not selected or "default" in selected:
        return list(DEFAULT_CAMERA_NAMES)
    if "all" in selected:
        return list(_camera_name_to_type())
    return selected


def main() -> int:
    args = parse_args()

    if args.hz is not None and args.hz <= 0:
        print("--hz must be greater than 0", file=sys.stderr)
        return 2
    if args.count < 1:
        print("--count must be at least 1", file=sys.stderr)
        return 2

    gdk = _ensure_gdk()

    if gdk.gdk_init() != gdk.GDKRes.kSuccess:
        print("failed to initialize GDK", file=sys.stderr)
        return 1

    collector: RobotObservationCollector | None = None
    try:
        collector = RobotObservationCollector(
            resolve_camera_names(args.camera),
            image_timeout_ms=args.timeout_ms,
            init_wait_s=args.init_wait_s,
            camera_config=args.camera_config,
            include_cameras=not args.no_camera,
            strict=args.strict,
            sync_cameras_to_robot_timestamp=not args.latest_camera,
            log_status=not args.quiet,
        )

        if args.web:
            collector.show_web(
                host=args.host,
                port=args.port,
                refresh_ms=args.refresh_ms,
            )
            return 0

        samples: list[dict[str, Any]] = []
        period_s = (1.0 / args.hz) if args.hz else None
        for index in range(args.count):
            sample_start_s = time.monotonic()
            observation = collector.collect()
            samples.append(observation)
            if not args.quiet:
                print_summary(observation)
            if index + 1 < args.count:
                elapsed_s = time.monotonic() - sample_start_s
                if period_s is not None:
                    sleep_s = period_s - elapsed_s
                    if sleep_s > 0:
                        time.sleep(sleep_s)
                    elif not args.quiet:
                        print(
                            f"[WARN] sampling overrun: elapsed={elapsed_s:.4f}s "
                            f"target_period={period_s:.4f}s",
                            file=sys.stderr,
                        )
                elif args.interval_s > 0:
                    time.sleep(args.interval_s)

        if args.output:
            payload: dict[str, Any] | list[dict[str, Any]]
            payload = samples[0] if args.count == 1 else samples
            output_path = Path(args.output)
            with output_path.open("wb") as fp:
                pickle.dump(payload, fp, protocol=pickle.HIGHEST_PROTOCOL)
            print(f"saved pickle: {output_path}")

        return 0
    finally:
        if collector is not None:
            collector.close()
        if gdk.gdk_release() != gdk.GDKRes.kSuccess:
            print("failed to release GDK", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
