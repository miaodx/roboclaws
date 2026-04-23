from __future__ import annotations

# Thin re-bind: OpenClawProvider lives in roboclaws.openclaw.bridge.
# Import it here so the providers package surface is consistent.
from roboclaws.openclaw.bridge import OpenClawProvider

__all__ = ["OpenClawProvider"]
