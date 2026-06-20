from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any


def read_json_value(path: Path, *, label: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{label} source is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} source must contain valid JSON: {path}") from exc


def read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} source is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} source must contain valid JSON object: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} source must contain a JSON object: {path}")
    return payload


def json_source_type_name(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    return type(payload).__name__


def read_jsonl_objects(path: Path, *, label: str) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} source is missing: {path}")
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"{label} source cannot be read: {path}: {exc}") from exc

    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{label} source row must contain valid JSON object: "
                f"{path}:{line_number}: {exc.msg}"
            ) from exc
        if not isinstance(row, dict):
            raise ValueError(f"{label} source row must contain a JSON object: {path}:{line_number}")
        rows.append(row)
    return rows


def read_gzip_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} source is missing: {path}")
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            payload = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} source must contain valid JSON object: {path}") from exc
    except OSError as exc:
        raise ValueError(f"{label} source cannot be read as gzip JSON: {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} source must contain a JSON object: {path}")
    return payload
