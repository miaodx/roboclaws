from __future__ import annotations

import html
import os
from collections.abc import Iterable
from typing import Any

REPORT_RERUN_COMMAND_ENV = "ROBOCLAWS_REPORT_RERUN_COMMAND"


def report_rerun_command_from_env() -> str:
    return os.environ.get(REPORT_RERUN_COMMAND_ENV, "").strip()


def shell_join(command: Iterable[Any]) -> str:
    return " ".join(_shell_quote(str(item)) for item in command)


def render_rerun_panel(command: str | None, *, note: str = "") -> str:
    command = (command or report_rerun_command_from_env()).strip()
    if not command:
        return ""
    note_html = f'<p class="rerun-note">{html.escape(note)}</p>' if note else ""
    return (
        '<section class="rerun-panel">'
        "<h2>Rerun Locally</h2>"
        f"{note_html}"
        f"<pre><code>{html.escape(command)}</code></pre>"
        "</section>"
    )


def rerun_panel_css() -> str:
    return (
        ".rerun-panel { background: #fff; border: 1px solid #d8dfeb;"
        " border-left: 4px solid #2952cc; border-radius: 8px; padding: 1rem;"
        " box-shadow: 0 1px 4px #0001; margin-bottom: 1rem; }"
        ".rerun-panel h2 { margin: 0 0 0.5rem; font-size: 1rem; color: #1f2a44; }"
        ".rerun-panel pre { margin: 0; background: #f6f8fb; border: 1px solid #e0e4ec;"
        " border-radius: 6px; padding: 0.75rem; overflow-x: auto;"
        " font-size: 0.85rem; line-height: 1.45; }"
        ".rerun-note { margin: 0 0 0.65rem; color: #5f6c85; font-size: 0.88rem; }"
    )


def _shell_quote(text: str) -> str:
    if not text:
        return "''"
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-"
    if all(char in safe for char in text):
        return text
    return "'" + text.replace("'", "'\"'\"'") + "'"
