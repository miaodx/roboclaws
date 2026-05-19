#!/usr/bin/env python3
"""Local web UI for RobotObservationCollector-style observations.

This module has no dependency on agibot_gdk. It only needs a provider that
returns the observation dict produced by robot_observation_collector.py.
"""

from __future__ import annotations

import base64
import math
import threading
import time
from typing import Any, Callable

try:
    from flask import Flask, jsonify, render_template_string

    HAS_FLASK = True
except ImportError:
    Flask = None  # type: ignore[assignment]
    HAS_FLASK = False

try:
    import cv2
    import numpy as np

    HAS_OPENCV = True
except ImportError:
    cv2 = None  # type: ignore[assignment]
    np = None  # type: ignore[assignment]
    HAS_OPENCV = False


LEFT_ARM_JOINT_LABELS = [
    "idx21_arm_l_joint1",
    "idx22_arm_l_joint2",
    "idx23_arm_l_joint3",
    "idx24_arm_l_joint4",
    "idx25_arm_l_joint5",
    "idx26_arm_l_joint6",
    "idx27_arm_l_joint7",
]

RIGHT_ARM_JOINT_LABELS = [
    "idx61_arm_r_joint1",
    "idx62_arm_r_joint2",
    "idx63_arm_r_joint3",
    "idx64_arm_r_joint4",
    "idx65_arm_r_joint5",
    "idx66_arm_r_joint6",
    "idx67_arm_r_joint7",
]

HEAD_JOINT_LABELS = [
    "idx11_head_joint1",
    "idx12_head_joint2",
    "idx13_head_joint3",
]

WAIST_JOINT_LABELS = [
    "idx01_body_joint1",
    "idx02_body_joint2",
    "idx03_body_joint3",
    "idx04_body_joint4",
    "idx05_body_joint5",
]


