#!/usr/bin/env python3
"""
Realtime SLAM localization demo.

Prints the current robot pose and optional odometry localization metadata.
Press Ctrl+C to stop.
"""

import argparse
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
GDK_ROOT = SCRIPT_PATH.parents[4]
APP_ROOT = GDK_ROOT.parent
BOOTSTRAP_MARKER = "AGIBOT_GDK_DEMO_BOOTSTRAPPED"


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
        fields = line.split()
        for field in fields:
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

        os.execvpe(
            python310,
            [python310, str(SCRIPT_PATH), *sys.argv[1:]],
            env,
        )

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
    """Return yaw in radians from a quaternion-like object."""
    return math.atan2(
        2.0 * (orientation.w * orientation.z + orientation.x * orientation.y),
        1.0 - 2.0 * (orientation.y * orientation.y + orientation.z * orientation.z),
    )


def unwrap_pose(pose_like):
    """
    Support both documented Pose and wrapped PoseWithCovariance-style objects.

    Some examples in this repository access odom_info.pose.pose.position, while
    the SLAM API documentation describes pose.position directly.
    """
    if hasattr(pose_like, "position") and hasattr(pose_like, "orientation"):
        return pose_like
    if hasattr(pose_like, "pose"):
        return unwrap_pose(pose_like.pose)
    raise AttributeError("pose object has no position/orientation fields")


def read_localization(slam, source):
    """Read localization from odometry or the current-pose API."""
    if source == "curr-pose":
        return unwrap_pose(slam.get_curr_pose()), None

    odom_info = slam.get_odom_info()
    return unwrap_pose(odom_info.pose), odom_info


def format_pose_line(pose, odom_info=None):
    position = pose.position
    orientation = pose.orientation
    yaw = quaternion_to_yaw(orientation)

    parts = [
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        f"pos=({position.x:.3f}, {position.y:.3f}, {position.z:.3f}) m",
        (
            "quat=("
            f"{orientation.x:.4f}, {orientation.y:.4f}, "
            f"{orientation.z:.4f}, {orientation.w:.4f})"
        ),
        f"yaw={yaw:.3f} rad",
    ]

    if odom_info is not None:
        parts.extend(
            [
                f"loc_state={getattr(odom_info, 'loc_state', 'n/a')}",
                f"confidence={getattr(odom_info, 'loc_confidence', float('nan')):.3f}",
                f"stationary={getattr(odom_info, 'is_stationary', 'n/a')}",
                f"slipping={getattr(odom_info, 'is_sliping', 'n/a')}",
            ]
        )

    return " | ".join(parts)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Realtime localization demo using agibot_gdk.Slam."
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Print interval in seconds. Default: 1.0",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Run duration in seconds. 0 means run until Ctrl+C. Default: 0",
    )
    parser.add_argument(
        "--init-wait",
        type=float,
        default=2.0,
        help="Seconds to wait after creating Slam. Default: 2.0",
    )
    parser.add_argument(
        "--source",
        choices=["odom", "curr-pose"],
        default="odom",
        help="Localization source. Default: odom",
    )
    parser.add_argument(
        "--start-mapping",
        action="store_true",
        help="Call slam.start_mapping() before reading localization.",
    )
    parser.add_argument(
        "--save-map-on-exit",
        action="store_true",
        help="When used with --start-mapping, stop and save the map instead of canceling it.",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.interval <= 0.0:
        raise ValueError("--interval must be greater than 0")
    if args.init_wait < 0.0:
        raise ValueError("--init-wait must be greater than or equal to 0")

    if "LOCATOR_IP" not in os.environ:
        print(
            "WARN: no 10.42.1.* network address found. "
            "GDK may not communicate with the robot until the robot network is ready."
        )

    import agibot_gdk

    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK init failed")
        return 1

    try:
        slam = agibot_gdk.Slam()
        time.sleep(args.init_wait)

        mapping_started = False
        if args.start_mapping:
            print("Starting SLAM mapping before reading localization...")
            slam.start_mapping()
            mapping_started = True
            time.sleep(1.0)

        start_time = time.monotonic()
        print("Realtime localization started. Press Ctrl+C to stop.")

        while True:
            if args.duration > 0.0 and time.monotonic() - start_time >= args.duration:
                break

            try:
                pose, odom_info = read_localization(slam, args.source)
                line = format_pose_line(pose, odom_info)
                print(line)
            except Exception as exc:
                try:
                    slam_state = slam.get_slam_state()
                    state_text = f" | slam_state={slam_state}"
                except Exception:
                    state_text = ""
                print(
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"localization not ready: {exc}{state_text}"
                )

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        if "mapping_started" in locals() and mapping_started:
            try:
                if args.save_map_on_exit:
                    slam.stop_mapping()
                    print("Mapping stopped and saved")
                else:
                    slam.cancel_mapping()
                    print("Mapping canceled")
            except Exception as exc:
                print(f"Failed to stop mapping cleanly: {exc}")

        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            print("GDK release failed")
        else:
            print("GDK released")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
