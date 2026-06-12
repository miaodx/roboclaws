const state = {
  worlds: [],
  routes: [],
  combinations: [],
  evidenceLanes: [],
  readiness: {},
  selectedWorld: null,
  selectedRoute: null,
  activeRunId: null,
  activeRouteId: "",
  activeState: null,
  operatorMode: "goal",
  pollTimer: null,
  readinessTimer: null,
  activeView: "overview",
  selectedIntent: "",
  setupSelectionKey: "",
  messupStatusKey: "",
  syncAxesFromRoute: false,
};

const STATE_RAIL_WIDTH_KEY = "roboclaws.operatorConsole.stateRailWidth";
const STATE_RAIL_DEFAULT_WIDTH = 300;
const STATE_RAIL_MIN_WIDTH = 260;
const STATE_RAIL_MAX_WIDTH = 760;
const WORKSPACE_MIN_WIDTH = 420;
const EVIDENCE_STRIP_HEIGHT_KEY = "roboclaws.operatorConsole.evidenceStripHeight";
const EVIDENCE_STRIP_DEFAULT_HEIGHT = 280;
const EVIDENCE_STRIP_MIN_HEIGHT = 160;
const EVIDENCE_STRIP_MAX_HEIGHT = 620;
const MAIN_CONTENT_MIN_HEIGHT = 360;

const els = {
  appShell: document.querySelector(".app-shell"),
  routeList: document.getElementById("route-list"),
  backendInput: document.getElementById("backend-input"),
  agentEngineInput: document.getElementById("agent-engine-input"),
  evidenceLaneInput: document.getElementById("evidence-lane-input"),
  providerProfileFields: document.getElementById("provider-profile-fields"),
  providerProfileInput: document.getElementById("provider-profile-input"),
  providerProfileHelp: document.getElementById("provider-profile-help"),
  taskPrompt: document.getElementById("prompt-input"),
  promptLabel: document.getElementById("prompt-label"),
  promptHelp: document.getElementById("prompt-copy"),
  promptCount: document.getElementById("char-count"),
  intentFields: document.getElementById("intent-fields"),
  intentInput: document.getElementById("intent-input"),
  intentPreview: document.getElementById("intent-preview"),
  seedInput: document.getElementById("seed-input"),
  scenarioSetupInput: document.getElementById("scenario-setup-input"),
  relocationCountField: document.getElementById("relocation-count-field"),
  relocationCountInput: document.getElementById("relocation-count-input"),
  messupButton: document.getElementById("messup-button"),
  messupStatus: document.getElementById("messup-status"),
  portInput: document.getElementById("port-input"),
  selectedRouteSummary: document.getElementById("selected-route-summary"),
  commonFields: document.getElementById("common-fields"),
  codexFields: document.getElementById("codex-fields"),
  claudeFields: document.getElementById("claude-fields"),
  isaacFields: document.getElementById("isaac-fields"),
  agibotFields: document.getElementById("agibot-fields"),
  agibotGateFields: document.getElementById("agibot-gate-fields"),
  codexProviderInput: document.getElementById("codex-provider-input"),
  claudeProviderInput: document.getElementById("claude-provider-input"),
  contextInput: document.getElementById("context-json-input"),
  isaacSceneInput: document.getElementById("isaac-scene-input"),
  localizationGate: document.getElementById("localization-gate"),
  enablementGate: document.getElementById("enablement-gate"),
  estopGate: document.getElementById("estop-gate"),
  realMovementGate: document.getElementById("real-movement-gate"),
  gateList: document.getElementById("gate-list"),
  commandPreview: document.getElementById("command-preview"),
  startButton: document.getElementById("start-button"),
  startHelp: document.getElementById("start-error"),
  runTitle: document.getElementById("run-title"),
  routeStatus: document.getElementById("route-status"),
  lockStatus: document.getElementById("lock-status"),
  elapsedStatus: document.getElementById("elapsed-status"),
  latestResultButton: document.getElementById("latest-result-button"),
  pauseButton: document.getElementById("pause-button"),
  stopButton: document.getElementById("stop-button"),
  emergencyButton: document.getElementById("emergency-button"),
  phaseValue: document.getElementById("phase-value"),
  backendLockValue: document.getElementById("backend-lock-value"),
  cameraAngleValue: document.getElementById("camera-angle-value"),
  terminalValue: document.getElementById("terminal-value"),
  decisionPanel: document.getElementById("decision-state"),
  toolPanel: document.getElementById("tool-state"),
  proofPanel: document.getElementById("proof-state"),
  artifactList: document.getElementById("artifact-list"),
  eventList: document.getElementById("event-log"),
  rawEvidence: document.getElementById("raw-evidence"),
  toggleRawButton: document.getElementById("toggle-raw-button"),
  stateRailResizer: document.getElementById("state-rail-resizer"),
  evidenceStripResizer: document.getElementById("evidence-strip-resizer"),
  confirmDialog: document.getElementById("confirm-dialog"),
  confirmTitle: document.getElementById("confirm-title"),
  confirmAction: document.getElementById("confirm-action"),
  confirmBody: document.getElementById("confirm-body"),
  imageDialog: document.getElementById("image-dialog"),
  imageDialogTitle: document.getElementById("image-dialog-title"),
  imageDialogPath: document.getElementById("image-dialog-path"),
  imageDialogImg: document.getElementById("image-dialog-img"),
};

async function boot() {
  const payload = await fetchJson("/api/routes");
  state.evidenceLanes = payload.evidence_lanes || [];
  state.combinations = payload.combinations || payload.routes || [];
  state.routes = state.combinations;
  state.worlds = orderedVisibleWorlds(payload.worlds || []);
  state.readiness = payload.readiness || {};
  state.selectedWorld = state.worlds[0] || null;
  state.selectedRoute =
    combinationsForWorld(state.selectedWorld && state.selectedWorld.id).find((route) => route.enabled) ||
    state.combinations.find((route) => route.enabled) ||
    state.combinations[0];
  if (state.selectedRoute) {
    state.selectedWorld =
      state.worlds.find((world) => world.id === state.selectedRoute.world_id) || state.selectedWorld;
    state.selectedIntent = state.selectedRoute.intent_id || "";
    state.syncAxesFromRoute = true;
  }
  renderRoutes();
  renderSelection();
  bindEvents();
  renderViewModes();
}

function orderedVisibleWorlds(worlds) {
  return worlds
    .map((world, index) => ({
      world,
      index,
      enabledLaunchCount: combinationsForWorld(world.id).filter((item) => item.enabled).length,
    }))
    .filter((item) => item.enabledLaunchCount > 0)
    .sort((left, right) => {
      const leftMolmo = isMolmospacesWorld(left.world);
      const rightMolmo = isMolmospacesWorld(right.world);
      if (leftMolmo !== rightMolmo) {
        return leftMolmo ? 1 : -1;
      }
      return left.index - right.index;
    })
    .map((item) => item.world);
}

function isMolmospacesWorld(world) {
  return world.id.startsWith("molmospaces/") || (world.tags || []).includes("molmospaces");
}

function bindEvents() {
  els.taskPrompt.addEventListener("input", () => {
    els.promptCount.textContent = `${els.taskPrompt.value.length} / 2000`;
    renderSelection();
  });
  els.intentInput.addEventListener("change", () => {
    state.selectedIntent = els.intentInput.value;
    renderSelection();
  });
  [
    els.contextInput,
    els.codexProviderInput,
    els.claudeProviderInput,
    els.portInput,
    els.backendInput,
    els.agentEngineInput,
    els.evidenceLaneInput,
    els.providerProfileInput,
    els.localizationGate,
    els.enablementGate,
    els.estopGate,
    els.realMovementGate,
  ].forEach((input) => {
    input.addEventListener("input", renderSelection);
    input.addEventListener("input", renderRoutes);
    input.addEventListener("input", scheduleReadinessRefresh);
    input.addEventListener("change", renderSelection);
    input.addEventListener("change", renderRoutes);
    input.addEventListener("change", refreshSelectedRouteReadiness);
  });
  [els.scenarioSetupInput, els.relocationCountInput].forEach((input) => {
    input.addEventListener("input", () => {
      resetMessupStatusForManualSetup();
      renderSelection();
      renderRoutes();
      scheduleReadinessRefresh();
    });
    input.addEventListener("change", () => {
      resetMessupStatusForManualSetup();
      renderSelection();
      renderRoutes();
      refreshSelectedRouteReadiness();
    });
  });
  els.startButton.addEventListener("click", handleStartAction);
  els.messupButton.addEventListener("click", previewMessup);
  els.latestResultButton.addEventListener("click", attachLatestResult);
  els.pauseButton.addEventListener("click", () => postRunAction("pause"));
  els.stopButton.addEventListener("click", () => {
    confirmAction({
      title: "Stop Run",
      cta: "Stop Run",
      body:
        "Stop this run? The console will terminate the active process and preserve the current artifacts.",
      onConfirm: () => postRunAction("stop"),
    });
  });
  els.emergencyButton.addEventListener("click", () => {
    confirmAction({
      title: "Emergency Stop",
      cta: "Trigger Emergency Stop",
      body:
        "Trigger the real-robot emergency stop path now. This ends the run and requires human takeover before another run.",
      onConfirm: () => postRunAction("emergency-stop"),
    });
  });
  document.querySelectorAll(".operator-mode").forEach((button) => {
    button.addEventListener("click", () => {
      state.operatorMode = button.dataset.operatorMode || "ask_why";
      renderSelection();
    });
  });
  els.toggleRawButton.addEventListener("click", toggleRawEvidence);
  bindStateRailResize();
  bindEvidenceStripResize();
  document.querySelectorAll(".view-mode").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeView = button.dataset.view;
      renderViewModes();
    });
  });
}

