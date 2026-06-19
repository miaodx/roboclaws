from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CODING_AGENT_ENV = REPO_ROOT / "scripts" / "dev" / "coding_agent_env.sh"


def clean_code_agent_env() -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "ROBOCLAWS_PYTHON": str(REPO_ROOT / ".venv" / "bin" / "python"),
    }


def run_helper(script: str) -> subprocess.CompletedProcess[str]:
    env = clean_code_agent_env()
    env["ROBOCLAWS_HELPER"] = str(CODING_AGENT_ENV)
    return subprocess.run(
        ["bash", "-c", script],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def test_codex_provider_args_reject_route_incompatible_model_override() -> None:
    result = run_helper(
        """
        set -euo pipefail
        source "$ROBOCLAWS_HELPER"
        ROBOCLAWS_PROVIDER_PROFILE=minimax-responses
        ROBOCLAWS_CODEX_MODEL=gpt-5.5
        MM_API_KEY=fake-mm-key
        args=()
        roboclaws_codex_provider_args args
        """
    )

    assert result.returncode == 2
    assert "coding-agent model 'gpt-5.5' is incompatible with provider 'minimax-responses'" in (
        result.stderr
    )
    assert "incompatible with provider_profile 'minimax-responses'" in result.stderr


def test_codex_provider_args_allow_route_compatible_model_override() -> None:
    result = run_helper(
        """
        set -euo pipefail
        source "$ROBOCLAWS_HELPER"
        ROBOCLAWS_PROVIDER_PROFILE=minimax-responses
        ROBOCLAWS_CODEX_MODEL=MiniMax-M2.7-highspeed
        MM_API_KEY=fake-mm-key
        args=()
        roboclaws_codex_provider_args args
        printf '%s\n' "${args[@]}"
        """
    )

    assert result.returncode == 0
    assert 'model="MiniMax-M2.7-highspeed"' in result.stdout.splitlines()
    assert 'model_provider="minimax-responses"' in result.stdout.splitlines()
