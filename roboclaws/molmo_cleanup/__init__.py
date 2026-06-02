"""Legacy import alias for the household domain package."""

from __future__ import annotations

from pathlib import Path

# Keep old ``roboclaws.molmo_cleanup.<module>`` imports working while current
# source moves to ``roboclaws.household``. The alias is intentionally lightweight
# so dependency-light scripts can import this package without pulling report/map
# dependencies through eager re-exports.
__path__ = [str(Path(__file__).resolve().parents[1] / "household")]
