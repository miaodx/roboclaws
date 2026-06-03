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


def test_static_app_has_route_specific_field_groups() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert 'id="isaac-fields"' in html
    assert 'id="agibot-fields"' in html
    assert 'id="agibot-gate-fields"' in html
    assert "renderRouteFields" in app
    assert "field_groups" in app
    assert "NEEDS PREFLIGHT" in app
    assert "NEEDS OPERATOR GATES" in app


def test_static_app_uses_overview_workspace_and_outputs_copy() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    css = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'data-view="overview"' in html
    assert 'data-view="outputs"' in html
    assert 'data-view="artifacts"' not in html
    assert 'id="outputs-panel"' in html
    assert ">Outputs<" in html
    assert "Artifacts" not in html
    assert 'activeView: "overview"' in app
    assert "visiblePanelsForView" in app
    assert "routeViewModes" in app
    assert ".mode-overview" in css
    assert '"fpv map"' in css
    assert '"grounding map"' in css
    assert ".mode-overview.no-grounding" in css
    assert "[hidden]" in css
    assert "display: none !important" in css
