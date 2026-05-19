#!/usr/bin/env python3
"""
Inspect and clear the current busy PNC task.

This is intended for recovering from a stuck/busy PNC state such as a mapping
task started by slam.start_mapping(). It prints the current task first, asks
for confirmation, then tries slam.cancel_mapping() followed by pnc.cancel_task()
if the task is still busy.
"""

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve()
GDK_ROOT = SCRIPT_PATH.parents[4]
APP_ROOT = GDK_ROOT.parent
BOOTSTRAP_MARKER = "AGIBOT_GDK_CLEAR_PNC_BOOTSTRAPPED"

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

TASK_TYPES = {
    0: "idle",
    1: "normal navigation",
    2: "remote control",
    3: "mapping or internal task",
}

READY_STATES = {0, 7, 8, 9}


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


def describe_task(task):
    state_name = TASK_STATES.get(task.state, f"unknown({task.state})")
    type_name = TASK_TYPES.get(task.type, f"unknown({task.type})")
    return (
        f"id={task.id}, state={state_name}({task.state}), "
        f"type={type_name}({task.type}), message={task.message}"
    )


def wait_until_ready(pnc, timeout):
    deadline = time.monotonic() + timeout
    last = None

    while time.monotonic() < deadline:
        task = pnc.get_task_state()
        line = describe_task(task)
        if line != last:
            print(f"Current task: {line}")
            last = line

        if task.state in READY_STATES:
            return task

        time.sleep(0.5)

    return pnc.get_task_state()


def parse_args():
    parser = argparse.ArgumentParser(
        description="Inspect or clear the current busy PNC task."
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Try to clear the busy task after confirmation.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive confirmation when used with --clear.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=15.0,
        help="Seconds to wait for the task to become ready. Default: 15",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.timeout <= 0.0:
        raise ValueError("--timeout must be greater than 0")

    import agibot_gdk

    if agibot_gdk.gdk_init() != agibot_gdk.GDKRes.kSuccess:
        print("GDK init failed")
        return 1

    try:
        pnc = agibot_gdk.Pnc()
        slam = agibot_gdk.Slam()
        time.sleep(1.0)

        task = pnc.get_task_state()
        print(f"Current task: {describe_task(task)}")

        if task.state in READY_STATES:
            print("PNC is already ready; nothing to clear.")
            return 0

        if not args.clear:
            print("Busy task found. Re-run with --clear to cancel it.")
            return 0

        if not args.yes:
            answer = input(
                "This may stop the robot's current navigation/mapping task. "
                "Type 'yes' to clear it: "
            ).strip()
            if answer.lower() != "yes":
                print("Canceled before clearing task.")
                return 0

        print("Trying slam.cancel_mapping() first...")
        try:
            slam.cancel_mapping()
        except Exception as exc:
            print(f"slam.cancel_mapping() failed or was not applicable: {exc}")

        task = wait_until_ready(pnc, min(args.timeout, 5.0))
        if task.state in READY_STATES:
            print("PNC is ready after cancel_mapping.")
            return 0

        print(f"Still busy, trying pnc.cancel_task({task.id})...")
        pnc.cancel_task(task.id)

        task = wait_until_ready(pnc, args.timeout)
        if task.state in READY_STATES:
            print("PNC is ready after cancel_task.")
            return 0

        print(f"PNC is still busy: {describe_task(task)}")
        return 1

    finally:
        if agibot_gdk.gdk_release() != agibot_gdk.GDKRes.kSuccess:
            print("GDK release failed")
        else:
            print("GDK released")


if __name__ == "__main__":
    raise SystemExit(main())
