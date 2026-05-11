"""Tests for roboclaws/openclaw/skill.py."""

from __future__ import annotations

import base64
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.openclaw.skill import AI2THORNavigatorSkill, SkillInput, SkillOutput

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

_SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills" / "ai2thor-navigator"
_SOULS_DIR = _SKILLS_DIR / "souls"


def _make_frame(h: int = 8, w: int = 8) -> np.ndarray:
    """Return a small solid-colour RGB frame."""
    return np.full((h, w, 3), 128, dtype=np.uint8)


def _mock_provider(action: str = "MoveAhead", reasoning: str = "test reasoning") -> MagicMock:
    provider = MagicMock()
    provider.get_action.return_value = {"action": action, "reasoning": reasoning}
    return provider


def _make_skill_input(agent_id: int = 0) -> SkillInput:
    return SkillInput(
        agent_id=agent_id,
        camera_frame=_make_frame(),
        overhead_frame=_make_frame(),
        game_state={"step": 1, "remaining_steps": 99, "game": "territory"},
    )


# ---------------------------------------------------------------------------
# AI2THORNavigatorSkill — initialisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("soul_name", ["aggressive", "cooperative", "defensive"])
def test_skill_init_loads_builtin_soul(soul_name: str):
    skill = AI2THORNavigatorSkill(_mock_provider(), soul=soul_name)
    assert len(skill._soul_text) > 0


def test_skill_init_with_raw_soul_string():
    raw = "You are a wandering robot. Move randomly."
    skill = AI2THORNavigatorSkill(_mock_provider(), soul=raw)
    assert skill._soul_text == raw


def test_skill_default_soul_is_cooperative():
    skill = AI2THORNavigatorSkill(_mock_provider())
    # default soul is "cooperative"; if file exists it loads the preset
    assert len(skill._soul_text) > 0


# ---------------------------------------------------------------------------
# list_souls
# ---------------------------------------------------------------------------


def test_list_souls_returns_three_presets():
    souls = AI2THORNavigatorSkill.list_souls()
    assert set(souls) == {"aggressive", "defensive", "cooperative"}


def test_list_souls_is_sorted():
    souls = AI2THORNavigatorSkill.list_souls()
    assert souls == sorted(souls)


# ---------------------------------------------------------------------------
# encode_frame
# ---------------------------------------------------------------------------


def test_encode_frame_returns_valid_base64():
    frame = _make_frame(16, 16)
    b64 = AI2THORNavigatorSkill.encode_frame(frame)
    decoded = base64.b64decode(b64)
    # JPEG magic bytes: FF D8 FF
    assert decoded[:3] == b"\xff\xd8\xff"


def test_encode_frame_different_frames_produce_different_strings():
    frame_a = np.zeros((8, 8, 3), dtype=np.uint8)
    frame_b = np.full((8, 8, 3), 200, dtype=np.uint8)
    enc = AI2THORNavigatorSkill.encode_frame
    assert enc(frame_a) != enc(frame_b)


# ---------------------------------------------------------------------------
# run — happy path
# ---------------------------------------------------------------------------


def test_run_returns_skill_output():
    skill = AI2THORNavigatorSkill(_mock_provider("RotateRight", "I see a wall"), soul="cooperative")
    out = skill.run(_make_skill_input())
    assert isinstance(out, SkillOutput)
    assert out.action == "RotateRight"
    assert out.reasoning == "I see a wall"


def test_run_passes_both_frames_to_provider():
    provider = _mock_provider()
    skill = AI2THORNavigatorSkill(provider, soul="aggressive")
    skill.run(_make_skill_input())
    call_args = provider.get_action.call_args
    images = call_args[1]["images"] if "images" in call_args[1] else call_args[0][0]
    assert len(images) == 2


def test_run_injects_agent_id_into_state():
    provider = _mock_provider()
    skill = AI2THORNavigatorSkill(provider, soul="defensive")
    skill.run(_make_skill_input(agent_id=3))
    call_args = provider.get_action.call_args
    state = call_args[1]["state"] if "state" in call_args[1] else call_args[0][1]
    assert state["agent_id"] == 3


def test_run_injects_soul_into_state():
    provider = _mock_provider()
    skill = AI2THORNavigatorSkill(provider, soul="cooperative")
    skill.run(_make_skill_input())
    call_args = provider.get_action.call_args
    state = call_args[1]["state"] if "state" in call_args[1] else call_args[0][1]
    assert "soul" in state
    assert len(state["soul"]) > 0


def test_run_injects_available_actions_into_state():
    provider = _mock_provider()
    skill = AI2THORNavigatorSkill(provider, soul="cooperative")
    skill.run(_make_skill_input())
    call_args = provider.get_action.call_args
    state = call_args[1]["state"] if "state" in call_args[1] else call_args[0][1]
    assert state["available_actions"] == NAVIGATION_ACTIONS


# ---------------------------------------------------------------------------
# run — invalid action fallback
# ---------------------------------------------------------------------------


def test_run_falls_back_on_invalid_action():
    provider = _mock_provider(action="INVALID_ACTION")
    skill = AI2THORNavigatorSkill(provider, soul="cooperative")
    out = skill.run(_make_skill_input())
    assert out.action == "MoveAhead"


def test_run_falls_back_when_action_missing():
    provider = MagicMock()
    provider.get_action.return_value = {"reasoning": "hmm"}
    skill = AI2THORNavigatorSkill(provider, soul="cooperative")
    out = skill.run(_make_skill_input())
    assert out.action == "MoveAhead"


def test_run_accepts_all_valid_actions():
    for valid_action in NAVIGATION_ACTIONS:
        provider = _mock_provider(action=valid_action)
        skill = AI2THORNavigatorSkill(provider, soul="cooperative")
        out = skill.run(_make_skill_input())
        assert out.action == valid_action


# ---------------------------------------------------------------------------
# SOUL files exist and have content
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("soul_name", ["aggressive", "defensive", "cooperative"])
def test_soul_file_has_content(soul_name: str):
    soul_path = _SOULS_DIR / f"{soul_name}.md"
    text = soul_path.read_text(encoding="utf-8")
    assert len(text) > 50, f"Soul file {soul_name}.md is too short"


def test_skill_md_exists():
    assert (_SKILLS_DIR / "SKILL.md").exists()
