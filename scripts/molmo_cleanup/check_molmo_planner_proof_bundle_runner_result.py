#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

from roboclaws.household.planner_proof_requests import (
    PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA,
    PLANNER_PROOF_EXECUTION_HORIZON_SCHEMA,
)
from scripts.molmo_cleanup.planner_proof_bundle_result_checker import (
    assert_prior_proof_result_summary,
    assert_proof_result_summary,
)
from scripts.molmo_cleanup.planner_proof_bundle_selection_checker import (
    assert_proof_request_selection,
    assert_selection_requirements,
    generated_fallback_request_count,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate MolmoSpaces planner proof bundle runner artifacts."
    )
    parser.add_argument("path", type=Path, help="proof_bundle_run_manifest.json or output dir")
    parser.add_argument("--require-proof-outputs", action="store_true")
    parser.add_argument("--require-cleanup-rerun-output", action="store_true")
    parser.add_argument("--min-selected-requests", type=int)
    parser.add_argument("--max-selected-requests", type=int)
    parser.add_argument("--require-prior-covered-exclusion", action="store_true")
    parser.add_argument("--require-proof-execution-horizon", action="store_true")
    parser.add_argument("--require-proof-quality", action="store_true")
    parser.add_argument("--require-planner-backed-proof-min-steps", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = args.path / "proof_bundle_run_manifest.json" if args.path.is_dir() else args.path
    data = json.loads(path.read_text(encoding="utf-8"))
    _assert_runner_result(
        data,
        path.parent,
        require_proof_outputs=args.require_proof_outputs,
        require_cleanup_rerun_output=args.require_cleanup_rerun_output,
        min_selected_requests=args.min_selected_requests,
        max_selected_requests=args.max_selected_requests,
        require_prior_covered_exclusion=args.require_prior_covered_exclusion,
        require_proof_execution_horizon=args.require_proof_execution_horizon,
        require_proof_quality=args.require_proof_quality,
        planner_backed_proof_min_steps=args.require_planner_backed_proof_min_steps,
    )
    print(f"molmo-planner-proof-bundle-runner ok: {path}")


def _assert_runner_result(
    data: dict[str, Any],
    base: Path,
    *,
    require_proof_outputs: bool = False,
    require_cleanup_rerun_output: bool = False,
    min_selected_requests: int | None = None,
    max_selected_requests: int | None = None,
    require_prior_covered_exclusion: bool = False,
    require_proof_execution_horizon: bool = False,
    require_proof_quality: bool = False,
    planner_backed_proof_min_steps: int | None = None,
) -> None:
    assert data.get("schema") == PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA, data
    assert data.get("status") in {
        "dry_run",
        "probes_executed",
        "cleanup_rerun",
        "local_runtime_blocked",
    }, data
    assert int(data.get("proof_request_count") or 0) >= int(data.get("ready_request_count") or 0), (
        data
    )
    commands = data.get("commands") or []
    assert data.get("command_count") == len(commands), data
    assert data.get("cleanup_run_result"), data
    report = _resolve_path(base, str(data.get("report") or "report.html"))
    assert report.is_file(), report
    report_text = report.read_text(encoding="utf-8")
    _assert_runner_report(report_text)
    proof_execution_horizon = data.get("proof_execution_horizon") or {}
    if proof_execution_horizon:
        _assert_proof_execution_horizon(proof_execution_horizon, report_text)
    elif require_proof_execution_horizon:
        raise AssertionError("proof_execution_horizon is required")
    local_runtime_preflight = data.get("local_runtime_preflight") or {}
    if local_runtime_preflight:
        _assert_local_runtime_preflight(local_runtime_preflight, report_text)
    warmup = data.get("warmup") or {}
    if warmup:
        _assert_warmup(
            warmup,
            base,
            report_text,
            require_outputs=require_proof_outputs,
        )
    proof_request_selection = data.get("proof_request_selection") or {}
    if proof_request_selection:
        assert_proof_request_selection(proof_request_selection, commands, report_text)
        assert_selection_requirements(
            proof_request_selection,
            report_text,
            min_selected_requests=min_selected_requests,
            max_selected_requests=max_selected_requests,
            require_prior_covered_exclusion=require_prior_covered_exclusion,
        )
        generated_count = generated_fallback_request_count(proof_request_selection)
    else:
        assert not require_prior_covered_exclusion, data
        assert min_selected_requests in {None, 0}, data
        generated_count = 0
    assert int(data.get("ready_request_count") or 0) + generated_count >= len(commands), data
    proof_result_summary = data.get("proof_result_summary") or {}
    prior_proof_result_summary = data.get("prior_proof_result_summary") or {}
    decision = data.get("grasp_feasibility_mitigation_decision") or {}
    if decision:
        _assert_grasp_mitigation_decision(decision, report_text)
    grasp_cache_preflight = data.get("grasp_cache_availability_preflight") or {}
    if grasp_cache_preflight:
        _assert_grasp_cache_availability_preflight(grasp_cache_preflight, report_text)
    grasp_generation_preflight = data.get("grasp_cache_generation_preflight") or {}
    if grasp_generation_preflight:
        _assert_grasp_cache_generation_preflight(grasp_generation_preflight, report_text)
    if prior_proof_result_summary:
        assert_prior_proof_result_summary(prior_proof_result_summary, base, report_text)
    if proof_result_summary:
        assert_proof_result_summary(
            proof_result_summary,
            commands,
            base,
            report_text,
            require_outputs=require_proof_outputs,
            require_quality=require_proof_quality,
            planner_backed_min_steps=planner_backed_proof_min_steps,
        )
    elif require_proof_outputs:
        raise AssertionError("proof_result_summary is required with --require-proof-outputs")
    for item in commands:
        _assert_command(item, base, report_text, require_proof_outputs=require_proof_outputs)
    cleanup_command = data.get("cleanup_command") or []
    if cleanup_command:
        command_text = " ".join(str(part) for part in cleanup_command)
        assert command_text in report_text, command_text
    cleanup_rerun = data.get("cleanup_rerun") or {}
    if data.get("status") == "cleanup_rerun" or cleanup_rerun or require_cleanup_rerun_output:
        _assert_cleanup_rerun(
            cleanup_rerun,
            base,
            report_text,
            require_outputs=require_cleanup_rerun_output or data.get("status") == "cleanup_rerun",
        )
    if data.get("status") == "local_runtime_blocked":
        assert local_runtime_preflight.get("status") == "blocked", local_runtime_preflight


def _assert_runner_report(report_text: str) -> None:
    for heading in (
        "Planner Proof Bundle Runner",
        "Source Cleanup Artifact",
        "Proof Probe Commands",
        "Cleanup Rerun Command",
    ):
        assert heading in report_text, (heading, report_text[:500])


def _assert_proof_execution_horizon(horizon: dict[str, Any], report_text: str) -> None:
    assert horizon.get("schema") == PLANNER_PROOF_EXECUTION_HORIZON_SCHEMA, horizon
    assert horizon.get("status") in {"aligned", "command_steps_below_coverage_horizon"}, horizon
    assert int(horizon.get("command_steps") or 0) >= 0, horizon
    assert int(horizon.get("prior_covered_min_proof_steps") or 0) >= 1, horizon
    assert str(horizon.get("command_quality_target") or "") in {
        "unknown",
        "one_step_motion",
        "multi_step_motion",
    }, horizon
    assert str(horizon.get("prior_covered_quality_floor") or "") in {
        "one_step_motion",
        "multi_step_motion",
    }, horizon
    assert "Proof Execution Horizon" in report_text, report_text[:500]
    for value in (
        horizon.get("status"),
        horizon.get("command_quality_target"),
        horizon.get("prior_covered_quality_floor"),
    ):
        _assert_report_contains(str(value), report_text)
    for blocker in horizon.get("blockers") or []:
        if not isinstance(blocker, dict):
            continue
        _assert_report_contains(str(blocker.get("code") or ""), report_text)
        _assert_report_contains(str(blocker.get("message") or ""), report_text)


def _assert_local_runtime_preflight(preflight: dict[str, Any], report_text: str) -> None:
    assert preflight.get("schema") == "planner_proof_bundle_local_runtime_preflight_v1", preflight
    assert preflight.get("status") in {"ready", "blocked", "not_checked"}, preflight
    assert "Local Runtime Preflight" in report_text, report_text[:500]
    assert str(preflight.get("status") or "") in report_text, report_text[:500]
    python_executable = str(preflight.get("python_executable") or "")
    if python_executable:
        _assert_report_contains(python_executable, report_text)
    for check in preflight.get("checks") or []:
        assert isinstance(check, dict), preflight
        for key in ("name", "status"):
            value = str(check.get(key) or "")
            if value:
                _assert_report_contains(value, report_text, key)
        command = " ".join(str(part) for part in check.get("command") or [])
        if command:
            _assert_report_contains(command, report_text, command)
    for blocker in preflight.get("blockers") or []:
        assert isinstance(blocker, dict), preflight
        for key in ("code", "message"):
            value = str(blocker.get(key) or "")
            if value:
                _assert_report_contains(value, report_text, key)


def _assert_report_contains(value: str, report_text: str, context: Any = "") -> None:
    assert value in report_text or html.escape(value) in report_text, (
        context or value,
        report_text[:500],
    )


def _assert_warmup(
    warmup: dict[str, Any],
    base: Path,
    report_text: str,
    *,
    require_outputs: bool,
) -> None:
    for key in ("output_dir", "run_result", "report", "command"):
        assert warmup.get(key), warmup
    command = warmup.get("command") or []
    assert isinstance(command, list) and command, warmup
    assert "--output-dir" in command, command
    assert "--probe-mode" in command, command
    assert "config_import" in command, command
    assert "--torch-extensions-dir" in command, command
    command_text = " ".join(str(part) for part in command)
    assert "RBY1M/CuRobo Warmup" in report_text, report_text[:500]
    assert command_text in report_text, command_text
    for key in ("output_dir", "run_result", "report"):
        assert str(warmup[key]) in report_text, (key, report_text[:500])
    if require_outputs:
        run_result = _resolve_path(base, str(warmup["run_result"]))
        proof_report = _resolve_path(base, str(warmup["report"]))
        assert run_result.is_file(), run_result
        assert proof_report.is_file(), proof_report


def _assert_command(
    item: dict[str, Any],
    base: Path,
    report_text: str,
    *,
    require_proof_outputs: bool,
) -> None:
    for key in (
        "request_id",
        "object_id",
        "target_receptacle_id",
        "output_dir",
        "run_result",
        "report",
    ):
        assert item.get(key), item
    command = item.get("command") or []
    assert isinstance(command, list) and command, item
    command_text = " ".join(str(part) for part in command)
    assert "--output-dir" in command, command
    assert "--cleanup-object-id" in command, command
    semantic_subphases = item.get("semantic_subphases") or []
    if semantic_subphases:
        assert "Semantic subphases" in report_text, report_text[:500]
        for subphase in semantic_subphases:
            if not isinstance(subphase, dict):
                continue
            for key in ("phase", "label", "detail"):
                value = str(subphase.get(key) or "")
                if value:
                    _assert_report_contains(value, report_text, key)
    for value in (
        item["request_id"],
        item["object_id"],
        item["target_receptacle_id"],
        item["run_result"],
        item["report"],
    ):
        assert str(value) in report_text, (value, report_text[:500])
    assert command_text in report_text, command_text
    if require_proof_outputs:
        run_result = _resolve_path(base, str(item["run_result"]))
        proof_report = _resolve_path(base, str(item["report"]))
        assert run_result.is_file(), run_result
        assert proof_report.is_file(), proof_report


def _assert_grasp_mitigation_decision(
    decision: dict[str, Any],
    report_text: str,
) -> None:
    assert decision.get("schema") == "planner_grasp_feasibility_mitigation_decision_v1", decision
    assert decision.get("status") in {"not_applicable", "action_required"}, decision
    assert decision.get("primary_route"), decision
    assert decision.get("recommendation"), decision
    assert "Grasp Feasibility Mitigation Decision" in report_text, report_text[:500]
    for value in [
        decision.get("status"),
        decision.get("primary_route"),
        decision.get("recommendation"),
        decision.get("source_rotation_state"),
        *(decision.get("missing_grasp_asset_uids") or []),
        *(decision.get("grasp_load_exception_types") or []),
    ]:
        if value:
            assert str(value) in report_text, (decision, report_text[:500])
    for item in decision.get("signature_groups") or []:
        assert isinstance(item, dict), decision
        for value in [
            item.get("source"),
            item.get("subkind"),
            item.get("summary"),
            *(item.get("request_ids") or []),
            *(item.get("object_names") or []),
            *(item.get("grasp_load_exception_asset_uids") or []),
        ]:
            if value:
                assert str(value) in report_text, (item, report_text[:500])


def _assert_grasp_cache_availability_preflight(
    preflight: dict[str, Any],
    report_text: str,
) -> None:
    assert preflight.get("schema") == "planner_grasp_cache_availability_preflight_v1", preflight
    assert preflight.get("status") in {"ready", "missing_cache", "not_applicable"}, preflight
    assert "Grasp Cache Availability Preflight" in report_text, report_text[:500]
    for value in [
        preflight.get("status"),
        preflight.get("assets_dir"),
        preflight.get("assets_dir_resolved"),
        preflight.get("assets_dir_source"),
        preflight.get("upstream_loader"),
        preflight.get("mitigation_recommendation"),
        *(preflight.get("missing_grasp_asset_uids") or []),
        *(preflight.get("cache_ready_asset_uids") or []),
        *(preflight.get("cache_missing_asset_uids") or []),
    ]:
        if value:
            _assert_report_contains(str(value), report_text, preflight)
    assets = preflight.get("assets") or []
    assert int(preflight.get("asset_count") or 0) == len(assets), preflight
    ready_count = sum(1 for item in assets if str(item.get("status") or "") == "ready")
    missing_count = sum(1 for item in assets if str(item.get("status") or "") == "missing_cache")
    assert int(preflight.get("ready_asset_count") or 0) == ready_count, preflight
    assert int(preflight.get("missing_cache_asset_count") or 0) == missing_count, preflight
    for asset in assets:
        assert isinstance(asset, dict), preflight
        assert asset.get("status") in {"ready", "missing_cache"}, asset
        for value in (
            asset.get("asset_uid"),
            asset.get("status"),
            asset.get("loader_file_status"),
            asset.get("object_asset_status"),
        ):
            if value:
                _assert_report_contains(str(value), report_text, asset)
        candidate_files = asset.get("candidate_grasp_files") or []
        assert len(candidate_files) == 3, asset
        for probe in [*candidate_files, *(asset.get("folder_probe_files") or [])]:
            assert isinstance(probe, dict), asset
            for key in (
                "source",
                "loader_role",
                "relative_path",
                "resolved_path",
                "validation_status",
                "transform_count",
            ):
                value = str(probe.get(key) or "")
                if value:
                    _assert_report_contains(value, report_text, probe)
        for object_file in asset.get("object_asset_files") or []:
            assert isinstance(object_file, dict), asset
            for key in ("kind", "relative_path", "resolved_path"):
                value = str(object_file.get(key) or "")
                if value:
                    _assert_report_contains(value, report_text, object_file)


def _assert_grasp_cache_generation_preflight(
    preflight: dict[str, Any],
    report_text: str,
) -> None:
    assert preflight.get("schema") == "planner_grasp_cache_generation_preflight_v1", preflight
    assert preflight.get("status") in {"ready", "blocked", "not_applicable"}, preflight
    if preflight.get("status") == "not_applicable":
        return
    assert "Grasp Cache Generation Preflight" in report_text, report_text[:500]
    for value in [
        preflight.get("status"),
        preflight.get("molmospaces_python"),
        preflight.get("molmospaces_root"),
        preflight.get("assets_dir"),
        preflight.get("objects_list_path"),
        preflight.get("working_dir"),
        preflight.get("mitigation_recommendation"),
    ]:
        if value:
            _assert_report_contains(str(value), report_text, preflight)
    assets = preflight.get("assets") or []
    assert int(preflight.get("asset_count") or 0) == len(assets), preflight
    for asset in assets:
        assert isinstance(asset, dict), preflight
        for key in (
            "asset_uid",
            "object_xml",
            "generated_npz_path",
            "cache_target_resolved_path",
        ):
            value = str(asset.get(key) or "")
            if value:
                _assert_report_contains(value, report_text, asset)
    checks = preflight.get("checks") or []
    for check in checks:
        assert isinstance(check, dict), preflight
        for key in ("name", "status", "code", "message"):
            value = str(check.get(key) or "")
            if value:
                _assert_report_contains(value, report_text, check)
        path_value = str(check.get("path") or check.get("resolved_path") or "")
        if path_value:
            _assert_report_contains(path_value, report_text, check)
    blockers = preflight.get("blockers") or []
    assert int(preflight.get("blocker_count") or 0) == len(blockers), preflight
    if preflight.get("status") == "blocked":
        assert blockers, preflight
    for blocker in blockers:
        assert isinstance(blocker, dict), preflight
        for key in ("code", "name", "message"):
            value = str(blocker.get(key) or "")
            if value:
                _assert_report_contains(value, report_text, blocker)


def _assert_cleanup_rerun(
    cleanup_rerun: dict[str, Any],
    base: Path,
    report_text: str,
    *,
    require_outputs: bool,
) -> None:
    for key in ("output_dir", "run_result", "report"):
        assert cleanup_rerun.get(key), cleanup_rerun
        assert str(cleanup_rerun[key]) in report_text, (key, report_text[:500])
    assert "Cleanup Rerun Artifact" in report_text, report_text[:500]
    if require_outputs:
        output_dir = _resolve_path(base, str(cleanup_rerun["output_dir"]))
        run_result = _resolve_path(base, str(cleanup_rerun["run_result"]))
        report = _resolve_path(base, str(cleanup_rerun["report"]))
        assert output_dir.is_dir(), output_dir
        assert run_result.is_file(), run_result
        assert report.is_file(), report


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or path.exists():
        return path
    return base / path


if __name__ == "__main__":
    main()
