from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_script_module():
    path = Path("scripts/dev/benchmark_model_matrix.py")
    spec = importlib.util.spec_from_file_location("benchmark_model_matrix", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_default_cases_cover_routes_and_wire_formats() -> None:
    script = _load_script_module()

    cases = {case.case_id: case for case in script.default_cases()}

    assert "codex-env:gpt-5.5:responses" in cases
    assert "mify:xiaomi-mimo-v2.5:openai-chat" in cases
    assert "mify:xiaomi-mimo-v2.5:openai-responses" in cases
    assert "mify:xiaomi-mimo-v2.5:anthropic" in cases
    assert "minimax:MiniMax-M3:responses" in cases
    assert "mimo-token-plan:mimo-v2.5:openai-chat" in cases
    assert "mimo-token-plan:mimo-v2.5:anthropic" in cases
    assert "mimo-inside:mimo-1000:openai-chat" in cases
    assert "kimi:k2.6:anthropic" in cases
    assert "nvidia:nemotron-nano-vl:chat" in cases
    assert {case.wire_api for case in cases.values()} == {
        "openai-chat",
        "openai-responses",
        "anthropic-messages",
    }


def test_nvidia_cases_read_adjacent_base_url_env(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_BASE_URL", "https://nvidia.example/v1")
    script = _load_script_module()

    cases = {case.case_id: case for case in script.default_cases()}

    assert cases["nvidia:nemotron-nano-vl:chat"].base_url == "https://nvidia.example/v1"
    assert cases["nvidia:nemotron-nano-vl:responses"].base_url == "https://nvidia.example/v1"


def test_mimo_inside_cases_read_registry_env(monkeypatch) -> None:
    monkeypatch.setenv("MIMO_BASE_URL", "https://inside.example/v1")
    script = _load_script_module()

    cases = {case.case_id: case for case in script.default_cases()}

    case = cases["mimo-inside:mimo-1000:openai-chat"]
    assert case.base_url == "https://inside.example/v1"
    assert case.api_key_env == "MIMO_API_KEY"
    assert "Default-enabled" in case.note


def test_endpoint_urls_normalize_wire_api_suffixes() -> None:
    script = _load_script_module()

    assert (
        script.endpoint_url("http://example.test", "openai-chat")
        == "http://example.test/v1/chat/completions"
    )
    assert (
        script.endpoint_url("http://example.test/v1", "openai-responses")
        == "http://example.test/v1/responses"
    )
    assert (
        script.endpoint_url("http://example.test/anthropic", "anthropic-messages")
        == "http://example.test/anthropic/v1/messages"
    )


def test_payloads_match_wire_format() -> None:
    script = _load_script_module()
    cases = {case.case_id: case for case in script.default_cases()}

    chat_payload = script.payload_for_case(
        cases["mimo-inside:mimo-1000:openai-chat"],
        prompt="ping",
        max_tokens=8,
    )
    responses_payload = script.payload_for_case(
        cases["mify:xiaomi-mimo-v2.5:openai-responses"],
        prompt="ping",
        max_tokens=8,
    )
    anthropic_payload = script.payload_for_case(
        cases["kimi:k2.6:anthropic"],
        prompt="ping",
        max_tokens=8,
    )

    assert chat_payload["messages"] == [{"role": "user", "content": "ping"}]
    assert chat_payload["max_tokens"] == 8
    assert "input" not in chat_payload
    assert responses_payload["input"] == "ping"
    assert responses_payload["max_output_tokens"] == 8
    assert "messages" not in responses_payload
    assert anthropic_payload["messages"] == [{"role": "user", "content": "ping"}]
    assert anthropic_payload["max_tokens"] == 8
    assert "max_output_tokens" not in anthropic_payload


def test_default_token_budget_leaves_room_for_reasoning() -> None:
    script = _load_script_module()

    assert script.DEFAULT_MAX_TOKENS >= 512
    assert script.DEFAULT_FIRST_CONTENT_MAX_TOKENS >= 256
    assert script.DEFAULT_THROUGHPUT_MAX_TOKENS >= 2048
    assert script.DEFAULT_STREAM_THROUGHPUT_MAX_TOKENS >= 4096
    assert script.DEFAULT_AGENT_CASE_MAX_TOKENS >= 512
    assert "2500 words" in script.DEFAULT_STREAM_THROUGHPUT_PROMPT
    assert script.DEFAULT_LAYERS == ("health", "throughput")
    assert "first-content" in script.LAYER_CHOICES
    assert "stream-throughput" in script.LAYER_CHOICES
    assert "agent-case" in script.LAYER_CHOICES


def test_headers_include_anthropic_version_and_custom_user_agent() -> None:
    script = _load_script_module()
    cases = {case.case_id: case for case in script.default_cases()}

    headers = script.headers_for_case(cases["kimi:k2.6:anthropic"], api_key="secret")

    assert headers["Authorization"] == "Bearer secret"
    assert headers["x-api-key"] == "secret"
    assert headers["anthropic-version"] == "2023-06-01"
    assert headers["User-Agent"] == "Claude-Code/1.0"


def test_missing_key_skips_without_secret_values() -> None:
    script = _load_script_module()
    case = script.MatrixCase(
        case_id="mimo-inside:mimo-1000:openai-chat",
        provider_id="mimo-inside",
        provider_label="MiMo inside",
        model="mimo-1000",
        wire_api="openai-chat",
        api_key_env="MIMO_API_KEY",
        base_url="https://mimo.example/v1",
    )

    result = script.run_case(
        case,
        layer="health",
        prompt="ping",
        iterations=1,
        max_tokens=8,
        timeout_s=1.0,
        env={"MIMO_BASE_URL": "https://secret.example"},
    )

    assert result.status == "SKIP"
    assert result.skipped_reason == "missing MIMO_API_KEY"
    assert "secret.example" not in str(result)


def test_result_payload_counts_statuses() -> None:
    script = _load_script_module()
    args = script.parse_args(["--iterations", "1"])

    payload = script.result_payload(
        [
            script.CaseResult(
                case_id="a",
                provider_id="p",
                provider_label="P",
                model="m",
                wire_api="openai-chat",
                layer="health",
                agent_case_id="",
                agent_case_label="",
                agent_case_source="",
                expected_support="native",
                status="PASS",
                api_key_env="KEY",
                api_key_alt_env="",
                base_url_configured=True,
                iterations=1,
                max_tokens=512,
                success_count=1,
                failure_count=0,
            ),
            script.CaseResult(
                case_id="b",
                provider_id="p",
                provider_label="P",
                model="m",
                wire_api="openai-responses",
                layer="throughput",
                agent_case_id="",
                agent_case_label="",
                agent_case_source="",
                expected_support="probe",
                status="FAIL",
                api_key_env="KEY",
                api_key_alt_env="",
                base_url_configured=True,
                iterations=1,
                max_tokens=2048,
                success_count=0,
                failure_count=1,
            ),
        ],
        args=args,
    )

    assert payload["benchmark"] == "roboclaws_model_matrix_wire_support_v1"
    assert payload["layers"] == ["health", "throughput"]
    assert payload["first_content_max_tokens"] >= 256
    assert payload["throughput_max_tokens"] >= 2048
    assert payload["stream_throughput_max_tokens"] >= 4096
    assert payload["agent_case_max_tokens"] >= 512
    assert payload["prompts"]["agent-case"]
    assert payload["status_counts"]["PASS"] == 1
    assert payload["status_counts"]["FAIL"] == 1
    assert payload["status_counts"]["SKIP"] == 0


def test_usage_tokens_and_tps_prefer_provider_usage() -> None:
    script = _load_script_module()
    case = {case.case_id: case for case in script.default_cases()}[
        "mimo-inside:mimo-1000:openai-chat"
    ]

    result = script.summarize_case(
        case,
        layer="throughput",
        trials=(
            script.TrialResult(
                index=1,
                layer="throughput",
                status="PASS",
                elapsed_s=2.0,
                response_model="mimo-v2.5-pro",
                output_preview="ok " * 40,
                output_chars=300,
                measured_output_tokens=200,
                output_token_count_source="provider_usage",
                output_tokens_per_s=100.0,
                output_chars_per_s=150.0,
                first_content_s=0.2,
                decode_s=1.8,
                decode_output_tokens_per_s=111.111,
                decode_output_chars_per_s=166.667,
                completion_tokens=200,
            ),
        ),
        iterations=1,
        max_tokens=2048,
        base_url_configured=True,
    )

    assert result.layer == "throughput"
    assert result.max_tokens == 2048
    assert result.median_output_tokens_per_s == 100.0
    assert result.median_output_chars_per_s == 150.0
    assert result.median_decode_output_tokens_per_s == 111.111
    assert result.median_first_content_s == 0.2
    assert result.median_decode_s == 1.8
    assert result.output_token_count_source == "provider_usage"
    assert result.output_preview.startswith("ok")


def test_stream_throughput_skips_non_chat_wire() -> None:
    script = _load_script_module()
    case = {case.case_id: case for case in script.default_cases()}[
        "mify:xiaomi-mimo-v2.5:openai-responses"
    ]

    result = script.run_case(
        case,
        layer="stream-throughput",
        prompt="ping",
        iterations=1,
        max_tokens=8,
        timeout_s=1.0,
        env={"XM_LLM_API_KEY": "secret"},
    )

    assert result.status == "SKIP"
    assert "OpenAI Chat streaming" in result.skipped_reason


def test_max_tokens_for_layer_uses_stream_budget() -> None:
    script = _load_script_module()
    args = script.parse_args(
        [
            "--first-content-max-tokens",
            "16",
            "--stream-throughput-max-tokens",
            "8192",
            "--stream-throughput-prompt",
            "stream",
            "--agent-case-max-tokens",
            "777",
        ]
    )

    assert script._max_tokens_for_layer(args, "health") == script.DEFAULT_MAX_TOKENS
    assert script._max_tokens_for_layer(args, "first-content") == 16
    assert script._max_tokens_for_layer(args, "throughput") == (
        script.DEFAULT_THROUGHPUT_MAX_TOKENS
    )
    assert script._max_tokens_for_layer(args, "stream-throughput") == 8192
    assert script._max_tokens_for_layer(args, "agent-case") == 777
    assert script._prompt_for_layer(args, "stream-throughput") == "stream"


def test_first_content_stream_payload_omits_usage_tail(monkeypatch) -> None:
    script = _load_script_module()
    case = script.MatrixCase(
        case_id="mimo-inside:mimo-1000:openai-chat",
        provider_id="mimo-inside",
        provider_label="MiMo inside",
        model="mimo-1000",
        wire_api="openai-chat",
        api_key_env="MIMO_API_KEY",
        base_url="https://mimo.example/v1",
    )
    captured: dict[str, object] = {}

    class _Response:
        status = 200
        headers = {"content-type": "text/event-stream"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __iter__(self):
            return iter(
                [
                    b"event: message\n",
                    b'data: {"model":"mimo-1000","choices":[{"delta":{"content":"ok"}}]}\n',
                    b"data: [DONE]\n",
                ]
            )

    def fake_urlopen(request, timeout):  # noqa: ANN001
        captured["payload"] = script.json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(script.urllib.request, "urlopen", fake_urlopen)

    result = script.run_trial(
        case,
        index=1,
        layer="first-content",
        prompt="stream",
        max_tokens=8,
        timeout_s=1.0,
        api_key="secret",
    )

    payload = captured["payload"]
    assert payload["stream"] is True
    assert "stream_options" not in payload
    assert result.status == "PASS"
    assert result.first_content_s is not None


def test_stream_throughput_payload_requests_usage_tail(monkeypatch) -> None:
    script = _load_script_module()
    case = script.MatrixCase(
        case_id="mimo-inside:mimo-1000:openai-chat",
        provider_id="mimo-inside",
        provider_label="MiMo inside",
        model="mimo-1000",
        wire_api="openai-chat",
        api_key_env="MIMO_API_KEY",
        base_url="https://mimo.example/v1",
    )
    captured: dict[str, object] = {}

    class _Response:
        status = 200
        headers = {"content-type": "text/event-stream"}

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def __iter__(self):
            return iter(
                [
                    b'data: {"model":"mimo-1000","choices":[{"delta":{"content":"ok"}}]}\n',
                    b"data: [DONE]\n",
                ]
            )

    def fake_urlopen(request, timeout):  # noqa: ANN001
        captured["payload"] = script.json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setattr(script.urllib.request, "urlopen", fake_urlopen)

    result = script.run_trial(
        case,
        index=1,
        layer="stream-throughput",
        prompt="stream",
        max_tokens=8,
        timeout_s=1.0,
        api_key="secret",
    )

    payload = captured["payload"]
    assert payload["stream"] is True
    assert payload["stream_options"] == {"include_usage": True}
    assert result.status == "PASS"
    assert result.first_content_s is not None


def test_agent_cases_are_selectable_and_do_not_store_full_prompt() -> None:
    script = _load_script_module()

    selected = script.selected_agent_cases(case_ids={"sdk-speedup-verdict"})

    assert [case.case_id for case in selected] == ["sdk-speedup-verdict"]
    assert "raw prompts" in selected[0].prompt
    assert len(selected[0].prompt) > 240


def test_agent_case_summary_carries_case_metadata() -> None:
    script = _load_script_module()
    case = {case.case_id: case for case in script.default_cases()}[
        "mimo-inside:mimo-1000:openai-chat"
    ]
    agent_case = script.selected_agent_cases(case_ids={"cleanup-worklist-plan"})[0]

    result = script.summarize_case(
        case,
        layer="agent-case",
        trials=(
            script.TrialResult(
                index=1,
                layer="agent-case",
                status="PASS",
                elapsed_s=2.0,
                agent_case_id=agent_case.case_id,
                agent_case_label=agent_case.label,
                output_preview="actions...",
                output_chars=300,
                measured_output_tokens=120,
                output_token_count_source="estimated_chars_div_4",
                output_tokens_per_s=60.0,
            ),
        ),
        iterations=1,
        max_tokens=768,
        base_url_configured=True,
        agent_case=agent_case,
    )

    assert result.agent_case_id == "cleanup-worklist-plan"
    assert result.agent_case_label
    assert result.agent_case_source.endswith("agent_view.json")
    assert result.output_preview == "actions..."


def test_measured_output_tokens_falls_back_to_char_estimate() -> None:
    script = _load_script_module()

    count, source = script.measured_output_token_count(output="a" * 40, completion_tokens=None)

    assert count == 10
    assert source == "estimated_chars_div_4"


def test_trial_results_store_preview_not_full_output() -> None:
    script = _load_script_module()

    trial = script.TrialResult(
        index=1,
        layer="throughput",
        status="PASS",
        elapsed_s=1.0,
        output_preview="preview",
        output_chars=4000,
    )

    assert "output" not in script.asdict(trial)
    assert script.asdict(trial)["output_preview"] == "preview"
