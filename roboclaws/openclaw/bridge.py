"""HTTP client for an OpenClaw Gateway (``POST /tools/invoke``).

The bridge lets a locally-running game loop outsource each agent's per-step
action decision to an OpenClaw Gateway that hosts the ``ai2thor-navigator``
skill (see ``roboclaws/openclaw/skill.py``).  Each simulation agent gets its
own ``sessionKey`` so SOUL + MEMORY are isolated per agent.

Protocol notes (see ``docs.openclaw.ai/gateway/tools-invoke-http-api``)
----------------------------------------------------------------------

* Endpoint: ``POST {gateway_url}/tools/invoke``.
* Auth:    ``Authorization: Bearer {token}`` (optional — only when the
           Gateway is started with ``OPENCLAW_AUTH_MODE=token``).
* Body:    ``{"tool": "ai2thor-navigator", "action": "step",
           "args": {"frame_path": ..., "overhead_path": ..., "state": ...,
           "step": N}, "sessionKey": "roboclaws-agent-{i}",
           "dryRun": false}``.
* Success: ``200 {"ok": true, "result": {"reasoning": ..., "action": ...}}``.
* Errors:  ``401`` (unauthorized), ``404`` (tool not allowlisted),
           ``400`` (invalid args), ``500`` (skill exec error),
           connection refused → :class:`OpenClawUnavailable`.

For multi-agent games every agent uses a distinct ``sessionKey`` so the
Gateway spawns one independent workspace per agent
(``~/.openclaw/agents/{sessionKey}/``).

This module is intentionally **thin** — it speaks only HTTP and validates
responses with the same ``AgentAction`` Pydantic model used by direct
VLM providers (``roboclaws.core.vlm``).  No retry loop, no caching,
no queueing — those belong in higher layers if ever needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


class OpenClawUnavailable(RuntimeError):
    """Raised when the Gateway is unreachable or the tool is not allowlisted.

    Callers (e.g. CI wrappers) should catch this to skip/degrade gracefully
    instead of treating it as a generic error.
    """


@dataclass
class BridgeResult:
    """Validated response from the Gateway's ``ai2thor-navigator`` skill."""

    reasoning: str
    action: str


