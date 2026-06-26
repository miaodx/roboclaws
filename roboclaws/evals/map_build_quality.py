from __future__ import annotations

from typing import Any

from roboclaws.evals.models import MISSING_NOT_APPLICABLE, MISSING_UNAVAILABLE


def grade_runtime_metric_map_quality(
    *,
    runtime_map: dict[str, Any],
    runtime_map_exists: bool,
    runtime_map_error: str,
    config: dict[str, Any],
    private_goal_reference: dict[str, Any] | None = None,
) -> dict[str, Any]:
    schema_ok = runtime_map.get("schema") == str(
        config.get("require_runtime_metric_map_schema") or "runtime_metric_map_v1"
    )
    anchors, anchors_error = _optional_list_value(runtime_map, "public_semantic_anchors")
    exploration, exploration_error = _optional_list_value(
        runtime_map,
        "generated_exploration_candidates",
    )
    observed_objects, observed_objects_error = _optional_list_value(runtime_map, "observed_objects")
    target_candidates, target_candidates_error = _optional_list_value(
        runtime_map,
        "target_candidates",
    )
    runtime_map_error = (
        runtime_map_error
        or anchors_error
        or exploration_error
        or observed_objects_error
        or target_candidates_error
    )
    stable_anchor_categories = _stable_semantic_anchor_categories(anchors)
    base_map_anchor_like_count = _base_map_anchor_like_count(anchors)
    runtime_enrichment_anchor_count = _runtime_enrichment_anchor_count(anchors)
    semantic_enrichment_over_base = runtime_enrichment_anchor_count > 0 and bool(
        stable_anchor_categories
    )
    duplicate_fixture_viewpoint_groups = _duplicate_fixture_viewpoint_groups(anchors)
    object_pose_claim_count = _rgb_only_object_pose_claim_count(
        [*anchors, *observed_objects, *target_candidates]
    )
    sim_truth_quality = _sim_truth_quality(
        anchors,
        private_goal_reference=private_goal_reference or {},
    )
    private_truth_absent = runtime_map.get("private_truth_included") is False
    source_map_not_mutated = runtime_map.get("source_map_mutated") is False
    sim_truth_category_passed = _threshold_passed(
        sim_truth_quality["fixture_category_recall"],
        config.get("min_sim_truth_fixture_category_recall"),
    ) and _threshold_passed(
        sim_truth_quality["fixture_category_precision"],
        config.get("min_sim_truth_fixture_category_precision"),
    )
    sim_truth_best_view_passed = _threshold_passed(
        sim_truth_quality["best_view_waypoint_accuracy"],
        config.get("min_sim_truth_best_view_waypoint_accuracy"),
    )
    observed_object_threshold_passed = _count_threshold_passed(
        len(observed_objects),
        config.get("min_observed_objects"),
    )
    target_candidate_threshold_passed = _count_threshold_passed(
        len(target_candidates),
        config.get("min_target_candidates"),
    )
    actionable_runtime_map_evidence = _any_configured_count_threshold_passed(
        observed_object_threshold_passed,
        target_candidate_threshold_passed,
        config.get("min_observed_objects"),
        config.get("min_target_candidates"),
    )
    passed = (
        runtime_map_exists
        and schema_ok
        and len(anchors) >= _int_value(config.get("min_public_semantic_anchors") or 0)
        and len(exploration) >= _int_value(config.get("min_generated_exploration_candidates") or 0)
        and len(stable_anchor_categories)
        >= _int_value(config.get("min_stable_semantic_anchor_categories") or 0)
        and runtime_enrichment_anchor_count
        >= _int_value(config.get("min_runtime_enrichment_anchors") or 0)
        and actionable_runtime_map_evidence
        and len(duplicate_fixture_viewpoint_groups)
        <= _int_value(config.get("max_duplicate_fixture_viewpoint_groups") or 0)
        and (
            object_pose_claim_count == 0
            if config.get("forbid_rgb_only_object_pose", False)
            else True
        )
        and (private_truth_absent if config.get("require_private_truth_absent", True) else True)
        and (
            semantic_enrichment_over_base
            if config.get("require_semantic_enrichment_over_base", False)
            else True
        )
        and (source_map_not_mutated if config.get("require_source_map_not_mutated", True) else True)
        and sim_truth_category_passed
        and sim_truth_best_view_passed
    )
    failure_class = MISSING_NOT_APPLICABLE
    if not passed:
        failure_class = (
            "artifact_missing"
            if runtime_map_error not in {"", "missing"}
            else "map_actionability_failure"
        )
    return {
        "status": "passed" if passed else "failed",
        "failure_class": failure_class,
        "runtime_metric_map_exists": runtime_map_exists,
        "runtime_metric_map_schema": runtime_map.get("schema", MISSING_UNAVAILABLE),
        "runtime_metric_map_error": runtime_map_error or MISSING_NOT_APPLICABLE,
        "schema_ok": schema_ok,
        "public_semantic_anchor_count": len(anchors),
        "base_map_anchor_like_count": base_map_anchor_like_count,
        "runtime_enrichment_anchor_count": runtime_enrichment_anchor_count,
        "semantic_enrichment_over_base": semantic_enrichment_over_base,
        "generated_exploration_candidate_count": len(exploration),
        "stable_semantic_anchor_category_count": len(stable_anchor_categories),
        "stable_semantic_anchor_categories": stable_anchor_categories,
        "observed_object_count": len(observed_objects),
        "target_candidate_count": len(target_candidates),
        "observed_object_threshold_passed": observed_object_threshold_passed,
        "target_candidate_threshold_passed": target_candidate_threshold_passed,
        "actionable_runtime_map_evidence": actionable_runtime_map_evidence,
        "duplicate_fixture_viewpoint_group_count": len(duplicate_fixture_viewpoint_groups),
        "duplicate_fixture_viewpoint_groups": duplicate_fixture_viewpoint_groups,
        "rgb_only_object_pose_claim_count": object_pose_claim_count,
        "sim_truth_fixture_category_recall": sim_truth_quality["fixture_category_recall"],
        "sim_truth_fixture_category_precision": sim_truth_quality["fixture_category_precision"],
        "sim_truth_expected_fixture_categories": sim_truth_quality["expected_categories"],
        "sim_truth_observed_fixture_categories": sim_truth_quality["observed_categories"],
        "sim_truth_missing_fixture_categories": sim_truth_quality["missing_categories"],
        "sim_truth_extra_fixture_categories": sim_truth_quality["extra_categories"],
        "sim_truth_best_view_waypoint_accuracy": sim_truth_quality["best_view_waypoint_accuracy"],
        "sim_truth_best_view_waypoint_mismatches": sim_truth_quality[
            "best_view_waypoint_mismatches"
        ],
        "private_truth_absent": private_truth_absent,
        "source_map_not_mutated": source_map_not_mutated,
    }


