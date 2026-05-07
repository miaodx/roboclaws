from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from roboclaws.core.engine import NAVIGATION_ACTIONS

SAFE_FALLBACK_ACTION = "RotateRight"
ALLOWED_NAVIGATION_ACTIONS = tuple(NAVIGATION_ACTIONS)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass(frozen=True)
class ActionDecision:
    reasoning: str
    action: str

    def to_dict(self) -> dict[str, str]:
        return {"reasoning": self.reasoning, "action": self.action}


def action_decision_from_fields(reasoning: Any, action: Any) -> ActionDecision:
    """Return a validated navigation decision from already-split fields."""
    reasoning_text = str(reasoning or "")
    action_text = str(action or "").strip()
    if action_text not in ALLOWED_NAVIGATION_ACTIONS:
        action_text = SAFE_FALLBACK_ACTION
    return ActionDecision(reasoning=reasoning_text, action=action_text)


def fallback_action_decision(raw: Any) -> ActionDecision:
    """Return the safe fallback decision while preserving debug context."""
    return ActionDecision(
        reasoning=str(raw or "").strip()[:500],
        action=SAFE_FALLBACK_ACTION,
    )


def parse_action_decision(raw_content: Any) -> ActionDecision:
    """Parse and validate a model/Gateway navigation decision.

    Accepts plain JSON, fenced JSON, or prose containing one JSON object.  Any
    malformed, missing, or unknown action falls back to the shared safe action.
    """
    content = str(raw_content or "")
    stripped = _CODE_FENCE_RE.sub("", content).strip()
    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start : end + 1]

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return fallback_action_decision(content)

    if not isinstance(parsed, dict) or "action" not in parsed:
        return fallback_action_decision(content)
    return action_decision_from_fields(parsed.get("reasoning", ""), parsed.get("action", ""))
