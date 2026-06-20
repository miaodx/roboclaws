from __future__ import annotations

from pathlib import Path

import pytest

from roboclaws.core.json_sources import read_json_object


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
