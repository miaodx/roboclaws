#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_POSITIVE_COUNTS = (
    "matched_entry_count",
    "labeled_entry_count",
    "renderable_labeled_prim_count",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a prepared MolmoSpaces flattened semantic USD summary."
    )
    parser.add_argument("path", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        summary = _read_json_object(args.path, label="prepared semantic USD summary")
        assert_prepared_semantic_usd_summary_ready(summary, path=args.path)
    except (FileNotFoundError, ValueError, AssertionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(f"prepared semantic USD ready: {summary.get('output_usd_path')}")
    return 0


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must contain valid JSON object: {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object: {path}")
    return payload


def assert_prepared_semantic_usd_summary_ready(
    summary: dict[str, Any],
    *,
    path: Path | None = None,
) -> None:
    label = str(path) if path is not None else "<summary>"
    assert summary.get("status") == "ready", (
        f"prepared semantic USD is not ready: {label}: {summary.get('status')}"
    )
    for key in REQUIRED_POSITIVE_COUNTS:
        assert int(summary.get(key) or 0) > 0, f"prepared semantic USD missing {key}: {label}"
    assert summary.get("scene_metadata_copied") is True, (
        f"prepared semantic USD did not copy scene_metadata.json: {label}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