def _stable_semantic_anchor_categories(anchors: list[Any]) -> list[str]:
    categories: set[str] = set()
    for anchor in _list_of_mappings(anchors):
        if anchor.get("anchor_type") not in {"fixture", "surface", "receptacle"}:
            continue
        category = _normalized_category(anchor)
        if category:
            categories.add(category)
    return sorted(categories)


def _base_map_anchor_like_count(anchors: list[Any]) -> int:
    return sum(
        1
        for anchor in _list_of_mappings(anchors)
        if anchor.get("anchor_type") in {"room_area", "observation_waypoint"}
    )


def _runtime_enrichment_anchor_count(anchors: list[Any]) -> int:
    return sum(
        1
        for anchor in _list_of_mappings(anchors)
        if anchor.get("anchor_type") in {"fixture", "surface", "receptacle"}
    )


def _duplicate_fixture_viewpoint_groups(anchors: list[Any]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, tuple[Any, Any, Any], str], list[str]] = {}
    for anchor in _list_of_mappings(anchors):
        if anchor.get("anchor_type") not in {"fixture", "surface", "receptacle"}:
            continue
        pose = anchor.get("pose") if isinstance(anchor.get("pose"), dict) else {}
        key = (
            _normalized_category(anchor),
            str(anchor.get("room_id") or ""),
            str(anchor.get("waypoint_id") or ""),
            (pose.get("x"), pose.get("y"), pose.get("yaw")),
            str(anchor.get("source_observation_id") or ""),
        )
        groups.setdefault(key, []).append(str(anchor.get("anchor_id") or ""))
    duplicates = []
    for key, anchor_ids in groups.items():
        unique_anchor_ids = sorted({anchor_id for anchor_id in anchor_ids if anchor_id})
        if len(unique_anchor_ids) > 1:
            category, room_id, waypoint_id, pose, source_observation_id = key
            duplicates.append(
                {
                    "category": category,
                    "room_id": room_id,
                    "waypoint_id": waypoint_id,
                    "pose": {"x": pose[0], "y": pose[1], "yaw": pose[2]},
                    "source_observation_id": source_observation_id,
                    "anchor_ids": unique_anchor_ids,
                }
            )
    return duplicates


def _rgb_only_object_pose_claim_count(items: list[Any]) -> int:
    count = 0
    for item in _list_of_mappings(items):
        if "object_pose" not in item:
            continue
        if not _has_trusted_object_pose_provenance(item):
            count += 1
    return count


