#!/usr/bin/env python3
"""Thin wrapper for the household cleanup direct CLI."""

from __future__ import annotations

from roboclaws.household.realworld_cleanup import (
    SYNTHETIC_BACKEND,
    main,
    run_realworld_cleanup,
)

__all__ = ["SYNTHETIC_BACKEND", "main", "run_realworld_cleanup"]


if __name__ == "__main__":
    raise SystemExit(main())
