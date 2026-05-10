#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.planner_proof_requests import (
    PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA,
    PLANNER_PROOF_REQUEST_SELECTION_SCHEMA,
    PLANNER_PROOF_RESULT_SUMMARY_SCHEMA,
)
from roboclaws.molmo_cleanup.planner_task_feasibility import grasp_feasibility_signature_counts


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
        _assert_proof_request_selection(proof_request_selection, commands, report_text)
        _assert_selection_requirements(
            proof_request_selection,
            report_text,
            min_selected_requests=min_selected_requests,
            max_selected_requests=max_selected_requests,
            require_prior_covered_exclusion=require_prior_covered_exclusion,
        )
        generated_count = _generated_fallback_request_count(proof_request_selection)
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
    if prior_proof_result_summary:
        _assert_prior_proof_result_summary(prior_proof_result_summary, base, report_text)
    if proof_result_summary:
        _assert_proof_result_summary(
            proof_result_summary,
            commands,
            base,
            report_text,
            require_outputs=require_proof_outputs,
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


def _assert_proof_request_selection(
    selection: dict[str, Any],
    commands: list[dict[str, Any]],
    report_text: str,
) -> None:
    assert selection.get("schema") == PLANNER_PROOF_REQUEST_SELECTION_SCHEMA, selection
    selected_ids = [str(item) for item in selection.get("selected_request_ids") or []]
    command_ids = [str(item.get("request_id") or "") for item in commands]
    assert selected_ids == command_ids, selection
    assert int(selection.get("selected_count") or 0) == len(command_ids), selection
    assert "Proof Request Selection" in report_text, report_text[:500]
    assert "Generated Fallback Requests" in report_text, report_text[:500]
    for item in selection.get("selected_requests") or []:
        for key in ("request_id", "object_id", "target_receptacle_id"):
            assert item.get(key), item
            assert str(item[key]) in report_text, (key, report_text[:500])
    for item in selection.get("excluded_requests") or []:
        for key in ("request_id", "reason", "prior_task_feasibility_status"):
            assert item.get(key), item
            assert str(item[key]) in report_text, (key, report_text[:500])
        for key in (
            "prior_task_feasibility_blocker_kind",
            "prior_task_feasibility_blocker_summary",
            "prior_result_match_kind",
        ):
            if item.get(key):
                assert str(item[key]) in report_text, (key, report_text[:500])
    target_feasibility_blockers = selection.get("target_feasibility_blockers") or []
    if "target_feasibility_blocker_count" in selection:
        assert int(selection.get("target_feasibility_blocker_count") or 0) == len(
            target_feasibility_blockers
        ), selection
    grasp_feasibility_blockers = selection.get("grasp_feasibility_blockers") or []
    if "grasp_feasibility_blocker_count" in selection:
        assert int(selection.get("grasp_feasibility_blocker_count") or 0) == len(
            grasp_feasibility_blockers
        ), selection
    if target_feasibility_blockers:
        assert "Target Feasibility Blockers" in report_text, report_text[:500]
    if grasp_feasibility_blockers:
        assert "Grasp Feasibility Blockers" in report_text, report_text[:500]
        assert "Grasp Feasibility Blocker Matrix" in report_text, report_text[:500]
    for item in target_feasibility_blockers:
        for key in ("kind", "source_request_id", "reason", "prior_task_feasibility_status"):
            assert item.get(key), item
            assert str(item[key]) in report_text, (key, report_text[:500])
        for key in (
            "object_id",
            "target_receptacle_id",
            "object_alias",
            "target_alias",
            "derived_from",
            "prior_report",
            "last_worker_stage",
            "prior_task_feasibility_blocker_kind",
            "prior_task_feasibility_blocker_summary",
            "prior_result_match_kind",
        ):
            if item.get(key):
                assert str(item[key]) in report_text, (key, report_text[:500])
    for item in grasp_feasibility_blockers:
        for key in ("kind", "source_request_id", "prior_task_feasibility_blocker_summary"):
            assert item.get(key), item
            assert str(item[key]) in report_text, (key, report_text[:500])
    fallback_generation = selection.get("fallback_generation") or {}
    if fallback_generation:
        fallback_status = str(fallback_generation.get("status") or "")
        assert fallback_status in {"disabled", "not_required", "generated", "exhausted"}, (
            fallback_generation
        )
        assert fallback_status in report_text, (fallback_status, report_text[:500])
        generated = fallback_generation.get("generated_requests") or []
        filtered_aliases = fallback_generation.get("filtered_aliases") or []
        discovered_aliases = fallback_generation.get("discovered_aliases") or []
        filtered_pairs = fallback_generation.get("filtered_pairs") or []
        normalized_aliases = fallback_generation.get("normalized_aliases") or []
        exhaustion_blockers = fallback_generation.get("exhaustion_blockers") or []
        assert int(selection.get("generated_fallback_request_count") or 0) == len(generated), (
            selection
        )
        assert int(fallback_generation.get("discovered_alias_count") or 0) == len(
            discovered_aliases
        ), fallback_generation
        assert int(fallback_generation.get("filtered_alias_count") or 0) == len(filtered_aliases), (
            fallback_generation
        )
        assert int(fallback_generation.get("filtered_pair_count") or 0) == len(filtered_pairs), (
            fallback_generation
        )
        assert int(fallback_generation.get("normalized_alias_count") or 0) == len(
            normalized_aliases
        ), fallback_generation
        assert int(fallback_generation.get("exhaustion_blocker_count") or 0) == len(
            exhaustion_blockers
        ), fallback_generation
        if fallback_status == "generated":
            assert generated, fallback_generation
        if fallback_status == "exhausted":
            assert not generated, fallback_generation
            if not selected_ids:
                assert selection.get("fallback_required") is True, selection
            assert exhaustion_blockers, fallback_generation
            assert "Fallback Exhaustion Blockers" in report_text, report_text[:500]
        for item in generated:
            fallback = item.get("fallback_request") or {}
            for key in ("request_id", "object_id", "target_receptacle_id"):
                assert item.get(key), item
                assert str(item[key]) in report_text, (key, report_text[:500])
            assert fallback.get("source_request_id"), item
            assert str(fallback["source_request_id"]) in report_text, report_text[:500]
            for key in (
                "prior_task_feasibility_blocker_kind",
                "prior_task_feasibility_blocker_summary",
                "prior_result_match_kind",
            ):
                if fallback.get(key):
                    assert str(fallback[key]) in report_text, (key, report_text[:500])
            args = item.get("planner_probe_args") or {}
            for key in (
                "--cleanup-planner-object-id",
                "--cleanup-planner-target-receptacle-id",
            ):
                value = str(args.get(key) or "")
                if value:
                    assert value in report_text, (key, report_text[:500])
        for item in discovered_aliases:
            for key in ("source_request_id", "axis", "alias", "derived_from", "reason"):
                assert item.get(key), item
                assert str(item[key]) in report_text, (key, report_text[:500])
        for item in filtered_aliases:
            for key in ("source_request_id", "axis", "alias", "reason"):
                assert item.get(key), item
                assert str(item[key]) in report_text, (key, report_text[:500])
        for item in filtered_pairs:
            for key in (
                "source_request_id",
                "object_alias",
                "target_alias",
                "derived_from",
                "reason",
            ):
                assert item.get(key), item
                assert str(item[key]) in report_text, (key, report_text[:500])
            for key in ("prior_report", "last_worker_stage"):
                if item.get(key):
                    assert str(item[key]) in report_text, (key, report_text[:500])
            for key in (
                "prior_task_feasibility_blocker_kind",
                "prior_task_feasibility_blocker_summary",
                "prior_result_match_kind",
            ):
                if item.get(key):
                    assert str(item[key]) in report_text, (key, report_text[:500])
        for item in exhaustion_blockers:
            for key in ("code", "message"):
                assert item.get(key), item
                assert str(item[key]) in report_text, (key, report_text[:500])
        for item in normalized_aliases:
            for key in ("alias", "normalized_alias", "reason"):
                assert item.get(key), item
                assert str(item[key]) in report_text, (key, report_text[:500])


def _assert_selection_requirements(
    selection: dict[str, Any],
    report_text: str,
    *,
    min_selected_requests: int | None,
    max_selected_requests: int | None,
    require_prior_covered_exclusion: bool,
) -> None:
    selected_count = int(selection.get("selected_count") or 0)
    if min_selected_requests is not None:
        assert selected_count >= min_selected_requests, selection
    if max_selected_requests is not None:
        assert selected_count <= max_selected_requests, selection
    if not require_prior_covered_exclusion:
        return
    excluded = selection.get("excluded_requests") or []
    covered = [
        item
        for item in excluded
        if isinstance(item, dict) and item.get("reason") == "prior_planner_proof_covered"
    ]
    assert covered, selection
    assert int(selection.get("covered_request_count") or 0) == len(covered), selection
    assert "prior_planner_proof_covered" in report_text, report_text[:500]


def _generated_fallback_request_count(selection: dict[str, Any]) -> int:
    fallback_generation = selection.get("fallback_generation") or {}
    if not isinstance(fallback_generation, dict):
        return 0
    return int(fallback_generation.get("generated_request_count") or 0)


def _assert_proof_result_summary(
    summary: dict[str, Any],
    commands: list[dict[str, Any]],
    base: Path,
    report_text: str,
    *,
    require_outputs: bool,
) -> None:
    assert summary.get("schema") == PLANNER_PROOF_RESULT_SUMMARY_SCHEMA, summary
    assert int(summary.get("expected_count") or 0) == len(commands), summary
    results = summary.get("results") or []
    assert len(results) == len(commands), summary
    assert "Proof Probe Results" in report_text, report_text[:500]
    if require_outputs:
        assert int(summary.get("result_count") or 0) == len(commands), summary
    timeout_count = sum(1 for item in results if _has_blocker_code(item, "timeout"))
    assert int(summary.get("timeout_count") or 0) == timeout_count, summary
    if timeout_count:
        assert "Timeouts" in report_text, report_text[:500]
    rby1m_config_import_timeout_count = sum(
        1
        for item in results
        if _has_blocker_code(item, "timeout")
        and item.get("last_worker_stage") == "rby1m_config_import"
    )
    assert (
        int(summary.get("rby1m_config_import_timeout_count") or 0)
        == rby1m_config_import_timeout_count
    ), summary
    _assert_grasp_signature_counts(summary, results, report_text)
    for item in results:
        for key in ("request_id", "status", "task_feasibility_status", "run_result", "report"):
            assert item.get(key), item
            assert str(item[key]) in report_text, (key, report_text[:500])
        assert item.get("task_feasibility_status") in {
            "not_run",
            "not_reached",
            "ready",
            "binding_not_promoted",
            "blocked",
            "unknown",
        }, item
        for blocker in [
            *(item.get("blockers") or []),
            *(item.get("cleanup_binding_blockers") or []),
        ]:
            code = str(blocker.get("code") or "")
            if code:
                assert code in report_text, (code, report_text[:500])
        for view in item.get("views") or []:
            _assert_report_view_src(view, base, report_text)
        for key in ("last_worker_stage", "stdout", "stderr"):
            value = str(item.get(key) or "")
            if value:
                assert value in report_text, (key, report_text[:500])
        blocker_kind = str(item.get("task_feasibility_blocker_kind") or "")
        if blocker_kind:
            assert "Task feasibility blocker" in report_text, report_text[:500]
            assert blocker_kind in report_text, ("task_feasibility_blocker_kind", report_text[:500])
        blocker_summary = str(item.get("task_feasibility_blocker_summary") or "")
        if blocker_summary:
            assert blocker_summary in report_text, (
                "task_feasibility_blocker_summary",
                report_text[:500],
            )
        sampler_adapter = item.get("cleanup_task_sampler_adapter") or {}
        robot_placement_profile = item.get("task_sampler_robot_placement_profile") or {}
        if robot_placement_profile:
            assert "Robot placement profile" in report_text, report_text[:500]
            for key in ("profile",):
                value = str(robot_placement_profile.get(key) or "")
                if value:
                    assert value in report_text, (key, report_text[:500])
            overrides = robot_placement_profile.get("place_robot_near_overrides") or {}
            max_tries = str(overrides.get("max_tries") or "")
            if max_tries:
                assert max_tries in report_text, ("place_robot_near_overrides", report_text[:500])
        if sampler_adapter:
            assert "Exact sampler adapter applied" in report_text, report_text[:500]
            for key in ("planner_object_id", "planner_target_receptacle_id", "task_sampler_class"):
                value = str(sampler_adapter.get(key) or "")
                if value:
                    assert value in report_text, (key, report_text[:500])
            pickup_binding = sampler_adapter.get("exact_pickup_candidate_binding") or {}
            if pickup_binding:
                assert "Exact pickup candidate action" in report_text, report_text[:500]
                if pickup_binding.get("retry_budget") is not None:
                    assert "Exact pickup retry budget" in report_text, report_text[:500]
                for key in ("planner_object_id", "action"):
                    value = str(pickup_binding.get(key) or "")
                    if value:
                        assert value in report_text, (key, report_text[:500])
        cleanup_task_config = item.get("cleanup_task_config") or {}
        config_blockers = cleanup_task_config.get("blockers") or []
        if config_blockers:
            assert "Exact task config blockers" in report_text, report_text[:500]
            for blocker in config_blockers:
                value = str(blocker.get("code") or "")
                if value:
                    assert value in report_text, (value, report_text[:500])
        task_sampler_failure = item.get("task_sampler_failure_diagnostics") or {}
        if task_sampler_failure:
            placement_failure_keys = ("robot_placement_failure_count", "asset_failure_count")
            if any(_positive_int(task_sampler_failure.get(key)) for key in placement_failure_keys):
                assert "Task sampler placement failures" in report_text, report_text[:500]
                for key in placement_failure_keys:
                    value = str(task_sampler_failure.get(key) or "")
                    if value and value != "0":
                        assert value in report_text, (key, report_text[:500])
            for key in ("robot_placement_attempt_count",):
                value = str(task_sampler_failure.get(key) or "")
                if value and value != "0":
                    assert value in report_text, (key, report_text[:500])
            grasp_failures = task_sampler_failure.get("grasp_failures") or []
            if grasp_failures:
                assert "Post-placement grasp failures" in report_text, report_text[:500]
                assert "Post-Placement Rejection Views" in report_text, report_text[:500]
                if "candidate_effective_removal_count" in task_sampler_failure:
                    assert "Post-placement effective removals" in report_text, report_text[:500]
                if "candidate_name_miss_count" in task_sampler_failure:
                    assert "Post-placement candidate name misses" in report_text, report_text[:500]
                value = str(task_sampler_failure.get("grasp_failure_count") or "")
                if value:
                    assert value in report_text, ("grasp_failure_count", report_text[:500])
            if task_sampler_failure.get("grasp_load_attempts") or task_sampler_failure.get(
                "grasp_collision_checks"
            ):
                assert "Grasp collision checks" in report_text, report_text[:500]
                last_check = task_sampler_failure.get("last_grasp_collision_check") or {}
                last_load = task_sampler_failure.get("last_grasp_load_attempt") or {}
                for key in ("asset_uid", "noncolliding_grasp_count", "cached_grasp_count"):
                    value = str(last_check.get(key) or last_load.get(key) or "")
                    if value:
                        assert value in report_text, (key, report_text[:500])
            last_scene = task_sampler_failure.get("last_placement_scene_diagnostic") or {}
            if last_scene:
                assert "Placement free-space fraction" in report_text, report_text[:500]
                value = str(last_scene.get("valid_neighborhood_fraction") or "")
                if value:
                    assert value in report_text, (
                        "last_placement_scene_diagnostic",
                        report_text[:500],
                    )
            last_failure = task_sampler_failure.get("last_robot_placement_failure") or {}
            value = str(last_failure.get("message") or "")
            if value:
                assert value in report_text, ("last_robot_placement_failure", report_text[:500])
        worker_stage_events = item.get("worker_stage_events") or []
        assert int(item.get("worker_stage_event_count") or 0) == len(worker_stage_events), item
        for event in worker_stage_events:
            assert isinstance(event, dict), item
            for key in ("event", "stage"):
                value = str(event.get(key) or "")
                if value:
                    assert value in report_text, (event, report_text[:500])


def _assert_prior_proof_result_summary(
    summary: dict[str, Any],
    base: Path,
    report_text: str,
) -> None:
    schema = str(summary.get("schema") or "")
    assert schema, summary
    results = summary.get("results") or []
    assert isinstance(results, list), summary
    assert "Prior Proof Evidence" in report_text, report_text[:500]
    _assert_grasp_signature_counts(summary, results, report_text)
    for item in results:
        assert isinstance(item, dict), summary
        for key in ("request_id", "status", "task_feasibility_status", "run_result", "report"):
            value = str(item.get(key) or "")
            if value:
                assert value in report_text, (key, report_text[:500])
        for view in item.get("views") or []:
            _assert_report_view_src(view, base, report_text)
        blocker_summary = str(item.get("task_feasibility_blocker_summary") or "")
        if blocker_summary:
            assert blocker_summary in report_text, (
                "task_feasibility_blocker_summary",
                report_text[:500],
            )
        blocker_kind = str(item.get("task_feasibility_blocker_kind") or "")
        if blocker_kind:
            assert blocker_kind in report_text, (
                "task_feasibility_blocker_kind",
                report_text[:500],
            )


def _assert_grasp_signature_counts(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    report_text: str,
) -> None:
    grasp_signature_counts = summary.get("grasp_feasibility_signature_counts") or []
    if grasp_signature_counts:
        assert int(summary.get("grasp_feasibility_signature_count") or 0) == len(
            grasp_signature_counts
        ), summary
    else:
        grasp_signature_counts = grasp_feasibility_signature_counts(results)
    if not grasp_signature_counts:
        return
    assert "Grasp Feasibility Signature Matrix" in report_text, report_text[:500]
    assert "Effective removals" in report_text, report_text[:500]
    for signature in grasp_signature_counts:
        assert signature.get("pattern_key"), signature
        assert int(signature.get("count") or 0) > 0, signature
        for value in [
            signature.get("summary"),
            signature.get("subkind"),
            *(signature.get("request_ids") or []),
            *(signature.get("object_names") or []),
            *(signature.get("grasp_load_exception_asset_uids") or []),
            *(signature.get("grasp_load_exception_types") or []),
        ]:
            if value:
                assert str(value) in report_text, (signature, report_text[:500])


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


def _assert_report_view_src(view: dict[str, Any], base: Path, report_text: str) -> None:
    path_text = str(view.get("path") or "")
    assert path_text, view
    src = _report_asset_src(path_text, base)
    expected = f'src="{html.escape(src)}"'
    assert expected in report_text, (expected, report_text[:500])
    if _resolve_path(base, path_text).exists():
        assert _resolve_path(base, src).is_file(), src


def _report_asset_src(path_text: str, base: Path) -> str:
    if path_text.startswith(("http://", "https://", "data:")):
        return path_text
    candidate = Path(path_text)
    try:
        if candidate.is_absolute():
            asset_path = candidate
        elif candidate.exists():
            asset_path = candidate.resolve()
        elif (base / candidate).exists():
            asset_path = (base / candidate).resolve()
        else:
            return path_text
        return Path(os.path.relpath(asset_path, base.resolve())).as_posix()
    except OSError:
        return path_text


def _has_blocker_code(item: dict[str, Any], code: str) -> bool:
    blockers = [*(item.get("blockers") or []), *(item.get("cleanup_binding_blockers") or [])]
    return any(
        isinstance(blocker, dict) and str(blocker.get("code") or "") == code for blocker in blockers
    )


def _positive_int(value: Any) -> bool:
    try:
        return int(value or 0) > 0
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    main()
