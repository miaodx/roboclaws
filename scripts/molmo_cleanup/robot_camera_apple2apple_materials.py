from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.household.artifact_paths import output_relpath


def probe_manifest_summary(
    payload: dict[str, Any],
    *,
    manifest_path: Path,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    summary = _dict(payload.get("summary"))
    scene = _dict(payload.get("scene"))
    render = _dict(summary.get("render_contract_diagnostics"))
    camera = _dict(summary.get("camera_contract_diagnostics"))
    residual = _dict(summary.get("residual_triage"))
    domain_checks = _dict(summary.get("render_domain_checks"))
    check_by_id = {
        str(item.get("check_id")): item
        for item in domain_checks.get("checks") or []
        if isinstance(item, dict) and item.get("check_id")
    }
    tone_color = _dict(check_by_id.get("tone_color_response"))
    fpv_lens = _dict(camera.get("fpv_lens_delta_summary"))
    fpv_pose = _dict(camera.get("fpv_world_pose_delta_summary"))
    rel_path = output_relpath(manifest_path, output_dir or manifest_path.parent)
    return {
        "status": "loaded",
        "path": rel_path,
        "scene": {
            "scene_source": scene.get("scene_source"),
            "scene_index": scene.get("scene_index"),
            "seed": scene.get("seed"),
            "generated_mess_count": scene.get("generated_mess_count"),
            "render_width": scene.get("render_width"),
            "render_height": scene.get("render_height"),
            "scene_usd_path": scene.get("scene_usd_path"),
        },
        "location_count": summary.get("location_count"),
        "fpv_mean_abs_rgb_avg": summary.get("fpv_mean_abs_rgb_avg"),
        "chase_mean_abs_rgb_avg": summary.get("chase_mean_abs_rgb_avg"),
        "camera_contract_status": camera.get("status"),
        "fpv_lens_status": fpv_lens.get("status"),
        "fpv_world_pose_status": fpv_pose.get("status"),
        "render_contract_status": render.get("status"),
        "mujoco_light_count": render.get("mujoco_light_count"),
        "isaac_light_count": render.get("isaac_light_count"),
        "isaac_shadow_disabled_prim_count": render.get("isaac_shadow_disabled_prim_count"),
        "residual_status": residual.get("status"),
        "fpv_residual_classes": _dict_path(residual, ("views", "fpv", "residual_classes")),
        "tone_color_status": tone_color.get("status"),
        "comparison_rgb_gain_applied": tone_color.get("comparison_rgb_gain_applied"),
        "comparison_rgb_gain": tone_color.get("comparison_rgb_gain"),
    }


def comparison_probe_comparable(
    baseline: dict[str, Any],
    probe: dict[str, Any],
) -> bool:
    baseline_scene = _dict(baseline.get("scene"))
    probe_scene = _dict(probe.get("scene"))
    keys = ("scene_source", "scene_index", "seed", "render_width", "render_height")
    if any(baseline_scene.get(key) != probe_scene.get(key) for key in keys):
        return False
    if probe.get("camera_contract_status") != baseline.get("camera_contract_status"):
        return False
    pose_status = probe.get("fpv_world_pose_status")
    baseline_pose_status = baseline.get("fpv_world_pose_status")
    if pose_status and baseline_pose_status and pose_status != baseline_pose_status:
        return False
    lens_status = probe.get("fpv_lens_status")
    baseline_lens_status = baseline.get("fpv_lens_status")
    return not (lens_status and baseline_lens_status and lens_status != baseline_lens_status)


def comparison_probe_delta(
    baseline: dict[str, Any],
    probe: dict[str, Any],
) -> dict[str, Any]:
    baseline_fpv = _float_or_none(baseline.get("fpv_mean_abs_rgb_avg"))
    probe_fpv = _float_or_none(probe.get("fpv_mean_abs_rgb_avg"))
    baseline_chase = _float_or_none(baseline.get("chase_mean_abs_rgb_avg"))
    probe_chase = _float_or_none(probe.get("chase_mean_abs_rgb_avg"))
    fpv_delta = _rounded_delta(probe_fpv, baseline_fpv)
    chase_delta = _rounded_delta(probe_chase, baseline_chase)
    return {
        "fpv_mean_abs_rgb_delta": fpv_delta,
        "chase_mean_abs_rgb_delta": chase_delta,
        "fpv_improvement": fpv_delta is not None and fpv_delta < -1.0,
        "fpv_worse": fpv_delta is not None and fpv_delta > 1.0,
        "chase_improvement": chase_delta is not None and chase_delta < -1.0,
        "chase_worse": chase_delta is not None and chase_delta > 1.0,
    }


def material_response_probe_history(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    return _probe_history(
        manifest,
        output_dir=output_dir,
        probe_manifest_paths=probe_manifest_paths,
        schema="robot_camera_material_response_probe_history_v1",
        count_delta_when_comparable_only=False,
        interpretation=(
            "Historical material-response probes are comparison evidence only. They "
            "separate texture colorspace, PreviewSurface roughness/specular response, "
            "and tone/material effects from the head-camera contract."
        ),
    )


def tone_color_probe_history(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    return _probe_history(
        manifest,
        output_dir=output_dir,
        probe_manifest_paths=probe_manifest_paths,
        schema="robot_camera_tone_color_probe_history_v1",
        count_delta_when_comparable_only=True,
        interpretation=(
            "Historical tone/color probes are comparison evidence only. They show whether "
            "RGB gain or tone calibration reduces FPV residuals under the same head-camera "
            "contract before any default renderer or policy-input change."
        ),
    )


def texture_colorspace_material_response_check(
    per_location: list[dict[str, Any]],
) -> dict[str, Any]:
    deltas = [_dict(item.get("target_contract_delta")) for item in per_location]
    delta_counts = _status_counts(str(item.get("status") or "") for item in deltas)
    bindings = [_dict(item.get("target_usd_binding")) for item in per_location]
    target_summaries = [texture_material_target_summary(item) for item in per_location]
    target_status_counts = _status_counts(
        str(item.get("material_response_status") or "") for item in target_summaries
    )
    texture_counts = _texture_match_counts(per_location)
    missing_ref_count = sum(
        int(binding.get("missing_referenced_asset_count") or 0) for binding in bindings
    )
    high_residual_targets = _high_residual_targets(target_summaries)
    status = _texture_colorspace_status(
        delta_counts=delta_counts,
        missing_ref_count=missing_ref_count,
        texture_path_full_delta_count=texture_counts["texture_path_full_delta_count"],
        target_location_count=len(per_location),
    )
    return {
        "check_id": "texture_colorspace_material_response",
        "status": status,
        "target_location_count": len(per_location),
        "target_contract_delta_counts": delta_counts,
        "exact_public_id_binding_count": sum(
            1 for binding in bindings if binding.get("match_strategy") == "exact_public_id"
        ),
        "missing_referenced_asset_count": missing_ref_count,
        **texture_counts,
        "material_response_status_counts": target_status_counts,
        "texture_backing_mismatch_count": sum(
            1 for item in target_summaries if item.get("texture_backing_mismatch")
        ),
        "rgba_diffuse_color_mismatch_count": sum(
            1 for item in target_summaries if item.get("rgba_diffuse_color_mismatch")
        ),
        "high_residual_target_count": len(high_residual_targets),
        "high_residual_targets": high_residual_targets[:5],
        "recommended_next_action": (
            "For high-residual FPV views, compare texture color space, sampler behavior, "
            "material albedo, and roughness/specular response even when texture basenames match."
        ),
    }


def texture_material_target_summary(item: dict[str, Any]) -> dict[str, Any]:
    target = _dict(item.get("target"))
    binding = _dict(item.get("target_usd_binding"))
    delta = _dict(item.get("target_contract_delta"))
    mujoco = _dict(item.get("mujoco_target_contract"))
    isaac = _dict(item.get("isaac_target_contract"))
    material_counts = _target_material_counts(mujoco=mujoco, isaac=isaac)
    texture_files = _target_texture_files(mujoco=mujoco, isaac=isaac)
    residual_class = str(item.get("fpv_residual_class") or "")
    indicators = _material_response_indicators(
        binding=binding,
        delta=delta,
        material_counts=material_counts,
        texture_files=texture_files,
        residual_class=residual_class,
    )
    return {
        "target_id": target.get("target_id"),
        "target_kind": target.get("kind"),
        "fpv_mean_abs_rgb": item.get("fpv_mean_abs_rgb"),
        "fpv_residual_class": item.get("fpv_residual_class"),
        "fpv_edge_abs_diff": item.get("fpv_edge_abs_diff"),
        "fpv_rgb_gain_oracle_mean_abs_rgb_after_gain": item.get(
            "fpv_rgb_gain_oracle_mean_abs_rgb_after_gain"
        ),
        "fpv_mujoco_mean_luminance": item.get("fpv_mujoco_mean_luminance"),
        "fpv_isaac_mean_luminance": item.get("fpv_isaac_mean_luminance"),
        "target_contract_status": delta.get("status"),
        "usd_match_strategy": binding.get("match_strategy"),
        "missing_referenced_asset_count": binding.get("missing_referenced_asset_count"),
        "mujoco_visual_count": mujoco.get("visual_geom_count"),
        **material_counts,
        **texture_files,
        "material_response_status": _material_response_status(indicators, residual_class),
        "material_response_indicators": indicators,
    }


def path_basenames(values: list[str]) -> list[str]:
    return sorted({Path(str(value)).name for value in values if value})


def usd_preview_surface_material_model_check(
    *,
    manifest: dict[str, Any],
    output_dir: Path,
    per_location: list[dict[str, Any]],
    probe_manifest_paths: list[Path] | None,
) -> dict[str, Any]:
    probe_history = material_response_probe_history(
        manifest,
        output_dir=output_dir,
        probe_manifest_paths=probe_manifest_paths,
    )
    counts = _preview_surface_material_counts(per_location)
    return {
        "check_id": "usd_preview_surface_material_model",
        "status": _preview_surface_status(counts),
        "isaac_material_binding_count": counts["isaac_material_binding_count"],
        "isaac_preview_surface_binding_count": counts["isaac_preview_surface_binding_count"],
        "isaac_diffuse_texture_binding_count": counts["isaac_diffuse_texture_binding_count"],
        "mujoco_visual_count": counts["mujoco_visual_count"],
        "mujoco_rgba_visual_count": counts["mujoco_rgba_visual_count"],
        "preview_surface_input_counts": _status_counts(counts["preview_input_statuses"]),
        "high_residual_target_count": len(counts["high_residual_targets"]),
        "high_residual_targets": counts["high_residual_targets"][:5],
        "probe_history": probe_history,
        "recommended_next_action": _preview_surface_next_action(probe_history),
    }


def preview_surface_target_summary(item: dict[str, Any]) -> dict[str, Any]:
    target = _dict(item.get("target"))
    mujoco = _dict(item.get("mujoco_target_contract"))
    isaac = _dict(item.get("isaac_target_contract"))
    visuals = [_dict(value) for value in mujoco.get("visuals") or []]
    bindings = [_dict(value) for value in isaac.get("bindings") or []]
    return {
        "target_id": target.get("target_id"),
        "target_kind": target.get("kind"),
        "fpv_mean_abs_rgb": item.get("fpv_mean_abs_rgb"),
        "fpv_residual_class": item.get("fpv_residual_class"),
        "fpv_mujoco_mean_luminance": item.get("fpv_mujoco_mean_luminance"),
        "fpv_isaac_mean_luminance": item.get("fpv_isaac_mean_luminance"),
        "mujoco_materials": mujoco.get("materials"),
        "mujoco_textures": mujoco.get("textures"),
        "mujoco_rgba_values": [visual.get("rgba") for visual in visuals if visual.get("rgba")][:5],
        "isaac_materials": isaac.get("materials"),
        "isaac_diffuse_texture_basenames": path_basenames(
            [str(value) for value in isaac.get("texture_files") or []]
        ),
        "isaac_diffuse_colors": [
            binding.get("diffuse_color") for binding in bindings if binding.get("diffuse_color")
        ][:5],
        "isaac_preview_surface_inputs": [
            _dict(binding.get("preview_surface_inputs"))
            for binding in bindings
            if binding.get("has_preview_surface")
        ][:5],
        "isaac_texture_source_color_spaces": sorted(
            {
                str(binding.get("texture_source_color_space"))
                for binding in bindings
                if binding.get("texture_source_color_space")
            }
        ),
        "isaac_texture_scales": [
            binding.get("texture_scale") for binding in bindings if binding.get("texture_scale")
        ][:5],
        "isaac_texture_fallbacks": [
            binding.get("texture_fallback")
            for binding in bindings
            if binding.get("texture_fallback")
        ][:5],
        "isaac_texture_wrap_modes": sorted(
            {
                f"{binding.get('texture_wrap_s')}/{binding.get('texture_wrap_t')}"
                for binding in bindings
                if binding.get("texture_wrap_s") or binding.get("texture_wrap_t")
            }
        ),
    }


def _probe_history(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    probe_manifest_paths: list[Path] | None,
    schema: str,
    count_delta_when_comparable_only: bool,
    interpretation: str,
) -> dict[str, Any]:
    paths = [Path(path) for path in probe_manifest_paths or []]
    if not paths:
        return {"schema": schema, "status": "not_attached", "probe_count": 0, "probes": []}
    baseline = probe_manifest_summary(
        manifest,
        manifest_path=output_dir / "comparison_manifest.json",
    )
    probes: list[dict[str, Any]] = []
    counts = {
        "comparable": 0,
        "improved": 0,
        "worsened": 0,
        "neutral": 0,
    }
    for path in paths:
        probe = _load_probe_manifest(path, output_dir=output_dir)
        if probe.get("status") == "loaded":
            _annotate_probe_history_row(
                probe,
                baseline=baseline,
                counts=counts,
                count_delta_when_comparable_only=count_delta_when_comparable_only,
            )
        probes.append(probe)
    return {
        "schema": schema,
        "status": _probe_history_status(counts),
        "baseline": baseline,
        "probe_count": len(probes),
        "comparable_probe_count": counts["comparable"],
        "improved_probe_count": counts["improved"],
        "worsened_probe_count": counts["worsened"],
        "neutral_probe_count": counts["neutral"],
        "probes": probes,
        "interpretation": interpretation,
    }


def _annotate_probe_history_row(
    probe: dict[str, Any],
    *,
    baseline: dict[str, Any],
    counts: dict[str, int],
    count_delta_when_comparable_only: bool,
) -> None:
    comparable = comparison_probe_comparable(baseline, probe)
    probe["comparable_to_current"] = comparable
    if comparable:
        counts["comparable"] += 1
    delta = comparison_probe_delta(baseline, probe)
    probe["delta_vs_current"] = delta
    should_count_delta = comparable or not count_delta_when_comparable_only
    if should_count_delta and delta.get("fpv_improvement") is True:
        counts["improved"] += 1
    if should_count_delta and delta.get("fpv_worse") is True:
        counts["worsened"] += 1
    if (
        comparable
        and delta.get("fpv_improvement") is not True
        and delta.get("fpv_worse") is not True
    ):
        counts["neutral"] += 1


def _probe_history_status(counts: dict[str, int]) -> str:
    if counts["improved"]:
        return "prior_probe_improved"
    if counts["worsened"] and counts["comparable"]:
        return "prior_probes_worse"
    if counts["comparable"]:
        return "prior_probes_no_fpv_gain"
    return "no_comparable_probe"


def _load_probe_manifest(path: Path, *, output_dir: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "missing_manifest", "path": output_relpath(path, output_dir)}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "read_failed",
            "path": output_relpath(path, output_dir),
            "error": f"{type(exc).__name__}: {exc}",
        }
    return probe_manifest_summary(payload, manifest_path=path, output_dir=output_dir)


def _texture_match_counts(per_location: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "texture_name_match_count": 0,
        "texture_path_basename_match_count": 0,
        "texture_path_full_delta_count": 0,
    }
    for item in per_location:
        mujoco = _dict(item.get("mujoco_target_contract"))
        isaac = _dict(item.get("isaac_target_contract"))
        mujoco_names = {Path(str(value)).name for value in mujoco.get("texture_files") or []}
        isaac_names = {Path(str(value)).name for value in isaac.get("texture_files") or []}
        if mujoco_names or isaac_names:
            counts["texture_name_match_count"] += int(mujoco_names == isaac_names)
        mujoco_paths = {str(value) for value in mujoco.get("texture_files") or []}
        isaac_paths = {str(value) for value in isaac.get("texture_files") or []}
        if mujoco_names and mujoco_names == isaac_names:
            counts["texture_path_basename_match_count"] += 1
            counts["texture_path_full_delta_count"] += int(mujoco_paths != isaac_paths)
    return counts


def _texture_colorspace_status(
    *,
    delta_counts: dict[str, int],
    missing_ref_count: int,
    texture_path_full_delta_count: int,
    target_location_count: int,
) -> str:
    high_priority_count = sum(
        count
        for name, count in delta_counts.items()
        if name in {"material_or_texture_name_delta", "missing_object_binding_evidence"}
    )
    if high_priority_count or missing_ref_count:
        return "target_material_texture_or_binding_gap"
    if texture_path_full_delta_count:
        return "texture_basenames_match_paths_or_colorspace_unverified"
    if delta_counts.get("material_texture_names_match") == target_location_count:
        return "material_texture_names_match_no_render_gap"
    return "material_texture_response_unverified"


def _target_material_counts(
    *,
    mujoco: dict[str, Any],
    isaac: dict[str, Any],
) -> dict[str, int | bool]:
    mujoco_visuals = [_dict(value) for value in mujoco.get("visuals") or []]
    isaac_bindings = [_dict(value) for value in isaac.get("bindings") or []]
    mujoco_texture_backed_visual_count = sum(
        1 for value in mujoco_visuals if value.get("texture") or value.get("texture_file")
    )
    mujoco_rgba_visual_count = sum(1 for value in mujoco_visuals if value.get("rgba"))
    isaac_diffuse_texture_binding_count = sum(
        1
        for value in isaac_bindings
        if value.get("has_diffuse_texture") or value.get("diffuse_texture_files")
    )
    isaac_diffuse_color_binding_count = sum(
        1 for value in isaac_bindings if value.get("diffuse_color")
    )
    return {
        "mujoco_texture_backed_visual_count": mujoco_texture_backed_visual_count,
        "mujoco_rgba_visual_count": mujoco_rgba_visual_count,
        "isaac_material_binding_count": int(isaac.get("material_binding_count") or 0),
        "isaac_diffuse_texture_binding_count": isaac_diffuse_texture_binding_count,
        "isaac_diffuse_color_binding_count": isaac_diffuse_color_binding_count,
        "texture_backing_mismatch": (
            mujoco_texture_backed_visual_count != isaac_diffuse_texture_binding_count
        ),
        "rgba_diffuse_color_mismatch": (
            mujoco_rgba_visual_count != isaac_diffuse_color_binding_count
        ),
    }


def _target_texture_files(
    *,
    mujoco: dict[str, Any],
    isaac: dict[str, Any],
) -> dict[str, Any]:
    mujoco_texture_files = [str(value) for value in mujoco.get("texture_files") or []]
    isaac_texture_files = [str(value) for value in isaac.get("texture_files") or []]
    return {
        "mujoco_texture_basenames": path_basenames(mujoco_texture_files),
        "isaac_texture_basenames": path_basenames(isaac_texture_files),
        "texture_full_path_delta": set(mujoco_texture_files) != set(isaac_texture_files),
    }


def _material_response_indicators(
    *,
    binding: dict[str, Any],
    delta: dict[str, Any],
    material_counts: dict[str, int | bool],
    texture_files: dict[str, Any],
    residual_class: str,
) -> list[str]:
    indicators: list[str] = []
    if delta.get("status") != "material_texture_names_match":
        indicators.append("material_texture_binding_gap")
    if int(binding.get("missing_referenced_asset_count") or 0) > 0:
        indicators.append("missing_referenced_assets")
    if (
        texture_files["mujoco_texture_basenames"] == texture_files["isaac_texture_basenames"]
        and texture_files["texture_full_path_delta"]
    ):
        indicators.append("texture_full_path_or_source_delta")
    if material_counts["texture_backing_mismatch"]:
        indicators.append("texture_backing_count_delta")
    if material_counts["rgba_diffuse_color_mismatch"]:
        indicators.append("rgba_vs_usd_diffuse_color_count_delta")
    if not indicators and residual_class not in {"", "low_residual"}:
        indicators.append("residual_after_material_texture_name_match")
    return indicators


def _material_response_status(indicators: list[str], residual_class: str) -> str:
    if "material_texture_binding_gap" in indicators or "missing_referenced_assets" in indicators:
        return "material_texture_binding_gap"
    if "texture_full_path_or_source_delta" in indicators:
        return "texture_path_or_colorspace_unverified"
    if (
        "texture_backing_count_delta" in indicators
        or "rgba_vs_usd_diffuse_color_count_delta" in indicators
    ):
        return "material_source_mix_delta"
    if residual_class not in {"", "low_residual"}:
        return "visual_residual_with_material_names_match"
    return "material_response_low_priority"


def _preview_surface_material_counts(per_location: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, Any] = {
        "isaac_material_binding_count": 0,
        "isaac_preview_surface_binding_count": 0,
        "isaac_diffuse_texture_binding_count": 0,
        "mujoco_visual_count": 0,
        "mujoco_rgba_visual_count": 0,
        "preview_input_statuses": [],
    }
    target_summaries = [preview_surface_target_summary(item) for item in per_location]
    counts["high_residual_targets"] = _high_residual_targets(target_summaries)
    for item in per_location:
        _add_isaac_preview_surface_counts(counts, _dict(item.get("isaac_target_contract")))
        _add_mujoco_visual_counts(counts, _dict(item.get("mujoco_target_contract")))
    return counts


def _add_isaac_preview_surface_counts(counts: dict[str, Any], isaac: dict[str, Any]) -> None:
    for binding in isaac.get("bindings") or []:
        if not isinstance(binding, dict):
            continue
        counts["isaac_material_binding_count"] += 1
        counts["isaac_preview_surface_binding_count"] += int(
            bool(binding.get("has_preview_surface"))
        )
        counts["isaac_diffuse_texture_binding_count"] += int(
            bool(binding.get("has_diffuse_texture"))
        )
        preview_inputs = _dict(binding.get("preview_surface_inputs"))
        counts["preview_input_statuses"].extend(
            key
            for key in ("roughness", "opacity", "metallic", "specular")
            if preview_inputs.get(key) is not None
        )


def _add_mujoco_visual_counts(counts: dict[str, Any], mujoco: dict[str, Any]) -> None:
    for visual in mujoco.get("visuals") or []:
        if isinstance(visual, dict):
            counts["mujoco_visual_count"] += 1
            counts["mujoco_rgba_visual_count"] += int(bool(visual.get("rgba")))


def _preview_surface_status(counts: dict[str, Any]) -> str:
    if counts["isaac_material_binding_count"] == 0 or counts["mujoco_visual_count"] == 0:
        return "preview_surface_material_evidence_missing"
    if counts["isaac_preview_surface_binding_count"] < counts["isaac_material_binding_count"]:
        return "usd_preview_surface_binding_gap"
    return "usd_preview_surface_vs_mujoco_material_model_delta"


def _preview_surface_next_action(probe_history: dict[str, Any]) -> str:
    if probe_history.get("improved_probe_count"):
        return (
            "A material-response probe improved FPV under the frozen head-camera "
            "contract, but keep it comparison-only until the same material conversion "
            "direction is validated across more targets, scenes, and seeds. Do not "
            "promote broad raw/colorspace or roughness edits from mixed probe history."
        )
    if probe_history.get("worsened_probe_count") and probe_history.get("neutral_probe_count"):
        return (
            "Do not promote global material-response edits yet: prior raw/colorspace or "
            "combined probes worsened FPV, while roughness-only evidence is below the "
            "improvement threshold. Continue with target-specific material probes or a "
            "broader corpus before changing defaults."
        )
    if probe_history.get("worsened_probe_count"):
        return (
            "Do not promote the already-worse material-response probe directly; split "
            "texture sourceColorSpace, PreviewSurface roughness, and target-specific "
            "sampler/material changes in comparison-only probes."
        )
    return (
        "Inspect USD PreviewSurface diffuse texture/color, roughness, opacity, and "
        "specular conversion against the MJCF material RGBA/texture inputs before "
        "changing the camera contract."
    )


def _high_residual_targets(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    targets = [
        item
        for item in items
        if item.get("fpv_residual_class") != "low_residual"
        or float(item.get("fpv_mean_abs_rgb") or 0.0) > 35.0
    ]
    targets.sort(key=lambda item: float(item.get("fpv_mean_abs_rgb") or 0.0), reverse=True)
    return targets


def _status_counts(values: Any) -> dict[str, int]:
    names = [str(value) for value in values if str(value)]
    return {name: names.count(name) for name in sorted(set(names))}


def _rounded_delta(left: float | None, right: float | None) -> float | None:
    return round(float(left - right), 4) if left is not None and right is not None else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _dict_path(value: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    current: Any = value
    for key in path:
        current = _dict(current).get(key)
    return _dict(current)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