function bindEvidenceStripResize() {
  if (!els.appShell || !els.evidenceStripResizer) {
    return;
  }
  const savedHeight = readSavedEvidenceStripHeight();
  if (savedHeight) {
    setEvidenceStripHeight(savedHeight, { persist: false });
  }
  els.evidenceStripResizer.addEventListener("pointerdown", startEvidenceStripResize);
  els.evidenceStripResizer.addEventListener("keydown", handleEvidenceStripResizeKey);
  window.addEventListener("resize", () => {
    setEvidenceStripHeight(currentEvidenceStripHeight(), { persist: false });
  });
}

function startEvidenceStripResize(event) {
  if (window.matchMedia("(max-width: 1360px)").matches) {
    return;
  }
  event.preventDefault();
  const startY = event.clientY;
  const startHeight = currentEvidenceStripHeight();
  const pointerId = event.pointerId;
  els.evidenceStripResizer.setPointerCapture(pointerId);
  document.body.classList.add("resizing-evidence-strip");

  const onPointerMove = (moveEvent) => {
    setEvidenceStripHeight(startHeight + startY - moveEvent.clientY, { persist: false });
  };
  const stopResize = () => {
    document.body.classList.remove("resizing-evidence-strip");
    persistEvidenceStripHeight(currentEvidenceStripHeight());
    els.evidenceStripResizer.removeEventListener("pointermove", onPointerMove);
    try {
      els.evidenceStripResizer.releasePointerCapture(pointerId);
    } catch {
      // Pointer capture may already be released after a cancelled drag.
    }
  };

  els.evidenceStripResizer.addEventListener("pointermove", onPointerMove);
  els.evidenceStripResizer.addEventListener("pointerup", stopResize, { once: true });
  els.evidenceStripResizer.addEventListener("pointercancel", stopResize, { once: true });
}

function handleEvidenceStripResizeKey(event) {
  if (!["ArrowUp", "ArrowDown", "Home", "End"].includes(event.key)) {
    return;
  }
  event.preventDefault();
  const step = event.shiftKey ? 80 : 24;
  const bounds = evidenceStripHeightBounds();
  if (event.key === "Home") {
    setEvidenceStripHeight(bounds.min);
  } else if (event.key === "End") {
    setEvidenceStripHeight(bounds.max);
  } else {
    const direction = event.key === "ArrowUp" ? 1 : -1;
    setEvidenceStripHeight(currentEvidenceStripHeight() + direction * step);
  }
}

function setEvidenceStripHeight(height, options = {}) {
  const persist = options.persist !== false;
  const bounds = evidenceStripHeightBounds();
  const nextHeight = Math.round(Math.min(bounds.max, Math.max(bounds.min, Number(height))));
  document.documentElement.style.setProperty("--evidence-strip-height", `${nextHeight}px`);
  els.evidenceStripResizer.setAttribute("aria-valuemin", String(bounds.min));
  els.evidenceStripResizer.setAttribute("aria-valuemax", String(bounds.max));
  els.evidenceStripResizer.setAttribute("aria-valuenow", String(nextHeight));
  if (persist) {
    persistEvidenceStripHeight(nextHeight);
  }
}

function currentEvidenceStripHeight() {
  const rawValue = getComputedStyle(document.documentElement)
    .getPropertyValue("--evidence-strip-height")
    .trim();
  const parsed = Number.parseFloat(rawValue);
  return Number.isFinite(parsed) ? parsed : EVIDENCE_STRIP_DEFAULT_HEIGHT;
}

function evidenceStripHeightBounds() {
  const shellHeight = els.appShell.getBoundingClientRect().height || window.innerHeight;
  const availableHeight = shellHeight - 56 - MAIN_CONTENT_MIN_HEIGHT;
  const max = Math.max(
    EVIDENCE_STRIP_MIN_HEIGHT,
    Math.min(EVIDENCE_STRIP_MAX_HEIGHT, Math.floor(availableHeight))
  );
  return { min: EVIDENCE_STRIP_MIN_HEIGHT, max };
}

function readSavedEvidenceStripHeight() {
  try {
    const height = Number.parseFloat(localStorage.getItem(EVIDENCE_STRIP_HEIGHT_KEY) || "");
    return Number.isFinite(height) ? height : 0;
  } catch {
    return 0;
  }
}

function persistEvidenceStripHeight(height) {
  try {
    localStorage.setItem(EVIDENCE_STRIP_HEIGHT_KEY, String(Math.round(height)));
  } catch {
    // Local storage can be disabled; resizing should still work for this page load.
  }
}

function bindStateRailResize() {
  if (!els.appShell || !els.stateRailResizer) {
    return;
  }
  const savedWidth = readSavedStateRailWidth();
  if (savedWidth) {
    setStateRailWidth(savedWidth, { persist: false });
  }
  els.stateRailResizer.addEventListener("pointerdown", startStateRailResize);
  els.stateRailResizer.addEventListener("keydown", handleStateRailResizeKey);
  window.addEventListener("resize", () => {
    setStateRailWidth(currentStateRailWidth(), { persist: false });
  });
}

function startStateRailResize(event) {
  if (window.matchMedia("(max-width: 1360px)").matches) {
    return;
  }
  event.preventDefault();
  const startX = event.clientX;
  const startWidth = currentStateRailWidth();
  const pointerId = event.pointerId;
  els.stateRailResizer.setPointerCapture(pointerId);
  document.body.classList.add("resizing-state-rail");

  const onPointerMove = (moveEvent) => {
    setStateRailWidth(startWidth + startX - moveEvent.clientX, { persist: false });
  };
  const stopResize = () => {
    document.body.classList.remove("resizing-state-rail");
    persistStateRailWidth(currentStateRailWidth());
    els.stateRailResizer.removeEventListener("pointermove", onPointerMove);
    try {
      els.stateRailResizer.releasePointerCapture(pointerId);
    } catch {
      // Pointer capture may already be released after a cancelled drag.
    }
  };

  els.stateRailResizer.addEventListener("pointermove", onPointerMove);
  els.stateRailResizer.addEventListener("pointerup", stopResize, { once: true });
  els.stateRailResizer.addEventListener("pointercancel", stopResize, { once: true });
}

function handleStateRailResizeKey(event) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
    return;
  }
  event.preventDefault();
  const step = event.shiftKey ? 80 : 24;
  const bounds = stateRailWidthBounds();
  if (event.key === "Home") {
    setStateRailWidth(bounds.min);
  } else if (event.key === "End") {
    setStateRailWidth(bounds.max);
  } else {
    const direction = event.key === "ArrowLeft" ? 1 : -1;
    setStateRailWidth(currentStateRailWidth() + direction * step);
  }
}

function setStateRailWidth(width, options = {}) {
  const persist = options.persist !== false;
  const bounds = stateRailWidthBounds();
  const nextWidth = Math.round(Math.min(bounds.max, Math.max(bounds.min, Number(width))));
  document.documentElement.style.setProperty("--state-rail-width", `${nextWidth}px`);
  els.stateRailResizer.setAttribute("aria-valuemin", String(bounds.min));
  els.stateRailResizer.setAttribute("aria-valuemax", String(bounds.max));
  els.stateRailResizer.setAttribute("aria-valuenow", String(nextWidth));
  if (persist) {
    persistStateRailWidth(nextWidth);
  }
}

function currentStateRailWidth() {
  const rawValue = getComputedStyle(document.documentElement)
    .getPropertyValue("--state-rail-width")
    .trim();
  const parsed = Number.parseFloat(rawValue);
  return Number.isFinite(parsed) ? parsed : STATE_RAIL_DEFAULT_WIDTH;
}

function stateRailWidthBounds() {
  const shellWidth = els.appShell.getBoundingClientRect().width || window.innerWidth;
  const availableWidth = shellWidth - 240 - 300 - WORKSPACE_MIN_WIDTH;
  const max = Math.max(
    STATE_RAIL_MIN_WIDTH,
    Math.min(STATE_RAIL_MAX_WIDTH, Math.floor(availableWidth))
  );
  return { min: STATE_RAIL_MIN_WIDTH, max };
}

function readSavedStateRailWidth() {
  try {
    const width = Number.parseFloat(localStorage.getItem(STATE_RAIL_WIDTH_KEY) || "");
    return Number.isFinite(width) ? width : 0;
  } catch {
    return 0;
  }
}

function persistStateRailWidth(width) {
  try {
    localStorage.setItem(STATE_RAIL_WIDTH_KEY, String(Math.round(width)));
  } catch {
    // Local storage can be disabled; resizing should still work for this page load.
  }
}

