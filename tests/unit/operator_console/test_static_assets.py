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
    assert 'id="codex-fields"' in html
    assert 'id="codex-provider-input"' in html
    assert 'id="codex-model-input"' not in html
    assert 'id="claude-fields"' in html
    assert 'id="claude-provider-input"' in html
    assert 'value="kimi-anthropic"' in html
    assert 'value="mimo-anthropic"' in html
    assert 'value="mify-anthropic"' in html
    assert 'id="agibot-fields"' in html
    assert 'id="agibot-gate-fields"' in html
    assert 'id="real-movement-gate"' in html
    assert 'id="isaac-preflight-gate"' not in html
    assert "Isaac preflight accepted" not in html
    assert "Isaac runtime preflight and smoke markers" in html
    assert "renderRouteFields" in app
    assert "field_groups" in app
    assert "real_movement_enabled" in app
    assert "Movement" in app
    assert "Provider" in app
    assert "env_overrides" in app
    assert "ROBOCLAWS_CODEX_PROVIDER" in app
    assert "ROBOCLAWS_CLAUDE_PROVIDER" in app
    assert "selectedCodexProvider" in app
    assert "selectedClaudeProvider" in app
    assert "Diagnostic" in app
    assert "Capability Gate" in app
    assert "NEEDS SAFETY GATES" in app
    assert "NEEDS CONTEXT" in app
    assert "NEEDS PREFLIGHT" not in app
    assert "NEEDS OPERATOR GATES" not in app
    assert "PORT IN USE" in app
    assert "ATTACH" in app
    assert "Attach Existing Run" in app
    assert "Latest Result" in html
    assert "latest-result-button" in app
    assert 'id="camera-angle-value"' in html
    assert "cameraStateLabel" in app
    assert "renderToolPanel" in app
    assert 'class="setup-panel"' in html
    assert 'class="state-rail"' in html
    setup_html = html.split('<aside class="setup-panel">', 1)[1].split("</aside>", 1)[0]
    state_rail_html = html.split('<aside class="state-rail">', 1)[1].split("</aside>", 1)[0]
    assert "Operator Input" in setup_html
    assert "Operator Input" not in state_rail_html
    assert 'id="prompt-label"' in html
    assert "Scenario seed for reproducible runs" in html
    assert "Baseline does not relocate objects" in html
    assert "Generated mess count" not in html
    assert 'id="mess-count-input"' not in html
    assert 'id="scenario-setup-input"' in html
    assert 'name="scenario_setup"' in html
    assert "Relocate loose objects" in html
    assert "Relocate cleanup-related objects" in html
    assert 'id="relocation-count-field"' in html
    assert 'id="relocation-count-input"' in html
    assert 'name="relocation_count"' in html
    assert "renderScenarioSetup" in app
    assert "defaultScenarioSetup" in app
    assert "selectedScenarioSetup" in app
    assert "generated_mess_count" not in app
    assert 'data-operator-mode="ask_why"' in html
    assert 'data-operator-mode="steer"' in html
    assert 'data-operator-mode="goal"' in html
    assert 'data-operator-mode="continue"' not in html
    assert 'id="operator-message-input"' not in html
    assert 'id="operator-message-button"' not in html
    assert "Continue" not in html
    assert "/continue" not in app
    assert "/next-goal" in app
    assert "Start Next Goal" in app
    assert "Confirm Next Goal" in app
    assert "/ask-why" in app
    assert "check_operator_messages" in app
    assert "attachLatestResult" in app
    assert "/api/runs/latest" in app
    assert "attachExistingRun" in app
    assert "attachable_run" in app
    assert "renderStartAction" in app
    assert "Run Attached" in app
    assert "Use Steer or Ask Why" in app
    assert "/api/readiness" in app
    assert "refreshSelectedRouteReadiness" in app
    assert "checker_status.message" in app


def test_static_app_exposes_explicit_intent_selector_and_interpretation() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    css = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'id="intent-input"' in html
    assert 'id="intent-preview"' in html
    assert "selectedIntent" in app
    assert "selectedIntentForRoute" in app
    assert "launchInterpretation" in app
    assert "route.intent_options" in app
    assert "intent_id: selectedIntent()" in app
    assert "world_id: route.world_id" in app
    assert "backend_id: route.backend_id" in app
    assert "agent_engine_id: route.agent_engine_id" in app
    assert "scenario_setup: selectedScenarioSetup()" in app
    assert "intent=${selected}" in app
    assert '"open-ended": "Open-ended"' in app
    assert "Goal scope" in app
    assert "Checker" in app
    assert "Evaluation" in app
    assert "prompt-scoped" in app
    assert "checker_id" in app
    assert ".intent-preview" in css


