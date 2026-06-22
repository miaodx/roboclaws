from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

JsonlObjectRowIssueKind = Literal["read_error", "invalid_json", "non_object"]


@dataclass(frozen=True)
class JsonlObjectRowIssue:
    line_number: int
    kind: JsonlObjectRowIssueKind
    message: str


def read_json_value(path: Path, *, label: str) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"{label} source is missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} source must contain valid JSON: {path}") from exc


def parse_json_object_text(text: str, *, label: str, source: str = "") -> dict[str, Any]:
    source_suffix = f": {source}" if source else ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} source must contain valid JSON object{source_suffix}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} source must contain a JSON object{source_suffix}")
    return payload


def read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} source is missing: {path}")
    return parse_json_object_text(path.read_text(encoding="utf-8"), label=label, source=str(path))


def json_source_type_name(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unknown"
    return type(payload).__name__


def read_jsonl_objects(path: Path, *, label: str) -> list[dict[str, Any]]:
    return [row for _, row in read_jsonl_object_rows(path, label=label)]


def read_jsonl_object_rows(path: Path, *, label: str) -> list[tuple[int, dict[str, Any]]]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} source is missing: {path}")
    rows, issues = collect_jsonl_object_rows(path, label=label)
    if issues:
        issue = issues[0]
        if issue.kind == "read_error":
            raise ValueError(f"{label} source cannot be read: {path}: {issue.message}")
        if issue.kind == "invalid_json":
            raise ValueError(
                f"{label} source row must contain valid JSON object: "
                f"{path}:{issue.line_number}: {issue.message}"
            )
        raise ValueError(
            f"{label} source row must contain a JSON object: {path}:{issue.line_number}"
        )
    return rows


def collect_jsonl_object_rows(
    path: Path, *, label: str
) -> tuple[list[tuple[int, dict[str, Any]]], tuple[JsonlObjectRowIssue, ...]]:
    if not path.is_file():
        return [], ()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [], (JsonlObjectRowIssue(line_number=0, kind="read_error", message=str(exc)),)

    rows: list[tuple[int, dict[str, Any]]] = []
    issues: list[JsonlObjectRowIssue] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            issues.append(
                JsonlObjectRowIssue(
                    line_number=line_number,
                    kind="invalid_json",
                    message=exc.msg,
                )
            )
            continue
        if not isinstance(row, dict):
            issues.append(
                JsonlObjectRowIssue(
                    line_number=line_number,
                    kind="non_object",
                    message=f"{label} source row must contain a JSON object",
                )
            )
            continue
        rows.append((line_number, row))
    return rows, tuple(issues)


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
