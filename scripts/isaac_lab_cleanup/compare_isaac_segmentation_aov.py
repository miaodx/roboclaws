#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.core.json_sources import read_json_object

SCHEMA = "isaac_segmentation_aov_comparison_v1"
SEGMENTATION_TYPE = "semantic_segmentation"
BACKGROUND_LABELS = {"", "background", "unlabelled", "unlabeled"}


@dataclass(frozen=True)
class DecisionFeatures:
    control_has_tensor: bool
    candidate_has_tensor: bool
    control_has_non_background: bool
    candidate_has_non_background: bool
    candidate_labels_applied: bool
    candidate_collapsed: bool
    selected_match_count_zero: bool


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare generated-control and MolmoSpaces Isaac segmentation artifacts."
    )
    parser.add_argument("--control-state", type=Path, required=True)
    parser.add_argument("--candidate-state", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--require-decision",
        action="store_true",
        help="Exit non-zero when the comparison cannot name a decision-changing divergence.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        comparison = compare_states(
            control_state_path=args.control_state,
            candidate_state_path=args.candidate_state,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(comparison, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    if args.require_decision and not comparison["decision"]["first_divergent_layer"]:
        return 1
    return 0


def compare_states(*, control_state_path: Path, candidate_state_path: Path) -> dict[str, Any]:
    control_state = _read_json(control_state_path)
    candidate_state = _read_json(candidate_state_path)
    control = _summarize_state(control_state_path, control_state)
    candidate = _summarize_state(candidate_state_path, candidate_state)
    decision = _decision(control, candidate)
    return {
        "schema": SCHEMA,
        "status": "decision_ready" if decision["first_divergent_layer"] else "inconclusive",
        "control": control,
        "candidate": candidate,
        "decision": decision,
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return read_json_object(path, label="state artifact")
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"state artifact is missing: {path}") from exc
    except ValueError as exc:
        message = str(exc)
        if "must contain valid JSON object" in message:
            raise ValueError(f"state artifact must contain valid JSON object: {path}") from exc
        if "must contain a JSON object" in message:
            raise ValueError(f"state artifact must contain a JSON object: {path}") from exc
        raise


def _summarize_state(path: Path, state: dict[str, Any]) -> dict[str, Any]:
    segmentation = _dict(state.get("segmentation"))
    label_application = _dict(segmentation.get("semantic_label_application"))
    semantic_views = [_semantic_view_summary(view) for view in segmentation.get("view_outputs", [])]
    semantic_views = [item for item in semantic_views if item["present"]]
    candidate_bboxes = [
        _dict(item) for item in segmentation.get("candidate_bboxes", []) if isinstance(item, dict)
    ]
    labels = [str(item.get("label") or "") for item in candidate_bboxes]
    non_background_labels = [
        label for label in labels if _label_class(label) not in BACKGROUND_LABELS
    ]
    return {
        "artifact": str(path),
        "scene_usd": state.get("scene_usd"),
        "loaded_asset_kind": _dict(state.get("scene_load")).get("loaded_asset_kind"),
        "generated_scene_kind": _dict(state.get("real_runtime_smoke")).get("generated_scene_kind"),
        "stage_prim_count": _dict(state.get("real_runtime_smoke")).get("stage_prim_count"),
        "segmentation_status": segmentation.get("status"),
        "segmentation_available": segmentation.get("available"),
        "output_data_types": segmentation.get("output_data_types") or [],
        "tensor_output_available": segmentation.get("tensor_output_available"),
        "candidate_bbox_count": _int(segmentation.get("candidate_bbox_count")),
        "selected_usd_prim_match_count": _int(segmentation.get("selected_usd_prim_match_count")),
        "semantic_filter": segmentation.get("semantic_filter"),
        "label_application": {
            "status": label_application.get("status"),
            "applied_count": _int(label_application.get("applied_count")),
            "failed_count": _int(label_application.get("failed_count")),
            "missing_prim_count": _int(label_application.get("missing_prim_count")),
            "descendant_label_count": _int(label_application.get("descendant_label_count")),
            "labeled_prim_count": _int(label_application.get("labeled_prim_count")),
            "gprim_label_count": _int(label_application.get("gprim_label_count")),
            "mesh_label_count": _int(label_application.get("mesh_label_count")),
            "target_samples": label_application.get("target_samples") or [],
        },
        "semantic_view_count": len(semantic_views),
        "semantic_views": semantic_views,
        "first_semantic_view": semantic_views[0] if semantic_views else {},
        "candidate_label_count": len(labels),
        "candidate_labels": labels[:12],
        "non_background_label_count": len(non_background_labels),
        "non_background_labels": non_background_labels[:12],
        "full_frame_background_view_count": sum(
            1 for view in semantic_views if view["unique_id_count"] == 1
        ),
    }


def _semantic_view_summary(view: Any) -> dict[str, Any]:
    row = _dict(_dict(view).get("outputs")).get(SEGMENTATION_TYPE)
    row = _dict(row)
    candidates = [
        _dict(item) for item in _dict(view).get("candidate_bboxes", []) if isinstance(item, dict)
    ]
    labels = [str(item.get("label") or "") for item in candidates]
    return {
        "view": _dict(view).get("view"),
        "present": row.get("present") is True,
        "shape": row.get("shape") or [],
        "dtype": row.get("dtype"),
        "label_count": _int(row.get("label_count")),
        "unique_id_count": _int(row.get("unique_id_count")),
        "labels_available": row.get("labels_available") is True,
        "candidate_count": len(candidates),
        "labels": labels[:8],
        "non_background_label_count": sum(
            1 for label in labels if _label_class(label) not in BACKGROUND_LABELS
        ),
    }


def _decision(control: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    features = _decision_features(control, candidate)
    first_layer, classification, next_action = _first_divergence(features)
    return {
        "first_divergent_layer": first_layer,
        "root_cause_classification": classification,
        "next_action": next_action,
        "evidence": _decision_evidence(features),
    }


def _decision_features(control: dict[str, Any], candidate: dict[str, Any]) -> DecisionFeatures:
    control_has_tensor = SEGMENTATION_TYPE in set(control["output_data_types"])
    candidate_has_tensor = SEGMENTATION_TYPE in set(candidate["output_data_types"])
    control_has_non_background = control["non_background_label_count"] > 0
    candidate_has_non_background = candidate["non_background_label_count"] > 0
    candidate_labels_applied = (
        candidate["label_application"]["status"] == "applied"
        and candidate["label_application"]["applied_count"] > 0
        and candidate["label_application"]["failed_count"] == 0
    )
    candidate_collapsed = (
        candidate_has_tensor
        and candidate["semantic_view_count"] > 0
        and candidate["full_frame_background_view_count"] == candidate["semantic_view_count"]
    )
    return DecisionFeatures(
        control_has_tensor=control_has_tensor,
        candidate_has_tensor=candidate_has_tensor,
        control_has_non_background=control_has_non_background,
        candidate_has_non_background=candidate_has_non_background,
        candidate_labels_applied=candidate_labels_applied,
        candidate_collapsed=candidate_collapsed,
        selected_match_count_zero=candidate["selected_usd_prim_match_count"] == 0,
    )


def _first_divergence(features: DecisionFeatures) -> tuple[str, str, str]:
    if not features.control_has_tensor:
        return (
            "control_missing_semantic_tensor",
            "comparison_control_invalid",
            "Regenerate the generated-control segmentation artifact before comparing.",
        )
    if not features.candidate_has_tensor:
        return (
            "candidate_missing_semantic_tensor",
            "segmentation_request_or_capture",
            "Debug camera data_types/render-product tensor capture for the candidate scene.",
        )
    if (
        features.control_has_non_background
        and features.candidate_labels_applied
        and features.candidate_collapsed
    ):
        return (
            "semantic_tensor_ids_collapsed_to_background",
            "semantic_aov_rendered_geometry_not_labelled",
            "Probe whether labels must be authored on rendered payload/reference Gprims "
            "rather than MolmoSpaces scene-index prims, or defer Phase E segmentation.",
        )
    if features.control_has_non_background and not features.candidate_has_non_background:
        return (
            "semantic_label_map_has_no_candidate_geometry_labels",
            "semantic_label_projection",
            "Inspect label map contents and authored semantics on rendered descendants "
            "before changing selected-path matching.",
        )
    if features.selected_match_count_zero and features.candidate_has_non_background:
        return (
            "selected_path_matching",
            "roboclaws_candidate_matching",
            "Debug candidate label-to-selected-USD matching.",
        )
    return "", "", ""


def _decision_evidence(features: DecisionFeatures) -> list[str]:
    evidence: list[str] = []
    if features.control_has_tensor:
        evidence.append("control produced semantic_segmentation tensors")
    if features.candidate_has_tensor:
        evidence.append("candidate produced semantic_segmentation tensors")
    if features.control_has_non_background:
        evidence.append("control produced non-background semantic labels")
    if features.candidate_labels_applied:
        evidence.append("candidate scene-index labels were applied without failures")
    if features.candidate_collapsed:
        evidence.append("candidate semantic views each contain one tensor id")
    if features.selected_match_count_zero:
        evidence.append("candidate has zero selected USD prim matches")
    return evidence


def _label_class(label: str) -> str:
    return label.strip().casefold()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
