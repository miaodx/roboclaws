const state = {
  routes: [],
  readiness: {},
  selectedRoute: null,
  activeRunId: null,
  activeRouteId: "",
  activeState: null,
  pollTimer: null,
  readinessTimer: null,
  activeView: "overview",
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
  taskPrompt: document.getElementById("prompt-input"),
  promptHelp: document.getElementById("prompt-copy"),
  promptCount: document.getElementById("char-count"),
  seedInput: document.getElementById("seed-input"),
  messInput: document.getElementById("mess-count-input"),
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
  pauseButton: document.getElementById("pause-button"),
  stopButton: document.getElementById("stop-button"),
  emergencyButton: document.getElementById("emergency-button"),
  phaseValue: document.getElementById("phase-value"),
  backendLockValue: document.getElementById("backend-lock-value"),
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
  state.routes = payload.routes || [];
  state.readiness = payload.readiness || {};
  state.selectedRoute = state.routes.find((route) => route.enabled) || state.routes[0];
  renderRoutes();
  renderSelection();
  bindEvents();
  renderViewModes();
}

function bindEvents() {
  els.taskPrompt.addEventListener("input", () => {
    els.promptCount.textContent = `${els.taskPrompt.value.length} / 2000`;
  });
  [
    els.contextInput,
    els.codexProviderInput,
    els.claudeProviderInput,
    els.portInput,
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
  els.startButton.addEventListener("click", handleStartAction);
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
  for (const route of state.routes) {
    const button = document.createElement("button");
    const readiness = effectiveReadiness(route);
    const selectable = Boolean(route.enabled);
    const display = routeStatusDisplay(route, readiness);
    button.type = "button";
    button.className = `route-card${route.id === state.selectedRoute.id ? " active" : ""}`;
    button.dataset.routeId = route.id;
    button.disabled = !selectable;
    button.innerHTML = `
      <div class="route-card-title">
        <span>${escapeHtml(route.label)}</span>
        <span class="badge ${display.className}">${display.label}</span>
      </div>
      <div class="meta-label">${escapeHtml(route.driver_label)} / ${escapeHtml(route.profile)}</div>
      <div>${escapeHtml(route.backend)}</div>
      ${
        route.disabled_reason
          ? `<div class="field-help">${escapeHtml(route.disabled_reason)}</div>`
          : ""
      }
    `;
    button.addEventListener("click", () => {
      state.selectedRoute = route;
      renderRoutes();
      renderSelection();
      refreshSelectedRouteReadiness();
    });
    els.routeList.appendChild(button);
  }
}

function renderSelection() {
  const route = state.selectedRoute;
  if (!route) {
    return;
  }
  const readiness = effectiveReadiness(route);
  renderRouteFields(route);
  renderSelectedRouteSummary(route, readiness);
  ensureActiveViewAvailable(route);
  renderViewModes(route);
  els.taskPrompt.disabled = !route.supports_prompt;
  els.taskPrompt.placeholder = route.task_prompt_default || route.default_prompt || "";
  els.promptHelp.textContent = route.supports_prompt
    ? "Empty prompt uses the route default. Prompt text is never interpreted as shell."
    : route.prompt_disabled_reason ||
      "This route cannot accept a custom prompt safely. Use the default task prompt.";

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
  els.selectedRouteSummary.innerHTML = `
    <div class="route-card-title">
      <span>${escapeHtml(route.label)}</span>
      <span class="badge ${status.className}">${status.label}</span>
    </div>
    <div class="meta-label">${escapeHtml(route.driver_label)} / ${escapeHtml(route.profile)}</div>
    <div class="field-help">${escapeHtml(route.backend)}</div>
  `;
}

function renderRouteFields(route) {
  const fieldGroups = new Set(route.field_groups || ["common"]);

  els.commonFields.hidden = !route.enabled || !fieldGroups.has("common");
  els.codexFields.hidden = !route.enabled || route.driver !== "codex";
  els.claudeFields.hidden = !route.enabled || route.driver !== "claude";
  els.isaacFields.hidden = !fieldGroups.has("isaac");
  els.agibotFields.hidden = !fieldGroups.has("agibot");
  els.agibotGateFields.hidden = !fieldGroups.has("agibot_gates");
}

function commandPreview(route) {
  const parts = route.argv_preview || route.command_preview || [];
  if (!parts.length) {
    return "Route unavailable.";
  }
  return parts.join(" ");
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

function isRealMovementGate(gate) {
  return ["localization_ready", "run_enabled", "estop_ready"].includes(gate.id);
}

function renderStartAction(route, readiness) {
  if (state.activeRunId) {
    els.startButton.textContent = "Run Attached";
    els.startButton.disabled = true;
    els.startHelp.textContent = `Watching run ${state.activeRunId}.`;
    return;
  }
  const attachableRun = readiness.attachable_run || null;
  els.startButton.textContent = attachableRun ? "Attach Existing Run" : "Start Agent Run";
  els.startButton.disabled = !route.enabled || (readiness.can_start === false && !attachableRun);
  els.startHelp.textContent = attachableRun
    ? `Existing run ${attachableRun.run_id} is using this backend. Attach to continue watching it.`
    : readiness.blocker || route.disabled_reason || "";
}

function handleStartAction() {
  const readiness = effectiveReadiness(state.selectedRoute);
  if (readiness.attachable_run) {
    attachExistingRun(readiness.attachable_run);
    return;
  }
  confirmLaunch();
}

function attachExistingRun(run) {
  state.activeRunId = run.run_id;
  state.activeRouteId = run.route_id || state.selectedRoute.id;
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
  const route = state.selectedRoute;
  if (!route || !route.enabled) {
    return;
  }
  const params = new URLSearchParams({
    route_id: route.id,
    host: "127.0.0.1",
    port: els.portInput.value || "18788",
  });
  if (els.contextInput.value) {
    params.set("context_json", els.contextInput.value);
  }
  if (isAgibotRoute(route)) {
    params.set("real_movement_enabled", els.realMovementGate.checked ? "true" : "false");
    params.set("localization_ready", els.localizationGate.checked ? "true" : "false");
    params.set("run_enabled", els.enablementGate.checked ? "true" : "false");
    params.set("estop_ready", els.estopGate.checked ? "true" : "false");
  }
  if (route.driver === "codex") {
    params.set("codex_provider", selectedCodexProvider());
  }
  if (route.driver === "claude") {
    params.set("claude_provider", selectedClaudeProvider());
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
  const promptSource = els.taskPrompt.value.trim() ? "custom" : "default";
  const providerRows =
    route.driver === "codex"
      ? `<dt>Provider</dt><dd>${escapeHtml(selectedCodexProvider())}</dd>`
      : route.driver === "claude"
        ? `<dt>Provider</dt><dd>${escapeHtml(selectedClaudeProviderLabel())}</dd>`
        : "";
  const movementRows = isAgibotRoute(route)
    ? `<dt>Movement</dt><dd>${escapeHtml(
        els.realMovementGate.checked ? "enabled" : "dry-run"
      )}</dd>`
    : "";
  const summary = `
    <dl class="state-list">
      <dt>Route</dt><dd>${escapeHtml(route.label)}</dd>
      <dt>Driver</dt><dd>${escapeHtml(route.driver_label || route.driver)}</dd>
      <dt>Backend</dt><dd>${escapeHtml(route.backend)}</dd>
      <dt>Profile</dt><dd>${escapeHtml(route.profile)}</dd>
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

async function launchRun() {
  const body = {
    route_id: state.selectedRoute.id,
    prompt: els.taskPrompt.value,
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
  if (els.messInput.value) {
    body.overrides.generated_mess_count = els.messInput.value;
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
  if (state.selectedRoute.driver === "codex") {
    body.env_overrides = {
      ROBOCLAWS_CODEX_PROVIDER: selectedCodexProvider(),
    };
  } else if (state.selectedRoute.driver === "claude") {
    body.env_overrides = {
      ROBOCLAWS_CLAUDE_PROVIDER: selectedClaudeProvider(),
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
  state.activeRouteId = state.selectedRoute.id;
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
  const url = `/api/runs/${encodeURIComponent(state.activeRunId)}?route=${encodeURIComponent(
    state.activeRouteId
  )}`;
  const payload = await fetchJson(url);
  if (payload.error) {
    return;
  }
  state.activeState = payload;
  renderRunState(payload);
  if (!els.rawEvidence.hidden) {
    refreshRawEvidence();
  }
}

function renderRunState(payload) {
  const route = payload.route || state.selectedRoute || {};
  const attemptLabel = payload.display_run_id && payload.display_run_id !== payload.run_id
    ? ` / ${payload.display_run_id}`
    : "";
  document.querySelector(".top-run-bar").classList.add("run-active");
  els.runTitle.textContent = `${route.label || "Agent run"} / ${payload.run_id}${attemptLabel}`;
  els.routeStatus.textContent = payload.status_label || payload.phase || payload.status || "Running";
  els.routeStatus.className = `badge ${statusClass(payload.status || payload.phase)}`;
  els.lockStatus.textContent = `lock: ${route.lock_name || payload.backend_lock || "none"}`;
  els.elapsedStatus.textContent =
    payload.elapsed_seconds == null ? "00:00" : formatElapsed(payload.elapsed_seconds);
  els.phaseValue.textContent = payload.phase || "idle";
  els.backendLockValue.textContent = payload.backend_lock || "none";
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
  els.toolPanel.textContent = JSON.stringify(payload.latest_tool_call || {}, null, 2);
  els.proofPanel.textContent = `${payload.checker_status.status || "pending"}: ${
    payload.checker_status.message ||
    payload.checker_status.checker_log ||
    "Checker has not run yet."
  }`;
  renderArtifacts(payload.artifact_paths || []);
  renderViews(payload.latest_view_assets || {}, route);
  renderEvents(payload);
  renderControls(payload);
}

function renderControls(payload) {
  const controls = payload.controls || {};
  els.pauseButton.disabled = !controls.pause_available;
  els.stopButton.disabled = !controls.stop_available;
  els.emergencyButton.disabled = !controls.emergency_stop_required;
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
  const chaseEmptyText = routeHasOverviewChase(route)
    ? "No chase frame yet. Waiting for the first observation artifact."
    : "Chase view unavailable for this backend.";
  setImageSlot("chase", assets.chase, chaseEmptyText);
  setImageSlot("map", assets.map, "Map artifact has not been written yet.");
  setImageSlot("grounding", assets.grounding, "No grounding result yet.");
  ensureActiveViewAvailable(route);
  renderViewModes(route);
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
    map: "Map",
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
  const bits = [
    `phase=${payload.phase}`,
    payload.terminal_reason ? `reason=${payload.terminal_reason}` : "",
    `action=${payload.latest_action || "none"}`,
    `checker=${payload.checker_status.status || "pending"}`,
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
  return new Set(route.view_modes || ["overview", "fpv", "map", "outputs"]);
}

function routeHasOverviewChase(route, modes = routeViewModes(route)) {
  return Boolean(route && route.resource_kind !== "physical_robot" && modes.has("chase"));
}

function isAgibotRoute(route) {
  const groups = new Set((route && route.field_groups) || []);
  return Boolean(route && (route.backend === "agibot_gdk" || groups.has("agibot_gates")));
}

function selectedCodexProvider() {
  return els.codexProviderInput.value || "codex-env";
}

function selectedClaudeProvider() {
  return els.claudeProviderInput.value || "mimo-anthropic";
}

function selectedClaudeProviderLabel() {
  const option = Array.from(els.claudeProviderInput.options).find(
    (item) => item.value === selectedClaudeProvider()
  );
  return option ? option.textContent : selectedClaudeProvider();
}

function visiblePanelsForView(view, modes, route = state.selectedRoute) {
  if (view === "overview") {
    const panels = new Set(["fpv", "map"]);
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
  if (result.reason) {
    els.eventList.textContent = result.reason;
  }
  pollState();
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

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

boot();
