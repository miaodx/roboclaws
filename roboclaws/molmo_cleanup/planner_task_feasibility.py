from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

GRASP_FEASIBILITY_SIGNATURE_SCHEMA = "planner_grasp_feasibility_signature_v1"
GRASP_FEASIBILITY_MITIGATION_DECISION_SCHEMA = "planner_grasp_feasibility_mitigation_decision_v1"
GRASP_CACHE_AVAILABILITY_PREFLIGHT_SCHEMA = "planner_grasp_cache_availability_preflight_v1"
GRASP_CACHE_GENERATION_PREFLIGHT_SCHEMA = "planner_grasp_cache_generation_preflight_v1"


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


def grasp_feasibility_mitigation_decision(
    *,
    prior_proof_result_summary: dict[str, Any] | None = None,
    proof_result_summary: dict[str, Any] | None = None,
    proof_request_selection: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prior_summary = prior_proof_result_summary or {}
    proof_summary = proof_result_summary or {}
    selection = proof_request_selection or {}
    signature_rows = _mitigation_signature_rows(
        [
            ("prior_proof_result_summary", prior_summary),
            ("proof_result_summary", proof_summary),
        ]
    )
    subkind_counts: dict[str, int] = {}
    missing_assets: list[str] = []
    exception_types: list[str] = []
    request_ids: list[str] = []
    for row in signature_rows:
        subkind = str(row.get("subkind") or "unknown")
        subkind_counts[subkind] = subkind_counts.get(subkind, 0) + int(row.get("count") or 0)
        for value in row.get("grasp_load_exception_asset_uids") or []:
            _append_unique(missing_assets, str(value or ""))
        for value in row.get("grasp_load_exception_types") or []:
            _append_unique(exception_types, str(value or ""))
        for value in row.get("request_ids") or []:
            _append_unique(request_ids, str(value or ""))
    selected_count = int(selection.get("selected_count") or 0)
    excluded_count = int(selection.get("excluded_count") or 0)
    source_rotation_state = _source_rotation_state(selected_count, excluded_count)
    primary_route, status, recommendation, rationale = _mitigation_route(
        missing_assets=missing_assets,
        subkind_counts=subkind_counts,
        source_rotation_state=source_rotation_state,
    )
    return {
        "schema": GRASP_FEASIBILITY_MITIGATION_DECISION_SCHEMA,
        "status": status,
        "primary_route": primary_route,
        "recommendation": recommendation,
        "rationale": rationale,
        "source_rotation_state": source_rotation_state,
        "selected_request_count": selected_count,
        "excluded_request_count": excluded_count,
        "signature_group_count": len(signature_rows),
        "subkind_counts": subkind_counts,
        "missing_grasp_asset_uids": missing_assets,
        "grasp_load_exception_types": exception_types,
        "evidence_request_ids": request_ids,
        "signature_groups": signature_rows,
    }


def grasp_cache_availability_preflight(
    decision: dict[str, Any],
    *,
    assets_dir: Path | str | None = None,
    assets_dir_source: str | None = None,
) -> dict[str, Any]:
    """Check the exact rigid grasp-cache files used by MolmoSpaces' loader."""
    missing_assets = _unique_nonempty(decision.get("missing_grasp_asset_uids") or [])
    resolved_assets_dir, resolved_assets_dir_source = _resolve_assets_dir(
        assets_dir,
        source=assets_dir_source,
    )
    if not missing_assets:
        return {
            "schema": GRASP_CACHE_AVAILABILITY_PREFLIGHT_SCHEMA,
            "status": "not_applicable",
            "assets_dir": str(resolved_assets_dir),
            "assets_dir_resolved": _resolved_path(resolved_assets_dir),
            "assets_dir_source": resolved_assets_dir_source,
            "assets_dir_exists": resolved_assets_dir.exists(),
            "missing_grasp_asset_uids": [],
            "asset_count": 0,
            "ready_asset_count": 0,
            "missing_cache_asset_count": 0,
            "cache_ready_asset_uids": [],
            "cache_missing_asset_uids": [],
            "loader_sources": ["droid", "droid_objaverse", "rum"],
            "assets": [],
            "upstream_loader": "molmo_spaces.utils.grasp_sample.load_grasps_for_object",
            "evidence_note": (
                "No missing grasp-cache asset IDs were present in the mitigation decision."
            ),
        }

    assets = [
        _grasp_cache_asset_preflight(asset_uid, assets_dir=resolved_assets_dir)
        for asset_uid in missing_assets
    ]
    ready_assets = [
        str(item.get("asset_uid") or "")
        for item in assets
        if str(item.get("status") or "") == "ready"
    ]
    missing_cache_assets = [
        str(item.get("asset_uid") or "")
        for item in assets
        if str(item.get("status") or "") == "missing_cache"
    ]
    status = "ready" if len(ready_assets) == len(assets) else "missing_cache"
    recommendation = (
        "cached_rigid_grasps_present_for_retry"
        if status == "ready"
        else "generate_or_install_rigid_grasp_cache_before_retry"
    )
    return {
        "schema": GRASP_CACHE_AVAILABILITY_PREFLIGHT_SCHEMA,
        "status": status,
        "assets_dir": str(resolved_assets_dir),
        "assets_dir_resolved": _resolved_path(resolved_assets_dir),
        "assets_dir_source": resolved_assets_dir_source,
        "assets_dir_exists": resolved_assets_dir.exists(),
        "missing_grasp_asset_uids": missing_assets,
        "asset_count": len(assets),
        "ready_asset_count": len(ready_assets),
        "missing_cache_asset_count": len(missing_cache_assets),
        "cache_ready_asset_uids": ready_assets,
        "cache_missing_asset_uids": missing_cache_assets,
        "loader_sources": ["droid", "droid_objaverse", "rum"],
        "assets": assets,
        "mitigation_recommendation": recommendation,
        "upstream_loader": "molmo_spaces.utils.grasp_sample.load_grasps_for_object",
        "evidence_note": (
            "Preflights the rigid-object grasp files used by MolmoSpaces "
            "load_grasps_for_object. The droid joint file is reported only as a "
            "folder probe and does not make the rigid loader ready."
        ),
    }


def _resolve_assets_dir(
    assets_dir: Path | str | None,
    *,
    source: str | None = None,
) -> tuple[Path, str]:
    if assets_dir is not None:
        return Path(assets_dir).expanduser(), source or "argument"
    env_value = os.environ.get("MLSPACES_ASSETS_DIR")
    if env_value:
        return Path(env_value).expanduser(), "MLSPACES_ASSETS_DIR"
    return Path("~/.cache/molmo-spaces-resources").expanduser(), "default"


def grasp_cache_generation_preflight(
    availability_preflight: dict[str, Any],
    *,
    output_dir: Path | str | None = None,
    molmospaces_python: Path | str | None = None,
    molmospaces_root: Path | str | None = None,
    timeout_s: float = 30.0,
) -> dict[str, Any]:
    """Preflight the upstream rigid grasp-generation path for missing cache assets."""
    missing_assets = [
        asset
        for asset in availability_preflight.get("assets") or []
        if isinstance(asset, dict) and str(asset.get("status") or "") == "missing_cache"
    ]
    if not missing_assets:
        return {
            "schema": GRASP_CACHE_GENERATION_PREFLIGHT_SCHEMA,
            "status": "not_applicable",
            "asset_count": 0,
            "ready": False,
            "assets": [],
            "checks": [],
            "blockers": [],
            "evidence_note": "No missing rigid grasp-cache assets require generation.",
        }

    checks: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    python_path = Path(molmospaces_python).expanduser() if molmospaces_python else None
    runtime = _molmospaces_runtime_probe(python_path, timeout_s=timeout_s)
    checks.extend(runtime["checks"])
    blockers.extend(runtime["blockers"])

    root_path = (
        Path(molmospaces_root).expanduser()
        if molmospaces_root is not None
        else _optional_path(runtime.get("molmospaces_root"))
    )
    assets_dir = _optional_path(availability_preflight.get("assets_dir")) or _optional_path(
        runtime.get("assets_dir")
    )
    output_root = Path(output_dir).expanduser() if output_dir else Path("output")
    objects_list_path = output_root / "grasp_generation" / "rigid_objects_list.json"

    if python_path is not None and runtime.get("python_ready"):
        for check in _rigid_generation_python_checks(python_path, timeout_s=timeout_s):
            checks.append(check)
            if check.get("status") == "blocked":
                blockers.append(_blocker_from_check(check))

    file_checks = _rigid_generation_file_checks(
        molmospaces_root=root_path,
        assets_dir=assets_dir,
    )
    checks.extend(file_checks)
    for check in file_checks:
        if check.get("status") == "blocked":
            blockers.append(_blocker_from_check(check))

    assets = [
        _grasp_cache_generation_asset_preflight(
            asset,
            molmospaces_root=root_path,
            objects_list_path=objects_list_path,
        )
        for asset in missing_assets
    ]
    for asset in assets:
        if not asset.get("object_xml_exists"):
            blockers.append(
                {
                    "code": "object_xml_missing",
                    "message": f"Object XML is missing for {asset.get('asset_uid')}",
                    "asset_uid": asset.get("asset_uid"),
                }
            )
        if not asset.get("cache_target_path"):
            blockers.append(
                {
                    "code": "cache_target_missing",
                    "message": f"No droid rigid cache target found for {asset.get('asset_uid')}",
                    "asset_uid": asset.get("asset_uid"),
                }
            )

    status = "ready" if not blockers else "blocked"
    command = _rigid_generation_command(
        molmospaces_python=python_path,
        molmospaces_root=root_path,
        objects_list_path=objects_list_path,
    )
    return {
        "schema": GRASP_CACHE_GENERATION_PREFLIGHT_SCHEMA,
        "status": status,
        "ready": status == "ready",
        "asset_count": len(assets),
        "assets": assets,
        "molmospaces_python": str(python_path or ""),
        "molmospaces_root": str(root_path or ""),
        "assets_dir": str(assets_dir or ""),
        "objects_list_path": str(objects_list_path),
        "working_dir": str(_grasp_generation_working_dir(root_path) or ""),
        "command": command,
        "checks": checks,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "mitigation_recommendation": (
            "run_rigid_grasp_generation_then_install_filtered_npz"
            if status == "ready"
            else "install_grasp_generation_prerequisites_before_cache_generation"
        ),
        "evidence_note": (
            "Preflights the upstream MolmoSpaces rigid grasp-generation pipeline. "
            "It does not create or install grasps; generated NPZ output must still "
            "be copied to the loader cache target and pass availability validation."
        ),
    }


def _grasp_cache_asset_preflight(asset_uid: str, *, assets_dir: Path) -> dict[str, Any]:
    candidate_files = _rigid_grasp_loader_files(asset_uid, assets_dir=assets_dir)
    folder_probe_files = _folder_probe_grasp_files(asset_uid, assets_dir=assets_dir)
    ready = any(bool(item.get("valid")) for item in candidate_files)
    present_candidate_count = sum(1 for item in candidate_files if bool(item.get("exists")))
    object_asset_files = _object_asset_files(asset_uid, assets_dir=assets_dir)
    return {
        "asset_uid": asset_uid,
        "status": "ready" if ready else "missing_cache",
        "loader_file_status": _loader_file_status(
            ready=ready,
            present_candidate_count=present_candidate_count,
        ),
        "object_asset_status": "present" if object_asset_files else "missing",
        "candidate_grasp_files": candidate_files,
        "folder_probe_files": folder_probe_files,
        "object_asset_files": object_asset_files,
    }


def _molmospaces_runtime_probe(
    molmospaces_python: Path | None,
    *,
    timeout_s: float,
) -> dict[str, Any]:
    if molmospaces_python is None:
        blocker = {
            "code": "molmospaces_python_not_configured",
            "message": "No MolmoSpaces Python executable was configured for grasp generation.",
        }
        return {
            "python_ready": False,
            "molmospaces_root": "",
            "assets_dir": "",
            "checks": [{"name": "molmospaces_python", "status": "blocked", **blocker}],
            "blockers": [blocker],
        }
    if not molmospaces_python.is_file():
        blocker = {
            "code": "molmospaces_python_missing",
            "message": f"MolmoSpaces Python executable is missing: {molmospaces_python}",
        }
        return {
            "python_ready": False,
            "molmospaces_root": "",
            "assets_dir": "",
            "checks": [{"name": "molmospaces_python", "status": "blocked", **blocker}],
            "blockers": [blocker],
        }
    command = [
        str(molmospaces_python),
        "-c",
        (
            "import json; "
            "from molmo_spaces.molmo_spaces_constants import "
            "ABS_PATH_OF_TOP_LEVEL_MOLMO_SPACES_DIR, ASSETS_DIR; "
            "print(json.dumps({'molmospaces_root': str(ABS_PATH_OF_TOP_LEVEL_MOLMO_SPACES_DIR), "
            "'assets_dir': str(ASSETS_DIR)}))"
        ),
    ]
    completed = _run_preflight_command(command, timeout_s=timeout_s)
    check = {
        "name": "molmo_spaces_runtime",
        "command": command,
        **completed,
    }
    if completed["status"] != "ready":
        blocker = _blocker_from_check(
            {
                **check,
                "code": "molmo_spaces_runtime_probe_failed",
                "message": completed.get("stderr")
                or completed.get("stdout")
                or "MolmoSpaces runtime probe failed.",
            }
        )
        check.update(blocker)
        return {
            "python_ready": False,
            "molmospaces_root": "",
            "assets_dir": "",
            "checks": [check],
            "blockers": [blocker],
        }
    try:
        payload = json.loads(str(completed.get("stdout") or "{}"))
    except json.JSONDecodeError:
        payload = {}
    root = str(payload.get("molmospaces_root") or "")
    assets_dir = str(payload.get("assets_dir") or "")
    check.update({"molmospaces_root": root, "assets_dir": assets_dir})
    return {
        "python_ready": True,
        "molmospaces_root": root,
        "assets_dir": assets_dir,
        "checks": [check],
        "blockers": [],
    }


def _rigid_generation_python_checks(
    molmospaces_python: Path,
    *,
    timeout_s: float,
) -> list[dict[str, Any]]:
    checks = [
        _python_import_check(
            molmospaces_python,
            name="python_module_mujoco",
            import_name="mujoco",
            timeout_s=timeout_s,
        ),
        _python_import_check(
            molmospaces_python,
            name="python_module_trimesh",
            import_name="trimesh",
            timeout_s=timeout_s,
        ),
        _python_import_check(
            molmospaces_python,
            name="python_module_sklearn",
            import_name="sklearn",
            timeout_s=timeout_s,
        ),
    ]
    collision_command = [
        str(molmospaces_python),
        "-c",
        "import trimesh; trimesh.collision.CollisionManager(); print('python-fcl ok')",
    ]
    completed = _run_preflight_command(collision_command, timeout_s=timeout_s)
    check = {
        "name": "python_fcl_runtime",
        "command": collision_command,
        **completed,
    }
    if check["status"] == "blocked":
        check.update(
            {
                "code": "python_fcl_missing",
                "message": check.get("stderr") or check.get("stdout") or "python-fcl unavailable",
            }
        )
    checks.append(check)
    return checks


def _python_import_check(
    molmospaces_python: Path,
    *,
    name: str,
    import_name: str,
    timeout_s: float,
) -> dict[str, Any]:
    command = [str(molmospaces_python), "-c", f"import {import_name}; print('{import_name} ok')"]
    completed = _run_preflight_command(command, timeout_s=timeout_s)
    check = {"name": name, "command": command, **completed}
    if check["status"] == "blocked":
        check.update(
            {
                "code": f"{import_name.replace('.', '_')}_missing",
                "message": check.get("stderr") or check.get("stdout") or f"{import_name} missing",
            }
        )
    return check


def _rigid_generation_file_checks(
    *,
    molmospaces_root: Path | None,
    assets_dir: Path | None,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    if molmospaces_root is None:
        checks.append(
            {
                "name": "molmospaces_root",
                "status": "blocked",
                "code": "molmospaces_root_unknown",
                "message": "MolmoSpaces repository root could not be resolved.",
            }
        )
        return checks
    checks.extend(
        [
            _path_check(
                "run_rigid_script",
                molmospaces_root / "molmo_spaces" / "grasp_generation" / "run_rigid.py",
                must_be_executable=False,
            ),
            _path_check(
                "combine_meshes_script",
                molmospaces_root
                / "molmo_spaces"
                / "grasp_generation"
                / "pipeline"
                / "combine_meshes.py",
                must_be_executable=False,
            ),
            _path_check(
                "generate_grasps_script",
                molmospaces_root
                / "molmo_spaces"
                / "grasp_generation"
                / "pipeline"
                / "generate_grasps.py",
                must_be_executable=False,
            ),
            _path_check(
                "perturbations_test_script",
                molmospaces_root
                / "molmo_spaces"
                / "grasp_generation"
                / "pipeline"
                / "perturbations_test.py",
                must_be_executable=False,
            ),
            _path_check(
                "manifold_executable",
                molmospaces_root / "external_src" / "Manifold" / "build" / "manifold",
                must_be_executable=True,
            ),
            _path_check(
                "simplify_executable",
                molmospaces_root / "external_src" / "Manifold" / "build" / "simplify",
                must_be_executable=True,
            ),
        ]
    )
    if assets_dir is None:
        checks.append(
            {
                "name": "assets_dir",
                "status": "blocked",
                "code": "assets_dir_unknown",
                "message": "MolmoSpaces assets dir could not be resolved.",
            }
        )
    else:
        checks.append(
            _path_check(
                "floating_robotiq_model",
                assets_dir / "robots" / "floating_robotiq" / "model_rigid.xml",
                must_be_executable=False,
            )
        )
    return checks


def _grasp_cache_generation_asset_preflight(
    asset: dict[str, Any],
    *,
    molmospaces_root: Path | None,
    objects_list_path: Path,
) -> dict[str, Any]:
    asset_uid = str(asset.get("asset_uid") or "")
    object_xml = _first_object_asset(asset, kind="xml")
    cache_target = _first_candidate(asset, source="droid")
    generated_npz = (
        molmospaces_root
        / "grasp_results"
        / "rigid_objects"
        / asset_uid
        / f"{asset_uid}_grasps_filtered.npz"
        if molmospaces_root is not None and asset_uid
        else None
    )
    return {
        "asset_uid": asset_uid,
        "object_xml": str(object_xml or ""),
        "object_xml_exists": bool(object_xml and object_xml.exists()),
        "objects_list_entry": {"name": asset_uid, "xml": str(object_xml or "")},
        "objects_list_path": str(objects_list_path),
        "generated_npz_path": str(generated_npz or ""),
        "generated_npz_exists": bool(generated_npz and generated_npz.exists()),
        "cache_target_path": str(cache_target.get("path") or ""),
        "cache_target_resolved_path": str(cache_target.get("resolved_path") or ""),
        "cache_target_relative_path": str(cache_target.get("relative_path") or ""),
    }


def _first_object_asset(asset: dict[str, Any], *, kind: str) -> Path | None:
    for item in asset.get("object_asset_files") or []:
        if isinstance(item, dict) and str(item.get("kind") or "") == kind:
            path = str(item.get("resolved_path") or item.get("path") or "")
            if path:
                return Path(path)
    return None


def _first_candidate(asset: dict[str, Any], *, source: str) -> dict[str, Any]:
    for item in asset.get("candidate_grasp_files") or []:
        if isinstance(item, dict) and str(item.get("source") or "") == source:
            return item
    return {}


def _rigid_generation_command(
    *,
    molmospaces_python: Path | None,
    molmospaces_root: Path | None,
    objects_list_path: Path,
) -> list[str]:
    working_dir = _grasp_generation_working_dir(molmospaces_root)
    script = working_dir / "run_rigid.py" if working_dir is not None else Path("run_rigid.py")
    return [
        str(molmospaces_python or "python"),
        str(script),
        "--objects_list",
        str(objects_list_path),
        "--max_successful_grasps",
        "1000",
        "--num_workers",
        "1",
    ]


def _grasp_generation_working_dir(molmospaces_root: Path | None) -> Path | None:
    if molmospaces_root is None:
        return None
    return molmospaces_root / "molmo_spaces" / "grasp_generation"


def _path_check(name: str, path: Path, *, must_be_executable: bool) -> dict[str, Any]:
    exists = path.exists()
    executable = os.access(path, os.X_OK) if exists else False
    ready = exists and (executable if must_be_executable else path.is_file())
    check = {
        "name": name,
        "path": str(path),
        "resolved_path": _resolved_path(path),
        "exists": exists,
        "executable": executable,
        "status": "ready" if ready else "blocked",
    }
    if not ready:
        check.update(
            {
                "code": f"{name}_missing",
                "message": f"Required path is not ready: {path}",
            }
        )
    return check


def _run_preflight_command(command: list[str], *, timeout_s: float) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "blocked",
            "returncode": "",
            "stdout": str(exc.stdout or "").strip(),
            "stderr": str(exc.stderr or "").strip(),
            "code": "preflight_command_timeout",
            "message": f"Preflight command exceeded {timeout_s:.1f}s.",
        }
    return {
        "status": "ready" if completed.returncode == 0 else "blocked",
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _blocker_from_check(check: dict[str, Any]) -> dict[str, Any]:
    return {
        "code": str(check.get("code") or f"{check.get('name', 'check')}_blocked"),
        "message": str(check.get("message") or check.get("stderr") or "preflight check blocked"),
        "name": str(check.get("name") or ""),
    }


def _optional_path(value: Any) -> Path | None:
    text = str(value or "")
    return Path(text).expanduser() if text else None


def _rigid_grasp_loader_files(asset_uid: str, *, assets_dir: Path) -> list[dict[str, Any]]:
    return [
        _file_probe(
            assets_dir / "grasps" / "droid" / asset_uid / f"{asset_uid}_grasps_filtered.npz",
            assets_dir=assets_dir,
            asset_uid=asset_uid,
            source="droid",
            gripper="droid",
            loader_role="rigid_object_loader",
        ),
        _file_probe(
            assets_dir
            / "grasps"
            / "droid_objaverse"
            / asset_uid
            / f"{asset_uid}_grasps_filtered.npz",
            assets_dir=assets_dir,
            asset_uid=asset_uid,
            source="droid_objaverse",
            gripper="droid",
            loader_role="rigid_object_loader",
        ),
        _file_probe(
            assets_dir / "grasps" / "rum" / asset_uid / f"{asset_uid}_grasps_filtered.json",
            assets_dir=assets_dir,
            asset_uid=asset_uid,
            source="rum",
            gripper="rum",
            loader_role="rigid_object_loader",
        ),
    ]


def _folder_probe_grasp_files(asset_uid: str, *, assets_dir: Path) -> list[dict[str, Any]]:
    return [
        _file_probe(
            assets_dir / "grasps" / "droid" / asset_uid / f"{asset_uid}_joint_grasps_filtered.npz",
            assets_dir=assets_dir,
            asset_uid=asset_uid,
            source="droid",
            gripper="droid",
            loader_role="has_grasp_folder_only",
        )
    ]


def _object_asset_files(
    asset_uid: str, *, assets_dir: Path, limit: int = 8
) -> list[dict[str, Any]]:
    if not assets_dir.exists():
        return []
    results: list[dict[str, Any]] = []
    roots = [assets_dir / "objects" / "thor"]
    for root in roots:
        if not root.exists():
            continue
        for pattern, kind in ((f"{asset_uid}.xml", "xml"), (f"{asset_uid}.obj", "obj")):
            for path in root.rglob(pattern):
                results.append(
                    {
                        "kind": kind,
                        "path": str(path),
                        "resolved_path": _resolved_path(path),
                        "relative_path": _relative_to_assets(path, assets_dir),
                        "exists": path.exists(),
                        "size_bytes": _file_size(path),
                    }
                )
                if len(results) >= limit:
                    return results
    return results


def _file_probe(
    path: Path,
    *,
    assets_dir: Path,
    asset_uid: str,
    source: str,
    gripper: str,
    loader_role: str,
) -> dict[str, Any]:
    validation = validate_grasp_cache_file(path) if loader_role == "rigid_object_loader" else {}
    return {
        "asset_uid": asset_uid,
        "source": source,
        "gripper": gripper,
        "loader_role": loader_role,
        "path": str(path),
        "resolved_path": _resolved_path(path),
        "parent_resolved_path": _resolved_path(path.parent),
        "parent_exists": path.parent.exists(),
        "relative_path": _relative_to_assets(path, assets_dir),
        "exists": path.exists(),
        "size_bytes": _file_size(path),
        **validation,
    }


def _loader_file_status(*, ready: bool, present_candidate_count: int) -> str:
    if ready:
        return "valid"
    if present_candidate_count:
        return "present_but_invalid"
    return "missing"


def validate_grasp_cache_file(path: Path | str) -> dict[str, Any]:
    path = Path(path)
    if not path.exists() or not path.is_file():
        return {
            "validation_status": "missing",
            "valid": False,
            "transform_count": 0,
        }
    try:
        if path.suffix == ".npz":
            import numpy as np

            with np.load(path) as data:
                transforms = data.get("transforms", [])
                transform_count = len(transforms)
        elif path.suffix == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            transforms = payload.get("transforms", []) if isinstance(payload, dict) else []
            transform_count = len(transforms)
        else:
            return {
                "validation_status": "unsupported",
                "valid": False,
                "transform_count": 0,
            }
    except Exception as exc:
        return {
            "validation_status": "error",
            "valid": False,
            "transform_count": 0,
            "validation_error_type": type(exc).__name__,
            "validation_error": str(exc),
        }
    return {
        "validation_status": "valid" if transform_count > 0 else "empty",
        "valid": transform_count > 0,
        "transform_count": transform_count,
    }


def _relative_to_assets(path: Path, assets_dir: Path) -> str:
    try:
        return str(path.relative_to(assets_dir))
    except ValueError:
        return str(path)


def _resolved_path(path: Path) -> str:
    try:
        return str(path.resolve(strict=False))
    except OSError:
        return str(path)


def _file_size(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    try:
        return path.stat().st_size
    except OSError:
        return 0


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


def _mitigation_signature_rows(
    summaries: list[tuple[str, dict[str, Any]]],
) -> list[dict[str, Any]]:
    rows = []
    for source, summary in summaries:
        if not isinstance(summary, dict) or not summary:
            continue
        signature_groups = summary.get("grasp_feasibility_signature_counts") or []
        if not signature_groups:
            signature_groups = grasp_feasibility_signature_counts(summary.get("results") or [])
        for group in signature_groups:
            if not isinstance(group, dict) or not group:
                continue
            rows.append(
                {
                    "source": source,
                    "subkind": str(group.get("subkind") or "unknown"),
                    "count": int(group.get("count") or 0),
                    "summary": str(group.get("summary") or ""),
                    "request_ids": [str(value) for value in group.get("request_ids") or []],
                    "object_names": [str(value) for value in group.get("object_names") or []],
                    "grasp_load_exception_asset_uids": [
                        str(value) for value in group.get("grasp_load_exception_asset_uids") or []
                    ],
                    "grasp_load_exception_types": [
                        str(value) for value in group.get("grasp_load_exception_types") or []
                    ],
                }
            )
    return rows


def _source_rotation_state(selected_count: int, excluded_count: int) -> str:
    if selected_count:
        return "available_for_unproven_requests"
    if excluded_count:
        return "exhausted_by_prior_memory"
    return "not_applicable"


def _mitigation_route(
    *,
    missing_assets: list[str],
    subkind_counts: dict[str, int],
    source_rotation_state: str,
) -> tuple[str, str, str, str]:
    if missing_assets:
        recommendation = "mitigate_missing_grasp_cache_before_retry"
        rationale = (
            "At least one exact-scene proof failed before collision masking because cached "
            "grasps could not be loaded for the requested asset."
        )
        if source_rotation_state == "available_for_unproven_requests":
            rationale += (
                " Source rotation still has selected unproven requests, but it should not "
                "be treated as a retry path for the missing-cache asset."
            )
        return ("grasp_cache_mitigation", "action_required", recommendation, rationale)
    if subkind_counts.get("zero_noncolliding_grasps"):
        return (
            "collision_or_pose_mitigation",
            "action_required",
            "investigate_zero_noncolliding_grasps",
            "Cached grasps loaded, but collision masking rejected every checked pose.",
        )
    if subkind_counts:
        return (
            "source_rotation",
            "action_required",
            "rotate_source_or_improve_grasp_policy",
            "Current grasp-feasibility evidence is not a missing-cache signature.",
        )
    return (
        "none",
        "not_applicable",
        "no_grasp_feasibility_signature_evidence",
        "No grouped grasp-feasibility signatures were present in prior or current proof results.",
    )


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
