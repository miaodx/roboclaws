from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "dev" / "network_status.sh"
CODING_AGENT_ENV = REPO_ROOT / "scripts" / "dev" / "coding_agent_env.sh"
JUST_DIR = REPO_ROOT / "just"


def _fake_curl(tmp_path: Path, http_code: str) -> dict[str, str]:
    fake = tmp_path / "curl"
    fake.write_text(
        f"#!/usr/bin/env bash\nprintf '%s' '{http_code}'\n",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    return env


def test_network_status_reports_work_when_probe_returns_http(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=REPO_ROOT,
        env=_fake_curl(tmp_path, "403"),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "network: work" in result.stdout
    assert "api-router.evad.mioffice.cn" in result.stdout


def test_assert_off_work_blocks_when_probe_is_reachable(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--assert-off-work", "Claude Code"],
        cwd=REPO_ROOT,
        env=_fake_curl(tmp_path, "204"),
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "work network detected" in result.stderr


def test_assert_off_work_allows_when_probe_is_unreachable(tmp_path: Path) -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--assert-off-work", "OpenClaw"],
        cwd=REPO_ROOT,
        env=_fake_curl(tmp_path, "000"),
        check=True,
        capture_output=True,
        text=True,
    )

    assert "network guard ok" in result.stderr


def test_claude_provider_guard_blocks_system_provider_on_work_network(tmp_path: Path) -> None:
    env = _fake_curl(tmp_path, "204")
    env.pop("ROBOCLAWS_CLAUDE_PROVIDER", None)
    env.pop("ROBOCLAWS_CODE_AGENT_PROVIDER", None)

    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            roboclaws_assert_claude_code_network_allowed "Claude Code"
            """,
        ],
        cwd=REPO_ROOT,
        env={**env, "ROBOCLAWS_HELPER": str(CODING_AGENT_ENV)},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "blocked while using system Claude Code provider" in result.stderr


def test_claude_provider_guard_allows_repo_local_provider_on_work_network(tmp_path: Path) -> None:
    env = _fake_curl(tmp_path, "204")
    env["ROBOCLAWS_CLAUDE_PROVIDER"] = "kimi-anthropic"

    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            roboclaws_assert_claude_code_network_allowed "Claude Code"
            """,
        ],
        cwd=REPO_ROOT,
        env={**env, "ROBOCLAWS_HELPER": str(CODING_AGENT_ENV)},
        check=True,
        capture_output=True,
        text=True,
    )

    assert "repo-local Claude provider (kimi-anthropic)" in result.stderr


def test_codex_provider_guard_blocks_system_provider_on_work_network(tmp_path: Path) -> None:
    env = _fake_curl(tmp_path, "204")
    env.pop("ROBOCLAWS_CODEX_PROVIDER", None)
    env.pop("ROBOCLAWS_CODE_AGENT_PROVIDER", None)

    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            roboclaws_assert_codex_network_allowed "Codex"
            """,
        ],
        cwd=REPO_ROOT,
        env={**env, "ROBOCLAWS_HELPER": str(CODING_AGENT_ENV)},
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "blocked while using system Codex provider" in result.stderr


def test_codex_provider_guard_allows_explicit_provider_on_work_network(tmp_path: Path) -> None:
    env = _fake_curl(tmp_path, "204")
    env["ROBOCLAWS_CODEX_PROVIDER"] = "codex-env"

    result = subprocess.run(
        [
            "bash",
            "-c",
            """
            set -euo pipefail
            source "$ROBOCLAWS_HELPER"
            roboclaws_assert_codex_network_allowed "Codex"
            """,
        ],
        cwd=REPO_ROOT,
        env={**env, "ROBOCLAWS_HELPER": str(CODING_AGENT_ENV)},
        check=True,
        capture_output=True,
        text=True,
    )

    assert "explicit Codex provider (codex-env)" in result.stderr


def test_claude_and_openclaw_just_recipes_use_network_guard() -> None:
    openclaw_guarded_files = (
        JUST_DIR / "openclaw.just",
        JUST_DIR / "chat.just",
        JUST_DIR / "appliance.just",
        JUST_DIR / "verify.just",
        JUST_DIR / "dev.just",
    )

    for path in openclaw_guarded_files:
        text = path.read_text(encoding="utf-8")
        assert "bash scripts/dev/network_status.sh --assert-off-work" in text, path

    for path in (JUST_DIR / "code.just", JUST_DIR / "harness.just", JUST_DIR / "molmo.just"):
        text = path.read_text(encoding="utf-8")
        assert "roboclaws_assert_claude_code_network_allowed" in text, path

    for path in (JUST_DIR / "code.just", JUST_DIR / "molmo.just"):
        text = path.read_text(encoding="utf-8")
        assert "roboclaws_assert_codex_network_allowed" in text, path

    assert "network-status:" in (JUST_DIR / "dev.just").read_text(encoding="utf-8")
