#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SUMMARY_SCHEMA = "scene_gaussian_map_alignment_evidence_summary_v1"
MANIFEST_SCHEMA = "scene_gaussian_map_alignment_manifest_v1"
TIERS = {"blocked", "candidate", "verified", "runtime_proven", "planner_backed"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize scene Gaussian/map alignment evidence without inventing claims."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("summarize", "manifest"),
        default="summarize",
    )
    parser.add_argument("--readiness-artifact", type=Path, required=True)
    parser.add_argument("--navigation-artifact", type=Path)
    parser.add_argument("--evidence-summary", type=Path)
    parser.add_argument("--map-bundle", type=Path)
    parser.add_argument("--alignment-id", default="")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        readiness = _read_json(args.readiness_artifact, label="readiness artifact")
        navigation = (
            _read_json(args.navigation_artifact, label="navigation artifact")
            if args.navigation_artifact
            else None
        )
        summary = (
            _read_json(args.evidence_summary, label="alignment evidence summary")
            if args.evidence_summary
            else summarize_alignment_evidence(
                readiness,
                navigation,
                readiness_artifact=str(args.readiness_artifact),
                navigation_artifact=str(args.navigation_artifact)
                if args.navigation_artifact
                else "",
            )
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc
    if args.command == "manifest":
        payload = build_alignment_manifest(
            readiness,
            navigation,
            evidence_summary=summary,
            readiness_artifact=str(args.readiness_artifact),
            navigation_artifact=str(args.navigation_artifact) if args.navigation_artifact else "",
            evidence_summary_artifact=str(args.evidence_summary) if args.evidence_summary else "",
            map_bundle=str(args.map_bundle) if args.map_bundle else "",
            alignment_id=args.alignment_id,
        )
    else:
        payload = summary
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def summarize_alignment_evidence(
    readiness: dict[str, Any],
    navigation: dict[str, Any] | None = None,
    *,
    readiness_artifact: str = "",
    navigation_artifact: str = "",
) -> dict[str, Any]:
    navigation = navigation or {}
    tier, tier_reason = _alignment_tier(readiness, navigation)
    blockers = _blockers(readiness, navigation, tier)
    summary = {
        "schema": SUMMARY_SCHEMA,
        "alignment_tier": tier,
        "tier_reason": tier_reason,
        "source_artifacts": {
            "readiness_artifact": readiness_artifact,
            "navigation_artifact": navigation_artifact,
        },
        "transform": {
            "map_overlay_status": readiness.get("map12_overlay_status")
            or _nested(readiness, "map12_overlay", "status"),
            "map_to_scene_transform_status": readiness.get("map12_to_b1_usd_transform_status")
            or _nested(readiness, "map12_overlay", "transform_status"),
            "semantic_source": readiness.get("semantic_source")
            or navigation.get("semantic_source"),
        },
        "gaussian_assets": _gaussian_assets(readiness, navigation),
        "semantics": {
            "semantic_usd_binding_status": readiness.get("semantic_usd_binding_status")
            or navigation.get("semantic_usd_binding_status"),
            "semantic_anchors_are_usd_truth": bool(
                readiness.get("semantic_anchors_are_usd_truth")
                or navigation.get("semantic_anchors_are_usd_truth")
            ),
            "usd_object_index_ready": bool(readiness.get("usd_object_index_ready")),
            "usd_receptacle_index_ready": bool(readiness.get("usd_receptacle_index_ready")),
            "manipulation_supported": bool(
                readiness.get("manipulation_supported") or navigation.get("manipulation_supported")
            ),
        },
        "navigation": {
            "status": navigation.get("status"),
            "robot_navigation_supported": bool(
                navigation.get("robot_navigation_supported")
                or readiness.get("robot_navigation_supported")
            ),
            "robot_view_evidence_status": navigation.get("robot_view_evidence_status")
            or readiness.get("robot_view_evidence_status"),
            "navigation_provenance": navigation.get("navigation_provenance")
            or readiness.get("navigation_provenance"),
            "planner_backed": bool(navigation.get("planner_backed")),
            "physical_robot": bool(navigation.get("physical_robot")),
            "waypoint_count": int(
                navigation.get("navigation_waypoint_count")
                or readiness.get("navigation_waypoint_count")
                or 0
            ),
        },
        "open_blockers": blockers,
        "next_promotion_step": _next_promotion_step(tier, blockers),
    }
    _assert_known_tier(summary["alignment_tier"])
    return summary


def build_alignment_manifest(
    readiness: dict[str, Any],
    navigation: dict[str, Any] | None = None,
    *,
    evidence_summary: dict[str, Any] | None = None,
    readiness_artifact: str = "",
    navigation_artifact: str = "",
    evidence_summary_artifact: str = "",
    map_bundle: str = "",
    alignment_id: str = "",
) -> dict[str, Any]:
    navigation = navigation or {}
    summary = evidence_summary or summarize_alignment_evidence(
        readiness,
        navigation,
        readiness_artifact=readiness_artifact,
        navigation_artifact=navigation_artifact,
    )
    _assert_known_tier(str(summary["alignment_tier"]))
    overlay = _dict(readiness.get("map12_overlay"))
    transform = _dict(overlay.get("transform"))
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "alignment_id": alignment_id or _default_alignment_id(readiness, map_bundle),
        "contract_note": (
            "This is a lightweight alignment contract. It records how independent "
            "scene, Gaussian, and map artifacts were related for evidence review; "
            "it is not a fused USD/Gaussian scene and does not make semantic USD truth claims."
        ),
        "source_assets": {
            "scene_root": str(readiness.get("b1_root") or ""),
            "scene_usd": str(_nested(readiness, "b1_geometry", "local_geometry", "path") or ""),
            "gaussian_scene_usd": str(
                _nested(readiness, "b1_geometry", "gaussian_scene_usd", "path") or ""
            ),
            "full_floor_usd": str(
                _nested(readiness, "b1_geometry", "full_floor_usd", "path") or ""
            ),
            "map_root": str(readiness.get("map12_root") or ""),
            "map_bundle": map_bundle,
            "semantic_source": readiness.get("semantic_source")
            or navigation.get("semantic_source"),
        },
        "frames": {
            "map_frame": transform.get("source_frame") or "robot_map_12_map",
            "scene_frame": transform.get("target_frame") or "b1_rebuilt_scene_usd_world_candidate",
            "pose_source": readiness.get("semantic_source") or navigation.get("semantic_source"),
        },
        "transform": {
            "status": readiness.get("map12_to_b1_usd_transform_status")
            or overlay.get("transform_status"),
            "method": transform.get("method"),
            "parameters": _transform_parameters(transform),
            "source_bounds": overlay.get("source_bounds") or {},
            "target_bounds": overlay.get("target_bounds") or {},
            "residual_evidence": overlay.get("residual_evidence") or {},
        },
        "candidate_correspondences": _candidate_correspondences(overlay),
        "evidence": {
            "alignment_tier": summary["alignment_tier"],
            "tier_reason": summary.get("tier_reason"),
            "readiness_artifact": readiness_artifact,
            "navigation_artifact": navigation_artifact,
            "evidence_summary_artifact": evidence_summary_artifact,
            "report_artifact": _default_report_artifact(navigation_artifact, readiness_artifact),
            "robot_view_evidence_status": _nested(
                summary, "navigation", "robot_view_evidence_status"
            ),
            "navigation_provenance": _nested(summary, "navigation", "navigation_provenance"),
            "planner_backed": bool(_nested(summary, "navigation", "planner_backed")),
            "waypoint_count": int(_nested(summary, "navigation", "waypoint_count") or 0),
        },
        "gaussian_assets": summary.get("gaussian_assets") or {},
        "semantics": summary.get("semantics") or {},
        "open_blockers": list(summary.get("open_blockers") or []),
        "next_promotion_step": summary.get("next_promotion_step") or "",
        "promotion_requirements": {
            "verified": "Add at least three named map/scene anchor correspondences with residuals.",
            "runtime_proven": (
                "Render or navigate robot views from the verified or candidate transform."
            ),
            "planner_backed": "Add Nav2-equivalent planner path proof in the aligned frame.",
            "semantic_usd_truth": (
                "Add segmentation, object manifest, or anchor-to-USD correspondences "
                "before claiming semantic_anchors_are_usd_truth."
            ),
            "fused_scene": (
                "Generate fused USD/Gaussian only after transform and semantic binding "
                "are verified enough to avoid baking candidate overlay into truth."
            ),
        },
    }
    return manifest