function renderRoutes() {
  els.routeList.innerHTML = "";
  for (const world of state.worlds) {
    const worldCombinations = combinationsForWorld(world.id);
    const enabledCount = worldCombinations.filter((item) => item.enabled).length;
    const button = document.createElement("button");
    const selectable = enabledCount > 0;
    const active = state.selectedWorld && world.id === state.selectedWorld.id;
    const display = selectable
      ? { label: world.availability === "experimental" ? "EXPERIMENTAL" : "READY", className: world.availability === "experimental" ? "warning" : "ready" }
      : { label: "UNAVAILABLE", className: "blocked" };
    button.type = "button";
    button.className = `route-card${active ? " active" : ""}`;
    button.dataset.worldId = world.id;
    button.disabled = !selectable;
    button.innerHTML = `
      <div class="route-card-title">
        <span>${escapeHtml(world.label)}</span>
        <span class="badge ${display.className}">${display.label}</span>
      </div>
      <div class="meta-label">${escapeHtml((world.tags || []).join(" / "))}</div>
      <div>${escapeHtml((world.available_backends || []).join(", "))}</div>
      <div class="field-help">${enabledCount} launch option${enabledCount === 1 ? "" : "s"}</div>
    `;
    button.addEventListener("click", () => {
      state.selectedWorld = world;
      state.selectedRoute =
        combinationsForWorld(world.id).find((item) => item.enabled) ||
        combinationsForWorld(world.id)[0];
      state.selectedIntent = state.selectedRoute ? state.selectedRoute.intent_id : "";
      state.syncAxesFromRoute = true;
      renderRoutes();
      renderSelection();
      refreshSelectedRouteReadiness();
    });
    els.routeList.appendChild(button);
  }
}

function combinationsForWorld(worldId) {
  return state.combinations.filter((item) => item.world_id === worldId);
}

function selectedCombinationFromAxes() {
  const worldId = state.selectedWorld && state.selectedWorld.id;
  const backendId = els.backendInput.value;
  const intentId = els.intentInput.value || state.selectedIntent;
  const agentEngineId = els.agentEngineInput.value;
  const evidenceLane = els.evidenceLaneInput.value || "world-oracle-labels";
  const axisCandidates = combinationsForWorld(worldId).filter(
    (item) =>
      item.backend_id === backendId &&
      item.intent_id === intentId &&
      item.agent_engine_id === agentEngineId
  );
  const candidates = axisCandidates.filter(
    (item) =>
      item.evidence_lane === evidenceLane
  );
  const providerProfile = els.providerProfileInput.value;
  return (
    candidates.find(
      (item) => item.enabled && (!item.provider_profile || item.provider_profile === providerProfile)
    ) ||
    candidates.find((item) => item.enabled) ||
    axisCandidates.find(
      (item) => item.enabled && (!item.provider_profile || item.provider_profile === providerProfile)
    ) ||
    axisCandidates.find((item) => item.enabled) ||
    candidates[0] ||
    axisCandidates[0] ||
    state.selectedRoute
  );
}

function renderSelection() {
  renderAxisSelectors();
  const route = selectedCombinationFromAxes();
  state.selectedRoute = route;
  if (!route) {
    return;
  }
  const readiness = effectiveReadiness(route);
  renderRouteFields(route);
  renderSelectedRouteSummary(route, readiness);
  ensureActiveViewAvailable(route);
  renderViewModes(route);
  renderIntentSelector(route);
  renderScenarioSetup(route);
  renderOperatorInput(route);
  renderSelectedScenePreview(route);

  const gates = readiness.gates || route.gates || [];
  els.gateList.innerHTML = "";
  for (const gate of gates) {
    const gateReady = gate.status === "ready";
    const display = gateBadgeDisplay(gate);
    const row = document.createElement("div");
    row.className = "gate-row";
    row.innerHTML = `
      <span>${escapeHtml(gate.label)}</span>
      <span class="badge ${display.className}">${display.label}</span>
      ${
        gate.message && (!gateReady || gate.evidence)
          ? `<span class="field-help">${escapeHtml(gate.message)}</span>`
          : ""
      }
      ${gate.evidence ? `<span class="field-help">${escapeHtml(gate.evidence)}</span>` : ""}
    `;
    els.gateList.appendChild(row);
  }
  if (!gates.length) {
    els.gateList.textContent = "No route-specific gates.";
  }

  els.commandPreview.textContent = commandPreview(route);
  renderStartAction(route, readiness);
}

function renderAxisSelectors() {
  const worldId = state.selectedWorld && state.selectedWorld.id;
  const combos = combinationsForWorld(worldId);
  const syncFromRoute = state.syncAxesFromRoute;
  const route = state.selectedRoute;
  const backendOptions = uniqueOptions(combos, "backend_id", "backend_label");
  renderSelectOptions(
    els.backendInput,
    backendOptions,
    syncFromRoute && route
      ? route.backend_id
      : currentSelectValue(els.backendInput, backendOptions, route && route.backend_id)
  );
  const agentOptions = uniqueOptions(combos, "agent_engine_id", "agent_engine_label");
  renderSelectOptions(
    els.agentEngineInput,
    agentOptions,
    syncFromRoute && route
      ? route.agent_engine_id
      : currentSelectValue(els.agentEngineInput, agentOptions, route && route.agent_engine_id)
  );
  const intentOptions = intentOptionsForCurrentAxes(combos);
  renderSelectOptions(
    els.intentInput,
    intentOptions,
    syncFromRoute && route
      ? route.intent_id
      : currentSelectValue(
          els.intentInput,
          intentOptions,
          state.selectedIntent || (route && route.intent_id)
        )
  );
  const laneOptions = evidenceLaneOptions(combos);
  renderSelectOptions(
    els.evidenceLaneInput,
    laneOptions,
    syncFromRoute && route
      ? route.evidence_lane
      : currentSelectValue(els.evidenceLaneInput, laneOptions, route && route.evidence_lane)
  );
  state.syncAxesFromRoute = false;
  const selected = selectedCombinationFromAxes();
  renderProviderProfileOptions(selected);
}

function currentSelectValue(select, options, fallbackValue = "") {
  const current = select.value || "";
  if (current && options.some((option) => option.value === current)) {
    return current;
  }
  if (fallbackValue && options.some((option) => option.value === fallbackValue)) {
    return fallbackValue;
  }
  return current || fallbackValue || "";
}

function uniqueOptions(items, valueKey, labelKey, labelFn) {
  const seen = new Map();
  for (const item of items) {
    const value = item[valueKey] || "";
    if (!value || seen.has(value)) {
      continue;
    }
    const rawLabel = item[labelKey] || value;
    seen.set(value, {
      value,
      label: labelFn ? labelFn(rawLabel) : rawLabel,
      disabled: false,
    });
  }
  return [...seen.values()];
}

function intentOptionsForCurrentAxes(combos) {
  const backendId = els.backendInput.value;
  const agentEngineId = els.agentEngineInput.value;
  const axisMatches = combos.filter(
    (item) => item.backend_id === backendId && item.agent_engine_id === agentEngineId
  );
  const scopedCombos = axisMatches.length ? axisMatches : combos;
  const intentValues = [
    ...new Set(scopedCombos.map((item) => item.intent_id).filter(Boolean)),
  ];
  return intentValues.map((value) => {
    const matching = scopedCombos.filter(
      (item) =>
        item.backend_id === backendId &&
        item.agent_engine_id === agentEngineId &&
        item.intent_id === value
    );
    const enabledMatch = matching.find((item) => item.enabled);
    const disabledMatch = matching.find((item) => !item.enabled);
    const reason = disabledMatch
      ? disabledMatch.unsupported_reason || disabledMatch.disabled_reason || "Unavailable for this route."
      : "Unavailable for this route.";
    return {
      value,
      label: intentLabel(value),
      disabled: !enabledMatch,
      title: enabledMatch ? "" : reason,
    };
  });
}

function evidenceLaneOptions(combos) {
  const backendId = els.backendInput.value;
  const intentId = els.intentInput.value || state.selectedIntent;
  const agentEngineId = els.agentEngineInput.value;
  const laneRows = state.evidenceLanes.length
    ? state.evidenceLanes
    : uniqueOptions(combos, "evidence_lane", "evidence_lane");
  return laneRows.map((lane) => {
    const value = lane.id || lane.value;
    const matching = combos.filter(
      (item) =>
        item.backend_id === backendId &&
        item.intent_id === intentId &&
        item.agent_engine_id === agentEngineId &&
        item.evidence_lane === value
    );
    const enabledMatch = matching.find((item) => item.enabled);
    const disabledMatch = matching.find((item) => !item.enabled);
    const reason = disabledMatch
      ? disabledMatch.unsupported_reason || disabledMatch.disabled_reason || "Unavailable for this route."
      : "Unavailable for this route.";
    return {
      value,
      label: lane.label || value,
      disabled: !enabledMatch,
      title: enabledMatch ? "" : reason,
    };
  });
}

