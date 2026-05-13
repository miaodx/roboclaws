"""Regression tests for `just/code.just` ↔ `just/mcp.just` wiring.

Locks in the fix for the 2026-04-28 bug where `just code::cc` registered the
MCP server with a corrupted URL (``http://host=127.0.0.1:port=18788/mcp``)
because the `cc` recipe passed ``host="..." port="..."`` after the recipe
name. In `just`, tokens after a recipe name are positional — ``name=value``
becomes the literal value of the next positional parameter, prefix and all.

Also pins the cross-module wiring: `code::cc` and `code::codex` must call
the shared `mcp::up` / `mcp::down` recipes rather than duplicating the
lifecycle logic.
"""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "justfile").is_file():
            return parent
    raise AssertionError("could not locate repo root")


REPO_ROOT = _repo_root()
JUST_DIR = REPO_ROOT / "just"
CODE_JUST = JUST_DIR / "code.just"
MCP_JUST = JUST_DIR / "mcp.just"
MOLMO_JUST = JUST_DIR / "molmo.just"
HARNESS_RUN = REPO_ROOT / "harness" / "run.sh"
LIVE_CODEX_RUNNER = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_codex_cleanup.py"

# Matches an inter-recipe call to mcp::up and captures the trailing argument
# list up to end-of-line. Excludes the recipe definition header.
_MCP_UP_CALL = re.compile(r"just mcp::up\s+([^\n]+?)(?:\)|$)", re.MULTILINE)


def _inter_recipe_calls() -> list[str]:
    text = CODE_JUST.read_text(encoding="utf-8")
    return [m.group(1).strip() for m in _MCP_UP_CALL.finditer(text)]


def test_just_files_exist() -> None:
    assert CODE_JUST.is_file(), f"missing {CODE_JUST}"
    assert MCP_JUST.is_file(), f"missing {MCP_JUST}"


def test_cc_and_codex_call_mcp_up_with_positional_args() -> None:
    calls = _inter_recipe_calls()
    assert len(calls) >= 2, f"expected cc + codex to both call mcp::up, found {len(calls)}: {calls}"
    for call in calls:
        for forbidden in ("scene=", "host=", "port="):
            assert forbidden not in call, (
                f"`just mcp::up` invocation uses `{forbidden}` named-arg syntax: "
                f"{call!r}. After a recipe name, just treats `name=value` as the "
                'literal positional value — use `"{{scene}}" "{{host}}" "{{port}}"` '
                "instead. See 2026-04-28 bug: corrupt MCP URL like "
                "http://host=127.0.0.1:port=18788/mcp."
            )


def test_mcp_url_template_is_well_formed() -> None:
    """The URL template inside mcp::up must produce a clean http://host:port/mcp."""
    text = MCP_JUST.read_text(encoding="utf-8")
    # Only match literal-URL assignments, not capture-from-subshell ones.
    matches = re.findall(r'mcp_url="(http://[^"]+)"', text)
    assert matches, "expected mcp_url assignments in mcp.just"
    for url in matches:
        assert url == "http://{{host}}:{{port}}/mcp", f"unexpected mcp_url template: {url!r}"


def test_code_just_does_not_duplicate_mcp_lifecycle() -> None:
    """`code.just` must delegate to mcp::up / mcp::down, not redefine them."""
    text = CODE_JUST.read_text(encoding="utf-8")
    # No standalone recipe headers for mcp_up / mcp_down (and no top-level
    # state vars duplicating the mcp module).
    forbidden_headers = (
        re.compile(r"^mcp_up\s", re.MULTILINE),
        re.compile(r"^mcp_down:", re.MULTILINE),
        re.compile(r"^server_pid_file\s*:=", re.MULTILINE),
    )
    for pattern in forbidden_headers:
        assert not pattern.search(text), (
            f"code.just defines `{pattern.pattern}` but should delegate to "
            f"just/mcp.just. Move the lifecycle to mcp.just."
        )


def test_code_agent_launches_default_to_full_permissions() -> None:
    """Direct Codex / Claude Code just recipes should not launch in read-only mode."""
    text = CODE_JUST.read_text(encoding="utf-8")

    assert 'codex_full_permission_args := "--dangerously-bypass-approvals-and-sandbox"' in text
    assert (
        'claude_full_permission_args := "--dangerously-skip-permissions '
        '--permission-mode bypassPermissions"'
    ) in text
    assert 'codex "${codex_model_args[@]}" {{codex_full_permission_args}}' in text
    assert (
        'claude_command=(claude "${claude_model_args[@]}" {{claude_full_permission_args}})' in text
    )
    assert 'for entry in "${claude_env_args[@]}"; do' in text
    assert 'export "$entry"' in text
    assert "codex --yolo" not in text
    assert re.search(r"^\s+codex\s*$", text, re.MULTILINE) is None
    assert re.search(r"^\s+claude\s*$", text, re.MULTILINE) is None


def test_molmo_codex_live_waits_for_server_and_runs_prompted_exec() -> None:
    """Molmo Codex reports should be runnable without a manual prompt paste."""
    text = MOLMO_JUST.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")

    assert "wait_for_mcp_ready" in text
    assert 'tmux new-session -d -s "$session_name"' in text
    assert '"exec"' in runner_text
    assert '"--json"' in runner_text
    assert '"--output-last-message"' in runner_text
    assert "*self.args.codex_model_arg" in runner_text
    assert 'FULL_PERMISSION_ARG = "--dangerously-bypass-approvals-and-sandbox"' in runner_text
    assert '"--cd"' in runner_text
    assert 'kickoff_prompt="Read skills/molmo-realworld-cleanup/SKILL.md.' in text


def test_other_just_files_do_not_launch_bare_coding_agents() -> None:
    """Keep future wrappers from bypassing the full-permission code recipes."""
    for path in JUST_DIR.glob("*.just"):
        if path == CODE_JUST:
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if re.match(r"^(codex|claude)\s+mcp(\s|$)", stripped):
                continue
            assert not re.match(r"^(codex|claude)(\s|$)", stripped), (
                f"{path.relative_to(JUST_DIR.parent)} launches a coding agent directly: "
                f"{stripped!r}. Route through just code::codex / code::cc or use the "
                "full-permission defaults from just/code.just."
            )


def test_navigator_harness_inherits_full_permission_code_recipe() -> None:
    text = HARNESS_RUN.read_text(encoding="utf-8")

    assert "just code::cc" in text
    assert "default full-permission launch args" in text
