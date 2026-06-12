#!/usr/bin/env python3
"""Dry-run and preflight the private OpenAI Agents SDK speedup matrix."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

FORBIDDEN_PRIVACY_KEYS = {
    "api_key",
    "compact_continuation_state",
    "credentials",
    "final_output",
    "function_input",
    "function_output",
    "full_tool_payload",
    "instructions",
    "last_agent",
    "model_output",
    "model_text",
    "output_text",
    "private_evaluator_truth",
    "private_manifest",
    "private_target_truth",
    "raw_prompt",
    "tool_payload_body",
}
FORBIDDEN_PRIVACY_MARKERS = {
    "bearer ",
    "compact_continuation_state:",
    "private_evaluator_truth",
    "private_manifest",
    "private_target_truth",
    "raw_prompt",
    "sk-",
    "tool_payload_body",
}
SAFE_SCAN_GLOBS = (
    "live_status.json",
    "live_timing.json",
    "openai-agents-events*.jsonl",
    "openai-agents-spans*.jsonl",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the no-provider Group 0 preflight packet for private "
            "openai-agents-live speedup experiments."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--offline-preflight", action="store_true")
    parser.add_argument("--privacy-gate", action="store_true")
    parser.add_argument("--decision-packet", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = _load_manifest(args.manifest)
    if manifest is None:
        return 1

    run_all = not (args.dry_run or args.offline_preflight or args.privacy_gate)
    dry_run = _dry_run_packet(manifest)
    if args.dry_run or run_all:
        _print_dry_run(dry_run)

    if not (args.offline_preflight or args.privacy_gate or run_all or args.decision_packet):
        return 0

    packet = _decision_packet(manifest, dry_run=dry_run)
    if args.privacy_gate or args.offline_preflight or run_all or args.decision_packet:
        _apply_privacy_gate(packet)
    if args.offline_preflight or run_all or args.decision_packet:
        _apply_offline_preflight(packet)
        _apply_quality_gate(packet)
        _apply_reducible_bucket_reports(packet)
    _finalize_packet(packet)

    if args.decision_packet:
        args.decision_packet.parent.mkdir(parents=True, exist_ok=True)
        args.decision_packet.write_text(
            json.dumps(packet, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"decision packet: {args.decision_packet}")

    failed = [row for row in packet["rows"] if row["status"] in {"rejected", "blocked"}]
    if failed:
        for row in failed:
            print(
                f"error: {row['row_id']} {row['status']}: {'; '.join(row.get('reasons') or [])}",
                file=sys.stderr,
            )
        return 1
    return 0


def _load_manifest(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: could not read matrix manifest {path}: {exc}", file=sys.stderr)
        return None
    if not isinstance(payload, dict):
        print("error: matrix manifest must be a JSON object", file=sys.stderr)
        return None
    if payload.get("schema") != "agent_sdk_speedup_matrix_v1":
        print("error: unsupported matrix manifest schema", file=sys.stderr)
        return None
    return payload


def _dry_run_packet(manifest: dict[str, Any]) -> dict[str, Any]:
    rows = _rows(manifest)
    budget_caps = _dict(manifest.get("budget_caps"))
    supported_rows = [row for row in rows if not row.get("unsupported_reason")]
    unsupported_rows = [row for row in rows if row.get("unsupported_reason")]
    planned_live_runs = sum(1 for row in supported_rows if bool(row.get("provider_calls")))
    return {
        "schema": "agent_sdk_speedup_matrix_dry_run_v1",
        "budget_caps": budget_caps,
        "concurrency": _int_or_none(budget_caps.get("concurrency")) or 1,
        "racing_multiplier": _float_or_none(budget_caps.get("racing_multiplier")) or 1.0,
        "planned_row_count": len(rows),
        "supported_row_count": len(supported_rows),
        "unsupported_row_count": len(unsupported_rows),
        "planned_live_run_count": planned_live_runs,
        "provider_calls_planned": planned_live_runs > 0,
        "candidate_groups": manifest.get("candidate_groups") or [],
        "rows": [_dry_run_row(row) for row in rows],
        "unsupported_rows": [_dry_run_row(row) for row in unsupported_rows],
    }


def _print_dry_run(packet: dict[str, Any]) -> None:
    print("Agent SDK speedup matrix dry-run")
    print(f"rows: {packet['planned_row_count']} supported={packet['supported_row_count']}")
    print(f"provider_calls_planned: {packet['provider_calls_planned']}")
    print(f"budget_caps: {json.dumps(packet['budget_caps'], sort_keys=True)}")
    for row in packet["rows"]:
        status = "unsupported" if row.get("unsupported_reason") else "planned"
        print(
            f"- {row['row_id']} | {row['provider_profile']} | {row['model']} | "
            f"{row['evidence_lane']} | {row['candidate_group']} | {status}"
        )
        if row.get("unsupported_reason"):
            print(f"  unsupported_reason: {row['unsupported_reason']}")
        print(f"  candidates: {','.join(row.get('candidate_ids') or [])}")
        print(f"  flags: {json.dumps(row.get('feature_flags') or {}, sort_keys=True)}")
        print(f"  dependencies: {','.join(row.get('dependency_candidate_ids') or []) or 'none'}")
        print(f"  stop_conditions: {len(row.get('stop_conditions') or [])}")


def _decision_packet(manifest: dict[str, Any], *, dry_run: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "agent_sdk_speedup_decision_packet_v1",
        "matrix_schema": manifest.get("schema"),
        "budget_caps": dry_run["budget_caps"],
        "provider_calls_planned": dry_run["provider_calls_planned"],
        "candidate_groups": manifest.get("candidate_groups") or [],
        "rows": [_decision_row(row) for row in _rows(manifest)],
        "summary": {},
    }


def _decision_row(row: dict[str, Any]) -> dict[str, Any]:
    unsupported_reason = str(row.get("unsupported_reason") or "")
    payload = {
        "row_id": str(row.get("row_id") or ""),
        "provider_profile": str(row.get("provider_profile") or ""),
        "model": str(row.get("model") or ""),
        "evidence_lane": str(row.get("evidence_lane") or row.get("lane") or ""),
        "candidate_group": str(row.get("candidate_group") or ""),
        "candidate_ids": _str_list(row.get("candidate_ids")),
        "dependency_candidate_ids": _str_list(row.get("dependency_candidate_ids")),
        "feature_flags": _dict(row.get("feature_flags")),
        "stop_conditions": _str_list(row.get("stop_conditions")),
        "baseline_role": str(row.get("baseline_role") or ""),
        "baseline_run_dir": str(row.get("baseline_run_dir") or ""),
        "candidate_run_dir": str(row.get("candidate_run_dir") or ""),
        "quality_policy": str(row.get("quality_policy") or "same_or_better"),
        "quality_waiver": str(row.get("quality_waiver") or ""),
        "expected_terminal": str(row.get("expected_terminal") or ""),
        "unsupported_reason": unsupported_reason,
        "status": "unsupported" if unsupported_reason else "pending",
        "reasons": [unsupported_reason] if unsupported_reason else [],
        "quality_comparison": {},
        "speed_comparison": {},
        "reducible_bucket_report": {},
        "artifact_links": {},
    }
    return payload


def _apply_privacy_gate(packet: dict[str, Any]) -> None:
    findings = _privacy_findings(packet)
    for row in packet["rows"]:
        row_findings = [item for item in findings if item.get("row_id") in {"", row.get("row_id")}]
        if not row_findings:
            row["privacy_gate"] = {"status": "passed", "findings": []}
            continue
        row["privacy_gate"] = {"status": "failed", "findings": row_findings}
        _block(row, "privacy gate failed")


def _apply_offline_preflight(packet: dict[str, Any]) -> None:
    if packet["provider_calls_planned"]:
        for row in packet["rows"]:
            _block(row, "Group 0 foundation cannot plan provider calls")
    for row in packet["rows"]:
        if row["unsupported_reason"]:
            continue
        if not row["row_id"]:
            _block(row, "row_id is required")
        if not row["candidate_ids"]:
            _block(row, "candidate_ids are required")
        if not row["feature_flags"]:
            _block(row, "feature_flags are required")
        if not row["stop_conditions"]:
            _block(row, "stop_conditions are required")
        _load_row_runs(row)


def _apply_quality_gate(packet: dict[str, Any]) -> None:
    for row in packet["rows"]:
        if row["status"] in {"blocked", "unsupported"}:
            continue
        baseline = row.get("_baseline_summary")
        candidate = row.get("_candidate_summary")
        if not isinstance(baseline, dict) or not isinstance(candidate, dict):
            row["status"] = "inconclusive"
            row["reasons"].append("baseline/candidate summaries unavailable")
            continue
        speed = _speed_comparison(baseline, candidate)
        quality = _quality_comparison(baseline, candidate, lane=row["evidence_lane"])
        row["speed_comparison"] = speed
        row["quality_comparison"] = quality
        if row["quality_waiver"]:
            row["status"] = "accepted"
            row["reasons"].append(f"quality waiver: {row['quality_waiver']}")
        elif quality["regressed"]:
            row["status"] = "rejected"
            row["reasons"].append("behavior quality regressed")
        elif row["evidence_lane"] == "camera-raw-fpv" and candidate["terminal"] != "finished":
            row["status"] = "accepted"
            row["reasons"].append("raw-FPV accepted as classified diagnostic evidence")
        else:
            row["status"] = "accepted"


def _apply_reducible_bucket_reports(packet: dict[str, Any]) -> None:
    for row in packet["rows"]:
        candidate = row.get("_candidate_summary")
        if not isinstance(candidate, dict):
            row["reducible_bucket_report"] = {"available": False, "recommendations": []}
            continue
        row["reducible_bucket_report"] = _reducible_bucket_report(
            candidate,
            lane=row["evidence_lane"],
        )


def _finalize_packet(packet: dict[str, Any]) -> None:
    for row in packet["rows"]:
        row.pop("_baseline_summary", None)
        row.pop("_candidate_summary", None)
    counts: dict[str, int] = {}
    for row in packet["rows"]:
        status = str(row.get("status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    packet["summary"] = {
        "status_counts": dict(sorted(counts.items())),
        "accepted": [row["row_id"] for row in packet["rows"] if row["status"] == "accepted"],
        "rejected": [row["row_id"] for row in packet["rows"] if row["status"] == "rejected"],
        "blocked": [row["row_id"] for row in packet["rows"] if row["status"] == "blocked"],
        "inconclusive": [
            row["row_id"] for row in packet["rows"] if row["status"] == "inconclusive"
        ],
        "unsupported": [row["row_id"] for row in packet["rows"] if row["status"] == "unsupported"],
    }


def _load_row_runs(row: dict[str, Any]) -> None:
    baseline_dir = Path(row["baseline_run_dir"]) if row["baseline_run_dir"] else None
    candidate_dir = Path(row["candidate_run_dir"]) if row["candidate_run_dir"] else None
    if baseline_dir is None or candidate_dir is None:
        _block(row, "baseline_run_dir and candidate_run_dir are required")
        return
    if not baseline_dir.exists():
        _block(row, f"baseline run dir missing: {baseline_dir}")
        return
    if not candidate_dir.exists():
        _block(row, f"candidate run dir missing: {candidate_dir}")
        return
    row["_baseline_summary"] = _run_summary(baseline_dir)
    row["_candidate_summary"] = _run_summary(candidate_dir)
    row["artifact_links"] = {
        "baseline_run_dir": str(baseline_dir),
        "candidate_run_dir": str(candidate_dir),
        "candidate_report": str(candidate_dir / "report.html"),
        "candidate_live_timing": str(candidate_dir / "live_timing.json"),
    }


def _run_summary(run_dir: Path) -> dict[str, Any]:
    live_timing = _read_json(run_dir / "live_timing.json")
    live_status = _read_json(run_dir / "live_status.json")
    run_result = _read_json(run_dir / "run_result.json")
    trace_events = _read_jsonl(run_dir / "trace.jsonl")
    runner_timing = _dict(live_timing.get("runner_timing"))
    mcp_timing = _dict(live_timing.get("mcp_trace_timing"))
    score = _dict(run_result.get("score"))
    return {
        "run_dir": str(run_dir),
        "elapsed_s": _float_or_none(runner_timing.get("total_elapsed_s")),
        "between_tool_gap_s": _float_or_none(mcp_timing.get("between_tool_gap_s")),
        "robot_view_capture_s": _float_or_none(mcp_timing.get("robot_view_capture_s")),
        "tool_handler_s": _float_or_none(mcp_timing.get("tool_handler_s")),
        "terminal": _terminal_state(live_timing, live_status),
        "checker": "result-present" if run_result else str(live_status.get("reason") or "missing"),
        "run_result_present": bool(run_result),
        "cleanup_status": run_result.get("cleanup_status"),
        "completion_status": run_result.get("completion_status"),
        "restored_count": _int_or_none(score.get("restored_count")),
        "total_targets": _int_or_none(score.get("total_targets")),
        "mess_restoration_rate": _float_or_none(
            run_result.get("mess_restoration_rate") or score.get("mess_restoration_rate")
        ),
        "sweep_coverage_rate": _float_or_none(run_result.get("sweep_coverage_rate")),
        "disturbance_count": _int_or_none(
            run_result.get("disturbance_count") or score.get("disturbance_count")
        )
        or 0,
        "semantic_accepted_count": _semantic_accepted_count(score),
        "failed_or_noop_tool_count": _failed_or_noop_tool_count(trace_events),
        "tool_counts": _tool_counts(trace_events),
        "trace_events": trace_events,
        "live_timing": live_timing,
    }


def _speed_comparison(baseline: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "elapsed_delta_s": _delta(candidate.get("elapsed_s"), baseline.get("elapsed_s")),
        "between_tool_gap_delta_s": _delta(
            candidate.get("between_tool_gap_s"),
            baseline.get("between_tool_gap_s"),
        ),
    }


def _quality_comparison(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    lane: str,
) -> dict[str, Any]:
    checks = {
        "run_result_present": not baseline["run_result_present"] or candidate["run_result_present"],
        "restored_count": _not_lower(
            candidate.get("restored_count"),
            baseline.get("restored_count"),
        ),
        "mess_restoration_rate": _not_lower(
            candidate.get("mess_restoration_rate"),
            baseline.get("mess_restoration_rate"),
        ),
        "sweep_coverage_rate": _not_lower(
            candidate.get("sweep_coverage_rate"),
            baseline.get("sweep_coverage_rate"),
        ),
        "disturbance_count": _not_higher(
            candidate.get("disturbance_count"),
            baseline.get("disturbance_count"),
        ),
        "semantic_accepted_count": _not_lower(
            candidate.get("semantic_accepted_count"),
            baseline.get("semantic_accepted_count"),
        ),
        "failed_or_noop_tool_count": _not_higher(
            candidate.get("failed_or_noop_tool_count"),
            baseline.get("failed_or_noop_tool_count"),
        ),
    }
    if lane == "camera-raw-fpv" and not candidate["run_result_present"]:
        checks["run_result_present"] = candidate["terminal"] not in {"unknown", "missing", ""}
    regressed = not all(checks.values())
    return {
        "policy": "same_or_better",
        "regressed": regressed,
        "checks": checks,
        "baseline": _quality_fields(baseline),
        "candidate": _quality_fields(candidate),
    }


def _quality_fields(summary: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_result_present": summary["run_result_present"],
        "restored_count": summary.get("restored_count"),
        "total_targets": summary.get("total_targets"),
        "mess_restoration_rate": summary.get("mess_restoration_rate"),
        "sweep_coverage_rate": summary.get("sweep_coverage_rate"),
        "disturbance_count": summary.get("disturbance_count"),
        "semantic_accepted_count": summary.get("semantic_accepted_count"),
        "failed_or_noop_tool_count": summary.get("failed_or_noop_tool_count"),
        "terminal": summary.get("terminal"),
    }


def _reducible_bucket_report(summary: dict[str, Any], *, lane: str) -> dict[str, Any]:
    recommendations: list[dict[str, Any]] = []
    elapsed = _float_or_none(summary.get("elapsed_s")) or 0.0
    between_gap = _float_or_none(summary.get("between_tool_gap_s")) or 0.0
    robot_view = _float_or_none(summary.get("robot_view_capture_s")) or 0.0
    tool_counts = _dict(summary.get("tool_counts"))
    if between_gap > 60 or (elapsed and between_gap / elapsed >= 0.45):
        recommendations.append(
            {
                "candidate_group": "group1_private_sdk_levers",
                "candidate_ids": ["A", "G", "J", "H", "I", "L"],
                "reason": "model/SDK between-tool gap remains a dominant bucket",
            }
        )
    if lane == "camera-grounded-labels" and tool_counts.get("declare_visual_candidates", 0) > 0:
        recommendations.append(
            {
                "candidate_group": "group2_lane_specific_reductions",
                "candidate_ids": ["O"],
                "reason": "camera-grounded observe/label two-step is present",
            }
        )
    if tool_counts.get("metric_map", 0) > 1:
        recommendations.append(
            {
                "candidate_group": "group2_lane_specific_reductions",
                "candidate_ids": ["N"],
                "reason": "metric_map is fetched repeatedly",
            }
        )
    if lane == "camera-raw-fpv" and summary.get("failed_or_noop_tool_count", 0) > 0:
        recommendations.append(
            {
                "candidate_group": "group3_raw_fpv_stabilization",
                "candidate_ids": ["P", "AA"],
                "reason": "raw-FPV has repeated public failure evidence",
            }
        )
    if robot_view > 60:
        recommendations.append(
            {
                "candidate_group": "group2_lane_specific_reductions",
                "candidate_ids": ["F"],
                "reason": "robot-view capture is a material wall-clock bucket",
            }
        )
    return {
        "available": True,
        "elapsed_s": elapsed,
        "between_tool_gap_s": between_gap,
        "robot_view_capture_s": robot_view,
        "tool_counts": tool_counts,
        "recommendations": recommendations,
    }


def _privacy_findings(packet: dict[str, Any]) -> list[dict[str, Any]]:
    findings = _privacy_scan_payload(packet, source="decision_packet", row_id="")
    for row in packet["rows"]:
        for key in ("baseline_run_dir", "candidate_run_dir"):
            run_dir = row.get(key)
            if not run_dir:
                continue
            findings.extend(_privacy_scan_run_dir(Path(str(run_dir)), row_id=row["row_id"]))
    return findings


def _privacy_scan_run_dir(run_dir: Path, *, row_id: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for pattern in SAFE_SCAN_GLOBS:
        for path in sorted(run_dir.glob(pattern)):
            findings.extend(_privacy_scan_text(path.read_text(encoding="utf-8"), path, row_id))
    return findings


def _privacy_scan_text(text: str, path: Path, row_id: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            payload = {"text": line}
        findings.extend(
            _privacy_scan_payload(payload, source=f"{path}:{line_number}", row_id=row_id)
        )
    return findings


def _privacy_scan_payload(payload: Any, *, source: str, row_id: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def visit(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                key_text = str(key)
                normalized_key = key_text.lower()
                if normalized_key in FORBIDDEN_PRIVACY_KEYS:
                    findings.append(
                        {
                            "row_id": row_id,
                            "source": source,
                            "path": f"{path}.{key_text}" if path else key_text,
                            "reason": f"forbidden key {key_text}",
                        }
                    )
                visit(item, f"{path}.{key_text}" if path else key_text)
            return
        if isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, f"{path}[{index}]")
            return
        if isinstance(value, str):
            lowered = value.lower()
            for marker in FORBIDDEN_PRIVACY_MARKERS:
                if marker in lowered:
                    findings.append(
                        {
                            "row_id": row_id,
                            "source": source,
                            "path": path,
                            "reason": f"forbidden marker {marker}",
                        }
                    )
                    break

    visit(payload, "")
    return findings


def _rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    rows = manifest.get("rows")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _dry_run_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": str(row.get("row_id") or ""),
        "provider_profile": str(row.get("provider_profile") or ""),
        "model": str(row.get("model") or ""),
        "evidence_lane": str(row.get("evidence_lane") or row.get("lane") or ""),
        "candidate_group": str(row.get("candidate_group") or ""),
        "candidate_ids": _str_list(row.get("candidate_ids")),
        "dependency_candidate_ids": _str_list(row.get("dependency_candidate_ids")),
        "feature_flags": _dict(row.get("feature_flags")),
        "stop_conditions": _str_list(row.get("stop_conditions")),
        "unsupported_reason": str(row.get("unsupported_reason") or ""),
        "provider_calls": bool(row.get("provider_calls")),
    }


def _block(row: dict[str, Any], reason: str) -> None:
    row["status"] = "blocked"
    if reason not in row["reasons"]:
        row["reasons"].append(reason)


def _terminal_state(live_timing: dict[str, Any], status: dict[str, Any]) -> str:
    terminal = live_timing.get("agent_sdk_budget_terminal")
    if isinstance(terminal, dict) and terminal.get("reason"):
        return str(terminal["reason"])
    reason = status.get("reason")
    if reason:
        return str(reason)
    return str(status.get("phase") or "unknown")


def _semantic_accepted_count(score: dict[str, Any]) -> int | None:
    rows = score.get("object_results")
    if not isinstance(rows, list):
        return None
    accepted = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        if row.get("restored") or str(row.get("semantic_acceptability") or "") in {
            "preferred",
            "acceptable",
        }:
            accepted += 1
    return accepted


def _failed_or_noop_tool_count(events: list[dict[str, Any]]) -> int:
    count = 0
    for event in events:
        if event.get("event") != "response":
            continue
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        ok = response.get("ok")
        error_reason = str(response.get("error_reason") or response.get("failure_reason") or "")
        status = str(response.get("status") or "")
        if ok is False or error_reason or status in {"noop", "failed", "error"}:
            count += 1
    return count


def _tool_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        if event.get("event") != "response":
            continue
        tool = str(event.get("tool") or "")
        if not tool:
            continue
        counts[tool] = counts.get(tool, 0) + 1
    return dict(sorted(counts.items()))


def _not_lower(candidate: Any, baseline: Any) -> bool:
    candidate_value = _float_or_none(candidate)
    baseline_value = _float_or_none(baseline)
    if candidate_value is None or baseline_value is None:
        return True
    return candidate_value >= baseline_value


def _not_higher(candidate: Any, baseline: Any) -> bool:
    candidate_value = _float_or_none(candidate)
    baseline_value = _float_or_none(baseline)
    if candidate_value is None or baseline_value is None:
        return True
    return candidate_value <= baseline_value


def _delta(candidate: Any, baseline: Any) -> float | None:
    candidate_value = _float_or_none(candidate)
    baseline_value = _float_or_none(baseline)
    if candidate_value is None or baseline_value is None:
        return None
    return round(candidate_value - baseline_value, 3)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _str_list(value: Any) -> list[str]:
    return [str(item) for item in value if str(item)] if isinstance(value, list) else []


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


if __name__ == "__main__":
    raise SystemExit(main())