def test_static_app_uses_overview_workspace_and_outputs_copy() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    css = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'data-view="overview"' in html
    assert 'data-view="outputs"' in html
    assert 'data-view="artifacts"' not in html
    assert 'id="outputs-panel"' in html
    assert 'data-panel="blank-chase"' in html
    assert ">Outputs<" in html
    assert "Artifacts" not in html
    assert 'activeView: "overview"' in app
    assert "visiblePanelsForView" in app
    assert "routeViewModes" in app
    assert "routeHasOverviewChase" in app
    assert 'resource_kind !== "physical_robot"' in app
    assert 'panels.add("blank-chase")' in app
    assert "No chase frame yet" in app
    assert "decision-proof-20260608" in html
    assert ".mode-overview" in css
    assert '"fpv map"' in css
    assert '"chase map"' in css
    assert '.mode-overview [data-panel="blank-chase"]' in css
    assert ".blank-panel" in css
    assert "[hidden]" in css
    assert "display: none !important" in css


def test_static_app_announces_run_state_via_live_region() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")

    # The event strip is the live region operators monitor peripherally; it
    # must announce terminal state and safety blockers without focus.
    assert 'id="event-log"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html


def test_static_app_has_resizable_run_evidence_panel() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    css = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'id="state-rail-resizer"' in html
    assert 'id="evidence-strip-resizer"' in html
    assert 'role="separator"' in html
    assert 'class="splitter state-rail-splitter"' in html
    assert 'class="splitter event-strip-splitter"' in html
    assert 'title="Drag to resize raw evidence log panel"\n          hidden' in html
    assert 'href="/styles.css?v=' in html
    assert 'src="/app.js?v=' in html
    assert 'aria-label="Resize run evidence panel"' in html
    assert 'aria-label="Resize raw evidence log panel"' in html
    assert "STATE_RAIL_WIDTH_KEY" in app
    assert "EVIDENCE_STRIP_HEIGHT_KEY" in app
    assert "startStateRailResize" in app
    assert "startEvidenceStripResize" in app
    assert "setPointerCapture" in app
    assert "ArrowLeft" in app
    assert "ArrowUp" in app
    assert "els.evidenceStripResizer.hidden = !hidden" in app
    assert "refreshRawEvidence()" in app
    assert "forceStickToBottom: true" in app
    assert "shouldStickToBottom" in app
    assert "raw-evidence-open" in app
    assert "--state-rail-width" in css
    assert "--evidence-strip-height" in css
    assert ".state-rail-splitter" in css
    assert ".event-strip-splitter" in css
    assert "cursor: col-resize" in css
    assert "cursor: row-resize" in css
    assert ".raw-evidence" in css
    assert "overflow: auto" in css
    assert "white-space: pre" in css


def test_static_app_routes_destructive_actions_through_styled_dialog() -> None:
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    css = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")

    # Stop and Emergency Stop must use the themed <dialog>, not native
    # window.confirm, and carry the contract CTA labels.
    assert "window.confirm" not in app
    assert "confirmAction(" in app
    assert "Trigger Emergency Stop" in app
    assert "Stop Run" in app

    # Run title reaches the 28px display role only once a run is active.
    assert ".top-run-bar.run-active #run-title" in css
    assert "font-variant-numeric: tabular-nums" in css


def test_static_app_hides_pause_until_a_route_supports_it() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert 'id="pause-button" class="secondary" disabled hidden' in html
    assert "const pauseAvailable = Boolean(controls.pause_available)" in app
    assert "els.pauseButton.hidden = !pauseAvailable" in app
    assert "els.pauseButton.disabled = !pauseAvailable" in app


def test_static_app_opens_images_in_large_dialog() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    css = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'id="image-dialog"' in html
    assert 'id="image-dialog-img"' in html
    assert "image-preview-button" in app
    assert "openImageDialog" in app
    assert "showModal()" in app
    assert "data-image-src" in app
    assert ".image-dialog" in css
    assert ".image-dialog-frame img" in css
    assert "max-height: calc(100vh - 168px)" in css
    assert "transform: scale(1.02)" in css
