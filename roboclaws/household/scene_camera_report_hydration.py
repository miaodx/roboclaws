from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SceneCameraReportHydration:
    candidate_visual_diagnostics: Callable[..., dict[str, Any]]
    projection_diagnostics: Callable[..., dict[str, Any]]
    visual_diagnostics: Callable[..., dict[str, Any]]
    room_wall_light_diagnostics: Callable[..., dict[str, Any]]
    native_isaac_render_diagnostics: Callable[..., dict[str, Any]]
    render_domain_source_diagnostics: Callable[..., dict[str, Any]]
    render_domain_view_triage: Callable[..., dict[str, Any]]
    render_domain_contract_probe: Callable[..., dict[str, Any]]
    lighting_tone_provenance: Callable[..., dict[str, Any]]
    shadow_parity_probe: Callable[..., dict[str, Any]]
    backend_swap_geometry_contract: Callable[..., dict[str, Any]]


def hydrate_scene_camera_report_manifest(
    manifest: dict[str, Any],
    *,
    output_dir: Path,
    builders: SceneCameraReportHydration,
) -> None:
    diagnostics: Mapping[str, Callable[[], dict[str, Any]]] = {
        "candidate_visual_diagnostics": lambda: builders.candidate_visual_diagnostics(
            manifest,
            output_dir=output_dir,
        ),
        "projection_diagnostics": lambda: builders.projection_diagnostics(manifest),
        "visual_diagnostics": lambda: builders.visual_diagnostics(
            manifest,
            output_dir=output_dir,
        ),
        "room_wall_light_diagnostics": lambda: builders.room_wall_light_diagnostics(
            manifest,
            output_dir=output_dir,
        ),
        "native_isaac_render_diagnostics": lambda: builders.native_isaac_render_diagnostics(
            manifest
        ),
        "render_domain_source_diagnostics": lambda: builders.render_domain_source_diagnostics(
            manifest
        ),
        "render_domain_view_triage": lambda: builders.render_domain_view_triage(manifest),
        "render_domain_contract_probe": lambda: builders.render_domain_contract_probe(manifest),
        "lighting_tone_provenance": lambda: builders.lighting_tone_provenance(manifest),
        "shadow_parity_probe": lambda: builders.shadow_parity_probe(manifest),
        "backend_swap_geometry_contract": lambda: builders.backend_swap_geometry_contract(manifest),
    }
    for key, build in diagnostics.items():
        if not isinstance(manifest.get(key), dict):
            manifest[key] = build()