function renderSelectOptions(select, options, selectedValue) {
  const previous = selectedValue || select.value || "";
  const fallback = options.find((option) => !option.disabled) || options[0];
  select.innerHTML = "";
  for (const option of options) {
    const node = document.createElement("option");
    node.value = option.value;
    node.textContent = option.label;
    node.disabled = Boolean(option.disabled);
    if (option.title) {
      node.title = option.title;
    }
    node.selected = option.value === previous;
    select.appendChild(node);
  }
  if ((!select.value || (select.selectedOptions[0] && select.selectedOptions[0].disabled)) && fallback) {
    select.value = fallback.value;
  }
}

function renderProviderProfileOptions(route) {
  if (!route || !route.provider_profile) {
    els.providerProfileFields.hidden = true;
    els.providerProfileInput.innerHTML = "";
    return;
  }
  els.providerProfileFields.hidden = false;
  const profiles = [...new Set(
    combinationsForWorld(route.world_id)
      .filter((item) => item.agent_engine_id === route.agent_engine_id)
      .map((item) => item.provider_profile)
      .filter(Boolean)
  )];
  renderSelectOptions(
    els.providerProfileInput,
    profiles.map((profile) => ({ value: profile, label: profile })),
    route.provider_profile
  );
}

function renderOperatorInput(route) {
  const mode = state.operatorMode;
  const hasRun = Boolean(state.activeRunId);
  if (mode === "goal") {
    els.promptLabel.textContent = hasRun ? "Next Goal" : "Goal";
    els.taskPrompt.disabled = !route.supports_prompt || (hasRun && !isRunTerminal());
    els.taskPrompt.placeholder = route.task_prompt_default || route.default_prompt || "";
    els.promptHelp.textContent = operatorGoalHelp(route);
    return;
  }
  if (mode === "steer") {
    els.promptLabel.textContent = "Steer Current Run";
    els.taskPrompt.disabled = false;
    els.taskPrompt.placeholder = "Tell the active agent what to prioritize, avoid, or check next.";
    els.promptHelp.textContent = "Steer writes an auditable active-run message for supported routes.";
    return;
  }
  els.promptLabel.textContent = "Ask Why";
  els.taskPrompt.disabled = false;
  els.taskPrompt.placeholder = "Ask about public evidence, actions, or terminal status for the attached run.";
  els.promptHelp.textContent = "Ask Why reads public run artifacts only and cannot change robot state.";
}

function operatorGoalHelp(route) {
  if (!state.activeRunId) {
    return route.supports_prompt
      ? "Empty goal uses the route default. Prompt text is never interpreted as shell."
      : route.prompt_disabled_reason ||
          "This route cannot accept a custom prompt safely. Use the default task prompt.";
  }
  if (isRunTerminal()) {
    return "Starts a linked Next Goal run using public parent context.";
  }
  return "Goal starts a run or terminal-parent Next Goal. Use Steer or Ask Why while this run is active.";
}

function routeStatusDisplay(route, readiness) {
  if (!route.enabled) {
    return { label: "UNAVAILABLE", className: "blocked" };
  }
  if (readiness.can_start !== false) {
    return { label: "READY", className: "ready" };
  }
  const kind = readiness.blocker_kind || "";
  if (kind === "locked" && readiness.attachable_run) {
    return { label: "ATTACH", className: "running" };
  }
  if (kind === "locked") return { label: "LOCKED", className: "blocked" };
  if (kind === "mcp_port_in_use") return { label: "PORT IN USE", className: "blocked" };
  if (kind === "needs_provider") return { label: "NEEDS PROVIDER", className: "needs_action" };
  if (kind === "needs_real_movement_gate") {
    return { label: "NEEDS SAFETY GATES", className: "needs_action" };
  }
  if (kind === "needs_agibot_context") {
    return { label: "NEEDS CONTEXT", className: "needs_action" };
  }
  return { label: "NEEDS ACTION", className: "needs_action" };
}

function gateBadgeDisplay(gate) {
  if (gate.status === "ready") {
    return { label: "Ready", className: "ready" };
  }
  if (gateBlocksStart(gate)) {
    return { label: "Required", className: "needs_action" };
  }
  if (gate.severity === "capability") {
    return { label: "Capability Gate", className: "warning" };
  }
  if (gate.severity === "advisory") {
    return { label: "Diagnostic", className: "warning" };
  }
  return { label: "Needs Action", className: "needs_action" };
}

function renderSelectedRouteSummary(route, readiness) {
  const status = routeStatusDisplay(route, readiness);
  const interpretation = launchInterpretation(route);
  els.selectedRouteSummary.innerHTML = `
    <div class="route-card-title">
      <span>${escapeHtml(route.label)}</span>
      <span class="badge ${status.className}">${status.label}</span>
    </div>
    <div class="meta-label">${escapeHtml(route.agent_engine_label || route.agent_engine_id)} / ${escapeHtml(route.evidence_lane)}</div>
    <div class="field-help">${escapeHtml(route.world_label || route.world_id)} / ${escapeHtml(route.backend_label || route.backend_id)}</div>
    <div class="field-help">${escapeHtml(interpretation.intentLabel)} / ${escapeHtml(
      interpretation.goalScope
    )}</div>
  `;
}

function renderRouteFields(route) {
  const fieldGroups = new Set(route.field_groups || ["common"]);

  els.commonFields.hidden = !route.enabled || !fieldGroups.has("common");
  els.codexFields.hidden = true;
  els.claudeFields.hidden = true;
  els.isaacFields.hidden = !fieldGroups.has("isaac");
  els.agibotFields.hidden = !fieldGroups.has("agibot");
  els.agibotGateFields.hidden = !fieldGroups.has("agibot_gates");
}

function renderScenarioSetup(route) {
  const defaults = routeDefaultOverrides(route);
  const intent = selectedIntentForRoute(route);
  const selectionKey = `${route.id}:${intent}`;
  const defaultSetup = defaultScenarioSetup(route, intent, defaults);
  if (state.setupSelectionKey !== selectionKey) {
    els.scenarioSetupInput.value = defaultSetup;
    els.relocationCountInput.value = defaults.relocation_count || "5";
    state.setupSelectionKey = selectionKey;
  }
  if (!els.relocationCountInput.value && defaults.relocation_count) {
    els.relocationCountInput.value = defaults.relocation_count;
  }
  const relocation = selectedScenarioSetup() !== "baseline";
  els.relocationCountField.hidden = !relocation;
  els.relocationCountInput.disabled = !relocation;
  renderMessupAction(route);
}

function defaultScenarioSetup(route, intent, defaults) {
  if (intent === "cleanup") {
    return route.scenario_setup || defaults.scenario_setup || "relocate-cleanup-related-objects";
  }
  return "baseline";
}

function renderMessupAction(route) {
  const supported = Boolean(
    route &&
      route.world_id &&
      route.world_id.startsWith("molmospaces/") &&
      route.backend_id === "mujoco"
  );
  const statusKey = route ? `${route.world_id}:${route.backend_id}` : "";
  els.messupButton.disabled = !supported || Boolean(state.activeRunId);
  els.messupButton.hidden = !supported;
  els.messupStatus.hidden = !supported;
  if (!supported) {
    return;
  }
  if (state.messupStatusKey !== statusKey) {
    state.messupStatusKey = statusKey;
    els.messupStatus.textContent = "Mess-up check is optional and does not block baseline tests.";
  }
}

function resetMessupStatusForManualSetup() {
  const route = state.selectedRoute;
  if (!route || !route.world_id || !route.world_id.startsWith("molmospaces/")) {
    return;
  }
  const relocation = selectedScenarioSetup() !== "baseline";
  els.messupStatus.textContent = relocation
    ? "Mess-up check is optional; run it again after changing setup or count."
    : "Baseline means no pre-run relocation. Start Agent Run will not mess up objects.";
}

function renderIntentSelector(route) {
  state.selectedIntent = selectedIntentForRoute(route);
  els.intentFields.hidden = !route.enabled;
  els.intentInput.disabled = false;
  const interpretation = launchInterpretation(route);
  els.intentPreview.innerHTML = `
    <dl class="state-list compact">
      <dt>Goal scope</dt><dd>${escapeHtml(interpretation.goalScope)}</dd>
      <dt>Checker</dt><dd>${escapeHtml(interpretation.checker)}</dd>
      <dt>Evaluation</dt><dd>${escapeHtml(interpretation.evaluation)}</dd>
    </dl>
  `;
}

function commandPreview(route) {
  const selected = selectedIntentForRoute(route);
  const parts = [...(route.argv_preview || route.command_preview || [])];
  if (!parts.length) {
    return "Route unavailable.";
  }
  const intentIndex = parts.findIndex((part) => String(part).startsWith("intent="));
  if (intentIndex >= 0) {
    parts[intentIndex] = `intent=${selected}`;
  }
  const prompt = launchPromptText();
  if (route.supports_prompt && prompt) {
    parts.push(`prompt=${prompt}`);
  }
  return commandPartsWithSetup(parts).join(" ");
}

