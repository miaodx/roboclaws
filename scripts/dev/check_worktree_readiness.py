#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

REQUIRED_ASSETS = (
    "vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot/nav2.yaml",
    "vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot/occupancy.pgm",
    "assets/maps/molmospaces/procthor-10k-val/0/map.yaml",
    "assets/maps/molmospaces/procthor-10k-val/0/semantics.json",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail-loud readiness check for Roboclaws worktree/dev-agent runs."
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable readiness.")
    parser.add_argument(
        "--bootstrap-submodules",
        action="store_true",
        help="Run git submodule sync/update before checking pinned vendor assets.",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root to check.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()
    if args.bootstrap_submodules:
        _run(["git", "submodule", "sync", "--recursive"], cwd=repo_root)
        _run(["git", "submodule", "update", "--init", "--recursive"], cwd=repo_root)

    readiness = readiness_report(repo_root)
    if args.json:
        print(json.dumps(readiness, indent=2, sort_keys=True))
    else:
        _print_human(readiness)
    return 0 if readiness["ok"] else 1


def readiness_report(repo_root: Path) -> dict[str, Any]:
    venv_python = repo_root / ".venv" / "bin" / "python"
    venv_pytest = repo_root / ".venv" / "bin" / "pytest"
    missing_assets = [path for path in REQUIRED_ASSETS if not (repo_root / path).exists()]
    submodules = _submodule_status(repo_root)
    bad_submodules = [
        row
        for row in submodules
        if row["status"] in {"missing", "uninitialized", "modified", "merge-conflict", "unknown"}
    ]
    checks = {
        "venv_python": venv_python.is_file() and venv_python.stat().st_mode & 0o111 != 0,
        "venv_pytest": venv_pytest.is_file() and venv_pytest.stat().st_mode & 0o111 != 0,
        "required_assets": not missing_assets,
        "submodules": not bad_submodules,
    }
    return {
        "schema": "roboclaws_worktree_readiness_v1",
        "ok": all(checks.values()),
        "repo_root": str(repo_root),
        "checks": checks,
        "python": str(venv_python),
        "pytest": str(venv_pytest),
        "missing_assets": missing_assets,
        "submodules": submodules,
        "bad_submodules": bad_submodules,
        "remediation": _remediation(checks, missing_assets, bad_submodules),
    }


def _submodule_status(repo_root: Path) -> list[dict[str, str]]:
    result = subprocess.run(
        ["git", "submodule", "status", "--recursive"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return [
            {
                "path": "<git-submodule-status>",
                "status": "unknown",
                "detail": result.stderr.strip() or result.stdout.strip(),
            }
        ]
    rows: list[dict[str, str]] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line:
            continue
        prefix = raw_line[0]
        parts = raw_line[1:].split(maxsplit=2)
        commit = parts[0] if parts else ""
        path = parts[1] if len(parts) > 1 else ""
        detail = parts[2] if len(parts) > 2 else ""
        status = {
            " ": "ok",
            "-": "uninitialized",
            "+": "modified",
            "U": "merge-conflict",
        }.get(prefix, "unknown")
        rows.append({"path": path, "commit": commit, "status": status, "detail": detail})
    return rows


def _remediation(
    checks: dict[str, bool], missing_assets: list[str], bad_submodules: list[dict[str, str]]
) -> list[str]:
    steps: list[str] = []
    if not checks["venv_python"] or not checks["venv_pytest"]:
        steps.append("run `uv sync --extra dev` in this checkout")
    if bad_submodules or missing_assets:
        steps.append("run `git submodule sync --recursive`")
        steps.append("run `git submodule update --init --recursive`")
    return steps


def _print_human(readiness: dict[str, Any]) -> None:
    status = "ok" if readiness["ok"] else "not ready"
    print(f"worktree readiness: {status}")
    for name, ok in readiness["checks"].items():
        print(f"- {name}: {'ok' if ok else 'fail'}")
    if readiness["missing_assets"]:
        print("missing assets:")
        for path in readiness["missing_assets"]:
            print(f"- {path}")
    if readiness["bad_submodules"]:
        print("submodule issues:")
        for row in readiness["bad_submodules"]:
            print(f"- {row['path']}: {row['status']} {row.get('detail', '')}".rstrip())
    if readiness["remediation"]:
        print("remediation:")
        for step in readiness["remediation"]:
            print(f"- {step}")


def _run(command: list[str], *, cwd: Path) -> None:
    result = subprocess.run(command, cwd=cwd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
