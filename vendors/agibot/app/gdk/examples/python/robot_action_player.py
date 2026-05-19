#!/usr/bin/env python3
"""Play joint-style action JSON through GDK robot control APIs.

Input shape:

{
  "actions": [
    {
      "robot_position": {
        "arm_joint_position": [float, ...],   # 14, left arm then right arm
        "head_joint_position": [float, ...],  # 3
        "waist_joint_position": [float, ...]  # 5
      },
      "gripper_position": [float, float],
      "chassis_velocity": [float, float, float]
    }
  ],
  "action_type": "joint",
  "action_freq": 30.0
}
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable

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
BODY_JOINT_NAMES = WAIST_JOINT_NAMES + HEAD_JOINT_NAMES + ARM_JOINT_NAMES

DEFAULT_ACTION_FREQ = 30.0
DEFAULT_INIT_WAIT_S = 1.0
DEFAULT_PLANNING_LIFE_TIME = 0.1
DEFAULT_PLANNING_VELOCITY = 0.3
DEFAULT_MAX_INITIAL_DELTA = 0.35
DEFAULT_MAX_STEP_DELTA = 0.2
DEFAULT_MAX_SERVO_VELOCITY = 1.0
DEFAULT_SPEED_SCALE = 1.0
DEFAULT_CHASSIS_DEADBAND = 1e-3

ANSI_RED = "\033[31m"
ANSI_YELLOW = "\033[33m"
ANSI_RESET = "\033[0m"


def _format_gdk_result(result: Any) -> str:
    return getattr(result, "name", str(result))


def _color(text: str, color: str) -> str:
    if "NO_COLOR" in os.environ:
        return text
    return f"{color}{text}{ANSI_RESET}"


def _error(message: str) -> None:
    print(_color(f"[ERROR] {message}", ANSI_RED), file=sys.stderr)


def _warn(message: str) -> None:
    print(_color(f"[WARN] {message}", ANSI_YELLOW), file=sys.stderr)


def _ensure_gdk() -> Any:
    global agibot_gdk
    if agibot_gdk is None:
        import agibot_gdk as loaded_gdk

        agibot_gdk = loaded_gdk
    return agibot_gdk


def _load_action_file(path: str) -> dict[str, Any]:
    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _as_float_list(value: Any, expected_len: int, field_name: str) -> list[float]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    if len(value) != expected_len:
        raise ValueError(f"{field_name} must have length {expected_len}, got {len(value)}")
    result = [float(item) for item in value]
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{field_name} contains non-finite value")
    return result


def _validate_payload(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], float]:
    if payload.get("action_type") != "joint":
        raise ValueError(f"only action_type='joint' is supported, got {payload.get('action_type')!r}")

    actions = payload.get("actions")
    if not isinstance(actions, list) or not actions:
        raise ValueError("actions must be a non-empty list")
    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            raise ValueError(f"actions[{index}] must be a dict")
        _body_joint_target(action, index)
        if "gripper_position" in action:
            _as_float_list(action["gripper_position"], 2, f"actions[{index}].gripper_position")
        if "chassis_velocity" in action:
            _as_float_list(action["chassis_velocity"], 3, f"actions[{index}].chassis_velocity")

    freq = float(payload.get("action_freq") or DEFAULT_ACTION_FREQ)
    if not math.isfinite(freq) or freq <= 0:
        raise ValueError(f"action_freq must be > 0, got {freq!r}")
    return actions, freq


def _body_joint_target(action: dict[str, Any], index: int) -> tuple[list[str], list[float]]:
    robot_position = action.get("robot_position") or {}
    if not isinstance(robot_position, dict):
        raise ValueError(f"actions[{index}].robot_position must be a dict")

    names: list[str] = []
    positions: list[float] = []

    if "waist_joint_position" in robot_position:
        names.extend(WAIST_JOINT_NAMES)
        positions.extend(
            _as_float_list(
                robot_position["waist_joint_position"],
                len(WAIST_JOINT_NAMES),
                f"actions[{index}].robot_position.waist_joint_position",
            )
        )
    if "head_joint_position" in robot_position:
        names.extend(HEAD_JOINT_NAMES)
        positions.extend(
            _as_float_list(
                robot_position["head_joint_position"],
                len(HEAD_JOINT_NAMES),
                f"actions[{index}].robot_position.head_joint_position",
            )
        )
    if "arm_joint_position" in robot_position:
        names.extend(ARM_JOINT_NAMES)
        positions.extend(
            _as_float_list(
                robot_position["arm_joint_position"],
                len(ARM_JOINT_NAMES),
                f"actions[{index}].robot_position.arm_joint_position",
            )
        )

    return names, positions


def _current_body_positions(robot: Any, joint_names: Iterable[str]) -> dict[str, float]:
    joint_states = robot.get_joint_states()
    by_name = {state["name"]: float(state["position"]) for state in joint_states["states"]}
    return {name: by_name[name] for name in joint_names if name in by_name}


def _initial_delta_summary(
    robot: Any,
    first_action: dict[str, Any],
) -> tuple[str, float, float, float]:
    names, target_positions = _body_joint_target(first_action, 0)
    if not names:
        return "", 0.0, 0.0, 0.0

    current = _current_body_positions(robot, names)
    missing = [name for name in names if name not in current]
    if missing:
        raise RuntimeError(f"current joint state is missing joints: {', '.join(missing)}")

    deltas = [
        (name, current[name], target, abs(target - current[name]))
        for name, target in zip(names, target_positions)
    ]
    return max(deltas, key=lambda item: item[3])


def _check_initial_delta(
    robot: Any,
    first_action: dict[str, Any],
    *,
    max_initial_delta: float,
) -> None:
    worst_name, current_value, target_value, worst_delta = _initial_delta_summary(robot, first_action)
    if worst_delta > max_initial_delta:
        message = (
            "first action is too far from current robot state: "
            f"{worst_name} current={current_value:.6f}, target={target_value:.6f}, "
            f"delta={worst_delta:.6f} > {max_initial_delta:.6f}. "
            "Use --allow-large-initial-jump only after checking the target is safe."
        )
        _error(message)
        raise RuntimeError(message)


def _check_step_delta(
    prev_positions: dict[str, float],
    names: list[str],
    positions: list[float],
    *,
    max_step_delta: float,
) -> None:
    if not prev_positions:
        return
    for name, target in zip(names, positions):
        if name not in prev_positions:
            continue
        delta = abs(target - prev_positions[name])
        if delta > max_step_delta:
            message = (
                f"step target for {name} changes too much: "
                f"delta={delta:.6f} > {max_step_delta:.6f}"
            )
            _error(message)
            raise RuntimeError(message)


def _clamp(value: float, limit: float) -> float:
    return max(-limit, min(limit, value))


def _compute_joint_velocities(
    prev_positions: dict[str, float],
    names: list[str],
    positions: list[float],
    period_s: float,
    max_velocity: float,
) -> list[float]:
    if not prev_positions:
        return [0.0] * len(names)
    velocities: list[float] = []
    for name, target in zip(names, positions):
        prev = prev_positions.get(name, target)
        velocities.append(_clamp((target - prev) / period_s, max_velocity))
    return velocities


def _send_body_servo(
    robot: Any,
    names: list[str],
    positions: list[float],
    velocities: list[float],
    *,
    period_s: float,
    enable_low_latency: bool,
) -> None:
    gdk = _ensure_gdk()
    req = gdk.JointServoControlReq()
    req.control_period = period_s
    req.joint_names = names
    req.joint_positions = positions
    req.joint_velocities = velocities
    try:
        result = robot.joint_servo_control(req, enable_low_latency=enable_low_latency)
    except Exception as exc:  # noqa: BLE001 - surface GDK command failure clearly
        _error(f"joint_servo_control failed: {exc}")
        raise
    if result not in (0, gdk.GDKRes.kSuccess):
        message = f"joint_servo_control failed: result={_format_gdk_result(result)}"
        _error(message)
        raise RuntimeError(message)


def _send_body_planning(
    robot: Any,
    names: list[str],
    positions: list[float],
    *,
    life_time: float,
    velocity: float,
) -> None:
    gdk = _ensure_gdk()
    req = gdk.JointControlReq()
    req.life_time = life_time
    req.joint_names = names
    req.joint_positions = positions
    req.joint_velocities = [velocity] * len(names)
    try:
        result = robot.joint_control_request(req)
    except Exception as exc:  # noqa: BLE001 - surface GDK command failure clearly
        _error(f"joint_control_request failed: {exc}")
        raise
    print(f"body planning request result={_format_gdk_result(result)} joints={len(names)}")


def _action_has_gripper(actions: list[dict[str, Any]]) -> bool:
    return any("gripper_position" in action for action in actions)


def _end_effector_joint_names_by_side(robot: Any) -> dict[str, list[str]]:
    end_state = robot.get_end_state()
    result: dict[str, list[str]] = {}
    for side in ("left", "right"):
        key = f"{side}_end_state"
        side_state = end_state.get(key)
        if not isinstance(side_state, dict):
            raise RuntimeError(f"get_end_state() missing {key}")
        names = side_state.get("names") or []
        states = side_state.get("end_states") or []
        if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
            raise RuntimeError(f"{key}.names must be a list of strings")
        if not names:
            raise RuntimeError(f"{key}.names is empty; cannot servo {side} gripper")
        if states and len(states) != len(names):
            raise RuntimeError(
                f"{key}.names length {len(names)} does not match end_states length {len(states)}"
            )
        result[side] = names
    return result


def _extend_gripper_servo_targets(
    names: list[str],
    positions: list[float],
    *,
    ee_joint_names_by_side: dict[str, list[str]],
    left_position: float,
    right_position: float,
    force_zero: bool,
) -> None:
    for side, position in (("left", left_position), ("right", right_position)):
        command_position = 0.0 if force_zero else position
        side_names = ee_joint_names_by_side[side]
        names.extend(side_names)
        positions.extend([command_position] * len(side_names))


def _send_gripper(robot: Any, side: str, position: float, target_type: str) -> None:
    gdk = _ensure_gdk()
    joint_states = gdk.JointStates()
    joint_states.group = f"{side}_tool"
    joint_states.target_type = target_type
    state = gdk.JointState()
    state.position = position
    joint_states.states = [state]
    joint_states.nums = 1
    try:
        result = robot.move_ee_pos(joint_states)
    except Exception as exc:  # noqa: BLE001 - surface GDK command failure clearly
        _error(
            f"{side} gripper move_ee_pos failed: target_type={target_type} "
            f"position={position:.6f}, error={exc}"
        )
        raise
    print(
        f"{side} gripper request result={_format_gdk_result(result)} "
        f"target_type={target_type} position={position:.6f}"
    )


def _make_twist(vx: float, vy: float, wz: float) -> Any:
    gdk = _ensure_gdk()
    twist = gdk.Twist()
    twist.linear = gdk.Vector3()
    twist.angular = gdk.Vector3()
    twist.linear.x = vx
    twist.linear.y = vy
    twist.linear.z = 0.0
    twist.angular.x = 0.0
    twist.angular.y = 0.0
    twist.angular.z = wz
    return twist


def _send_chassis_velocity(pnc: Any, velocity: list[float]) -> None:
    pnc.move_chassis(_make_twist(velocity[0], velocity[1], velocity[2]))


def _stop_chassis(pnc: Any | None) -> None:
    if pnc is not None:
        try:
            _send_chassis_velocity(pnc, [0.0, 0.0, 0.0])
        except Exception as exc:  # noqa: BLE001 - best-effort stop
            _warn(f"failed to send chassis stop: {exc}")


def _action_has_chassis(actions: list[dict[str, Any]]) -> bool:
    return any("chassis_velocity" in action for action in actions)


def _action_has_active_chassis(actions: list[dict[str, Any]], deadband: float) -> bool:
    for action in actions:
        if "chassis_velocity" not in action:
            continue
        velocity = _as_float_list(action["chassis_velocity"], 3, "chassis_velocity")
        if any(abs(value) > deadband for value in velocity):
            return True
    return False


def _print_gripper_range_summary(
    actions: list[dict[str, Any]],
    *,
    start_index: int,
    force_zero: bool,
) -> None:
    mins = {"left": math.inf, "right": math.inf}
    maxs = {"left": -math.inf, "right": -math.inf}
    command_mins = {"left": math.inf, "right": math.inf}
    command_maxs = {"left": -math.inf, "right": -math.inf}
    seen = False
    command_seen = {"left": False, "right": False}

    for offset, action in enumerate(actions):
        if "gripper_position" not in action:
            continue
        seen = True
        left_position, right_position = _as_float_list(
            action["gripper_position"],
            2,
            f"actions[{start_index + offset}].gripper_position",
        )
        for side, position in (("left", left_position), ("right", right_position)):
            mins[side] = min(mins[side], position)
            maxs[side] = max(maxs[side], position)
            if force_zero:
                command_position = 0.0
            else:
                command_position = position
            command_seen[side] = True
            command_mins[side] = min(command_mins[side], command_position)
            command_maxs[side] = max(command_maxs[side], command_position)

    if not seen:
        return
    left_command_range = (
        f"[{command_mins['left']:.6f}, {command_maxs['left']:.6f}]"
        if command_seen["left"]
        else "none"
    )
    right_command_range = (
        f"[{command_mins['right']:.6f}, {command_maxs['right']:.6f}]"
        if command_seen["right"]
        else "none"
    )
    command_range = f"commanded_left={left_command_range} commanded_right={right_command_range}"
    print(
        "gripper_range "
        f"json_left=[{mins['left']:.6f}, {maxs['left']:.6f}] "
        f"json_right=[{mins['right']:.6f}, {maxs['right']:.6f}] "
        f"handling={'force_zero' if force_zero else 'direct'} "
        f"{command_range}"
    )


def _print_body_step_summary(
    actions: list[dict[str, Any]],
    *,
    start_index: int,
    hz: float,
) -> None:
    max_delta = 0.0
    max_index = start_index
    max_joint = ""
    prev_positions_by_name: dict[str, float] = {}

    for offset, action in enumerate(actions):
        index = start_index + offset
        names, positions = _body_joint_target(action, index)
        if prev_positions_by_name:
            for name, position in zip(names, positions):
                if name not in prev_positions_by_name:
                    continue
                delta = abs(position - prev_positions_by_name[name])
                if delta > max_delta:
                    max_delta = delta
                    max_index = index
                    max_joint = name
        prev_positions_by_name = dict(zip(names, positions))

    if max_joint:
        print(
            "body_step_summary "
            f"max_adjacent_delta={max_delta:.6f} rad "
            f"at_action={max_index} joint={max_joint} "
            f"equiv_velocity={max_delta * hz:.6f} rad/s"
        )


def _print_action_summary(index: int, action: dict[str, Any]) -> None:
    names, positions = _body_joint_target(action, index)
    gripper = action.get("gripper_position")
    chassis = action.get("chassis_velocity")
    print(
        f"[action {index}] body_joints={len(names)} "
        f"gripper={'yes' if gripper is not None else 'no'} "
        f"chassis={'yes' if chassis is not None else 'no'}"
    )
    if names:
        print(f"  first_joint={names[0]} target={positions[0]:.6f}")
    if gripper is not None:
        print(f"  gripper={gripper}")
    if chassis is not None:
        print(f"  chassis_velocity={chassis}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Play joint action JSON through agibot_gdk Robot/Pnc control APIs.",
    )
    parser.add_argument("input", help="Action JSON file path, or '-' for stdin.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually send commands to the robot. Omit for validation-only dry run.",
    )
    parser.add_argument(
        "--mode",
        choices=["servo", "planning"],
        default="servo",
        help="servo streams actions at action_freq; planning sends JointControlReq targets.",
    )
    parser.add_argument(
        "--move-to-first",
        action="store_true",
        help=(
            "Move from the current robot state to actions[0] once using "
            "Robot.joint_control_request(); no 30Hz streaming and no chassis command."
        ),
    )
    parser.add_argument("--hz", type=float, help="Override payload action_freq.")
    parser.add_argument(
        "--speed-scale",
        type=float,
        default=DEFAULT_SPEED_SCALE,
        help=(
            "Playback speed multiplier when --hz is not set. "
            "Use 0.5 for half speed, 1.0 for payload action_freq."
        ),
    )
    parser.add_argument("--start-index", type=int, default=0, help="First action index to play.")
    parser.add_argument("--count", type=int, help="Maximum number of actions to play.")
    parser.add_argument("--init-wait-s", type=float, default=DEFAULT_INIT_WAIT_S)
    parser.add_argument("--no-body", action="store_true", help="Do not command body joints.")
    parser.add_argument("--no-gripper", action="store_true", help="Do not command grippers.")
    parser.add_argument("--no-chassis", action="store_true", help="Do not command chassis velocity.")
    parser.add_argument(
        "--chassis-deadband",
        type=float,
        default=DEFAULT_CHASSIS_DEADBAND,
        help="Do not request chassis control unless any chassis velocity exceeds this absolute value.",
    )
    parser.add_argument(
        "--ignore-chassis-control-failure",
        action="store_true",
        help="If Pnc.request_chassis_control() fails, continue playing body/gripper commands without chassis.",
    )
    parser.add_argument(
        "--chassis-control-mode",
        type=int,
        choices=[0, 1],
        default=0,
        help="Passed to Pnc.request_chassis_control(); 0 follows local example default, 1 is crab mode.",
    )
    parser.add_argument(
        "--gripper-target-type",
        default="omnipicker",
        help="JointStates.target_type used by move_ee_pos() in planning mode.",
    )
    parser.add_argument(
        "--force-gripper-zero",
        "--zero-gripper",
        action="store_true",
        dest="force_gripper_zero",
        help="Ignore JSON gripper values and command both grippers to 0.0.",
    )
    parser.add_argument(
        "--planning-life-time",
        type=float,
        default=DEFAULT_PLANNING_LIFE_TIME,
        help="JointControlReq.life_time in planning mode.",
    )
    parser.add_argument(
        "--planning-velocity",
        type=float,
        default=DEFAULT_PLANNING_VELOCITY,
        help="Per-joint velocity used in planning mode.",
    )
    parser.add_argument(
        "--enable-low-latency",
        action="store_true",
        help="Enable low latency flag for joint_servo_control().",
    )
    parser.add_argument(
        "--max-servo-velocity",
        type=float,
        default=DEFAULT_MAX_SERVO_VELOCITY,
        help="Clamp computed servo joint velocities.",
    )
    parser.add_argument(
        "--max-initial-delta",
        type=float,
        default=DEFAULT_MAX_INITIAL_DELTA,
        help="Abort if first target differs from current joint state by more than this many rad.",
    )
    parser.add_argument(
        "--max-step-delta",
        type=float,
        default=DEFAULT_MAX_STEP_DELTA,
        help="Abort if adjacent action targets differ by more than this many rad.",
    )
    parser.add_argument(
        "--allow-large-initial-jump",
        action="store_true",
        help="Disable first-target-vs-current safety check.",
    )
    parser.add_argument(
        "--allow-large-step",
        action="store_true",
        help="Disable adjacent-action delta safety check.",
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce per-action logging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = _load_action_file(args.input)
    actions, payload_freq = _validate_payload(payload)

    if args.move_to_first:
        control_mode = "planning"
        selected_actions = actions[:1]
        start_index = 0
    else:
        if args.start_index < 0:
            print("--start-index must be >= 0", file=sys.stderr)
            return 2
        if args.start_index >= len(actions):
            print("--start-index is outside actions", file=sys.stderr)
            return 2
        if args.count is not None and args.count < 1:
            print("--count must be >= 1", file=sys.stderr)
            return 2

        control_mode = args.mode
        start_index = args.start_index
        selected_actions = actions[start_index:]
        if args.count is not None:
            selected_actions = selected_actions[: args.count]

    if not math.isfinite(args.speed_scale) or args.speed_scale <= 0:
        print("--speed-scale must be > 0", file=sys.stderr)
        return 2
    if args.chassis_deadband < 0:
        print("--chassis-deadband must be >= 0", file=sys.stderr)
        return 2

    hz = float(args.hz) if args.hz is not None else float(payload_freq) * args.speed_scale
    if not math.isfinite(hz) or hz <= 0:
        print("hz/action_freq must be > 0", file=sys.stderr)
        return 2
    period_s = 1.0 / hz

    print(
        f"loaded actions={len(actions)}, selected={len(selected_actions)}, "
        f"payload_freq={payload_freq:.3f}Hz, playback_hz={hz:.3f}Hz, "
        f"speed_scale={args.speed_scale:.3f}, mode={control_mode}, "
        f"execute={args.execute}, move_to_first={args.move_to_first}, "
        f"force_gripper_zero={args.force_gripper_zero}"
    )
    if not args.quiet:
        _print_body_step_summary(selected_actions, start_index=start_index, hz=hz)
        _print_gripper_range_summary(
            selected_actions,
            start_index=start_index,
            force_zero=args.force_gripper_zero,
        )

    if not args.execute:
        print("dry run only; add --execute to send commands to the robot")
        if not args.quiet:
            for offset, action in enumerate(selected_actions[:5]):
                _print_action_summary(start_index + offset, action)
            if len(selected_actions) > 5:
                print(f"... {len(selected_actions) - 5} more action(s)")
        return 0

    gdk = _ensure_gdk()
    if gdk.gdk_init() != gdk.GDKRes.kSuccess:
        print("failed to initialize GDK", file=sys.stderr)
        return 1

    robot: Any | None = None
    pnc: Any | None = None
    prev_positions: dict[str, float] = {}
    try:
        robot = gdk.Robot()
        use_servo_gripper = (
            control_mode == "servo"
            and not args.no_gripper
            and _action_has_gripper(selected_actions)
        )
        ee_joint_names_by_side: dict[str, list[str]] = {}
        use_chassis = (
            not args.no_chassis
            and not args.move_to_first
            and _action_has_active_chassis(selected_actions, args.chassis_deadband)
        )
        if not args.no_chassis and not args.move_to_first and _action_has_chassis(selected_actions) and not use_chassis:
            print(
                "chassis velocities are within deadband; skip chassis control request "
                f"(deadband={args.chassis_deadband})"
            )
        if use_chassis:
            pnc = gdk.Pnc()

        time.sleep(args.init_wait_s)

        if use_servo_gripper:
            ee_joint_names_by_side = _end_effector_joint_names_by_side(robot)
            print(
                "servo gripper via joint_servo_control "
                f"left={ee_joint_names_by_side['left']} "
                f"right={ee_joint_names_by_side['right']}"
            )

        if use_chassis:
            try:
                pnc.request_chassis_control(args.chassis_control_mode)
                time.sleep(0.2)
            except Exception as exc:  # noqa: BLE001 - optional chassis path
                if not args.ignore_chassis_control_failure:
                    raise
                _warn(
                    "failed to request chassis control; continue without chassis: "
                    f"{exc}"
                )
                use_chassis = False
                pnc = None

        if not args.no_body:
            worst_name, current_value, target_value, worst_delta = _initial_delta_summary(
                robot,
                selected_actions[0],
            )
            if worst_name:
                print(
                    "current->first max_joint_delta "
                    f"{worst_name}: current={current_value:.6f}, "
                    f"target={target_value:.6f}, delta={worst_delta:.6f} rad"
                )
            if not args.allow_large_initial_jump:
                _check_initial_delta(
                    robot,
                    selected_actions[0],
                    max_initial_delta=args.max_initial_delta,
                )

        for offset, action in enumerate(selected_actions):
            index = start_index + offset
            started = time.monotonic()
            body_names, body_positions = _body_joint_target(action, index)
            servo_names: list[str] = []
            servo_positions: list[float] = []

            if not args.no_body and body_names:
                if not args.allow_large_step:
                    _check_step_delta(
                        prev_positions,
                        body_names,
                        body_positions,
                        max_step_delta=args.max_step_delta,
                    )
                if control_mode == "servo":
                    servo_names.extend(body_names)
                    servo_positions.extend(body_positions)
                else:
                    _send_body_planning(
                        robot,
                        body_names,
                        body_positions,
                        life_time=args.planning_life_time,
                        velocity=args.planning_velocity,
                    )

            if not args.no_gripper and "gripper_position" in action:
                left_gripper, right_gripper = _as_float_list(
                    action["gripper_position"],
                    2,
                    f"actions[{index}].gripper_position",
                )
                if control_mode == "servo":
                    _extend_gripper_servo_targets(
                        servo_names,
                        servo_positions,
                        ee_joint_names_by_side=ee_joint_names_by_side,
                        left_position=left_gripper,
                        right_position=right_gripper,
                        force_zero=args.force_gripper_zero,
                    )
                else:
                    for side, position in (("left", left_gripper), ("right", right_gripper)):
                        command_position = 0.0 if args.force_gripper_zero else position
                        _send_gripper(robot, side, command_position, args.gripper_target_type)

            if control_mode == "servo" and servo_names:
                velocities = _compute_joint_velocities(
                    prev_positions,
                    servo_names,
                    servo_positions,
                    period_s,
                    args.max_servo_velocity,
                )
                _send_body_servo(
                    robot,
                    servo_names,
                    servo_positions,
                    velocities,
                    period_s=period_s,
                    enable_low_latency=args.enable_low_latency,
                )
                prev_positions = dict(zip(servo_names, servo_positions))
            elif control_mode != "servo" and not args.no_body and body_names:
                prev_positions = dict(zip(body_names, body_positions))

            if use_chassis and "chassis_velocity" in action:
                velocity = _as_float_list(
                    action["chassis_velocity"],
                    3,
                    f"actions[{index}].chassis_velocity",
                )
                if all(abs(value) <= args.chassis_deadband for value in velocity):
                    velocity = [0.0, 0.0, 0.0]
                if args.chassis_control_mode == 0 and abs(velocity[1]) > 1e-6:
                    _warn(
                        "chassis_control_mode=0 may ignore linear.y; "
                        "use --chassis-control-mode 1 for crab-mode lateral velocity"
                    )
                _send_chassis_velocity(pnc, velocity)

            if not args.quiet:
                _print_action_summary(index, action)

            elapsed = time.monotonic() - started
            sleep_s = period_s - elapsed
            if sleep_s > 0 and offset + 1 < len(selected_actions):
                time.sleep(sleep_s)
            elif sleep_s <= 0:
                _warn(
                    f"action {index} overrun elapsed={elapsed:.4f}s "
                    f"period={period_s:.4f}s"
                )

        _stop_chassis(pnc)
        return 0
    finally:
        _stop_chassis(pnc)
        if gdk.gdk_release() != gdk.GDKRes.kSuccess:
            print("failed to release GDK", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
