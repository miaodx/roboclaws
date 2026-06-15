from __future__ import annotations

import json
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
    assert 'value="minimax"' in html
    assert 'value="mimo-openai-chat"' in html
    assert 'value="kimi-openai-chat"' in html
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
    assert "Isaac runtime preflight and smoke markers" not in html
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
    assert "Diagnostic" not in app
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
    assert 'id="messup-button"' in html
    assert 'id="messup-status"' in html
    assert "Try Mess-up" in html
    assert "renderScenarioSetup" in app
    assert "defaultScenarioSetup" in app
    assert "selectedScenarioSetup" in app
    assert "previewMessup" in app
    assert "/api/messup-preview" in app
    assert "Baseline remains available" in app
    assert "Baseline means no pre-run relocation" in app
    assert "markCurrentSetupSelection" in app
    assert "resetMessupStatusForManualSetup" in app
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
    assert "?selection_id=" in app
    assert "?route=" not in app
    assert "renderStartAction" in app
    assert "compactRunId" in app
    assert "compactDisplayRunId" in app
    assert "compactRunPart" in app
    assert "Run Attached" in app
    assert "Use Steer or Ask Why" in app
    assert "/api/readiness" in app
    assert "refreshSelectedRouteReadiness" in app
    assert "checkerStatus.message" in app
    assert "state.evidenceLanes" in app
    assert "payload.evidence_lanes" in app
    assert "evidenceLaneOptions" in app
    assert "intentOptionsForCurrentAxes" in app
    assert "node.disabled = Boolean(option.disabled)" in app
    assert "node.title = option.title" in app
    assert "orderedVisibleWorlds(payload.worlds || [])" in app
    assert "enabledLaunchCount > 0" in app
    assert "isMolmospacesWorld" in app
    assert "return leftMolmo ? 1 : -1" in app


def test_static_app_renders_scene_preview_assets() -> None:
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    preview_dir = STATIC_ROOT / "previews"

    assert "renderSelectedScenePreview" in app
    assert "renderSelectedScenePreview(route);" in app
    assert "route.preview_assets" in app
    assert 'setImageSlot("topdown", previews.topdown' in app
    assert "No top-down scene preview is available." in app
    assert "state.activeRunId" in app
    assert "Grounding will appear after a camera-grounded run starts." in app

    preview_files = sorted(path.name for path in preview_dir.glob("molmospaces-val_*-*.png"))
    assert len(preview_files) == 36
    for scene_index in (0, 1, 2, 3, 4, 5, 7, 9):
        for view_name in ("fpv", "map", "chase", "topdown"):
            path = preview_dir / f"molmospaces-val_{scene_index}-{view_name}.png"
            assert path.is_file()
            assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        metadata_path = preview_dir / f"molmospaces-val_{scene_index}-preview.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["views"]["fpv"]["view"] == "raw_fpv"
        assert metadata["views"]["map"]["view"] == "semantic_map_aligned_preview"
        assert metadata["views"]["chase"]["view"] == "chase_camera"
        assert metadata["views"]["chase"]["image_diagnostics"]["visual_status"] == "reviewable"
        assert metadata["views"]["topdown"]["view"] == "topdown_scene_render"
        assert metadata["views"]["topdown"]["semantic_map_fallback"] is False
        assert (
            metadata["views"]["map"]["scene_alignment"]
            == metadata["views"]["topdown"]["scene_alignment"]
        )
        assert metadata["views"]["fpv"]["path"] != metadata["views"]["topdown"]["path"]
        assert metadata["views"]["chase"]["path"] != metadata["views"]["fpv"]["path"]
        assert metadata["views"]["chase"]["path"] != metadata["views"]["topdown"]["path"]
    assert not (preview_dir / "ai2thor-floorplan201-topdown.png").exists()


