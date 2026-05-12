from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_PATH = REPO_ROOT / "examples" / "molmo_cleanup" / "molmo_cleanup_agent_server.py"


def _load_server_module():
    spec = importlib.util.spec_from_file_location("molmo_cleanup_agent_server", SERVER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_molmo_agent_server_prints_codex_claude_and_openclaw_setup(
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_server_module()

    module.print_setup(
        tmp_path,
        "http://127.0.0.1:18788/mcp",
        "codex_agent",
    )

    output = capsys.readouterr().out
    assert "Molmo cleanup MCP server is ready." in output
    assert "codex mcp add roboclaws --url http://127.0.0.1:18788/mcp" in output
    assert "claude mcp add --transport http roboclaws http://127.0.0.1:18788/mcp" in output
    assert "ROBOCLAWS_MCP_URL=http://host.docker.internal:18788/mcp" in output
    assert "skills/molmo-cleanup/SKILL.md" in output
    assert "roboclaws__observe" in output
    assert "current_contract" in output
    assert "Backend       : api_semantic_synthetic" in output
    assert "Visual report : disabled" in output


def test_molmo_agent_server_prints_visual_setup(tmp_path: Path, capsys) -> None:
    module = _load_server_module()

    module.print_setup(
        tmp_path,
        "http://127.0.0.1:18788/mcp",
        "codex_agent",
        backend="molmospaces_subprocess",
        record_robot_views=True,
    )

    output = capsys.readouterr().out
    assert "Backend       : molmospaces_subprocess" in output
    assert "Visual report : enabled" in output


def test_molmo_agent_server_client_setup_commands() -> None:
    module = _load_server_module()

    commands = module.client_setup_commands("http://127.0.0.1:18788/mcp")

    assert commands["Codex"] == "codex mcp add roboclaws --url http://127.0.0.1:18788/mcp"
    assert commands["Claude Code"] == (
        "claude mcp add --transport http roboclaws http://127.0.0.1:18788/mcp"
    )
    assert commands["OpenClaw"].startswith("ROBOCLAWS_MCP_URL=http://host.docker.internal:")
