#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.planner_proof_requests import (
    PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA,
    PLANNER_PROOF_REQUEST_SELECTION_SCHEMA,
    PLANNER_PROOF_RESULT_SUMMARY_SCHEMA,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate MolmoSpaces planner proof bundle runner artifacts."
    )
    parser.add_argument("path", type=Path, help="proof_bundle_run_manifest.json or output dir")
    parser.add_argument("--require-proof-outputs", action="store_true")
    parser.add_argument("--require-cleanup-rerun-output", action="store_true")
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
    )
    print(f"molmo-planner-proof-bundle-runner ok: {path}")


def _assert_runner_result(
    data: dict[str, Any],
    base: Path,
    *,
    require_proof_outputs: bool = False,
    require_cleanup_rerun_output: bool = False,
) -> None:
    assert data.get("schema") == PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA, data
    assert data.get("status") in {"dry_run", "probes_executed", "cleanup_rerun"}, data
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
        generated_count = _generated_fallback_request_count(proof_request_selection)
    else:
        generated_count = 0
    assert int(data.get("ready_request_count") or 0) + generated_count >= len(commands), data
    proof_result_summary = data.get("proof_result_summary") or {}
    if proof_result_summary:
        _assert_proof_result_summary(
            proof_result_summary,
            commands,
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


def _assert_runner_report(report_text: str) -> None:
    for heading in (
        "Planner Proof Bundle Runner",
        "Source Cleanup Artifact",
        "Proof Probe Commands",
        "Cleanup Rerun Command",
    ):
        assert heading in report_text, (heading, report_text[:500])


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
        if fallback_status == "generated":
            assert generated, fallback_generation
        if fallback_status == "exhausted":
            assert not generated, fallback_generation
            assert selection.get("fallback_required") is True, selection
        for item in generated:
            fallback = item.get("fallback_request") or {}
            for key in ("request_id", "object_id", "target_receptacle_id"):
                assert item.get(key), item
                assert str(item[key]) in report_text, (key, report_text[:500])
            assert fallback.get("source_request_id"), item
            assert str(fallback["source_request_id"]) in report_text, report_text[:500]
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


def _generated_fallback_request_count(selection: dict[str, Any]) -> int:
    fallback_generation = selection.get("fallback_generation") or {}
    if not isinstance(fallback_generation, dict):
        return 0
    return int(fallback_generation.get("generated_request_count") or 0)


def _assert_proof_result_summary(
    summary: dict[str, Any],
    commands: list[dict[str, Any]],
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
            assert str(view.get("path") or "") in report_text, (view, report_text[:500])
        for key in ("last_worker_stage", "stdout", "stderr"):
            value = str(item.get(key) or "")
            if value:
                assert value in report_text, (key, report_text[:500])
        worker_stage_events = item.get("worker_stage_events") or []
        assert int(item.get("worker_stage_event_count") or 0) == len(worker_stage_events), item
        for event in worker_stage_events:
            assert isinstance(event, dict), item
            for key in ("event", "stage"):
                value = str(event.get(key) or "")
                if value:
                    assert value in report_text, (event, report_text[:500])


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


def _has_blocker_code(item: dict[str, Any], code: str) -> bool:
    blockers = [*(item.get("blockers") or []), *(item.get("cleanup_binding_blockers") or [])]
    return any(
        isinstance(blocker, dict) and str(blocker.get("code") or "") == code for blocker in blockers
    )


if __name__ == "__main__":
    main()
