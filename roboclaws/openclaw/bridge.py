"""HTTP client for a running OpenClaw Gateway — Phase 2.1 transport.

Drives a locally- or remotely-running OpenClaw Gateway via its OpenAI-compatible
``POST /v1/chat/completions`` endpoint.  Each simulation agent is routed to its
own named Gateway agent (``model="openclaw/{agent_prefix}{agent_id}"``) so SOUL,
MEMORY, and auth profile are isolated per agent — matching the
``skills/ai2thor-navigator/SKILL.md`` promise that "each simulation agent runs
as a separate OpenClaw instance".

The Gateway agent's system prompt already contains the workspace skill
(``ai2thor-navigator``); a short per-turn user message steers it to reply in
the skill's JSON shape.  Images flow inline as base64 data URLs — no bind
mount, no shared filesystem.

See ``docs/openclaw-local.md`` + ``scripts/openclaw-bootstrap.sh`` for the
one-shot container setup that pre-creates the N named agents this bridge
expects.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from PIL import Image

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.core.turn_metrics import round_seconds
from roboclaws.core.vlm import ProviderStatus

_DEFAULT_GATEWAY_URL = "http://localhost:18789"
_DEFAULT_AGENT_PREFIX = "agent-"
_CHAT_PATH = "/v1/chat/completions"
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)
# Generous enough for reasoning models (e.g. nvidia/nemotron-nano-12b-v2-vl:free
# on OpenRouter) whose hidden chain-of-thought easily consumes 200+ tokens
# before producing the visible content. Non-reasoning models ignore the cap
# if they answer shorter.
_DEFAULT_MAX_TOKENS = 1024
# OpenClawProvider retries upstream read timeouts this many times (incl. the first
# attempt) with exponential backoff (2s, 4s, 8s) before raising a
# "Model unavailable" error.  Connect errors, protocol errors, and HTTP 4xx/5xx
# are NOT retried here — they fail fast so the caller can surface the root cause.
_RETRY_ATTEMPTS = 3


@dataclass
class RunResult:
    final_message: str
    wallclock_s: float
    terminated_by: Literal["done", "wall_clock", "error"]
    debug: dict[str, Any] = field(default_factory=dict)


class OpenClawUnavailable(RuntimeError):
    """Raised when the Gateway is unreachable or rejects our request.

    Callers (e.g. the CI wrapper) can catch this to skip/degrade the
    OpenClaw backend without masking unrelated HTTP errors.
    """


class OpenClawBridge:
    """HTTP client for a single OpenClaw Gateway using ``/v1/chat/completions``.

    Parameters
    ----------
    gateway_url:
        Base URL of the Gateway (no trailing slash required).  Defaults to
        ``http://localhost:18789`` but may be overridden via the
        ``OPENCLAW_GATEWAY_URL`` env var.
    token:
        Bearer token for ``Authorization: Bearer <token>``.  Falls back to
        the ``OPENCLAW_GATEWAY_TOKEN`` env var.
    agent_prefix:
        Prefix applied to ``agent_id`` to derive the named Gateway agent,
        e.g. ``agent_prefix="agent-"`` + ``agent_id=2`` →
        ``model="openclaw/agent-2"``.  Matches the bootstrap script's
        ``AGENT_PREFIX`` env var — single source of truth for the naming
        scheme.
    timeout:
        Per-request timeout in seconds.  Defaults to 180s — long enough to
        absorb the first image-bearing call to a cold Kimi session (prior
        60s default timed out before the upstream replied).  Can be
        overridden via the ``OPENCLAW_HTTP_TIMEOUT`` env var.
    """

    def __init__(
        self,
        gateway_url: str | None = None,
        token: str | None = None,
        agent_prefix: str = _DEFAULT_AGENT_PREFIX,
        timeout: float | None = None,
    ) -> None:
        if timeout is None:
            env_timeout = os.environ.get("OPENCLAW_HTTP_TIMEOUT")
            timeout = float(env_timeout) if env_timeout else 180.0
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - httpx ships with instructor
            raise ImportError("httpx is required for OpenClawBridge: pip install httpx") from exc

        self._gateway_url = (
            gateway_url or os.environ.get("OPENCLAW_GATEWAY_URL") or _DEFAULT_GATEWAY_URL
        ).rstrip("/")
        self._token = token or os.environ.get("OPENCLAW_GATEWAY_TOKEN")
        self._agent_prefix = agent_prefix
        self._timeout = timeout

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        self._client = httpx.Client(
            base_url=self._gateway_url,
            headers=headers,
            timeout=timeout,
        )
        self._last_step_metrics: dict[str, Any] = {}
        self._last_run_metrics: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def get_last_step_metrics(self) -> dict[str, Any]:
        """Return timing/payload telemetry for the last bridge step."""
        return dict(self._last_step_metrics)

    def get_last_run_metrics(self) -> dict[str, Any]:
        """Return timing/payload telemetry for the last autonomous start_run call."""
        return dict(self._last_run_metrics)

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
    # Named-agent helpers
    # ------------------------------------------------------------------

    def model_id(self, agent_id: int) -> str:
        """Return the ``model`` string routing to the named Gateway agent."""
        return f"openclaw/{self._agent_prefix}{agent_id}"

    def ping(self, agent_id: int = 0) -> str:
        """One-shot PONG probe against a named agent.

        Used by :class:`OpenClawProvider` / the demo script to fail fast if
        the Gateway doesn't know about the requested agent before running
        N simulation steps.  Returns the raw assistant reply string; raises
        :class:`OpenClawUnavailable` on any transport / auth / routing
        failure.
        """
        payload = {
            "model": self.model_id(agent_id),
            "messages": [
                {"role": "user", "content": "Reply with only PONG."},
            ],
            "max_tokens": _DEFAULT_MAX_TOKENS,
        }
        body = self._post_chat(payload)
        return _extract_content(body)

    def start_run(
        self,
        agent_id: int,
        prompt: str,
        wall_budget_s: float,
        done_event: threading.Event,
    ) -> RunResult:
        """Kick off a long-running autonomous Gateway run for one named agent."""
        del done_event  # Reserved for future early-abort integration from the sim server.

        per_call_timeout = wall_budget_s + 60.0
        run_metrics: dict[str, Any] = {
            "model": self.model_id(agent_id),
            "agent_id": agent_id,
            "wall_budget_s": round_seconds(wall_budget_s),
            "http_timeout_s": round_seconds(per_call_timeout),
            "prompt_chars": len(prompt),
            "prompt_lines": prompt.count("\n") + 1,
        }
        reset_started = time.perf_counter()
        self._reset_workspace_state(agent_id)
        run_metrics["workspace_reset_seconds"] = round_seconds(time.perf_counter() - reset_started)
        started = time.monotonic()
        payload = {
            "model": self.model_id(agent_id),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": _DEFAULT_MAX_TOKENS,
        }
        run_metrics["request_payload_chars"] = len(json.dumps(payload))
        self._last_run_metrics = dict(run_metrics)

        import httpx

        try:
            resp = self._client.post(
                _CHAT_PATH,
                json=payload,
                timeout=per_call_timeout,
            )
        except httpx.ReadTimeout:
            run_metrics.update(
                {
                    "terminated_by": "wall_clock",
                    "gateway_request_seconds": round_seconds(time.monotonic() - started),
                    "gateway_error": "read_timeout",
                }
            )
            self._last_run_metrics = dict(run_metrics)
            return RunResult(
                final_message="<wall-clock timeout - no final message>",
                wallclock_s=round_seconds(time.monotonic() - started),
                terminated_by="wall_clock",
                debug=dict(run_metrics),
            )
        except httpx.ConnectError as exc:
            run_metrics.update(
                {
                    "terminated_by": "error",
                    "gateway_request_seconds": round_seconds(time.monotonic() - started),
                    "gateway_error": "connect_error",
                }
            )
            self._last_run_metrics = dict(run_metrics)
            raise OpenClawUnavailable(f"Gateway unreachable (local ConnectError): {exc}") from exc
        except httpx.RemoteProtocolError as exc:
            run_metrics.update(
                {
                    "terminated_by": "error",
                    "gateway_request_seconds": round_seconds(time.monotonic() - started),
                    "gateway_error": "remote_protocol_error",
                }
            )
            self._last_run_metrics = dict(run_metrics)
            raise OpenClawUnavailable(f"Gateway protocol error: {exc}") from exc
        except httpx.HTTPError as exc:
            run_metrics.update(
                {
                    "terminated_by": "error",
                    "gateway_request_seconds": round_seconds(time.monotonic() - started),
                    "gateway_error": "http_error",
                }
            )
            self._last_run_metrics = dict(run_metrics)
            raise OpenClawUnavailable(f"Gateway transport error: {exc}") from exc

        body = self._parse_json_response(resp)
        final_message = _extract_content(body)
        usage = body.get("usage")
        choice = ((body.get("choices") or [{}])[0]) if isinstance(body, dict) else {}
        run_metrics.update(
            {
                "terminated_by": "done",
                "gateway_request_seconds": round_seconds(time.monotonic() - started),
                "http_status_code": int(resp.status_code),
                "response_bytes": len(resp.content),
                "finish_reason": choice.get("finish_reason"),
                "usage": usage if isinstance(usage, dict) else None,
                "final_message_chars": len(final_message),
            }
        )
        self._last_run_metrics = dict(run_metrics)
        return RunResult(
            final_message=final_message,
            wallclock_s=round_seconds(time.monotonic() - started),
            terminated_by="done",
            debug=dict(run_metrics),
        )

    # ------------------------------------------------------------------
    # Tool invocation
    # ------------------------------------------------------------------

    def step(
        self,
        agent_id: int,
        frame: np.ndarray,
        overhead: np.ndarray,
        state: dict[str, Any],
        step_idx: int,
    ) -> dict[str, Any]:
        """POST a turn to ``/v1/chat/completions`` for the named Gateway agent.

        Parameters
        ----------
        agent_id:
            Simulation agent index.  Routed to ``openclaw/{agent_prefix}{agent_id}``.
        frame:
            First-person RGB frame as a ``(H, W, 3) uint8`` numpy array.
        overhead:
            Overhead map RGB as a ``(H, W, 3) uint8`` numpy array.
        state:
            Structured game state dict.  Serialised to JSON in the user
            message for the agent to read.
        step_idx:
            Monotonic step counter (included in the steer for observability).

        Returns
        -------
        Dict with ``"reasoning"`` (str) and ``"action"`` (one of
        :data:`~roboclaws.core.engine.NAVIGATION_ACTIONS`).

        Raises
        ------
        OpenClawUnavailable
            When the Gateway is unreachable, rejects auth, doesn't know the
            named agent, or has ``/v1/chat/completions`` disabled.
        """
        step_started = time.perf_counter()
        fpv_url, fpv_metrics = _ndarray_to_data_url(frame)
        map_url, map_metrics = _ndarray_to_data_url(overhead)

        agent_name = f"{self._agent_prefix}{agent_id}"
        state_started = time.perf_counter()
        state_json = json.dumps(state, default=str)
        state_json_seconds = time.perf_counter() - state_started
        steer = (
            f"You are RoboClaws {agent_name}, step {step_idx}. "
            f"Follow the ai2thor-navigator skill. "
            f"Current state (JSON): {state_json}. "
            "FPV and overhead map attached. "
            'Reply with ONLY JSON: {"reasoning": "...", "action": "..."}.'
        )

        payload = {
            "model": self.model_id(agent_id),
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": steer},
                        {"type": "image_url", "image_url": {"url": fpv_url}},
                        {"type": "image_url", "image_url": {"url": map_url}},
                    ],
                },
            ],
            # Reasoning models (OpenRouter :free nemotron-vl, Kimi-thinking)
            # may consume hundreds of hidden tokens before the visible JSON.
            # Without a generous cap they hit finish_reason=length and return
            # content=null, which breaks _parse_action downstream.
            "max_tokens": _DEFAULT_MAX_TOKENS,
        }
        request_started = time.perf_counter()
        body = self._post_chat(payload)
        request_seconds = time.perf_counter() - request_started

        parse_started = time.perf_counter()
        content = _extract_content(body)
        result = _parse_action(content)
        parse_seconds = time.perf_counter() - parse_started

        self._last_step_metrics = {
            "timings": {
                "openclaw_encode_fpv_seconds": fpv_metrics["encode_seconds"],
                "openclaw_encode_overhead_seconds": map_metrics["encode_seconds"],
                "openclaw_state_json_seconds": round_seconds(state_json_seconds),
                "openclaw_gateway_request_seconds": round_seconds(request_seconds),
                "openclaw_response_parse_seconds": round_seconds(parse_seconds),
                "openclaw_bridge_step_seconds": round_seconds(time.perf_counter() - step_started),
            },
            "payload": {
                "transport": "openclaw_data_url",
                "model": self.model_id(agent_id),
                "image_count": 2,
                "state_json_chars": len(state_json),
                "steer_text_chars": len(steer),
                "images": [
                    {"label": "fpv", **fpv_metrics},
                    {"label": "overhead", **map_metrics},
                ],
                "total_jpeg_bytes": fpv_metrics["jpeg_bytes"] + map_metrics["jpeg_bytes"],
                "total_base64_chars": fpv_metrics["base64_chars"] + map_metrics["base64_chars"],
            },
        }
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _post_chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        """POST to ``/v1/chat/completions`` and normalise HTTP errors."""
        import httpx

        try:
            resp = self._client.post(_CHAT_PATH, json=payload)
        except httpx.ConnectError as exc:
            raise OpenClawUnavailable(f"Gateway unreachable (local ConnectError): {exc}") from exc
        except httpx.ReadTimeout as exc:
            model_id = payload.get("model", "?")
            raise OpenClawUnavailable(
                f"Upstream read timeout after {self._timeout:.0f}s (model={model_id}) — "
                f"raise via OPENCLAW_HTTP_TIMEOUT=<seconds>: {exc}"
            ) from exc
        except httpx.RemoteProtocolError as exc:
            raise OpenClawUnavailable(f"Gateway protocol error: {exc}") from exc
        except httpx.HTTPError as exc:
            raise OpenClawUnavailable(f"Gateway transport error: {exc}") from exc
        return self._parse_json_response(resp)

    def _parse_json_response(self, resp: Any) -> dict[str, Any]:
        self._raise_for_http_status(resp)
        try:
            return resp.json()
        except ValueError as exc:
            raise OpenClawUnavailable(f"Gateway returned non-JSON: {exc}") from exc

    def _raise_for_http_status(self, resp: Any) -> None:
        if resp.status_code == 401:
            raise OpenClawUnavailable("Gateway rejected bearer token (401)")
        if resp.status_code == 404:
            raise OpenClawUnavailable(
                "/v1/chat/completions not enabled (404) — re-run scripts/openclaw-bootstrap.sh"
            )
        if resp.status_code == 400:
            text = resp.text or ""
            if "Invalid model" in text or "invalid model" in text.lower():
                raise OpenClawUnavailable(
                    f"Gateway rejected model id ({text.strip()[:200]}). "
                    "The named agent is likely not registered — re-run "
                    "scripts/openclaw-bootstrap.sh with AGENTS>=<agent_id>+1"
                )
            raise OpenClawUnavailable(f"Gateway returned HTTP 400: {text[:200]}")
        if resp.status_code >= 400:
            text = resp.text or ""
            msg = text[:200]
            try:
                err = resp.json().get("error") or {}
                if isinstance(err, dict) and err.get("message"):
                    msg = str(err["message"])
            except ValueError:
                pass
            raise OpenClawUnavailable(f"Gateway returned HTTP {resp.status_code}: {msg}")

    def _reset_workspace_state(self, agent_id: int) -> None:
        agent_name = f"{self._agent_prefix}{agent_id}"
        cmd = [
            "docker",
            "exec",
            "openclaw-gateway",
            "sh",
            "-c",
            f"rm -rf /home/node/.openclaw/workspaces/{agent_name}/state/*",
        ]
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()[:200]
            print(
                f"[openclaw] warning: workspace reset failed for {agent_name}: {detail}",
                file=sys.stderr,
            )


# ---------------------------------------------------------------------------
# OpenAI chat response → action parsing
# ---------------------------------------------------------------------------


def _extract_content(body: dict[str, Any]) -> str:
    """Return ``choices[0].message.content`` as a string.

    OpenAI-style responses may put the content directly on
    ``message.content`` (a string) or as a list of content blocks with
    ``{"type": "text", "text": "..."}`` entries.  Handle both.

    Some reasoning-style models (e.g. NVIDIA Nemotron Nano VL via OpenRouter)
    return ``content: null`` alongside a ``reasoning`` / ``reasoning_content``
    string when they hit ``finish_reason: length``.  We fall back to the
    reasoning field so downstream JSON extraction at least has the model's
    partial thought to try to parse an ``action`` out of.
    """
    choices = body.get("choices") or []
    if not choices:
        raise OpenClawUnavailable(f"Gateway returned no choices: {body!r}")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        text = "".join(parts)
    elif content is None:
        text = ""
    else:
        text = str(content)
    if text:
        return text
    # Reasoning-only fallback: some providers surface the chain-of-thought in
    # a separate field when the answer got truncated.
    for reasoning_field in ("reasoning", "reasoning_content"):
        val = message.get(reasoning_field)
        if isinstance(val, str) and val.strip():
            return val
    return text


def _parse_action(content: str) -> dict[str, Any]:
    """Parse ``{"reasoning": "...", "action": "..."}`` out of the LLM reply.

    LLMs often wrap JSON in ```` ```json ... ``` ```` fences.  Strip any
    fences, attempt ``json.loads``, and validate ``action`` is in
    :data:`~roboclaws.core.engine.NAVIGATION_ACTIONS`.  On any parse or
    validation failure, log a warning and fall back to ``MoveAhead`` so the
    demo keeps moving instead of crashing.
    """
    stripped = _CODE_FENCE_RE.sub("", content).strip()

    # If the LLM wrote text-then-JSON, pull the outermost {...} block.
    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start : end + 1]

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        _warn_malformed(content)
        return {"reasoning": content.strip()[:500], "action": "MoveAhead"}

    if not isinstance(parsed, dict):
        _warn_malformed(content)
        return {"reasoning": content.strip()[:500], "action": "MoveAhead"}

    action = str(parsed.get("action", "MoveAhead"))
    reasoning = str(parsed.get("reasoning", ""))
    if action not in NAVIGATION_ACTIONS:
        _warn_invalid_action(action)
        action = "MoveAhead"
    return {"reasoning": reasoning, "action": action}


def _warn_malformed(content: str) -> None:
    snippet = content.strip().replace("\n", " ")[:200]
    print(f"[openclaw] warning: LLM returned non-JSON content, using MoveAhead: {snippet!r}")


def _warn_invalid_action(action: str) -> None:
    print(f"[openclaw] warning: LLM returned invalid action {action!r}, coercing to MoveAhead")


def _ndarray_to_data_url(frame: np.ndarray, quality: int = 70) -> tuple[str, dict[str, Any]]:
    """Encode an RGB numpy array as a ``data:image/jpeg;base64,...`` URL.

    Resizes to a compact 320x240 to keep per-turn payloads well under any
    prompt-token limit.  Matches the earlier base64-intermediate behaviour
    of the demo but skips the filesystem round-trip.
    """
    started = time.perf_counter()
    image = Image.fromarray(frame, mode="RGB").resize((320, 240), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    jpeg_bytes = buf.getvalue()
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    return f"data:image/jpeg;base64,{b64}", {
        "jpeg_bytes": len(jpeg_bytes),
        "base64_chars": len(b64),
        "width": 320,
        "height": 240,
        "jpeg_quality": quality,
        "encode_seconds": round_seconds(time.perf_counter() - started),
    }


# ---------------------------------------------------------------------------
# VLMProvider-compatible adapter
# ---------------------------------------------------------------------------


class OpenClawProvider:
    """Drop-in :class:`~roboclaws.core.vlm.VLMProvider` backed by :class:`OpenClawBridge`.

    Wraps the bridge so the demo's main loop can treat the Gateway like any
    other VLM provider.  No filesystem exchange — frames flow inline as
    base64 data URLs.

    Cost tracking is not available for an external Gateway; ``cumulative_cost``
    is always ``0.0``.
    """

    def __init__(
        self,
        bridge: OpenClawBridge | None = None,
        **bridge_kwargs: Any,
    ) -> None:
        self._bridge = bridge or OpenClawBridge(**bridge_kwargs)
        self._owns_bridge = bridge is None
        self._cost = 0.0
        self._step = 0
        self.model = f"openclaw:{self._bridge._agent_prefix}*"
        self._status = ProviderStatus(provider_name="openclaw", model=self.model)
        self._last_turn_metrics: dict[str, Any] = {}

    # -- VLMProvider protocol -----------------------------------------

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_status(self) -> dict[str, Any]:
        return self._status.to_dict()

    def get_last_turn_metrics(self) -> dict[str, Any]:
        return dict(self._last_turn_metrics)

    def get_action(
        self,
        images: list[np.ndarray],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Route one turn to the Gateway for the requested agent.

        Parameters
        ----------
        images:
            Ordered list of numpy RGB frames.  ``images[0]`` is treated as
            the first-person frame; ``images[1]`` (if present) as the
            overhead map.  Missing or empty entries fall back to a 1×1
            black placeholder so the named agent still gets a valid payload.
        state:
            Structured game state.  ``state["my_agent_id"]`` (preferred) or
            ``state["current_agent"]`` routes the turn to the right agent.
        """
        agent_id = int(state.get("my_agent_id", state.get("current_agent", 0)))
        step_idx = int(state.get("step", self._step))

        frame = images[0] if images else _placeholder_frame()
        overhead = images[1] if len(images) > 1 else _placeholder_frame()

        started = time.monotonic()
        last_exc: Exception | None = None
        retry_delay_seconds_this_call = 0.0
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                result = self._bridge.step(
                    agent_id=agent_id,
                    frame=frame,
                    overhead=overhead,
                    state=state,
                    step_idx=step_idx,
                )
            except OpenClawUnavailable as exc:
                last_exc = exc
                self._status.last_error = str(exc)
                self._status.last_error_kind = exc.__class__.__name__
                is_timeout = "read timeout" in str(exc).lower()
                if is_timeout and attempt < _RETRY_ATTEMPTS - 1:
                    self._status.transient_errors += 1
                    self._status.retry_events += 1
                    delay = min(2.0 * (2**attempt), 8.0)
                    self._status.total_retry_delay_seconds += delay
                    retry_delay_seconds_this_call += delay
                    time.sleep(delay)
                    continue
                self._status.total_calls += 1
                self._status.failed_calls += 1
                self._status.consecutive_failures += 1
                self._status.last_call_duration_seconds = time.monotonic() - started
                self._status.total_call_duration_seconds += self._status.last_call_duration_seconds
                self._last_turn_metrics = {
                    "timings": {
                        "openclaw_provider_call_seconds": round_seconds(time.monotonic() - started),
                        "openclaw_retry_delay_seconds": round_seconds(
                            retry_delay_seconds_this_call
                        ),
                    },
                    "provider": {
                        "attempts": attempt + 1,
                        "retries_this_call": attempt,
                        "error_kind": exc.__class__.__name__,
                    },
                }
                if is_timeout:
                    raise OpenClawUnavailable(
                        f"Model unavailable: openclaw/{self._bridge._agent_prefix}{agent_id} "
                        f"timed out on {_RETRY_ATTEMPTS} consecutive attempts — last: {exc}"
                    ) from exc
                raise
            except Exception as exc:
                self._status.total_calls += 1
                self._status.failed_calls += 1
                self._status.consecutive_failures += 1
                self._status.last_error = str(exc)
                self._status.last_error_kind = exc.__class__.__name__
                self._status.last_call_duration_seconds = time.monotonic() - started
                self._status.total_call_duration_seconds += self._status.last_call_duration_seconds
                self._last_turn_metrics = {
                    "timings": {
                        "openclaw_provider_call_seconds": round_seconds(time.monotonic() - started),
                        "openclaw_retry_delay_seconds": round_seconds(
                            retry_delay_seconds_this_call
                        ),
                    },
                    "provider": {
                        "attempts": attempt + 1,
                        "retries_this_call": attempt,
                        "error_kind": exc.__class__.__name__,
                    },
                }
                raise
            else:
                self._status.total_calls += 1
                self._status.successful_calls += 1
                self._status.consecutive_failures = 0
                self._status.last_call_duration_seconds = time.monotonic() - started
                self._status.total_call_duration_seconds += self._status.last_call_duration_seconds
                bridge_metrics = self._bridge.get_last_step_metrics()
                bridge_timings = (
                    bridge_metrics.get("timings", {}) if isinstance(bridge_metrics, dict) else {}
                )
                bridge_payload = (
                    bridge_metrics.get("payload", {}) if isinstance(bridge_metrics, dict) else {}
                )
                self._last_turn_metrics = {
                    "timings": {
                        "openclaw_provider_call_seconds": round_seconds(time.monotonic() - started),
                        "openclaw_retry_delay_seconds": round_seconds(
                            retry_delay_seconds_this_call
                        ),
                        **bridge_timings,
                    },
                    "payload": bridge_payload,
                    "provider": {
                        "attempts": attempt + 1,
                        "retries_this_call": attempt,
                    },
                }
                self._step += 1
                return result
        # Defensive: loop should always return or raise above.
        assert last_exc is not None
        raise last_exc

    # -- Convenience --------------------------------------------------

    def ping(self, agent_id: int = 0) -> str:
        """Expose :meth:`OpenClawBridge.ping` for precondition probes."""
        return self._bridge.ping(agent_id)

    # -- Lifecycle ----------------------------------------------------

    def close(self) -> None:
        if self._owns_bridge:
            self._bridge.close()