def _sim_truth_quality(
    anchors: list[Any],
    *,
    private_goal_reference: dict[str, Any],
) -> dict[str, Any]:
    truth = _sim_fixture_truth(private_goal_reference)
    expected_categories = sorted(_normalized_text(item) for item in truth.get("categories", []))
    expected_categories = sorted({item for item in expected_categories if item})
    fixture_anchors = [
        anchor
        for anchor in _list_of_mappings(anchors)
        if anchor.get("anchor_type") in {"fixture", "surface", "receptacle"}
    ]
    observed_categories = sorted(
        {_normalized_category(anchor) for anchor in fixture_anchors if _normalized_category(anchor)}
    )
    category_overlap = sorted(set(expected_categories) & set(observed_categories))
    missing_categories = sorted(set(expected_categories) - set(observed_categories))
    extra_categories = sorted(set(observed_categories) - set(expected_categories))
    if expected_categories:
        recall: float | str = round(len(category_overlap) / len(expected_categories), 6)
        precision = (
            round(len(category_overlap) / len(observed_categories), 6)
            if observed_categories
            else 0.0
        )
    else:
        recall = MISSING_NOT_APPLICABLE
        precision = MISSING_NOT_APPLICABLE

    best_view_rows = _best_view_truth_rows(truth)
    mismatches = []
    matched = 0
    anchors_by_category: dict[str, list[dict[str, Any]]] = {}
    for anchor in fixture_anchors:
        anchors_by_category.setdefault(_normalized_category(anchor), []).append(anchor)
    for row in best_view_rows:
        category = row["category"]
        expected_waypoint_ids = row["waypoint_ids"]
        observed_waypoint_ids = sorted(
            {
                str(anchor.get("waypoint_id") or "")
                for anchor in anchors_by_category.get(category, [])
                if str(anchor.get("waypoint_id") or "")
            }
        )
        if set(observed_waypoint_ids) & set(expected_waypoint_ids):
            matched += 1
            continue
        mismatches.append(
            {
                "category": category,
                "expected_waypoint_ids": expected_waypoint_ids,
                "observed_waypoint_ids": observed_waypoint_ids,
            }
        )
    accuracy: float | str = (
        round(matched / len(best_view_rows), 6) if best_view_rows else MISSING_NOT_APPLICABLE
    )
    return {
        "expected_categories": expected_categories,
        "observed_categories": observed_categories,
        "missing_categories": missing_categories,
        "extra_categories": extra_categories,
        "fixture_category_recall": recall,
        "fixture_category_precision": precision,
        "best_view_waypoint_accuracy": accuracy,
        "best_view_waypoint_mismatches": mismatches,
    }


def _sim_fixture_truth(private_goal_reference: dict[str, Any]) -> dict[str, Any]:
    truth = private_goal_reference.get("simulator_fixture_truth")
    return truth if isinstance(truth, dict) else {}


def _best_view_truth_rows(truth: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for raw_row in truth.get("best_view_waypoint_truth") or []:
        if not isinstance(raw_row, dict):
            continue
        category = _normalized_text(raw_row.get("category"))
        waypoint_ids = sorted(
            {
                str(item).strip()
                for item in raw_row.get("waypoint_ids")
                or raw_row.get("expected_waypoint_ids")
                or []
                if str(item).strip()
            }
        )
        if category and waypoint_ids:
            rows.append({"category": category, "waypoint_ids": waypoint_ids})
    return rows


def _has_trusted_object_pose_provenance(item: dict[str, Any]) -> bool:
    trusted_sources = {
        "agibot_navigation_memory_pose",
        "depth_projection",
        "trusted_projection",
        "simulator_truth_projection",
    }
    source = str(item.get("object_pose_source") or "")
    if source in trusted_sources:
        return True
    provenance = item.get("object_pose_provenance")
    if isinstance(provenance, dict):
        provenance_source = str(provenance.get("source") or provenance.get("method") or "")
        return provenance_source in trusted_sources
    return False


def _optional_list_value(payload: dict[str, Any], key: str) -> tuple[list[Any], str]:
    if key not in payload or payload.get(key) is None:
        return [], ""
    value = payload.get(key)
    if not isinstance(value, list):
        return [], f"{key}:invalid_json_array"
    return value, ""


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _normalized_category(item: dict[str, Any]) -> str:
    return _normalized_text(item.get("category") or item.get("label"))


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _threshold_passed(value: Any, minimum: Any) -> bool:
    if minimum is None:
        return True
    try:
        threshold = float(minimum)
    except (TypeError, ValueError):
        return True
    if threshold <= 0:
        return True
    try:
        return float(value) >= threshold
    except (TypeError, ValueError):
        return False


def _count_threshold_passed(count: int, minimum: Any) -> bool:
    threshold = _int_value(minimum)
    return threshold <= 0 or count >= threshold


def _any_configured_count_threshold_passed(
    observed_passed: bool,
    target_passed: bool,
    observed_minimum: Any,
    target_minimum: Any,
) -> bool:
    configured = []
    if _int_value(observed_minimum) > 0:
        configured.append(observed_passed)
    if _int_value(target_minimum) > 0:
        configured.append(target_passed)
    return any(configured) if configured else True


def _int_value(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
