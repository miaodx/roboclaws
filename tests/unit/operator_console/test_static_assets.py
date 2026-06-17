from __future__ import annotations

import json
import re
from pathlib import Path

from roboclaws.launch.worlds import (
    MOLMOSPACES_CONSOLE_WORLD_IDS,
    MOLMOSPACES_LAUNCH_ALIAS_SCENE_INDICES,
    WORLD_SPECS,
)

STATIC_ROOT = Path(__file__).resolve().parents[3] / "roboclaws" / "operator_console" / "static"


def _assert_contains_all(body: str, snippets: tuple[str, ...]) -> None:
    missing = [snippet for snippet in snippets if snippet not in body]
    assert missing == []


def _assert_contains_none(body: str, snippets: tuple[str, ...]) -> None:
    present = [snippet for snippet in snippets if snippet in body]
    assert present == []


ROUTE_FIELD_HTML_REQUIRED = (
    'id="isaac-fields"',
    'id="codex-fields"',
    'id="codex-provider-input"',
    'value="minimax"',
    'value="mimo-openai-chat"',
    'value="kimi-openai-chat"',
    'id="claude-fields"',
    'id="claude-provider-input"',
    'value="kimi-anthropic"',
    'value="mimo-anthropic"',
    'value="mify-anthropic"',
    'id="agibot-fields"',
    'id="agibot-gate-fields"',
    'id="real-movement-gate"',
    "Latest Result",
    'id="camera-angle-value"',
    'class="setup-panel"',
    'class="state-rail"',
    'id="prompt-label"',
    'id="prompt-preview-panel"',
    'id="prompt-preview-text"',
    'id="agent-prompt-state"',
    "Agent Prompt",
    "Scenario seed for reproducible runs",
    "Baseline does not relocate objects",
    'id="scenario-setup-input"',
    'name="scenario_setup"',
    "Relocate loose objects",
    "Relocate cleanup-related objects",
    'id="relocation-count-field"',
    'id="relocation-count-input"',
    'name="relocation_count"',
    'id="messup-button"',
    'id="messup-status"',
    "Try Mess-up",
    'data-operator-mode="steer"',
    'data-operator-mode="goal"',
    'data-view="tasks"',
    'id="tasks-panel"',
    "Background Tasks",
    'id="background-task-list"',
    "No blocking background resources loaded.",
)

ROUTE_FIELD_HTML_FORBIDDEN = (
    'id="codex-model-input"',
    'id="isaac-preflight-gate"',
    "Isaac preflight accepted",
    "Isaac runtime preflight and smoke markers",
    "Generated mess count",
    'id="mess-count-input"',
    'data-operator-mode="continue"',
    'data-operator-mode="ask_why"',
    'id="operator-message-input"',
    'id="operator-message-button"',
    "Continue",
    "Ask Why",
    "/ask-why",
    'id="task-status-filter"',
    'id="task-owner-filter"',
    'id="task-search-input"',
)

ROUTE_FIELD_APP_REQUIRED = (
    "renderRouteFields",
    "field_groups",
    "real_movement_enabled",
    "Movement",
    "Provider",
    "env_overrides",
    "ROBOCLAWS_CODEX_PROVIDER",
    "ROBOCLAWS_CLAUDE_PROVIDER",
    "selectedCodexProvider",
    "selectedClaudeProvider",
    "Capability Gate",
    "NEEDS SAFETY GATES",
    "NEEDS CONTEXT",
    "PORT IN USE",
    "ATTACH",
    "Attach Existing Run",
    "latest-result-button",
    "cameraStateLabel",
    "renderToolPanel",
    "renderScenarioSetup",
    "defaultScenarioSetup",
    "selectedScenarioSetup",
    "previewMessup",
    "/api/messup-preview",
    "Baseline remains available",
    "Baseline means no pre-run relocation",
    "els.messupButton.hidden = !supported || !relocation;",
    "els.messupButton.disabled = !supported || !relocation || Boolean(state.activeRunId);",
    "return `${route.world_id}:${route.backend_id}:${selectedScenarioSetup()}`;",
    "markCurrentSetupSelection",
    "markCurrentMessupStatus",
    "resetMessupStatusForManualSetup",
    "/next-goal",
    "Start Next Goal",
    "Confirm Next Goal",
    "check_operator_messages",
    "attachLatestResult",
    "/api/runs/latest",
    "attachExistingRun",
    "attachable_run",
    "?selection_id=",
    "renderStartAction",
    "compactRunId",
    "compactDisplayRunId",
    "compactRunPart",
    "Run Attached",
    "Use Steer while this run is active.",
    "/api/readiness",
    "refreshSelectedRouteReadiness",
    "checkerStatus.message",
    "state.evidenceLanes",
    "payload.evidence_lanes",
    "evidenceLaneOptions",
    "intentOptionsForCurrentAxes",
    "node.disabled = Boolean(option.disabled)",
    "node.title = option.title",
    "orderedVisibleWorlds(payload.worlds || [])",
    "enabledLaunchCount > 0",
    "isMolmospacesWorld",
    "return leftMolmo ? 1 : -1",
    "payload.runtime",
    "/api/runtime/tasks",
    "/api/prompt-preview",
    "refreshPromptPreview",
    "renderAgentPromptState",
    "agent_kickoff_prompt",
    "wrapper_notes",
    "effectiveLaunchPromptText",
    "renderBackgroundTasks",
    "No blocking background resources detected.",
    "background_blockers",
    "TASK RUNNING",
    "data-open-background-tasks",
    "copy_command",
    "api_post",
)

