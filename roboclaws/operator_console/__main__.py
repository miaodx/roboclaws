"""Entrypoint for ``python -m roboclaws.operator_console``."""

from __future__ import annotations

from roboclaws.operator_console.server import main

if __name__ == "__main__":
    raise SystemExit(main())
