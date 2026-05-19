#!/usr/bin/env python3
"""
Move the robot backward by 10 cm through map-based PNC navigation.

The default behavior reads the current SLAM odom pose, computes a target point
10 cm behind the robot in the map frame, then calls Pnc.normal_navi().
"""

import argparse
import math
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
GDK_ROOT = SCRIPT_PATH.parents[4]
APP_ROOT = GDK_ROOT.parent
BOOTSTRAP_MARKER = "AGIBOT_GDK_NAV_BOOTSTRAPPED"


TASK_STATES = {
    0: "idle",
    1: "starting",
    2: "running",
    3: "pausing",
    4: "paused",
    5: "resuming",
    6: "canceling",
    7: "canceled",
    8: "failed",
    9: "success",
}

TASK_READY_STATES = {0, 7, 8, 9}


def prepend_env_path(env, key, paths):
    current = [item for item in env.get(key, "").split(os.pathsep) if item]
    values = []
    for path in paths:
        path_str = str(path)
        if path_str not in values and path_str not in current:
            values.append(path_str)
    env[key] = os.pathsep.join(values + current)


def shared_library_dirs(root):
    if not root.exists():
        return []

    dirs = []
    for dirpath, _, filenames in os.walk(root):
        if any(name.endswith(".so") or ".so." in name for name in filenames):
            dirs.append(Path(dirpath))
    return dirs


