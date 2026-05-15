from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "examples" / "openclaw"))

import openclaw_photo_task  # noqa: E402
from openclaw_photo_task import photo_task_kickoff_prompt  # noqa: E402


def test_photo_task_prompt_delegates_to_capture_skill() -> None:
    prompt = photo_task_kickoff_prompt(42)

    assert "skills/ai2thor-navigator/SKILL.md" in prompt
    assert "skills/capture-object-photo/SKILL.md" in prompt
    assert "scene_objects" in prompt
    assert "goto" in prompt
    assert "privileged helpers" in prompt
    assert "42" in prompt


def test_photo_task_launcher_opts_into_privileged_mcp_helpers() -> None:
    source = Path(openclaw_photo_task.__file__).read_text(encoding="utf-8")

    assert "allow_privileged_tools=True" in source
