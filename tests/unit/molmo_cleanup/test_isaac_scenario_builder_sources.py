from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.household.generated_mess import GENERATED_MESS_MANIFEST_SCHEMA
from scripts.isaac_lab_cleanup.isaac_scenario_builders import load_generated_mess_manifest


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "{not-json\n",
            r"generated mess manifest source must contain valid JSON object: .*manifest\.json",
        ),
        (
            "[]\n",
            r"generated mess manifest source must contain a JSON object: .*manifest\.json",
        ),
    ],
)
def test_isaac_generated_mess_manifest_rejects_bad_json_sources(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_generated_mess_manifest(manifest_path)


def test_isaac_generated_mess_manifest_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(
        FileNotFoundError,
        match=r"generated mess manifest source is missing: .*missing_manifest\.json",
    ):
        load_generated_mess_manifest(tmp_path / "missing_manifest.json")


def test_isaac_generated_mess_manifest_preserves_schema_validation(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"schema": "wrong_schema"}), encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            "generated mess manifest schema mismatch: "
            f"wrong_schema != {GENERATED_MESS_MANIFEST_SCHEMA}"
        ),
    ):
        load_generated_mess_manifest(manifest_path)


def test_isaac_generated_mess_manifest_loads_object_payload(tmp_path: Path) -> None:
    manifest = {"schema": GENERATED_MESS_MANIFEST_SCHEMA, "targets": []}
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert load_generated_mess_manifest(manifest_path) == manifest
