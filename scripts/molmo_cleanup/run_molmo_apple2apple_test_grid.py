#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.apple2apple_test_grid import (  # noqa: E402
    DEFAULT_MAP_BUNDLE,
    RUNTIME_MAP_PRIOR_PLACEHOLDER,
    build_apple2apple_test_grid,
    mark_grid_dry_run,
    row_rerun_command,
    write_grid_manifest,
    write_grid_report,
)
from roboclaws.molmo_cleanup.realworld_contract import DEFAULT_REALWORLD_TASK  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create or execute the MolmoSpaces apple-to-apple cleanup test grid "
            "for online/offline semantic-map comparison."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/molmo/apple2apple-grid"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--generated-mess-count", type=int, default=10)
    parser.add_argument("--task", default=DEFAULT_REALWORLD_TASK)
    parser.add_argument("--map-bundle", default=DEFAULT_MAP_BUNDLE)
    parser.add_argument("--runtime-map-prior", default="")
    parser.add_argument("--visual-grounding-timeout-s", default="auto")
    parser.add_argument(
        "--row",
        action="append",
        default=[],
        help="Only execute or mark matching cleanup row ids. May be repeated.",
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--just-bin", default="just")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    grid = build_apple2apple_test_grid(
        output_dir=args.output_dir,
        seed=args.seed,
        generated_mess_count=args.generated_mess_count,
        task=args.task,
        map_bundle=args.map_bundle,
        runtime_map_prior=args.runtime_map_prior,
        visual_grounding_timeout_s=args.visual_grounding_timeout_s,
    )

    if not args.execute:
        mark_grid_dry_run(grid)
        _write_outputs(grid, args.output_dir)
        print(f"apple-to-apple grid manifest: {args.output_dir / 'apple2apple_test_grid.json'}")
        print(f"apple-to-apple grid report: {args.output_dir / 'apple2apple_test_grid.html'}")
        return 0

    status = _execute_grid(grid, args)
    _write_outputs(grid, args.output_dir)
    return status


def _execute_grid(grid: dict[str, Any], args: argparse.Namespace) -> int:
    selected_rows = _selected_rows(grid, filters=set(args.row))
    if not selected_rows:
        raise SystemExit("no cleanup rows selected")

    for row in grid.get("rows") or []:
        if row not in selected_rows:
            row["status"] = "not_selected"
            row["reason"] = "row was not selected for this execution"

    prior_path = args.runtime_map_prior
    if any(row.get("requires_runtime_map_prior") for row in selected_rows) and not prior_path:
        prior_path = _execute_prior_build(grid, args)
        grid["runtime_map_prior"] = prior_path
        _replace_runtime_map_prior(grid, prior_path)

    failure_count = 0
    for row in selected_rows:
        status = _execute_row(row, args)
        if status != 0:
            failure_count += 1
            if not args.continue_on_error:
                break
    return 1 if failure_count else 0


def _execute_prior_build(grid: dict[str, Any], args: argparse.Namespace) -> str:
    setup_rows = list(grid.get("setup_rows") or [])
    if not setup_rows:
        raise RuntimeError("offline rows require a runtime-map prior but no setup row exists")
    row = setup_rows[0]
    status = _execute_row(row, args)
    if status != 0:
        raise RuntimeError("offline semantic-map prior build failed")
    prior = _latest_runtime_map(Path(row["output_dir"]), seed=args.seed)
    if prior is None:
        raise RuntimeError("semantic-map prior build produced no runtime_metric_map.json")
    row["runtime_map_prior"] = str(prior)
    return str(prior)


def _execute_row(row: dict[str, Any], args: argparse.Namespace) -> int:
    command = _command_for_row(row, just_bin=args.just_bin)
    env = os.environ.copy()
    env.update({str(key): str(value) for key, value in (row.get("env") or {}).items()})
    print("+ " + row_rerun_command({**row, "command": command}))
    status = subprocess.run(command, env=env, check=False).returncode
    row["exit_status"] = status
    row["updated_at"] = _now()
    run_dir = _latest_seed_dir(Path(row["output_dir"]), seed=args.seed)
    if run_dir is not None:
        row["run_dir"] = str(run_dir)
        report_path = run_dir / "report.html"
        if report_path.is_file():
            row["report_path"] = str(report_path)
    if status == 0:
        row["status"] = "success" if row.get("run_dir") else "launched"
        row["reason"] = (
            "" if row.get("run_dir") else "command returned before seed artifact existed"
        )
    else:
        row["status"] = "failed"
        row["reason"] = f"command exited with status {status}"
    return status


def _selected_rows(grid: dict[str, Any], *, filters: set[str]) -> list[dict[str, Any]]:
    rows = list(grid.get("rows") or [])
    if not filters:
        return rows
    return [row for row in rows if str(row.get("row_id") or "") in filters]


def _replace_runtime_map_prior(grid: dict[str, Any], prior_path: str) -> None:
    for row in grid.get("rows") or []:
        command = [
            (
                f"runtime_map_prior={prior_path}"
                if item == f"runtime_map_prior={RUNTIME_MAP_PRIOR_PLACEHOLDER}"
                else item
            )
            for item in row.get("command") or []
        ]
        row["command"] = command
        row["rerun_command"] = row_rerun_command(row)


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
        )
    )
    return candidates[-1] if candidates else None


def _write_outputs(grid: dict[str, Any], output_dir: Path) -> None:
    write_grid_manifest(grid, output_dir)
    write_grid_report(grid, output_dir)


def _now() -> str:
    import datetime as dt

    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())