function commandPartsWithSetup(parts) {
  const setup = selectedScenarioSetup();
  const next = withoutKeys(parts, ["scenario_setup", "relocation_count"]);
  next.push(`scenario_setup=${setup}`);
  if (setup !== "baseline") {
    next.push(`relocation_count=${els.relocationCountInput.value || "5"}`);
  }
  return next;
}

function withoutKeys(parts, keys) {
  return parts.filter((part) => {
    const text = String(part);
    return !keys.some((key) => text.startsWith(`${key}=`));
  });
}

function selectedScenarioSetup() {
  return els.scenarioSetupInput.value || "baseline";
}

function routeDefaultOverrides(route) {
  const defaults = {};
  for (const item of route.default_overrides || []) {
    const text = String(item);
    const index = text.indexOf("=");
    if (index > 0) {
      defaults[text.slice(0, index)] = text.slice(index + 1);
    }
  }
  return defaults;
}

function launchPromptText() {
  if (state.operatorMode !== "goal" || state.activeRunId) {
    return "";
  }
  return els.taskPrompt.value.trim();
}

function selectedIntent() {
  const route = state.selectedRoute;
  if (!route) {
    return "";
  }
  const value = els.intentInput.value || state.selectedIntent || route.default_intent || route.intent;
  return selectedIntentForRoute(route, value);
}

function selectedIntentForRoute(route, requestedIntent = "") {
  const options = intentOptions(route);
  const fallback = route.default_intent || route.intent || (options[0] && options[0].id) || "";
  const candidate = requestedIntent || state.selectedIntent || fallback;
  return options.some((option) => option.id === candidate) ? candidate : fallback;
}

function intentOptions(route) {
  const options = route.intent_options || [];
  if (options.length) {
    return options;
  }
  return (route.supported_intents || [route.intent]).map((intent) => ({
    id: intent,
    label: intentLabel(intent),
    checker_id: route.checker_id || "",
    goal_scope: intent === "map-build" ? "whole-room" : "agent-declared",
    evaluation_policy: intent.replace("-", "_"),
  }));
}

function launchInterpretation(route) {
  const intent = selectedIntentForRoute(route);
  const option = intentOptions(route).find((item) => item.id === intent) || {};
  return {
    intent,
    intentLabel: option.label || intentLabel(intent),
    goalScope: goalScopeForIntent(intent, option.goal_scope || ""),
    checker: option.checker_id || route.checker_id || "",
    evaluation: option.evaluation_policy || intent.replace("-", "_"),
  };
}

function goalScopeForIntent(intent, defaultScope) {
  if (intent === "cleanup") {
    return launchPromptText() ? "prompt-scoped" : "whole-room";
  }
  if (intent === "map-build") {
    return "whole-room";
  }
  return defaultScope || "agent-declared";
}

function intentLabel(intent) {
  const labels = {
    cleanup: "Cleanup",
    "open-ended": "Open-ended",
    "map-build": "Map build",
  };
  return labels[intent] || intent;
}

function effectiveReadiness(route) {
  const base = state.readiness[route.id] || {};
  const gates = (base.gates || route.gates || []).map((gate) => ({ ...gate }));
  const lockBlocked =
    base.blocker_kind === "locked" || (base.lock && base.lock.held && !base.lock.stale);
  let blocker = "";

  if (!route.enabled) {
    return { can_start: false, blocker: route.disabled_reason || "", gates };
  }
  if (lockBlocked) {
    blocker =
      base.blocker ||
      "Backend lock is held by another run. Open that run or wait for it to finish.";
  }

  for (const gate of gates) {
    applyLocalGateEvidence(gate);
    if (gate.status !== "ready" && gateBlocksStart(gate) && !blocker) {
      blocker = gate.message || "Required gate is incomplete.";
    }
  }

  return {
    ...base,
    can_start: !blocker,
    blocker,
    blocker_kind: blocker ? (base.blocker_kind || firstBlockingGateKind(gates)) : "",
    gates,
  };
}

function applyLocalGateEvidence(gate) {
  const localReady =
    (gate.id === "context_json" && Boolean(els.contextInput.value.trim())) ||
    (gate.id === "localization_ready" && els.localizationGate.checked) ||
    (gate.id === "run_enabled" && els.enablementGate.checked) ||
    (gate.id === "estop_ready" && els.estopGate.checked);

  if (isRealMovementGate(gate) && els.realMovementGate.checked) {
    gate.blocks_start = true;
    gate.required = true;
    if (gate.status !== "ready") {
      gate.kind = "needs_real_movement_gate";
      gate.message =
        "Real movement is enabled; localization, run enablement, and E-stop/manual-stop readiness must be accepted before launch.";
    }
  }

  if (!localReady) {
    return;
  }
  gate.status = "ready";
  gate.message = "Operator evidence accepted for this launch.";
}

function firstBlockingGateKind(gates) {
  const gate = gates.find((item) => item.status !== "ready" && gateBlocksStart(item));
  return gate ? gate.kind || "" : "";
}

function gateBlocksStart(gate) {
  return Boolean(gate.blocks_start || gate.required);
}

function isRunTerminal(payload = state.activeState || {}) {
  if (!state.activeRunId) {
    return false;
  }
  const controls = payload.controls || {};
  if (controls.next_goal_available === true) {
    return true;
  }
  const statusValues = [
    payload.status,
    payload.phase,
    payload.terminal_reason,
    payload.checker_status && payload.checker_status.status,
  ].map((value) => String(value || "").toLowerCase());
  return statusValues.some((value) =>
    [
      "done",
      "finished",
      "passed",
      "stopped_by_operator",
      "human_takeover_stop",
      "emergency_stopped",
      "failed",
    ].includes(value)
  );
}

function isRealMovementGate(gate) {
  return ["localization_ready", "run_enabled", "estop_ready"].includes(gate.id);
}

function renderStartAction(route, readiness) {
  const mode = state.operatorMode;
  if (mode === "ask_why") {
    els.startButton.textContent = "Ask Why";
    els.startButton.disabled = !state.activeRunId;
    els.startHelp.textContent = state.activeRunId
      ? "Ask Why will read public artifacts for the attached run."
      : "Attach a run before asking why.";
    return;
  }
  if (mode === "steer") {
    const controls = (state.activeState && state.activeState.controls) || {};
    const enabled = Boolean(state.activeRunId && controls.steer_available);
    els.startButton.textContent = "Steer Run";
    els.startButton.disabled = !enabled;
    els.startHelp.textContent = steerHelp(controls);
    return;
  }
  if (state.activeRunId) {
    const terminal = isRunTerminal();
    els.startButton.textContent = terminal ? "Start Next Goal" : "Run Attached";
    els.startButton.disabled = !terminal || !route.supports_prompt;
    els.startHelp.textContent = terminal
      ? "Start a linked Next Goal from this terminal parent run."
      : `Watching active run ${state.activeRunId}. Use Steer or Ask Why.`;
    return;
  }
  const attachableRun = readiness.attachable_run || null;
  els.startButton.textContent = attachableRun ? "Attach Existing Run" : "Start Agent Run";
  els.startButton.disabled = !route.enabled || (readiness.can_start === false && !attachableRun);
  els.startHelp.textContent = attachableRun
    ? `Existing run ${attachableRun.run_id} is using this backend. Attach to watch it.`
    : readiness.blocker || route.disabled_reason || "";
}

function steerHelp(controls) {
  if (!state.activeRunId) {
    return "Attach a run before steering.";
  }
  if (controls.steer_available) {
    return "Message will be written to operator_messages.jsonl for the active run.";
  }
  return controls.supports_operator_steer
    ? "Steer is unavailable after this run is terminal. Use Goal for Next Goal."
    : "This route does not expose active-run steering.";
}

function handleStartAction() {
  if (state.operatorMode === "ask_why" || state.operatorMode === "steer") {
    sendOperatorMessage();
    return;
  }
  if (state.activeRunId && isRunTerminal()) {
    confirmNextGoal();
    return;
  }
  if (state.activeRunId) {
    els.startHelp.textContent = "Use Steer or Ask Why while this run is active.";
    return;
  }
  const readiness = effectiveReadiness(state.selectedRoute);
  if (readiness.attachable_run) {
    attachExistingRun(readiness.attachable_run);
    return;
  }
  confirmLaunch();
}

function attachExistingRun(run) {
  state.activeRunId = run.run_id;
  state.activeRouteId = run.selection_id || run.route_id || state.selectedRoute.id;
  renderStartAction(state.selectedRoute, effectiveReadiness(state.selectedRoute));
  startPolling();
}

async function attachLatestResult() {
  const result = await fetchJson("/api/runs/latest");
  if (result.error) {
    els.eventList.textContent = result.error;
    return;
  }
  const route = state.routes.find(
    (item) => item.id === (result.selection_id || result.route_id)
  );
  if (route) {
    state.selectedRoute = route;
    state.selectedIntent = route.intent_id || "";
    state.syncAxesFromRoute = true;
    renderRoutes();
    renderSelection();
  }
  state.activeRunId = result.run_id;
  state.activeRouteId = result.selection_id || result.route_id || (route ? route.id : state.selectedRoute.id);
  els.eventList.textContent = `Attached latest result ${result.run_id}${
    result.display_run_id ? ` / ${result.display_run_id}` : ""
  }.`;
  renderStartAction(state.selectedRoute, effectiveReadiness(state.selectedRoute));
  startPolling();
}

