#!/usr/bin/env python3
"""RoboChallenge-compatible HTTP bridge backed by GDK observations.

Run this on the robot/GDK computer. A remote RoboChallengeInference client can
point its InterfaceClient.robot_url at this server and read state with the same
pickle format expected by robot/interface_client.py.
"""

from __future__ import annotations

import argparse
import pickle
import threading
import time
from typing import Any

try:
    from flask import Flask, Response, jsonify, request

    HAS_FLASK = True
except ImportError:
    HAS_FLASK = False

from robot_observation_collector import RobotObservationCollector, _ensure_gdk

try:
    import cv2
    import numpy as np

    HAS_OPENCV = True
except ImportError:
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    HAS_OPENCV = False


ROBO_TO_COLLECTOR_CAMERA = {
    "kHeadStereoLeft": "head_stereo_left",
    "kHeadStereoRight": "head_stereo_right",
    "kHandLeftColor": "hand_left_color",
    "kHandRightColor": "hand_right_color",
    "kHeadColor": "head_color",
    "kHeadDepth": "head_depth",
}

COLLECTOR_TO_ROBO_CAMERA = {
    value: key for key, value in ROBO_TO_COLLECTOR_CAMERA.items()
}

DEFAULT_ROBO_CAMERAS = [
    "kHeadStereoLeft",
    "kHeadStereoRight",
    "kHandLeftColor",
    "kHandRightColor",
    "kHeadColor",
    "kHeadDepth",
]

DEPTH_CAMERAS = {"kHeadDepth"}


class RoboChallengeStateServer:
    """Expose RobotObservationCollector through RoboChallenge HTTP endpoints."""

    def __init__(
        self,
        collector: RobotObservationCollector,
        *,
        host: str = "0.0.0.0",
        port: int = 9098,
    ) -> None:
        if not HAS_FLASK:
            raise RuntimeError("Flask is required to run the bridge server")

        self.collector = collector
        self.host = host
        self.port = port
        self._collect_lock = threading.Lock()
        self._action_queue: list[dict[str, Any]] = []
        self.app = Flask(__name__)
        self._setup_routes()

    def run(self) -> None:
        print("RoboChallenge state bridge started")
        print(f"Root URL: http://{self.host}:{self.port}")
        print("State endpoint: /state or /robots/<robot_id>/direct/state")
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

    def _setup_routes(self) -> None:
        self.app.add_url_rule("/clock_sync", view_func=self.clock_sync, methods=["GET"])
        self.app.add_url_rule(
            "/robots/<robot_id>/direct/clock_sync",
            view_func=self.clock_sync,
            methods=["GET"],
        )
        self.app.add_url_rule("/state", view_func=self.get_state, methods=["GET"])
        self.app.add_url_rule(
            "/robots/<robot_id>/direct/state",
            view_func=self.get_state,
            methods=["GET"],
        )
        self.app.add_url_rule("/status", view_func=self.get_status, methods=["GET"])
        self.app.add_url_rule(
            "/robots/<robot_id>/direct/status",
            view_func=self.get_status,
            methods=["GET"],
        )
        self.app.add_url_rule("/actions", view_func=self.post_actions, methods=["POST"])
        self.app.add_url_rule(
            "/robots/<robot_id>/direct/actions",
            view_func=self.post_actions,
            methods=["POST"],
        )
        self.app.add_url_rule("/stop_motion", view_func=self.stop_motion, methods=["POST"])
        self.app.add_url_rule(
            "/robots/<robot_id>/direct/stop_motion",
            view_func=self.stop_motion,
            methods=["POST"],
        )
        self.app.add_url_rule(
            "/goto_navi_position",
            view_func=self.goto_navi_position,
            methods=["POST"],
        )
        self.app.add_url_rule(
            "/robots/<robot_id>/direct/goto_navi_position",
            view_func=self.goto_navi_position,
            methods=["POST"],
        )

    def clock_sync(self, robot_id: str | None = None) -> dict[str, float]:
        return {"timestamp": time.time()}

    def get_state(self, robot_id: str | None = None) -> Response:
        requested_robo_cameras = _parse_camera_args(request.args.getlist("cameras"))
        if not requested_robo_cameras:
            requested_robo_cameras = list(DEFAULT_ROBO_CAMERAS)

        image_width = request.args.get("image_width", type=int)
        image_height = request.args.get("image_height", type=int)
        image_size = None
        if image_width is not None and image_height is not None:
            image_size = (image_width, image_height)

        with self._collect_lock:
            observation = self.collector.collect()

        observation["camera"] = self._filter_and_format_cameras(
            observation.get("camera") or {},
            requested_robo_cameras,
            image_size,
        )
        payload = pickle.dumps(observation, protocol=pickle.HIGHEST_PROTOCOL)
        return Response(response=payload, mimetype="application/vnd.python.pickle")

    def get_status(self, robot_id: str | None = None) -> dict[str, Any]:
        return {
            "action_queue": len(self._action_queue),
            "navigation_queue": 0,
            "resetting": False,
            "status": "free",
        }

    def post_actions(self, robot_id: str | None = None) -> Any:
        data = request.get_json(silent=True) or {}
        actions = data.get("actions") or []
        if isinstance(actions, list):
            self._action_queue.extend(actions)
        return jsonify({"status": "accepted", "queued": len(actions)})

    def stop_motion(self, robot_id: str | None = None) -> Any:
        self._action_queue.clear()
        return jsonify({"status": "stopped"})

    def goto_navi_position(self, robot_id: str | None = None) -> Any:
        return jsonify({"status": "accepted"})

    def _filter_and_format_cameras(
        self,
        collected_cameras: dict[str, dict[str, Any]],
        requested_robo_cameras: list[str],
        image_size: tuple[int, int] | None,
    ) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for robo_name in requested_robo_cameras:
            collector_name = ROBO_TO_COLLECTOR_CAMERA.get(robo_name)
            if not collector_name:
                continue
            camera_data = collected_cameras.get(collector_name)
            if not camera_data:
                continue

            output = dict(camera_data)
            if robo_name not in DEPTH_CAMERAS and image_size is not None:
                output = _resize_color_camera(output, image_size)

            output["encoding"] = "UNCOMPRESSED" if robo_name in DEPTH_CAMERAS else "JPEG"
            output["color_format"] = "RS2_FORMAT_Z16" if robo_name in DEPTH_CAMERAS else "RGB"
            result[robo_name] = output
        return result


