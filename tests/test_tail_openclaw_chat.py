# ruff: noqa: I001

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# Import via file because the script name contains a hyphen.
import importlib.util  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "tail_openclaw_chat",
    Path(__file__).resolve().parent.parent / "scripts" / "tail-openclaw-chat.py",
)
assert _SPEC and _SPEC.loader
_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_mod)

_fmt_content = _mod._fmt_content
_render_line = _mod._render_line


def test_fmt_content_text_only() -> None:
    parts = [{"type": "text", "text": "hello world"}]
    assert _fmt_content(parts) == ["hello world"]


def test_fmt_content_tool_call_summarises_name_and_args() -> None:
    parts = [
        {
            "type": "toolCall",
            "id": "call-1",
            "name": "roboclaws__move",
            "arguments": {"direction": "MoveAhead", "reason": "toward plate"},
        }
    ]
    lines = _fmt_content(parts)
    assert len(lines) == 1
    line = lines[0]
    assert line.startswith("→ toolCall roboclaws__move ")
    assert "MoveAhead" in line
    assert "toward plate" in line


def test_fmt_content_tool_result_preserves_inner_kinds() -> None:
    parts = [
        {
            "type": "toolResult",
            "toolCallId": "call-1",
            "toolName": "roboclaws__observe",
            "content": [
                {"type": "image", "source": {"type": "base64"}},
                {"type": "image", "source": {"type": "base64"}},
                {"type": "text", "text": "state json"},
            ],
        }
    ]
    lines = _fmt_content(parts)
    assert lines == ["← toolResult roboclaws__observe parts=['image', 'image', 'text']"]


def test_fmt_content_image_block_rendered() -> None:
    parts = [{"type": "image", "source": {"type": "base64"}}]
    assert _fmt_content(parts) == ["[image: base64]"]


def test_fmt_content_truncates_long_args() -> None:
    payload = {"x": "y" * 500}
    parts = [{"type": "toolCall", "name": "foo", "arguments": payload}]
    line = _fmt_content(parts)[0]
    assert len(line) < 160
    assert line.endswith("...")


def test_render_line_message_with_text_and_tool_call() -> None:
    raw = json.dumps(
        {
            "type": "message",
            "message": {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "working on it"},
                    {"type": "toolCall", "name": "roboclaws__observe", "arguments": {}},
                ],
            },
        }
    )
    lines = _render_line(raw)
    assert lines[0] == "assistant: working on it"
    assert lines[1].strip().startswith("→ toolCall roboclaws__observe")


def test_render_line_non_message_events_are_terse() -> None:
    assert _render_line(json.dumps({"type": "session"})) == [". session"]
    assert _render_line(json.dumps({"type": "model_change"})) == [". model_change"]


def test_render_line_invalid_json_is_flagged() -> None:
    lines = _render_line("{not json")
    assert lines == ["?? invalid json: {not json"]
