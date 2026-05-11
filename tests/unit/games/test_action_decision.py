from __future__ import annotations

import pytest

from roboclaws.core.action_decision import (
    SAFE_FALLBACK_ACTION,
    action_decision_from_fields,
    parse_action_decision,
)


@pytest.mark.parametrize(
    ("raw", "expected_reasoning", "expected_action"),
    [
        ('{"reasoning": "clear path", "action": "MoveAhead"}', "clear path", "MoveAhead"),
        (
            '```json\n{"reasoning": "turn", "action": "RotateLeft", "extra": true}\n```',
            "turn",
            "RotateLeft",
        ),
        (
            'I will do this: {"reasoning": "back up", "action": "MoveBack"}',
            "back up",
            "MoveBack",
        ),
    ],
)
def test_parse_action_decision_accepts_valid_json_variants(
    raw: str,
    expected_reasoning: str,
    expected_action: str,
) -> None:
    decision = parse_action_decision(raw)

    assert decision.to_dict() == {
        "reasoning": expected_reasoning,
        "action": expected_action,
    }


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        '{"reasoning": "missing action"}',
        '["MoveAhead"]',
    ],
)
def test_parse_action_decision_falls_back_for_invalid_output(raw: str) -> None:
    decision = parse_action_decision(raw)

    assert decision.action == SAFE_FALLBACK_ACTION
    assert raw[:40].strip() in decision.reasoning


def test_parse_action_decision_preserves_reasoning_on_unknown_action() -> None:
    decision = parse_action_decision('{"reasoning": "bad action", "action": "WalkIntoWall"}')

    assert decision.action == SAFE_FALLBACK_ACTION
    assert decision.reasoning == "bad action"


def test_action_decision_from_fields_validates_provider_objects() -> None:
    assert action_decision_from_fields("ok", "MoveRight").to_dict() == {
        "reasoning": "ok",
        "action": "MoveRight",
    }

    fallback = action_decision_from_fields("bad", "Jump")
    assert fallback.action == SAFE_FALLBACK_ACTION
    assert fallback.reasoning == "bad"