def _placeholder_frame() -> np.ndarray:
    """1×1 black RGB frame used when the caller omits an image."""
    return np.zeros((1, 1, 3), dtype=np.uint8)


def build_openclaw_provider_or_die(
    *,
    gateway_url: str | None = None,
    agent_count: int,
) -> "OpenClawProvider":
    """Construct an :class:`OpenClawProvider` and fail fast if the Gateway is unreachable.

    Reads ``OPENCLAW_GATEWAY_TOKEN`` and ``OPENCLAW_AGENT_PREFIX`` from the
    environment (no CLI flags — tokens must not appear in shell history).

    Parameters
    ----------
    gateway_url:
        Override the Gateway base URL.  Defaults to the ``OPENCLAW_GATEWAY_URL``
        env var, then ``http://localhost:18789``.
    agent_count:
        Number of simulation agents; used to compose the hint message when
        the Gateway is unreachable.

    Raises
    ------
    SystemExit
        With a human-readable hint when the Gateway is unreachable, the token
        is expired, or the named agent hasn't been registered.
    """
    kwargs: dict[str, Any] = {}
    if gateway_url is not None:
        kwargs["gateway_url"] = gateway_url
    agent_prefix = os.environ.get("OPENCLAW_AGENT_PREFIX", _DEFAULT_AGENT_PREFIX)
    kwargs["agent_prefix"] = agent_prefix

    provider = OpenClawProvider(**kwargs)
    try:
        provider.ping(agent_id=0)
    except OpenClawUnavailable as exc:
        provider.close()
        msg = str(exc)
        if "401" in msg or "bearer token" in msg.lower():
            hint = (
                "Token likely expired — re-capture with: TOKEN=$(./scripts/openclaw-bootstrap.sh)"
            )
        elif "400" in msg and "Invalid model" in msg:
            hint = (
                f"Agent 0 not registered — re-run with AGENTS={agent_count}: "
                "TOKEN=$(AGENTS={agent_count} ./scripts/openclaw-bootstrap.sh)"
            )
        else:
            hint = (
                "Gateway not running — check `docker ps` and re-run ./scripts/openclaw-bootstrap.sh"
            )
        raise SystemExit(f"Gateway precondition failed: {exc}\nHint: {hint}") from exc
    return provider
