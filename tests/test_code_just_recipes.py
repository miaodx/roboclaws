"""Regression tests for `just/code.just` recipe wiring.

Locks in the fix for the 2026-04-28 bug where `just code::cc` registered the
MCP server with a corrupted URL (``http://host=127.0.0.1:port=18788/mcp``)
because the `cc` recipe passed ``host="..." port="..."`` after the recipe
name. In `just`, tokens after a recipe name are positional — ``name=value``
becomes the literal value of the next positional parameter, prefix and all.
"""

from __future__ import annotations

import re
from pathlib import Path

CODE_JUST = Path(__file__).resolve().parent.parent / "just" / "code.just"

# Matches an inter-recipe call to mcp_up and captures the trailing argument list
# up to end-of-line. Excludes the recipe definition header (which has `:` after
# the name and parameter list).
_MCP_UP_CALL = re.compile(r"just code::mcp_up\s+([^\n]+?)(?:\)|$)", re.MULTILINE)


def _inter_recipe_calls() -> list[str]:
    text = CODE_JUST.read_text(encoding="utf-8")
    return [
        m.group(1).strip()
        for m in _MCP_UP_CALL.finditer(text)
        # Skip the recipe definition line: `mcp_up scene="..." host="..." port="...":`
        if not m.group(0).startswith("mcp_up ")
    ]


def test_code_just_exists() -> None:
    assert CODE_JUST.is_file(), f"missing {CODE_JUST}"


def test_cc_and_codex_call_mcp_up_with_positional_args() -> None:
    calls = _inter_recipe_calls()
    assert len(calls) >= 2, (
        f"expected cc + codex to both call code::mcp_up, found {len(calls)}: {calls}"
    )
    for call in calls:
        for forbidden in ("scene=", "host=", "port="):
            assert forbidden not in call, (
                f"`just code::mcp_up` invocation uses `{forbidden}` named-arg syntax: "
                f"{call!r}. After a recipe name, just treats `name=value` as the "
                'literal positional value — use `"{{scene}}" "{{host}}" "{{port}}"` '
                "instead. See 2026-04-28 bug: corrupt MCP URL like "
                "http://host=127.0.0.1:port=18788/mcp."
            )


def test_mcp_url_template_is_well_formed() -> None:
    """The URL template inside mcp_up must produce a clean http://host:port/mcp."""
    text = CODE_JUST.read_text(encoding="utf-8")
    # Both warm-path and cold-path build the URL with the same template.
    # Only match literal-URL assignments, not capture-from-subshell ones.
    matches = re.findall(r'mcp_url="(http://[^"]+)"', text)
    assert matches, "expected mcp_url assignments in code.just"
    for url in matches:
        assert url == "http://{{host}}:{{port}}/mcp", f"unexpected mcp_url template: {url!r}"
