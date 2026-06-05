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

const els = {
  routeList: document.getElementById("route-list"),
  taskPrompt: document.getElementById("prompt-input"),
  promptHelp: document.getElementById("prompt-copy"),
  promptCount: document.getElementById("char-count"),
  seedInput: document.getElementById("seed-input"),
  messInput: document.getElementById("mess-count-input"),
  portInput: document.getElementById("port-input"),
  selectedRouteSummary: document.getElementById("selected-route-summary"),
  commonFields: document.getElementById("common-fields"),
  isaacFields: document.getElementById("isaac-fields"),
  agibotFields: document.getElementById("agibot-fields"),
  agibotGateFields: document.getElementById("agibot-gate-fields"),
  contextInput: document.getElementById("context-json-input"),
  isaacSceneInput: document.getElementById("isaac-scene-input"),
  isaacPreflightGate: document.getElementById("isaac-preflight-gate"),
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
  confirmDialog: document.getElementById("confirm-dialog"),
  confirmTitle: document.getElementById("confirm-title"),
  confirmAction: document.getElementById("confirm-action"),
  confirmBody: document.getElementById("confirm-body"),
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
    els.portInput,
    els.isaacPreflightGate,
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
  els.startButton.addEventListener("click", confirmLaunch);
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
  document.querySelectorAll(".view-mode").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeView = button.dataset.view;
      renderViewModes();
    });
  });
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
    const row = document.createElement("div");
    row.className = "gate-row";
    row.innerHTML = `
      <span>${escapeHtml(gate.label)}</span>
      <span class="badge ${gateReady ? "ready" : "needs_action"}">
        ${gateReady ? "Ready" : "Needs Action"}
      </span>
    `;
    els.gateList.appendChild(row);
  }
  if (!gates.length) {
    els.gateList.textContent = "No route-specific gates.";
  }

  els.commandPreview.textContent = commandPreview(route);
  els.startButton.disabled = !route.enabled || readiness.can_start === false;
  els.startHelp.textContent = readiness.blocker || route.disabled_reason || "";
}

function routeStatusDisplay(route, readiness) {
  if (!route.enabled) {
    return { label: "UNAVAILABLE", className: "blocked" };
  }
  if (readiness.can_start !== false) {
    return { label: "READY", className: "ready" };
  }
  const kind = readiness.blocker_kind || "";
  if (kind === "locked") return { label: "LOCKED", className: "blocked" };
  if (kind === "mcp_port_in_use") return { label: "PORT IN USE", className: "blocked" };
  if (kind === "needs_provider") return { label: "NEEDS PROVIDER", className: "needs_action" };
  if (kind === "needs_isaac_preflight") {
    return { label: "NEEDS PREFLIGHT", className: "needs_action" };
  }
  if (kind === "needs_agibot_context" || kind === "needs_agibot_gates") {
    return { label: "NEEDS OPERATOR GATES", className: "needs_action" };
  }
  return { label: "NEEDS ACTION", className: "needs_action" };
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
  const lockBlocked = base.lock && base.lock.held && !base.lock.stale;
  let blocker = "";

  if (!route.enabled) {
    return { can_start: false, blocker: route.disabled_reason || "", gates };
  }
  if (lockBlocked) {
    blocker = "Backend lock is held by another run. Open that run or wait for it to finish.";
  }

  for (const gate of gates) {
    applyLocalGateEvidence(gate);
    if (gate.status !== "ready" && !blocker) {
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
    (gate.id === "isaac_preflight" && els.isaacPreflightGate.checked) ||
    (gate.id === "context_json" && Boolean(els.contextInput.value.trim())) ||
    (gate.id === "localization_ready" && els.localizationGate.checked) ||
    (gate.id === "run_enabled" && els.enablementGate.checked) ||
    (gate.id === "estop_ready" && els.estopGate.checked);

  if (!localReady) {
    return;
  }
  gate.status = "ready";
  gate.message = "Operator evidence accepted for this launch.";
}

function firstBlockingGateKind(gates) {
  const gate = gates.find((item) => item.status !== "ready");
  return gate ? gate.kind || "" : "";
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
      isaac_preflight: els.isaacPreflightGate.checked,
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
}

function renderRunState(payload) {
  const route = payload.route || state.selectedRoute || {};
  document.querySelector(".top-run-bar").classList.add("run-active");
  els.runTitle.textContent = `${route.label || "Agent run"} / ${payload.run_id}`;
  els.routeStatus.textContent = payload.phase || payload.status || "Running";
  els.routeStatus.className = `badge ${statusClass(payload.phase || payload.status)}`;
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
    payload.checker_status.checker_log || "Checker has not run yet."
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
  setImageSlot("chase", assets.chase, "Chase view unavailable for this backend.");
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
  slot.innerHTML = `<img alt="${name} artifact" src="${asset.href || artifactHref(asset.path)}" />`;
}

function renderEvents(payload) {
  const bits = [
    `phase=${payload.phase}`,
    `action=${payload.latest_action || "none"}`,
    `checker=${payload.checker_status.status || "pending"}`,
    `outputs=${payload.run_dir}`,
  ];
  els.eventList.textContent = bits.join("  ");
}

function renderViewModes(route = state.selectedRoute) {
  const visualGrid = document.getElementById("visual-grid");
  if (!visualGrid || !route) {
    return;
  }
  const modes = routeViewModes(route);
  const hasGrounding = modes.has("grounding");
  const activeView = state.activeView || "overview";
  visualGrid.className = `view-grid mode-${activeView}${hasGrounding ? "" : " no-grounding"}`;

  document.querySelectorAll(".view-mode").forEach((button) => {
    const enabled = modes.has(button.dataset.view);
    button.hidden = !enabled;
    button.classList.toggle("active", enabled && button.dataset.view === activeView);
  });

  const visiblePanels = visiblePanelsForView(activeView, modes);
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

function isAgibotRoute(route) {
  const groups = new Set((route && route.field_groups) || []);
  return Boolean(route && (route.backend === "agibot_gdk" || groups.has("agibot_gates")));
}

function visiblePanelsForView(view, modes) {
  if (view === "overview") {
    const panels = new Set(["fpv", "map"]);
    if (modes.has("grounding")) {
      panels.add("grounding");
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
  els.toggleRawButton.textContent = hidden ? "Hide Raw Evidence" : "Show Raw Evidence";
  if (hidden) {
    const driver = (state.activeState.artifact_paths || []).find(
      (item) => item.label === "Driver Log"
    );
    const text = driver
      ? await fetch(`/api/raw/${encodeURI(driver.path)}`).then((response) => response.text())
      : "";
    els.rawEvidence.textContent = text || "No raw driver log yet.";
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
