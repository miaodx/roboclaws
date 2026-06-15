"""Source selection data for the MolmoSpaces scene sampler."""

from __future__ import annotations

from typing import Any

CURRENT_ALIAS_INDICES: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 7, 9)

SOURCE_UI_SELECTED_INDICES: dict[str, tuple[int, ...]] = {
    "procthor-10k-val": (0, 2, 9),
    "procthor-objaverse-val": (0, 1, 4),
}

SOURCE_EVAL_READY_INDICES: dict[str, tuple[int, ...]] = {
    "procthor-10k-val": (0, 2, 3, 5, 9, 10, 11, 12, 13, 15),
    "procthor-objaverse-val": (0, 1, 4, 5, 7, 10, 11, 12, 13, 14),
}

SCANNER_READY_METADATA: dict[str, dict[int, dict[str, Any]]] = {
    "procthor-10k-val": {
        10: {
            "room_count": 4,
            "waypoint_count": 8,
            "quality_score": 1.0,
            "coverage_score": 0.4,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-10k-val-10/0615_2303/seed-7"
            ),
        },
        11: {
            "room_count": 4,
            "waypoint_count": 8,
            "quality_score": 1.0,
            "coverage_score": 0.4,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-10k-val-11/0615_2303/seed-7"
            ),
        },
        12: {
            "room_count": 10,
            "waypoint_count": 20,
            "quality_score": 1.0,
            "coverage_score": 1.0,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-10k-val-12/0615_2304/seed-7"
            ),
        },
        13: {
            "room_count": 4,
            "waypoint_count": 8,
            "quality_score": 1.0,
            "coverage_score": 0.4,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-10k-val-13/0615_2306/seed-7"
            ),
        },
        15: {
            "room_count": 10,
            "waypoint_count": 20,
            "quality_score": 1.0,
            "coverage_score": 1.0,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-10k-val-15/0615_2308/seed-7"
            ),
        },
    },
    "procthor-objaverse-val": {
        0: {
            "room_count": 4,
            "waypoint_count": 8,
            "quality_score": 1.0,
            "coverage_score": 0.4,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-0/0615_2348/seed-7"
            ),
        },
        1: {
            "room_count": 7,
            "waypoint_count": 14,
            "quality_score": 1.0,
            "coverage_score": 0.7,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-1/0615_2348/seed-7"
            ),
        },
        4: {
            "room_count": 4,
            "waypoint_count": 8,
            "quality_score": 1.0,
            "coverage_score": 0.4,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-4/0615_2350/seed-7"
            ),
        },
        5: {
            "room_count": 7,
            "waypoint_count": 14,
            "quality_score": 1.0,
            "coverage_score": 0.7,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-5/0615_2350/seed-7"
            ),
        },
        7: {
            "room_count": 6,
            "waypoint_count": 12,
            "quality_score": 1.0,
            "coverage_score": 0.6,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-7/0615_2351/seed-7"
            ),
        },
        10: {
            "room_count": 5,
            "waypoint_count": 10,
            "quality_score": 1.0,
            "coverage_score": 0.5,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-10/0616_0003/seed-7"
            ),
        },
        11: {
            "room_count": 8,
            "waypoint_count": 16,
            "quality_score": 1.0,
            "coverage_score": 0.8,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-11/0616_0004/seed-7"
            ),
        },
        12: {
            "room_count": 6,
            "waypoint_count": 12,
            "quality_score": 1.0,
            "coverage_score": 0.6,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-12/0616_0004/seed-7"
            ),
        },
        13: {
            "room_count": 6,
            "waypoint_count": 12,
            "quality_score": 1.0,
            "coverage_score": 0.6,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-13/0616_0005/seed-7"
            ),
        },
        14: {
            "room_count": 6,
            "waypoint_count": 12,
            "quality_score": 1.0,
            "coverage_score": 0.6,
            "product_smoke_run_dir": (
                "output/scene-sampler-scanner/product-smoke/"
                "molmospaces-procthor-objaverse-val-14/0616_0006/seed-7"
            ),
        },
    },
}

SCANNER_REJECTED_METADATA: dict[str, dict[int, dict[str, Any]]] = {
    "procthor-objaverse-val": {
        2: {
            "room_count": 1,
            "waypoint_count": 2,
            "quality_score": 1.0,
            "coverage_score": 0.1,
            "blocked_reason": "fewer_than_three_public_navigation_areas",
        },
        3: {
            "room_count": 2,
            "waypoint_count": 4,
            "quality_score": 1.0,
            "coverage_score": 0.2,
            "blocked_reason": "fewer_than_three_public_navigation_areas",
        },
        6: {
            "room_count": 1,
            "waypoint_count": 2,
            "quality_score": 1.0,
            "coverage_score": 0.1,
            "blocked_reason": "fewer_than_three_public_navigation_areas",
        },
        8: {
            "room_count": 2,
            "waypoint_count": 4,
            "quality_score": 1.0,
            "coverage_score": 0.2,
            "blocked_reason": "fewer_than_three_public_navigation_areas",
        },
        9: {
            "room_count": 2,
            "waypoint_count": 4,
            "quality_score": 1.0,
            "coverage_score": 0.2,
            "blocked_reason": "fewer_than_three_public_navigation_areas",
        },
    },
}


def admitted_sources(*, supported_sources: tuple[str, ...]) -> tuple[str, ...]:
    admitted = set(SOURCE_UI_SELECTED_INDICES) | set(SOURCE_EVAL_READY_INDICES)
    return tuple(source for source in supported_sources if source in admitted)


def known_indices_for_source(source: str) -> tuple[int, ...]:
    return tuple(
        sorted(
            {
                *SOURCE_UI_SELECTED_INDICES.get(source, ()),
                *SOURCE_EVAL_READY_INDICES.get(source, ()),
                *SCANNER_REJECTED_METADATA.get(source, ()),
                *(CURRENT_ALIAS_INDICES if source == "procthor-10k-val" else ()),
            }
        )
    )


def scanner_metadata(*, source: str, scene_index: int) -> dict[str, Any]:
    return (
        SCANNER_READY_METADATA.get(source, {}).get(scene_index)
        or SCANNER_REJECTED_METADATA.get(source, {}).get(scene_index)
        or {}
    )


def source_ui_indices(source: str) -> tuple[int, ...]:
    return SOURCE_UI_SELECTED_INDICES.get(source, ())


def source_eval_indices(source: str) -> tuple[int, ...]:
    return SOURCE_EVAL_READY_INDICES.get(source, ())


def sampler_world_id(*, source: str, scene_index: int) -> str:
    if source == "procthor-10k-val" and scene_index in CURRENT_ALIAS_INDICES:
        return f"molmospaces/val_{scene_index}"
    return f"molmospaces/{source}/{scene_index}"


def legacy_world_id(*, source: str, scene_index: int) -> str:
    if source == "procthor-10k-val" and scene_index in CURRENT_ALIAS_INDICES:
        return f"molmospaces/val_{scene_index}"
    return ""


def category_provenance(source: str) -> str:
    if source == "procthor-objaverse-val":
        return "source_metadata"
    return "prepared_visual_label_manifest"


def category_manifest(source: str, *, default_manifest: str) -> str:
    if source == "procthor-objaverse-val":
        return ""
    return default_manifest


def uses_legacy_preview_assets(*, source: str, scene_index: int) -> bool:
    return source == "procthor-10k-val" and scene_index not in SCANNER_READY_METADATA.get(
        source, {}
    )
