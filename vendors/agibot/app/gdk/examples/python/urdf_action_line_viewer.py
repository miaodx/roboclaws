#!/usr/bin/env python3
"""Visualize a URDF robot as animated line segments from action JSON."""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from flask import Flask, Response, jsonify, render_template_string

    HAS_FLASK = True
except ImportError:
    Flask = None  # type: ignore[assignment]
    HAS_FLASK = False


DEFAULT_URDF = "/home/mi/Downloads/G2/genie_robot_description/urdf/G2_t2_crs_omnipicker.urdf"
DEFAULT_ACTIONS = "/tmp/aligned_joints_actions.json"

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

LEFT_GRIPPER_DRIVER = "idx31_gripper_l_inner_joint1"
RIGHT_GRIPPER_DRIVER = "idx71_gripper_r_inner_joint1"


@dataclass(frozen=True)
class MimicSpec:
    joint: str
    multiplier: float = 1.0
    offset: float = 0.0


@dataclass(frozen=True)
class UrdfJoint:
    name: str
    joint_type: str
    parent: str
    child: str
    xyz: tuple[float, float, float]
    rpy: tuple[float, float, float]
    axis: tuple[float, float, float]
    mimic: MimicSpec | None = None


@dataclass(frozen=True)
class UrdfLoopJoint:
    name: str
    link1: str
    link2: str
    xyz1: tuple[float, float, float]
    rpy1: tuple[float, float, float]
    xyz2: tuple[float, float, float]
    rpy2: tuple[float, float, float]


