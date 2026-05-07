from __future__ import annotations

from collections.abc import Callable
from typing import Any

from roboclaws.games.common import _MOVE_ACTIONS


def normalize_navigation_action(
    *,
    action: Any,
    action_space: tuple[str, ...],
    safe_fallback_action: str,
    current_state: Any,
    last_action_by_agent: dict[int, str | None],
    agent_id: int,
) -> str:
    """Clamp a model action to the game-local action space and escape repeats."""
    action_name = str(action or "").strip()
    if action_name not in action_space:
        return safe_fallback_action

    if (
        not current_state.last_action_success
        and action_name in _MOVE_ACTIONS
        and last_action_by_agent.get(agent_id) == action_name
    ):
        return safe_fallback_action
    return action_name


def decide_turn(
    *,
    provider: Any,
    images: list[Any],
    prompt_state: dict[str, Any],
    normalize_action: Callable[[Any], str],
    override_action: Callable[[str, dict[str, Any]], tuple[str, str | None]] | None = None,
) -> dict[str, Any]:
    """Run the shared provider-decision portion of one control turn."""
    raw_response = provider.get_action(images=images, state=prompt_state)
    raw_action = raw_response.get("action")
    action_name = normalize_action(raw_action)
    override_reason: str | None = None
    if override_action is not None:
        action_name, override_reason = override_action(action_name, prompt_state)
    decision = {
        "reasoning": str(raw_response.get("reasoning", "")),
        "action": action_name,
        "raw_action": raw_action,
    }
    if override_action is not None:
        decision["override_reason"] = override_reason
    return decision


def execute_control_turn(
    *,
    engine: Any,
    agent_count: int,
    current_agent: int,
    action: Any,
    normalize_action: Callable[[Any], str],
    after_step: Callable[[int, str, Any], None],
) -> tuple[str, int]:
    """Apply one normalized action and return ``(action_name, next_agent)``."""
    action_name = normalize_action(action)
    new_state = engine.step(agent_id=current_agent, action=action_name)
    after_step(current_agent, action_name, new_state)
    return action_name, (current_agent + 1) % agent_count
