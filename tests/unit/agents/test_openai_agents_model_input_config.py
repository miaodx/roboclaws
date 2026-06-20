from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from roboclaws.agents.drivers.openai_agents_model_input import _input_compaction_config
from roboclaws.agents.live_runtime import LiveAgentMCPServer, LiveAgentRequest
from scripts.molmo_cleanup.openai_agents_perf_profile import resolve_agent_sdk_perf_profile


def _live_request_with_compaction(
    tmp_path: Path,
    min_chars: object | None = None,
) -> LiveAgentRequest:
    config: dict[str, object] = {"enabled": True}
    if min_chars is not None:
        config["min_chars"] = min_chars
    return LiveAgentRequest(
        run_id="household-world.cleanup",
        skill_name="molmo-realworld-cleanup",
        kickoff_prompt="clean the room",
        mcp_server=LiveAgentMCPServer(name="cleanup", url="http://127.0.0.1:18788/mcp"),
        run_dir=tmp_path / "run",
        metadata={"model_input_compaction": config},
    )


def _perf_profile_args(**overrides: object) -> Namespace:
    values = dict.fromkeys(
        """
        max_turns incomplete_turn_continuation_attempts context_soft_limit_tokens
        context_hard_limit_tokens max_observe_per_waypoint raw_fpv_candidate_budget
        done_retry_budget model_input_compaction model_input_compaction_min_chars model_racing
        model_racing_arm_count raw_fpv_repeated_failure_limit raw_fpv_image_memory
        raw_fpv_image_memory_retain camera_grounded_history_compaction
        camera_grounded_history_retain camera_grounded_composite_tools
        model_service_retry_attempts model_service_retry_sleep_s
        model_thinking_mode
        """.split(),
        None,
    )
    values.update(
        provider_profile="codex-router-responses",
        model="gpt-5.5",
        agent_sdk_perf_profile="",
        continuation_mode="",
        model_thinking_mode="default",
        cache_tools_list=True,
        mcp_client_session_timeout_s=30.0,
        robot_view_capture_policy="",
    )
    values.update(overrides)
    return Namespace(**values)


@pytest.mark.parametrize(
    ("env_value", "expected_detail"),
    [
        ("0", "ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS must be a positive integer"),
        ("-5", "ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS must be a positive integer"),
    ],
)
def test_input_compaction_config_rejects_non_positive_min_chars_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    env_value: str,
    expected_detail: str,
) -> None:
    monkeypatch.setenv("ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS", env_value)

    with pytest.raises(ValueError, match=expected_detail):
        _input_compaction_config(_live_request_with_compaction(tmp_path))


@pytest.mark.parametrize(
    ("min_chars", "expected_detail"),
    [
        (True, "model_input_compaction.min_chars must be a positive integer, got True"),
        (0, "model_input_compaction.min_chars must be a positive integer, got 0"),
        (-5, "model_input_compaction.min_chars must be a positive integer, got -5"),
    ],
)
def test_input_compaction_config_rejects_invalid_direct_min_chars(
    tmp_path: Path,
    min_chars: object,
    expected_detail: str,
) -> None:
    with pytest.raises(ValueError, match=expected_detail):
        _input_compaction_config(_live_request_with_compaction(tmp_path, min_chars))


@pytest.mark.parametrize(
    ("env_value", "direct_value", "expected_error"),
    [
        (
            "0",
            None,
            "OpenAI Agents SDK setting model_input_compaction_min_chars must be positive",
        ),
        (
            "",
            0,
            "OpenAI Agents SDK setting model_input_compaction_min_chars must be positive",
        ),
        (
            "",
            True,
            "OpenAI Agents SDK setting model_input_compaction_min_chars must be an integer",
        ),
    ],
)
def test_perf_profile_rejects_invalid_compaction_min_chars(
    monkeypatch: pytest.MonkeyPatch,
    env_value: str,
    direct_value: object | None,
    expected_error: str,
) -> None:
    if env_value:
        monkeypatch.setenv("ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS", env_value)
    else:
        monkeypatch.delenv("ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS", raising=False)

    with pytest.raises(ValueError, match=expected_error):
        resolve_agent_sdk_perf_profile(
            _perf_profile_args(model_input_compaction_min_chars=direct_value)
        )
