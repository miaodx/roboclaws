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
    assert lines == [
        "← toolResult roboclaws__observe delivery=images parts=['image', 'image', 'text']"
    ]


def test_fmt_content_observe_tool_result_surfaces_text_bridge_delivery() -> None:
    parts = [
        {
            "type": "toolResult",
            "toolCallId": "call-1",
            "toolName": "roboclaws__observe",
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "observe_delivery": "text-bridge",
                            "view_variant": "map-v2+chase",
                            "image_labels": ["vision_bridge"],
                        }
                    ),
                },
                {"type": "text", "text": "Immediate view: clear hall."},
            ],
        }
    ]
    lines = _fmt_content(parts)
    assert lines == ["← toolResult roboclaws__observe delivery=text-bridge parts=['text', 'text']"]


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


# ---------------------------------------------------------------------------
# Default log path + symlink maintenance
# ---------------------------------------------------------------------------


def test_latest_run_dir_picks_newest_mtime(tmp_path: Path, monkeypatch) -> None:
    """_latest_run_dir returns the run subdir with the most recent mtime."""
    import os

    runs_dir = tmp_path / "output" / "openclaw-interactive"
    older = runs_dir / "20260422T100000Z"
    newer = runs_dir / "20260423T100000Z"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    os.utime(older, (1000, 1000))
    os.utime(newer, (2000, 2000))

    monkeypatch.setattr(_mod, "_DEFAULT_RUNS_DIR", runs_dir)
    assert _mod._latest_run_dir() == newer


def test_latest_run_dir_returns_none_when_no_runs(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(_mod, "_DEFAULT_RUNS_DIR", tmp_path / "missing")
    assert _mod._latest_run_dir() is None


def test_refresh_latest_symlink_creates_relative_link(tmp_path: Path, monkeypatch) -> None:
    """Symlink at output/openclaw-interactive/latest-chat.log points at
    the run's chat.log via a relative path so the tree stays portable."""
    runs_dir = tmp_path / "output" / "openclaw-interactive"
    run = runs_dir / "20260423T100000Z"
    run.mkdir(parents=True)
    target = run / "chat.log"
    target.write_text("one line\n", encoding="utf-8")

    link = runs_dir / "latest-chat.log"
    monkeypatch.setattr(_mod, "_LATEST_SYMLINK", link)
    _mod._refresh_latest_symlink(target)

    assert link.is_symlink()
    # Relative link: readlink yields `20260423T100000Z/chat.log` (not abs).
    readlink = link.readlink()
    assert not readlink.is_absolute(), (
        f"symlink should be relative so the tree stays portable; got {readlink!r}"
    )
    assert link.resolve() == target.resolve()


def test_refresh_latest_symlink_replaces_existing_link(tmp_path: Path, monkeypatch) -> None:
    """Re-running against a new run dir replaces the symlink, not errors."""
    runs_dir = tmp_path / "output" / "openclaw-interactive"
    run_a = runs_dir / "runA"
    run_b = runs_dir / "runB"
    for r in (run_a, run_b):
        r.mkdir(parents=True)
        (r / "chat.log").write_text("x", encoding="utf-8")

    link = runs_dir / "latest-chat.log"
    monkeypatch.setattr(_mod, "_LATEST_SYMLINK", link)

    _mod._refresh_latest_symlink(run_a / "chat.log")
    _mod._refresh_latest_symlink(run_b / "chat.log")

    assert link.resolve() == (run_b / "chat.log").resolve()