ROUTE_FIELD_APP_FORBIDDEN = (
    "Diagnostic",
    "NEEDS PREFLIGHT",
    "NEEDS OPERATOR GATES",
    "generated_mess_count",
    "/continue",
    "/ask-why",
    "ask_why",
    "Ask Why",
    "latestAskWhyText",
    "latestOperatorResultText",
    "?route=",
)


def test_static_app_references_existing_dom_ids() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    declared_ids = set(re.findall(r'id="([^"]+)"', html))
    referenced_ids = set(re.findall(r'getElementById\("([^"`$]+)"\)', app))

    assert referenced_ids - declared_ids == set()


def test_static_app_has_route_specific_field_groups() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    _assert_contains_all(html, ROUTE_FIELD_HTML_REQUIRED)
    _assert_contains_none(html, ROUTE_FIELD_HTML_FORBIDDEN)
    _assert_contains_all(app, ROUTE_FIELD_APP_REQUIRED)
    _assert_contains_none(app, ROUTE_FIELD_APP_FORBIDDEN)

    setup_html = html.split('<aside class="setup-panel">', 1)[1].split("</aside>", 1)[0]
    state_rail_html = html.split('<aside class="state-rail">', 1)[1].split("</aside>", 1)[0]
    top_bar_html = html.split('<header class="top-run-bar">', 1)[1].split("</header>", 1)[0]
    workspace_tabs_html = html.split('<nav class="view-modes"', 1)[1].split("</nav>", 1)[0]
    assert "Operator Input" in setup_html
    assert "Operator Input" not in state_rail_html
    assert 'data-view="tasks"' in top_bar_html
    assert 'data-view="tasks"' not in workspace_tabs_html


