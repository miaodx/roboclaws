#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.household.camera_control import DEFAULT_SCENE_PROBE_COLOR_PROFILE

SCHEMA = "roboclaws_robot_camera_visual_parity_summary_v1"
ROBOT_CAMERA_MANIFEST_SCHEMA = "roboclaws_robot_camera_apple2apple_comparison_v1"
RAW_FPV_PASS_STATUS = "raw_fpv_agent_input_uses_head_camera"
HEAD_CAMERA_PASS_STATUS = "head_camera_geometry_aligned"
CAMERA_STATUS_ACCEPTED = {
    "fpv_contract_shared_with_static_head_camera_pitch_correction",
}
LENS_STATUS_ACCEPTED = {
    "fpv_lens_aligned",
}
POSE_STATUS_ACCEPTED = {
    "fpv_world_pose_aligned",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize existing MuJoCo-vs-Isaac robot-camera apple-to-apple reports into "
            "one visual-parity gate. This is read-only: it does not rerender either backend."
        )
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--baseline-manifest",
        type=Path,
        action="append",
        default=[],
        help="Post-FOV baseline robot-camera comparison manifest. Repeat for a corpus.",
    )
    parser.add_argument(
        "--probe-manifest",
        action="append",
        default=[],
        help=(
            "Probe robot-camera comparison manifest, optionally label=path. Repeat for "
            "RGB/tone, light/shadow, or material probes."
        ),
    )
    parser.add_argument(
        "--raw-fpv-run-result",
        type=Path,
        action="append",
        default=[],
        help="Optional cleanup run_result.json proving camera-raw/RAW_FPV agent-input lane.",
    )
    parser.add_argument(
        "--calibration-manifest",
        type=Path,
        action="append",
        default=[],
        help="Optional scene-camera calibration manifest with render-domain calibration evidence.",
    )
    parser.add_argument(
        "--required-scene-count",
        type=int,
        default=3,
        help="Minimum distinct scene signatures needed before considering visual parity broad.",
    )
    parser.add_argument(
        "--required-seed-count",
        type=int,
        default=2,
        help="Minimum distinct seeds needed before considering visual parity broad.",
    )
    args = parser.parse_args(argv)

    manifest = build_summary(
        output_dir=args.output_dir,
        baseline_manifest_paths=args.baseline_manifest,
        probe_specs=args.probe_manifest,
        raw_fpv_run_result_paths=args.raw_fpv_run_result,
        calibration_manifest_paths=args.calibration_manifest,
        required_scene_count=args.required_scene_count,
        required_seed_count=args.required_seed_count,
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"robot camera visual parity manifest: {args.output_dir / 'visual_parity_summary.json'}")
    print(f"robot camera visual parity report: {args.output_dir / 'report.html'}")
    return 0 if manifest["status"] in {"passed", "active"} else 2


def build_summary(
    *,
    output_dir: Path,
    baseline_manifest_paths: list[Path],
    probe_specs: list[str],
    raw_fpv_run_result_paths: list[Path] | None = None,
    calibration_manifest_paths: list[Path] | None = None,
    required_scene_count: int = 3,
    required_seed_count: int = 2,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    baselines = [_robot_camera_manifest_summary(path) for path in baseline_manifest_paths]
    probes = [_probe_summary(spec) for spec in probe_specs]
    raw_fpv_runs = [_raw_fpv_summary(path) for path in raw_fpv_run_result_paths or []]
    calibration = _calibration_summary(calibration_manifest_paths or [])
    render_domain_probe_matrix = _render_domain_probe_matrix_check(baselines, probes)
    checks = {
        "head_camera_contract": _head_camera_contract_check(baselines),
        "corpus_coverage": _corpus_coverage_check(
            baselines,
            required_scene_count=required_scene_count,
            required_seed_count=required_seed_count,
        ),
        "rgb_tone_cross_validation": _rgb_tone_cross_validation_check(baselines, probes),
        "render_domain_probe_matrix": render_domain_probe_matrix,
        "prepared_scale_square_default_gate": _prepared_scale_square_default_gate_check(
            render_domain_probe_matrix,
            required_scene_count=required_scene_count,
            required_seed_count=required_seed_count,
        ),
        "raw_fpv_input_lane": _raw_fpv_input_lane_check(raw_fpv_runs),
        "calibration_scene": calibration,
    }
    status = _overall_status(checks)
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": status,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "purpose": (
            "Read-only parity gate for MuJoCo and Isaac robot-camera visual evidence. "
            "FPV remains the robot-mounted head camera; chase is report evidence only."
        ),
        "policy": {
            "fpv": "robot-mounted head camera",
            "mujoco_fpv": "robot_0/head_camera",
            "isaac_fpv": "/World/robot_0/head_camera",
            "chase": "auxiliary report evidence only",
            "render_probes": "comparison_only_until_broader_corpus_and_calibration_pass",
        },
        "checks": checks,
        "baselines": baselines,
        "probes": probes,
        "raw_fpv_runs": raw_fpv_runs,
        "artifacts": {
            "manifest": "visual_parity_summary.json",
            "report": "report.html",
        },
        "recommended_next_action": _recommended_next_action(checks),
    }
    _write_json(output_dir / "visual_parity_summary.json", manifest)
    (output_dir / "report.html").write_text(_render_report(manifest), encoding="utf-8")
    return manifest


