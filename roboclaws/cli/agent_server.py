"""CLI router for supported coding-agent MCP servers."""

from __future__ import annotations

import sys

SUPPORTED_SERVERS = ("household-cleanup", "semantic-map-build")


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        expected = "|".join(SUPPORTED_SERVERS)
        print(f"error: missing server (expected {expected})", file=sys.stderr)
        return 2

    server = args.pop(0)
    if server == "household-cleanup":
        from roboclaws.cli.household_agent_server import main as household_main

        return household_main(args)
    if server == "semantic-map-build":
        from roboclaws.cli.agibot_map_build_agent_server import main as semantic_map_main

        return semantic_map_main(args)

    expected = "|".join(SUPPORTED_SERVERS)
    print(f"error: unsupported server {server!r} (expected {expected})", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
