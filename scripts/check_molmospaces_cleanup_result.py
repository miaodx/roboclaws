#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a MolmoSpaces cleanup run_result.")
    parser.add_argument("run_result", type=Path)
    parser.add_argument("--require-public-planner", action="store_true")
    parser.add_argument("--expect-task")
    parser.add_argument("--expect-backend")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = json.loads(args.run_result.read_text(encoding="utf-8"))
    score = data["score"]
    assert data["cleanup_status"] == "success", data
    assert data["primitive_provenance"] == "api_semantic", data
    if args.expect_backend is not None:
        assert data.get("backend") == args.expect_backend, data
    if args.expect_task is not None:
        assert data.get("task_prompt") == args.expect_task, data
    if args.require_public_planner:
        assert data.get("planner") == "public_heuristic", data
        assert data.get("planner_uses_private_manifest") is False, data
    assert score["restored_count"] >= score["success_threshold"], data
    report = Path(data["artifacts"]["report"])
    assert report.is_file(), report
    print(f"molmo-cleanup ok: {args.run_result} -> {report}")


if __name__ == "__main__":
    main()
