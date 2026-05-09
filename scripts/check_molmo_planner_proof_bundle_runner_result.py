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
    assert int(data.get("ready_request_count") or 0) >= len(commands), data
    assert data.get("cleanup_run_result"), data
    report = _resolve_path(base, str(data.get("report") or "report.html"))
    assert report.is_file(), report
    report_text = report.read_text(encoding="utf-8")
    _assert_runner_report(report_text)
    proof_request_selection = data.get("proof_request_selection") or {}
    if proof_request_selection:
        _assert_proof_request_selection(proof_request_selection, commands, report_text)
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
    for item in selection.get("selected_requests") or []:
        for key in ("request_id", "object_id", "target_receptacle_id"):
            assert item.get(key), item
            assert str(item[key]) in report_text, (key, report_text[:500])
    for item in selection.get("excluded_requests") or []:
        for key in ("request_id", "reason", "prior_task_feasibility_status"):
            assert item.get(key), item
            assert str(item[key]) in report_text, (key, report_text[:500])


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
