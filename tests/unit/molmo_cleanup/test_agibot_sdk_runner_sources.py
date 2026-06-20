from __future__ import annotations

from pathlib import Path

import pytest

from roboclaws.household.agibot_sdk_runner import AgibotSDKRunnerAdapter


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (
            "{not-json\n",
            "Agibot SDK runner artifact source must contain valid JSON object",
        ),
        ("[]\n", "Agibot SDK runner artifact source must contain a JSON object"),
    ],
)
def test_agibot_sdk_runner_context_source_rejects_malformed_json(
    tmp_path: Path, content: str, message: str
) -> None:
    context_path = tmp_path / "context.json"
    context_path.write_text(content, encoding="utf-8")
    adapter = AgibotSDKRunnerAdapter(
        context_json=context_path,
        run_dir=tmp_path / "run",
        runner_script=tmp_path / "runner.py",
    )

    with pytest.raises(ValueError, match=message):
        adapter.context_payload


def test_agibot_sdk_runner_context_source_loads_object_payload(tmp_path: Path) -> None:
    context_path = tmp_path / "context.json"
    context_path.write_text('{"inspection_waypoints": []}\n', encoding="utf-8")
    adapter = AgibotSDKRunnerAdapter(
        context_json=context_path,
        run_dir=tmp_path / "run",
        runner_script=tmp_path / "runner.py",
    )

    assert adapter.context_payload == {"inspection_waypoints": []}
