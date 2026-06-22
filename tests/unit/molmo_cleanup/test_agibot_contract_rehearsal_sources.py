from __future__ import annotations

from pathlib import Path

import pytest

from roboclaws.household import agibot_contract_rehearsal as rehearsal


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "{not-json\n",
            (
                "MolmoSpaces Agibot contract rehearsal artifact source must contain "
                r"valid JSON object: .*context\.json"
            ),
        ),
        (
            "[]\n",
            (
                "MolmoSpaces Agibot contract rehearsal artifact source must contain "
                r"a JSON object: .*context\.json"
            ),
        ),
    ],
)
def test_agibot_contract_rehearsal_context_source_rejects_bad_json(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    context_path = tmp_path / "context.json"
    context_path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        rehearsal._agibot_map_reference(
            context_json=context_path,
            agibot_map_artifact_dir=None,
        )


def test_agibot_contract_rehearsal_context_source_rejects_missing_json(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        FileNotFoundError,
        match=(
            "MolmoSpaces Agibot contract rehearsal artifact source is missing: "
            r".*missing_context\.json"
        ),
    ):
        rehearsal._agibot_map_reference(
            context_json=tmp_path / "missing_context.json",
            agibot_map_artifact_dir=None,
        )


def test_agibot_contract_rehearsal_context_source_loads_object_payload(
    tmp_path: Path,
) -> None:
    context_path = tmp_path / "context.json"
    context_path.write_text(
        """
        {
          "schema": "agibot_map_context_v1",
          "environment_id": "agibot-test-map",
          "map_version": "test-v1",
          "frame_id": "map",
          "rooms": [{"id": "kitchen"}],
          "fixtures": [{"id": "table"}],
          "inspection_waypoints": [{"waypoint_id": "wp_1"}],
          "map_source": {"type": "agibot", "id": "12", "name": "Map 12"}
        }
        """,
        encoding="utf-8",
    )

    reference = rehearsal._agibot_map_reference(
        context_json=context_path,
        agibot_map_artifact_dir=None,
    )

    assert reference["context_schema"] == "agibot_map_context_v1"
    assert reference["environment_id"] == "agibot-test-map"
    assert reference["map_version"] == "test-v1"
    assert reference["frame_id"] == "map"
    assert reference["room_count"] == 1
    assert reference["fixture_count"] == 1
    assert reference["inspection_waypoint_count"] == 1
    assert reference["map_source"] == {
        "type": "agibot",
        "id": "12",
        "name": "Map 12",
    }