class OpenClawBridge:
    """Synchronous HTTP client for an OpenClaw Gateway.

    Parameters
    ----------
    gateway_url:
        Base URL of the Gateway (no trailing ``/tools/invoke``).
    token:
        Bearer token.  Falls back to ``OPENCLAW_GATEWAY_TOKEN`` env var.
        ``None`` (or empty) disables the ``Authorization`` header entirely
        — intended for Gateways started without auth.
    session_prefix:
        Prefix for ``sessionKey``; the bridge appends ``-{agent_id}``.
    timeout:
        httpx timeout in seconds applied to every request.
    tool_name:
        Name of the skill to invoke.  Defaults to ``"ai2thor-navigator"``
        (see ``skills/ai2thor-navigator/SKILL.md``).
    """

    def __init__(
        self,
        gateway_url: str = "http://localhost:18789",
        token: str | None = None,
        session_prefix: str = "roboclaws-agent",
        timeout: float = 30.0,
        tool_name: str = "ai2thor-navigator",
    ) -> None:
        self.gateway_url = gateway_url.rstrip("/")
        self.session_prefix = session_prefix
        self.timeout = timeout
        self.tool_name = tool_name

        resolved_token = token if token is not None else os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        self._token = resolved_token or None  # treat empty string as no-auth

        headers = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.Client(base_url=self.gateway_url, timeout=timeout, headers=headers)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying httpx client."""
        self._client.close()

    def __enter__(self) -> OpenClawBridge:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def healthcheck(self) -> bool:
        """Return ``True`` iff both ``/healthz`` and ``/readyz`` return ``200``.

        Never raises: a connection error is reported as ``False`` so callers
        can branch on availability without wrapping in try/except.
        """
        try:
            for path in ("/healthz", "/readyz"):
                resp = self._client.get(path)
                if resp.status_code != 200:
                    return False
        except httpx.HTTPError:
            return False
        return True

    # ------------------------------------------------------------------
    # Core RPC
    # ------------------------------------------------------------------

    def step(
        self,
        agent_id: int,
        frame_path: Path | str,
        overhead_path: Path | str,
        state: dict[str, Any],
        step_idx: int,
    ) -> BridgeResult:
        """Invoke the navigation skill for one agent and return its action.

        Parameters
        ----------
        agent_id:
            Simulation-side agent index.  Determines the ``sessionKey``.
        frame_path:
            Path to the agent's first-person JPEG, visible to the Gateway
            via the shared work volume (see the skill's shared-volume
            contract in ``roboclaws/openclaw/skill.py``).
        overhead_path:
            Path to the overhead map JPEG, same volume semantics.
        state:
            Structured game state dict (already includes ``my_agent_id``,
            ``step``, etc. — mirror of what direct VLM providers receive).
        step_idx:
            Step index, echoed in the payload for the skill to log.

        Returns
        -------
        :class:`BridgeResult` with a validated ``action`` + ``reasoning``.

        Raises
        ------
        OpenClawUnavailable
            The Gateway refused the connection or the tool is not
            allowlisted (HTTP 404).
        httpx.HTTPStatusError
            Any other non-2xx response (400 / 401 / 500 …).
        """
        payload = {
            "tool": self.tool_name,
            "action": "step",
            "args": {
                "frame_path": str(frame_path),
                "overhead_path": str(overhead_path),
                "state": state,
                "step": step_idx,
            },
            "sessionKey": f"{self.session_prefix}-{agent_id}",
            "dryRun": False,
        }

        try:
            resp = self._client.post("/tools/invoke", json=payload)
        except httpx.ConnectError as exc:
            raise OpenClawUnavailable(f"Cannot reach Gateway at {self.gateway_url}: {exc}") from exc

        if resp.status_code == 404:
            raise OpenClawUnavailable(
                f"Tool {self.tool_name!r} not allowlisted on Gateway at {self.gateway_url}"
            )
        resp.raise_for_status()

        body = resp.json()
        if not body.get("ok"):
            raise RuntimeError(f"Gateway returned error: {body}")

        result = body.get("result") or {}
        return _validate_result(result)


# ---------------------------------------------------------------------------
# Response validation — reuse the AgentAction schema used by direct providers
# ---------------------------------------------------------------------------


def _validate_result(result: dict[str, Any]) -> BridgeResult:
    """Validate the Gateway's ``result`` dict against ``AgentAction``.

    Import of the Pydantic model is deferred so this module stays
    import-safe in environments that ship only the Gateway client
    without instructor/pydantic.
    """
    from roboclaws.core.vlm import _build_agent_action_model

    AgentAction = _build_agent_action_model()
    validated = AgentAction(**result)
    return BridgeResult(reasoning=validated.reasoning, action=validated.action)


# ---------------------------------------------------------------------------
# VLMProvider adapter — lets TerritoryGame / CoverageGame drop in the bridge
# in place of a direct VLM provider without any changes to the game loop.
# ---------------------------------------------------------------------------


class OpenClawBridgeProvider:
    """Adapter that exposes an :class:`OpenClawBridge` as a ``VLMProvider``.

    The existing :class:`~roboclaws.games.territory.TerritoryGame` and
    :class:`~roboclaws.games.coverage.CoverageGame` call
    ``provider.get_action(images, state)`` once per step.  This adapter
    forwards the call to ``bridge.step(agent_id, frame_path, overhead_path,
    state, step_idx)``.

    It extracts ``my_agent_id`` and ``step`` from the state dict (both are
    already set by the game loop).  The ``frame_path`` / ``overhead_path``
    fields come from the constructor — callers wire them up via the
    ``examples/`` scripts once per step before invoking the game step.

    Cost tracking is a no-op: the Gateway bills upstream (the Kimi/OpenAI/
    Anthropic key lives *inside* the Gateway container).  We return 0.0 so
    the provider interface stays satisfied.
    """

    def __init__(
        self,
        bridge: OpenClawBridge,
        frame_path_fn: Any | None = None,
        overhead_path_fn: Any | None = None,
    ) -> None:
        """Create an adapter.

        Parameters
        ----------
        bridge:
            Underlying HTTP bridge.
        frame_path_fn:
            Optional ``(agent_id, step) -> Path`` callable returning the
            first-person JPEG path.  If ``None``, uses ``"<unavailable>"``
            (still exercises the protocol shape for unit / contract tests).
        overhead_path_fn:
            Same, for the overhead map.
        """
        self._bridge = bridge
        self._frame_path_fn = frame_path_fn
        self._overhead_path_fn = overhead_path_fn
        self._cost = 0.0

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Forward to ``bridge.step`` using fields already present in ``state``."""
        agent_id = int(state.get("my_agent_id", 0))
        step_idx = int(state.get("step", 0))
        frame_path: Path | str = (
            self._frame_path_fn(agent_id, step_idx) if self._frame_path_fn else "<unavailable>"
        )
        overhead_path: Path | str = (
            self._overhead_path_fn(agent_id, step_idx)
            if self._overhead_path_fn
            else "<unavailable>"
        )
        result = self._bridge.step(
            agent_id=agent_id,
            frame_path=frame_path,
            overhead_path=overhead_path,
            state=state,
            step_idx=step_idx,
        )
        return {"reasoning": result.reasoning, "action": result.action}