function scheduleReadinessRefresh() {
  if (state.readinessTimer) {
    clearTimeout(state.readinessTimer);
  }
  state.readinessTimer = setTimeout(refreshSelectedRouteReadiness, 250);
}

async function refreshSelectedRouteReadiness() {
  state.selectedRoute = selectedCombinationFromAxes();
  const route = state.selectedRoute;
  if (!route || !route.enabled) {
    return;
  }
  const params = new URLSearchParams({
    selection_id: route.id,
    host: "127.0.0.1",
    port: els.portInput.value || "18788",
    scenario_setup: selectedScenarioSetup(),
  });
  if (selectedProviderProfile()) {
    params.set("provider_profile", selectedProviderProfile());
  }
  if (els.contextInput.value) {
    params.set("context_json", els.contextInput.value);
  }
  if (isAgibotRoute(route)) {
    params.set("real_movement_enabled", els.realMovementGate.checked ? "true" : "false");
    params.set("localization_ready", els.localizationGate.checked ? "true" : "false");
    params.set("run_enabled", els.enablementGate.checked ? "true" : "false");
    params.set("estop_ready", els.estopGate.checked ? "true" : "false");
  }
  const readiness = await fetchJson(`/api/readiness?${params.toString()}`);
  if (readiness.error) {
    els.startHelp.textContent = readiness.error;
    return;
  }
  state.readiness[route.id] = readiness;
  renderRoutes();
  renderSelection();
}

function confirmLaunch() {
  const route = state.selectedRoute;
  const promptSource = launchPromptText() ? "custom" : "default";
  const interpretation = launchInterpretation(route);
  const providerRows = route.provider_profile
    ? `<dt>Provider</dt><dd>${escapeHtml(selectedProviderProfile())}</dd>`
    : "";
  const movementRows = isAgibotRoute(route)
    ? `<dt>Movement</dt><dd>${escapeHtml(
        els.realMovementGate.checked ? "enabled" : "dry-run"
      )}</dd>`
    : "";
  const summary = `
    <dl class="state-list">
      <dt>World</dt><dd>${escapeHtml(route.world_label || route.world_id)}</dd>
      <dt>Backend</dt><dd>${escapeHtml(route.backend_label || route.backend_id)}</dd>
      <dt>Agent</dt><dd>${escapeHtml(route.agent_engine_label || route.agent_engine_id)}</dd>
      <dt>Evidence</dt><dd>${escapeHtml(route.evidence_lane)}</dd>
      <dt>Intent</dt><dd>${escapeHtml(interpretation.intentLabel)}</dd>
      <dt>Goal scope</dt><dd>${escapeHtml(interpretation.goalScope)}</dd>
      <dt>Checker</dt><dd>${escapeHtml(interpretation.checker)}</dd>
      <dt>Evaluation</dt><dd>${escapeHtml(interpretation.evaluation)}</dd>
      ${providerRows}
      <dt>Lock</dt><dd>${escapeHtml(route.lock_name)}</dd>
      ${movementRows}
      <dt>Prompt</dt><dd>${promptSource}</dd>
      <dt>Output</dt><dd>output/operator-console/runs/...</dd>
    </dl>
  `;
  confirmAction({
    title: "Launch Run",
    cta: "Launch Run",
    bodyHtml: summary,
    onConfirm: launchRun,
  });
}

function confirmNextGoal() {
  const prompt = els.taskPrompt.value.trim();
  if (!prompt) {
    els.startHelp.textContent = "Enter a Next Goal before starting a linked run.";
    return;
  }
  const route = state.activeState && state.activeState.route ? state.activeState.route : state.selectedRoute;
  const summary = `
    <dl class="state-list">
      <dt>Parent Run</dt><dd>${escapeHtml(state.activeRunId || "")}</dd>
      <dt>Launch</dt><dd>${escapeHtml(route.label || state.selectedRoute.label)}</dd>
      <dt>World</dt><dd>${escapeHtml(route.world_label || route.world_id || "")}</dd>
      <dt>Backend</dt><dd>${escapeHtml(route.backend_label || route.backend_id || "")}</dd>
      <dt>Next Goal</dt><dd>custom</dd>
      <dt>Context</dt><dd>public parent artifacts only</dd>
    </dl>
  `;
  confirmAction({
    title: "Start Next Goal",
    cta: "Start Next Goal",
    bodyHtml: summary,
    onConfirm: () => sendNextGoal({ confirmed: false }),
  });
}

async function sendNextGoal({ confirmed = false } = {}) {
  if (!state.activeRunId) {
    return;
  }
  const prompt = els.taskPrompt.value.trim();
  if (!prompt) {
    els.startHelp.textContent = "Enter a Next Goal before starting a linked run.";
    return;
  }
  const result = await fetchJson(
    `/api/runs/${encodeURIComponent(state.activeRunId)}/next-goal`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, confirmed }),
    }
  );
  if (result.error) {
    els.startHelp.textContent = result.error;
    return;
  }
  if (result.status === "confirmation_required" && !confirmed) {
    confirmAction({
      title: "Confirm Next Goal",
      cta: "Confirm Next Goal",
      body: nextGoalConfirmationText(result),
      onConfirm: () => sendNextGoal({ confirmed: true }),
    });
    return;
  }
  if (result.started_run && result.started_run.run_id) {
    state.activeRunId = result.started_run.run_id;
    state.activeRouteId = result.started_run.launch_selection
      ? result.started_run.launch_selection.id
      : result.started_run.route
      ? result.started_run.route.id
      : state.activeRouteId || state.selectedRoute.id;
    state.activeState = result.started_run;
    els.taskPrompt.value = "";
    els.promptCount.textContent = "0 / 2000";
    els.startHelp.textContent = `Started Next Goal ${state.activeRunId}.`;
    startPolling();
    renderSelection();
    return;
  }
  els.startHelp.textContent = operatorMessageResultText(result);
  pollState();
}

function nextGoalConfirmationText(result) {
  const reason = result.queue_reason || "operator_confirmation_required";
  return (
    "This parent run needs explicit confirmation before a linked Next Goal starts.\n\n" +
    `Reason: ${reason}\n\n` +
    "Confirm only if the parent artifacts are sufficient and any required movement gates are accepted."
  );
}

// Shared confirmation modal. Pass `body` for plain text or `bodyHtml` for
// pre-escaped markup. Routes the styled <dialog> for every destructive or
// launch action instead of a native browser prompt.
function confirmAction({ title, cta, body, bodyHtml, onConfirm }) {
  els.confirmTitle.textContent = title;
  els.confirmAction.textContent = cta;
  if (bodyHtml != null) {
    els.confirmBody.innerHTML = bodyHtml;
  } else {
    els.confirmBody.textContent = body || "";
  }
  els.confirmDialog.showModal();
  els.confirmDialog.addEventListener(
    "close",
    () => {
      if (els.confirmDialog.returnValue === "confirm") {
        onConfirm();
      }
    },
    { once: true }
  );
}

async function previewMessup() {
  const route = state.selectedRoute;
  if (!route) {
    return;
  }
  const requestedCount = els.relocationCountInput.value || "5";
  els.messupButton.disabled = true;
  els.messupStatus.textContent = "Checking mess-up target capacity...";
  const result = await fetchJson("/api/messup-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      world_id: route.world_id,
      backend_id: route.backend_id,
      scenario_setup: "relocate-cleanup-related-objects",
      relocation_count: requestedCount,
      seed: els.seedInput.value || "7",
    }),
  });
  els.messupButton.disabled = false;
  if (result.error) {
    els.scenarioSetupInput.value = "baseline";
    els.messupStatus.textContent = `Mess-up check failed: ${result.error}. Baseline remains available.`;
    renderSelection();
    return;
  }
  if (result.ok) {
    els.scenarioSetupInput.value = result.scenario_setup || "relocate-cleanup-related-objects";
    els.relocationCountInput.value = String(result.requested_count || requestedCount);
    markCurrentSetupSelection(route);
    els.messupStatus.textContent =
      `Mess-up ready: ${result.selected_count} / ${result.requested_count} targets. ` +
      "Start Agent Run will use this relocation setup.";
  } else {
    els.scenarioSetupInput.value = "baseline";
    markCurrentSetupSelection(route);
    els.messupStatus.textContent =
      `Mess-up unavailable: ${result.message || "not enough eligible targets"}. ` +
      "Baseline remains available for follow-up tests.";
  }
  renderSelection();
  scheduleReadinessRefresh();
}

function markCurrentSetupSelection(route) {
  state.setupSelectionKey = `${route.id}:${selectedIntentForRoute(route)}`;
}

