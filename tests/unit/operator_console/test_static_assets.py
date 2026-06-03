from __future__ import annotations

import re
from pathlib import Path

STATIC_ROOT = Path(__file__).resolve().parents[3] / "roboclaws" / "operator_console" / "static"


def test_static_app_references_existing_dom_ids() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    declared_ids = set(re.findall(r'id="([^"]+)"', html))
    referenced_ids = set(re.findall(r'getElementById\("([^"`$]+)"\)', app))

    assert referenced_ids - declared_ids == set()