def _read_json(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} source is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} source must contain valid JSON object: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} source must contain a JSON object: {path}")
    return payload


def _alignment_tier(readiness: dict[str, Any], navigation: dict[str, Any]) -> tuple[str, str]:
    validation_errors = _validation_errors(readiness) + _validation_errors(navigation)
    if validation_errors:
        return "blocked", "artifact validation errors are present"
    if navigation.get("status") == "blocked":
        return "blocked", "navigation artifact is blocked"
    if _overlay_status(readiness) == "blocked":
        return "blocked", "map-to-scene overlay is blocked"
    if navigation.get("planner_backed") and navigation.get("robot_navigation_supported"):
        return "planner_backed", "navigation artifact reports planner-backed robot navigation"
    if navigation.get("robot_navigation_supported") and _robot_views_available(navigation):
        return "runtime_proven", "robot-view smoke evidence exists at aligned candidate poses"
    if _transform_status(readiness) in {"verified", "anchor_verified", "residual_verified"}:
        return "verified", "map-to-scene transform has verified anchor evidence"
    if _overlay_status(readiness) in {"candidate", "ready"} or _transform_status(readiness):
        return "candidate", "only heuristic or unverified map-to-scene alignment is available"
    return "blocked", "no usable map-to-scene alignment evidence was found"


