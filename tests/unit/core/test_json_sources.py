from __future__ import annotations

from pathlib import Path

import pytest

from roboclaws.core.json_sources import read_json_object, read_jsonl_objects


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("{not-json\n", r"sample source must contain valid JSON object: .*source\.json"),
        ("[]\n", r"sample source must contain a JSON object: .*source\.json"),
    ],
)
def test_read_json_object_rejects_malformed_sources(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    path = tmp_path / "source.json"
    path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        read_json_object(path, label="sample")


def test_read_json_object_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"sample source is missing: .*missing\.json"):
        read_json_object(tmp_path / "missing.json", label="sample")


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            '{"ok": true}\n{not-json\n',
            r"sample events source row must contain valid JSON object: .*events\.jsonl:2",
        ),
        (
            '{"ok": true}\n[]\n',
            r"sample events source row must contain a JSON object: .*events\.jsonl:2",
        ),
    ],
)
def test_read_jsonl_objects_rejects_malformed_rows(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        read_jsonl_objects(path, label="sample events")


def test_read_jsonl_objects_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(
        FileNotFoundError, match=r"sample events source is missing: .*missing\.jsonl"
    ):
        read_jsonl_objects(tmp_path / "missing.jsonl", label="sample events")


def test_read_jsonl_objects_returns_object_rows_and_skips_blank_lines(tmp_path: Path) -> None:
    path = tmp_path / "events.jsonl"
    path.write_text('{"event": "start"}\n\n{"event": "done"}\n', encoding="utf-8")

    assert read_jsonl_objects(path, label="sample events") == [
        {"event": "start"},
        {"event": "done"},
    ]
