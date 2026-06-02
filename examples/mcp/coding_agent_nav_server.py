#!/usr/bin/env python3
"""Thin wrapper for the AI2-THOR coding-agent MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from roboclaws.cli.agent_server import ai2thor_nav_server_main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(ai2thor_nav_server_main())
