"""HTTP client for a running OpenClaw Gateway.

Implements a thin bridge that lets ``roboclaws`` drive a locally- or
remotely-running OpenClaw Gateway through ``POST /tools/invoke``.  One
``sessionKey`` is assigned per simulation agent so per-agent SOUL + MEMORY
is preserved by the Gateway.

See issue #13 and https://docs.openclaw.ai/gateway/tools-invoke-http-api.
"""

from __future__ import annotations

import base64
import io
import os
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.core.vlm import ProviderStatus

_DEFAULT_GATEWAY_URL = "http://localhost:18789"
_DEFAULT_TOOL = "ai2thor-navigator"


class OpenClawUnavailable(RuntimeError):
    """Raised when the Gateway is unreachable or the skill is not allowlisted.

    Callers (e.g. the CI wrapper) can catch this to skip/degrade the
    OpenClaw backend without masking unrelated HTTP errors.
    """


class OpenClawBridge:
    """HTTP client for a single OpenClaw Gateway.

    Parameters
    ----------
    gateway_url:
        Base URL of the Gateway (no trailing slash required).  Defaults to
        ``http://localhost:18789`` but may be overridden via the
        ``OPENCLAW_GATEWAY_URL`` env var.
    token:
        Bearer token for ``Authorization: Bearer <token>``.  Falls back to
        the ``OPENCLAW_GATEWAY_TOKEN`` env var.
    session_prefix:
        Prefix for per-agent ``sessionKey``; the final key is
        ``f"{session_prefix}-{agent_id}"``.
    tool:
        Tool name to invoke (default: ``"ai2thor-navigator"``).
    timeout:
        Per-request timeout in seconds.
    """

    def __init__(
        self,
        gateway_url: str | None = None,
        token: str | None = None,
        session_prefix: str = "roboclaws-agent",
        tool: str = _DEFAULT_TOOL,
        timeout: float = 30.0,
    ) -> None:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - httpx ships with instructor
            raise ImportError("httpx is required for OpenClawBridge: pip install httpx") from exc

        self._gateway_url = (
            gateway_url or os.environ.get("OPENCLAW_GATEWAY_URL") or _DEFAULT_GATEWAY_URL
        ).rstrip("/")
        self._token = token or os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        self._session_prefix = session_prefix
        self._tool = tool
        self._timeout = timeout

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.Client(
            base_url=self._gateway_url,
            headers=headers,
            timeout=timeout,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> OpenClawBridge:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    def healthcheck(self) -> bool:
        """Return True iff both ``/healthz`` and ``/readyz`` respond 200."""
        import httpx

        try:
            for path in ("/healthz", "/readyz"):
                resp = self._client.get(path)
                if resp.status_code != 200:
                    return False
        except httpx.HTTPError:
            return False
        return True

    # ------------------------------------------------------------------
    # Tool invocation
    # ------------------------------------------------------------------

    def session_key(self, agent_id: int) -> str:
        """Return the ``sessionKey`` used for *agent_id*."""
        return f"{self._session_prefix}-{agent_id}"

    def step(
        self,
        agent_id: int,
        frame_path: Path | str,
        overhead_path: Path | str,
        state: dict[str, Any],
        step_idx: int,
    ) -> dict[str, Any]:
        """Invoke the navigator skill for one agent and return its action.

        Parameters
        ----------
        agent_id:
            Simulation agent index, routed to its own Gateway session.
        frame_path:
            Path (visible to the Gateway container) of the first-person frame.
        overhead_path:
            Path (visible to the Gateway container) of the overhead map.
        state:
            Structured game state dict passed verbatim to the skill.
        step_idx:
            Monotonic step counter (used for observability + memory writes).

        Returns
        -------
        Dict with ``"reasoning"`` (str) and ``"action"`` (one of
        :data:`~roboclaws.core.engine.NAVIGATION_ACTIONS`).

        Raises
        ------
        OpenClawUnavailable
            When the Gateway is unreachable or the tool is not allowlisted.
        """
        payload = {
            "tool": self._tool,
            "action": "step",
            "args": {
                "frame_path": str(frame_path),
                "overhead_path": str(overhead_path),
                "state": state,
                "step": step_idx,
            },
            "sessionKey": self.session_key(agent_id),
            "dryRun": False,
        }
        return self._post_and_parse("/tools/invoke", payload)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _post_and_parse(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        import httpx

        try:
            resp = self._client.post(path, json=payload)
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
            raise OpenClawUnavailable(f"Gateway unreachable: {exc}") from exc
        except httpx.HTTPError as exc:
            raise OpenClawUnavailable(f"Gateway transport error: {exc}") from exc

        if resp.status_code == 404:
            raise OpenClawUnavailable(f"Tool {self._tool!r} not allowlisted on Gateway (404)")
        if resp.status_code == 401:
            raise OpenClawUnavailable("Gateway rejected bearer token (401)")
        if resp.status_code >= 400:
            raise OpenClawUnavailable(
                f"Gateway returned HTTP {resp.status_code}: {resp.text[:200]}"
            )

        try:
            body = resp.json()
        except ValueError as exc:
            raise OpenClawUnavailable(f"Gateway returned non-JSON: {exc}") from exc

        if not body.get("ok", False):
            raise OpenClawUnavailable(f"Gateway reported error: {body!r}")

        result = body.get("result") or {}
        action = result.get("action", "MoveAhead")
        reasoning = result.get("reasoning", "")
        if action not in NAVIGATION_ACTIONS:
            action = "MoveAhead"
        return {"reasoning": reasoning, "action": action}


# ---------------------------------------------------------------------------
# VLMProvider-compatible adapter
# ---------------------------------------------------------------------------


class OpenClawProvider:
    """Drop-in :class:`~roboclaws.core.vlm.VLMProvider` backed by :class:`OpenClawBridge`.

    Wraps the bridge so ``--backend openclaw`` slots into the existing game
    loop without further changes.  Each call to :meth:`get_action` writes any
    provided images to a temp directory and hands the paths to the Gateway.

    Cost tracking is not available for an external Gateway; ``cumulative_cost``
    is always ``0.0``.
    """

    def __init__(
        self,
        bridge: OpenClawBridge | None = None,
        work_dir: Path | str | None = None,
        **bridge_kwargs: Any,
    ) -> None:
        self._bridge = bridge or OpenClawBridge(**bridge_kwargs)
        self._owns_bridge = bridge is None
        self._work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="openclaw-"))
        self._work_dir.mkdir(parents=True, exist_ok=True)
        self._cost = 0.0
        self._step = 0
        self.model = getattr(self._bridge, "_tool", _DEFAULT_TOOL)
        self._status = ProviderStatus(provider_name="openclaw", model=self.model)

    # -- VLMProvider protocol -----------------------------------------

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_status(self) -> dict[str, Any]:
        return self._status.to_dict()

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Route one VLM call to the Gateway.

        ``images`` is the list of base64 JPEG strings the skill expects; the
        first is treated as the first-person frame, the second (if present)
        as the overhead map.  State keys ``my_agent_id`` (preferred) or
        ``current_agent`` identify the routed agent.
        """
        agent_id = int(state.get("my_agent_id", state.get("current_agent", 0)))
        step_idx = int(state.get("step", self._step))

        frame_path = self._write_image(images[0] if images else None, agent_id, step_idx, "fpv")
        overhead_path = self._write_image(
            images[1] if len(images) > 1 else None, agent_id, step_idx, "map"
        )

        started = time.monotonic()
        try:
            result = self._bridge.step(
                agent_id=agent_id,
                frame_path=frame_path,
                overhead_path=overhead_path,
                state=state,
                step_idx=step_idx,
            )
        except Exception as exc:
            self._status.total_calls += 1
            self._status.failed_calls += 1
            self._status.consecutive_failures += 1
            self._status.last_error = str(exc)
            self._status.last_error_kind = exc.__class__.__name__
            self._status.last_call_duration_seconds = time.monotonic() - started
            self._status.total_call_duration_seconds += self._status.last_call_duration_seconds
            raise
        self._status.total_calls += 1
        self._status.successful_calls += 1
        self._status.consecutive_failures = 0
        self._status.last_call_duration_seconds = time.monotonic() - started
        self._status.total_call_duration_seconds += self._status.last_call_duration_seconds
        self._step += 1
        return result

    # -- Lifecycle ----------------------------------------------------

    def close(self) -> None:
        if self._owns_bridge:
            self._bridge.close()

    # -- Internal -----------------------------------------------------

    def _write_image(
        self,
        img_b64: str | None,
        agent_id: int,
        step_idx: int,
        kind: str,
    ) -> Path:
        """Decode *img_b64* and write it to the shared work dir; return the path.

        If *img_b64* is None, an empty placeholder is written so the Gateway
        still receives a valid path (the skill may then skip vision).
        """
        step_dir = self._work_dir / f"step-{step_idx:04d}"
        step_dir.mkdir(parents=True, exist_ok=True)
        out = step_dir / f"agent-{agent_id}-{kind}.jpg"

        if img_b64:
            raw = base64.b64decode(img_b64)
            # Verify it's a valid image; re-encode via PIL for safety.
            Image.open(io.BytesIO(raw)).convert("RGB").save(out, format="JPEG", quality=80)
        else:
            # 1x1 black placeholder — cheap and keeps paths well-formed
            Image.fromarray(np.zeros((1, 1, 3), dtype=np.uint8), mode="RGB").save(
                out, format="JPEG"
            )
        return out