def find_robot_locator_ip():
    try:
        result = subprocess.run(
            ["ip", "-o", "-4", "addr", "list"],
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
    except Exception:
        return None

    for line in result.stdout.splitlines():
        for field in line.split():
            if field.startswith("10.42.1.") and "/" in field:
                return field.split("/", 1)[0]
    return None


def build_gdk_env():
    env = os.environ.copy()
    prepend_env_path(env, "PYTHONPATH", [GDK_ROOT / "lib"])
    prepend_env_path(env, "LD_LIBRARY_PATH", shared_library_dirs(APP_ROOT / "lib"))
    prepend_env_path(env, "PATH", [APP_ROOT / "bin"])

    env.setdefault("APP_CONF_PATH", str(GDK_ROOT / "config" / "app_conf.yml"))
    env.setdefault("AORTA_DISPATCHER_THREAD_NUM", "6")

    if "LOCATOR_IP" not in env:
        locator_ip = find_robot_locator_ip()
        if locator_ip:
            env["LOCATOR_IP"] = locator_ip

    if "LOCATOR_IP" in env:
        env.setdefault("AORTA_DISCOVERY_URI", "http://10.42.1.101:2379")

    env[BOOTSTRAP_MARKER] = "1"
    return env


def ensure_gdk_runtime():
    env = build_gdk_env()
    running_python = Path(sys.executable).resolve()

    if sys.version_info[:2] != (3, 10):
        python310 = shutil.which("python3.10")
        if not python310:
            print(
                "This GDK package contains a Python 3.10 agibot_gdk extension, "
                f"but the current interpreter is Python {sys.version_info.major}."
                f"{sys.version_info.minor}. Install or activate python3.10 first."
            )
            raise SystemExit(1)

        os.execvpe(python310, [python310, str(SCRIPT_PATH), *sys.argv[1:]], env)

    if os.environ.get(BOOTSTRAP_MARKER) != "1":
        os.execvpe(
            str(running_python),
            [str(running_python), str(SCRIPT_PATH), *sys.argv[1:]],
            env,
        )

    python_lib = str(GDK_ROOT / "lib")
    if python_lib not in sys.path:
        sys.path.insert(0, python_lib)


ensure_gdk_runtime()


def quaternion_to_yaw(orientation):
    return math.atan2(
        2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
        1.0 - 2.0 * (orientation.y * orientation.y + orientation.z * orientation.z),
    )


def unwrap_pose(pose_like):
    if hasattr(pose_like, "position") and hasattr(pose_like, "orientation"):
        return pose_like
    if hasattr(pose_like, "pose"):
        return unwrap_pose(pose_like.pose)
    raise AttributeError("pose object has no position/orientation fields")


def get_odom_pose(slam):
    odom = slam.get_odom_info()
    return unwrap_pose(odom.pose), odom


def describe_pose(prefix, pose, odom=None):
    yaw = quaternion_to_yaw(pose.orientation)
    parts = [
        prefix,
        f"pos=({pose.position.x:.3f}, {pose.position.y:.3f}, {pose.position.z:.3f}) m",
        (
            "quat=("
            f"{pose.orientation.x:.4f}, {pose.orientation.y:.4f}, "
            f"{pose.orientation.z:.4f}, {pose.orientation.w:.4f})"
        ),
        f"yaw={yaw:.3f} rad",
    ]
    if odom is not None:
        parts.extend(
            [
                f"loc_state={getattr(odom, 'loc_state', 'n/a')}",
                f"confidence={getattr(odom, 'loc_confidence', 'n/a')}",
            ]
        )
    return " | ".join(parts)


def planar_distance(a, b):
    return math.hypot(a.position.x - b.position.x, a.position.y - b.position.y)


def point_distance(pose, x, y):
    return math.hypot(pose.position.x - x, pose.position.y - y)


def make_navi_req(agibot_gdk, x, y, z, orientation=None):
    req = agibot_gdk.NaviReq()
    req.timestamp_ns = time.time_ns()
    req.target.position.x = x
    req.target.position.y = y
    req.target.position.z = z

    if orientation is None:
        req.target.orientation.x = 0.0
        req.target.orientation.y = 0.0
        req.target.orientation.z = 0.0
        req.target.orientation.w = 1.0
    else:
        req.target.orientation.x = orientation.x
        req.target.orientation.y = orientation.y
        req.target.orientation.z = orientation.z
        req.target.orientation.w = orientation.w

    return req


def wait_for_task(pnc, timeout):
    deadline = time.monotonic() + timeout
    last_line = None

    while time.monotonic() < deadline:
        task = pnc.get_task_state()
        state_name = TASK_STATES.get(task.state, f"unknown({task.state})")
        line = (
            f"task_id={task.id} state={state_name}({task.state}) "
            f"type={task.type} message={task.message}"
        )
        if line != last_line:
            print(line)
            last_line = line

        if task.state in TASK_READY_STATES:
            return task

        time.sleep(0.5)

    return pnc.get_task_state()


def wait_for_navigation(pnc, slam, start_pose, target_x, target_y, requested_distance, timeout, max_overshoot):
    deadline = time.monotonic() + timeout
    last_task_line = None
    last_report = 0.0

    while time.monotonic() < deadline:
        task = pnc.get_task_state()
        state_name = TASK_STATES.get(task.state, f"unknown({task.state})")
        task_line = (
            f"task_id={task.id} state={state_name}({task.state}) "
            f"type={task.type} message={task.message}"
        )
        if task_line != last_task_line:
            print(task_line)
            last_task_line = task_line

        try:
            pose, odom = get_odom_pose(slam)
            traveled = planar_distance(start_pose, pose)
            remaining = point_distance(pose, target_x, target_y)
            now = time.monotonic()
            if now - last_report >= 0.5:
                print(
                    "progress: "
                    f"traveled={traveled:.3f} m, remaining_to_target={remaining:.3f} m, "
                    f"loc_state={getattr(odom, 'loc_state', 'n/a')}, "
                    f"confidence={getattr(odom, 'loc_confidence', 'n/a')}"
                )
                last_report = now

            if traveled > requested_distance + max_overshoot and task.state not in TASK_READY_STATES:
                print(
                    "WARN: traveled distance exceeded guard threshold "
                    f"({traveled:.3f} m > {requested_distance + max_overshoot:.3f} m). "
                    f"Canceling task {task.id}."
                )
                pnc.cancel_task(task.id)
                return wait_until_task_ready(pnc, 5.0)
        except Exception as exc:
            print(f"WARN: failed to monitor pose during navigation: {exc}")

        if task.state in TASK_READY_STATES:
            return task

        time.sleep(0.2)

    return pnc.get_task_state()


def wait_until_task_ready(pnc, timeout):
    deadline = time.monotonic() + timeout
    last_line = None

    while time.monotonic() < deadline:
        task = pnc.get_task_state()
        state_name = TASK_STATES.get(task.state, f"unknown({task.state})")
        line = (
            f"task_id={task.id} state={state_name}({task.state}) "
            f"type={task.type} message={task.message}"
        )
        if line != last_line:
            print(f"Waiting for PNC ready: {line}")
            last_line = line

        if task.state in TASK_READY_STATES:
            return task

        time.sleep(0.5)

    return pnc.get_task_state()


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Read current SLAM pose, compute a map-frame target 10 cm behind "
            "the robot, then call Pnc.normal_navi."
        )
    )
    parser.add_argument(
        "--distance",
        type=float,
        default=0.10,
        help="Backward distance in meters. Default: 0.10",
    )
    parser.add_argument(
        "--mode",
        choices=["relative", "normal"],
        default="normal",
        help=(
            "normal computes a map-frame target and uses Pnc.normal_navi. "
            "relative uses Pnc.relative_move. Default: normal"
        ),
    )
    parser.add_argument(
        "--start-mapping",
        action="store_true",
        help=(
            "Do not use for navigation. Kept only to make the conflict explicit: "
            "mapping occupies PNC and blocks normal_navi."
        ),
    )
    parser.add_argument(
        "--init-wait",
        type=float,
        default=2.0,
        help="Seconds to wait after creating Slam/Pnc. Default: 2.0",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Seconds to wait for task state after sending command. Default: 20",
    )
    parser.add_argument(
        "--max-overshoot",
        type=float,
        default=0.03,
        help="Cancel navigation if planar travel exceeds distance + this value. Default: 0.03",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Send command and exit without waiting for task state.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.distance <= 0.0:
        raise ValueError("--distance must be greater than 0")
    if args.timeout <= 0.0:
        raise ValueError("--timeout must be greater than 0")
    if args.max_overshoot < 0.0:
        raise ValueError("--max-overshoot must be greater than or equal to 0")
    if args.start_mapping:
        print(
            "ERROR: --start-mapping starts a mapping task, which occupies PNC. "
            "Map-based normal_navi requires the robot to already be localized "
            "with PNC idle. Run this script without --start-mapping."
        )
        return 1

    if "LOCATOR_IP" not in os.environ:
        print(
            "WARN: no 10.42.1.* network address found. "
            "GDK may not communicate with the robot until the robot network is ready."
        )

    import agibot_gdk

    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK init failed")
        return 1

    mapping_started = False
    command_sent = False
    pnc = None

    try:
        slam = agibot_gdk.Slam()
        pnc = agibot_gdk.Pnc()
        time.sleep(args.init_wait)

        if args.start_mapping:
            print("Starting SLAM mapping before navigation...")
            slam.start_mapping()
            mapping_started = True
            time.sleep(1.0)

        current_pose = None
        current_odom = None
        try:
            current_pose, current_odom = get_odom_pose(slam)
            print(describe_pose("Current pose", current_pose, current_odom))
        except Exception as exc:
            if args.mode == "normal":
                raise RuntimeError(
                    "normal mode needs current SLAM odom pose. "
                    "Try adding --start-mapping first."
                ) from exc
            print(f"WARN: current pose unavailable: {exc}")

        if args.mode == "relative":
            req = make_navi_req(agibot_gdk, -args.distance, 0.0, 0.0)
            action_desc = (
                f"Pnc.relative_move: backward {args.distance:.3f} m "
                "in robot body frame"
            )
        else:
            yaw = quaternion_to_yaw(current_pose.orientation)
            # target_x = current_pose.position.x - args.distance * math.cos(yaw)
            # target_y = current_pose.position.y - args.distance * math.sin(yaw)
            # target_z = current_pose.position.z
            # delta_x = target_x - current_pose.position.x
            # delta_y = target_y - current_pose.position.y
            # target_distance = math.hypot(delta_x, delta_y)
            target_x = current_pose.position.x + 0.0
            target_y = current_pose.position.y
            target_z = current_pose.position.z
            delta_x = target_x - current_pose.position.x
            delta_y = target_y - current_pose.position.y
            target_distance = math.hypot(delta_x, delta_y)
            req = make_navi_req(
                agibot_gdk,
                target_x,
                target_y,
                target_z,
                current_pose.orientation,
            )
            action_desc = (
                "Map-frame Pnc.normal_navi target: "
                f"({target_x:.3f}, {target_y:.3f}, {target_z:.3f}) m, "
                f"computed from current pose and yaw={yaw:.3f} rad; "
                f"delta=({delta_x:.3f}, {delta_y:.3f}) m, "
                f"distance={target_distance:.3f} m; orientation preserved"
            )

        print(f"Prepared command: {action_desc}")
        if not args.yes:
            answer = input(
                "Robot will navigate to the computed map target. Type 'yes' to execute: "
            ).strip()
            if answer.lower() != "yes":
                print("Canceled before sending command")
                return 0

        if mapping_started:
            print("Canceling mapping before PNC navigation...")
            slam.cancel_mapping()
            mapping_started = False
            ready_task = wait_until_task_ready(pnc, min(args.timeout, 10.0))
            if ready_task.state not in TASK_READY_STATES:
                raise RuntimeError(
                    "PNC task is still busy after canceling mapping: "
                    f"id={ready_task.id}, state={ready_task.state}, "
                    f"type={ready_task.type}, message={ready_task.message}"
                )

        ready_task = pnc.get_task_state()
        if ready_task.state not in TASK_READY_STATES:
            raise RuntimeError(
                "PNC is busy. Refusing to send navigation command: "
                f"id={ready_task.id}, state={ready_task.state}, "
                f"type={ready_task.type}, message={ready_task.message}"
            )

        if args.mode == "relative":
            pnc.relative_move(req)
        else:
            pnc.normal_navi(req)
        command_sent = True
        print("Navigation command sent")

        if not args.no_wait:
            if args.mode == "normal":
                final_task = wait_for_navigation(
                    pnc,
                    slam,
                    current_pose,
                    req.target.position.x,
                    req.target.position.y,
                    args.distance,
                    args.timeout,
                    args.max_overshoot,
                )
            else:
                final_task = wait_for_task(pnc, args.timeout)
            final_name = TASK_STATES.get(final_task.state, f"unknown({final_task.state})")
            print(f"Final task state: {final_name}({final_task.state})")

        try:
            pose_after, odom_after = get_odom_pose(slam)
            print(describe_pose("Pose after command", pose_after, odom_after))
            if current_pose is not None:
                print(f"Actual planar displacement: {planar_distance(current_pose, pose_after):.3f} m")
        except Exception as exc:
            print(f"WARN: pose after command unavailable: {exc}")

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        if command_sent and pnc is not None:
            try:
                task = pnc.get_task_state()
                if task.id:
                    pnc.cancel_task(task.id)
                    print(f"Canceled task {task.id}")
            except Exception as exc:
                print(f"WARN: failed to cancel task: {exc}")
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1
    finally:
        if mapping_started:
            try:
                slam.cancel_mapping()
                print("Mapping canceled")
            except Exception as exc:
                print(f"WARN: failed to cancel mapping: {exc}")

        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            print("GDK release failed")
        else:
            print("GDK released")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
