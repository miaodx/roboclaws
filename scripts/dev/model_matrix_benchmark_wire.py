"""Wire-format helpers for the model-matrix benchmark."""

from __future__ import annotations

import json
import urllib.parse
from typing import Any

from model_matrix_benchmark_catalog import MatrixCase, WireApi

from roboclaws.agents.thinking_policy import thinking_request_body_for_wire


def openai_chat_stream_event(raw_line: bytes) -> dict[str, Any] | None:
    line = raw_line.decode("utf-8", errors="replace").strip()
    if not line:
        return None
    if line.startswith("data:"):
        line = line.removeprefix("data:").strip()
    elif line.startswith(("event:", "id:", "retry:", ":")) or not line.startswith("{"):
        return None
    if not line or line == "[DONE]":
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    return event if isinstance(event, dict) else None


def latest_usage_tokens(
    wire_api: WireApi,
    event: dict[str, Any],
    *,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    total_tokens: int | None,
) -> tuple[int | None, int | None, int | None]:
    usage_prompt, usage_completion, usage_total = usage_tokens(wire_api, event)
    return (
        usage_prompt if usage_prompt is not None else prompt_tokens,
        usage_completion if usage_completion is not None else completion_tokens,
        usage_total if usage_total is not None else total_tokens,
    )


def openai_chat_stream_piece(event: dict[str, Any]) -> str:
    choices = event.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first = choices[0] if isinstance(choices[0], dict) else {}
    delta = first.get("delta") if isinstance(first, dict) else {}
    if not isinstance(delta, dict):
        return ""
    return str(delta.get("content") or delta.get("reasoning_content") or "")


def endpoint_url(base_url: str, wire_api: WireApi) -> str:
    base = base_url.strip().rstrip("/")
    if wire_api == "openai-chat":
        return _openai_endpoint(base, "chat/completions")
    if wire_api == "openai-responses":
        return _openai_endpoint(base, "responses")
    return _anthropic_endpoint(base)


def payload_for_case(case: MatrixCase, *, prompt: str, max_tokens: int) -> dict[str, Any]:
    if case.wire_api == "openai-chat":
        payload: dict[str, Any] = {
            "model": case.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        }
        if case.provider_id == "kimi" and case.model == "kimi-k2.7-code":
            payload.update(
                thinking_request_body_for_wire(
                    provider_profile="kimi-openai-chat",
                    wire_api="chat-completions",
                    mode="default",
                )
            )
        return payload
    if case.wire_api == "openai-responses":
        payload = {
            "model": case.model,
            "input": prompt,
            "max_output_tokens": max_tokens,
            "stream": False,
        }
        payload.update(
            thinking_request_body_for_wire(
                provider_profile=case.provider_id,
                wire_api="responses",
                mode="default",
            )
        )
        return payload
    return {
        "model": case.model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }


def headers_for_case(case: MatrixCase, *, api_key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if case.wire_api == "anthropic-messages":
        headers["anthropic-version"] = "2023-06-01"
        headers["x-api-key"] = api_key
    headers.update(dict(case.headers))
    return headers


def output_text(wire_api: WireApi, data: dict[str, Any]) -> str:
    if wire_api == "openai-chat":
        return _openai_chat_output_text(data)
    if wire_api == "openai-responses":
        return _openai_responses_output_text(data)
    return _anthropic_messages_output_text(data)


def response_model(wire_api: WireApi, data: dict[str, Any]) -> str:
    if wire_api in {"openai-chat", "openai-responses"}:
        return str(data.get("model") or "")
    return str(data.get("model") or "")


def usage_tokens(
    wire_api: WireApi, data: dict[str, Any]
) -> tuple[int | None, int | None, int | None]:
    usage = data.get("usage") if isinstance(data, dict) else {}
    if not isinstance(usage, dict):
        return None, None, None
    if wire_api == "anthropic-messages":
        prompt_tokens = _int_or_none(usage.get("input_tokens"))
        completion_tokens = _int_or_none(usage.get("output_tokens"))
        total_tokens = (
            prompt_tokens + completion_tokens
            if prompt_tokens is not None and completion_tokens is not None
            else None
        )
        return prompt_tokens, completion_tokens, total_tokens
    return (
        _int_or_none(usage.get("prompt_tokens")),
        _int_or_none(usage.get("completion_tokens")),
        _int_or_none(usage.get("total_tokens")),
    )


def _openai_endpoint(base: str, suffix: str) -> str:
    if base.endswith("/" + suffix):
        return base
    parsed = urllib.parse.urlparse(base)
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/{suffix}"


def _anthropic_endpoint(base: str) -> str:
    if base.endswith("/v1/messages"):
        return base
    return f"{base}/v1/messages"


def _openai_chat_output_text(data: dict[str, Any]) -> str:
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    return str(message.get("content") or message.get("reasoning_content") or "").strip()


def _openai_responses_output_text(data: dict[str, Any]) -> str:
    direct = data.get("output_text")
    if direct:
        return str(direct).strip()
    output = data.get("output")
    if not isinstance(output, list):
        return ""
    parts: list[str] = []
    for item in output:
        if isinstance(item, dict):
            parts.extend(_response_content_text_parts(item.get("content")))
    return "\n".join(parts).strip()


def _response_content_text_parts(content: Any) -> list[str]:
    if not isinstance(content, list):
        return []
    return [str(part["text"]) for part in content if isinstance(part, dict) and part.get("text")]


def _anthropic_messages_output_text(data: dict[str, Any]) -> str:
    content = data.get("content")
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text"))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text" and part.get("text")
        ).strip()
    return ""


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None