def _robot_camera_manifest_summary(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    summary = _dict(payload.get("summary"))
    scene = _dict(payload.get("scene"))
    camera = _dict(summary.get("camera_contract_diagnostics"))
    target_selection = _dict(summary.get("target_selection") or payload.get("target_selection"))
    render_checks = _dict(summary.get("render_domain_checks"))
    render = _dict(summary.get("render_contract_diagnostics"))
    fpv_lens = _dict(camera.get("fpv_lens_delta_summary"))
    fpv_pose = _dict(camera.get("fpv_world_pose_delta_summary"))
    return {
        "status": "loaded",
        "path": str(path),
        "schema": payload.get("schema"),
        "comparison_status": payload.get("status"),
        "scene": {
            "scene_source": scene.get("scene_source"),
            "scene_index": scene.get("scene_index"),
            "seed": scene.get("seed"),
            "generated_mess_count": scene.get("generated_mess_count"),
            "render_width": scene.get("render_width"),
            "render_height": scene.get("render_height"),
            "scene_usd_path": scene.get("scene_usd_path"),
        },
        "scene_signature": _scene_signature(scene),
        "location_count": summary.get("location_count"),
        "successful_location_count": summary.get("successful_location_count"),
        "fpv_mean_abs_rgb_avg": summary.get("fpv_mean_abs_rgb_avg"),
        "chase_mean_abs_rgb_avg": summary.get("chase_mean_abs_rgb_avg"),
        "camera_contract_status": camera.get("status"),
        "fpv_head_camera_contract_count": camera.get("fpv_head_camera_contract_count"),
        "fpv_lens_status": fpv_lens.get("status"),
        "fpv_world_pose_status": fpv_pose.get("status"),
        "render_domain_status": render_checks.get("status"),
        "render_contract_status": render.get("status"),
        "target_selection": {
            "status": target_selection.get("status"),
            "selected_count": target_selection.get("selected_count"),
            "dropped_unbound_target_count": target_selection.get("dropped_unbound_target_count"),
        },
        "render_domain_checks": _render_checks_by_id(render_checks),
    }


def _probe_summary(spec: str) -> dict[str, Any]:
    label, path = _parse_probe_spec(spec)
    summary = _robot_camera_manifest_summary(path)
    summary["label"] = label
    summary["probe_kind"] = _infer_probe_kind(summary)
    summary["rgb_gain_source"] = _rgb_gain_source(path)
    return summary


def _head_camera_contract_check(baselines: list[dict[str, Any]]) -> dict[str, Any]:
    failures = []
    for baseline in baselines:
        successful_locations = int(baseline.get("successful_location_count") or 0)
        head_count = int(baseline.get("fpv_head_camera_contract_count") or 0)
        if baseline.get("schema") != ROBOT_CAMERA_MANIFEST_SCHEMA:
            failures.append({"path": baseline.get("path"), "reason": "wrong_schema"})
        if baseline.get("comparison_status") != "success":
            failures.append({"path": baseline.get("path"), "reason": "comparison_not_success"})
        if baseline.get("camera_contract_status") not in CAMERA_STATUS_ACCEPTED:
            failures.append(
                {
                    "path": baseline.get("path"),
                    "reason": "camera_contract_status",
                    "value": baseline.get("camera_contract_status"),
                }
            )
        if successful_locations <= 0 or head_count != successful_locations:
            failures.append(
                {
                    "path": baseline.get("path"),
                    "reason": "fpv_head_camera_count",
                    "head_count": head_count,
                    "successful_locations": successful_locations,
                }
            )
        if baseline.get("fpv_lens_status") not in LENS_STATUS_ACCEPTED:
            failures.append(
                {
                    "path": baseline.get("path"),
                    "reason": "fpv_lens_status",
                    "value": baseline.get("fpv_lens_status"),
                }
            )
        if baseline.get("fpv_world_pose_status") not in POSE_STATUS_ACCEPTED:
            failures.append(
                {
                    "path": baseline.get("path"),
                    "reason": "fpv_world_pose_status",
                    "value": baseline.get("fpv_world_pose_status"),
                }
            )
    return {
        "status": HEAD_CAMERA_PASS_STATUS if baselines and not failures else "not_proven",
        "baseline_count": len(baselines),
        "failure_count": len(failures),
        "failures": failures,
        "interpretation": (
            "Camera geometry is treated as frozen only when every baseline uses the "
            "robot-mounted head camera, has aligned lens metadata, and has aligned FPV "
            "world pose."
        ),
    }


def _corpus_coverage_check(
    baselines: list[dict[str, Any]],
    *,
    required_scene_count: int,
    required_seed_count: int,
) -> dict[str, Any]:
    scenes = sorted({str(item.get("scene_signature") or "") for item in baselines})
    seeds = sorted({_dict(item.get("scene")).get("seed") for item in baselines})
    total_locations = sum(int(item.get("successful_location_count") or 0) for item in baselines)
    pass_status = (
        len(scenes) >= required_scene_count
        and len(seeds) >= required_seed_count
        and total_locations >= required_scene_count * 4
    )
    return {
        "status": "broad_corpus_ready" if pass_status else "needs_broader_corpus",
        "baseline_count": len(baselines),
        "scene_signature_count": len(scenes),
        "scene_signatures": scenes,
        "seed_count": len([seed for seed in seeds if seed is not None]),
        "seeds": seeds,
        "successful_location_count": total_locations,
        "required_scene_count": required_scene_count,
        "required_seed_count": required_seed_count,
        "interpretation": (
            "Current one-day visual probes are useful for root-cause direction, but renderer "
            "defaults need held-out scene and seed coverage before promotion."
        ),
    }


def _rgb_tone_cross_validation_check(
    baselines: list[dict[str, Any]],
    probes: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_by_scene = {str(item.get("scene_signature")): item for item in baselines}
    evaluated = []
    for probe in probes:
        if probe.get("probe_kind") != "tone_color":
            continue
        baseline = baseline_by_scene.get(str(probe.get("scene_signature")))
        delta = _delta_vs_baseline(baseline, probe)
        source = _dict(probe.get("rgb_gain_source"))
        source_scene = _source_scene_signature(source)
        source_scene_key = _source_scene_key(source)
        probe_scene_key = _scene_key(_dict(probe.get("scene")))
        held_out_scene = bool(source_scene_key and source_scene_key != probe_scene_key)
        held_out_slice = bool(source_scene and source_scene != probe.get("scene_signature"))
        evaluated.append(
            {
                "label": probe.get("label"),
                "path": probe.get("path"),
                "scene_signature": probe.get("scene_signature"),
                "source_manifest": source.get("manifest_path"),
                "source_scene_signature": source_scene,
                "held_out_scene": held_out_scene,
                "held_out_slice": held_out_slice,
                "backend_rgb_gain": source.get("backend_rgb_gain"),
                "fpv_delta": delta.get("fpv_delta"),
                "chase_delta": delta.get("chase_delta"),
                "fpv_improved": delta.get("fpv_improved"),
                "comparable": delta.get("comparable"),
            }
        )
    comparable = [item for item in evaluated if item.get("comparable")]
    improved = [item for item in comparable if item.get("fpv_improved")]
    held_out_improved = [item for item in improved if item.get("held_out_scene")]
    if held_out_improved:
        status = "comparison_only_rgb_tone_positive"
    elif improved:
        status = "same_slice_rgb_tone_positive"
    elif comparable:
        status = "rgb_tone_not_positive"
    else:
        status = "rgb_tone_not_evaluated"
    return {
        "status": status,
        "comparison_only": True,
        "evaluated_probe_count": len(evaluated),
        "comparable_probe_count": len(comparable),
        "improved_probe_count": len(improved),
        "held_out_improved_probe_count": len(held_out_improved),
        "probes": evaluated,
        "interpretation": (
            "RGB/tone gain is evidence for render-domain mismatch only. It can be a default "
            "renderer setting only after broad corpus and calibration checks also pass."
        ),
    }


def _render_domain_probe_matrix_check(
    baselines: list[dict[str, Any]],
    probes: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_by_scene = {str(item.get("scene_signature")): item for item in baselines}
    matrix: dict[str, list[dict[str, Any]]] = {}
    for probe in probes:
        kind = str(probe.get("probe_kind") or "unknown")
        baseline = baseline_by_scene.get(str(probe.get("scene_signature")))
        delta = _delta_vs_baseline(baseline, probe)
        matrix.setdefault(kind, []).append(
            {
                "label": probe.get("label"),
                "path": probe.get("path"),
                "scene_signature": probe.get("scene_signature"),
                "fpv_delta": delta.get("fpv_delta"),
                "chase_delta": delta.get("chase_delta"),
                "fpv_improved": delta.get("fpv_improved"),
                "fpv_worse": delta.get("fpv_worse"),
                "comparable": delta.get("comparable"),
            }
        )
    status_by_kind = {
        kind: _probe_kind_status(rows)
        for kind, rows in sorted(matrix.items())
        if kind != "tone_color"
    }
    active_baseline_statuses = sorted(
        {
            str(item.get("render_contract_status") or item.get("render_domain_status") or "")
            for item in baselines
            if item.get("render_contract_status") or item.get("render_domain_status")
        }
    )
    return {
        "status": "render_domain_delta_active",
        "baseline_render_statuses": active_baseline_statuses,
        "probe_status_by_kind": status_by_kind,
        "probe_matrix": matrix,
        "interpretation": (
            "Light/shadow, texture, and PreviewSurface probes are comparison-only. Simple "
            "switches should not be promoted when they are neutral or worse for FPV."
        ),
    }


def _prepared_scale_square_default_gate_check(
    render_domain_probe_matrix: dict[str, Any],
    *,
    required_scene_count: int,
    required_seed_count: int,
    chase_regression_tolerance: float = 1.0,
) -> dict[str, Any]:
    matrix = _dict(render_domain_probe_matrix.get("probe_matrix"))
    material_rows = _list_dicts(matrix.get("material_response"))
    prepared_rows = [
        row
        for row in material_rows
        if "prepared_scale_square_gate" in str(row.get("label") or "").lower()
    ]
    comparable = [row for row in prepared_rows if row.get("comparable")]
    scene_signatures = sorted({str(row.get("scene_signature") or "") for row in comparable})
    seeds = sorted(
        {
            seed
            for seed in (
                _seed_from_scene_signature(str(row.get("scene_signature") or ""))
                for row in comparable
            )
            if seed is not None
        }
    )
    fpv_improved = [row for row in comparable if row.get("fpv_improved")]
    fpv_worse = [row for row in comparable if row.get("fpv_worse")]
    chase_regressions = [
        row
        for row in comparable
        if _float_or_none(row.get("chase_delta")) is not None
        and _float_or_none(row.get("chase_delta")) > chase_regression_tolerance
    ]
    baseline_render_statuses = [
        status
        for status in _list_strings(render_domain_probe_matrix.get("baseline_render_statuses"))
        if status and status != "render_domain_delta_resolved"
    ]
    blockers: list[dict[str, Any]] = []
    if not prepared_rows:
        blockers.append({"reason": "no_prepared_scale_square_probe"})
    if len(comparable) != len(prepared_rows):
        blockers.append(
            {
                "reason": "not_all_prepared_probes_comparable",
                "prepared_probe_count": len(prepared_rows),
                "comparable_probe_count": len(comparable),
            }
        )
    if len(scene_signatures) < required_scene_count:
        blockers.append(
            {
                "reason": "needs_broader_scene_corpus",
                "scene_signature_count": len(scene_signatures),
                "required_scene_count": required_scene_count,
            }
        )
    if len(seeds) < required_seed_count:
        blockers.append(
            {
                "reason": "needs_broader_seed_corpus",
                "seed_count": len(seeds),
                "required_seed_count": required_seed_count,
            }
        )
    if len(fpv_improved) != len(comparable):
        blockers.append(
            {
                "reason": "not_all_comparable_probes_improve_fpv",
                "fpv_improved_count": len(fpv_improved),
                "comparable_probe_count": len(comparable),
            }
        )
    if fpv_worse:
        blockers.append(
            {
                "reason": "fpv_regression",
                "labels": [row.get("label") for row in fpv_worse],
            }
        )
    if chase_regressions:
        blockers.append(
            {
                "reason": "chase_regression",
                "tolerance": chase_regression_tolerance,
                "labels": [row.get("label") for row in chase_regressions],
            }
        )
    if baseline_render_statuses:
        blockers.append(
            {
                "reason": "render_domain_residuals_active",
                "baseline_render_statuses": baseline_render_statuses,
            }
        )
    if not prepared_rows:
        status = "not_evaluated"
    elif fpv_worse:
        status = "do_not_promote"
    elif comparable and len(fpv_improved) == len(comparable) and not blockers:
        status = "prepared_scale_square_default_ready"
    elif comparable and fpv_improved:
        status = "comparison_only_not_default"
    else:
        status = "neutral_do_not_promote"
    return {
        "status": status,
        "comparison_only": status != "prepared_scale_square_default_ready",
        "default_candidate": status == "prepared_scale_square_default_ready",
        "prepared_probe_count": len(prepared_rows),
        "comparable_probe_count": len(comparable),
        "fpv_improved_count": len(fpv_improved),
        "fpv_worse_count": len(fpv_worse),
        "chase_regression_count": len(chase_regressions),
        "scene_signature_count": len(scene_signatures),
        "scene_signatures": scene_signatures,
        "seed_count": len(seeds),
        "seeds": seeds,
        "required_scene_count": required_scene_count,
        "required_seed_count": required_seed_count,
        "chase_regression_tolerance": chase_regression_tolerance,
        "blockers": blockers,
        "probes": [
            {
                "label": row.get("label"),
                "path": row.get("path"),
                "scene_signature": row.get("scene_signature"),
                "fpv_delta": row.get("fpv_delta"),
                "chase_delta": row.get("chase_delta"),
                "fpv_improved": row.get("fpv_improved"),
                "comparable": row.get("comparable"),
            }
            for row in prepared_rows
        ],
        "recommended_next_action": (
            "Keep prepared scale-square comparison-only until FPV gain, chase "
            "non-regression tolerance, and remaining render-domain residual gates pass."
            if status != "prepared_scale_square_default_ready"
            else "Prepared scale-square is ready for default-rendering review."
        ),
        "interpretation": (
            "This gate decides whether the opt-in prepared USD texture scale/fallback "
            "squaring evidence is strong enough to become default rendering behavior."
        ),
    }


def _raw_fpv_summary(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    camera = _dict(payload.get("robot_view_camera_control"))
    agent_view = _dict(payload.get("agent_view"))
    raw_observations = _list_dicts(
        payload.get("raw_fpv_observations") or agent_view.get("raw_fpv_observations")
    )
    return {
        "status": "loaded",
        "path": str(path),
        "backend": payload.get("backend"),
        "cleanup_profile": payload.get("cleanup_profile"),
        "perception_mode": payload.get("perception_mode") or agent_view.get("perception_mode"),
        "raw_fpv_observation_count": len(raw_observations),
        "model_declared_observation_count": len(
            _list_dicts(payload.get("model_declared_observations"))
        ),
        "head_camera_fpv": bool(camera.get("head_camera_fpv")),
        "camera_status": camera.get("status"),
        "head_camera_contract_count": camera.get("head_camera_contract_count"),
        "step_count": camera.get("step_count"),
    }


def _raw_fpv_input_lane_check(raw_fpv_runs: list[dict[str, Any]]) -> dict[str, Any]:
    passing = [
        item
        for item in raw_fpv_runs
        if item.get("cleanup_profile") == "camera-raw"
        and item.get("perception_mode") == "raw_fpv_only"
        and item.get("head_camera_fpv") is True
        and int(item.get("raw_fpv_observation_count") or 0) > 0
    ]
    return {
        "status": RAW_FPV_PASS_STATUS if passing else "raw_fpv_input_lane_not_proven",
        "run_count": len(raw_fpv_runs),
        "passing_run_count": len(passing),
        "runs": raw_fpv_runs,
        "interpretation": (
            "The RAW_FPV lane is the agent-input proof. World-label apple-to-apple images "
            "remain report evidence only."
        ),
    }


def _calibration_summary(calibration_manifest_paths: list[Path]) -> dict[str, Any]:
    default_source = str(
        DEFAULT_SCENE_PROBE_COLOR_PROFILE.get("backend_luminance_gain_source") or ""
    )
    candidates = []
    for path in calibration_manifest_paths:
        candidates.append(_calibration_manifest_summary(path))
    default_source_exists = bool(default_source and Path(default_source).is_file())
    usable = [item for item in candidates if item.get("render_domain_calibration_status")]
    if usable:
        status = "calibration_scene_evidence_loaded"
    elif default_source and not default_source_exists:
        status = "default_calibration_artifact_missing"
    else:
        status = "calibration_scene_not_provided"
    return {
        "status": status,
        "default_luminance_gain_source": default_source,
        "default_luminance_gain_source_exists": default_source_exists,
        "provided_manifest_count": len(calibration_manifest_paths),
        "usable_manifest_count": len(usable),
        "manifests": candidates,
        "interpretation": (
            "A real calibration scene/report is needed before turning comparison-only "
            "RGB/luminance gain into default cleanup rendering behavior."
        ),
    }


def _calibration_manifest_summary(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"status": "missing", "path": str(path)}
    payload = _read_json(path)
    calibration = _find_first_dict(payload, "render_domain_calibration") or {}
    return {
        "status": "loaded",
        "path": str(path),
        "schema": payload.get("schema"),
        "comparison_status": payload.get("status"),
        "render_domain_calibration_status": calibration.get("status"),
        "global_isaac_luminance_gain": calibration.get("global_isaac_luminance_gain"),
        "mean_abs_calibrated_luminance_residual": calibration.get(
            "mean_abs_calibrated_luminance_residual"
        ),
    }


def _overall_status(checks: dict[str, dict[str, Any]]) -> str:
    required_pass = {
        "head_camera_contract": HEAD_CAMERA_PASS_STATUS,
        "raw_fpv_input_lane": RAW_FPV_PASS_STATUS,
        "corpus_coverage": "broad_corpus_ready",
        "calibration_scene": "calibration_scene_evidence_loaded",
    }
    foundational_checks_pass = all(
        checks[key].get("status") == status for key, status in required_pass.items()
    )
    render_domain_resolved = checks["render_domain_probe_matrix"].get("status") == (
        "render_domain_delta_resolved"
    )
    prepared_scale_ready = checks.get("prepared_scale_square_default_gate", {}).get("status") == (
        "prepared_scale_square_default_ready"
    )
    rgb_ready_for_default = checks["rgb_tone_cross_validation"].get("status") == (
        "default_rgb_tone_ready"
    )
    if (
        foundational_checks_pass
        and render_domain_resolved
        and prepared_scale_ready
        and rgb_ready_for_default
    ):
        return "passed"
    if checks["head_camera_contract"].get("status") == HEAD_CAMERA_PASS_STATUS:
        return "active"
    return "needs_camera_work"


def _recommended_next_action(checks: dict[str, dict[str, Any]]) -> str:
    if checks["head_camera_contract"].get("status") != HEAD_CAMERA_PASS_STATUS:
        return "Fix the head-camera FPV pose/lens contract before any render tuning."
    if checks["corpus_coverage"].get("status") != "broad_corpus_ready":
        return (
            "Run additional bound-target post-FOV apple-to-apple baselines across held-out "
            "scene indices and seeds, then evaluate the existing RGB/tone profiles there."
        )
    if checks["calibration_scene"].get("status") != "calibration_scene_evidence_loaded":
        return (
            "Generate a root-visible calibration-scene report before promoting any "
            "RGB/luminance gain to default rendering."
        )
    prepared_gate = checks.get("prepared_scale_square_default_gate", {})
    if prepared_gate.get("status") == "comparison_only_not_default":
        return str(prepared_gate.get("recommended_next_action") or "")
    if checks["rgb_tone_cross_validation"].get("comparison_only") is True:
        return (
            "Keep RGB/tone as comparison-only and review remaining render-domain residuals "
            "before changing default cleanup rendering."
        )
    return "Review remaining render-domain residuals before changing default cleanup rendering."


def _infer_probe_kind(summary: dict[str, Any]) -> str:
    label = str(summary.get("label") or "").lower()
    path_text = str(summary.get("path") or "").lower()
    evidence = f"{label} {path_text}"
    if _rgb_gain_source(Path(str(summary.get("path") or ""))).get("backend_rgb_gain"):
        return "tone_color"
    if "rgb_gain" in evidence or "val0_rgb" in evidence or "self_rgb" in evidence:
        return "tone_color"
    if (
        "pillow" in evidence
        or "roughness" in evidence
        or "material" in evidence
        or "texture" in evidence
        or "srgb" in evidence
        or "scale_square" in evidence
        or "lightwood" in evidence
    ):
        return "material_response"
    if (
        "no_dome" in evidence
        or "no_shadow" in evidence
        or "light_shadow" in evidence
        or "lighting" in evidence
    ):
        return "light_shadow"
    return "unknown"


def _delta_vs_baseline(
    baseline: dict[str, Any] | None,
    probe: dict[str, Any],
) -> dict[str, Any]:
    if baseline is None:
        return {"comparable": False, "reason": "missing_matching_baseline"}
    if baseline.get("camera_contract_status") != probe.get("camera_contract_status"):
        return {"comparable": False, "reason": "camera_contract_mismatch"}
    fpv_delta = _delta(probe.get("fpv_mean_abs_rgb_avg"), baseline.get("fpv_mean_abs_rgb_avg"))
    chase_delta = _delta(
        probe.get("chase_mean_abs_rgb_avg"),
        baseline.get("chase_mean_abs_rgb_avg"),
    )
    return {
        "comparable": True,
        "fpv_delta": fpv_delta,
        "chase_delta": chase_delta,
        "fpv_improved": fpv_delta is not None and fpv_delta < -1.0,
        "fpv_worse": fpv_delta is not None and fpv_delta > 1.0,
        "chase_improved": chase_delta is not None and chase_delta < -1.0,
        "chase_worse": chase_delta is not None and chase_delta > 1.0,
    }


def _probe_kind_status(rows: list[dict[str, Any]]) -> str:
    comparable = [row for row in rows if row.get("comparable")]
    if not comparable:
        return "not_evaluated"
    if any(row.get("fpv_improved") for row in comparable):
        return "has_fpv_gain_comparison_only"
    if any(row.get("fpv_worse") for row in comparable):
        return "worse_or_mixed_do_not_promote"
    return "neutral_do_not_promote"


def _rgb_gain_source(manifest_path: Path) -> dict[str, Any]:
    state_path = manifest_path.parent / "isaac_state.json"
    if not state_path.is_file():
        return {}
    state = _read_json(state_path)
    override = _dict(state.get("robot_view_color_profile_override"))
    profile = _dict(state.get("robot_view_color_profile"))
    gain = _dict(override.get("backend_rgb_gain")) or _dict(profile.get("backend_rgb_gain"))
    source = str(
        override.get("backend_rgb_gain_source") or profile.get("backend_rgb_gain_source") or ""
    )
    manifest_source = source.split(" global least-squares ", 1)[0] if source else ""
    source_summary = {}
    if manifest_source and Path(manifest_source).is_file():
        source_summary = _robot_camera_manifest_summary(Path(manifest_source))
    return {
        "backend_rgb_gain": gain,
        "source": source,
        "manifest_path": manifest_source,
        "source_manifest_loaded": bool(source_summary),
        "source_scene": source_summary.get("scene"),
        "source_scene_signature": source_summary.get("scene_signature"),
    }


def _source_scene_signature(source: dict[str, Any]) -> str:
    if source.get("source_scene_signature"):
        return str(source["source_scene_signature"])
    scene = _dict(source.get("source_scene"))
    return _scene_signature(scene) if scene else ""


def _source_scene_key(source: dict[str, Any]) -> str:
    scene = _dict(source.get("source_scene"))
    return _scene_key(scene) if scene else ""


def _scene_key(scene: dict[str, Any]) -> str:
    return "|".join(str(scene.get(key)) for key in ("scene_source", "scene_index"))


def _scene_signature(scene: dict[str, Any]) -> str:
    return "|".join(
        str(scene.get(key))
        for key in (
            "scene_source",
            "scene_index",
            "seed",
            "generated_mess_count",
            "render_width",
            "render_height",
        )
    )


def _seed_from_scene_signature(scene_signature: str) -> int | None:
    parts = scene_signature.split("|")
    if len(parts) < 3:
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


def _render_checks_by_id(render_domain_checks: dict[str, Any]) -> dict[str, dict[str, Any]]:
    checks = {}
    for item in render_domain_checks.get("checks") or []:
        if isinstance(item, dict) and item.get("check_id"):
            probe_history = _dict(item.get("probe_history"))
            checks[str(item["check_id"])] = {
                "status": item.get("status"),
                "probe_history_status": probe_history.get("status"),
                "probe_count": probe_history.get("probe_count"),
                "comparable_probe_count": probe_history.get("comparable_probe_count"),
                "improved_probe_count": probe_history.get("improved_probe_count"),
                "worsened_probe_count": probe_history.get("worsened_probe_count"),
                "neutral_probe_count": probe_history.get("neutral_probe_count"),
            }
    return checks


def _parse_probe_spec(spec: str) -> tuple[str, Path]:
    if "=" in spec:
        label, raw_path = spec.split("=", 1)
        return label.strip() or Path(raw_path).parent.name, Path(raw_path)
    path = Path(spec)
    return path.parent.name, path


def _delta(left: Any, right: Any) -> float | None:
    try:
        return round(float(left) - float(right), 4)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _find_first_dict(payload: Any, key: str) -> dict[str, Any] | None:
    if isinstance(payload, dict):
        for item_key, value in payload.items():
            if item_key == key and isinstance(value, dict):
                return value
            found = _find_first_dict(value, key)
            if found is not None:
                return found
    if isinstance(payload, list):
        for value in payload:
            found = _find_first_dict(value, key)
            if found is not None:
                return found
    return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _list_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _render_report(manifest: dict[str, Any]) -> str:
    checks = _dict(manifest.get("checks"))
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(check_id)}</td>"
        f"<td>{html.escape(str(_dict(check).get('status') or ''))}</td>"
        f"<td>{html.escape(str(_dict(check).get('interpretation') or ''))}</td>"
        "</tr>"
        for check_id, check in checks.items()
    )
    baseline_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('path') or ''))}</td>"
        f"<td>{html.escape(str(item.get('scene_signature') or ''))}</td>"
        f"<td>{html.escape(str(item.get('fpv_mean_abs_rgb_avg') or ''))}</td>"
        f"<td>{html.escape(str(item.get('chase_mean_abs_rgb_avg') or ''))}</td>"
        "</tr>"
        for item in manifest.get("baselines") or []
        if isinstance(item, dict)
    )
    probe_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label') or ''))}</td>"
        f"<td>{html.escape(str(item.get('probe_kind') or ''))}</td>"
        f"<td>{html.escape(str(item.get('scene_signature') or ''))}</td>"
        f"<td>{html.escape(str(item.get('fpv_mean_abs_rgb_avg') or ''))}</td>"
        "</tr>"
        for item in manifest.get("probes") or []
        if isinstance(item, dict)
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Robot Camera Visual Parity</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; line-height: 1.45; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f3f3; }}
    code {{ background: #f6f6f6; padding: 1px 4px; }}
  </style>
</head>
<body>
  <h1>Robot Camera Visual Parity</h1>
  <p>Status: <code>{html.escape(str(manifest.get("status")))}</code></p>
  <p>{html.escape(str(manifest.get("recommended_next_action") or ""))}</p>
  <h2>Checks</h2>
  <table><thead><tr><th>Check</th><th>Status</th><th>Interpretation</th></tr></thead><tbody>{rows}</tbody></table>
  <h2>Baselines</h2>
  <table><thead><tr><th>Manifest</th><th>Scene</th><th>FPV</th><th>Chase</th></tr></thead><tbody>{baseline_rows}</tbody></table>
  <h2>Probes</h2>
  <table><thead><tr><th>Label</th><th>Kind</th><th>Scene</th><th>FPV</th></tr></thead><tbody>{probe_rows}</tbody></table>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
