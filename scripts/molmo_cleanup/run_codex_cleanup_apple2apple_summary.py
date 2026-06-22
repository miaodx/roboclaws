#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

SCHEMA = "roboclaws_codex_cleanup_apple2apple_comparison_v1"
MUJOCO_LANE_ID = "molmospaces-mujoco-codex"
ISAAC_LANE_ID = "isaaclab-rby1m-usd-codex"
ROBOT_VIEW_KEYS = ("fpv", "chase")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize two existing Codex household-cleanup runs into one "
            "MuJoCo-vs-Isaac apple-to-apple report."
        )
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mujoco-run-result", type=Path, required=True)
    parser.add_argument("--isaac-run-result", type=Path, required=True)
    parser.add_argument("--mujoco-lane-id", default=MUJOCO_LANE_ID)
    parser.add_argument("--isaac-lane-id", default=ISAAC_LANE_ID)
    args = parser.parse_args(argv)

    manifest = build_summary(
        output_dir=args.output_dir,
        lane_paths={
            args.mujoco_lane_id: args.mujoco_run_result,
            args.isaac_lane_id: args.isaac_run_result,
        },
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"cleanup apple2apple manifest: {args.output_dir / 'comparison_manifest.json'}")
    print(f"cleanup apple2apple report: {args.output_dir / 'report.html'}")
    return 0


def build_summary(*, output_dir: Path, lane_paths: dict[str, Path]) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    lanes = {
        lane_id: _lane_summary(lane_id=lane_id, run_result_path=run_result, output_dir=output_dir)
        for lane_id, run_result in lane_paths.items()
    }
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "success",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "purpose": (
            "Current-state apple-to-apple summary for Codex household cleanup on "
            "MuJoCo and Isaac. This report reads existing run artifacts; it does "
            "not rerun Codex, simulation, or scoring."
        ),
        "comparison": _comparison_summary(lanes),
        "lanes": lanes,
        "artifacts": {
            "comparison_manifest": "comparison_manifest.json",
            "report": "report.html",
        },
    }
    _write_json(output_dir / "comparison_manifest.json", manifest)
    (output_dir / "report.html").write_text(_render_report(manifest), encoding="utf-8")
    return manifest


def _lane_summary(*, lane_id: str, run_result_path: Path, output_dir: Path) -> dict[str, Any]:
    run_result_path = run_result_path.resolve()
    run_dir = run_result_path.parent
    run_result = _read_json(run_result_path)
    score = dict(run_result.get("score") or {})
    private_evaluation = dict(run_result.get("private_evaluation") or {})
    agent_view = _agent_view(run_result, run_dir)
    robot_steps = _list_dicts(run_result.get("robot_view_steps"))
    camera_summary = dict(run_result.get("robot_view_camera_control") or {})
    first_contract = _first_robot_view_contract(robot_steps)
    robot_asset = dict(first_contract.get("robot_asset") or {})
    artifacts = _artifact_links(run_result, run_dir=run_dir, output_dir=output_dir)
    return {
        "lane_id": lane_id,
        "backend": run_result.get("backend"),
        "policy": run_result.get("policy"),
        "completion_status": run_result.get("completion_status") or score.get("completion_status"),
        "scenario_id": run_result.get("scenario_id"),
        "scene": _scene_signature(run_result),
        "seed": run_result.get("seed"),
        "map_mode": run_result.get("map_mode"),
        "static_fixture_projection_mode": run_result.get("static_fixture_projection_mode"),
        "perception_mode": run_result.get("perception_mode"),
        "visual_grounding_pipeline_id": run_result.get("visual_grounding_pipeline_id"),
        "requested_generated_mess_count": _first_present(
            run_result.get("requested_generated_mess_count"),
            private_evaluation.get("requested_generated_mess_count"),
        ),
        "generated_mess_count": _first_present(
            run_result.get("generated_mess_count"),
            private_evaluation.get("generated_mess_count"),
        ),
        "score": _score_summary(score),
        "cleanup_target_signature": _cleanup_target_signature(score),
        "agent_diagnostics": run_result.get("agent_diagnostics") or {},
        "worklist": _worklist_summary(agent_view),
        "robot_view_camera_control": camera_summary,
        "robot_view_contract": _robot_view_contract_summary(first_contract),
        "robot_import": _robot_import_summary(robot_asset),
        "terminate_reason": run_result.get("terminate_reason"),
        "codex_last_message": _read_text_if_exists(run_dir / "codex-last-message.md"),
        "artifacts": artifacts,
        "robot_view_samples": _robot_view_samples(
            robot_steps,
            run_dir=run_dir,
            output_dir=output_dir,
        ),
    }


