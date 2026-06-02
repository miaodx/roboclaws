"""Runner command builders for launch plans."""

from __future__ import annotations


def build_agent_run_argv(
    *,
    task: str,
    driver: str,
    mode: str,
    overrides: tuple[str, ...],
) -> tuple[str, ...]:
    """Return the current lower dispatcher command for a public task route."""

    return ("just", "agent::run", task, driver, mode, *overrides)