class UrdfLineRobot:
    """Load a URDF and expose simple line-segment forward kinematics."""

    def __init__(self, urdf_path: str | Path) -> None:
        self.urdf_path = Path(urdf_path)
        self.robot_name = ""
        self.links: set[str] = set()
        self.joints: list[UrdfJoint] = []
        self.joints_by_name: dict[str, UrdfJoint] = {}
        self.children_by_parent: dict[str, list[UrdfJoint]] = {}
        self.loop_joints: list[UrdfLoopJoint] = []
        self.root_link = ""
        self._load()

    def _load(self) -> None:
        root = ET.parse(self.urdf_path).getroot()
        self.robot_name = root.attrib.get("name", self.urdf_path.stem)
        self.links = {link.attrib["name"] for link in root.findall("link") if "name" in link.attrib}

        joints: list[UrdfJoint] = []
        for elem in root.findall("joint"):
            name = elem.attrib.get("name", "")
            parent_elem = elem.find("parent")
            child_elem = elem.find("child")
            parent = parent_elem.attrib.get("link", "") if parent_elem is not None else ""
            child = child_elem.attrib.get("link", "") if child_elem is not None else ""
            if not name or not parent or not child:
                continue
            origin = elem.find("origin")
            axis = elem.find("axis")
            mimic = elem.find("mimic")
            joints.append(
                UrdfJoint(
                    name=name,
                    joint_type=elem.attrib.get("type", "fixed"),
                    parent=parent,
                    child=child,
                    xyz=_parse_vec(origin.attrib.get("xyz") if origin is not None else None, 3),
                    rpy=_parse_vec(origin.attrib.get("rpy") if origin is not None else None, 3),
                    axis=_parse_vec(axis.attrib.get("xyz") if axis is not None else None, 3, default=(0.0, 0.0, 1.0)),
                    mimic=(
                        MimicSpec(
                            joint=mimic.attrib.get("joint", ""),
                            multiplier=float(mimic.attrib.get("multiplier", 1.0)),
                            offset=float(mimic.attrib.get("offset", 0.0)),
                        )
                        if mimic is not None
                        else None
                    ),
                )
            )
        self.joints = joints
        self.joints_by_name = {joint.name: joint for joint in joints}

        children_by_parent: dict[str, list[UrdfJoint]] = {}
        child_links = set()
        for joint in joints:
            children_by_parent.setdefault(joint.parent, []).append(joint)
            child_links.add(joint.child)
        self.children_by_parent = children_by_parent
        roots = sorted(self.links - child_links)
        self.root_link = "base_link" if "base_link" in roots or "base_link" in self.links else (roots[0] if roots else "")

        self.loop_joints = []
        for elem in root.findall("loop_joint"):
            link1 = elem.find("link1")
            link2 = elem.find("link2")
            if link1 is None or link2 is None:
                continue
            self.loop_joints.append(
                UrdfLoopJoint(
                    name=elem.attrib.get("name", ""),
                    link1=link1.attrib.get("link", ""),
                    link2=link2.attrib.get("link", ""),
                    xyz1=_parse_vec(link1.attrib.get("xyz"), 3),
                    rpy1=_parse_vec(link1.attrib.get("rpy"), 3),
                    xyz2=_parse_vec(link2.attrib.get("xyz"), 3),
                    rpy2=_parse_vec(link2.attrib.get("rpy"), 3),
                )
            )

    def summary(self) -> dict[str, Any]:
        return {
            "robot_name": self.robot_name,
            "urdf_path": str(self.urdf_path),
            "root_link": self.root_link,
            "link_count": len(self.links),
            "joint_count": len(self.joints),
            "loop_joint_count": len(self.loop_joints),
            "mimic_joint_count": sum(1 for joint in self.joints if joint.mimic is not None),
        }

    def action_to_joint_values(self, action: dict[str, Any]) -> dict[str, float]:
        robot_position = action.get("robot_position") or {}
        values: dict[str, float] = {}

        self._extend_joint_values(values, WAIST_JOINT_NAMES, robot_position.get("waist_joint_position"))
        self._extend_joint_values(values, HEAD_JOINT_NAMES, robot_position.get("head_joint_position"))
        self._extend_joint_values(values, ARM_JOINT_NAMES, robot_position.get("arm_joint_position"))

        gripper = action.get("gripper_position")
        if isinstance(gripper, list) and len(gripper) >= 2:
            values[LEFT_GRIPPER_DRIVER] = float(gripper[0])
            values[RIGHT_GRIPPER_DRIVER] = float(gripper[1])

        return values

    def _extend_joint_values(
        self,
        values: dict[str, float],
        names: list[str],
        positions: Any,
    ) -> None:
        if positions is None:
            return
        if not isinstance(positions, list) or len(positions) != len(names):
            raise ValueError(f"expected {len(names)} positions for {names[0]}..., got {positions!r}")
        for name, position in zip(names, positions):
            values[name] = float(position)

    def forward_kinematics(self, joint_values: dict[str, float]) -> dict[str, Any]:
        link_transforms: dict[str, Matrix4] = {self.root_link: _identity()}
        lines: list[dict[str, Any]] = []

        def visit(parent_link: str) -> None:
            parent_tf = link_transforms[parent_link]
            for joint in self.children_by_parent.get(parent_link, []):
                value = self._joint_value(joint, joint_values)
                child_tf = _matmul(parent_tf, _matmul(_origin_transform(joint.xyz, joint.rpy), _motion_transform(joint, value)))
                link_transforms[joint.child] = child_tf
                parent_pos = _translation(parent_tf)
                child_pos = _translation(child_tf)
                lines.append(
                    {
                        "a": parent_pos,
                        "b": child_pos,
                        "joint": joint.name,
                        "parent": joint.parent,
                        "child": joint.child,
                        "category": _category_for(joint.name, joint.parent, joint.child),
                        "type": joint.joint_type,
                    }
                )
                visit(joint.child)

        if self.root_link:
            visit(self.root_link)

        loop_lines: list[dict[str, Any]] = []
        for loop_joint in self.loop_joints:
            if loop_joint.link1 not in link_transforms or loop_joint.link2 not in link_transforms:
                continue
            p1 = _translation(_matmul(link_transforms[loop_joint.link1], _origin_transform(loop_joint.xyz1, loop_joint.rpy1)))
            p2 = _translation(_matmul(link_transforms[loop_joint.link2], _origin_transform(loop_joint.xyz2, loop_joint.rpy2)))
            loop_lines.append(
                {
                    "a": p1,
                    "b": p2,
                    "joint": loop_joint.name,
                    "parent": loop_joint.link1,
                    "child": loop_joint.link2,
                    "category": _category_for(loop_joint.name, loop_joint.link1, loop_joint.link2),
                    "type": "loop",
                }
            )

        points = {link: _translation(tf) for link, tf in link_transforms.items()}
        return {
            "root": self.root_link,
            "points": points,
            "lines": lines + loop_lines,
        }

    def _joint_value(
        self,
        joint: UrdfJoint,
        joint_values: dict[str, float],
        seen: set[str] | None = None,
    ) -> float:
        if joint.mimic is None:
            return float(joint_values.get(joint.name, 0.0))
        if seen is None:
            seen = set()
        if joint.name in seen:
            return 0.0
        seen.add(joint.name)
        source = self.joints_by_name.get(joint.mimic.joint)
        base = self._joint_value(source, joint_values, seen) if source is not None else float(joint_values.get(joint.mimic.joint, 0.0))
        return joint.mimic.multiplier * base + joint.mimic.offset


