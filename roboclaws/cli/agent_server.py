"""CLI router for supported coding-agent MCP servers."""

from __future__ import annotations

import sys

SUPPORTED_SERVER_TARGETS = ("household-world.cleanup", "household-world.map-build")
SERVER_TARGET_ALIASES = {
    "household-world.cleanup": "household-cleanup",
    "cleanup": "household-cleanup",
    "household-world.map-build": "semantic-map-build",
    "map-build": "semantic-map-build",
}


def _expected_server_text() -> str:
    return "|".join(SUPPORTED_SERVER_TARGETS)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(f"error: missing server (expected {_expected_server_text()})", file=sys.stderr)
        return 2

    raw_server = args.pop(0)
    server = SERVER_TARGET_ALIASES.get(raw_server)
    if server is None:
        print(
            f"error: unsupported server {raw_server!r} (expected {_expected_server_text()})",
            file=sys.stderr,
        )
        return 2
    if server == "household-cleanup":
        from roboclaws.cli.household_agent_server import main as household_main

        return household_main(args)
    if server == "semantic-map-build":
        from roboclaws.cli.agibot_map_build_agent_server import main as semantic_map_main

        return semantic_map_main(args)

    print(
        f"error: unsupported server {raw_server!r} (expected {_expected_server_text()})",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
