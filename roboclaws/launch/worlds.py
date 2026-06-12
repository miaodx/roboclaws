"""Operator-facing launch world and scene metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorldSpec:
    """A room, map, site, or scene selected before backend/runtime choices."""

    id: str
    label: str
    surface_id: str
    available_backends: tuple[str, ...]
    scene_source: str
    tags: tuple[str, ...]
    default_backend: str
    resource_kind: str
    availability: str = "enabled"
    default_overrides: tuple[str, ...] = ()
    preview_assets: tuple[tuple[str, str], ...] = ()


MOLMOSPACES_CONSOLE_SCENE_INDICES: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 7, 9)
MOLMOSPACES_CONSOLE_WORLD_IDS: tuple[str, ...] = tuple(
    f"molmospaces/val_{index}" for index in MOLMOSPACES_CONSOLE_SCENE_INDICES
)


def _molmospaces_world_spec(scene_index: int) -> WorldSpec:
    world_id = f"molmospaces/val_{scene_index}"
    scene_name = f"val_{scene_index}"
    tags = ("household", "molmospaces", "curated-default" if scene_index == 0 else "curated-10")
    default_overrides = (
        "scene_source=procthor-10k-val",
        f"scene_index={scene_index}",
    )
    if scene_index != 0:
        default_overrides = (*default_overrides, "map_bundle=none")
    return WorldSpec(
        id=world_id,
        label=f"MolmoSpaces {scene_name}",
        surface_id="household-world",
        available_backends=("mujoco", "isaaclab"),
        scene_source="procthor-10k-val",
        tags=tags,
        default_backend="mujoco",
        resource_kind="simulator",
        default_overrides=default_overrides,
        preview_assets=(
            ("fpv", f"/previews/molmospaces-{scene_name}-fpv.png"),
            ("map", f"/previews/molmospaces-{scene_name}-map.png"),
            ("chase", f"/previews/molmospaces-{scene_name}-chase.png"),
            ("topdown", f"/previews/molmospaces-{scene_name}-topdown.png"),
        ),
    )


WORLD_SPECS: dict[str, WorldSpec] = {
    **{
        f"molmospaces/val_{index}": _molmospaces_world_spec(index)
        for index in MOLMOSPACES_CONSOLE_SCENE_INDICES
    },
    "agibot-g2/map-12": WorldSpec(
        id="agibot-g2/map-12",
        label="Agibot G2 Map 12",
        surface_id="household-world",
        available_backends=("agibot-gdk",),
        scene_source="operator-map",
        tags=("household", "physical-robot", "map-build"),
        default_backend="agibot-gdk",
        resource_kind="physical_robot",
        preview_assets=(("map", "/asset-previews/maps/agibot-robot-map-12/preview.png"),),
    ),
    "b1-map12": WorldSpec(
        id="b1-map12",
        label="B1 / Map 12 Digital Twin",
        surface_id="household-world",
        available_backends=("isaaclab",),
        scene_source="b1-gaussian-digital-twin",
        tags=("household", "digital-twin", "experimental"),
        default_backend="isaaclab",
        resource_kind="gpu",
        availability="experimental",
        default_overrides=(
            "map_bundle=agibot-robot-map-12",
            "isaac_scene_usd_path=data/robot-data-lab/scene-engine/data/"
            "B1_floor2_slow/usda/livingroom/livingroom_usdz_unpacked/livingroom.usda",
            "robot_views=on",
        ),
        preview_assets=(("map", "/asset-previews/maps/agibot-robot-map-12/preview.png"),),
    ),
    "ai2thor/FloorPlan201": WorldSpec(
        id="ai2thor/FloorPlan201",
        label="AI2-THOR FloorPlan201",
        surface_id="ai2thor-world",
        available_backends=("ai2thor",),
        scene_source="ithor",
        tags=("ai2thor", "navigation"),
        default_backend="ai2thor",
        resource_kind="simulator",
        default_overrides=("scene=FloorPlan201",),
    ),
    "ai2thor-games/FloorPlan201": WorldSpec(
        id="ai2thor-games/FloorPlan201",
        label="AI2-THOR Games FloorPlan201",
        surface_id="ai2thor-games",
        available_backends=("ai2thor",),
        scene_source="ithor",
        tags=("ai2thor", "game"),
        default_backend="ai2thor",
        resource_kind="simulator",
        default_overrides=("scene=FloorPlan201",),
    ),
    "planner-proof/default": WorldSpec(
        id="planner-proof/default",
        label="MolmoSpaces Planner Proof",
        surface_id="planner-proof",
        available_backends=("mujoco",),
        scene_source="molmospaces",
        tags=("household", "planner-proof"),
        default_backend="mujoco",
        resource_kind="simulator",
        preview_assets=(("map", "/previews/molmospaces-val_0-map.png"),),
    ),
}


DEFAULT_WORLD_BY_SURFACE: dict[str, str] = {
    "household-world": "molmospaces/val_0",
    "ai2thor-world": "ai2thor/FloorPlan201",
    "ai2thor-games": "ai2thor-games/FloorPlan201",
    "planner-proof": "planner-proof/default",
}


def world_spec(world_id: str) -> WorldSpec:
    """Return a world spec by id."""

    return WORLD_SPECS[world_id]
