from __future__ import annotations

import json

from roboclaws.openclaw.transcript_recovery import (
    SessionStoreReader,
    extract_text_blocks,
    timestamp_to_epoch_seconds,
)


def test_session_store_reader_recovers_new_assistant_transcript() -> None:
    reader = SessionStoreReader(agent_prefix="agent-")
    session_file = "/home/node/.openclaw/agents/agent-0/sessions/new.jsonl"
    index_payload = {
        "old": {
            "sessionId": "old-session",
            "startedAt": 1776844930000,
            "sessionFile": "/home/node/.openclaw/agents/agent-0/sessions/old.jsonl",
        },
        "new": {
            "sessionId": "new-session",
            "startedAt": 1776844941000,
            "sessionFile": session_file,
        },
    }
    transcript_lines = [
        {
            "type": "message",
            "timestamp": "2026-04-22T08:02:22.466Z",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "Checking"},
                    {"type": "toolCall", "name": "roboclaws__observe"},
                    {"type": "text", "text": " session"},
                ],
                "stopReason": "stop",
            },
        }
    ]

    def fake_read_container_text(path: str) -> str:
        if path.endswith("/sessions/sessions.json"):
            return json.dumps(index_payload)
        if path == session_file:
            return "\n".join(json.dumps(line) for line in transcript_lines)
        return ""

    reader._read_container_text = fake_read_container_text  # type: ignore[method-assign]

    capture = reader.recover(
        agent_id=0,
        started_wallclock=1776844940.0,
        preexisting_ids={"old-session"},
    )

    assert capture is not None
    assert capture.session_id == "new-session"
    assert capture.session_file == session_file
    assert len(capture.transcript_messages) == 1
    message = capture.transcript_messages[0]
    assert message.source == "session-store"
    assert message.content == "Checking session"
    assert message.wallclock_s == 2.466
    assert message.is_final is True


def test_transcript_recovery_text_helpers_are_imported_from_recovery_module() -> None:
    assert (
        extract_text_blocks(
            [
                {"type": "text", "text": "Checking"},
                {"type": "toolCall", "name": "roboclaws__observe"},
                {"type": "text", "text": " session"},
            ]
        )
        == "Checking session"
    )
    assert timestamp_to_epoch_seconds("2026-04-22T08:02:22.466Z") == 1776844942.466
