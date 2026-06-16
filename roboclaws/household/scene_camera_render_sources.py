from __future__ import annotations

MOLMOSPACES_LANE_ID = "molmospaces-mujoco"
ISAAC_LANE_ID = "isaaclab-prepared-usd"

OFFICIAL_RENDER_SOURCE_REFERENCES = (
    {
        "evidence_id": "mujoco_housegen_materials",
        "lane": MOLMOSPACES_LANE_ID,
        "path": "vendors/molmospaces/molmo_spaces/housegen/builder.py",
        "line_start": 361,
        "line_end": 399,
        "claim": (
            "MuJoCo scene generation parses source-scene material albedo, specular values, "
            "and diffuse texture paths into MJCF material metadata."
        ),
    },
    {
        "evidence_id": "mujoco_housegen_lights",
        "lane": MOLMOSPACES_LANE_ID,
        "path": "vendors/molmospaces/molmo_spaces/housegen/builder.py",
        "line_start": 455,
        "line_end": 470,
        "claim": (
            "MuJoCo housegen optionally exports house lights, otherwise it creates a "
            "default MJCF light at scene-build time."
        ),
    },
    {
        "evidence_id": "mujoco_asset_texture_material_collection",
        "lane": MOLMOSPACES_LANE_ID,
        "path": "vendors/molmospaces/molmo_spaces/housegen/builder.py",
        "line_start": 1372,
        "line_end": 1452,
        "claim": (
            "MuJoCo asset import copies texture slots and material RGBA into the scene "
            "spec before rendering."
        ),
    },
    {
        "evidence_id": "isaac_preview_surface_material_conversion",
        "lane": ISAAC_LANE_ID,
        "path": (
            "vendors/molmospaces/molmo_spaces_isaac/src/molmo_spaces_isaac/assets/utils/material.py"
        ),
        "line_start": 52,
        "line_end": 112,
        "claim": (
            "Isaac USD conversion maps MJCF materials to USD PreviewSurface materials, "
            "forces opacity to 1.0, maps shininess to roughness, and handles diffuse "
            "textures through USD texture nodes."
        ),
    },
    {
        "evidence_id": "isaac_material_binding_texture_warning",
        "lane": ISAAC_LANE_ID,
        "path": (
            "vendors/molmospaces/molmo_spaces_isaac/src/"
            "molmo_spaces_isaac/assets/house_converter.py"
        ),
        "line_start": 288,
        "line_end": 322,
        "claim": (
            "Isaac material binding warns that textured materials bound to non-Mesh prims "
            "can discard textures at render time."
        ),
    },
    {
        "evidence_id": "isaac_default_lights_and_shadow_flags",
        "lane": ISAAC_LANE_ID,
        "path": (
            "vendors/molmospaces/molmo_spaces_isaac/src/"
            "molmo_spaces_isaac/assets/house_converter.py"
        ),
        "line_start": 325,
        "line_end": 380,
        "claim": (
            "Isaac scene conversion authors default DistantLight/DomeLight and disables "
            "shadow casting on selected wall or ceiling visual prims."
        ),
    },
)
