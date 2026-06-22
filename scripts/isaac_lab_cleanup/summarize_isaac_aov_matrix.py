#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.isaac_lab_cleanup.compare_isaac_segmentation_aov import (
    BACKGROUND_LABELS,
    SEGMENTATION_TYPE,
    _dict,
    _int,
    _label_class,
)

SCHEMA = "isaac_segmentation_aov_matrix_v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize Isaac segmentation AOV control/candidate artifacts."
    )
    parser.add_argument(
        "--entry",
        action="append",
        default=[],
        metavar="LABEL=PATH",
        help="Matrix entry state/preflight JSON path, for example A=output/.../state.json.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--require-decision", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = summarize_entries(args.entry)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    payload = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    if args.require_decision and result["decision"]["status"] == "inconclusive":
        return 1
    return 0


def summarize_entries(entries: list[str]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for spec in entries:
        label, path = _parse_entry(spec)
        summaries[label] = _summarize_path(path)
    decision = _matrix_decision(summaries)
    return {
        "schema": SCHEMA,
        "status": decision["status"],
        "entries": summaries,
        "decision": decision,
    }


def _parse_entry(spec: str) -> tuple[str, Path]:
    label, separator, path = spec.partition("=")
    if not separator or not label.strip() or not path.strip():
        raise ValueError(f"entry must be LABEL=PATH: {spec}")
    return label.strip(), Path(path.strip())


def _summarize_path(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    if payload.get("schema") == "roboclaws_isaac_lab_runtime_preflight_v1":
        return _summarize_preflight(path, payload)
    return _summarize_state(path, payload)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"artifact is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"artifact must contain valid JSON object: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"artifact must contain a JSON object: {path}")
    return payload


def _summarize_preflight(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact": str(path),
        "artifact_kind": "runtime_preflight",
        "status": payload.get("status"),
        "runtime_dir": payload.get("runtime_dir"),
        "isaaclab_source": payload.get("isaaclab_source"),
        "checks": payload.get("checks") or [],
        "install_attempt": payload.get("install_attempt") or {},
    }


def _summarize_state(path: Path, state: dict[str, Any]) -> dict[str, Any]:
    segmentation = _dict(state.get("segmentation"))
    label_application = _dict(segmentation.get("semantic_label_application"))
    semantic_views = [
        _semantic_view_summary(view)
        for view in segmentation.get("view_outputs", [])
        if isinstance(view, dict)
    ]
    semantic_views = [item for item in semantic_views if item["present"]]
    candidate_bboxes = [
        dict(item) for item in segmentation.get("candidate_bboxes", []) if isinstance(item, dict)
    ]
    labels = [str(item.get("label") or "") for item in candidate_bboxes]
    non_background_labels = [
        label for label in labels if _label_class(label) not in BACKGROUND_LABELS
    ]
    return {
        "artifact": str(path),
        "artifact_kind": "runtime_state",
        "scene_usd": state.get("scene_usd"),
        "loaded_asset_kind": _dict(state.get("scene_load")).get("loaded_asset_kind"),
        "generated_scene_kind": _dict(state.get("real_runtime_smoke")).get("generated_scene_kind"),
        "segmentation_status": segmentation.get("status"),
        "output_data_types": segmentation.get("output_data_types") or [],
        "tensor_output_available": segmentation.get("tensor_output_available"),
        "candidate_bbox_count": _int(segmentation.get("candidate_bbox_count")),
        "selected_usd_prim_match_count": _int(segmentation.get("selected_usd_prim_match_count")),
        "semantic_view_count": len(semantic_views),
        "full_frame_background_view_count": sum(
            1 for view in semantic_views if view["unique_id_count"] == 1
        ),
        "non_background_label_count": len(non_background_labels),
        "candidate_labels": labels[:12],
        "non_background_labels": non_background_labels[:12],
        "label_application": {
            "status": label_application.get("status"),
            "applied_count": _int(label_application.get("applied_count")),
            "failed_count": _int(label_application.get("failed_count")),
            "missing_prim_count": _int(label_application.get("missing_prim_count")),
            "descendant_label_count": _int(label_application.get("descendant_label_count")),
            "gprim_label_count": _int(label_application.get("gprim_label_count")),
            "mesh_label_count": _int(label_application.get("mesh_label_count")),
            "target_samples": label_application.get("target_samples") or [],
        },
    }


def _semantic_view_summary(view: dict[str, Any]) -> dict[str, Any]:
    row = _dict(_dict(view.get("outputs")).get(SEGMENTATION_TYPE))
    return {
        "view": view.get("view"),
        "present": row.get("present") is True,
        "unique_id_count": _int(row.get("unique_id_count")),
    }


def _matrix_decision(entries: dict[str, Any]) -> dict[str, Any]:
    state_entries = {
        label: entry
        for label, entry in entries.items()
        if entry.get("artifact_kind") == "runtime_state"
    }
    controls = {
        label: entry
        for label, entry in state_entries.items()
        if entry.get("loaded_asset_kind") == "generated_runtime_smoke_usd"
    }
    candidates = {
        label: entry
        for label, entry in state_entries.items()
        if entry.get("loaded_asset_kind") == "local_scene_usd"
    }
    control_ok = any(_has_non_background_semantic(entry) for entry in controls.values())
    official_ok = any(
        entry.get("generated_scene_kind") == "isaac_official_blocks"
        and _has_non_background_semantic(entry)
        for entry in controls.values()
    )
    candidate_collapsed = any(_is_collapsed_background(entry) for entry in candidates.values())
    candidate_labelled_gprims = any(
        _dict(entry.get("label_application")).get("gprim_label_count", 0) > 0
        or _dict(entry.get("label_application")).get("mesh_label_count", 0) > 0
        for entry in candidates.values()
    )
    preflights = {
        label: entry
        for label, entry in entries.items()
        if entry.get("artifact_kind") == "runtime_preflight"
    }

    if official_ok and candidate_collapsed and candidate_labelled_gprims:
        status = "decision_ready"
        classification = "molmospaces_scene_usd_semantic_aov_projection"
        next_action = (
            "Treat Isaac AOV support as present in this runtime and isolate the "
            "MolmoSpaces USD composition/render-product semantics path."
        )
    elif control_ok and candidate_collapsed:
        status = "decision_ready"
        classification = "molmospaces_scene_usd_semantic_aov_projection"
        next_action = (
            "Isaac semantic AOV works for generated controls, but the candidate "
            "MolmoSpaces scene still collapses to background."
        )
    else:
        status = "inconclusive"
        classification = ""
        next_action = "Regenerate missing A/B/C evidence before deciding the root cause."

    return {
        "status": status,
        "root_cause_classification": classification,
        "control_has_non_background": control_ok,
        "official_control_has_non_background": official_ok,
        "candidate_collapsed_to_background": candidate_collapsed,
        "candidate_labelled_gprims_or_meshes": candidate_labelled_gprims,
        "runtime_preflight_count": len(preflights),
        "next_action": next_action,
    }


def _has_non_background_semantic(entry: dict[str, Any]) -> bool:
    return SEGMENTATION_TYPE in set(entry.get("output_data_types") or []) and (
        _int(entry.get("non_background_label_count")) > 0
    )


def _is_collapsed_background(entry: dict[str, Any]) -> bool:
    return (
        SEGMENTATION_TYPE in set(entry.get("output_data_types") or [])
        and _int(entry.get("semantic_view_count")) > 0
        and _int(entry.get("semantic_view_count"))
        == _int(entry.get("full_frame_background_view_count"))
    )


if __name__ == "__main__":
    raise SystemExit(main())