class RobotObservationWebViewer:
    """Display robot observations in a local Flask page.

    Use it either in pull mode:

        viewer = RobotObservationWebViewer(collector)
        viewer.run()

    or in push mode:

        viewer = RobotObservationWebViewer()
        viewer.start_background()
        viewer.update(observation)
    """

    def __init__(
        self,
        collector: Any | None = None,
        *,
        observation_provider: Callable[[], dict[str, Any]] | None = None,
        host: str = "0.0.0.0",
        port: int = 5000,
        refresh_ms: int = 500,
        title: str = "机器人状态查看器",
    ) -> None:
        if collector is not None and observation_provider is not None:
            raise ValueError("collector and observation_provider cannot both be set")

        if observation_provider is not None:
            self._provider = observation_provider
        elif collector is not None:
            if callable(collector) and not hasattr(collector, "collect"):
                self._provider = collector
            else:
                self._provider = collector.collect
        else:
            self._provider = None

        self.host = host
        self.port = port
        self.refresh_ms = refresh_ms
        self.title = title
        self._latest_observation: dict[str, Any] | None = None
        self._latest_error: str | None = None
        self._lock = threading.Lock()
        self._server_thread: threading.Thread | None = None

        self.app = Flask(__name__) if HAS_FLASK else None
        if self.app is not None:
            self._setup_routes()

    def update(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Push a newly collected observation into the viewer."""
        with self._lock:
            self._latest_observation = observation
            self._latest_error = None
        return self._build_payload(observation)

    def run(self) -> None:
        """Run the local web UI. This call blocks until the server exits."""
        if self.app is None:
            print("Flask 未安装，无法启动本地界面。请先安装 flask。")
            return

        print("本地机器人状态界面已启动")
        print(f"访问地址: http://{self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port, debug=False, threaded=True)

    def start_background(self) -> threading.Thread:
        """Start the viewer in a background daemon thread and return it."""
        if self._server_thread and self._server_thread.is_alive():
            return self._server_thread

        self._server_thread = threading.Thread(target=self.run, daemon=True)
        self._server_thread.start()
        return self._server_thread

    def snapshot_payload(self) -> dict[str, Any]:
        """Return a JSON-serializable payload for the current observation."""
        if self._provider is not None:
            try:
                observation = self._provider()
                return self.update(observation)
            except Exception as exc:  # noqa: BLE001 - show runtime collection errors
                with self._lock:
                    self._latest_error = str(exc)
                return {
                    "success": False,
                    "error": str(exc),
                    "generated_at": time.time(),
                    "cameras": [],
                    "sections": [],
                }

        with self._lock:
            observation = self._latest_observation
            latest_error = self._latest_error

        if observation is None:
            return {
                "success": False,
                "error": latest_error or "还没有 observation 数据",
                "generated_at": time.time(),
                "cameras": [],
                "sections": [],
            }
        return self._build_payload(observation)

    def _setup_routes(self) -> None:
        assert self.app is not None

        @self.app.route("/")
        def index() -> str:
            return render_template_string(
                HTML_TEMPLATE,
                title=self.title,
                refresh_ms=max(100, int(self.refresh_ms)),
            )

        @self.app.route("/api/observation")
        def api_observation() -> Any:
            return jsonify(self.snapshot_payload())

        @self.app.route("/health")
        def health() -> Any:
            return jsonify({"success": True})

    def _build_payload(self, observation: dict[str, Any]) -> dict[str, Any]:
        cameras = self._format_cameras(observation.get("camera") or {})
        sections = self._format_sections(observation)
        return {
            "success": True,
            "generated_at": time.time(),
            "timestamp": observation.get("timestamp"),
            "cameras": cameras,
            "sections": sections,
        }

    def _format_cameras(self, cameras: dict[str, Any]) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for name, image in cameras.items():
            camera = {
                "name": str(name),
                "width": _safe_int(image.get("width")),
                "height": _safe_int(image.get("height")),
                "timestamp_ns": _safe_int(image.get("timestamp_ns")),
                "encoding": str(image.get("encoding") or ""),
                "color_format": str(image.get("color_format") or ""),
                "image": None,
                "error": None,
            }

            try:
                camera["image"] = self._image_to_data_uri(image)
            except Exception as exc:  # noqa: BLE001 - keep page alive
                camera["error"] = str(exc)
            result.append(camera)
        return result

    def _format_sections(self, observation: dict[str, Any]) -> list[dict[str, Any]]:
        sections: list[dict[str, Any]] = []

        timestamp = observation.get("timestamp")
        sections.append(
            {
                "title": "基础信息",
                "rows": [
                    {"name": "采集时间戳", "value": _format_value(timestamp)},
                    {"name": "界面更新时间", "value": time.strftime("%H:%M:%S")},
                ],
            }
        )

        robot_position = observation.get("robot_position") or {}
        arm_positions = _as_float_list(robot_position.get("arm_joint_position"))
        if len(arm_positions) == 14:
            sections.append(
                _rows_section(
                    "左臂关节",
                    _joint_rows(LEFT_ARM_JOINT_LABELS, arm_positions[:7], "rad"),
                )
            )
            sections.append(
                _rows_section(
                    "右臂关节",
                    _joint_rows(RIGHT_ARM_JOINT_LABELS, arm_positions[7:], "rad"),
                )
            )
        elif arm_positions:
            sections.append(
                _rows_section(
                    "手臂关节",
                    _joint_rows(None, arm_positions, "rad"),
                )
            )

        head_positions = _as_float_list(robot_position.get("head_joint_position"))
        if head_positions:
            sections.append(
                _rows_section(
                    "头部关节",
                    _joint_rows(HEAD_JOINT_LABELS, head_positions, "rad"),
                )
            )

        waist_positions = _as_float_list(robot_position.get("waist_joint_position"))
        if waist_positions:
            sections.append(
                _rows_section(
                    "腰部关节",
                    _joint_rows(WAIST_JOINT_LABELS, waist_positions, "rad"),
                )
            )

        pose_rows = []
        pose_rows.extend(
            _named_vector_rows(
                "左末端位置",
                robot_position.get("left_end_position"),
                ["x", "y", "z"],
                "m",
            )
        )
        pose_rows.extend(
            _named_vector_rows(
                "左末端姿态",
                robot_position.get("left_end_orientation"),
                ["x", "y", "z", "w"],
                "",
            )
        )
        pose_rows.extend(
            _named_vector_rows(
                "右末端位置",
                robot_position.get("right_end_position"),
                ["x", "y", "z"],
                "m",
            )
        )
        pose_rows.extend(
            _named_vector_rows(
                "右末端姿态",
                robot_position.get("right_end_orientation"),
                ["x", "y", "z", "w"],
                "",
            )
        )
        if pose_rows:
            sections.append(_rows_section("末端位姿", pose_rows))

        gripper_position = _as_float_list(observation.get("gripper_position"))
        if gripper_position:
            labels = ["左夹爪", "右夹爪"]
            rows = []
            for index, value in enumerate(gripper_position):
                name = labels[index] if index < len(labels) else f"夹爪 {index + 1}"
                rows.append({"name": name, "value": _format_number(value, "rad")})
            sections.append(_rows_section("夹爪位置", rows))

        slam_pose = observation.get("slam_pose")
        if slam_pose:
            slam_rows = []
            slam_rows.extend(
                _named_vector_rows(
                    "SLAM 位置",
                    slam_pose.get("position"),
                    ["x", "y", "z"],
                    "m",
                )
            )
            slam_rows.extend(
                _named_vector_rows(
                    "SLAM 姿态",
                    slam_pose.get("orientation"),
                    ["x", "y", "z", "w"],
                    "",
                )
            )
            sections.append(_rows_section("SLAM 位姿", slam_rows))
        else:
            sections.append(_rows_section("SLAM 位姿", [{"name": "状态", "value": "无数据"}]))

        extra_rows = []
        for key, value in observation.items():
            if key in {"timestamp", "robot_position", "camera", "gripper_position", "slam_pose"}:
                continue
            extra_rows.append({"name": str(key), "value": _format_value(value)})
        if extra_rows:
            sections.append(_rows_section("其他信息", extra_rows))

        return sections

    def _image_to_data_uri(self, image: dict[str, Any]) -> str | None:
        raw_data = _bytes_from_image_data(image.get("data"))
        if not raw_data:
            return None

        encoding = str(image.get("encoding") or "").rsplit(".", 1)[-1].upper()
        color_format = str(image.get("color_format") or "").rsplit(".", 1)[-1].upper()
        width = _safe_int(image.get("width"))
        height = _safe_int(image.get("height"))

        if encoding == "JPEG":
            return _data_uri("image/jpeg", raw_data)
        if encoding == "PNG":
            return _data_uri("image/png", raw_data)
        if not HAS_OPENCV:
            raise RuntimeError("raw image requires opencv/numpy to display")

        if color_format == "RS2_FORMAT_Z16" or "DEPTH" in color_format:
            return _data_uri("image/jpeg", _depth_z16_to_jpeg(raw_data, width, height))
        if color_format in {"RGB", "BGR", "RGBA", "BGRA", "GRAY8", "GRAY16"}:
            return _data_uri(
                "image/jpeg",
                _uncompressed_color_to_jpeg(raw_data, width, height, color_format),
            )
        raise RuntimeError(f"unsupported image format: {encoding}/{color_format}")


def run_observation_viewer(
    collector: Any,
    *,
    host: str = "0.0.0.0",
    port: int = 5000,
    refresh_ms: int = 500,
) -> RobotObservationWebViewer:
    """Create and run a RobotObservationWebViewer for a collector."""
    viewer = RobotObservationWebViewer(
        collector,
        host=host,
        port=port,
        refresh_ms=refresh_ms,
    )
    viewer.run()
    return viewer


def _rows_section(title: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    return {"title": title, "rows": rows}


def _joint_rows(
    labels: list[str] | None,
    values: list[float],
    unit: str,
) -> list[dict[str, str]]:
    rows = []
    for index, value in enumerate(values):
        label = labels[index] if labels and index < len(labels) else f"joint_{index + 1}"
        rows.append({"name": label, "value": _format_number(value, unit)})
    return rows


def _named_vector_rows(
    prefix: str,
    values: Any,
    labels: list[str],
    unit: str,
) -> list[dict[str, str]]:
    numbers = _as_float_list(values)
    rows = []
    for index, value in enumerate(numbers):
        axis = labels[index] if index < len(labels) else str(index)
        rows.append({"name": f"{prefix}.{axis}", "value": _format_number(value, unit)})
    return rows


def _as_float_list(value: Any) -> list[float]:
    if value is None or isinstance(value, (str, bytes, bytearray)):
        return []
    try:
        return [float(item) for item in value]
    except TypeError:
        return []


def _format_number(value: float, unit: str) -> str:
    if not math.isfinite(value):
        return "nan"
    suffix = f" {unit}" if unit else ""
    return f"{value:.6f}{suffix}"


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return _format_number(value, "")
    if isinstance(value, (list, tuple)):
        return "[" + ", ".join(_format_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return ", ".join(f"{key}: {_format_value(val)}" for key, val in value.items())
    return str(value)


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _bytes_from_image_data(data: Any) -> bytes:
    if data is None:
        return b""
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, memoryview):
        return data.tobytes()
    if hasattr(data, "tobytes"):
        return data.tobytes()
    return bytes(data)


def _data_uri(mime: str, data: bytes) -> str:
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _depth_z16_to_jpeg(raw_data: bytes, width: int, height: int) -> bytes:
    if not HAS_OPENCV:
        raise RuntimeError("opencv/numpy is required for depth images")
    assert cv2 is not None
    assert np is not None

    expected = width * height * 2
    if expected and len(raw_data) < expected:
        raise RuntimeError(f"depth image is too small: {len(raw_data)} < {expected}")

    depth = np.frombuffer(raw_data[:expected], dtype=np.uint16).reshape((height, width))
    valid = depth > 0
    normalized = np.zeros_like(depth, dtype=np.uint8)
    if np.any(valid):
        min_depth = int(np.min(depth[valid]))
        max_depth = int(np.max(depth[valid]))
        if max_depth > min_depth:
            normalized = ((depth - min_depth) / (max_depth - min_depth) * 255).astype(np.uint8)
        colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
        cv2.putText(
            colored,
            f"{min_depth}-{max_depth} mm",
            (10, 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
    else:
        colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)

    ok, jpeg = cv2.imencode(".jpg", colored, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise RuntimeError("failed to encode depth image")
    return jpeg.tobytes()


def _uncompressed_color_to_jpeg(
    raw_data: bytes,
    width: int,
    height: int,
    color_format: str,
) -> bytes:
    if not HAS_OPENCV:
        raise RuntimeError("opencv/numpy is required for raw color images")
    assert cv2 is not None
    assert np is not None

    if color_format == "RGB":
        image = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 3))
        bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    elif color_format == "BGR":
        bgr = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 3))
    elif color_format == "RGBA":
        image = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 4))
        bgr = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
    elif color_format == "BGRA":
        image = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width, 4))
        bgr = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    elif color_format == "GRAY8":
        gray = np.frombuffer(raw_data, dtype=np.uint8).reshape((height, width))
        bgr = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    elif color_format == "GRAY16":
        gray16 = np.frombuffer(raw_data, dtype=np.uint16).reshape((height, width))
        gray8 = (gray16 / 256).astype(np.uint8)
        bgr = cv2.cvtColor(gray8, cv2.COLOR_GRAY2BGR)
    else:
        raise RuntimeError(f"unsupported raw color format: {color_format}")

    ok, jpeg = cv2.imencode(".jpg", bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if not ok:
        raise RuntimeError("failed to encode raw color image")
    return jpeg.tobytes()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }}</title>
    <style>
        :root {
            --bg: #f6f7f9;
            --panel: #ffffff;
            --line: #d9dee7;
            --text: #1f2933;
            --muted: #687386;
            --accent: #0f766e;
            --bad: #b42318;
        }
        * { box-sizing: border-box; }
        body {
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: Arial, "Microsoft YaHei", sans-serif;
        }
        .shell {
            width: min(1600px, calc(100vw - 32px));
            margin: 0 auto;
            padding: 18px 0 28px;
        }
        .topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--line);
            padding-bottom: 12px;
        }
        h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 0;
        }
        .status {
            color: var(--muted);
            font-size: 14px;
            text-align: right;
        }
        .status.error { color: var(--bad); }
        .layout {
            display: grid;
            grid-template-columns: minmax(460px, 1.4fr) minmax(360px, 0.8fr);
            gap: 16px;
            align-items: start;
        }
        .section-title {
            margin: 0 0 10px;
            font-size: 17px;
            font-weight: 700;
        }
        .camera-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 12px;
        }
        .camera-card, .text-panel {
            background: var(--panel);
            border: 1px solid var(--line);
            border-radius: 8px;
            overflow: hidden;
        }
        .camera-head {
            display: flex;
            justify-content: space-between;
            gap: 10px;
            padding: 10px 12px;
            border-bottom: 1px solid var(--line);
            font-size: 14px;
        }
        .camera-name { font-weight: 700; }
        .camera-meta { color: var(--muted); white-space: nowrap; }
        .camera-image-wrap {
            aspect-ratio: 4 / 3;
            background: #101418;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .camera-image {
            width: 100%;
            height: 100%;
            object-fit: contain;
            display: block;
        }
        .empty-image {
            color: #b8c0cc;
            font-size: 14px;
        }
        .text-stack {
            display: grid;
            gap: 12px;
        }
        .text-panel h2 {
            margin: 0;
            padding: 10px 12px;
            border-bottom: 1px solid var(--line);
            font-size: 15px;
            background: #fbfcfd;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            table-layout: fixed;
        }
        td {
            padding: 7px 12px;
            border-bottom: 1px solid #edf0f4;
            font-size: 13px;
            vertical-align: top;
        }
        tr:last-child td { border-bottom: 0; }
        td:first-child {
            width: 46%;
            color: var(--muted);
            overflow-wrap: anywhere;
        }
        td:last-child {
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            overflow-wrap: anywhere;
        }
        .empty {
            background: var(--panel);
            border: 1px dashed var(--line);
            border-radius: 8px;
            padding: 24px;
            color: var(--muted);
            text-align: center;
        }
        @media (max-width: 980px) {
            .layout { grid-template-columns: 1fr; }
            .topbar { align-items: flex-start; flex-direction: column; }
            .status { text-align: left; }
        }
    </style>
</head>
<body>
    <main class="shell">
        <div class="topbar">
            <h1>{{ title }}</h1>
            <div id="status" class="status">连接中...</div>
        </div>
        <div class="layout">
            <section>
                <h2 class="section-title">相机图像</h2>
                <div id="camera-grid" class="camera-grid"></div>
            </section>
            <section>
                <h2 class="section-title">机器人状态</h2>
                <div id="text-stack" class="text-stack"></div>
            </section>
        </div>
    </main>
    <script>
        const refreshMs = {{ refresh_ms }};

        function setStatus(text, error = false) {
            const status = document.getElementById('status');
            status.textContent = text;
            status.className = error ? 'status error' : 'status';
        }

        function renderCameras(cameras) {
            const grid = document.getElementById('camera-grid');
            grid.innerHTML = '';
            if (!cameras.length) {
                grid.innerHTML = '<div class="empty">没有相机数据</div>';
                return;
            }
            cameras.forEach((camera) => {
                const card = document.createElement('article');
                card.className = 'camera-card';

                const head = document.createElement('div');
                head.className = 'camera-head';

                const name = document.createElement('div');
                name.className = 'camera-name';
                name.textContent = camera.name;

                const meta = document.createElement('div');
                meta.className = 'camera-meta';
                meta.textContent = `${camera.width}x${camera.height}`;

                head.appendChild(name);
                head.appendChild(meta);

                const wrap = document.createElement('div');
                wrap.className = 'camera-image-wrap';
                if (camera.image) {
                    const img = document.createElement('img');
                    img.className = 'camera-image';
                    img.alt = camera.name;
                    img.src = camera.image;
                    wrap.appendChild(img);
                } else {
                    const empty = document.createElement('div');
                    empty.className = 'empty-image';
                    empty.textContent = camera.error || '无图像';
                    wrap.appendChild(empty);
                }

                card.appendChild(head);
                card.appendChild(wrap);
                grid.appendChild(card);
            });
        }

        function renderSections(sections) {
            const stack = document.getElementById('text-stack');
            stack.innerHTML = '';
            if (!sections.length) {
                stack.innerHTML = '<div class="empty">没有状态数据</div>';
                return;
            }
            sections.forEach((section) => {
                const panel = document.createElement('article');
                panel.className = 'text-panel';

                const title = document.createElement('h2');
                title.textContent = section.title;
                panel.appendChild(title);

                const table = document.createElement('table');
                const tbody = document.createElement('tbody');
                section.rows.forEach((row) => {
                    const tr = document.createElement('tr');
                    const name = document.createElement('td');
                    const value = document.createElement('td');
                    name.textContent = row.name;
                    value.textContent = row.value;
                    tr.appendChild(name);
                    tr.appendChild(value);
                    tbody.appendChild(tr);
                });
                table.appendChild(tbody);
                panel.appendChild(table);
                stack.appendChild(panel);
            });
        }

        async function refresh() {
            try {
                const response = await fetch('/api/observation', { cache: 'no-store' });
                const data = await response.json();
                if (!data.success) {
                    setStatus(data.error || '获取数据失败', true);
                    renderCameras([]);
                    renderSections([]);
                    return;
                }
                renderCameras(data.cameras || []);
                renderSections(data.sections || []);
                const cameraCount = (data.cameras || []).length;
                const sectionCount = (data.sections || []).length;
                setStatus(`正常刷新 | 相机 ${cameraCount} 路 | 状态 ${sectionCount} 组`);
            } catch (error) {
                setStatus(`连接错误: ${error}`, true);
            }
        }

        refresh();
        setInterval(refresh, refreshMs);
    </script>
</body>
</html>
"""