async function launchRun() {
  const route = state.selectedRoute;
  const body = {
    world_id: route.world_id,
    backend_id: route.backend_id,
    intent_id: selectedIntent(),
    agent_engine_id: route.agent_engine_id,
    provider_profile: selectedProviderProfile(),
    evidence_lane: route.evidence_lane,
    scenario_setup: selectedScenarioSetup(),
    prompt: launchPromptText(),
    overrides: {
      seed: els.seedInput.value || "7",
      host: "127.0.0.1",
      port: els.portInput.value || "18788",
    },
    gates: {
      localization_ready: els.localizationGate.checked,
      run_enabled: els.enablementGate.checked,
      estop_ready: els.estopGate.checked,
    },
  };
  if (body.scenario_setup !== "baseline" && els.relocationCountInput.value) {
    body.overrides.relocation_count = els.relocationCountInput.value;
  }
  if (els.contextInput.value) {
    body.overrides.context_json = els.contextInput.value;
  }
  if (isAgibotRoute(state.selectedRoute)) {
    body.overrides.real_movement_enabled = els.realMovementGate.checked ? "true" : "false";
  }
  if (els.isaacSceneInput.value) {
    body.overrides.isaac_scene_usd_path = els.isaacSceneInput.value;
  }
  if (route.agent_engine_id === "codex-cli" || route.agent_engine_id === "openai-agents-sdk") {
    body.env_overrides = {
      ROBOCLAWS_CODEX_PROVIDER: selectedProviderProfile(),
    };
  } else if (route.agent_engine_id === "claude-code") {
    body.env_overrides = {
      ROBOCLAWS_CLAUDE_PROVIDER: selectedProviderProfile(),
    };
  }

  const result = await fetchJson("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (result.error) {
    els.startHelp.textContent = result.error;
    return;
  }
  state.activeRunId = result.run_id;
  state.activeRouteId = route.id;
  renderStartAction(state.selectedRoute, effectiveReadiness(state.selectedRoute));
  startPolling();
}

function startPolling() {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
  }
  pollState();
  state.pollTimer = setInterval(pollState, 2000);
}

async function pollState() {
  if (!state.activeRunId) {
    return;
  }
  const url = `/api/runs/${encodeURIComponent(state.activeRunId)}?selection_id=${encodeURIComponent(
    state.activeRouteId
  )}`;
  const payload = await fetchJson(url);
  if (payload.error) {
    return;
  }
  state.activeState = payload;
  if (payload.launch_selection && payload.launch_selection.id) {
    state.activeRouteId = payload.launch_selection.id;
  } else if (payload.route && payload.route.id) {
    state.activeRouteId = payload.route.id;
  }
  renderRunState(payload);
  if (!els.rawEvidence.hidden) {
    refreshRawEvidence();
  }
}

function renderRunState(payload) {
  const route = payload.launch_selection || payload.route || state.selectedRoute || {};
  const runLabel = compactRunId(payload.run_id);
  const displayRunLabel = compactDisplayRunId(payload.display_run_id || "");
  const attemptLabel = displayRunLabel && displayRunLabel !== runLabel
    ? ` / ${displayRunLabel}`
    : "";
  document.querySelector(".top-run-bar").classList.add("run-active");
  els.runTitle.textContent = `${route.label || "Agent run"} / ${runLabel}${attemptLabel}`;
  els.runTitle.title = `${route.label || "Agent run"} / ${payload.run_id || ""}${
    payload.display_run_id && payload.display_run_id !== payload.run_id
      ? ` / ${payload.display_run_id}`
      : ""
  }`;
  els.routeStatus.textContent = payload.status_label || payload.phase || payload.status || "Running";
  els.routeStatus.className = `badge ${statusClass(payload.status || payload.phase)}`;
  els.lockStatus.textContent = `lock: ${route.lock_name || payload.backend_lock || "none"}`;
  els.elapsedStatus.textContent =
    payload.elapsed_seconds == null ? "00:00" : formatElapsed(payload.elapsed_seconds);
  els.phaseValue.textContent = payload.phase || "idle";
  els.backendLockValue.textContent = payload.backend_lock || "none";
  els.cameraAngleValue.textContent = cameraStateLabel(payload.camera_state || {});
  els.terminalValue.textContent = payload.terminal_reason || "none";

  const decision = payload.latest_public_decision_evidence || {};
  els.decisionPanel.innerHTML = `
    <strong>${escapeHtml(payload.latest_action || "No action")}</strong>
    <p>${escapeHtml(
      decision.observation_summary || "No decision yet. The agent has not called a robot tool."
    )}</p>
    <p>${escapeHtml(decision.reasoning || decision.decision || "")}</p>
    ${decision.blocked_reason ? `<p class="field-help">${escapeHtml(decision.blocked_reason)}</p>` : ""}
  `;
  renderToolPanel(payload);
  const checkerStatus = payload.checker_status || {};
  els.proofPanel.textContent = `${checkerStatus.status || "pending"}: ${
    checkerStatus.message ||
    checkerStatus.checker_log ||
    "Checker has not run yet."
  }`;
  renderArtifacts(payload.artifact_paths || []);
  renderViews(payload.latest_view_assets || {}, route);
  renderEvents(payload);
  renderControls(payload);
  renderOperatorInput(state.selectedRoute);
  renderStartAction(state.selectedRoute, effectiveReadiness(state.selectedRoute));
  renderOperatorMode(payload);
}

function renderToolPanel(payload) {
  const cameraState = payload.camera_state || {};
  const cameraSummary = cameraState.summary || "yaw 0 deg, pitch 0 deg (neutral)";
  const activeClass = cameraState.active ? "camera-active" : "camera-neutral";
  els.toolPanel.innerHTML = `
    <div class="camera-angle-row">
      <span class="camera-angle-label">Camera</span>
      <span class="camera-angle-badge ${activeClass}">${escapeHtml(cameraSummary)}</span>
    </div>
    <pre class="tool-json">${escapeHtml(JSON.stringify(payload.latest_tool_call || {}, null, 2))}</pre>
  `;
}

function cameraStateLabel(cameraState) {
  return cameraState.summary || "yaw 0 deg, pitch 0 deg (neutral)";
}

function renderControls(payload) {
  const controls = payload.controls || {};
  const pauseAvailable = Boolean(controls.pause_available);
  els.pauseButton.hidden = !pauseAvailable;
  els.pauseButton.disabled = !pauseAvailable;
  els.stopButton.disabled = !controls.stop_available;
  els.emergencyButton.disabled = !controls.emergency_stop_required;
}

function renderOperatorMode(payload = state.activeState || {}) {
  document.querySelectorAll(".operator-mode").forEach((button) => {
    button.classList.toggle("active", button.dataset.operatorMode === state.operatorMode);
  });
  const messages = payload.operator_messages || {};
  if (messages.operator_message_pending) {
    els.startHelp.textContent = `${
      messages.pending_steer_count || 1
    } steer message(s) waiting for agent checkpoint.`;
  }
}

async function sendOperatorMessage() {
  if (!state.activeRunId) {
    return;
  }
  const text = els.taskPrompt.value.trim();
  if (!text) {
    els.startHelp.textContent = "Enter operator text before sending.";
    return;
  }
  const encodedRun = encodeURIComponent(state.activeRunId);
  const mode = state.operatorMode;
  const endpoint =
    mode === "ask_why" ? `/api/runs/${encodedRun}/ask-why` : `/api/runs/${encodedRun}/messages`;
  const key = mode === "ask_why" ? "question" : "body";
  const result = await fetchJson(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ [key]: text }),
  });
  if (result.error) {
    els.startHelp.textContent = result.error;
    return;
  }
  els.taskPrompt.value = "";
  els.promptCount.textContent = "0 / 2000";
  els.startHelp.textContent = operatorMessageResultText(result);
  pollState();
}

function operatorMessageResultText(result) {
  if (result.command_type === "ask_why") {
    const summary = result.answer && result.answer.summary ? `: ${result.answer.summary}` : "";
    return `Ask Why answered${summary}`;
  }
  if (result.command_type === "next_goal") {
    return `Next Goal ${result.status || "queued"} (${result.queue_reason || "queued"}).`;
  }
  if (result.command_type === "steer") {
    return `Steer message ${result.status || "queued"}; waiting for check_operator_messages.`;
  }
  return "Operator message recorded.";
}

function renderArtifacts(items) {
  els.artifactList.innerHTML = "";
  for (const item of items) {
    const row = document.createElement("div");
    row.className = "artifact-row";
    const link = item.href || artifactHref(item.path);
    row.innerHTML = `
      <span>${escapeHtml(item.label)}</span>
      ${link ? `<a href="${link}" target="_blank" rel="noreferrer">Open</a>` : `<span class="field-help">pending</span>`}
    `;
    els.artifactList.appendChild(row);
  }
}

function renderViews(assets, route = state.selectedRoute) {
  setImageSlot("fpv", assets.fpv, "No frame yet. Waiting for the first observation artifact.");
  setImageSlot("map", assets.map, "Semantic map artifact has not been written yet.");
  setImageSlot("topdown", assets.topdown, "Top-down scene view has not been written yet.");
  const chaseEmptyText = routeHasOverviewChase(route)
    ? "No chase frame yet. Waiting for the first observation artifact."
    : "Chase view unavailable for this backend.";
  setImageSlot("chase", assets.chase, chaseEmptyText);
  setImageSlot("grounding", assets.grounding, "No grounding result yet.");
  ensureActiveViewAvailable(route);
  renderViewModes(route);
}