def _parse_camera_args(values: list[str]) -> list[str]:
    cameras: list[str] = []
    for value in values:
        for item in value.split(","):
            item = item.strip()
            if item:
                cameras.append(item)
    return cameras


def _resize_color_camera(
    camera_data: dict[str, Any],
    image_size: tuple[int, int],
) -> dict[str, Any]:
    width, height = image_size
    if width <= 0 or height <= 0:
        return camera_data
    if not HAS_OPENCV:
        return camera_data
    assert cv2 is not None
    assert np is not None

    original_width = int(camera_data.get("width") or 0)
    original_height = int(camera_data.get("height") or 0)
    if width > original_width or height > original_height:
        return camera_data

    raw = camera_data.get("data") or b""
    encoded = np.frombuffer(raw, dtype=np.uint8)
    image = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
    if image is None:
        return camera_data

    resized = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    ok, jpeg = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ok:
        return camera_data

    resized_data = dict(camera_data)
    resized_data["width"] = width
    resized_data["height"] = height
    resized_data["data"] = jpeg.tobytes()
    return resized_data


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve GDK robot observations through RoboChallenge-compatible HTTP endpoints.",
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=9098)
    parser.add_argument(
        "--camera",
        action="append",
        choices=["default", *DEFAULT_ROBO_CAMERAS],
        help="RoboChallenge camera name to collect. Repeat for multiple cameras.",
    )
    parser.add_argument("--timeout-ms", type=float, default=34.0)
    parser.add_argument("--init-wait-s", type=float, default=2.0)
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def resolve_collector_cameras(selected: list[str] | None) -> list[str]:
    if not selected or "default" in selected:
        return [ROBO_TO_COLLECTOR_CAMERA[name] for name in DEFAULT_ROBO_CAMERAS]
    return [ROBO_TO_COLLECTOR_CAMERA[name] for name in selected]


def main() -> int:
    args = parse_args()
    gdk = _ensure_gdk()
    if gdk.gdk_init() != gdk.GDKRes.kSuccess:
        print("failed to initialize GDK")
        return 1

    collector: RobotObservationCollector | None = None
    try:
        collector = RobotObservationCollector(
            resolve_collector_cameras(args.camera),
            image_timeout_ms=args.timeout_ms,
            init_wait_s=args.init_wait_s,
            sync_cameras_to_robot_timestamp=False,
            log_status=not args.quiet,
        )
        server = RoboChallengeStateServer(
            collector,
            host=args.host,
            port=args.port,
        )
        server.run()
        return 0
    finally:
        if collector is not None:
            collector.close()
        if gdk.gdk_release() != gdk.GDKRes.kSuccess:
            print("failed to release GDK")


if __name__ == "__main__":
    raise SystemExit(main())
