from __future__ import annotations

# ---------------------------------------------------------------------------
# Shared grid / heading helpers — used by both CoverageGame and TerritoryGame.
# ---------------------------------------------------------------------------

_MOVE_ACTIONS: frozenset[str] = frozenset({"MoveAhead", "MoveBack", "MoveLeft", "MoveRight"})
_DECISION_ACTIONS: tuple[str, ...] = (
    "MoveAhead",
    "MoveBack",
    "MoveLeft",
    "MoveRight",
    "RotateLeft",
    "RotateRight",
)


def _heading_index(rotation: dict[str, float]) -> int:
    """Return the nearest 90-degree heading bucket as 0/1/2/3."""
    return int(round(float(rotation.get("y", 0.0)) / 90.0)) % 4


def _forward_delta(rotation: dict[str, float]) -> tuple[int, int]:
    """Return the discrete forward delta for the given rotation."""
    return (
        (0, 1),
        (1, 0),
        (0, -1),
        (-1, 0),
    )[_heading_index(rotation)]


def _rotation_after_turn(rotation: dict[str, float], action: str) -> dict[str, float]:
    """Return the rotation after applying a 90-degree turn action."""
    delta = -90.0 if action == "RotateLeft" else 90.0
    new_rotation = dict(rotation)
    new_rotation["y"] = (float(rotation.get("y", 0.0)) + delta) % 360.0
    return new_rotation


def _move_target_cell(
    cell: tuple[int, int],
    rotation: dict[str, float],
    action: str,
) -> tuple[int, int]:
    """Return the destination cell for a discrete movement action."""
    dx, dz = _forward_delta(rotation)
    if action == "MoveAhead":
        delta = (dx, dz)
    elif action == "MoveBack":
        delta = (-dx, -dz)
    elif action == "MoveLeft":
        delta = (-dz, dx)
    else:
        delta = (dz, -dx)
    return (cell[0] + delta[0], cell[1] + delta[1])


def _pos_to_cell(pos: dict[str, float], grid_size: float) -> tuple[int, int]:
    """Convert a continuous (x, z) position to a discrete grid cell index."""
    return (round(pos["x"] / grid_size), round(pos["z"] / grid_size))
