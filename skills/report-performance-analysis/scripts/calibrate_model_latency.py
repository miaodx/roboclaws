#!/usr/bin/env python3
"""Fit simple model-latency coefficients from sanitized model-call rows."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate model latency from roboclaws_model_call_metric_v1 rows.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("model_call_metrics", type=Path, nargs="+")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-samples", type=int, default=5)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    rows = [
        row
        for path in args.model_call_metrics
        for row in _read_jsonl(path)
        if row.get("schema") == "roboclaws_model_call_metric_v1"
    ]
    usable = [
        row
        for row in rows
        if _float_or_none(row.get("duration_s")) is not None
        and _int_or_none(row.get("uncached_input_tokens")) is not None
        and _int_or_none(row.get("output_tokens")) is not None
    ]
    packet: dict[str, Any] = {
        "schema": "roboclaws_model_latency_calibration_v1",
        "sample_count": len(usable),
        "total_row_count": len(rows),
        "available": len(usable) >= args.min_samples,
        "limitations": [],
    }
    if len(usable) < args.min_samples:
        packet["limitations"].append("insufficient_samples")
    else:
        total_duration = sum(float(row["duration_s"]) for row in usable)
        total_uncached = sum(int(row.get("uncached_input_tokens") or 0) for row in usable)
        total_output = sum(int(row.get("output_tokens") or 0) for row in usable)
        packet["coefficients"] = {
            "intercept_s": 0.0,
            "uncached_input_s_per_token": _safe_div(total_duration * 0.5, total_uncached),
            "output_s_per_token": _safe_div(total_duration * 0.5, total_output),
            "cached_input_s_per_token": 0.0,
            "reasoning_s_per_token": 0.0,
            "image_s_per_unit": 0.0,
        }
        packet["limitations"].append(
            "simple_two-feature_fit_for_diagnostics_only_requires_named_dataset_review"
        )

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(packet, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"calibration: {args.output}")
    else:
        print(json.dumps(packet, indent=2, sort_keys=True))
    return 0 if packet["available"] else 1


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
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


def _safe_div(numerator: float, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 9)


if __name__ == "__main__":
    raise SystemExit(main())
