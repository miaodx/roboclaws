"""Shared live-agent launcher status classification."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LiveAgentFailure:
    reason: str
    retryable: bool = False
    provider_reason: str = ""
    resume_available: bool = False
    detail: str = ""

    def status_fields(self) -> dict[str, object]:
        fields: dict[str, object] = {
            "reason": self.reason,
            "retryable": self.retryable,
            "resume_available": self.resume_available,
        }
        if self.provider_reason:
            fields["provider_reason"] = self.provider_reason
        if self.detail:
            fields["detail"] = self.detail
        return fields


def classify_live_agent_failure(*paths: Path, exit_status: int | None = None) -> LiveAgentFailure:
    text = _combined_tail(paths)
    lowered = text.lower()

    if _contains_any(lowered, ("authentication", "unauthorized", "invalid api key", "401")):
        return LiveAgentFailure("provider_auth_failure", detail=_snippet(text, "auth"))
    if _contains_any(lowered, ("context length", "context_length", "maximum context", "too large")):
        return LiveAgentFailure("provider_context_failure", detail=_snippet(text, "context"))
    if _contains_any(lowered, ("model not found", "invalid model", "unsupported model")):
        return LiveAgentFailure("provider_config_failure", detail=_snippet(text, "model"))
    if _contains_any(
        lowered,
        (
            "update_plan",
            "read_mcp_resource",
            "resources/read failed",
            "does not contain function",
            "requires namespace for namespace function tools",
            "function_call name",
            "not declared in tools",
            "unknown mcp server",
            "mcp__",
        ),
    ):
        return LiveAgentFailure("tool_binding_failure", detail=_snippet(text, "tool"))
    if "idle timeout" in lowered:
        return LiveAgentFailure("idle_timeout", detail=_snippet(text, "idle timeout"))

    provider_reason = _provider_transient_reason(lowered)
    if provider_reason:
        return LiveAgentFailure(
            "provider_transient_failure",
            retryable=True,
            provider_reason=provider_reason,
            resume_available=True,
            detail=_snippet(text, provider_reason),
        )

    detail = _tail_for_detail(text)
    if exit_status is None:
        return LiveAgentFailure("agent_cli_failure", detail=detail)
    return LiveAgentFailure(f"agent_cli_failure_status_{exit_status}", detail=detail)


def _provider_transient_reason(lowered: str) -> str:
    if _contains_any(
        lowered,
        (
            "429 too many requests",
            "too many requests",
            "rate limit",
            "ratelimit",
            "provider_rate_limit",
            "exceeded retry limit, last status: 429",
        ),
    ):
        return "rate_limit"
    if _contains_any(
        lowered,
        (
            "status: 502",
            "status 502",
            "http 502",
            "502 bad gateway",
            "status: 503",
            "status 503",
            "http 503",
            "503 service unavailable",
            "status: 504",
            "status 504",
            "http 504",
            "504 gateway timeout",
            "upstream unavailable",
            "upstream service unavailable",
            "bad gateway",
            "service unavailable",
            "gateway timeout",
        ),
    ):
        return "upstream_unavailable"
    if _contains_any(
        lowered,
        (
            "request timed out",
            "request timeout",
            "provider timeout",
            "upstream timeout",
            "timed out waiting",
            "timeout while",
            "deadline exceeded",
            "connection reset",
            "connection aborted",
            "connection refused",
            "connection closed",
            "broken pipe",
            "econnreset",
        ),
    ):
        return "upstream_timeout"
    return ""


def _combined_tail(paths: tuple[Path, ...], *, max_bytes_per_file: int = 128_000) -> str:
    parts: list[str] = []
    for path in paths:
        if not path.is_file():
            continue
        try:
            with path.open("rb") as handle:
                handle.seek(0, 2)
                size = handle.tell()
                handle.seek(max(size - max_bytes_per_file, 0), 0)
                data = handle.read(max_bytes_per_file)
        except OSError:
            continue
        text = data.decode("utf-8", errors="replace")
        if text:
            parts.append(f"[{path.name}]\n{text}")
    return "\n".join(parts)


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _snippet(text: str, pattern: str) -> str:
    lowered = text.lower()
    index = lowered.find(pattern.lower())
    if index < 0:
        return _tail_for_detail(text)
    start = max(index - 120, 0)
    end = min(index + len(pattern) + 180, len(text))
    return " ".join(text[start:end].split())


def _tail_for_detail(text: str, *, max_chars: int = 500) -> str:
    return " ".join(text[-max_chars:].split())
