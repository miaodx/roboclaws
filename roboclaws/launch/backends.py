"""Launch backend metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BackendSpec:
    """Runtime/backend metadata for one launch world."""

    id: str
    label: str
    implementation_backend: str
    lock_name: str
    resource_kind: str
    field_groups: tuple[str, ...]
    view_modes: tuple[str, ...]
    gates: tuple[str, ...] = ()
    default_overrides: tuple[str, ...] = ()
    availability: str = "enabled"


BACKEND_SPECS: dict[str, BackendSpec] = {
    "mujoco": BackendSpec(
        id="mujoco",
        label="MuJoCo",
        implementation_backend="molmospaces_subprocess",
        lock_name="molmospaces_mujoco",
        resource_kind="simulator",
        field_groups=("common",),
        view_modes=("overview", "fpv", "map", "chase", "outputs"),
    ),
    "isaaclab": BackendSpec(
        id="isaaclab",
        label="Isaac Lab",
        implementation_backend="isaaclab_subprocess",
        lock_name="isaac_gpu",
        resource_kind="gpu",
        field_groups=("common", "isaac"),
        view_modes=("overview", "fpv", "map", "grounding", "chase", "outputs"),
        gates=("isaac_preflight",),
    ),
    "agibot-gdk": BackendSpec(
        id="agibot-gdk",
        label="Agibot GDK",
        implementation_backend="agibot_gdk",
        lock_name="agibot_g2",
        resource_kind="physical_robot",
        field_groups=("common", "agibot", "agibot_gates"),
        view_modes=("overview", "fpv", "map", "grounding", "outputs"),
        gates=("context_json", "localization_ready", "run_enabled", "estop_ready"),
    ),
    "ai2thor": BackendSpec(
        id="ai2thor",
        label="AI2-THOR",
        implementation_backend="ai2thor",
        lock_name="ai2thor",
        resource_kind="simulator",
        field_groups=("common",),
        view_modes=("overview", "fpv", "map", "outputs"),
    ),
}


def backend_spec(backend_id: str) -> BackendSpec:
    """Return a backend spec by public id."""

    return BACKEND_SPECS[backend_id]