def _gaussian_assets(readiness: dict[str, Any], navigation: dict[str, Any]) -> dict[str, Any]:
    point_clouds = _nested(readiness, "b1_geometry", "gaussian_point_clouds") or []
    referenced_layers = []
    for stage_key in ("local_geometry", "full_floor_usd", "full_floor_default_usd"):
        referenced_layers.extend(
            _nested(readiness, "b1_geometry", stage_key, "local_referenced_layers") or []
        )
    gaussian_layers = _gaussian_layer_paths(readiness, referenced_layers)
    explicit_render_claim = bool(
        readiness.get("gaussian_rendered")
        or readiness.get("renderer_consumed_gaussian_asset")
        or navigation.get("gaussian_rendered")
        or navigation.get("renderer_consumed_gaussian_asset")
    )
    render_status = "rendered" if explicit_render_claim else "not_claimed"
    if (point_clouds or gaussian_layers) and not explicit_render_claim:
        render_status = "inventoried_only"
    return {
        "point_cloud_count": len(point_clouds) if isinstance(point_clouds, list) else 0,
        "point_cloud_paths": [
            str(item.get("path"))
            for item in point_clouds
            if isinstance(item, dict) and item.get("path")
        ],
        "usd_references_gaussian_layers": bool(gaussian_layers),
        "usd_gaussian_layers": gaussian_layers,
        "render_status": render_status,
        "claim_note": (
            "Renderer consumption is explicit in the artifact."
            if explicit_render_claim
            else "Gaussian/splat assets are not claimed as rendered by this summary."
        ),
    }


def _gaussian_layer_paths(readiness: dict[str, Any], referenced_layers: list[Any]) -> list[str]:
    paths: list[str] = []
    for path in referenced_layers:
        if _looks_like_gaussian_layer(path):
            paths.append(str(path))
    for stage_key in ("local_geometry", "full_floor_usd", "full_floor_default_usd"):
        path = _nested(readiness, "b1_geometry", stage_key, "path")
        if _looks_like_gaussian_layer(path):
            paths.append(str(path))
    for item in _nested(readiness, "b1_geometry", "gaussian_layers") or []:
        if isinstance(item, dict) and item.get("path"):
            paths.append(str(item["path"]))
    for item in _nested(readiness, "b1_geometry", "scene_partitions") or []:
        path = _nested(item, "gaussian_layer", "path") if isinstance(item, dict) else None
        if path:
            paths.append(str(path))
    return _dedupe(paths)


def _looks_like_gaussian_layer(path: Any) -> bool:
    raw = str(path or "").lower()
    return bool(raw) and ("gauss" in raw or "splat" in raw or "scene_gs" in raw)


def _blockers(readiness: dict[str, Any], navigation: dict[str, Any], tier: str) -> list[str]:
    blockers: list[str] = []
    blockers.extend(str(item) for item in readiness.get("blockers") or [])
    blockers.extend(_validation_errors(readiness))
    blockers.extend(_validation_errors(navigation))
    for failure in navigation.get("child_failures") or []:
        if isinstance(failure, dict):
            blockers.append(str(failure.get("stderr_tail") or failure.get("reason") or failure))
        else:
            blockers.append(str(failure))
    if tier in {"candidate", "runtime_proven"} and not navigation.get("planner_backed"):
        blockers.append("planner_backed navigation proof is missing")
    if not (
        readiness.get("semantic_anchors_are_usd_truth")
        or navigation.get("semantic_anchors_are_usd_truth")
    ):
        blockers.append("semantic anchors are not bound to USD/scene object truth")
    if not (readiness.get("manipulation_supported") or navigation.get("manipulation_supported")):
        blockers.append(
            "manipulation is unsupported until object/receptacle binding and pick/place proof exist"
        )
    if _gaussian_assets(readiness, navigation)["render_status"] != "rendered":
        blockers.append("Gaussian/splat rendering is not proven")
    return _dedupe(blockers)