Matrix4 = list[list[float]]


def load_action_payload(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as fp:
        payload = json.load(fp)
    actions = payload.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("action payload must contain a non-empty actions list")
    return payload


def build_visualization_payload(robot: UrdfLineRobot, actions_payload: dict[str, Any], max_frames: int | None = None) -> dict[str, Any]:
    actions = actions_payload["actions"]
    if max_frames is not None:
        actions = actions[:max_frames]
    action_freq = float(actions_payload.get("action_freq") or 30.0)
    period_s = 1.0 / action_freq

    frames: list[dict[str, Any]] = []
    bounds_min = [float("inf"), float("inf"), float("inf")]
    bounds_max = [float("-inf"), float("-inf"), float("-inf")]
    base_x = 0.0
    base_y = 0.0
    base_yaw = 0.0
    base_path: list[list[float]] = []

    for index, action in enumerate(actions):
        joint_values = robot.action_to_joint_values(action)
        fk = robot.forward_kinematics(joint_values)
        raw_velocity = action.get("chassis_velocity", [0.0, 0.0, 0.0])
        chassis_velocity = _chassis_velocity(raw_velocity)
        base_pose = [base_x, base_y, base_yaw]
        base_path.append([base_x, base_y, 0.0])

        lines = _transform_lines(fk["lines"], base_x, base_y, base_yaw)
        for line in lines:
            for point in (line["a"], line["b"]):
                for axis in range(3):
                    bounds_min[axis] = min(bounds_min[axis], point[axis])
                    bounds_max[axis] = max(bounds_max[axis], point[axis])
        bounds_min[0] = min(bounds_min[0], base_x)
        bounds_min[1] = min(bounds_min[1], base_y)
        bounds_min[2] = min(bounds_min[2], 0.0)
        bounds_max[0] = max(bounds_max[0], base_x)
        bounds_max[1] = max(bounds_max[1], base_y)
        bounds_max[2] = max(bounds_max[2], 0.0)
        frames.append(
            {
                "index": index,
                "time_s": index / action_freq,
                "lines": lines,
                "gripper_position": action.get("gripper_position", [0.0, 0.0]),
                "chassis_velocity": chassis_velocity,
                "base_pose": base_pose,
            }
        )

        vx, vy, wz = chassis_velocity
        cos_yaw = math.cos(base_yaw)
        sin_yaw = math.sin(base_yaw)
        base_x += (cos_yaw * vx - sin_yaw * vy) * period_s
        base_y += (sin_yaw * vx + cos_yaw * vy) * period_s
        base_yaw += wz * period_s

    if not frames:
        bounds_min = [-1.0, -1.0, -1.0]
        bounds_max = [1.0, 1.0, 1.0]

    return {
        "robot": robot.summary(),
        "action_freq": action_freq,
        "frame_count": len(frames),
        "bounds": {"min": bounds_min, "max": bounds_max},
        "base_path": base_path,
        "frames": frames,
        "generated_at": time.time(),
    }


def _chassis_velocity(value: Any) -> list[float]:
    if not isinstance(value, list):
        return [0.0, 0.0, 0.0]
    if len(value) >= 6:
        return [float(value[0]), float(value[1]), float(value[5])]
    if len(value) >= 3:
        return [float(value[0]), float(value[1]), float(value[2])]
    return [0.0, 0.0, 0.0]


def _transform_lines(lines: list[dict[str, Any]], base_x: float, base_y: float, base_yaw: float) -> list[dict[str, Any]]:
    return [
        {
            **line,
            "a": _transform_point(line["a"], base_x, base_y, base_yaw),
            "b": _transform_point(line["b"], base_x, base_y, base_yaw),
        }
        for line in lines
    ]


def _transform_point(point: list[float], base_x: float, base_y: float, base_yaw: float) -> list[float]:
    cos_yaw = math.cos(base_yaw)
    sin_yaw = math.sin(base_yaw)
    x = cos_yaw * point[0] - sin_yaw * point[1] + base_x
    y = sin_yaw * point[0] + cos_yaw * point[1] + base_y
    return [x, y, point[2]]


def _parse_vec(value: str | None, count: int, default: tuple[float, ...] | None = None) -> tuple[float, ...]:
    if default is None:
        default = tuple(0.0 for _ in range(count))
    if not value:
        return default
    parts = [float(part) for part in value.split()]
    if len(parts) != count:
        return default
    return tuple(parts)


def _identity() -> Matrix4:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _translation(tf: Matrix4) -> list[float]:
    return [tf[0][3], tf[1][3], tf[2][3]]


def _matmul(a: Matrix4, b: Matrix4) -> Matrix4:
    return [[sum(a[row][k] * b[k][col] for k in range(4)) for col in range(4)] for row in range(4)]


def _origin_transform(xyz: tuple[float, ...], rpy: tuple[float, ...]) -> Matrix4:
    return _matmul(_translate(xyz[0], xyz[1], xyz[2]), _rpy(rpy[0], rpy[1], rpy[2]))


def _translate(x: float, y: float, z: float) -> Matrix4:
    tf = _identity()
    tf[0][3] = x
    tf[1][3] = y
    tf[2][3] = z
    return tf


def _rpy(roll: float, pitch: float, yaw: float) -> Matrix4:
    return _matmul(_matmul(_rot_z(yaw), _rot_y(pitch)), _rot_x(roll))


def _rot_x(angle: float) -> Matrix4:
    c = math.cos(angle)
    s = math.sin(angle)
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, c, -s, 0.0],
        [0.0, s, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _rot_y(angle: float) -> Matrix4:
    c = math.cos(angle)
    s = math.sin(angle)
    return [
        [c, 0.0, s, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [-s, 0.0, c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _rot_z(angle: float) -> Matrix4:
    c = math.cos(angle)
    s = math.sin(angle)
    return [
        [c, -s, 0.0, 0.0],
        [s, c, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _axis_angle(axis: tuple[float, ...], angle: float) -> Matrix4:
    x, y, z = _normalize(axis)
    c = math.cos(angle)
    s = math.sin(angle)
    t = 1.0 - c
    return [
        [t * x * x + c, t * x * y - s * z, t * x * z + s * y, 0.0],
        [t * x * y + s * z, t * y * y + c, t * y * z - s * x, 0.0],
        [t * x * z - s * y, t * y * z + s * x, t * z * z + c, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _normalize(axis: tuple[float, ...]) -> tuple[float, float, float]:
    x, y, z = float(axis[0]), float(axis[1]), float(axis[2])
    norm = math.sqrt(x * x + y * y + z * z)
    if norm <= 1e-12:
        return 0.0, 0.0, 1.0
    return x / norm, y / norm, z / norm


def _motion_transform(joint: UrdfJoint, value: float) -> Matrix4:
    if joint.joint_type in {"revolute", "continuous"}:
        return _axis_angle(joint.axis, value)
    if joint.joint_type == "prismatic":
        axis = _normalize(joint.axis)
        return _translate(axis[0] * value, axis[1] * value, axis[2] * value)
    return _identity()


def _category_for(*names: str) -> str:
    text = " ".join(names).lower()
    if "gripper_l" in text or "_gripper_l" in text or "_ee_l" in text:
        return "left_gripper"
    if "gripper_r" in text or "_gripper_r" in text or "_ee_r" in text:
        return "right_gripper"
    if "arm_l" in text or "_arm_l" in text:
        return "left_arm"
    if "arm_r" in text or "_arm_r" in text:
        return "right_arm"
    if "head" in text or "neck" in text:
        return "head"
    if "body" in text or "waist" in text:
        return "waist"
    if "chassis" in text or "wheel" in text:
        return "chassis"
    return "other"


def create_app(payload: dict[str, Any]) -> Flask:
    if not HAS_FLASK:
        raise RuntimeError("flask is required for the web viewer")

    app = Flask(__name__)
    payload_json = json.dumps(payload, separators=(",", ":"))

    @app.route("/")
    def index() -> str:
        return render_template_string(HTML_TEMPLATE)

    @app.route("/api/model")
    def api_model() -> Response:
        return Response(payload_json, mimetype="application/json")

    @app.route("/health")
    def health() -> Any:
        return jsonify({"success": True})

    return app


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Line-render a URDF and animate it from action JSON.")
    parser.add_argument("--urdf", default=DEFAULT_URDF, help="URDF file path.")
    parser.add_argument("--actions", default=DEFAULT_ACTIONS, help="Action JSON path.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5004)
    parser.add_argument("--max-frames", type=int, help="Limit frames loaded into the viewer.")
    parser.add_argument("--summary", action="store_true", help="Print model/action summary and exit.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    robot = UrdfLineRobot(args.urdf)
    actions = load_action_payload(args.actions)
    payload = build_visualization_payload(robot, actions, max_frames=args.max_frames)

    if args.summary:
        print(json.dumps({k: v for k, v in payload.items() if k != "frames"}, indent=2))
        print(f"frames: {len(payload['frames'])}")
        if payload["frames"]:
            print(f"lines_per_frame: {len(payload['frames'][0]['lines'])}")
        return 0

    app = create_app(payload)
    print(f"loaded URDF: {args.urdf}")
    print(f"loaded actions: {args.actions}")
    print(f"frames: {payload['frame_count']}, action_freq: {payload['action_freq']:.3f} Hz")
    print(f"open: http://{args.host if args.host != '0.0.0.0' else '127.0.0.1'}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0


HTML_TEMPLATE = r"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>URDF Action Line Viewer</title>
  <style>
    :root {
      --bg: #f5f7f8;
      --ink: #172026;
      --muted: #66717a;
      --panel: rgba(255, 255, 255, 0.88);
      --edge: rgba(23, 32, 38, 0.14);
      --accent: #0f766e;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      height: 100vh;
      overflow: hidden;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    canvas {
      display: block;
      width: 100vw;
      height: 100vh;
      background:
        linear-gradient(90deg, rgba(23, 32, 38, 0.035) 1px, transparent 1px),
        linear-gradient(rgba(23, 32, 38, 0.035) 1px, transparent 1px),
        #f5f7f8;
      background-size: 32px 32px;
    }
    .hud {
      position: fixed;
      left: 16px;
      right: 16px;
      bottom: 16px;
      display: grid;
      grid-template-columns: auto minmax(160px, 1fr) auto auto auto;
      gap: 10px;
      align-items: center;
      padding: 10px;
      border: 1px solid var(--edge);
      background: var(--panel);
      backdrop-filter: blur(10px);
      border-radius: 8px;
      box-shadow: 0 12px 32px rgba(20, 30, 40, 0.12);
    }
    .topbar {
      position: fixed;
      left: 16px;
      top: 16px;
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
      max-width: calc(100vw - 32px);
      padding: 9px 10px;
      border: 1px solid var(--edge);
      background: var(--panel);
      backdrop-filter: blur(10px);
      border-radius: 8px;
      box-shadow: 0 12px 32px rgba(20, 30, 40, 0.10);
      color: var(--muted);
      font-size: 13px;
    }
    .metric {
      color: var(--ink);
      font-variant-numeric: tabular-nums;
    }
    button {
      height: 36px;
      min-width: 42px;
      border: 1px solid rgba(15, 118, 110, 0.35);
      border-radius: 7px;
      background: #ffffff;
      color: var(--accent);
      font-size: 15px;
      cursor: pointer;
    }
    button:hover { background: #edf7f5; }
    input[type="range"] {
      width: 100%;
      accent-color: var(--accent);
    }
    select {
      height: 36px;
      border: 1px solid var(--edge);
      border-radius: 7px;
      background: #fff;
      color: var(--ink);
      padding: 0 8px;
    }
    .legend {
      position: fixed;
      right: 16px;
      top: 16px;
      display: grid;
      gap: 5px;
      padding: 10px;
      border: 1px solid var(--edge);
      background: var(--panel);
      backdrop-filter: blur(10px);
      border-radius: 8px;
      color: var(--muted);
      font-size: 12px;
    }
    .legend-row { display: flex; align-items: center; gap: 7px; }
    .swatch { width: 18px; height: 3px; border-radius: 99px; }
    @media (max-width: 720px) {
      .hud {
        grid-template-columns: auto 1fr auto;
        bottom: 10px;
        left: 10px;
        right: 10px;
      }
      .hud select { display: none; }
      .legend { display: none; }
      .topbar { left: 10px; right: 10px; top: 10px; }
    }
  </style>
</head>
<body>
  <canvas id="view"></canvas>
  <div class="topbar">
    <span id="robot-name" class="metric">loading</span>
    <span>frames <span id="frame-count" class="metric">0</span></span>
    <span>freq <span id="freq" class="metric">0.0</span>Hz</span>
    <span>gripper <span id="gripper" class="metric">[0, 0]</span></span>
    <span>chassis <span id="chassis" class="metric">[0, 0, 0]</span></span>
    <span>base <span id="base-pose" class="metric">[0, 0, 0]</span></span>
  </div>
  <div class="legend" id="legend"></div>
  <div class="hud">
    <button id="play" title="Play/Pause">Pause</button>
    <input id="scrub" type="range" min="0" max="0" value="0">
    <span id="frame-label" class="metric">0 / 0</span>
    <select id="speed">
      <option value="0.25">0.25x</option>
      <option value="0.5">0.5x</option>
      <option value="1" selected>1x</option>
      <option value="2">2x</option>
      <option value="4">4x</option>
    </select>
    <button id="reset" title="Reset View">Reset</button>
  </div>
  <script>
    const canvas = document.getElementById('view');
    const ctx = canvas.getContext('2d');
    const playBtn = document.getElementById('play');
    const resetBtn = document.getElementById('reset');
    const scrub = document.getElementById('scrub');
    const speedSelect = document.getElementById('speed');

    const colors = {
      waist: '#425466',
      head: '#7c3aed',
      left_arm: '#0f766e',
      right_arm: '#b45309',
      left_gripper: '#0284c7',
      right_gripper: '#db2777',
      chassis: '#64748b',
      other: '#94a3b8'
    };

    let model = null;
    let frameIndex = 0;
    let playing = true;
    let yaw = -0.75;
    let pitch = 0.42;
    let zoom = 1.0;
    let dragging = false;
    let lastPointer = null;
    let lastTime = performance.now();
    let accumulator = 0;

    function resize() {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.floor(window.innerWidth * dpr);
      canvas.height = Math.floor(window.innerHeight * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw();
    }

    function resetView() {
      yaw = -0.75;
      pitch = 0.42;
      zoom = 1.0;
      draw();
    }

    function rotatePoint(p) {
      const cy = Math.cos(yaw), sy = Math.sin(yaw);
      const cp = Math.cos(pitch), sp = Math.sin(pitch);
      const x1 = cy * p[0] + sy * p[1];
      const y1 = -sy * p[0] + cy * p[1];
      const z1 = p[2];
      return [x1, cp * y1 - sp * z1, sp * y1 + cp * z1];
    }

    function project(p, center, scale) {
      const r = rotatePoint([p[0] - center[0], p[1] - center[1], p[2] - center[2]]);
      return [
        window.innerWidth * 0.5 + r[0] * scale,
        window.innerHeight * 0.53 - r[2] * scale
      ];
    }

    function boundsCenter() {
      const b = model.bounds;
      return [
        (b.min[0] + b.max[0]) / 2,
        (b.min[1] + b.max[1]) / 2,
        (b.min[2] + b.max[2]) / 2
      ];
    }

    function boundsScale() {
      const b = model.bounds;
      const span = Math.max(
        b.max[0] - b.min[0],
        b.max[1] - b.min[1],
        b.max[2] - b.min[2],
        0.1
      );
      return Math.min(window.innerWidth, window.innerHeight) * 0.68 * zoom / span;
    }

    function drawGround(center, scale) {
      ctx.save();
      ctx.lineWidth = 1;
      ctx.strokeStyle = 'rgba(23, 32, 38, 0.12)';
      for (let i = -8; i <= 8; i++) {
        const a = project([center[0] - 1.2, center[1] + i * 0.15, 0], center, scale);
        const b = project([center[0] + 1.2, center[1] + i * 0.15, 0], center, scale);
        ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
        const c = project([center[0] + i * 0.15, center[1] - 1.2, 0], center, scale);
        const d = project([center[0] + i * 0.15, center[1] + 1.2, 0], center, scale);
        ctx.beginPath(); ctx.moveTo(c[0], c[1]); ctx.lineTo(d[0], d[1]); ctx.stroke();
      }
      ctx.restore();
    }

    function draw() {
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      if (!model) return;
      const frame = model.frames[frameIndex];
      const center = boundsCenter();
      const scale = boundsScale();
      drawGround(center, scale);
      drawBasePath(center, scale);

      for (const line of frame.lines) {
        const a = project(line.a, center, scale);
        const b = project(line.b, center, scale);
        const loop = line.type === 'loop';
        ctx.save();
        ctx.strokeStyle = colors[line.category] || colors.other;
        ctx.globalAlpha = loop ? 0.42 : 0.92;
        ctx.lineWidth = loop ? 1.1 : (line.category.includes('gripper') ? 2.4 : 3.2);
        if (loop) ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(a[0], a[1]);
        ctx.lineTo(b[0], b[1]);
        ctx.stroke();
        ctx.restore();
      }

      for (const line of frame.lines) {
        if (line.type === 'loop') continue;
        const b = project(line.b, center, scale);
        ctx.fillStyle = colors[line.category] || colors.other;
        ctx.beginPath();
        ctx.arc(b[0], b[1], 3.2, 0, Math.PI * 2);
        ctx.fill();
      }

      updateLabels();
    }

    function drawBasePath(center, scale) {
      if (!model.base_path || model.base_path.length < 2) return;
      ctx.save();
      ctx.strokeStyle = 'rgba(220, 38, 38, 0.62)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < model.base_path.length; i++) {
        const p = project(model.base_path[i], center, scale);
        if (i === 0) ctx.moveTo(p[0], p[1]);
        else ctx.lineTo(p[0], p[1]);
      }
      ctx.stroke();

      const pose = model.frames[frameIndex].base_pose;
      const current = project([pose[0], pose[1], 0], center, scale);
      ctx.fillStyle = '#dc2626';
      ctx.beginPath();
      ctx.arc(current[0], current[1], 4.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    }

    function updateLabels() {
      if (!model) return;
      const frame = model.frames[frameIndex];
      document.getElementById('frame-label').textContent = `${frameIndex + 1} / ${model.frame_count}`;
      document.getElementById('gripper').textContent = `[${frame.gripper_position.map(v => Number(v).toFixed(3)).join(', ')}]`;
      document.getElementById('chassis').textContent = `[${frame.chassis_velocity.map(v => Number(v).toFixed(3)).join(', ')}]`;
      document.getElementById('base-pose').textContent = `[${frame.base_pose.map(v => Number(v).toFixed(3)).join(', ')}]`;
      scrub.value = String(frameIndex);
    }

    function animate(now) {
      if (model && playing) {
        const dt = (now - lastTime) / 1000;
        accumulator += dt * Number(speedSelect.value);
        const step = 1 / model.action_freq;
        while (accumulator >= step) {
          frameIndex = (frameIndex + 1) % model.frame_count;
          accumulator -= step;
        }
        draw();
      }
      lastTime = now;
      requestAnimationFrame(animate);
    }

    function setupLegend() {
      const legend = document.getElementById('legend');
      legend.innerHTML = '';
      for (const key of ['waist', 'head', 'left_arm', 'right_arm', 'left_gripper', 'right_gripper', 'chassis']) {
        const row = document.createElement('div');
        row.className = 'legend-row';
        const swatch = document.createElement('span');
        swatch.className = 'swatch';
        swatch.style.background = colors[key];
        const label = document.createElement('span');
        label.textContent = key;
        row.appendChild(swatch);
        row.appendChild(label);
        legend.appendChild(row);
      }
    }

    canvas.addEventListener('pointerdown', (event) => {
      dragging = true;
      lastPointer = [event.clientX, event.clientY];
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener('pointermove', (event) => {
      if (!dragging || !lastPointer) return;
      const dx = event.clientX - lastPointer[0];
      const dy = event.clientY - lastPointer[1];
      yaw += dx * 0.008;
      pitch = Math.max(-1.2, Math.min(1.2, pitch + dy * 0.006));
      lastPointer = [event.clientX, event.clientY];
      draw();
    });
    canvas.addEventListener('pointerup', () => {
      dragging = false;
      lastPointer = null;
    });
    canvas.addEventListener('wheel', (event) => {
      event.preventDefault();
      zoom = Math.max(0.25, Math.min(4.0, zoom * Math.exp(-event.deltaY * 0.001)));
      draw();
    }, { passive: false });

    playBtn.addEventListener('click', () => {
      playing = !playing;
      playBtn.textContent = playing ? 'Pause' : 'Play';
    });
    resetBtn.addEventListener('click', resetView);
    scrub.addEventListener('input', () => {
      frameIndex = Number(scrub.value);
      accumulator = 0;
      draw();
    });
    window.addEventListener('resize', resize);

    fetch('/api/model')
      .then((response) => response.json())
      .then((payload) => {
        model = payload;
        frameIndex = 0;
        scrub.max = String(Math.max(0, model.frame_count - 1));
        document.getElementById('robot-name').textContent = model.robot.robot_name;
        document.getElementById('frame-count').textContent = String(model.frame_count);
        document.getElementById('freq').textContent = Number(model.action_freq).toFixed(2);
        setupLegend();
        resize();
        requestAnimationFrame(animate);
      });
  </script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
