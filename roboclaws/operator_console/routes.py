"""Explicit route registry for the standalone Codex operator console."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from roboclaws.launch.catalog import resolve_task_launch


@dataclass(frozen=True)
class RouteGate:
    """A start gate surfaced to operators before a live robot run."""

    id: str
    label: str
    kind: str
    required: bool = True
    help_text: str = ""

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConsoleRoute:
    """One route card in the Codex-only operator console."""

    id: str
    label: str
    task: str
    driver: str
    profile: str
    backend: str
    lock_name: str
    supports_prompt: bool
    enabled: bool
    checker_id: str
    task_prompt_default: str
    required_overrides: tuple[str, ...] = ()
    default_overrides: tuple[str, ...] = ()
    gates: tuple[RouteGate, ...] = ()
    disabled_reason: str = ""
    pause_supported: bool = False
    emergency_stop_required: bool = False
    resource_kind: str = "simulator"

    def base_args(self) -> list[str]:
        return [
            self.task,
            self.driver,
            self.profile,
            f"backend={self.backend}",
            *self.default_overrides,
        ]

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["argv_preview"] = ["just", "task::run", *self.base_args()]
        payload["command_preview"] = payload["argv_preview"]
        payload["gates"] = [gate.to_payload() for gate in self.gates]
        payload["required_gates"] = payload["gates"]
        payload["state"] = "enabled" if self.enabled else "disabled"
        payload["blocker"] = self.disabled_reason
        payload["prompt_disabled_reason"] = (
            ""
            if self.supports_prompt
            else "This route cannot accept a custom prompt safely. Use the default task prompt."
        )
        payload["default_prompt"] = self.task_prompt_default
        return payload


PROVIDER_KEY_GATE = RouteGate(
    id="provider_key",
    label="Provider key route present",
    kind="provider_key",
    help_text="Load a repo-local Codex provider key route before launch.",
)
ISAAC_PREFLIGHT_GATE = RouteGate(
    id="isaac_preflight",
    label="Isaac preflight accepted",
    kind="isaac_preflight",
    help_text="Run or accept a recent Isaac runtime preflight/smoke artifact before launch.",
)
AGIBOT_CONTEXT_GATE = RouteGate(
    id="context_json",
    label="Agibot context JSON attached",
    kind="request_field",
    help_text="Attach a completed Agibot map context JSON.",
)
AGIBOT_LOCALIZATION_GATE = RouteGate(
    id="localization_ready",
    label="Localization gate accepted",
    kind="operator_gate",
)
AGIBOT_ENABLEMENT_GATE = RouteGate(
    id="run_enabled",
    label="Run enablement accepted",
    kind="operator_gate",
)
AGIBOT_ESTOP_GATE = RouteGate(
    id="estop_ready",
    label="E-stop readiness visible",
    kind="operator_gate",
)


SUPPORTED_ROUTES: tuple[ConsoleRoute, ...] = (
    ConsoleRoute(
        id="mujoco-cleanup",
        label="MuJoCo Cleanup",
        task="household-cleanup",
        driver="codex",
        profile="world-labels",
        backend="molmospaces_subprocess",
        lock_name="molmospaces_mujoco",
        supports_prompt=True,
        enabled=True,
        checker_id="cleanup_report",
        task_prompt_default="帮我收拾这个房间",
        default_overrides=("seed=7", "generated_mess_count=5"),
        gates=(PROVIDER_KEY_GATE,),
    ),
    ConsoleRoute(
        id="isaac-cleanup",
        label="Isaac Cleanup",
        task="household-cleanup",
        driver="codex",
        profile="world-labels",
        backend="isaaclab_subprocess",
        lock_name="isaac_gpu",
        supports_prompt=True,
        enabled=True,
        checker_id="cleanup_report",
        task_prompt_default="帮我收拾这个房间",
        default_overrides=("seed=7", "generated_mess_count=1"),
        gates=(PROVIDER_KEY_GATE, ISAAC_PREFLIGHT_GATE),
        resource_kind="gpu",
    ),
    ConsoleRoute(
        id="agibot-g2-map-build",
        label="Agibot G2 Map Build",
        task="semantic-map-build",
        driver="codex",
        profile="camera-labels",
        backend="agibot_gdk",
        lock_name="agibot_g2",
        supports_prompt=True,
        enabled=True,
        checker_id="runtime_metric_map",
        task_prompt_default="帮我建立这个房间的语义地图",
        required_overrides=("context_json",),
        default_overrides=("visual_grounding=grounding-dino",),
        gates=(
            PROVIDER_KEY_GATE,
            AGIBOT_CONTEXT_GATE,
            AGIBOT_LOCALIZATION_GATE,
            AGIBOT_ENABLEMENT_GATE,
            AGIBOT_ESTOP_GATE,
        ),
        emergency_stop_required=True,
        resource_kind="physical_robot",
    ),
    ConsoleRoute(
        id="mujoco-map-build",
        label="MuJoCo Map Build",
        task="semantic-map-build",
        driver="codex",
        profile="world-labels",
        backend="molmospaces_subprocess",
        lock_name="molmospaces_mujoco",
        supports_prompt=True,
        enabled=True,
        checker_id="runtime_metric_map",
        task_prompt_default="帮我建立这个房间的语义地图",
        default_overrides=("seed=7", "generated_mess_count=5"),
        gates=(PROVIDER_KEY_GATE,),
    ),
    ConsoleRoute(
        id="isaac-map-build",
        label="Isaac Map Build",
        task="semantic-map-build",
        driver="codex",
        profile="world-labels",
        backend="isaaclab_subprocess",
        lock_name="isaac_gpu",
        supports_prompt=True,
        enabled=True,
        checker_id="runtime_metric_map",
        task_prompt_default="帮我建立这个房间的语义地图",
        default_overrides=("seed=7", "generated_mess_count=1"),
        gates=(PROVIDER_KEY_GATE, ISAAC_PREFLIGHT_GATE),
        resource_kind="gpu",
    ),
)


DISABLED_ROUTES: tuple[ConsoleRoute, ...] = (
    ConsoleRoute(
        id="agibot-g2-cleanup",
        label="Agibot G2 Cleanup",
        task="household-cleanup",
        driver="codex",
        profile="camera-labels",
        backend="agibot_gdk",
        lock_name="agibot_g2",
        supports_prompt=False,
        enabled=False,
        checker_id="blocked_capability",
        task_prompt_default="",
        disabled_reason="Physical manipulation is blocked. Run Agibot G2 Map Build first.",
        emergency_stop_required=True,
        resource_kind="physical_robot",
    ),
    ConsoleRoute(
        id="non-codex-routes",
        label="Direct / OpenClaw / Claude / VLM",
        task="household-cleanup",
        driver="codex",
        profile="world-labels",
        backend="unsupported",
        lock_name="unsupported",
        supports_prompt=False,
        enabled=False,
        checker_id="unsupported",
        task_prompt_default="",
        disabled_reason="This console is Codex-only for v1.",
    ),
    ConsoleRoute(
        id="ai2thor-games",
        label="AI2-THOR games",
        task="coverage",
        driver="codex",
        profile="visual",
        backend="unsupported",
        lock_name="unsupported",
        supports_prompt=False,
        enabled=False,
        checker_id="unsupported",
        task_prompt_default="",
        disabled_reason="Navigation games are outside this operator console.",
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
        resolve_task_launch(route.base_args())


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