def test_static_app_does_not_short_circuit_context_json_readiness() -> None:
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert 'gate.id === "context_json" && Boolean(els.contextInput.value.trim())' not in app


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

    expected_preview_files = sorted(
        {
            *(
                f"molmospaces-val_{scene_index}-{view_name}.png"
                for scene_index in MOLMOSPACES_LAUNCH_ALIAS_SCENE_INDICES
                for view_name in ("chase", "fpv", "map", "topdown")
            ),
            *(
                Path(path).name
                for world_id in MOLMOSPACES_CONSOLE_WORLD_IDS
                for _view_name, path in WORLD_SPECS[world_id].preview_assets
                if path.startswith("/previews/")
            ),
        }
    )
    molmospaces_preview_files = sorted(
        path.name
        for path in preview_dir.glob("molmospaces-*.png")
        if path.name.startswith(("molmospaces-val_", "molmospaces-procthor-objaverse-val-"))
    )
    assert molmospaces_preview_files == expected_preview_files
    metadata_files = sorted(
        path.name
        for path in preview_dir.glob("molmospaces-*-preview.json")
        if path.name.startswith(("molmospaces-val_", "molmospaces-procthor-objaverse-val-"))
    )
    expected_metadata_files = sorted(
        {
            *(
                f"molmospaces-val_{scene_index}-preview.json"
                for scene_index in MOLMOSPACES_LAUNCH_ALIAS_SCENE_INDICES
            ),
            *(
                f"{Path(WORLD_SPECS[world_id].preview_assets[0][1]).name.rsplit('-', 1)[0]}"
                "-preview.json"
                for world_id in MOLMOSPACES_CONSOLE_WORLD_IDS
            ),
        }
    )
    assert metadata_files == expected_metadata_files
    assert not any(name.startswith("molmospaces-val_6-") for name in molmospaces_preview_files)
    assert not any(name.startswith("molmospaces-val_8-") for name in molmospaces_preview_files)
    b1_preview_files = sorted(path.name for path in preview_dir.glob("b1-map12-*.png"))
    assert b1_preview_files == [
        "b1-map12-chase.png",
        "b1-map12-fpv.png",
        "b1-map12-map.png",
        "b1-map12-topdown.png",
    ]

    for world_id in MOLMOSPACES_CONSOLE_WORLD_IDS:
        preview_by_view = dict(WORLD_SPECS[world_id].preview_assets)
        for view_name in ("fpv", "map", "chase", "topdown"):
            path = preview_dir / Path(preview_by_view[view_name]).name
            assert path.is_file()
            assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
        scene_slug = Path(preview_by_view["fpv"]).name.rsplit("-", 1)[0]
        metadata_path = preview_dir / f"{scene_slug}-preview.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert metadata["world_id"] == world_id
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
    for view_name in ("fpv", "map", "chase", "topdown"):
        path = preview_dir / f"b1-map12-{view_name}.png"
        assert path.is_file()
        assert path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    b1_metadata = json.loads((preview_dir / "b1-map12-preview.json").read_text(encoding="utf-8"))
    assert b1_metadata["world_id"] == "b1-map12"
    assert b1_metadata["backend"] == "isaaclab"
    assert b1_metadata["views"]["fpv"]["provenance"] == (
        "isaac_runtime_robot_mounted_head_camera_fpv"
    )
    assert b1_metadata["views"]["chase"]["provenance"] == "isaac_runtime_report_chase_camera"
    assert b1_metadata["views"]["topdown"]["view"] == "semantic_room_topdown"
    assert b1_metadata["views"]["map"]["path"] != b1_metadata["views"]["topdown"]["path"]
    assert b1_metadata["views"]["fpv"]["path"] != b1_metadata["views"]["map"]["path"]
    assert b1_metadata["views"]["chase"]["path"] != b1_metadata["views"]["fpv"]["path"]
    assert b1_metadata["camera_preview_artifact"]["path"]
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
    assert "prompt-preview-20260616" in html
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
    responsive_controls = (
        css.split("@media (max-width: 1360px)", 1)[1]
        .split(
            ".global-controls {",
            1,
        )[1]
        .split("\n  }", 1)[0]
    )

    assert 'href="/styles.css?v=prompt-preview-20260616"' in html
    assert 'src="/app.js?v=prompt-preview-20260616"' in html
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
        "return `${fullTimestamp[2]}${fullTimestamp[3]}-${fullTimestamp[4]}${fullTimestamp[5]}`"
    ) in app
    assert (
        "return `${shortTimestamp[1]}${shortTimestamp[2]}_${shortTimestamp[3]}${shortTimestamp[4]}`"
    ) in app
    assert '"$2$3-$4$5$7"' not in app


def test_static_app_hides_pause_until_a_route_supports_it() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")

    assert 'id="pause-button" class="secondary" disabled hidden' in html
    assert "const pauseAvailable = Boolean(controls.pause_available)" in app
    assert "els.pauseButton.hidden = !pauseAvailable" in app
    assert "els.pauseButton.disabled = !pauseAvailable" in app


def test_static_app_wires_manual_relative_navigation_controls() -> None:
    html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    app = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    css = (STATIC_ROOT / "styles.css").read_text(encoding="utf-8")

    assert 'id="manual-control-panel"' in html
    assert 'id="manual-control-status"' in html
    for action in ("forward", "back", "left", "right", "turn-left", "turn-right", "observe"):
        assert f'data-control-action="{action}"' in html
    assert "MANUAL_CONTROL_STEP_M = 0.25" in app
    assert "MANUAL_CONTROL_TURN_DEG = 15" in app
    assert 'action: "navigate_to_relative_pose"' in app
    assert 'return { action: "observe" }' in app
    assert "/control" in app
    assert "supports_relative_navigation_control" in app
    assert "relative_navigation_control_available" in app
    assert "operator moves are recorded as assisted interventions".lower() in app.lower()
    assert ".manual-control-panel" in css
    assert ".manual-control-grid" in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr));" in css


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
