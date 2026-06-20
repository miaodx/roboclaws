from __future__ import annotations

import gzip
from pathlib import Path

import pytest

from roboclaws.core.json_sources import (
    json_source_type_name,
    read_gzip_json_object,
    read_json_object,
    read_json_value,
    read_jsonl_objects,
)


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
    ("source", "type_name"),
    [
        ("[]\n", "list"),
        ('"value"\n', "str"),
    ],
)
def test_json_source_type_name_reports_parseable_payload_type(
    tmp_path: Path,
    source: str,
    type_name: str,
) -> None:
    path = tmp_path / "source.json"
    path.write_text(source, encoding="utf-8")

    assert json_source_type_name(path) == type_name


@pytest.mark.parametrize("source", ["{not-json\n", None])
def test_json_source_type_name_returns_unknown_for_unreadable_source(
    tmp_path: Path,
    source: str | None,
) -> None:
    path = tmp_path / "source.json"
    if source is not None:
        path.write_text(source, encoding="utf-8")

    assert json_source_type_name(path) == "unknown"


def test_read_json_value_returns_non_object_payload(tmp_path: Path) -> None:
    path = tmp_path / "source.json"
    path.write_text('[{"ok": true}]', encoding="utf-8")

    assert read_json_value(path, label="sample") == [{"ok": True}]


def test_read_json_value_rejects_malformed_source(tmp_path: Path) -> None:
    path = tmp_path / "source.json"
    path.write_text("{not-json\n", encoding="utf-8")

    with pytest.raises(ValueError, match=r"sample source must contain valid JSON: .*source\.json"):
        read_json_value(path, label="sample")


def test_read_json_value_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match=r"sample source is missing: .*missing\.json"):
        read_json_value(tmp_path / "missing.json", label="sample")


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


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("{not-json\n", r"sample gzip source must contain valid JSON object: .*source\.json\.gz"),
        ("[]\n", r"sample gzip source must contain a JSON object: .*source\.json\.gz"),
    ],
)
def test_read_gzip_json_object_rejects_malformed_sources(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    path = tmp_path / "source.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(source)

    with pytest.raises(ValueError, match=message):
        read_gzip_json_object(path, label="sample gzip")


def test_read_gzip_json_object_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(
        FileNotFoundError, match=r"sample gzip source is missing: .*missing\.json\.gz"
    ):
        read_gzip_json_object(tmp_path / "missing.json.gz", label="sample gzip")


def test_read_gzip_json_object_rejects_plain_json_source(tmp_path: Path) -> None:
    path = tmp_path / "source.json.gz"
    path.write_text('{"ok": true}', encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"sample gzip source cannot be read as gzip JSON: .*source\.json\.gz",
    ):
        read_gzip_json_object(path, label="sample gzip")


def test_read_gzip_json_object_returns_object_payload(tmp_path: Path) -> None:
    path = tmp_path / "source.json.gz"
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write('{"ok": true}\n')

    assert read_gzip_json_object(path, label="sample gzip") == {"ok": True}
