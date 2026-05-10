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
        grasp_load_failures = int(
            task_sampler_failure_diagnostics.get("grasp_load_failure_count") or 0
        )
        grasp_collision_checks = int(
            task_sampler_failure_diagnostics.get("grasp_collision_check_count") or 0
        )
        zero_noncolliding_checks = int(
            task_sampler_failure_diagnostics.get("zero_noncolliding_grasp_check_count") or 0
        )
        summary = (
            f"{int(task_sampler_failure_diagnostics.get('grasp_failure_count') or 0)} "
            "grasp failures; "
            f"{int(task_sampler_failure_diagnostics.get('candidate_removal_count') or 0)} "
            "candidate-removal calls"
        )
        if "candidate_effective_removal_count" in task_sampler_failure_diagnostics:
            effective_removals = int(
                task_sampler_failure_diagnostics.get("candidate_effective_removal_count") or 0
            )
            summary += f"; {effective_removals} effective removals"
        if "candidate_name_miss_count" in task_sampler_failure_diagnostics:
            name_misses = int(
                task_sampler_failure_diagnostics.get("candidate_name_miss_count") or 0
            )
            summary += f"; {name_misses} candidate-name misses"
        if grasp_load_failures:
            summary += f"; {grasp_load_failures} grasp-load failures"
            missing_assets = _grasp_load_exception_asset_uids(task_sampler_failure_diagnostics)
            if missing_assets:
                summary += f"; missing grasp cache: {', '.join(missing_assets)}"
        if grasp_collision_checks:
            summary += f"; {grasp_collision_checks} grasp collision checks"
        if zero_noncolliding_checks:
            summary += f"; {zero_noncolliding_checks} zero non-colliding checks"
        return summary
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
        "subkind": _grasp_feasibility_subkind(task_sampler_failure_diagnostics),
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
        "grasp_load_attempt_count": int(
            task_sampler_failure_diagnostics.get("grasp_load_attempt_count") or 0
        ),
        "grasp_load_failure_count": int(
            task_sampler_failure_diagnostics.get("grasp_load_failure_count") or 0
        ),
        "grasp_collision_check_count": int(
            task_sampler_failure_diagnostics.get("grasp_collision_check_count") or 0
        ),
        "zero_noncolliding_grasp_check_count": int(
            task_sampler_failure_diagnostics.get("zero_noncolliding_grasp_check_count") or 0
        ),
        "grasp_load_exception_asset_uids": _grasp_load_exception_asset_uids(
            task_sampler_failure_diagnostics
        ),
        "grasp_load_exception_types": _grasp_load_exception_types(task_sampler_failure_diagnostics),
        "object_name_count": len(object_names),
        "object_names": object_names,
        "image_artifact_count": len(task_sampler_failure_diagnostics.get("image_artifacts") or {}),
    }
    for key in (
        "candidate_effective_removal_count",
        "candidate_name_miss_count",
        "grasp_threshold_exceeded_count",
    ):
        if key in task_sampler_failure_diagnostics:
            signature[key] = int(task_sampler_failure_diagnostics.get(key) or 0)
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
                "candidate_effective_removal_count": signature.get(
                    "candidate_effective_removal_count"
                ),
                "candidate_name_miss_count": signature.get("candidate_name_miss_count"),
                "grasp_threshold_exceeded_count": signature.get("grasp_threshold_exceeded_count"),
                "robot_placement_attempt_count": signature.get("robot_placement_attempt_count"),
                "robot_placement_failure_count": signature.get("robot_placement_failure_count"),
                "place_robot_near_call_count": signature.get("place_robot_near_call_count"),
                "grasp_load_attempt_count": signature.get("grasp_load_attempt_count"),
                "grasp_load_failure_count": signature.get("grasp_load_failure_count"),
                "grasp_collision_check_count": signature.get("grasp_collision_check_count"),
                "zero_noncolliding_grasp_check_count": signature.get(
                    "zero_noncolliding_grasp_check_count"
                ),
                "subkind": signature.get("subkind"),
                "grasp_load_exception_asset_uids": [],
                "grasp_load_exception_types": [],
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
        for asset_uid in signature.get("grasp_load_exception_asset_uids") or []:
            _append_unique(group["grasp_load_exception_asset_uids"], str(asset_uid or ""))
        for exception_type in signature.get("grasp_load_exception_types") or []:
            _append_unique(group["grasp_load_exception_types"], str(exception_type or ""))
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
        "subkind": _grasp_feasibility_subkind(task_sampler_failure_diagnostics),
    }
    for key in ("candidate_effective_removal_count", "candidate_name_miss_count"):
        if key in task_sampler_failure_diagnostics:
            fields[key] = int(task_sampler_failure_diagnostics.get(key) or 0)
    for key in (
        "grasp_load_attempt_count",
        "grasp_load_failure_count",
        "grasp_collision_check_count",
        "zero_noncolliding_grasp_check_count",
    ):
        if key in task_sampler_failure_diagnostics:
            fields[key] = int(task_sampler_failure_diagnostics.get(key) or 0)
    missing_assets = _grasp_load_exception_asset_uids(task_sampler_failure_diagnostics)
    if missing_assets:
        fields["grasp_load_exception_asset_uids"] = missing_assets
    exception_types = _grasp_load_exception_types(task_sampler_failure_diagnostics)
    if exception_types:
        fields["grasp_load_exception_types"] = exception_types
    return json.dumps(fields, sort_keys=True, separators=(",", ":"))


def _grasp_feasibility_subkind(task_sampler_failure_diagnostics: dict[str, Any]) -> str:
    if int(task_sampler_failure_diagnostics.get("grasp_load_failure_count") or 0) and not int(
        task_sampler_failure_diagnostics.get("grasp_collision_check_count") or 0
    ):
        return "grasp_cache_missing"
    if int(task_sampler_failure_diagnostics.get("zero_noncolliding_grasp_check_count") or 0):
        return "zero_noncolliding_grasps"
    return "grasp_rejection"


def _grasp_load_exception_asset_uids(
    task_sampler_failure_diagnostics: dict[str, Any],
) -> list[str]:
    return _unique_nonempty(
        str(item.get("asset_uid") or "")
        for item in task_sampler_failure_diagnostics.get("grasp_load_attempts") or []
        if isinstance(item, dict) and str(item.get("result") or "") != "loaded"
    )


def _grasp_load_exception_types(
    task_sampler_failure_diagnostics: dict[str, Any],
) -> list[str]:
    return _unique_nonempty(
        str(item.get("exception_type") or "")
        for item in task_sampler_failure_diagnostics.get("grasp_load_attempts") or []
        if isinstance(item, dict) and str(item.get("result") or "") != "loaded"
    )


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def _unique_nonempty(values: Any) -> list[str]:
    result: list[str] = []
    for value in values:
        _append_unique(result, str(value or ""))
    return result
