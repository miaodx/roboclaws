"""OpenClaw skill wrapper for AI2-THOR navigation.

Packages the VLM navigation loop as an OpenClaw-compatible skill that can be
run as an independent agent instance.  In Phase 2 each simulation agent maps
to one :class:`AI2THORNavigatorSkill` instance driven by its own SOUL preset.

Usage::

    from roboclaws.core.vlm import create_provider
    from roboclaws.openclaw.skill import AI2THORNavigatorSkill, SkillInput

    provider = create_provider("anthropic")
    skill = AI2THORNavigatorSkill(provider, soul="aggressive")

    output = skill.run(SkillInput(
        agent_id=0,
        camera_frame=agent_state.frame,
        overhead_frame=engine.get_overhead_frame(),
        game_state=game.get_state(),
    ))
    print(output.action)  # e.g. "MoveAhead"
"""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from roboclaws.core.engine import NAVIGATION_ACTIONS

# SOUL presets are stored alongside the skill definition
_SOULS_DIR: Path = (
    Path(__file__).resolve().parent.parent.parent / "skills" / "ai2thor-navigator" / "souls"
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class SkillInput:
    """Per-step observation payload passed to the skill."""

    agent_id: int
    camera_frame: np.ndarray  # (H, W, 3) uint8 RGB — agent's first-person view
    overhead_frame: np.ndarray  # (H, W, 3) uint8 RGB — top-down map
    game_state: dict[str, Any]  # structured state from the game engine


@dataclass
class SkillOutput:
    """Action decision returned by the skill."""

    reasoning: str  # VLM chain-of-thought
    action: str  # one of NAVIGATION_ACTIONS


# ---------------------------------------------------------------------------
# Skill
# ---------------------------------------------------------------------------


class AI2THORNavigatorSkill:
    """OpenClaw skill that drives one AI2-THOR agent using a VLM provider.

    Each instance is associated with a *soul* — a strategy personality
    expressed as a short Markdown document.  Three built-in presets are
    provided: ``"aggressive"``, ``"defensive"``, and ``"cooperative"``.
    A raw SOUL.md string may also be passed instead of a preset name.

    Parameters
    ----------
    provider:
        Any :class:`~roboclaws.core.vlm.VLMProvider`-compatible object.
    soul:
        Name of a built-in SOUL preset (``"aggressive"``, ``"defensive"``,
        ``"cooperative"``) or a raw SOUL text string.
    """

    def __init__(
        self,
        provider: Any,
        soul: str = "cooperative",
    ) -> None:
        self._provider = provider
        self._soul_text = self._load_soul(soul)

    # ------------------------------------------------------------------
    # SOUL helpers
    # ------------------------------------------------------------------

    def _load_soul(self, soul: str) -> str:
        """Return SOUL text for the given preset name or raw string.

        If *soul* matches a file stem inside the built-in souls directory
        (e.g. ``"aggressive"`` → ``souls/aggressive.md``) that file is
        returned.  Otherwise *soul* is used verbatim as the SOUL text.
        """
        candidate = _SOULS_DIR / f"{soul}.md"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8")
        return soul

    @staticmethod
    def list_souls() -> list[str]:
        """Return the names of available built-in SOUL presets (sorted)."""
        if not _SOULS_DIR.exists():
            return []
        return sorted(p.stem for p in _SOULS_DIR.glob("*.md"))

    # ------------------------------------------------------------------
    # Frame encoding
    # ------------------------------------------------------------------

    @staticmethod
    def encode_frame(frame: np.ndarray) -> str:
        """Encode a (H, W, 3) uint8 RGB array as a base64 JPEG string."""
        buf = io.BytesIO()
        Image.fromarray(frame, mode="RGB").save(buf, format="JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode("ascii")

    # ------------------------------------------------------------------
    # Skill execution
    # ------------------------------------------------------------------

    def run(self, skill_input: SkillInput) -> SkillOutput:
        """Execute one navigation step for the given observation.

        The soul text is included in the state dict so every provider can
        see it regardless of whether it supports a dedicated system prompt.

        Parameters
        ----------
        skill_input:
            Per-step observation for one agent.

        Returns
        -------
        :class:`SkillOutput` with a validated action and VLM reasoning.
        """
        images = [
            self.encode_frame(skill_input.camera_frame),
            self.encode_frame(skill_input.overhead_frame),
        ]

        state: dict[str, Any] = dict(skill_input.game_state)
        state["agent_id"] = skill_input.agent_id
        state["soul"] = self._soul_text
        state["available_actions"] = NAVIGATION_ACTIONS

        response = self._provider.get_action(images=images, state=state)

        action = response.get("action", "MoveAhead")
        if action not in NAVIGATION_ACTIONS:
            action = "MoveAhead"
        reasoning = response.get("reasoning", "")

        return SkillOutput(reasoning=reasoning, action=action)
