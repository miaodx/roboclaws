"""Internal transcript recovery seam for OpenClaw autonomous runs.

This module is intentionally imported by transport tests and by
``roboclaws.openclaw.transport``. It is not re-exported from
``roboclaws.openclaw.bridge`` so the provider adapter surface stays focused on
Gateway turns.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from roboclaws.core.turn_metrics import round_seconds

TranscriptSource = Literal["terminal-body", "session-store", "none"]
SESSION_STORE_SOURCE: Literal["session-store"] = "session-store"
GATEWAY_CONTAINER = "openclaw-gateway"


@dataclass
class TranscriptMessage:
    wallclock_s: float
    source: TranscriptSource
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
class SessionStoreCapture:
    session_id: str
    session_file: str
    transcript_messages: list[TranscriptMessage]


class SessionStoreReader:
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
    ) -> SessionStoreCapture | None:
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
        return SessionStoreCapture(
            session_id=session_id,
            session_file=session_file,
            transcript_messages=transcript_messages,
        )

    def _read_container_text(self, path: str) -> str:
        result = subprocess.run(
            ["docker", "exec", GATEWAY_CONTAINER, "cat", path],
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
            content = extract_text_blocks(message.get("content"))
            if not content.strip():
                continue
            timestamp = timestamp_to_epoch_seconds(entry.get("timestamp"))
            transcript_messages.append(
                TranscriptMessage(
                    wallclock_s=max(
                        0.0,
                        round_seconds(
                            timestamp - started_wallclock if timestamp is not None else 0.0
                        ),
                    ),
                    source=SESSION_STORE_SOURCE,
                    content=content,
                    message_index=len(transcript_messages),
                    chunk_index=0,
                    is_final=is_terminal_stop_reason(message.get("stopReason")),
                )
            )
        return transcript_messages


def extract_text_blocks(content: Any) -> str:
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


def is_terminal_stop_reason(stop_reason: Any) -> bool:
    if not isinstance(stop_reason, str):
        return False
    return stop_reason not in {"toolUse", "aborted"}


def timestamp_to_epoch_seconds(value: Any) -> float | None:
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
