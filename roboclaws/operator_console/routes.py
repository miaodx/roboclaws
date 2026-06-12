"""Launch-axis registry for the standalone agent operator console."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from roboclaws.household.profiles import (
    CAMERA_GROUNDED_LABELS_LANE,
    SIM_PROJECTED_LABELS_CAMERA_LABELER,
    cleanup_evidence_lane_names,
)
from roboclaws.launch.agent_engines import AGENT_ENGINE_SPECS
from roboclaws.launch.backends import BACKEND_SPECS, BackendSpec
from roboclaws.launch.catalog import LaunchError, resolve_surface_launch
from roboclaws.launch.environment_setup import (
    ENVIRONMENT_SETUP_BASELINE,
    ENVIRONMENT_SETUP_RELOCATE_CLEANUP_RELATED_OBJECTS,
)
from roboclaws.launch.intents import TASK_INTENT_SPECS
from roboclaws.launch.worlds import MOLMOSPACES_CONSOLE_WORLD_IDS, WORLD_SPECS

DEFAULT_PROMPTS = {
    "cleanup": "帮我收拾这个房间",
    "map-build": "帮我建立这个房间的语义地图",
    "open-ended": "在这个场景中完成开放性导航任务，并报告你看到的证据。",
}

AGIBOT_CAMERA_LABELER = "grounding-dino"
SIMULATION_CAMERA_LABELER = SIM_PROJECTED_LABELS_CAMERA_LABELER

REAL_EVIDENCE_LANES = cleanup_evidence_lane_names()
ISAAC_SUPPORTED_EVIDENCE_LANES = tuple(
    lane for lane in REAL_EVIDENCE_LANES if lane != CAMERA_GROUNDED_LABELS_LANE
)
ISAAC_UNSUPPORTED_EVIDENCE_LANES = (CAMERA_GROUNDED_LABELS_LANE,)
MOLMOSPACES_DEFAULT_CLEANUP_TARGET_COUNT = 5
MOLMOSPACES_MUJOCO_DEFAULT_CLEANUP_WORLD_IDS = (
    "molmospaces/val_0",
    "molmospaces/val_2",
    "molmospaces/val_3",
    "molmospaces/val_4",
    "molmospaces/val_9",
)
MOLMOSPACES_ISAAC_ONE_TARGET_CLEANUP_WORLD_IDS = (
    "molmospaces/val_0",
    "molmospaces/val_1",
    "molmospaces/val_2",
    "molmospaces/val_3",
    "molmospaces/val_4",
    "molmospaces/val_5",
    "molmospaces/val_7",
    "molmospaces/val_9",
)


@dataclass(frozen=True)
class RouteGate:
    """A start gate surfaced to operators before a live robot run."""

    id: str
    label: str
    kind: str
    required: bool = True
    severity: str = "blocking"
    help_text: str = ""

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConsoleLaunchSelection:
    """Canonical operator-console launch selection."""

    world_id: str
    backend_id: str
    intent_id: str
    agent_engine_id: str
    provider_profile: str | None
    evidence_lane: str
    scenario_setup: str
    enabled: bool = True
    unsupported_reason: str = ""
    required_overrides: tuple[str, ...] = ()
    default_overrides: tuple[str, ...] = ()
    gates: tuple[RouteGate, ...] = ()
    supports_prompt: bool = True
    supports_operator_steer: bool = False
    pause_supported: bool = False
    emergency_stop_required: bool = False

    @property
    def id(self) -> str:
        return "::".join(
            (
                self.world_id,
                self.backend_id,
                self.intent_id,
                self.agent_engine_id,
                self.evidence_lane,
            )
        )

    @property
    def surface(self) -> str:
        return WORLD_SPECS[self.world_id].surface_id

    @property
    def backend(self) -> BackendSpec:
        return BACKEND_SPECS[self.backend_id]

    @property
    def lock_name(self) -> str:
        return self.backend.lock_name

    @property
    def resource_kind(self) -> str:
        return self.backend.resource_kind

    @property
    def checker_id(self) -> str:
        return TASK_INTENT_SPECS[self.intent_id].checker_id

    @property
    def task_prompt_default(self) -> str:
        return DEFAULT_PROMPTS.get(self.intent_id, "")

    @property
    def launch_default_overrides(self) -> tuple[str, ...]:
        return (
            *WORLD_SPECS[self.world_id].default_overrides,
            *BACKEND_SPECS[self.backend_id].default_overrides,
            *self.default_overrides,
        )

    @property
    def label(self) -> str:
        world = WORLD_SPECS[self.world_id].label
        backend = self.backend.label
        intent = _intent_label(self.intent_id)
        engine = AGENT_ENGINE_SPECS[self.agent_engine_id].label
        return f"{world} / {backend} / {intent} / {engine}"

    @property
    def disabled_reason(self) -> str:
        return self.unsupported_reason

    def base_args(self) -> list[str]:
        args = [
            f"surface={self.surface}",
            f"world={self.world_id}",
            f"backend={self.backend_id}",
            f"intent={self.intent_id}",
            f"agent_engine={self.agent_engine_id}",
            f"evidence_lane={self.evidence_lane}",
            f"scenario_setup={self.scenario_setup}",
            *self.launch_default_overrides,
        ]
        if self.provider_profile:
            args.append(f"provider_profile={self.provider_profile}")
        return args

    def to_payload(self) -> dict[str, Any]:
        world = WORLD_SPECS[self.world_id]
        backend = self.backend
        engine = AGENT_ENGINE_SPECS[self.agent_engine_id]
        payload = {
            "id": self.id,
            "label": self.label,
            "world_id": self.world_id,
            "world_label": world.label,
            "backend_id": self.backend_id,
            "backend_label": backend.label,
            "intent_id": self.intent_id,
            "intent": self.intent_id,
            "agent_engine_id": self.agent_engine_id,
            "agent_engine_label": engine.label,
            "provider_profile": self.provider_profile or "",
            "evidence_lane": self.evidence_lane,
            "scenario_setup": self.scenario_setup,
            "surface": self.surface,
            "enabled": self.enabled,
            "unsupported_reason": self.unsupported_reason,
            "checker_id": self.checker_id,
            "lock_name": backend.lock_name,
            "resource_kind": backend.resource_kind,
            "supports_prompt": self.supports_prompt,
            "supports_operator_steer": self.supports_operator_steer,
            "pause_supported": self.pause_supported,
            "emergency_stop_required": self.emergency_stop_required,
            "required_overrides": list(self.required_overrides),
            "default_overrides": list(self.default_overrides),
            "launch_default_overrides": list(self.launch_default_overrides),
            "preview_assets": _preview_assets_payload(world.preview_assets),
            "gates": [gate.to_payload() for gate in self.gates],
            "required_gates": [gate.to_payload() for gate in self.gates if gate.required],
            "state": "enabled" if self.enabled else "disabled",
            "blocker": self.unsupported_reason,
            "default_prompt": self.task_prompt_default,
            "prompt_disabled_reason": (
                ""
                if self.supports_prompt
                else (
                    "This selection cannot accept a custom prompt safely. "
                    "Use the default task prompt."
                )
            ),
            "field_groups": list(backend.field_groups),
            "view_modes": list(backend.view_modes),
            "argv_preview": ["just", "run::surface", *self.base_args()],
            "command_preview": ["just", "run::surface", *self.base_args()],
            "intent_options": [_intent_option(self.intent_id)],
            "default_intent": self.intent_id,
            "supported_intents": [self.intent_id],
        }
        return payload


@dataclass(frozen=True)
class ConsoleRoute:
    """Legacy display wrapper for older route-id history records."""

    id: str
    label: str
    selection: ConsoleLaunchSelection

    def to_payload(self) -> dict[str, Any]:
        payload = self.selection.to_payload()
        payload["legacy_route_id"] = self.id
        payload["id"] = self.id
        payload["label"] = self.label
        return payload

    @property
    def surface(self) -> str:
        return self.selection.surface

    @property
    def intent(self) -> str:
        return self.selection.intent_id

    @property
    def driver(self) -> str:
        return AGENT_ENGINE_SPECS[self.selection.agent_engine_id].dispatch_runner

    @property
    def driver_label(self) -> str:
        return AGENT_ENGINE_SPECS[self.selection.agent_engine_id].label

    @property
    def profile(self) -> str:
        return self.selection.evidence_lane

    @property
    def backend(self) -> str:
        return self.selection.backend.implementation_backend

    @property
    def default_overrides(self) -> tuple[str, ...]:
        return self.selection.default_overrides

    @property
    def launch_default_overrides(self) -> tuple[str, ...]:
        return self.selection.launch_default_overrides

    @property
    def required_overrides(self) -> tuple[str, ...]:
        return self.selection.required_overrides

    @property
    def gates(self) -> tuple[RouteGate, ...]:
        return self.selection.gates

    @property
    def enabled(self) -> bool:
        return self.selection.enabled

    @property
    def disabled_reason(self) -> str:
        return self.selection.disabled_reason

    @property
    def lock_name(self) -> str:
        return self.selection.lock_name

    @property
    def supports_prompt(self) -> bool:
        return self.selection.supports_prompt

    @property
    def supports_operator_steer(self) -> bool:
        return self.selection.supports_operator_steer

    @property
    def pause_supported(self) -> bool:
        return self.selection.pause_supported

    @property
    def emergency_stop_required(self) -> bool:
        return self.selection.emergency_stop_required

    @property
    def resource_kind(self) -> str:
        return self.selection.resource_kind

    @property
    def checker_id(self) -> str:
        return self.selection.checker_id

    @property
    def task_prompt_default(self) -> str:
        return self.selection.task_prompt_default

    def __getattr__(self, name: str) -> Any:
        return getattr(self.selection, name)


PROVIDER_KEY_GATE = RouteGate(
    id="provider_key",
    label="Agent provider route present",
    kind="provider_key",
    help_text="Load a repo-local coding-agent provider route before launch.",
)
MCP_PORT_FREE_GATE = RouteGate(
    id="mcp_port_free",
    label="MCP port available",
    kind="mcp_port_free",
    help_text="The runner will start its MCP server on this host and port.",
)
ISAAC_PREFLIGHT_GATE = RouteGate(
    id="isaac_preflight",
    label="Isaac runtime diagnostic",
    kind="isaac_preflight",
    required=False,
    severity="advisory",
    help_text=(
        "Shows recent Isaac runtime preflight/smoke evidence when present; "
        "launch can start without a manual acceptance marker."
    ),
)
AGIBOT_CONTEXT_GATE = RouteGate(
    id="context_json",
    label="Agibot map context JSON attached",
    kind="request_field",
    help_text="Attach a completed Agibot map context JSON.",
)
AGIBOT_LOCALIZATION_GATE = RouteGate(
    id="localization_ready",
    label="Localization available for real movement",
    kind="operator_gate",
    required=False,
    severity="capability",
    help_text="Required only when real movement is enabled.",
)
AGIBOT_ENABLEMENT_GATE = RouteGate(
    id="run_enabled",
    label="Run enablement available for real movement",
    kind="operator_gate",
    required=False,
    severity="capability",
    help_text="Required only when real movement is enabled.",
)
AGIBOT_ESTOP_GATE = RouteGate(
    id="estop_ready",
    label="E-stop/manual-stop visible for real movement",
    kind="operator_gate",
    required=False,
    severity="capability",
    help_text="Required only when real movement is enabled.",
)


def list_worlds(*, include_hidden: bool = False) -> tuple[dict[str, Any], ...]:
    """Return searchable world/scene metadata for the console rail."""

    rows = []
    for world in WORLD_SPECS.values():
        if world.availability == "hidden" and not include_hidden:
            continue
        rows.append(
            {
                "id": world.id,
                "label": world.label,
                "surface_id": world.surface_id,
                "available_backends": list(world.available_backends),
                "scene_source": world.scene_source,
                "tags": list(world.tags),
                "default_backend": world.default_backend,
                "resource_kind": world.resource_kind,
                "availability": world.availability,
                "preview_assets": _preview_assets_payload(world.preview_assets),
            }
        )
    return tuple(rows)


def list_evidence_lanes() -> tuple[dict[str, str], ...]:
    """Return the full operator-visible household evidence-lane list."""

    return tuple(
        {
            "id": lane,
            "label": lane,
        }
        for lane in cleanup_evidence_lane_names()
    )


def _preview_assets_payload(items: tuple[tuple[str, str], ...]) -> dict[str, dict[str, str]]:
    return {name: {"path": path, "href": path} for name, path in items}


def list_console_combinations(
    *, include_disabled: bool = True
) -> tuple[ConsoleLaunchSelection, ...]:
    """Return the catalog-backed console support matrix."""

    rows = _enabled_combinations()
    disabled = _disabled_combinations()
    if include_disabled:
        return (*rows, *disabled)
    return rows


def get_selection(selection_id: str) -> ConsoleLaunchSelection:
    for selection in list_console_combinations(include_disabled=True):
        if selection.id == selection_id:
            return selection
    legacy = _LEGACY_ROUTE_BY_ID.get(selection_id)
    if legacy:
        return legacy.selection
    raise KeyError(selection_id)


def list_console_routes(*, include_disabled: bool = True) -> tuple[ConsoleRoute, ...]:
    """Return legacy route wrappers for old callers."""

    routes = tuple(_LEGACY_ROUTE_BY_ID.values())
    if include_disabled:
        return routes
    return tuple(route for route in routes if route.selection.enabled)


def get_route(route_id: str) -> ConsoleRoute:
    route = _LEGACY_ROUTE_BY_ID.get(route_id)
    if route:
        return route
    selection = get_selection(route_id)
    return ConsoleRoute(id=selection.id, label=selection.label, selection=selection)


def validate_supported_routes_against_catalog() -> None:
    """Fail if supported console combinations drift away from launch catalog."""

    for selection in list_console_combinations(include_disabled=False):
        try:
            resolve_surface_launch(selection.base_args())
        except LaunchError as exc:  # pragma: no cover - assertion context
            raise AssertionError(f"invalid console selection {selection.id}: {exc}") from exc


def accepted_isaac_preflight(root: Path) -> Path | None:
    """Return the newest accepted Isaac proof marker, if one exists."""

    candidates = [
        root / "output" / "isaaclab" / "runtime-preflight-accepted.json",
        root / "output" / "isaaclab" / "runtime-smoke-accepted.json",
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return None
    return max(existing, key=lambda path: path.stat().st_mtime)


def _common_gates() -> tuple[RouteGate, ...]:
    return (PROVIDER_KEY_GATE, MCP_PORT_FREE_GATE)


def _enabled_combinations() -> tuple[ConsoleLaunchSelection, ...]:
    common_gates = _common_gates()
    return (
        *_molmospaces_enabled_combinations(),
        *_lane_selections(
            "agibot-g2/map-12",
            "agibot-gdk",
            "map-build",
            "codex-cli",
            "codex-env",
            camera_labeler=AGIBOT_CAMERA_LABELER,
            scenario_setup=ENVIRONMENT_SETUP_BASELINE,
            gates=(
                *common_gates,
                AGIBOT_CONTEXT_GATE,
                AGIBOT_LOCALIZATION_GATE,
                AGIBOT_ENABLEMENT_GATE,
                AGIBOT_ESTOP_GATE,
            ),
            required_overrides=("context_json",),
            default_overrides=(
                "policy=codex_agibot_semantic_map_build_pilot",
                "visual_grounding_timeout_s=20",
            ),
            emergency_stop_required=True,
        ),
        *_lane_selections(
            "b1-map12",
            "isaaclab",
            "open-ended",
            "codex-cli",
            "codex-env",
            evidence_lanes=ISAAC_SUPPORTED_EVIDENCE_LANES,
            scenario_setup=ENVIRONMENT_SETUP_BASELINE,
            gates=(*common_gates, ISAAC_PREFLIGHT_GATE),
            default_overrides=("seed=7",),
            supports_operator_steer=True,
        ),
    )


def _molmospaces_enabled_combinations() -> tuple[ConsoleLaunchSelection, ...]:
    rows: list[ConsoleLaunchSelection] = []
    common_gates = _common_gates()
    for world_id in MOLMOSPACES_CONSOLE_WORLD_IDS:
        if world_id in MOLMOSPACES_MUJOCO_DEFAULT_CLEANUP_WORLD_IDS:
            rows.extend(
                _lane_selections(
                    world_id,
                    "mujoco",
                    "cleanup",
                    "codex-cli",
                    "codex-env",
                    gates=common_gates,
                    default_overrides=("seed=7",),
                    supports_operator_steer=True,
                )
            )
            rows.extend(
                _lane_selections(
                    world_id,
                    "mujoco",
                    "cleanup",
                    "claude-code",
                    "mimo-anthropic",
                    gates=common_gates,
                    default_overrides=("seed=7",),
                    supports_operator_steer=True,
                )
            )
            rows.extend(
                _lane_selections(
                    world_id,
                    "mujoco",
                    "cleanup",
                    "openai-agents-sdk",
                    "codex-env",
                    gates=common_gates,
                    default_overrides=("seed=7",),
                    supports_operator_steer=True,
                )
            )
        rows.extend(
            _lane_selections(
                world_id,
                "mujoco",
                "map-build",
                "codex-cli",
                "codex-env",
                scenario_setup=ENVIRONMENT_SETUP_BASELINE,
                gates=common_gates,
                default_overrides=("seed=7",),
            )
        )
        rows.extend(
            _lane_selections(
                world_id,
                "mujoco",
                "open-ended",
                "codex-cli",
                "codex-env",
                scenario_setup=ENVIRONMENT_SETUP_BASELINE,
                gates=common_gates,
                default_overrides=("seed=7",),
                supports_operator_steer=True,
            )
        )
        rows.extend(
            _lane_selections(
                world_id,
                "mujoco",
                "open-ended",
                "claude-code",
                "mimo-anthropic",
                scenario_setup=ENVIRONMENT_SETUP_BASELINE,
                gates=common_gates,
                default_overrides=("seed=7",),
                supports_operator_steer=True,
            )
        )
        rows.extend(
            _lane_selections(
                world_id,
                "mujoco",
                "map-build",
                "direct-runner",
                None,
                scenario_setup=ENVIRONMENT_SETUP_BASELINE,
                gates=(MCP_PORT_FREE_GATE,),
                default_overrides=("seed=7",),
            )
        )
        if world_id in MOLMOSPACES_ISAAC_ONE_TARGET_CLEANUP_WORLD_IDS:
            rows.extend(
                _lane_selections(
                    world_id,
                    "isaaclab",
                    "cleanup",
                    "codex-cli",
                    "codex-env",
                    evidence_lanes=ISAAC_SUPPORTED_EVIDENCE_LANES,
                    gates=(*common_gates, ISAAC_PREFLIGHT_GATE),
                    default_overrides=("seed=7", "relocation_count=1"),
                    supports_operator_steer=True,
                )
            )
            rows.extend(
                _lane_selections(
                    world_id,
                    "isaaclab",
                    "cleanup",
                    "claude-code",
                    "mimo-anthropic",
                    evidence_lanes=ISAAC_SUPPORTED_EVIDENCE_LANES,
                    gates=(*common_gates, ISAAC_PREFLIGHT_GATE),
                    default_overrides=("seed=7", "relocation_count=1"),
                    supports_operator_steer=True,
                )
            )
        rows.extend(
            _lane_selections(
                world_id,
                "isaaclab",
                "map-build",
                "codex-cli",
                "codex-env",
                evidence_lanes=ISAAC_SUPPORTED_EVIDENCE_LANES,
                scenario_setup=ENVIRONMENT_SETUP_BASELINE,
                gates=(*common_gates, ISAAC_PREFLIGHT_GATE),
                default_overrides=("seed=7",),
            )
        )
    return tuple(rows)


def _disabled_combinations() -> tuple[ConsoleLaunchSelection, ...]:
    return (
        *_disabled_molmospaces_cleanup_combinations(),
        *_lane_selections(
            "molmospaces/val_0",
            "isaaclab",
            "cleanup",
            "codex-cli",
            "codex-env",
            evidence_lanes=ISAAC_UNSUPPORTED_EVIDENCE_LANES,
            enabled=False,
            unsupported_reason=(
                "Isaac Lab camera-grounded labels are not wired yet; use world labels or raw FPV."
            ),
            gates=(*_common_gates(), ISAAC_PREFLIGHT_GATE),
            default_overrides=("seed=7", "relocation_count=1"),
            supports_operator_steer=True,
        ),
        *_lane_selections(
            "molmospaces/val_0",
            "isaaclab",
            "cleanup",
            "claude-code",
            "mimo-anthropic",
            evidence_lanes=ISAAC_UNSUPPORTED_EVIDENCE_LANES,
            enabled=False,
            unsupported_reason=(
                "Isaac Lab camera-grounded labels are not wired yet; use world labels or raw FPV."
            ),
            gates=(*_common_gates(), ISAAC_PREFLIGHT_GATE),
            default_overrides=("seed=7", "relocation_count=1"),
            supports_operator_steer=True,
        ),
        *_lane_selections(
            "molmospaces/val_0",
            "isaaclab",
            "map-build",
            "codex-cli",
            "codex-env",
            evidence_lanes=ISAAC_UNSUPPORTED_EVIDENCE_LANES,
            scenario_setup=ENVIRONMENT_SETUP_BASELINE,
            enabled=False,
            unsupported_reason=(
                "Isaac Lab camera-grounded labels are not wired yet; use world labels or raw FPV."
            ),
            gates=(*_common_gates(), ISAAC_PREFLIGHT_GATE),
            default_overrides=("seed=7",),
        ),
        *_lane_selections(
            "b1-map12",
            "isaaclab",
            "open-ended",
            "codex-cli",
            "codex-env",
            evidence_lanes=ISAAC_UNSUPPORTED_EVIDENCE_LANES,
            scenario_setup=ENVIRONMENT_SETUP_BASELINE,
            enabled=False,
            unsupported_reason=(
                "Isaac Lab camera-grounded labels are not wired yet; use world labels or raw FPV."
            ),
            gates=(*_common_gates(), ISAAC_PREFLIGHT_GATE),
            default_overrides=("seed=7",),
            supports_operator_steer=True,
        ),
        _selection(
            "agibot-g2/map-12",
            "agibot-gdk",
            "cleanup",
            "codex-cli",
            "codex-env",
            evidence_lane="camera-grounded-labels",
            enabled=False,
            unsupported_reason=(
                "Physical manipulation is not available yet. Run Agibot G2 Map Build first."
            ),
            supports_prompt=False,
            emergency_stop_required=True,
        ),
        _selection(
            "molmospaces/val_0",
            "mujoco",
            "map-build",
            "claude-code",
            "mimo-anthropic",
            enabled=False,
            unsupported_reason=(
                "Map-build is currently proven for Codex CLI and direct runner only."
            ),
        ),
        _selection(
            "molmospaces/val_0",
            "mujoco",
            "open-ended",
            "openai-agents-sdk",
            "codex-env",
            enabled=False,
            unsupported_reason="OpenAI Agents SDK is not proven for open-ended household runs yet.",
        ),
    )


def _disabled_molmospaces_cleanup_combinations() -> tuple[ConsoleLaunchSelection, ...]:
    rows: list[ConsoleLaunchSelection] = []
    for world_id in MOLMOSPACES_CONSOLE_WORLD_IDS:
        if world_id not in MOLMOSPACES_MUJOCO_DEFAULT_CLEANUP_WORLD_IDS:
            reason = (
                "This scene does not expose at least "
                f"{MOLMOSPACES_DEFAULT_CLEANUP_TARGET_COUNT} generated cleanup targets "
                "under the current cleanup rules. Use Map Build or choose a cleanup-ready scene."
            )
            for agent_engine_id, provider_profile in (
                ("codex-cli", "codex-env"),
                ("claude-code", "mimo-anthropic"),
                ("openai-agents-sdk", "codex-env"),
            ):
                rows.extend(
                    _lane_selections(
                        world_id,
                        "mujoco",
                        "cleanup",
                        agent_engine_id,
                        provider_profile,
                        enabled=False,
                        unsupported_reason=reason,
                        gates=_common_gates(),
                        default_overrides=("seed=7",),
                        supports_operator_steer=True,
                    )
                )
        if world_id not in MOLMOSPACES_ISAAC_ONE_TARGET_CLEANUP_WORLD_IDS:
            reason = (
                "This scene has no generated cleanup targets under the current cleanup rules. "
                "Use Map Build or choose a cleanup-ready scene."
            )
            for agent_engine_id, provider_profile in (
                ("codex-cli", "codex-env"),
                ("claude-code", "mimo-anthropic"),
            ):
                rows.extend(
                    _lane_selections(
                        world_id,
                        "isaaclab",
                        "cleanup",
                        agent_engine_id,
                        provider_profile,
                        evidence_lanes=ISAAC_SUPPORTED_EVIDENCE_LANES,
                        enabled=False,
                        unsupported_reason=reason,
                        gates=(*_common_gates(), ISAAC_PREFLIGHT_GATE),
                        default_overrides=("seed=7", "relocation_count=1"),
                        supports_operator_steer=True,
                    )
                )
    return tuple(rows)


def _selection(
    world_id: str,
    backend_id: str,
    intent_id: str,
    agent_engine_id: str,
    provider_profile: str | None,
    *,
    evidence_lane: str = "world-oracle-labels",
    scenario_setup: str | None = None,
    enabled: bool = True,
    unsupported_reason: str = "",
    required_overrides: tuple[str, ...] = (),
    default_overrides: tuple[str, ...] = (),
    gates: tuple[RouteGate, ...] = (),
    supports_prompt: bool = True,
    supports_operator_steer: bool = False,
    pause_supported: bool = False,
    emergency_stop_required: bool = False,
) -> ConsoleLaunchSelection:
    setup = scenario_setup or (
        ENVIRONMENT_SETUP_RELOCATE_CLEANUP_RELATED_OBJECTS
        if intent_id == "cleanup"
        else ENVIRONMENT_SETUP_BASELINE
    )
    return ConsoleLaunchSelection(
        world_id=world_id,
        backend_id=backend_id,
        intent_id=intent_id,
        agent_engine_id=agent_engine_id,
        provider_profile=provider_profile,
        evidence_lane=evidence_lane,
        scenario_setup=setup,
        enabled=enabled,
        unsupported_reason=unsupported_reason,
        required_overrides=required_overrides,
        default_overrides=default_overrides,
        gates=gates,
        supports_prompt=supports_prompt,
        supports_operator_steer=supports_operator_steer,
        pause_supported=pause_supported,
        emergency_stop_required=emergency_stop_required,
    )


def _lane_selections(
    world_id: str,
    backend_id: str,
    intent_id: str,
    agent_engine_id: str,
    provider_profile: str | None,
    *,
    evidence_lanes: tuple[str, ...] = REAL_EVIDENCE_LANES,
    camera_labeler: str = SIMULATION_CAMERA_LABELER,
    scenario_setup: str | None = None,
    enabled: bool = True,
    unsupported_reason: str = "",
    required_overrides: tuple[str, ...] = (),
    default_overrides: tuple[str, ...] = (),
    gates: tuple[RouteGate, ...] = (),
    supports_prompt: bool = True,
    supports_operator_steer: bool = False,
    pause_supported: bool = False,
    emergency_stop_required: bool = False,
) -> tuple[ConsoleLaunchSelection, ...]:
    rows: list[ConsoleLaunchSelection] = []
    for evidence_lane in evidence_lanes:
        lane_default_overrides = default_overrides
        if evidence_lane == CAMERA_GROUNDED_LABELS_LANE:
            lane_default_overrides = (
                *lane_default_overrides,
                f"camera_labeler={camera_labeler}",
            )
        rows.append(
            _selection(
                world_id,
                backend_id,
                intent_id,
                agent_engine_id,
                provider_profile,
                evidence_lane=evidence_lane,
                scenario_setup=scenario_setup,
                enabled=enabled,
                unsupported_reason=unsupported_reason,
                required_overrides=required_overrides,
                default_overrides=lane_default_overrides,
                gates=gates,
                supports_prompt=supports_prompt,
                supports_operator_steer=supports_operator_steer,
                pause_supported=pause_supported,
                emergency_stop_required=emergency_stop_required,
            )
        )
    return tuple(rows)


_LEGACY_ROUTE_BY_ID: dict[str, ConsoleRoute] = {
    "codex-mujoco-cleanup": ConsoleRoute(
        id="codex-mujoco-cleanup",
        label="MolmoSpaces val_0 / MuJoCo / Cleanup / Codex CLI",
        selection=get_selection(
            "molmospaces/val_0::mujoco::cleanup::codex-cli::world-oracle-labels"
        ),
    ),
    "claude-mujoco-cleanup": ConsoleRoute(
        id="claude-mujoco-cleanup",
        label="MolmoSpaces val_0 / MuJoCo / Cleanup / Claude Code",
        selection=get_selection(
            "molmospaces/val_0::mujoco::cleanup::claude-code::world-oracle-labels"
        ),
    ),
    "codex-isaac-cleanup": ConsoleRoute(
        id="codex-isaac-cleanup",
        label="MolmoSpaces val_0 / Isaac Lab / Cleanup / Codex CLI",
        selection=get_selection(
            "molmospaces/val_0::isaaclab::cleanup::codex-cli::world-oracle-labels"
        ),
    ),
    "claude-isaac-cleanup": ConsoleRoute(
        id="claude-isaac-cleanup",
        label="MolmoSpaces val_0 / Isaac Lab / Cleanup / Claude Code",
        selection=get_selection(
            "molmospaces/val_0::isaaclab::cleanup::claude-code::world-oracle-labels"
        ),
    ),
    "codex-agibot-g2-map-build": ConsoleRoute(
        id="codex-agibot-g2-map-build",
        label="Agibot G2 Map 12 / Agibot GDK / Map Build / Codex CLI",
        selection=get_selection(
            "agibot-g2/map-12::agibot-gdk::map-build::codex-cli::camera-grounded-labels"
        ),
    ),
    "codex-mujoco-map-build": ConsoleRoute(
        id="codex-mujoco-map-build",
        label="MolmoSpaces val_0 / MuJoCo / Map Build / Codex CLI",
        selection=get_selection(
            "molmospaces/val_0::mujoco::map-build::codex-cli::world-oracle-labels"
        ),
    ),
    "codex-isaac-map-build": ConsoleRoute(
        id="codex-isaac-map-build",
        label="MolmoSpaces val_0 / Isaac Lab / Map Build / Codex CLI",
        selection=get_selection(
            "molmospaces/val_0::isaaclab::map-build::codex-cli::world-oracle-labels"
        ),
    ),
    "codex-b1-map12-open-ended": ConsoleRoute(
        id="codex-b1-map12-open-ended",
        label="B1 / Map 12 / Isaac Lab / Open-ended / Codex CLI",
        selection=get_selection("b1-map12::isaaclab::open-ended::codex-cli::world-oracle-labels"),
    ),
    "agibot-g2-cleanup": ConsoleRoute(
        id="agibot-g2-cleanup",
        label="Agibot G2 Map 12 / Agibot GDK / Cleanup / Codex CLI",
        selection=get_selection(
            "agibot-g2/map-12::agibot-gdk::cleanup::codex-cli::camera-grounded-labels"
        ),
    ),
}


def _intent_option(intent_id: str) -> dict[str, str]:
    spec = TASK_INTENT_SPECS.get(intent_id)
    if spec is None:
        return {
            "id": intent_id,
            "label": _intent_label(intent_id),
            "prompt_id": "",
            "checker_id": "",
            "goal_scope": "",
            "evaluation_policy": "",
            "done_readiness_policy": "",
            "checker_policy": "",
        }
    return {
        "id": intent_id,
        "label": _intent_label(intent_id),
        "prompt_id": spec.prompt_id,
        "checker_id": spec.checker_id,
        "goal_scope": spec.default_goal_scope,
        "evaluation_policy": spec.evaluation_policy,
        "done_readiness_policy": spec.done_readiness_policy,
        "checker_policy": spec.checker_policy,
    }


def _intent_label(intent_id: str) -> str:
    return {
        "cleanup": "Cleanup",
        "open-ended": "Open-ended",
        "map-build": "Map build",
    }.get(intent_id, intent_id.replace("-", " ").title())
