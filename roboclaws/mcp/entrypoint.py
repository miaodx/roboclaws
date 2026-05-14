"""Generic MCP entrypoint/router helpers for selected contract profiles."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from roboclaws.mcp.profiles import ContractProfile, contract_profile, contract_profile_names

ToolHandler = Callable[..., Any]


class MCPProfileRouter:
    """Register exactly one contract profile's public tool surface."""

    def __init__(
        self,
        profile_id: str,
        handlers: Mapping[str, ToolHandler],
        *,
        allow_extra_handlers: bool = False,
    ) -> None:
        self.profile = load_contract_profile(profile_id)
        self.handlers = dict(handlers)
        self.allow_extra_handlers = allow_extra_handlers
        self._validate_handlers()

    def public_tool_names(self) -> tuple[str, ...]:
        return self.profile.public_tool_names()

    def register_tools(self, mcp: Any) -> tuple[str, ...]:
        registered: list[str] = []
        for tool in self.profile.public_tools:
            handler = self.handlers[tool.name]
            mcp.tool(name=tool.name, description=tool.summary)(handler)
            registered.append(tool.name)
        return tuple(registered)

    def _validate_handlers(self) -> None:
        expected = set(self.profile.public_tool_names())
        provided = set(self.handlers)
        missing = sorted(expected - provided)
        if missing:
            raise ValueError(
                f"profile {self.profile.profile_id} missing handlers for: {', '.join(missing)}"
            )
        extras = sorted(provided - expected)
        if extras and not self.allow_extra_handlers:
            raise ValueError(
                f"profile {self.profile.profile_id} got handlers outside public profile: "
                f"{', '.join(extras)}"
            )


def load_contract_profile(profile_id: str) -> ContractProfile:
    try:
        return contract_profile(profile_id)
    except ValueError as exc:
        expected = ", ".join(contract_profile_names())
        raise ValueError(
            f"unknown MCP contract profile {profile_id!r}; allowed profiles: {expected}"
        ) from exc


def register_profile_tools(
    mcp: Any,
    *,
    profile_id: str,
    handlers: Mapping[str, ToolHandler],
    allow_extra_handlers: bool = False,
) -> tuple[str, ...]:
    router = MCPProfileRouter(
        profile_id,
        handlers,
        allow_extra_handlers=allow_extra_handlers,
    )
    return router.register_tools(mcp)