def test_static_app_exposes_explicit_intent_selector_and_interpretation() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    css = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'id="intent-input"' in html
    assert 'id="intent-preview"' in html
    assert "selectedIntent" in app
    assert "selectedIntentForRoute" in app
    assert "state.selectedIntent = els.intentInput.value;" in app
    assert "state.selectedIntent = selectedIntent();" not in app
    assert "syncAxesFromRoute" in app
    assert "currentSelectValue" in app
    assert "currentSelectValue(\n          els.intentInput" in app
    assert "const scopedCombos = axisMatches.length ? axisMatches : combos;" in app
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
    assert ">Semantic Map<" in html
    assert ">Top-down<" in html
    assert "topdown-frame" in html
    assert "Top-down Scene View" in app
    assert 'activeView: "overview"' in app
    assert "visiblePanelsForView" in app
    assert "routeViewModes" in app
    assert "routeHasOverviewChase" in app
    assert 'resource_kind !== "physical_robot"' in app
    assert 'panels.add("chase")' in app
    assert 'panels.add("blank-chase")' in app
    assert "No chase frame yet" in app
    assert "header-layout-20260615" in html
    assert ".mode-overview" in css
    assert '"fpv map"' in css
    assert '"chase topdown"' in css
    assert "object-position: center center" in css
    assert ".image-panel > .image-frame" in css
    assert "aspect-ratio: auto" in css
    assert '.mode-overview [data-panel="chase"]' in css
    assert '.mode-overview [data-panel="blank-chase"]' in css
    assert ".blank-panel" in css
    assert "[hidden]" in css
    assert "display: none !important" in css
    assert ".top-run-bar.run-active #run-title" in css
    assert "font-size: 14px" in css
    assert "text-overflow: ellipsis" in css


def test_static_app_announces_run_state_via_live_region() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")

    # The event strip is the live region operators monitor peripherally; it
    # must announce terminal state and safety blockers without focus.
    assert 'id="event-log"' in html
    assert 'role="status"' in html
    assert 'aria-live="polite"' in html


def test_static_app_renders_stop_result_before_detaching_run() -> None:
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    detach_body = app.split("function detachRunAfterStop(result) {", 1)[1].split(
        "\n}\n\nasync function toggleRawEvidence",
        1,
    )[0]

    assert "state.activeState = result;" in detach_body
    assert "renderRunState(result);" in detach_body
    assert detach_body.index("renderRunState(result);") < detach_body.index(
        "state.activeRunId = null;"
    )
    assert app.count("const checkerStatus = payload.checker_status || {};") >= 2


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


def test_static_app_keeps_long_run_header_within_fixed_top_bar() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    css = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")
    desktop_controls = css.split(".global-controls {", 1)[1].split("\n}", 1)[0]
    responsive_controls = css.split("@media (max-width: 1360px)", 1)[1].split(
        ".global-controls {",
        1,
    )[1].split("\n  }", 1)[0]

    assert 'href="/styles.css?v=header-layout-20260615"' in html
    assert 'src="/app.js?v=header-layout-20260615"' in html
    assert ".run-meta {\n  display: flex;" in css
    assert "flex-wrap: nowrap;" in css
    assert ".run-meta > *" in css
    assert "#run-title {\n  flex: 1 1 auto;" in css
    assert "overflow: hidden" in css
    assert ".global-controls {\n  display: flex;" in css
    assert "flex: 0 0 auto;" in desktop_controls
    assert "flex-wrap: nowrap;" in desktop_controls
    assert "min-width: max-content;" in desktop_controls
    assert ".global-controls button" in css
    assert "white-space: nowrap;" in css
    assert "@media (max-width: 1360px)" in css
    assert "justify-content: flex-start;" in responsive_controls
    assert "flex-wrap: wrap;" in responsive_controls
    assert "#run-title {\n    flex-basis: 100%;" in css
    assert "function compactRunPart(part)" in app
    assert (
        "return `${fullTimestamp[2]}${fullTimestamp[3]}-"
        "${fullTimestamp[4]}${fullTimestamp[5]}`"
    ) in app
    assert (
        "return `${shortTimestamp[1]}${shortTimestamp[2]}_"
        "${shortTimestamp[3]}${shortTimestamp[4]}`"
    ) in app
    assert '"$2$3-$4$5$7"' not in app


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
