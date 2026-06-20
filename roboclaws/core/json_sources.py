from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} source is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} source must contain valid JSON object: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} source must contain a JSON object: {path}")
    return payload