function renderSelectedScenePreview(route = state.selectedRoute) {
  if (state.activeRunId) {
    return;
  }
  const previews = route && route.preview_assets ? route.preview_assets : {};
  setImageSlot("fpv", previews.fpv, "No scene FPV preview is available.");
  setImageSlot("map", previews.map, "No semantic map preview is available.");
  setImageSlot("topdown", previews.topdown, "No top-down scene preview is available.");
  setImageSlot("grounding", null, "Grounding will appear after a camera-grounded run starts.");
  const chaseEmptyText = routeHasOverviewChase(route)
    ? "Chase preview will appear after a run starts."
    : "Chase view unavailable for this backend.";
  setImageSlot("chase", previews.chase, chaseEmptyText);
}

function setImageSlot(name, asset, emptyText) {
  const slot = document.getElementById(`${name}-frame`);
  if (!slot) {
    return;
  }
  if (!asset || !asset.path) {
    slot.textContent = emptyText;
    return;
  }
  const src = asset.href || artifactHref(asset.path);
  const label = imageLabel(name);
  slot.innerHTML = `
    <button
      type="button"
      class="image-preview-button"
      data-image-src="${escapeHtml(src)}"
      data-image-title="${escapeHtml(label)}"
      data-image-path="${escapeHtml(asset.path || "")}"
      aria-label="Open ${escapeHtml(label)} image preview"
      title="Open image preview"
    >
      <img alt="${escapeHtml(label)} artifact" src="${escapeHtml(src)}" />
    </button>
  `;
  const button = slot.querySelector(".image-preview-button");
  button.addEventListener("click", () => {
    openImageDialog({
      src,
      title: label,
      path: asset.path || "",
    });
  });
}

function imageLabel(name) {
  const labels = {
    fpv: "FPV",
    map: "Semantic Map",
    topdown: "Top-down Scene View",
    grounding: "Grounding",
    chase: "Chase",
  };
  return labels[name] || name;
}

function openImageDialog({ src, title, path }) {
  if (!src) {
    return;
  }
  els.imageDialogTitle.textContent = title;
  els.imageDialogPath.textContent = path;
  els.imageDialogImg.src = src;
  els.imageDialogImg.alt = `${title} artifact`;
  els.imageDialog.showModal();
}

function renderEvents(payload) {
  const checkerStatus = payload.checker_status || {};
  const bits = [
    `phase=${payload.phase}`,
    payload.terminal_reason ? `reason=${payload.terminal_reason}` : "",
    `action=${payload.latest_action || "none"}`,
    `checker=${checkerStatus.status || "pending"}`,
    `outputs=${payload.display_run_dir || payload.run_dir}`,
  ].filter(Boolean);
  els.eventList.textContent = bits.join("  ");
}

function renderViewModes(route = state.selectedRoute) {
  const visualGrid = document.getElementById("visual-grid");
  if (!visualGrid || !route) {
    return;
  }
  const modes = routeViewModes(route);
  const hasOverviewChase = routeHasOverviewChase(route, modes);
  const activeView = state.activeView || "overview";
  visualGrid.className = `view-grid mode-${activeView}${
    hasOverviewChase ? " has-overview-chase" : " no-overview-chase"
  }`;

  document.querySelectorAll(".view-mode").forEach((button) => {
    const enabled = modes.has(button.dataset.view);
    button.hidden = !enabled;
    button.classList.toggle("active", enabled && button.dataset.view === activeView);
  });

  const visiblePanels = visiblePanelsForView(activeView, modes, route);
  document.querySelectorAll("[data-panel]").forEach((panel) => {
    panel.hidden = !visiblePanels.has(panel.dataset.panel);
  });
}

function ensureActiveViewAvailable(route = state.selectedRoute) {
  if (!route) {
    return;
  }
  const modes = routeViewModes(route);
  if (!modes.has(state.activeView)) {
    state.activeView = "overview";
  }
}

function routeViewModes(route) {
  const modes = new Set(route.view_modes || ["overview", "fpv", "map", "outputs"]);
  modes.add("topdown");
  return modes;
}

function routeHasOverviewChase(route, modes = routeViewModes(route)) {
  return Boolean(route && route.resource_kind !== "physical_robot" && modes.has("chase"));
}

function isAgibotRoute(route) {
  const groups = new Set((route && route.field_groups) || []);
  return Boolean(route && (route.backend_id === "agibot-gdk" || groups.has("agibot_gates")));
}

function selectedCodexProvider() {
  return selectedProviderProfile() || els.codexProviderInput.value || "codex-env";
}

function selectedClaudeProvider() {
  return selectedProviderProfile() || els.claudeProviderInput.value || "mimo-anthropic";
}

function selectedProviderProfile() {
  return (els.providerProfileInput && els.providerProfileInput.value) || "";
}

function selectedClaudeProviderLabel() {
  const option = Array.from(els.claudeProviderInput.options).find(
    (item) => item.value === selectedClaudeProvider()
  );
  return option ? option.textContent : selectedClaudeProvider();
}

function visiblePanelsForView(view, modes, route = state.selectedRoute) {
  if (view === "overview") {
    const panels = new Set(["fpv", "map", "topdown"]);
    if (routeHasOverviewChase(route, modes)) {
      panels.add("chase");
    } else {
      panels.add("blank-chase");
    }
    return panels;
  }
  if (!modes.has(view)) {
    return new Set(["fpv", "map"]);
  }
  if (view === "outputs") {
    return new Set(["outputs"]);
  }
  return new Set([view]);
}

async function postRunAction(action) {
  if (!state.activeRunId) {
    return;
  }
  const result = await fetchJson(`/api/runs/${encodeURIComponent(state.activeRunId)}/${action}`, {
    method: "POST",
  });
  if (result.error) {
    els.eventList.textContent = result.error;
    return;
  }
  if (result.reason) {
    els.eventList.textContent = result.reason;
  }
  if (["stop", "emergency-stop"].includes(action)) {
    detachRunAfterStop(result);
    await refreshSelectedRouteReadiness();
    return;
  }
  pollState();
}

function detachRunAfterStop(result) {
  if (state.pollTimer) {
    clearInterval(state.pollTimer);
    state.pollTimer = null;
  }
  state.activeState = result;
  renderRunState(result);
  state.activeRunId = null;
  state.activeRouteId = "";
  els.eventList.textContent =
    result.terminal_reason || result.phase || "Run stopped; backend lock released.";
  renderStartAction(state.selectedRoute, effectiveReadiness(state.selectedRoute));
}

async function toggleRawEvidence() {
  if (!state.activeRunId) {
    return;
  }
  const hidden = els.rawEvidence.hidden;
  els.rawEvidence.hidden = !hidden;
  els.evidenceStripResizer.hidden = !hidden;
  els.appShell.classList.toggle("raw-evidence-open", hidden);
  els.toggleRawButton.textContent = hidden ? "Hide Raw Evidence" : "Show Raw Evidence";
  if (hidden) {
    refreshRawEvidence({ forceStickToBottom: true });
  }
}

async function refreshRawEvidence(options = {}) {
  const forceStickToBottom = options.forceStickToBottom === true;
  const driver = ((state.activeState && state.activeState.artifact_paths) || []).find(
    (item) => item.label === "Driver Log"
  );
  const shouldStickToBottom =
    forceStickToBottom ||
    els.rawEvidence.scrollTop + els.rawEvidence.clientHeight >=
      els.rawEvidence.scrollHeight - 24;
  const text = driver
    ? await fetch(`/api/raw/${encodeURI(driver.path)}`).then((response) => response.text())
    : "";
  els.rawEvidence.textContent = text || "No raw driver log yet.";
  if (shouldStickToBottom) {
    els.rawEvidence.scrollTop = els.rawEvidence.scrollHeight;
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  return response.json();
}

function artifactHref(path) {
  const marker = "output/operator-console/";
  const index = String(path || "").indexOf(marker);
  if (index >= 0) {
    return `/artifacts/${encodeURIComponent(path.slice(index + marker.length)).replaceAll(
      "%2F",
      "/"
    )}`;
  }
  return "";
}

function statusClass(value) {
  if (!value) return "neutral";
  const text = String(value);
  if (text.includes("pass") || text.includes("finish")) return "passed";
  if (text.includes("rate_limit")) return "failed";
  if (text.includes("fail") || text.includes("stop")) return "failed";
  if (text.includes("run") || text.includes("start")) return "running";
  return "warning";
}

function formatElapsed(seconds) {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  const minutes = String(Math.floor(value / 60)).padStart(2, "0");
  const rest = String(value % 60).padStart(2, "0");
  return `${minutes}:${rest}`;
}

function compactRunId(runId) {
  return String(runId || "").replace(
    /^(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})(.*)$/,
    "$2$3-$4$5$7"
  );
}

function compactDisplayRunId(displayRunId) {
  return String(displayRunId || "").replace(
    /^(\d{2})(\d{2})_(\d{2})(\d{2})(.*)$/,
    "$1$2_$3$4$5"
  );
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

boot();
