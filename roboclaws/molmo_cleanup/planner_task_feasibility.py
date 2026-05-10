from __future__ import annotations

import json
from typing import Any

GRASP_FEASIBILITY_SIGNATURE_SCHEMA = "planner_grasp_feasibility_signature_v1"


def task_feasibility_blocker_kind(
    blockers: list[dict[str, Any]],
    task_sampler_failure_diagnostics: dict[str, Any],
) -> str:
    robot_placement_failures = int(
        task_sampler_failure_diagnostics.get("robot_placement_failure_count") or 0
    )
    grasp_failures = int(task_sampler_failure_diagnostics.get("grasp_failure_count") or 0)
    if robot_placement_failures:
        return "robot_placement"
    if grasp_failures:
        return "grasp_feasibility"
    codes = {str(item.get("code") or "") for item in blockers}
    if "HouseInvalidForTask" in codes:
        return "task_sampling"
    return ""


def task_feasibility_blocker_summary(
    blocker_kind: str,
    task_sampler_failure_diagnostics: dict[str, Any],
) -> str:
    if blocker_kind == "robot_placement":
        return (
            f"{int(task_sampler_failure_diagnostics.get('robot_placement_failure_count') or 0)} "
            "robot-placement failures"
        )
    if blocker_kind == "grasp_feasibility":
        return (
            f"{int(task_sampler_failure_diagnostics.get('grasp_failure_count') or 0)} "
            "grasp failures; "
            f"{int(task_sampler_failure_diagnostics.get('candidate_removal_count') or 0)} "
            "candidate-removal calls"
        )
    return ""


def grasp_feasibility_signature(
    task_sampler_failure_diagnostics: dict[str, Any],
) -> dict[str, Any]:
    grasp_failure_count = int(task_sampler_failure_diagnostics.get("grasp_failure_count") or 0)
    if not grasp_failure_count:
        return {}
    object_names = _unique_nonempty(
        str(item.get("object_name") or "")
        for item in task_sampler_failure_diagnostics.get("grasp_failures") or []
        if isinstance(item, dict)
    )
    signature = {
        "schema": GRASP_FEASIBILITY_SIGNATURE_SCHEMA,
        "kind": "grasp_feasibility",
        "pattern_key": _grasp_pattern_key(task_sampler_failure_diagnostics),
        "summary": task_feasibility_blocker_summary(
            "grasp_feasibility",
            task_sampler_failure_diagnostics,
        ),
        "grasp_failure_count": grasp_failure_count,
        "candidate_removal_count": int(
            task_sampler_failure_diagnostics.get("candidate_removal_count") or 0
        ),
        "robot_placement_attempt_count": int(
            task_sampler_failure_diagnostics.get("robot_placement_attempt_count") or 0
        ),
        "robot_placement_failure_count": int(
            task_sampler_failure_diagnostics.get("robot_placement_failure_count") or 0
        ),
        "place_robot_near_call_count": int(
            task_sampler_failure_diagnostics.get("place_robot_near_call_count") or 0
        ),
        "object_name_count": len(object_names),
        "object_names": object_names,
        "image_artifact_count": len(task_sampler_failure_diagnostics.get("image_artifacts") or {}),
    }
    return signature


def grasp_feasibility_signature_counts(
    proof_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for item in proof_results:
        signature = item.get("grasp_feasibility_signature") or {}
        if not isinstance(signature, dict) or not signature:
            continue
        key = str(signature.get("pattern_key") or json.dumps(signature, sort_keys=True))
        group = groups.setdefault(
            key,
            {
                "schema": "planner_grasp_feasibility_signature_group_v1",
                "pattern_key": key,
                "summary": str(signature.get("summary") or ""),
                "count": 0,
                "request_ids": [],
                "object_ids": [],
                "target_receptacle_ids": [],
                "object_names": [],
                "proof_reports": [],
                "grasp_failure_count": signature.get("grasp_failure_count"),
                "candidate_removal_count": signature.get("candidate_removal_count"),
                "robot_placement_attempt_count": signature.get("robot_placement_attempt_count"),
                "robot_placement_failure_count": signature.get("robot_placement_failure_count"),
                "place_robot_near_call_count": signature.get("place_robot_near_call_count"),
                "image_artifact_count": 0,
            },
        )
        group["count"] += 1
        group["image_artifact_count"] += int(signature.get("image_artifact_count") or 0)
        _append_unique(group["request_ids"], str(item.get("request_id") or ""))
        _append_unique(group["object_ids"], str(item.get("object_id") or ""))
        _append_unique(
            group["target_receptacle_ids"],
            str(item.get("target_receptacle_id") or ""),
        )
        for object_name in signature.get("object_names") or []:
            _append_unique(group["object_names"], str(object_name or ""))
        _append_unique(group["proof_reports"], str(item.get("report") or ""))
    return sorted(
        groups.values(),
        key=lambda item: (-int(item.get("count") or 0), str(item.get("pattern_key") or "")),
    )


def _grasp_pattern_key(task_sampler_failure_diagnostics: dict[str, Any]) -> str:
    fields = {
        "candidate_removal_count": int(
            task_sampler_failure_diagnostics.get("candidate_removal_count") or 0
        ),
        "grasp_failure_count": int(
            task_sampler_failure_diagnostics.get("grasp_failure_count") or 0
        ),
        "place_robot_near_call_count": int(
            task_sampler_failure_diagnostics.get("place_robot_near_call_count") or 0
        ),
        "robot_placement_failure_count": int(
            task_sampler_failure_diagnostics.get("robot_placement_failure_count") or 0
        ),
    }
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _unique_nonempty(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        _append_unique(result, str(value or ""))
    return result
