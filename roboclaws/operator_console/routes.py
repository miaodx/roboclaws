"""Explicit route registry for the standalone agent operator console."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from roboclaws.launch.catalog import resolve_surface_launch
from roboclaws.launch.environment_setup import (
    ENVIRONMENT_SETUP_BASELINE,
    ENVIRONMENT_SETUP_RELOCATE_CLEANUP_RELATED_OBJECTS,
)
from roboclaws.launch.intents import TASK_INTENT_SPECS

B1_MAP12_BUNDLE = "agibot-robot-map-12"
B1_MAP12_LIVINGROOM_USD = (
    "data/robot-data-lab/scene-engine/data/B1_floor2_slow/"
    "usda/livingroom/livingroom_usdz_unpacked/livingroom.usda"
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
class ConsoleRoute:
    """One route card in the local operator console."""

    id: str
    label: str
    task: str
    surface: str
    intent: str
    driver: str
    profile: str
    backend: str
    lock_name: str
    supports_prompt: bool
    enabled: bool
    checker_id: str
    task_prompt_default: str
    supported_intents: tuple[str, ...] = ()
    required_overrides: tuple[str, ...] = ()
    default_overrides: tuple[str, ...] = ()
    gates: tuple[RouteGate, ...] = ()
    disabled_reason: str = ""
    pause_supported: bool = False
    emergency_stop_required: bool = False
    supports_operator_steer: bool = False
    resource_kind: str = "simulator"
    driver_label: str = ""
    driver_family: str = "coding_agent"
    field_groups: tuple[str, ...] = ()
    view_modes: tuple[str, ...] = ()

    def supported_intent_ids(self) -> tuple[str, ...]:
        return self.supported_intents or (self.intent,)

    def selected_intent(self, intent: str = "") -> str:
        selected = str(intent or self.intent).strip()
        if selected.startswith("intent="):
            selected = selected.removeprefix("intent=")
        if selected not in self.supported_intent_ids():
            supported = "|".join(self.supported_intent_ids())
            raise ValueError(
                f"unsupported intent '{selected}' for route '{self.id}'; expected {supported}"
            )
        return selected

    def base_args(self, *, intent: str = "") -> list[str]:
        selected_intent = self.selected_intent(intent)
        return [
            f"surface={self.surface}",
            f"driver={self.driver}",
            f"intent={selected_intent}",
            f"evidence_lane={self.profile}",
            f"backend={self.backend}",
            *self.default_overrides,
        ]

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["argv_preview"] = ["just", "run::surface", *self.base_args()]
        payload["command_preview"] = payload["argv_preview"]
        payload["default_intent"] = self.intent
        payload["supported_intents"] = list(self.supported_intent_ids())
        payload["intent_options"] = [
            _intent_option(intent_id) for intent_id in self.supported_intent_ids()
        ]
        payload["gates"] = [gate.to_payload() for gate in self.gates]
        payload["required_gates"] = [gate for gate in payload["gates"] if gate["required"]]
        payload["state"] = "enabled" if self.enabled else "disabled"
        payload["blocker"] = self.disabled_reason
        payload["prompt_disabled_reason"] = (
            ""
            if self.supports_prompt
            else "This route cannot accept a custom prompt safely. Use the default task prompt."
        )
        payload["default_prompt"] = self.task_prompt_default
        payload["driver_label"] = self.driver_label or self.driver.title()
        payload["field_groups"] = list(self.field_groups or _default_field_groups(self))
        payload["view_modes"] = list(self.view_modes or _default_view_modes(self))
        return payload


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


def _cleanup_route(
    *,
    route_id: str,
    label: str,
    driver: str,
    backend: str,
    lock_name: str,
    default_relocation_count: int,
    gates: tuple[RouteGate, ...],
    resource_kind: str = "simulator",
    supports_operator_steer: bool = True,
) -> ConsoleRoute:
    return ConsoleRoute(
        id=route_id,
        label=label,
        task="household-cleanup",
        surface="household-world",
        intent="cleanup",
        driver=driver,
        profile="world-oracle-labels",
        backend=backend,
        lock_name=lock_name,
        supports_prompt=True,
        enabled=True,
        checker_id="cleanup_report",
        task_prompt_default="帮我收拾这个房间",
        supported_intents=("cleanup", "open-ended"),
        default_overrides=(
            "seed=7",
            f"environment_setup={ENVIRONMENT_SETUP_RELOCATE_CLEANUP_RELATED_OBJECTS}",
            f"relocation_count={default_relocation_count}",
        ),
        gates=(PROVIDER_KEY_GATE, MCP_PORT_FREE_GATE, *gates),
        resource_kind=resource_kind,
        supports_operator_steer=supports_operator_steer,
        driver_label="Claude Code" if driver == "claude" else "Codex",
    )


SUPPORTED_ROUTES: tuple[ConsoleRoute, ...] = (
    ConsoleRoute(
        id="codex-mujoco-cleanup",
        label="MuJoCo Cleanup",
        task="household-cleanup",
        surface="household-world",
        intent="cleanup",
        driver="codex",
        profile="world-oracle-labels",
        backend="molmospaces_subprocess",
        lock_name="molmospaces_mujoco",
        supports_prompt=True,
        enabled=True,
        checker_id="cleanup_report",
        task_prompt_default="帮我收拾这个房间",
        supported_intents=("cleanup", "open-ended"),
        default_overrides=(
            "seed=7",
            f"environment_setup={ENVIRONMENT_SETUP_RELOCATE_CLEANUP_RELATED_OBJECTS}",
            "relocation_count=5",
        ),
        gates=(PROVIDER_KEY_GATE, MCP_PORT_FREE_GATE),
        driver_label="Codex",
        supports_operator_steer=True,
    ),
    _cleanup_route(
        route_id="claude-mujoco-cleanup",
        label="MuJoCo Cleanup",
        driver="claude",
        backend="molmospaces_subprocess",
        lock_name="molmospaces_mujoco",
        default_relocation_count=5,
        gates=(),
        supports_operator_steer=True,
    ),
    _cleanup_route(
        route_id="codex-isaac-cleanup",
        label="Isaac Cleanup",
        driver="codex",
        backend="isaaclab_subprocess",
        lock_name="isaac_gpu",
        default_relocation_count=1,
        gates=(ISAAC_PREFLIGHT_GATE,),
        resource_kind="gpu",
        supports_operator_steer=True,
    ),
    _cleanup_route(
        route_id="claude-isaac-cleanup",
        label="Isaac Cleanup",
        driver="claude",
        backend="isaaclab_subprocess",
        lock_name="isaac_gpu",
        default_relocation_count=1,
        gates=(ISAAC_PREFLIGHT_GATE,),
        resource_kind="gpu",
        supports_operator_steer=True,
    ),
    ConsoleRoute(
        id="codex-agibot-g2-map-build",
        label="Agibot G2 Map Build",
        task="semantic-map-build",
        surface="household-world",
        intent="map-build",
        driver="codex",
        profile="camera-grounded-labels",
        backend="agibot_gdk",
        lock_name="agibot_g2",
        supports_prompt=True,
        enabled=True,
        checker_id="runtime_metric_map",
        task_prompt_default="帮我建立这个房间的语义地图",
        required_overrides=("context_json",),
        default_overrides=(
            "policy=codex_agibot_semantic_map_build_pilot",
            "camera_labeler=grounding-dino",
            "visual_grounding_timeout_s=20",
            f"environment_setup={ENVIRONMENT_SETUP_BASELINE}",
        ),
        gates=(
            PROVIDER_KEY_GATE,
            MCP_PORT_FREE_GATE,
            AGIBOT_CONTEXT_GATE,
            AGIBOT_LOCALIZATION_GATE,
            AGIBOT_ENABLEMENT_GATE,
            AGIBOT_ESTOP_GATE,
        ),
        emergency_stop_required=True,
        resource_kind="physical_robot",
        driver_label="Codex",
    ),
    ConsoleRoute(
        id="codex-mujoco-map-build",
        label="MuJoCo Map Build",
        task="semantic-map-build",
        surface="household-world",
        intent="map-build",
        driver="codex",
        profile="world-oracle-labels",
        backend="molmospaces_subprocess",
        lock_name="molmospaces_mujoco",
        supports_prompt=True,
        enabled=True,
        checker_id="runtime_metric_map",
        task_prompt_default="帮我建立这个房间的语义地图",
        default_overrides=("seed=7", f"environment_setup={ENVIRONMENT_SETUP_BASELINE}"),
        gates=(PROVIDER_KEY_GATE, MCP_PORT_FREE_GATE),
        driver_label="Codex",
    ),
    ConsoleRoute(
        id="codex-isaac-map-build",
        label="Isaac Map Build",
        task="semantic-map-build",
        surface="household-world",
        intent="map-build",
        driver="codex",
        profile="world-oracle-labels",
        backend="isaaclab_subprocess",
        lock_name="isaac_gpu",
        supports_prompt=True,
        enabled=True,
        checker_id="runtime_metric_map",
        task_prompt_default="帮我建立这个房间的语义地图",
        default_overrides=("seed=7", f"environment_setup={ENVIRONMENT_SETUP_BASELINE}"),
        gates=(PROVIDER_KEY_GATE, MCP_PORT_FREE_GATE, ISAAC_PREFLIGHT_GATE),
        resource_kind="gpu",
        driver_label="Codex",
    ),
    ConsoleRoute(
        id="codex-b1-map12-open-ended",
        label="B1 Map 12 Open-Ended",
        task="household-open-ended",
        surface="household-world",
        intent="open-ended",
        driver="codex",
        profile="world-oracle-labels",
        backend="isaaclab_subprocess",
        lock_name="isaac_gpu",
        supports_prompt=True,
        enabled=True,
        checker_id="open_ended_report",
        task_prompt_default="在 B1 / Map 12 场景中完成开放性导航任务，并报告你看到的证据。",
        supported_intents=("open-ended",),
        default_overrides=(
            "seed=7",
            f"environment_setup={ENVIRONMENT_SETUP_BASELINE}",
            f"map_bundle={B1_MAP12_BUNDLE}",
            f"isaac_scene_usd_path={B1_MAP12_LIVINGROOM_USD}",
            "robot_views=on",
        ),
        gates=(PROVIDER_KEY_GATE, MCP_PORT_FREE_GATE, ISAAC_PREFLIGHT_GATE),
        resource_kind="gpu",
        supports_operator_steer=True,
        driver_label="Codex",
    ),
)


DISABLED_ROUTES: tuple[ConsoleRoute, ...] = (
    ConsoleRoute(
        id="agibot-g2-cleanup",
        label="Agibot G2 Cleanup",
        task="household-cleanup",
        surface="household-world",
        intent="cleanup",
        driver="codex",
        profile="camera-grounded-labels",
        backend="agibot_gdk",
        lock_name="agibot_g2",
        supports_prompt=False,
        enabled=False,
        checker_id="blocked_capability",
        task_prompt_default="",
        disabled_reason=(
            "Physical manipulation is not available yet. Run Agibot G2 Map Build first."
        ),
        emergency_stop_required=True,
        resource_kind="physical_robot",
        driver_label="Codex",
    ),
    ConsoleRoute(
        id="unsupported-drivers",
        label="Direct / OpenClaw / VLM",
        task="household-cleanup",
        surface="household-world",
        intent="cleanup",
        driver="direct",
        profile="world-oracle-labels",
        backend="unsupported",
        lock_name="unsupported",
        supports_prompt=False,
        enabled=False,
        checker_id="unsupported",
        task_prompt_default="",
        disabled_reason="This console supports local coding-agent drivers only.",
    ),
    ConsoleRoute(
        id="claude-map-build",
        label="Claude Map Build",
        task="semantic-map-build",
        surface="household-world",
        intent="map-build",
        driver="claude",
        profile="world-oracle-labels",
        backend="unsupported",
        lock_name="unsupported",
        supports_prompt=False,
        enabled=False,
        checker_id="unsupported",
        task_prompt_default="",
        disabled_reason="semantic-map-build does not support the Claude driver yet.",
        driver_label="Claude Code",
    ),
    ConsoleRoute(
        id="ai2thor-games",
        label="AI2-THOR games",
        task="coverage",
        surface="ai2thor-games",
        intent="coverage",
        driver="codex",
        profile="visual",
        backend="unsupported",
        lock_name="unsupported",
        supports_prompt=False,
        enabled=False,
        checker_id="unsupported",
        task_prompt_default="",
        disabled_reason="Navigation games are outside this operator console.",
        driver_label="Codex",
    ),
)


def list_console_routes(*, include_disabled: bool = True) -> tuple[ConsoleRoute, ...]:
    """Return the v1 route matrix for the console."""

    if include_disabled:
        return (*SUPPORTED_ROUTES, *DISABLED_ROUTES)
    return SUPPORTED_ROUTES


def get_route(route_id: str) -> ConsoleRoute:
    for route in list_console_routes(include_disabled=True):
        if route.id == route_id:
            return route
    raise KeyError(route_id)


def validate_supported_routes_against_catalog() -> None:
    """Fail if supported console routes drift away from the public catalog."""

    for route in SUPPORTED_ROUTES:
        for intent in route.supported_intent_ids():
            resolve_surface_launch(route.base_args(intent=intent))


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


def _default_field_groups(route: ConsoleRoute) -> tuple[str, ...]:
    groups = ["common"]
    gate_ids = {gate.id for gate in route.gates}
    if "isaac_preflight" in gate_ids:
        groups.append("isaac")
    if "context_json" in gate_ids:
        groups.append("agibot")
    if {"localization_ready", "run_enabled", "estop_ready"} & gate_ids:
        groups.append("agibot_gates")
    return tuple(groups)


def _default_view_modes(route: ConsoleRoute) -> tuple[str, ...]:
    modes = ["overview", "fpv", "map"]
    has_grounding = (
        route.profile == "camera-grounded-labels"
        or route.backend == "isaaclab_subprocess"
        or any(item.startswith("camera_labeler=") for item in route.default_overrides)
    )
    if has_grounding:
        modes.append("grounding")
    if route.backend in {"molmospaces_subprocess", "isaaclab_subprocess"}:
        modes.append("chase")
    modes.append("outputs")
    return tuple(modes)


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
        "coverage": "Coverage",
    }.get(intent_id, intent_id.replace("-", " ").title())
