from __future__ import annotations

from unittest.mock import MagicMock

from roboclaws.games.common import _DECISION_ACTIONS
from roboclaws.games.turns import decide_turn, execute_control_turn, normalize_navigation_action


def test_normalize_navigation_action_uses_safe_fallback_for_unknown_action() -> None:
    action = normalize_navigation_action(
        action="Teleport",
        action_space=_DECISION_ACTIONS,
        safe_fallback_action="RotateRight",
        current_state=MagicMock(last_action_success=True),
        last_action_by_agent={0: None},
        agent_id=0,
    )

    assert action == "RotateRight"


def test_normalize_navigation_action_allows_different_escape_move_after_failed_move() -> None:
    action = normalize_navigation_action(
        action="MoveLeft",
        action_space=_DECISION_ACTIONS,
        safe_fallback_action="RotateRight",
        current_state=MagicMock(last_action_success=False),
        last_action_by_agent={0: "MoveAhead"},
        agent_id=0,
    )

    assert action == "MoveLeft"


def test_decide_turn_queries_provider_and_normalizes_action() -> None:
    provider = MagicMock()
    provider.get_action.return_value = {"reasoning": "bad", "action": "Teleport"}

    decision = decide_turn(
        provider=provider,
        images=["a", "b", "c"],
        prompt_state={"my_agent_id": 0},
        normalize_action=lambda action: "RotateRight" if action == "Teleport" else str(action),
    )

    assert decision == {"reasoning": "bad", "action": "RotateRight", "raw_action": "Teleport"}
    provider.get_action.assert_called_once()


def test_execute_control_turn_steps_engine_and_advances_round_robin() -> None:
    engine = MagicMock()
    engine.step.return_value = MagicMock(last_action_success=True)
    after_step_calls = []

    action_name, next_agent = execute_control_turn(
        engine=engine,
        agent_count=3,
        current_agent=1,
        action="MoveAhead",
        normalize_action=lambda action: str(action),
        after_step=lambda agent_id, action_name, new_state: after_step_calls.append(
            (agent_id, action_name, new_state)
        ),
    )

    assert action_name == "MoveAhead"
    assert next_agent == 2
    engine.step.assert_called_once_with(agent_id=1, action="MoveAhead")
    assert after_step_calls == [(1, "MoveAhead", engine.step.return_value)]
