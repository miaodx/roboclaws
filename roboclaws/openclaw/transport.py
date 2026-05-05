"""HTTP transport layer for the OpenClaw Gateway — low-level bridge client.

Provides :class:`OpenClawBridge` (the HTTP client) plus all supporting
dataclasses, exceptions, and response-parsing helpers.  The higher-level
VLMProvider adapter lives in :mod:`roboclaws.openclaw.bridge`.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, NoReturn

import numpy as np
from PIL import Image

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.core.turn_metrics import round_seconds

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

_TRANSCRIPT_SOURCE = Literal["terminal-body", "session-store", "none"]
_SESSION_STORE_SOURCE: Literal["session-store"] = "session-store"
_GATEWAY_CONTAINER = "openclaw-gateway"


@dataclass
class TranscriptMessage:
    wallclock_s: float
    source: _TRANSCRIPT_SOURCE
    content: str
    message_index: int
    chunk_index: int
    is_final: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "wallclock_s": self.wallclock_s,
            "source": self.source,
            "content": self.content,
            "message_index": self.message_index,
            "chunk_index": self.chunk_index,
            "is_final": self.is_final,
        }


@dataclass
class _StartRunCapture:
    terminated_by: Literal["done", "wall_clock", "error"]
    final_message: str
    transcript_source: _TRANSCRIPT_SOURCE
    transcript_messages: list[TranscriptMessage] = field(default_factory=list)
    http_status_code: int | None = None
    response_bytes: int | None = None
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
    gateway_error: str | None = None


@dataclass
class RunResult:
    final_message: str
    wallclock_s: float
    terminated_by: Literal["done", "wall_clock", "error"]
    transcript_source: _TRANSCRIPT_SOURCE = "none"
    transcript_messages: list[TranscriptMessage] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)


@dataclass
class _SessionStoreCapture:
    session_id: str
    session_file: str
    transcript_messages: list[TranscriptMessage]


class OpenClawUnavailable(RuntimeError):
    """Raised when the Gateway is unreachable or rejects our request.

    Callers (e.g. the CI wrapper) can catch this to skip/degrade the
    OpenClaw backend without masking unrelated HTTP errors.
    """


class _SessionStoreReader:
    """Reads agent session transcripts from the OpenClaw Gateway Docker container."""

    def __init__(self, agent_prefix: str) -> None:
        self._agent_prefix = agent_prefix

    def ids(self, agent_id: int) -> set[str]:
        agent_name = f"{self._agent_prefix}{agent_id}"
        return {
            str(entry.get("sessionId"))
            for entry in self._read_index(agent_name)
            if entry.get("sessionId")
        }

    def recover(
        self,
        *,
        agent_id: int,
        started_wallclock: float,
        preexisting_ids: set[str],
    ) -> _SessionStoreCapture | None:
        agent_name = f"{self._agent_prefix}{agent_id}"
        candidates = self._read_index(agent_name)
        started_ms = int(started_wallclock * 1000)

        def _sort_key(entry: dict[str, Any]) -> tuple[int, str]:
            started_at = entry.get("startedAt")
            return (
                int(started_at) if isinstance(started_at, int) else -1,
                str(entry.get("sessionId", "")),
            )

        matching: list[dict[str, Any]] = []
        for entry in candidates:
            session_id = str(entry.get("sessionId", ""))
            if not session_id or session_id in preexisting_ids:
                continue
            started_at = entry.get("startedAt")
            if isinstance(started_at, int) and started_at >= started_ms - 5000:
                matching.append(entry)
        if not matching:
            for entry in sorted(candidates, key=_sort_key, reverse=True):
                started_at = entry.get("startedAt")
                if isinstance(started_at, int) and started_at >= started_ms - 5000:
                    matching = [entry]
                    break
        if not matching:
            return None

        selected = sorted(matching, key=_sort_key, reverse=True)[0]
        session_id = str(selected.get("sessionId", ""))
        session_file = str(selected.get("sessionFile", "")).strip()
        if not session_id or not session_file:
            return None
        transcript_messages = self._read_transcript(
            session_file=session_file,
            started_wallclock=started_wallclock,
        )
        if not transcript_messages:
            return None
        return _SessionStoreCapture(
            session_id=session_id,
            session_file=session_file,
            transcript_messages=transcript_messages,
        )

    def _read_container_text(self, path: str) -> str:
        result = subprocess.run(
            ["docker", "exec", _GATEWAY_CONTAINER, "cat", path],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 and result.stdout.strip() else ""

    def _read_index(self, agent_name: str) -> list[dict[str, Any]]:
        path = f"/home/node/.openclaw/agents/{agent_name}/sessions/sessions.json"
        stdout = self._read_container_text(path)
        if not stdout:
            return []
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, dict):
            return []

        entries: list[dict[str, Any]] = []
        session_root = f"/home/node/.openclaw/agents/{agent_name}/sessions/"
        for value in payload.values():
            if not isinstance(value, dict):
                continue
            session_file = value.get("sessionFile")
            if isinstance(session_file, str) and session_file.startswith(session_root):
                entries.append(value)
        return entries

    def _read_transcript(
        self,
        *,
        session_file: str,
        started_wallclock: float,
    ) -> list[TranscriptMessage]:
        stdout = self._read_container_text(session_file)
        if not stdout:
            return []

        transcript_messages: list[TranscriptMessage] = []
        for line in stdout.splitlines():
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "message":
                continue
            message = entry.get("message") or {}
            if not isinstance(message, dict) or message.get("role") != "assistant":
                continue
            content = _extract_text_blocks(message.get("content"))
            if not content.strip():
                continue
            timestamp = _timestamp_to_epoch_seconds(entry.get("timestamp"))
            transcript_messages.append(
                TranscriptMessage(
                    wallclock_s=max(
                        0.0,
                        round_seconds(
                            timestamp - started_wallclock if timestamp is not None else 0.0
                        ),
                    ),
                    source=_SESSION_STORE_SOURCE,
                    content=content,
                    message_index=len(transcript_messages),
                    chunk_index=0,
                    is_final=_is_terminal_stop_reason(message.get("stopReason")),
                )
            )
        return transcript_messages


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
        self._session_store = _SessionStoreReader(agent_prefix)

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
    ) -> RunResult:
        """Kick off a long-running autonomous Gateway run for one named agent."""
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
        preexisting_session_ids = self._session_store.ids(agent_id)
        run_metrics["session_store_snapshot_count"] = len(preexisting_session_ids)
        started = time.monotonic()
        started_wallclock = time.time()
        payload = {
            "model": self.model_id(agent_id),
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": _DEFAULT_MAX_TOKENS,
        }
        run_metrics["request_payload_chars"] = len(json.dumps(payload))
        self._last_run_metrics = dict(run_metrics)

        import httpx

        try:
            capture = self._terminal_body_run(payload, timeout=per_call_timeout, started=started)
        except httpx.ReadTimeout:
            capture = _StartRunCapture(
                final_message="<wall-clock timeout - no final message>",
                terminated_by="wall_clock",
                transcript_source="none",
                transcript_messages=[],
                gateway_error="read_timeout",
            )
        except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.HTTPError) as exc:
            self._handle_transport_exc(exc, started, run_metrics)

        session_store_capture = self._session_store.recover(
            agent_id=agent_id,
            started_wallclock=started_wallclock,
            preexisting_ids=preexisting_session_ids,
        )
        if not capture.transcript_messages and session_store_capture is not None:
            capture.transcript_source = _SESSION_STORE_SOURCE
            capture.transcript_messages = list(session_store_capture.transcript_messages)
            run_metrics["session_store_session_id"] = session_store_capture.session_id
            run_metrics["session_store_session_file"] = session_store_capture.session_file
        if session_store_capture is not None:
            run_metrics["session_store_message_count"] = len(
                session_store_capture.transcript_messages
            )

        run_metrics.update(
            {
                "terminated_by": capture.terminated_by,
                "gateway_request_seconds": round_seconds(time.monotonic() - started),
                "http_status_code": capture.http_status_code,
                "response_bytes": capture.response_bytes,
                "finish_reason": capture.finish_reason,
                "usage": capture.usage if isinstance(capture.usage, dict) else None,
                "final_message_chars": len(capture.final_message),
                "transcript_source": capture.transcript_source,
                "transcript_message_count": len(capture.transcript_messages),
            }
        )
        if capture.gateway_error:
            run_metrics["gateway_error"] = capture.gateway_error
        self._last_run_metrics = dict(run_metrics)
        return RunResult(
            final_message=capture.final_message,
            wallclock_s=round_seconds(time.monotonic() - started),
            terminated_by=capture.terminated_by,
            transcript_source=capture.transcript_source,
            transcript_messages=list(capture.transcript_messages),
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
        chase: np.ndarray,
        state: dict[str, Any],
        step_idx: int,
    ) -> dict[str, Any]:
        """POST a turn to ``/v1/chat/completions`` for the named Gateway agent.

        Parameters
        ----------
        agent_id:
            Simulation agent index.  Routed to ``openclaw/{agent_prefix}{agent_id}``.
        frame:
            First-person (FPV) RGB frame as a ``(H, W, 3) uint8`` numpy array.
        overhead:
            Structured overhead map RGB (map_v2) as a ``(H, W, 3) uint8`` numpy array.
        chase:
            Chase camera RGB as a ``(H, W, 3) uint8`` numpy array.
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
        chase_url, chase_metrics = _ndarray_to_data_url(chase)

        agent_name = f"{self._agent_prefix}{agent_id}"
        state_started = time.perf_counter()
        state_json = json.dumps(state, default=str)
        state_json_seconds = time.perf_counter() - state_started
        steer = (
            f"You are RoboClaws {agent_name}, step {step_idx}. "
            f"Follow the ai2thor-navigator skill. "
            f"Current state (JSON): {state_json}. "
            "FPV, structured overhead map, and chase camera attached in order. "
            'Reply with ONLY JSON: {"reasoning": "...", "action": "...".}'
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
                        {"type": "image_url", "image_url": {"url": chase_url}},
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
                "openclaw_encode_chase_seconds": chase_metrics["encode_seconds"],
                "openclaw_state_json_seconds": round_seconds(state_json_seconds),
                "openclaw_gateway_request_seconds": round_seconds(request_seconds),
                "openclaw_response_parse_seconds": round_seconds(parse_seconds),
                "openclaw_bridge_step_seconds": round_seconds(
                    time.perf_counter() - step_started
                ),
            },
            "payload": {
                "transport": "openclaw_data_url",
                "model": self.model_id(agent_id),
                "image_count": 3,
                "state_json_chars": len(state_json),
                "steer_text_chars": len(steer),
                "images": [
                    {"label": "fpv", **fpv_metrics},
                    {"label": "map_v2", **map_metrics},
                    {"label": "chase", **chase_metrics},
                ],
                "total_jpeg_bytes": (
                    fpv_metrics["jpeg_bytes"]
                    + map_metrics["jpeg_bytes"]
                    + chase_metrics["jpeg_bytes"]
                ),
                "total_base64_chars": (
                    fpv_metrics["base64_chars"]
                    + map_metrics["base64_chars"]
                    + chase_metrics["base64_chars"]
                ),
            },
        }
        return result

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _handle_transport_exc(
        self,
        exc: Exception,
        started: float,
        run_metrics: dict[str, Any],
    ) -> NoReturn:
        import httpx

        if isinstance(exc, httpx.ConnectError):
            label, msg = "connect_error", f"Gateway unreachable (local ConnectError): {exc}"
        elif isinstance(exc, httpx.RemoteProtocolError):
            label, msg = "remote_protocol_error", f"Gateway protocol error: {exc}"
        else:
            label, msg = "http_error", f"Gateway transport error: {exc}"
        run_metrics.update(
            {
                "terminated_by": "error",
                "gateway_request_seconds": round_seconds(time.monotonic() - started),
                "gateway_error": label,
            }
        )
        self._last_run_metrics = dict(run_metrics)
        raise OpenClawUnavailable(msg) from exc

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

    def _terminal_body_run(
        self,
        payload: dict[str, Any],
        *,
        timeout: float,
        started: float,
    ) -> _StartRunCapture:
        resp = self._client.post(
            _CHAT_PATH,
            json=payload,
            timeout=timeout,
        )
        body = self._parse_json_response(resp)
        final_message = _extract_content(body)
        transcript_messages: list[TranscriptMessage] = []
        transcript_source: Literal["terminal-body", "none"] = "none"
        if final_message.strip():
            transcript_messages.append(
                TranscriptMessage(
                    wallclock_s=round_seconds(time.monotonic() - started),
                    source="terminal-body",
                    content=final_message,
                    message_index=0,
                    chunk_index=0,
                    is_final=True,
                )
            )
            transcript_source = "terminal-body"

        usage = body.get("usage")
        choice = ((body.get("choices") or [{}])[0]) if isinstance(body, dict) else {}
        return _StartRunCapture(
            terminated_by="done",
            final_message=final_message,
            transcript_source=transcript_source,
            transcript_messages=transcript_messages,
            http_status_code=int(resp.status_code),
            response_bytes=len(resp.content),
            finish_reason=choice.get("finish_reason"),
            usage=usage if isinstance(usage, dict) else None,
        )

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
            _GATEWAY_CONTAINER,
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
    if content is None:
        text = ""
    else:
        text = _extract_text_blocks(content)
    if text:
        return text
    # Reasoning-only fallback: some providers surface the chain-of-thought in
    # a separate field when the answer got truncated.
    for reasoning_field in ("reasoning", "reasoning_content"):
        val = message.get(reasoning_field)
        if isinstance(val, str) and val.strip():
            return val
    return text


def _extract_text_blocks(content: Any) -> str:
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def _is_terminal_stop_reason(stop_reason: Any) -> bool:
    if not isinstance(stop_reason, str):
        return False
    return stop_reason not in {"toolUse", "aborted"}


def _timestamp_to_epoch_seconds(value: Any) -> float | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return (
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .timestamp()
        )
    except ValueError:
        return None


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

    fallback = {"reasoning": content.strip()[:500], "action": "MoveAhead"}
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        _warn_malformed(content)
        return fallback

    if not isinstance(parsed, dict):
        _warn_malformed(content)
        return fallback

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
