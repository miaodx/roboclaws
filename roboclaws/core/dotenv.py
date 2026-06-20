from __future__ import annotations

import os
from pathlib import Path


def load_dotenv_file(
    path: Path,
    env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return an environment with values loaded from a simple KEY=VALUE dotenv file."""

    env_map = dict(os.environ if env is None else env)
    if not path.exists():
        return env_map
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in env_map:
            continue
        env_map[key] = clean_dotenv_value(value)
    return env_map


def update_env_from_dotenv_file(path: Path, env: dict[str, str] | None = None) -> dict[str, str]:
    """Load dotenv values into ``env`` in place and return the updated mapping."""

    env_map = os.environ if env is None else env
    loaded = load_dotenv_file(path, env_map)
    env_map.update(loaded)
    return env_map


def clean_dotenv_value(value: str) -> str:
    clean = value.strip()
    if clean.startswith("export "):
        clean = clean.removeprefix("export ").strip()
    if len(clean) >= 2 and clean[0] == clean[-1] and clean[0] in {"'", '"'}:
        clean = clean[1:-1]
    return clean
