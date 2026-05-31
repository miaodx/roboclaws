#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

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
NAVIGATION_BACKEND = "agibot_gdk"
NORMAL_NAVI_PROVENANCE = "agibot_gdk_normal_navi"
VERIFIED = "verified"
BLOCKED = "blocked"
TIMEOUT = "timeout"
UNVERIFIED = "unverified"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify operator-recorded Agibot waypoints by sending Pnc.normal_navi "
            "goals. This moves the real robot."
        )
    )
    parser.add_argument("context_json", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Verify every waypoint.")
    group.add_argument(
        "--waypoint-id",
        action="append",
        default=[],
        help="Waypoint id to verify. Repeat for multiple waypoints.",
    )
    parser.add_argument("--timeout-s", type=float, default=45.0)
    parser.add_argument("--poll-s", type=float, default=0.5)
    parser.add_argument("--init-wait-s", type=float, default=2.0)
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required to send navigation commands to the robot.",
    )
    parser.add_argument(
        "--allow-map-mismatch",
        action="store_true",
        help="Do not stop when the current GDK map differs from context map_source.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not args.yes:
        raise SystemExit(
            "Refusing to move the robot without --yes. Review operator stop access first."
        )
    context = _load_context(args.context_json)
    selected = select_waypoints(context, all_waypoints=args.all, waypoint_ids=args.waypoint_id)
    if not selected:
        raise SystemExit("no waypoints selected")

    gdk = _import_gdk()
    initialized = False
    try:
        result = gdk.gdk_init()
        if hasattr(gdk, "GDKRes") and result != gdk.GDKRes.kSuccess:
            raise SystemExit(f"agibot_gdk.gdk_init failed: {result}")
        initialized = True
        pnc = gdk.Pnc()
        map_manager = gdk.Map()
        time.sleep(args.init_wait_s)

        current_map = _map_name_to_dict(_try_call(map_manager.get_curr_map))
        map_check = compare_current_map(context, current_map)
        if not map_check["ok"] and not args.allow_map_mismatch:
            raise SystemExit(
                "current Agibot map does not match context map_source: "
                f"{map_check['message']}. Use --allow-map-mismatch only deliberately."
            )

        for waypoint in selected:
            waypoint_id = str(waypoint.get("waypoint_id") or "")
            print(f"verifying waypoint: {waypoint_id}", file=sys.stderr)
            result = verify_waypoint(
                gdk=gdk,
                pnc=pnc,
                waypoint=waypoint,
                timeout_s=args.timeout_s,
                poll_s=args.poll_s,
                map_check=map_check,
            )
            record_waypoint_verification(waypoint, result)
            _write_json(args.context_json, context)
            print(
                f"{waypoint_id}: {result['reachability_status']} "
                f"final_state={result.get('final_state_name', '')}",
                file=sys.stderr,
            )
    finally:
        if initialized:
            try:
                gdk.gdk_release()
            except Exception as exc:  # noqa: BLE001
                print(f"warning: agibot_gdk.gdk_release failed: {exc}", file=sys.stderr)


def select_waypoints(
    context: dict[str, Any],
    *,
    all_waypoints: bool,
    waypoint_ids: list[str],
) -> list[dict[str, Any]]:
    waypoints = [
        item for item in context.get("inspection_waypoints") or [] if isinstance(item, dict)
    ]
    if all_waypoints:
        return waypoints
    wanted = set(waypoint_ids)
    selected = [item for item in waypoints if str(item.get("waypoint_id") or "") in wanted]
    missing = sorted(wanted - {str(item.get("waypoint_id") or "") for item in selected})
    if missing:
        raise SystemExit(f"unknown waypoint id(s): {', '.join(missing)}")
    return selected


def verify_waypoint(
    *,
    gdk: Any,
    pnc: Any,
    waypoint: dict[str, Any],
    timeout_s: float,
    poll_s: float,
    map_check: dict[str, Any],
) -> dict[str, Any]:
    started_at = _now_iso()
    ready_task = pnc.get_task_state()
    if int(getattr(ready_task, "state", -1)) not in TASK_READY_STATES:
        return _verification_result(
            waypoint,
            status=BLOCKED,
            started_at=started_at,
            map_check=map_check,
            initial_task=task_state_payload(ready_task),
            final_task=task_state_payload(ready_task),
            message="PNC task state was busy before verification.",
            timeout_s=timeout_s,
        )

    req = make_navi_req(gdk, waypoint)
    try:
        pnc.normal_navi(req)
    except Exception as exc:  # noqa: BLE001
        task = _safe_task_state(pnc)
        return _verification_result(
            waypoint,
            status=BLOCKED,
            started_at=started_at,
            map_check=map_check,
            initial_task=task_state_payload(ready_task),
            final_task=task_state_payload(task),
            message=f"Pnc.normal_navi raised: {exc}",
            timeout_s=timeout_s,
        )

    final_task, timed_out = wait_for_task(pnc, timeout_s=timeout_s, poll_s=poll_s)
    if timed_out:
        cancel_evidence = cancel_task_on_timeout(pnc, final_task)
        final_after_cancel = _safe_task_state(pnc)
        result = _verification_result(
            waypoint,
            status=TIMEOUT,
            started_at=started_at,
            map_check=map_check,
            initial_task=task_state_payload(ready_task),
            final_task=task_state_payload(final_after_cancel or final_task),
            message="PNC verification timed out.",
            timeout_s=timeout_s,
        )
        result.update(cancel_evidence)
        result["final_task_before_cancel"] = task_state_payload(final_task)
        result["final_task_after_cancel"] = task_state_payload(final_after_cancel or final_task)
        return result

    final_state = int(getattr(final_task, "state", -1))
    return _verification_result(
        waypoint,
        status=VERIFIED if final_state == 9 else BLOCKED,
        started_at=started_at,
        map_check=map_check,
        initial_task=task_state_payload(ready_task),
        final_task=task_state_payload(final_task),
        message="PNC verification finished.",
        timeout_s=timeout_s,
    )


def make_navi_req(gdk: Any, waypoint: dict[str, Any]) -> Any:
    req = gdk.NaviReq()
    if hasattr(req, "timestamp_ns"):
        req.timestamp_ns = time.time_ns()
    req.target.position.x = float(waypoint["x"])
    req.target.position.y = float(waypoint["y"])
    req.target.position.z = float(waypoint.get("z", 0.0) or 0.0)
    qx, qy, qz, qw = quaternion_from_yaw(float(waypoint["yaw"]))
    req.target.orientation.x = qx
    req.target.orientation.y = qy
    req.target.orientation.z = qz
    req.target.orientation.w = qw
    return req


def wait_for_task(pnc: Any, *, timeout_s: float, poll_s: float) -> tuple[Any, bool]:
    deadline = time.monotonic() + timeout_s
    last_task = None
    while time.monotonic() < deadline:
        task = pnc.get_task_state()
        last_task = task
        if int(getattr(task, "state", -1)) in TASK_READY_STATES:
            return task, False
        time.sleep(poll_s)
    return last_task or pnc.get_task_state(), True


def cancel_task_on_timeout(pnc: Any, final_task: Any) -> dict[str, Any]:
    task_id = int(getattr(final_task, "id", 0) or 0)
    evidence: dict[str, Any] = {
        "cancel_attempted": bool(task_id),
        "cancel_task_id": task_id,
        "cancel_requested": False,
        "cancel_error": "",
    }
    if not task_id:
        evidence["cancel_error"] = "PNC task id unavailable; cancel_task was not called."
        return evidence
    try:
        pnc.cancel_task(task_id)
    except Exception as exc:  # noqa: BLE001
        evidence["cancel_error"] = str(exc)
        return evidence
    evidence["cancel_requested"] = True
    return evidence


def record_waypoint_verification(waypoint: dict[str, Any], result: dict[str, Any]) -> None:
    waypoint["reachability_status"] = result["reachability_status"]
    waypoint["verification"] = result


def compare_current_map(context: dict[str, Any], current_map: dict[str, Any]) -> dict[str, Any]:
    expected = context.get("map_source") if isinstance(context.get("map_source"), dict) else {}
    expected_id = expected.get("map_id")
    expected_name = str(expected.get("map_name") or "")
    current_id = current_map.get("id")
    current_name = str(current_map.get("name") or "")
    id_matches = expected_id is None or str(expected_id) == str(current_id)
    name_matches = not expected_name or expected_name == current_name
    ok = id_matches and name_matches
    return {
        "ok": ok,
        "expected_map_id": expected_id,
        "expected_map_name": expected_name,
        "current_map_id": current_id,
        "current_map_name": current_name,
        "message": "map matched" if ok else "map id/name mismatch",
    }


def task_state_payload(task: Any) -> dict[str, Any]:
    if task is None:
        return {}
    state = int(getattr(task, "state", -1))
    return {
        "id": int(getattr(task, "id", 0) or 0),
        "state": state,
        "state_name": TASK_STATES.get(state, f"unknown({state})"),
        "type": str(getattr(task, "type", "")),
        "message": str(getattr(task, "message", "")),
    }


def quaternion_from_yaw(yaw: float) -> tuple[float, float, float, float]:
    return (0.0, 0.0, math.sin(yaw / 2.0), math.cos(yaw / 2.0))


def _verification_result(
    waypoint: dict[str, Any],
    *,
    status: str,
    started_at: str,
    map_check: dict[str, Any],
    initial_task: dict[str, Any],
    final_task: dict[str, Any],
    message: str,
    timeout_s: float,
) -> dict[str, Any]:
    final_state = final_task.get("state")
    final_name = final_task.get("state_name", "")
    return {
        "schema": "agibot_gdk_pnc_waypoint_verification_v1",
        "navigation_backend": NAVIGATION_BACKEND,
        "primitive_provenance": NORMAL_NAVI_PROVENANCE,
        "reachability_status": status,
        "checked_at": _now_iso(),
        "started_at": started_at,
        "timeout_s": timeout_s,
        "waypoint_id": str(waypoint.get("waypoint_id") or ""),
        "goal": {
            "frame_id": str(waypoint.get("frame_id") or "map"),
            "x": float(waypoint["x"]),
            "y": float(waypoint["y"]),
            "yaw": float(waypoint["yaw"]),
        },
        "map_check": map_check,
        "initial_task": initial_task,
        "final_task": final_task,
        "final_state": final_state,
        "final_state_name": final_name,
        "message": message,
    }


def _safe_task_state(pnc: Any) -> Any:
    try:
        return pnc.get_task_state()
    except Exception:  # noqa: BLE001
        return None


def _load_context(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("context JSON must contain an object")
    if data.get("schema") != "agibot_gdk_map_context_authoring_v1":
        raise SystemExit("context schema must be agibot_gdk_map_context_authoring_v1")
    return data


def _import_gdk() -> Any:
    try:
        import agibot_gdk
    except ImportError as exc:
        raise SystemExit(
            "agibot_gdk is not importable. Run this script on the Agibot GDK machine."
        ) from exc
    return agibot_gdk


def _map_name_to_dict(item: Any) -> dict[str, Any]:
    if item is None:
        return {"id": None, "name": "", "is_curr_map": None}
    return {
        "id": getattr(item, "id", None),
        "name": str(getattr(item, "name", "") or ""),
        "is_curr_map": getattr(item, "is_curr_map", None),
    }


def _try_call(func: Any) -> Any:
    try:
        return func()
    except Exception as exc:  # noqa: BLE001
        print(f"warning: {getattr(func, '__name__', 'gdk call')} failed: {exc}", file=sys.stderr)
        return None


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