def _comparison_summary(lanes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    lane_values = list(lanes.values())
    head_camera_fpv_values = [
        bool((lane.get("robot_view_camera_control") or {}).get("head_camera_fpv"))
        for lane in lane_values
    ]
    axes = {
        "seed": _same_value(lane_values, "seed"),
        "policy": _same_value(lane_values, "policy"),
        "map_mode": _same_value(lane_values, "map_mode"),
        "requested_generated_mess_count": _same_value(
            lane_values,
            "requested_generated_mess_count",
        ),
        "generated_mess_count": _same_value(lane_values, "generated_mess_count"),
        "scene_index": _same_nested_value(lane_values, ("scene", "scene_index")),
        "cleanup_target_signature": _same_value(lane_values, "cleanup_target_signature"),
        "head_camera_fpv": {
            "matches": all(head_camera_fpv_values),
            "values": head_camera_fpv_values,
        },
    }
    non_comparable_axes = [
        axis
        for axis, value in axes.items()
        if axis not in {"head_camera_fpv"} and value.get("matches") is False
    ]
    strict_scene_identical = not non_comparable_axes
    return {
        "strict_scene_identical": strict_scene_identical,
        "status_label": "strict" if strict_scene_identical else "current_state_not_strict",
        "axis_checks": axes,
        "non_comparable_axes": non_comparable_axes,
        "headline": _headline(lanes),
        "interpretation_notes": _interpretation_notes(lanes, non_comparable_axes),
    }


def _headline(lanes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        lane_id: {
            "completion_status": lane.get("completion_status"),
            "restored": _restored_text(lane),
            "mess_restoration_rate": (lane.get("score") or {}).get("mess_restoration_rate"),
            "sweep_coverage_rate": (lane.get("score") or {}).get("sweep_coverage_rate"),
        }
        for lane_id, lane in lanes.items()
    }


def _interpretation_notes(
    lanes: dict[str, dict[str, Any]],
    non_comparable_axes: list[str],
) -> list[str]:
    notes: list[str] = []
    if all(
        bool((lane.get("robot_view_camera_control") or {}).get("head_camera_fpv"))
        for lane in lanes.values()
    ):
        notes.append(
            "Both lanes report agent-facing FPV as robot-mounted head-camera output. "
            "Chase/map/verify views are report evidence only."
        )
    if non_comparable_axes:
        notes.append(
            "This artifact is a current-state comparison, not a fully strict scene-identical "
            f"comparison, because these axes differ: {', '.join(non_comparable_axes)}."
        )
    for lane_id, lane in lanes.items():
        if lane.get("completion_status") == "failed":
            reason = str(lane.get("terminate_reason") or "").strip()
            if reason:
                notes.append(f"{lane_id} failed with terminate_reason: {reason}")
    return notes


def _score_summary(score: dict[str, Any]) -> dict[str, Any]:
    object_results = _list_dicts(score.get("object_results"))
    total_targets = _first_present(score.get("total_targets"), len(object_results))
    return {
        "status": score.get("status"),
        "completion_status": score.get("completion_status"),
        "restored_count": score.get("restored_count"),
        "total_targets": total_targets,
        "restored_text": f"{score.get('restored_count', 0)}/{total_targets}",
        "mess_restoration_rate": score.get("mess_restoration_rate"),
        "sweep_coverage_rate": score.get("sweep_coverage_rate"),
        "disturbance_count": score.get("disturbance_count"),
        "missed_object_ids": list(score.get("missed_object_ids") or []),
        "object_results": [_object_result_summary(item) for item in object_results],
        "semantic_acceptability": score.get("semantic_acceptability") or {},
    }


def _cleanup_target_signature(score: dict[str, Any]) -> list[dict[str, Any]]:
    signature = []
    for item in _list_dicts(score.get("object_results")):
        signature.append(
            {
                "object_id": item.get("object_id"),
                "object_category": item.get("object_category"),
            }
        )
    return sorted(
        signature,
        key=lambda item: (str(item.get("object_id")), str(item.get("object_category"))),
    )


def _object_result_summary(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_id": item.get("object_id"),
        "object_category": item.get("object_category"),
        "restored": item.get("restored"),
        "actual_location_id": item.get("actual_location_id"),
        "actual_receptacle_category": item.get("actual_receptacle_category"),
        "semantic_acceptability": item.get("semantic_acceptability"),
        "semantic_reason": item.get("semantic_reason"),
        "exact_private_match": item.get("exact_private_match"),
    }


def _worklist_summary(agent_view: dict[str, Any]) -> dict[str, Any]:
    worklist = dict(agent_view.get("cleanup_worklist") or {})
    objects = _list_dicts(worklist.get("objects"))
    state_counts: dict[str, int] = {}
    for item in objects:
        state = str(item.get("state") or "unknown")
        state_counts[state] = state_counts.get(state, 0) + 1
    return {
        "object_count": len(objects),
        "cleanup_recommended_count": sum(1 for item in objects if item.get("cleanup_recommended")),
        "held_object_id": worklist.get("held_object_id"),
        "state_counts": state_counts,
        "objects": [
            {
                "object_id": item.get("object_id"),
                "category": item.get("category"),
                "state": item.get("state"),
                "cleanup_recommended": item.get("cleanup_recommended"),
                "candidate_fixture_id": item.get("candidate_fixture_id"),
                "last_waypoint_id": item.get("last_waypoint_id"),
            }
            for item in objects
        ],
    }


def _robot_view_contract_summary(contract: dict[str, Any]) -> dict[str, Any]:
    fpv = dict(contract.get("agent_facing_fpv") or {})
    verify = dict(contract.get("report_verify_view") or {})
    return {
        "backend": contract.get("backend"),
        "status": contract.get("status"),
        "camera_model": contract.get("camera_model"),
        "pose_source": contract.get("pose_source"),
        "lens_source": contract.get("lens_source"),
        "fpv_source": fpv.get("source"),
        "fpv_camera_prim_path": fpv.get("camera_prim_path") or contract.get("camera_prim_path"),
        "fpv_robot_mounted": fpv.get("robot_mounted"),
        "fpv_head_camera_equivalent": fpv.get("head_camera_equivalent"),
        "verify_source": verify.get("source"),
        "evidence_note": contract.get("evidence_note"),
    }


def _robot_import_summary(robot_asset: dict[str, Any]) -> dict[str, Any]:
    import_summary = dict(robot_asset.get("import_summary") or {})
    converter = dict(import_summary.get("converter") or {})
    fallback = dict(converter.get("fallback") or {})
    return {
        "head_camera_mounted": robot_asset.get("head_camera_mounted"),
        "head_camera_equivalent": robot_asset.get("head_camera_equivalent"),
        "head_camera_prim_path": robot_asset.get("head_camera_prim_path"),
        "head_link_name": robot_asset.get("head_link_name"),
        "expected_usd_path": robot_asset.get("expected_usd_path"),
        "status": import_summary.get("status"),
        "import_method": import_summary.get("import_method"),
        "asset_robot_prim_path": import_summary.get("asset_robot_prim_path"),
        "asset_head_camera_prim_path": import_summary.get("asset_head_camera_prim_path"),
        "fallback_status": fallback.get("status"),
        "mesh_reference_count": fallback.get("mesh_reference_count"),
        "missing_mesh_count": fallback.get("missing_mesh_count"),
        "unsupported_mesh_count": fallback.get("unsupported_mesh_count"),
        "note": fallback.get("note") or robot_asset.get("evidence_note"),
    }


def _artifact_links(
    run_result: dict[str, Any],
    *,
    run_dir: Path,
    output_dir: Path,
) -> dict[str, str]:
    artifacts = dict(run_result.get("artifacts") or {})
    resolved = {
        "run_dir": run_dir,
        "run_result": run_dir / "run_result.json",
        "report": _resolve_artifact(artifacts.get("report") or "report.html", run_dir),
        "trace": _resolve_artifact(artifacts.get("trace") or "trace.jsonl", run_dir),
        "agent_view": _resolve_artifact(artifacts.get("agent_view") or "agent_view.json", run_dir),
        "private_evaluation": _resolve_artifact(
            artifacts.get("private_evaluation") or "private_evaluation.json",
            run_dir,
        ),
        "codex_last_message": run_dir / "codex-last-message.md",
        "before_snapshot": _resolve_artifact(
            artifacts.get("before_snapshot") or "before.png",
            run_dir,
        ),
        "after_snapshot": _resolve_artifact(
            artifacts.get("after_snapshot") or "after.png", run_dir
        ),
        "robot_views": _resolve_artifact(artifacts.get("robot_views") or "robot_views", run_dir),
    }
    return {
        key: _output_relpath(path, output_dir)
        for key, path in resolved.items()
        if isinstance(path, Path) and path.exists()
    }


def _robot_view_samples(
    steps: list[dict[str, Any]],
    *,
    run_dir: Path,
    output_dir: Path,
) -> list[dict[str, Any]]:
    if not steps:
        return []
    indices = sorted({0, len(steps) // 2, len(steps) - 1})
    samples = []
    for index in indices:
        step = steps[index]
        views = dict(step.get("views") or {})
        samples.append(
            {
                "index": index,
                "label": step.get("label"),
                "action": step.get("action"),
                "semantic_phase": step.get("semantic_phase"),
                "views": {
                    key: _output_relpath(_resolve_artifact(views[key], run_dir), output_dir)
                    for key in ROBOT_VIEW_KEYS
                    if key in views
                },
                "robot_pose": step.get("robot_pose") or {},
            }
        )
    return samples


def _scene_signature(run_result: dict[str, Any]) -> dict[str, Any]:
    scenario_id = str(run_result.get("scenario_id") or "")
    scene_index = _scene_index_from_scenario(scenario_id)
    return {
        "scenario_id": scenario_id,
        "scene_source": _scene_source_from_scenario(scenario_id),
        "scene_index": scene_index,
    }


def _scene_index_from_scenario(scenario_id: str) -> int | None:
    match = re.search(r"val-(\d+)-", scenario_id)
    if not match:
        return None
    return int(match.group(1))


def _scene_source_from_scenario(scenario_id: str) -> str | None:
    if "procthor" in scenario_id:
        return "procthor-10k-val"
    return None


def _agent_view(run_result: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    path = run_dir / "agent_view.json"
    if path.is_file():
        return _read_json(path)
    return dict(run_result.get("agent_view") or {})


def _first_robot_view_contract(steps: list[dict[str, Any]]) -> dict[str, Any]:
    for step in steps:
        contract = step.get("camera_control_contract")
        if isinstance(contract, dict):
            return dict(contract)
    return {}


def _resolve_artifact(path_value: Any, run_dir: Path) -> Path:
    path = Path(str(path_value))
    if path.is_absolute():
        return path
    run_relative = run_dir / path
    if run_relative.exists():
        return run_relative
    return Path.cwd() / path


def _output_relpath(path: Path, output_dir: Path) -> str:
    try:
        return os.path.relpath(path.resolve(), output_dir.resolve())
    except ValueError:
        return str(path)


def _same_value(items: list[dict[str, Any]], key: str) -> dict[str, Any]:
    values = [item.get(key) for item in items]
    unique = {_json_key(value) for value in values}
    return {"matches": len(unique) <= 1, "values": values}


def _same_nested_value(items: list[dict[str, Any]], path: tuple[str, ...]) -> dict[str, Any]:
    values = [_nested(item, path) for item in items]
    unique = {_json_key(value) for value in values}
    return {"matches": len(unique) <= 1, "values": values}


def _nested(item: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = item
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def _json_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def _first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text_if_exists(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _render_report(manifest: dict[str, Any]) -> str:
    title = "Codex Cleanup Apple2Apple"
    comparison = dict(manifest.get("comparison") or {})
    lanes = dict(manifest.get("lanes") or {})
    body = "\n".join(
        [
            _summary_section(title, comparison, lanes),
            _comparability_section(comparison),
            _lane_result_section(lanes),
            _object_result_section(lanes),
            _camera_contract_section(lanes),
            _snapshot_section(lanes),
            _robot_view_sample_section(lanes),
            _agent_message_section(lanes),
            _artifact_section(lanes),
        ]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      color: #20242c;
      background: #eef2f6;
    }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 28px 20px 48px; }}
    h1 {{ margin: 0; font-size: 30px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; letter-spacing: 0; }}
    a {{ color: #155db1; }}
    .summary {{
      background: #20242c;
      color: #f8fafc;
      border-radius: 8px;
      padding: 22px;
      box-shadow: 0 14px 34px rgba(25, 32, 44, 0.16);
    }}
    .eyebrow {{
      margin: 0 0 6px;
      color: #a7d8cf;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .summary p {{ color: #dbe5ef; max-width: 980px; }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 10px;
      margin-top: 16px;
    }}
    .metric {{
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
    }}
    .summary .metric {{
      background: rgba(255, 255, 255, 0.09);
      border-color: rgba(255, 255, 255, 0.18);
      color: #e9edf4;
    }}
    .metric strong {{ display: block; font-size: 20px; margin-top: 4px; overflow-wrap: anywhere; }}
    .metric span {{ color: #657184; font-size: 12px; text-transform: uppercase; }}
    .summary .metric span {{ color: #b8c5d4; }}
    .panel {{
      background: #ffffff;
      border: 1px solid #d8dee8;
      border-radius: 8px;
      padding: 18px;
      margin-top: 18px;
      box-shadow: 0 5px 16px rgba(25, 32, 44, 0.06);
    }}
    .note {{ color: #565f70; margin: 0 0 12px; }}
    .warn {{ color: #8a5b00; }}
    .good {{ color: #147349; }}
    .bad {{ color: #a93535; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #d9dde6; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{
      padding: 9px 10px;
      text-align: left;
      border-bottom: 1px solid #e5e8ee;
      font-size: 14px;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    th {{ background: #eef1f5; font-weight: 650; }}
    .lane-grid, .image-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }}
    figure {{
      margin: 0;
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 10px;
    }}
    img {{ width: 100%; height: auto; display: block; background: #111; }}
    figcaption {{ margin-top: 8px; color: #565f70; font-size: 13px; overflow-wrap: anywhere; }}
    pre {{
      white-space: pre-wrap;
      background: #f7f8fa;
      border: 1px solid #e1e5ec;
      border-radius: 6px;
      padding: 10px;
      overflow-wrap: anywhere;
    }}
    @media (max-width: 640px) {{
      main {{ padding: 18px 12px 36px; }}
      .lane-grid, .image-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body><main>{body}</main></body>
</html>
"""


def _summary_section(
    title: str,
    comparison: dict[str, Any],
    lanes: dict[str, dict[str, Any]],
) -> str:
    metrics = [
        ("mode", comparison.get("status_label")),
        ("strict scene", "yes" if comparison.get("strict_scene_identical") else "no"),
    ]
    for lane_id, lane in lanes.items():
        metrics.append((f"{lane_id} status", lane.get("completion_status")))
        metrics.append((f"{lane_id} restored", _restored_text(lane)))
    return f"""
<section class="summary">
  <p class="eyebrow">Household cleanup A/B</p>
  <h1>{html.escape(title)}</h1>
  <p>
    This report compares existing Codex cleanup artifacts from MuJoCo and Isaac.
    It is meant to separate simulator/camera contract evidence from cleanup
    outcome differences.
  </p>
  <div class="metric-grid">{"".join(_metric(label, value) for label, value in metrics)}</div>
</section>
"""


def _comparability_section(comparison: dict[str, Any]) -> str:
    axis_rows = []
    for axis, check in dict(comparison.get("axis_checks") or {}).items():
        values = check.get("values") if isinstance(check, dict) else []
        axis_rows.append(
            "<tr>"
            f"<td>{html.escape(str(axis))}</td>"
            f"<td>{_status_text(bool(check.get('matches')))}</td>"
            f"<td><code>{html.escape(json.dumps(values, ensure_ascii=False))}</code></td>"
            "</tr>"
        )
    notes = "".join(
        f"<li>{html.escape(str(note))}</li>"
        for note in list(comparison.get("interpretation_notes") or [])
    )
    return f"""
<section class="panel">
  <h2>Comparability</h2>
  <p class="note">
    A strict apple-to-apple result requires the same seed, scene, requested and
    actual generated mess count, cleanup target object set, policy, map mode,
    and camera contract. This section records which axes matched in the current
    artifacts.
  </p>
  <div class="table-wrap"><table>
    <thead><tr><th>Axis</th><th>Match</th><th>Values</th></tr></thead>
    <tbody>{"".join(axis_rows)}</tbody>
  </table></div>
  <ul>{notes}</ul>
</section>
"""


def _lane_result_section(lanes: dict[str, dict[str, Any]]) -> str:
    rows = []
    for lane_id, lane in lanes.items():
        score = dict(lane.get("score") or {})
        rows.append(
            "<tr>"
            f"<td><strong>{html.escape(lane_id)}</strong><br>{html.escape(str(lane.get('backend')))}</td>"
            f"<td>{_completion_status(lane.get('completion_status'))}</td>"
            f"<td>{html.escape(str(score.get('restored_text')))}</td>"
            f"<td>{_percent(score.get('mess_restoration_rate'))}</td>"
            f"<td>{_percent(score.get('sweep_coverage_rate'))}</td>"
            f"<td>{html.escape(str(score.get('disturbance_count')))}</td>"
            f"<td>{html.escape(str(lane.get('generated_mess_count')))} / "
            f"{html.escape(str(lane.get('requested_generated_mess_count')))}</td>"
            f"<td>{html.escape(str(lane.get('scenario_id')))}</td>"
            "</tr>"
        )
    return f"""
<section class="panel">
  <h2>Lane Results</h2>
  <div class="table-wrap"><table>
    <thead>
      <tr>
        <th>Lane</th><th>Status</th><th>Restored</th><th>Restoration</th>
        <th>Sweep</th><th>Disturbances</th><th>Mess count</th><th>Scenario</th>
      </tr>
    </thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _object_result_section(lanes: dict[str, dict[str, Any]]) -> str:
    blocks = []
    for lane_id, lane in lanes.items():
        rows = []
        for item in list((lane.get("score") or {}).get("object_results") or []):
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(item.get('object_category')))}</td>"
                f"<td><code>{html.escape(str(item.get('object_id')))}</code></td>"
                f"<td>{'yes' if item.get('restored') else 'no'}</td>"
                f"<td>{html.escape(str(item.get('actual_receptacle_category')))}</td>"
                f"<td>{html.escape(str(item.get('semantic_acceptability')))}</td>"
                f"<td>{html.escape(str(item.get('semantic_reason')))}</td>"
                "</tr>"
            )
        blocks.append(
            f"""
<h3>{html.escape(lane_id)}</h3>
<div class="table-wrap"><table>
  <thead>
    <tr><th>Category</th><th>Object</th><th>Restored</th><th>Final receptacle</th>
    <th>Semantic</th><th>Reason</th></tr>
  </thead>
  <tbody>{"".join(rows)}</tbody>
</table></div>
"""
        )
    return f'<section class="panel"><h2>Private Score Objects</h2>{"".join(blocks)}</section>'


def _camera_contract_section(lanes: dict[str, dict[str, Any]]) -> str:
    rows = []
    for lane_id, lane in lanes.items():
        camera = dict(lane.get("robot_view_contract") or {})
        import_summary = dict(lane.get("robot_import") or {})
        rows.append(
            "<tr>"
            f"<td>{html.escape(lane_id)}</td>"
            f"<td>{html.escape(str(camera.get('camera_model')))}</td>"
            f"<td>{html.escape(str(camera.get('fpv_source')))}</td>"
            f"<td>{html.escape(str(camera.get('fpv_camera_prim_path') or ''))}</td>"
            f"<td>{html.escape(str(camera.get('lens_source')))}</td>"
            f"<td>{html.escape(str(import_summary.get('import_method') or 'n/a'))}</td>"
            f"<td>{html.escape(str(import_summary.get('note') or ''))}</td>"
            "</tr>"
        )
    return f"""
<section class="panel">
  <h2>Camera And Robot Import</h2>
  <p class="note">
    FPV is the agent-facing camera. Chase is intentionally an auxiliary report
    camera and is not used as the robot's first-person input.
  </p>
  <div class="table-wrap"><table>
    <thead>
      <tr>
        <th>Lane</th><th>Camera model</th><th>FPV source</th><th>FPV prim</th>
        <th>Lens source</th><th>Robot import</th><th>Import note</th>
      </tr>
    </thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _snapshot_section(lanes: dict[str, dict[str, Any]]) -> str:
    figures = []
    for lane_id, lane in lanes.items():
        artifacts = dict(lane.get("artifacts") or {})
        for key, title in (("before_snapshot", "before"), ("after_snapshot", "after")):
            path = artifacts.get(key)
            if not path:
                continue
            figures.append(_figure(path, f"{lane_id} {title}"))
    return f"""
<section class="panel">
  <h2>Before And After</h2>
  <div class="image-grid">{"".join(figures)}</div>
</section>
"""


def _robot_view_sample_section(lanes: dict[str, dict[str, Any]]) -> str:
    blocks = []
    for lane_id, lane in lanes.items():
        figures = []
        for sample in list(lane.get("robot_view_samples") or []):
            views = dict(sample.get("views") or {})
            for view_key in ROBOT_VIEW_KEYS:
                if view_key not in views:
                    continue
                caption = f"{lane_id} {sample.get('label')} {view_key}"
                figures.append(_figure(views[view_key], caption))
        blocks.append(
            f'<h3>{html.escape(lane_id)}</h3><div class="image-grid">{"".join(figures)}</div>'
        )
    return f"""
<section class="panel">
  <h2>Robot View Samples</h2>
  <p class="note">
    Samples are first/middle/final within each run, so they are useful for
    camera inspection but are not timestep-aligned across lanes.
  </p>
  {"".join(blocks)}
</section>
"""


def _agent_message_section(lanes: dict[str, dict[str, Any]]) -> str:
    blocks = []
    for lane_id, lane in lanes.items():
        blocks.append(
            f"""
<h3>{html.escape(lane_id)}</h3>
<p><strong>Terminate reason:</strong> {html.escape(str(lane.get("terminate_reason") or ""))}</p>
<pre>{html.escape(str(lane.get("codex_last_message") or ""))}</pre>
"""
        )
    return f'<section class="panel"><h2>Agent Summaries</h2>{"".join(blocks)}</section>'


def _artifact_section(lanes: dict[str, dict[str, Any]]) -> str:
    rows = []
    for lane_id, lane in lanes.items():
        artifacts = dict(lane.get("artifacts") or {})
        links = []
        for key in ("report", "run_result", "trace", "agent_view", "private_evaluation"):
            path = artifacts.get(key)
            if path:
                links.append(f'<a href="{html.escape(path, quote=True)}">{html.escape(key)}</a>')
        rows.append(f"<tr><td>{html.escape(lane_id)}</td><td>{' | '.join(links)}</td></tr>")
    return f"""
<section class="panel">
  <h2>Artifacts</h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Lane</th><th>Links</th></tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(str(label))}</span>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</div>"
    )


def _status_text(matches: bool) -> str:
    if matches:
        return '<span class="good">yes</span>'
    return '<span class="warn">no</span>'


def _completion_status(value: Any) -> str:
    text = html.escape(str(value))
    if value == "success":
        return f'<span class="good">{text}</span>'
    if value == "failed":
        return f'<span class="bad">{text}</span>'
    return text


def _percent(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return html.escape(str(value))


def _figure(path: str, caption: str) -> str:
    return (
        "<figure>"
        f'<img src="{html.escape(path, quote=True)}" alt="{html.escape(caption, quote=True)}">'
        f"<figcaption>{html.escape(caption)}</figcaption>"
        "</figure>"
    )


def _restored_text(lane: dict[str, Any]) -> str:
    score = dict(lane.get("score") or {})
    return str(score.get("restored_text") or "")


if __name__ == "__main__":
    raise SystemExit(main())
