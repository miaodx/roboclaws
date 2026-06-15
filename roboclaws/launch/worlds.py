"""Operator-facing launch world and scene metadata."""

from __future__ import annotations

from dataclasses import dataclass

from roboclaws.launch.scene_sampler import (
    legacy_molmospaces_world_ids,
    sampler_rows,
    ui_molmospaces_world_ids,
)


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
    sampler_metadata: dict[str, object] | None = None


MOLMOSPACES_CONSOLE_WORLD_IDS: tuple[str, ...] = ui_molmospaces_world_ids()
MOLMOSPACES_LAUNCH_ALIAS_WORLD_IDS: tuple[str, ...] = legacy_molmospaces_world_ids()
MOLMOSPACES_LAUNCH_ALIAS_SCENE_INDICES: tuple[int, ...] = tuple(
    int(world_id.rsplit("_", 1)[1]) for world_id in MOLMOSPACES_LAUNCH_ALIAS_WORLD_IDS
)


def _molmospaces_world_spec(row) -> WorldSpec:
    scene_index = row.scene_index
    if scene_index is None:
        raise ValueError("blocked sampler rows do not create launch worlds")
    tags = (
        "household",
        "molmospaces",
        "source-aware-sampler",
        "sampler-ui" if row.ui_ready else "sampler-alias",
        "curated-default" if scene_index == 0 else "curated-source",
    )
    return WorldSpec(
        id=row.world_id,
        label=f"MolmoSpaces {row.scene_source} #{scene_index}",
        surface_id="household-world",
        available_backends=("mujoco", "isaaclab"),
        scene_source=row.scene_source,
        tags=tags,
        default_backend="mujoco",
        resource_kind="simulator",
        availability="enabled" if row.ui_ready else "hidden",
        default_overrides=row.default_overrides,
        preview_assets=row.preview_assets,
        sampler_metadata={
            "schema": "molmospaces_scene_sampler_world_metadata_v1",
            "scene_family": row.scene_family,
            "scene_split": row.scene_split,
            "scene_source": row.scene_source,
            "scene_index": row.scene_index,
            "room_count": row.room_count,
            "waypoint_count": row.waypoint_count,
            "category_provenance": row.category_provenance,
            "selected_reason": row.selected_reason,
            "lanes": list(row.lanes),
            "generator_version": row.to_dict()["generator_version"],
        },
    )


WORLD_SPECS: dict[str, WorldSpec] = {
    **{
        row.world_id: _molmospaces_world_spec(row)
        for row in sampler_rows()
        if row.scene_index is not None
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
            "map_bundle=b1-map12-room-semantics",
            "isaac_scene_usd_path=data/robot-data-lab/scene-engine/data/"
            "2rd_floor_seperated/storey_1/configuration/scene_base.usd",
            "robot_views=on",
        ),
        preview_assets=(("map", "/asset-previews/maps/b1-map12-room-semantics/preview.png"),),
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
    "planner-proof": "planner-proof/default",
}


def world_spec(world_id: str) -> WorldSpec:
    """Return a world spec by id."""

    return WORLD_SPECS[world_id]