def _next_promotion_step(tier: str, blockers: list[str]) -> str:
    if tier == "blocked":
        return (
            "Fix the first blocked asset or validation error, then rebuild the readiness artifact."
        )
    if tier == "candidate":
        return (
            "Add matched map/scene anchors with residuals, or run robot-view smoke "
            "if anchor verification is not available yet."
        )
    if tier == "verified":
        return "Run Isaac or robot-view navigation smoke from the verified transform."
    if tier == "runtime_proven":
        if any("planner_backed" in blocker for blocker in blockers):
            return (
                "Add planner/Nav2-equivalent path proof before claiming planner-backed alignment."
            )
        return "Add semantic object/receptacle binding before claiming manipulation readiness."
    return (
        "Keep planner evidence linked to semantic binding and manipulation proofs "
        "before expanding task claims."
    )


def _validation_errors(payload: dict[str, Any]) -> list[str]:
    validation = payload.get("validation") if isinstance(payload, dict) else None
    if not isinstance(validation, dict):
        return []
    if validation.get("status") in {None, "passed"}:
        return []
    return [str(error) for error in validation.get("errors") or ["validation failed"]]


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _transform_parameters(transform: dict[str, Any]) -> dict[str, Any]:
    keys = ("scale_x", "scale_y", "translate_x", "translate_y")
    return {key: transform[key] for key in keys if key in transform}


def _candidate_correspondences(overlay: dict[str, Any]) -> list[dict[str, Any]]:
    correspondences = []
    for waypoint in overlay.get("candidate_waypoints") or []:
        if not isinstance(waypoint, dict):
            continue
        correspondences.append(
            {
                "status": "candidate",
                "source_anchor_id": waypoint.get("source_anchor_id"),
                "waypoint_id": waypoint.get("waypoint_id"),
                "label": waypoint.get("label"),
                "semantic_source": waypoint.get("semantic_source"),
                "map_pose": waypoint.get("map12_nav_goal") or {},
                "scene_pose": waypoint.get("b1_pose") or {},
                "usd_binding_status": "not_bound",
            }
        )
    return correspondences


def _default_alignment_id(readiness: dict[str, Any], map_bundle: str) -> str:
    bundle_name = Path(map_bundle).name if map_bundle else "map12"
    scene_path = str(_nested(readiness, "b1_geometry", "local_geometry", "path") or "")
    scene_name = Path(scene_path).stem if scene_path else "scene"
    return f"{scene_name}-{bundle_name}-candidate-overlay"


def _default_report_artifact(navigation_artifact: str, readiness_artifact: str) -> str:
    for artifact in (navigation_artifact, readiness_artifact):
        if artifact:
            return str(Path(artifact).parent / "report.html")
    return ""


def _overlay_status(readiness: dict[str, Any]) -> str:
    return str(
        readiness.get("map12_overlay_status") or _nested(readiness, "map12_overlay", "status") or ""
    )


def _transform_status(readiness: dict[str, Any]) -> str:
    return str(
        readiness.get("map12_to_b1_usd_transform_status")
        or _nested(readiness, "map12_overlay", "transform_status")
        or ""
    )


def _robot_views_available(navigation: dict[str, Any]) -> bool:
    return (
        navigation.get("status") == "passed"
        and navigation.get("robot_view_evidence_status") == "available"
        and int(navigation.get("navigation_waypoint_count") or 0) >= 2
    )


def _nested(payload: dict[str, Any], *keys: str) -> Any:
    item: Any = payload
    for key in keys:
        if not isinstance(item, dict):
            return None
        item = item.get(key)
    return item


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _assert_known_tier(tier: str) -> None:
    if tier not in TIERS:
        raise ValueError(f"unexpected alignment tier: {tier!r}")


if __name__ == "__main__":
    raise SystemExit(main())
