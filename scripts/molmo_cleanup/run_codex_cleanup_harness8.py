#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.core.rerun import shell_join  # noqa: E402
from roboclaws.household.apple2apple_test_grid import (  # noqa: E402
    DEFAULT_MAP_BUNDLE,
    RUNTIME_MAP_PRIOR_PLACEHOLDER,
)
from roboclaws.household.realworld_contract import DEFAULT_REALWORLD_TASK  # noqa: E402

HARNESS_SCHEMA = "codex_cleanup_harness8_v1"
ROW_SCHEMA = "codex_cleanup_harness8_row_v1"
DIRECT_MAP_MODE = "direct"
PRIOR_MAP_MODE = "dino-prior"
RATE_LIMIT_LOG_NAMES = (
    "driver.log",
    "codex.stderr.log",
    "codex-last-message.md",
)
RATE_LIMIT_PATTERNS = (
    "429 too many requests",
    "too many requests",
    "provider_rate_limit",
    "rate limit",
    "ratelimit",
    "exceeded retry limit",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build or execute the eight-case Codex household-cleanup harness: "
            "four evidence lanes without a Runtime Metric Map prior and the same "
            "four lanes using a DINO semantic-map-build prior."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/molmo/codex-harness8"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--generated-mess-count", type=int, default=10)
    parser.add_argument("--task", default=DEFAULT_REALWORLD_TASK)
    parser.add_argument("--map-bundle", default=DEFAULT_MAP_BUNDLE)
    parser.add_argument("--runtime-map-prior", default="")
    parser.add_argument("--visual-grounding-timeout-s", default="auto")
    parser.add_argument("--just-bin", default="just")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--row", action="append", default=[])
    parser.add_argument("--live-wait-timeout-s", type=float, default=7200.0)
    parser.add_argument("--live-wait-poll-s", type=float, default=10.0)
    parser.add_argument(
        "--rate-limit-retries",
        type=int,
        default=1,
        help=(
            "Additional whole-row retries for provider 429/rate-limit failures. "
            "Ordinary cleanup failures are not retried."
        ),
    )
    parser.add_argument("--rate-limit-retry-sleep-s", type=float, default=60.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    harness = build_harness(
        output_dir=args.output_dir,
        seed=args.seed,
        generated_mess_count=args.generated_mess_count,
        task=args.task,
        map_bundle=args.map_bundle,
        runtime_map_prior=args.runtime_map_prior,
        visual_grounding_timeout_s=args.visual_grounding_timeout_s,
    )
    if args.execute:
        if args.row:
            _merge_existing_state(harness, args.output_dir, selected_row_ids=set(args.row))
        if args.runtime_map_prior:
            _mark_explicit_runtime_map_prior(harness, args.runtime_map_prior)
        status = _execute_harness(harness, args)
    else:
        _mark_dry_run(harness)
        status = 0
    _write_outputs(harness, args.output_dir)
    print(f"codex harness8 manifest: {args.output_dir / 'codex_cleanup_harness8.json'}")
    print(f"codex harness8 report: {args.output_dir / 'codex_cleanup_harness8.html'}")
    return status


def build_harness(
    *,
    output_dir: Path,
    seed: int,
    generated_mess_count: int,
    task: str,
    map_bundle: str,
    runtime_map_prior: str,
    visual_grounding_timeout_s: str,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    prior_value = runtime_map_prior or RUNTIME_MAP_PRIOR_PLACEHOLDER
    setup_rows = [
        _semantic_map_prior_row(
            output_dir=output_dir,
            seed=seed,
            generated_mess_count=generated_mess_count,
            task=task,
            map_bundle=map_bundle,
            visual_grounding_timeout_s=visual_grounding_timeout_s,
        )
    ]
    rows = []
    for map_mode in (DIRECT_MAP_MODE, PRIOR_MAP_MODE):
        for lane in _harness_lanes():
            rows.append(
                _cleanup_row(
                    output_dir=output_dir,
                    seed=seed,
                    generated_mess_count=generated_mess_count,
                    task=task,
                    map_bundle=map_bundle,
                    map_mode=map_mode,
                    lane=lane,
                    runtime_map_prior=prior_value if map_mode == PRIOR_MAP_MODE else "",
                    visual_grounding_timeout_s=visual_grounding_timeout_s,
                )
            )
    return {
        "schema": HARNESS_SCHEMA,
        "generated_at": _utc_timestamp(),
        "name": "codex_cleanup_harness8",
        "description": (
            "Eight-case live Codex cleanup harness for source/skill regression "
            "checks: two world-label lanes, Grounding DINO camera labels, and "
            "RAW_FPV, each run directly and with a DINO semantic-map prior."
        ),
        "seed": seed,
        "generated_mess_count": generated_mess_count,
        "task": task,
        "map_bundle": map_bundle,
        "runtime_map_prior": runtime_map_prior,
        "runtime_map_prior_placeholder": RUNTIME_MAP_PRIOR_PLACEHOLDER,
        "setup_rows": setup_rows,
        "rows": rows,
    }


def _harness_lanes() -> tuple[dict[str, str], ...]:
    return (
        {
            "lane_id": "world-labels",
            "label": "World labels",
            "profile": "world-labels",
            "visual_grounding": "sim",
        },
        {
            "lane_id": "world-labels-sanitized",
            "label": "Sanitized world labels",
            "profile": "world-labels-sanitized",
            "visual_grounding": "sim",
        },
        {
            "lane_id": "camera-labels-grounding-dino",
            "label": "Grounding DINO camera labels",
            "profile": "camera-labels",
            "visual_grounding": "grounding-dino",
        },
        {
            "lane_id": "camera-raw",
            "label": "RAW_FPV",
            "profile": "camera-raw",
            "visual_grounding": "grounding-dino",
        },
    )


def _semantic_map_prior_row(
    *,
    output_dir: Path,
    seed: int,
    generated_mess_count: int,
    task: str,
    map_bundle: str,
    visual_grounding_timeout_s: str,
) -> dict[str, Any]:
    row_output_dir = output_dir / "_semantic-map-prior-dino"
    command = [
        "just",
        "task::run",
        "semantic-map-build",
        "direct",
        "camera-labels",
        f"seed={seed}",
        f"generated_mess_count={generated_mess_count}",
        f"output_dir={row_output_dir}",
        f"task={task}",
        f"map_bundle={map_bundle}",
        "visual_grounding=grounding-dino",
    ]
    if visual_grounding_timeout_s != "auto":
        command.append(f"visual_grounding_timeout_s={visual_grounding_timeout_s}")
    return _row_payload(
        row_id="setup-semantic-map-prior-dino",
        label="Build DINO semantic-map prior",
        grid_role="setup",
        map_mode="setup",
        lane_id="camera-labels-grounding-dino",
        command=command,
        output_dir=row_output_dir,
        requires_runtime_map_prior=False,
        expected_artifacts=["runtime_metric_map.json", "report.html"],
    )


def _cleanup_row(
    *,
    output_dir: Path,
    seed: int,
    generated_mess_count: int,
    task: str,
    map_bundle: str,
    map_mode: str,
    lane: dict[str, str],
    runtime_map_prior: str,
    visual_grounding_timeout_s: str,
) -> dict[str, Any]:
    row_id = f"{map_mode}-{lane['lane_id']}"
    row_output_dir = output_dir / row_id
    command = [
        "just",
        "task::run",
        "household-cleanup",
        "codex",
        lane["profile"],
        f"seed={seed}",
        f"generated_mess_count={generated_mess_count}",
        f"output_dir={row_output_dir}",
        f"task={task}",
        f"map_bundle={map_bundle}",
        f"visual_grounding={lane['visual_grounding']}",
    ]
    if visual_grounding_timeout_s != "auto":
        command.append(f"visual_grounding_timeout_s={visual_grounding_timeout_s}")
    if runtime_map_prior:
        command.append(f"runtime_map_prior={runtime_map_prior}")
    return _row_payload(
        row_id=row_id,
        label=f"{map_mode} Codex {lane['label']}",
        grid_role="cleanup",
        map_mode=map_mode,
        lane_id=lane["lane_id"],
        command=command,
        output_dir=row_output_dir,
        requires_runtime_map_prior=bool(runtime_map_prior),
        expected_artifacts=["run_result.json", "report.html", "runtime_metric_map.json"],
    )


def _row_payload(
    *,
    row_id: str,
    label: str,
    grid_role: str,
    map_mode: str,
    lane_id: str,
    command: list[str],
    output_dir: Path,
    requires_runtime_map_prior: bool,
    expected_artifacts: list[str],
) -> dict[str, Any]:
    row = {
        "schema": ROW_SCHEMA,
        "row_id": row_id,
        "label": label,
        "grid_role": grid_role,
        "axes": {
            "agent_route": "codex",
            "map_mode": map_mode,
            "perception_lane": lane_id,
        },
        "command": [str(item) for item in command],
        "env": {},
        "required_env": ["XM_LLM_API_KEY|CODEX_API_KEY+CODEX_BASE_URL"]
        if grid_role == "cleanup"
        else [],
        "output_dir": str(output_dir),
        "requires_runtime_map_prior": requires_runtime_map_prior,
        "expected_artifacts": expected_artifacts,
        "status": "pending",
        "reason": "",
        "run_dir": "",
        "report_path": "",
        "run_result_path": "",
        "metrics": {},
    }
    row["rerun_command"] = row_rerun_command(row)
    return row


def _execute_harness(harness: dict[str, Any], args: argparse.Namespace) -> int:
    selected_rows = _selected_rows(harness, filters=set(args.row))
    if not selected_rows:
        raise SystemExit("no cleanup rows selected")

    selected_ids = {str(row.get("row_id") or "") for row in selected_rows}
    for row in harness.get("rows") or []:
        if str(row.get("row_id") or "") not in selected_ids and not _has_existing_row_evidence(row):
            row["status"] = "not_selected"
            row["reason"] = "row was not selected for this execution"
            row["updated_at"] = _utc_timestamp()

    prior_path = args.runtime_map_prior
    if any(row.get("requires_runtime_map_prior") for row in selected_rows) and not prior_path:
        prior_path = _execute_prior_build(harness, args)
        harness["runtime_map_prior"] = prior_path
        if not prior_path:
            _mark_prior_dependent_rows_blocked(selected_rows, harness)
            return 1
        _replace_runtime_map_prior(harness, prior_path)

    failure_count = 0
    for row in selected_rows:
        status = _execute_row_with_retries(row, args)
        if status != 0:
            failure_count += 1
            if not args.continue_on_error:
                break
    return 1 if failure_count else 0


def _execute_prior_build(harness: dict[str, Any], args: argparse.Namespace) -> str:
    setup_rows = list(harness.get("setup_rows") or [])
    if not setup_rows:
        raise RuntimeError("prior rows require a runtime-map prior but no setup row exists")
    row = setup_rows[0]
    status = _execute_row_with_retries(row, args)
    prior = _latest_runtime_map(Path(row["output_dir"]), seed=args.seed)
    if prior is None:
        if str(row.get("status") or "") == "rate_limited":
            harness["setup_status"] = "rate_limited"
            harness["behavior_status"] = "infra_failure"
            harness["reason"] = row.get("reason") or "semantic-map prior build was rate limited"
            return ""
        if status != 0:
            raise RuntimeError("semantic-map prior build failed")
        raise RuntimeError("semantic-map prior build produced no runtime_metric_map.json")
    if status != 0:
        row["status"] = "artifact_success"
        row["reason"] = (
            f"runtime_metric_map.json was produced; setup command exited with status {status}"
        )
    row["runtime_map_prior"] = str(prior)
    return str(prior)


def _mark_prior_dependent_rows_blocked(
    rows: list[dict[str, Any]],
    harness: dict[str, Any],
) -> None:
    reason = str(
        harness.get("reason")
        or "runtime_map_prior unavailable because semantic-map prior setup failed"
    )
    for row in rows:
        if not row.get("requires_runtime_map_prior"):
            continue
        row["status"] = "blocked"
        row["behavior_status"] = "infra_failure"
        row["reason"] = reason
        row["updated_at"] = _utc_timestamp()


def _execute_row_with_retries(row: dict[str, Any], args: argparse.Namespace) -> int:
    attempts: list[dict[str, Any]] = []
    max_attempts = max(int(args.rate_limit_retries), 0) + 1
    status = 1
    final_rate_limit: dict[str, Any] | None = None
    for attempt_index in range(max_attempts):
        if attempt_index:
            sleep_s = max(float(args.rate_limit_retry_sleep_s), 0.0)
            if sleep_s:
                time.sleep(sleep_s)
        status = _execute_row(row, args)
        rate_limit = _rate_limit_evidence(row)
        final_rate_limit = rate_limit
        attempts.append(
            {
                "attempt": attempt_index + 1,
                "exit_status": status,
                "run_dir": row.get("run_dir") or "",
                "rate_limited": bool(rate_limit),
                "rate_limit_evidence": rate_limit,
                "finished_at": _utc_timestamp(),
            }
        )
        if status == 0 or not rate_limit or attempt_index == max_attempts - 1:
            break
        print(
            f"provider rate limit detected for {row.get('row_id')}; "
            f"retrying attempt {attempt_index + 2}/{max_attempts}"
        )

    row["attempts"] = attempts
    row["retry_count"] = max(len(attempts) - 1, 0)
    row["rate_limit_retry_count"] = sum(1 for attempt in attempts if attempt["rate_limited"])
    if status == 0 and len(attempts) > 1:
        row["infra_note"] = "succeeded after provider rate-limit retry"
    elif status != 0 and final_rate_limit:
        row["status"] = "rate_limited"
        row["behavior_status"] = "infra_failure"
        row["reason"] = (
            f"provider rate limited after {len(attempts)} attempt(s); "
            f"{final_rate_limit.get('snippet') or final_rate_limit.get('source') or 'see logs'}"
        )
    return status


def _execute_row(row: dict[str, Any], args: argparse.Namespace) -> int:
    command = _command_for_row(row, just_bin=args.just_bin)
    print("+ " + row_rerun_command({**row, "command": command}))
    status = subprocess.run(command, env=os.environ.copy(), check=False).returncode
    run_dir = _latest_seed_dir(Path(row["output_dir"]), seed=args.seed)
    if run_dir is not None:
        row["run_dir"] = str(run_dir)
        live_status = _wait_for_live_terminal_status(
            run_dir,
            timeout_s=args.live_wait_timeout_s,
            poll_s=args.live_wait_poll_s,
        )
        if live_status is not None:
            status = int(live_status.get("exit_status") or 0)
            row["live_status"] = live_status
    _refresh_row_from_evidence(row, status=status, run_dir=run_dir)
    return status


def _refresh_row_from_evidence(
    row: dict[str, Any],
    *,
    status: int | None = None,
    run_dir: Path | None = None,
) -> None:
    if run_dir is None:
        row_run_dir = row.get("run_dir")
        if row_run_dir:
            candidate = Path(str(row_run_dir))
            if candidate.is_dir():
                run_dir = candidate
    if run_dir is not None:
        row["run_dir"] = str(run_dir)
        live_status = _read_status(run_dir / "live_status.json")
        if live_status.get("phase") != "unknown":
            row["live_status"] = live_status
            if status is None and "exit_status" in live_status:
                status = int(live_status.get("exit_status") or 0)
        _refresh_row_artifacts(row, run_dir)
    elif row.get("run_result_path"):
        _refresh_row_artifacts(row, Path(str(row["run_result_path"])).parent)

    if status is None:
        existing_status = row.get("strict_exit_status", row.get("exit_status"))
        if isinstance(existing_status, int):
            status = existing_status
    if status is None:
        return
    row["exit_status"] = status
    row["updated_at"] = _utc_timestamp()
    _refresh_row_status(row, status)


def _refresh_row_status(row: dict[str, Any], status: int) -> None:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    completion_status = str(metrics.get("completion_status") or "")
    score_status = str(metrics.get("score_status") or "")
    row["strict_exit_status"] = status
    if _is_setup_row(row):
        if row.get("runtime_map_path"):
            row["status"] = "artifact_success"
            row["behavior_status"] = "artifact_success"
            row["reason"] = (
                ""
                if status == 0
                else f"runtime_metric_map.json was produced; command exited with status {status}"
            )
        elif status == 0:
            row["status"] = "launched"
            row["behavior_status"] = "artifact_pending"
            row["reason"] = "command returned before runtime_metric_map.json existed"
        else:
            row["status"] = "failed"
            row["behavior_status"] = "failed"
            row["reason"] = f"command exited with status {status}"
        return
    if status == 0:
        row["status"] = "success" if row.get("report_path") else "launched"
        row["reason"] = (
            "" if row.get("report_path") else "command returned before seed report existed"
        )
        row["behavior_status"] = completion_status or score_status or row["status"]
    elif completion_status == "success" or score_status == "success":
        row["status"] = "strict_checker_failed"
        row["behavior_status"] = "success"
        row["reason"] = (
            f"strict cleanup checker exited with status {status}; "
            "run_result.json reports cleanup success"
        )
    else:
        row["status"] = "failed"
        row["behavior_status"] = completion_status or score_status or "failed"
        row["reason"] = f"command exited with status {status}"


def _refresh_row_artifacts(row: dict[str, Any], run_dir: Path) -> None:
    report_path = run_dir / "report.html"
    if report_path.is_file():
        row["report_path"] = str(report_path)
    run_result_path = run_dir / "run_result.json"
    if run_result_path.is_file():
        row["run_result_path"] = str(run_result_path)
        row["metrics"] = (
            _setup_result_metrics(run_result_path)
            if _is_setup_row(row)
            else _run_result_metrics(run_result_path)
        )
    runtime_map_path = run_dir / "runtime_metric_map.json"
    if runtime_map_path.is_file():
        row["runtime_map_path"] = str(runtime_map_path)


def _run_result_metrics(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    score = data.get("score") if isinstance(data.get("score"), dict) else {}
    advisory = (
        data.get("advisory_evaluation")
        if isinstance(data.get("advisory_evaluation"), dict)
        else {}
    )
    advisory_counts = (
        advisory.get("counts") if isinstance(advisory.get("counts"), dict) else {}
    )
    runtime = data.get("runtime_timing") if isinstance(data.get("runtime_timing"), dict) else {}
    score_semantic = (
        score.get("semantic_acceptability")
        if isinstance(score.get("semantic_acceptability"), dict)
        else {}
    )
    diagnostics = (
        data.get("agent_diagnostics")
        if isinstance(data.get("agent_diagnostics"), dict)
        else {}
    )
    return {
        "completion_status": data.get("completion_status") or score.get("completion_status") or "",
        "score_status": score.get("status") or "",
        "exact_restored": score.get("restored_count"),
        "total_targets": score.get("total_targets"),
        "semantic_accepted": _semantic_accepted_count(score, advisory_counts),
        "score_semantic_accepted": score_semantic.get("accepted_count"),
        "supports_exact": advisory_counts.get("supports_exact"),
        "benign_disagreement": advisory_counts.get("benign_disagreement"),
        "disagrees": advisory_counts.get("disagrees"),
        "semantic_order_errors": diagnostics.get("semantic_order_errors"),
        "semantic_order_recovered_errors": diagnostics.get("semantic_order_recovered_errors"),
        "semantic_order_unrecovered_errors": diagnostics.get("semantic_order_unrecovered_errors"),
        "sweep_coverage_rate": data.get("sweep_coverage_rate")
        if data.get("sweep_coverage_rate") is not None
        else score.get("sweep_coverage_rate"),
        "disturbance_count": data.get("disturbance_count")
        if data.get("disturbance_count") is not None
        else score.get("disturbance_count"),
        "tool_call_count": runtime.get("tool_call_count"),
        "total_elapsed_s": runtime.get("total_elapsed_s"),
        "report_path": str(path.parent / "report.html"),
    }


def _setup_result_metrics(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    runtime_map = (
        data.get("runtime_metric_map")
        if isinstance(data.get("runtime_metric_map"), dict)
        else {}
    )
    return {
        "sweep_coverage_rate": data.get("sweep_coverage_rate"),
        "disturbance_count": data.get("disturbance_count"),
        "runtime_semantic_anchor_count": len(runtime_map.get("public_semantic_anchors") or []),
        "visual_grounding_pipeline_id": data.get("visual_grounding_pipeline_id") or "",
        "report_path": str(path.parent / "report.html"),
    }


def _semantic_accepted_count(score: dict[str, Any], advisory_counts: dict[str, Any]) -> int | None:
    score_semantic = (
        score.get("semantic_acceptability")
        if isinstance(score.get("semantic_acceptability"), dict)
        else {}
    )
    accepted = score_semantic.get("accepted_count")
    if isinstance(accepted, int):
        return accepted
    total = advisory_counts.get("total_reviewed")
    rejected = 0
    for key in ("needs_review", "disagrees"):
        value = advisory_counts.get(key)
        if isinstance(value, int):
            rejected += value
    if isinstance(total, int):
        return total - rejected
    rows = score.get("object_results")
    if isinstance(rows, list):
        return sum(
            1
            for item in rows
            if isinstance(item, dict)
            and str(item.get("semantic_acceptability") or "") in {"preferred", "acceptable"}
        )
    return None


def _selected_rows(harness: dict[str, Any], *, filters: set[str]) -> list[dict[str, Any]]:
    rows = list(harness.get("rows") or [])
    if not filters:
        return rows
    return [row for row in rows if str(row.get("row_id") or "") in filters]


def _mark_dry_run(harness: dict[str, Any]) -> None:
    for row in [*(harness.get("setup_rows") or []), *(harness.get("rows") or [])]:
        row["status"] = "dry_run"
        row["reason"] = "dry run requested; command was not executed"
        row["updated_at"] = _utc_timestamp()


def _mark_explicit_runtime_map_prior(harness: dict[str, Any], prior_path: str) -> None:
    prior = Path(prior_path)
    for row in harness.get("setup_rows") or []:
        row["runtime_map_prior"] = str(prior)
        row["updated_at"] = _utc_timestamp()
        if prior.is_file():
            row["status"] = "artifact_success"
            row["behavior_status"] = "artifact_success"
            row["reason"] = (
                "using explicit runtime_map_prior; setup command was not executed by this harness"
            )
            row["run_dir"] = str(prior.parent)
            _refresh_row_artifacts(row, prior.parent)
        else:
            row["status"] = "failed"
            row["reason"] = "explicit runtime_map_prior does not exist"


def _merge_existing_state(
    harness: dict[str, Any],
    output_dir: Path,
    *,
    selected_row_ids: set[str],
) -> None:
    manifest_path = output_dir / "codex_cleanup_harness8.json"
    if not manifest_path.is_file():
        return
    try:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(existing, dict):
        return
    existing_setup = _rows_by_id(existing.get("setup_rows") or [])
    harness["setup_rows"] = [
        _merged_existing_row(existing_setup, row) for row in harness.get("setup_rows") or []
    ]
    existing_rows = _rows_by_id(existing.get("rows") or [])
    merged_rows = []
    for row in harness.get("rows") or []:
        row_id = str(row.get("row_id") or "")
        if row_id not in selected_row_ids and row_id in existing_rows:
            merged_rows.append(_merged_existing_row(existing_rows, row))
        else:
            merged_rows.append(row)
    harness["rows"] = merged_rows


def _merged_existing_row(
    existing_rows: dict[str, dict[str, Any]],
    row: dict[str, Any],
) -> dict[str, Any]:
    row_id = str(row.get("row_id") or "")
    existing = existing_rows.get(row_id)
    if existing is None:
        return row
    _refresh_row_from_evidence(existing)
    return existing


def _replace_runtime_map_prior(harness: dict[str, Any], prior_path: str) -> None:
    for row in harness.get("rows") or []:
        row["command"] = [
            (
                f"runtime_map_prior={prior_path}"
                if item == f"runtime_map_prior={RUNTIME_MAP_PRIOR_PLACEHOLDER}"
                else item
            )
            for item in row.get("command") or []
        ]
        row["rerun_command"] = row_rerun_command(row)


def _rows_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("row_id") or ""): row for row in rows if isinstance(row, dict)}


def _has_existing_row_evidence(row: dict[str, Any]) -> bool:
    return bool(
        row.get("run_result_path")
        or row.get("report_path")
        or row.get("runtime_map_path")
        or row.get("live_status")
        or row.get("run_dir")
        or row.get("exit_status") is not None
        or row.get("status") in {"success", "failed", "artifact_success", "launched"}
    )


def _is_setup_row(row: dict[str, Any]) -> bool:
    return str(row.get("grid_role") or "") == "setup"


def _rate_limit_evidence(row: dict[str, Any]) -> dict[str, Any] | None:
    live_status = row.get("live_status") if isinstance(row.get("live_status"), dict) else {}
    for key in ("reason", "error", "message", "phase"):
        evidence = _rate_limit_match(str(live_status.get(key) or ""), source=f"live_status.{key}")
        if evidence:
            return evidence

    run_dir_value = row.get("run_dir")
    if not run_dir_value:
        return None
    run_dir = Path(str(run_dir_value))
    paths = [run_dir / name for name in RATE_LIMIT_LOG_NAMES]
    paths.extend(sorted(run_dir.glob("codex-continuation-*.stderr.log")))
    paths.extend(sorted(run_dir.glob("codex-events*.jsonl")))
    for path in paths:
        if not path.is_file():
            continue
        evidence = _rate_limit_match(_tail_text(path), source=str(path.name))
        if evidence:
            return evidence
    return None


def _rate_limit_match(text: str, *, source: str) -> dict[str, Any] | None:
    lowered = text.lower()
    for pattern in RATE_LIMIT_PATTERNS:
        index = lowered.find(pattern)
        if index < 0:
            continue
        start = max(index - 90, 0)
        end = min(index + len(pattern) + 140, len(text))
        snippet = " ".join(text[start:end].split())
        return {"source": source, "pattern": pattern, "snippet": snippet}
    return None


def _tail_text(path: Path, *, max_bytes: int = 256_000) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(size - max_bytes, 0), os.SEEK_SET)
            data = handle.read(max_bytes)
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


def _command_for_row(row: dict[str, Any], *, just_bin: str) -> list[str]:
    command = [str(item) for item in row.get("command") or []]
    if command and command[0] == "just":
        command[0] = just_bin
    return command


def _latest_runtime_map(output_dir: Path, *, seed: int) -> Path | None:
    seed_dir = _latest_seed_dir(output_dir, seed=seed)
    if seed_dir is None:
        return None
    path = seed_dir / "runtime_metric_map.json"
    return path if path.is_file() else None


def _latest_seed_dir(output_dir: Path, *, seed: int) -> Path | None:
    direct = output_dir / f"seed-{seed}"
    if direct.is_dir():
        return direct
    candidates = sorted(
        path
        for path in output_dir.glob(f"*/seed-{seed}")
        if path.is_dir()
        and (
            (path / "run_result.json").is_file()
            or (path / "runtime_metric_map.json").is_file()
            or (path / "report.html").is_file()
            or (path / "live_status.json").is_file()
            or (path / "tmux_session.txt").is_file()
        )
    )
    return candidates[-1] if candidates else None


def _wait_for_live_terminal_status(
    run_dir: Path,
    *,
    timeout_s: float,
    poll_s: float,
) -> dict[str, Any] | None:
    status_path = run_dir / "live_status.json"
    if not status_path.is_file():
        return None
    deadline = time.monotonic() + timeout_s
    last_status = _read_status(status_path)
    while True:
        phase = str(last_status.get("phase") or "")
        if phase in {"finished", "failed"} and "exit_status" in last_status:
            return last_status
        if time.monotonic() >= deadline:
            timed_out = dict(last_status)
            timed_out["phase"] = "failed"
            timed_out["exit_status"] = 124
            timed_out["reason"] = "live row did not reach terminal status before timeout"
            return timed_out
        time.sleep(max(float(poll_s), 0.1))
        last_status = _read_status(status_path)


def _read_status(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"phase": "unknown"}
    return data if isinstance(data, dict) else {"phase": "unknown"}


def row_rerun_command(row: dict[str, Any]) -> str:
    env = row.get("env") or {}
    env_prefix = " ".join(f"{key}={value}" for key, value in sorted(env.items()))
    command = shell_join(row.get("command") or [])
    return f"{env_prefix} {command}".strip()


def _write_outputs(harness: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "codex_cleanup_harness8.json").write_text(
        json.dumps(harness, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "codex_cleanup_harness8.html").write_text(
        _render_report(harness),
        encoding="utf-8",
    )


def _render_report(harness: dict[str, Any]) -> str:
    setup_rows = "\n".join(_render_row(row) for row in harness.get("setup_rows") or [])
    rows = "\n".join(_render_row(row) for row in harness.get("rows") or [])
    if not setup_rows:
        setup_rows = '<tr><td colspan="11">No setup row.</td></tr>'
    if not rows:
        rows = '<tr><td colspan="11">No cleanup rows.</td></tr>'
    return (
        "\n".join(
            [
                "<!doctype html>",
                '<meta charset="utf-8">',
                "<title>Codex Cleanup Harness 8</title>",
                "<style>",
                "body{font-family:system-ui,sans-serif;max-width:1280px;margin:2rem auto;"
                "padding:0 1rem;color:#202331;background:#f7f8fb}",
                "table{border-collapse:collapse;width:100%;background:white;margin:1rem 0}",
                "th,td{border:1px solid #d9dee8;padding:.55rem;text-align:left;vertical-align:top}",
                "th{background:#edf1f7}",
                "code{background:#f0f3f8;padding:1px 4px;border-radius:4px;white-space:pre-wrap}",
                ".sub{color:#5f6675}",
                "</style>",
                "<h1>Codex Cleanup Harness 8</h1>",
                f'<p class="sub">{html.escape(str(harness.get("description") or ""))}</p>',
                "<h2>Setup</h2>",
                f"<table>{_thead()}{setup_rows}</table>",
                "<h2>Cleanup Rows</h2>",
                f"<table>{_thead()}{rows}</table>",
            ]
        )
        + "\n"
    )


def _thead() -> str:
    return (
        "<thead><tr><th>Row</th><th>Status</th><th>Behavior</th><th>Map</th><th>Lane</th>"
        "<th>Exact</th><th>Semantic</th><th>Sweep</th><th>Disturb</th>"
        "<th>Order</th><th>Elapsed</th><th>Report</th><th>Command / reason</th></tr></thead>"
    )


def _render_row(row: dict[str, Any]) -> str:
    axes = row.get("axes") or {}
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    report_path = str(row.get("report_path") or "")
    if report_path:
        report = f'<a href="{html.escape(report_path, quote=True)}">report.html</a>'
    else:
        report = ""
    exact = _ratio(metrics.get("exact_restored"), metrics.get("total_targets"))
    semantic = _ratio(metrics.get("semantic_accepted"), metrics.get("total_targets"))
    if not semantic:
        semantic = _ratio(metrics.get("score_semantic_accepted"), metrics.get("total_targets"))
    elapsed = metrics.get("total_elapsed_s")
    if isinstance(elapsed, (int, float)):
        elapsed_text = f"{float(elapsed):.1f}s"
    else:
        elapsed_text = ""
    order_errors = metrics.get("semantic_order_unrecovered_errors")
    if isinstance(order_errors, int):
        order_text = str(order_errors)
    else:
        order_text = ""
    reason = str(row.get("reason") or "")
    retry_text = ""
    retry_count = row.get("retry_count")
    if isinstance(retry_count, int) and retry_count:
        retry_text = f"<br>retry_count={retry_count}"
    infra_note = str(row.get("infra_note") or "")
    if infra_note:
        retry_text += f"<br>{html.escape(infra_note)}"
    command = str(row.get("rerun_command") or "")
    return (
        "<tr>"
        f"<td>{html.escape(str(row.get('label') or row.get('row_id') or 'row'))}"
        f"<br><code>{html.escape(str(row.get('row_id') or ''))}</code></td>"
        f"<td><code>{html.escape(str(row.get('status') or 'pending'))}</code></td>"
        f"<td><code>{html.escape(str(row.get('behavior_status') or ''))}</code></td>"
        f"<td><code>{html.escape(str(axes.get('map_mode') or ''))}</code></td>"
        f"<td><code>{html.escape(str(axes.get('perception_lane') or ''))}</code></td>"
        f"<td>{html.escape(exact)}</td>"
        f"<td>{html.escape(semantic)}</td>"
        f"<td>{html.escape(str(metrics.get('sweep_coverage_rate') or ''))}</td>"
        f"<td>{html.escape(str(metrics.get('disturbance_count') or ''))}</td>"
        f"<td>{html.escape(order_text)}</td>"
        f"<td>{html.escape(elapsed_text)}</td>"
        f"<td>{report}</td>"
        f"<td><code>{html.escape(command)}</code><br>{html.escape(reason)}{retry_text}</td>"
        "</tr>"
    )


def _ratio(value: Any, total: Any) -> str:
    if isinstance(value, int) and isinstance(total, int) and total:
        return f"{value}/{total}"
    return ""


def _utc_timestamp() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
