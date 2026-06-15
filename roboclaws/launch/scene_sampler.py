"""Source-aware MolmoSpaces scene sampler contract."""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SAMPLER_MANIFEST_SCHEMA = "molmospaces_scene_sampler_manifest_v1"
SAMPLER_LABEL_MANIFEST_SCHEMA = "molmospaces_scene_room_labels_v1"
SAMPLER_PROJECTION_SCHEMA = "molmospaces_scene_sampler_projection_v1"
SAMPLER_GENERATOR_VERSION = "2026-06-15.preview-readiness-v1"
PRIMARY_MOLMOSPACES_BACKEND = "mujoco"
UI_TARGET_PER_SCENE_SOURCE = 3
EVAL_TARGET_PER_SCENE_SOURCE = 10

UI_LANE = "ui"
EVAL_STRESS_LANE = "eval_stress"
READINESS_READY = "ready"
READINESS_BLOCKED = "blocked"
READINESS_REJECTED = "rejected"

SUPPORTED_SCENE_SOURCES: tuple[str, ...] = (
    "procthor-10k-val",
    "ithor",
    "procthor-objaverse-val",
    "holodeck-objaverse-val",
)

_CURRENT_ALIAS_INDICES: tuple[int, ...] = (0, 1, 2, 3, 4, 5, 7, 9)
_UI_SELECTED_INDICES: tuple[int, ...] = (0, 2, 9)
_EVAL_READY_INDICES: tuple[int, ...] = (0, 2, 3, 5, 9)
_PREVIEW_ROOT = Path(__file__).resolve().parents[1] / "operator_console" / "static" / "previews"
_LABEL_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "data" / "molmospaces" / (
    "scene_sampler_room_labels.json"
)


@dataclass(frozen=True)
class MolmoSpacesSceneRef:
    """A parsed MolmoSpaces world id with explicit source identity."""

    scene_source: str
    scene_index: int


@dataclass(frozen=True)
class SceneSamplerRow:
    """One source-qualified scene sampler candidate or blocked source row."""

    scene_family: str
    scene_split: str
    scene_source: str
    scene_index: int | None
    backend: str
    readiness_status: str
    lanes: tuple[str, ...]
    world_id: str
    legacy_world_id: str
    room_count: int
    waypoint_count: int
    category_provenance: str
    category_manifest: str
    preview_assets: tuple[tuple[str, str], ...]
    selected_reason: str
    blocked_reason: str = ""
    failure_class: str = ""
    quality_score: float = 0.0
    coverage_score: float = 0.0

    @property
    def ui_ready(self) -> bool:
        return self.readiness_status == READINESS_READY and UI_LANE in self.lanes

    @property
    def eval_ready(self) -> bool:
        return self.readiness_status == READINESS_READY and EVAL_STRESS_LANE in self.lanes

    @property
    def index_token(self) -> str:
        if self.scene_index is None:
            return "blocked"
        return str(self.scene_index)

    @property
    def default_overrides(self) -> tuple[str, ...]:
        if self.scene_index is None:
            return ()
        overrides = (
            f"scene_source={self.scene_source}",
            f"scene_index={self.scene_index}",
        )
        if self.scene_index != 0:
            overrides = (*overrides, "map_bundle=none")
        return overrides

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_family": self.scene_family,
            "scene_split": self.scene_split,
            "scene_source": self.scene_source,
            "scene_index": self.scene_index,
            "backend": self.backend,
            "readiness_status": self.readiness_status,
            "lanes": list(self.lanes),
            "world_id": self.world_id,
            "legacy_world_id": self.legacy_world_id,
            "room_count": self.room_count,
            "waypoint_count": self.waypoint_count,
            "category_provenance": self.category_provenance,
            "category_manifest": self.category_manifest,
            "preview_assets": [
                {"view": view, "path": path} for view, path in self.preview_assets
            ],
            "selected_reason": self.selected_reason,
            "blocked_reason": self.blocked_reason,
            "failure_class": self.failure_class,
            "quality_score": self.quality_score,
            "coverage_score": self.coverage_score,
            "generator_version": SAMPLER_GENERATOR_VERSION,
        }


def sampler_manifest() -> dict[str, Any]:
    """Return the canonical source-aware MolmoSpaces sampler manifest."""

    rows = [row.to_dict() for row in sampler_rows()]
    return {
        "schema": SAMPLER_MANIFEST_SCHEMA,
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "primary_backend": PRIMARY_MOLMOSPACES_BACKEND,
        "ui_target_per_scene_source": UI_TARGET_PER_SCENE_SOURCE,
        "eval_target_per_scene_source": EVAL_TARGET_PER_SCENE_SOURCE,
        "supported_scene_sources": list(SUPPORTED_SCENE_SOURCES),
        "room_label_manifest": str(_LABEL_MANIFEST_PATH.relative_to(_repo_root())),
        "rows": rows,
        "projections": {
            "ui_world_ids": [row.world_id for row in ui_sampler_rows()],
            "eval_sample_ids": [eval_sample_id(row) for row in eval_sampler_rows()],
            "blocked_scene_sources": [
                row.scene_source
                for row in sampler_rows()
                if row.readiness_status == READINESS_BLOCKED
            ],
        },
    }


def sampler_rows() -> tuple[SceneSamplerRow, ...]:
    """Return all known source rows, including blocked source-family packets."""

    rows = [_ready_row(index) for index in _CURRENT_ALIAS_INDICES]
    rows.extend(_blocked_source_row(scene_source) for scene_source in SUPPORTED_SCENE_SOURCES[1:])
    return tuple(rows)


def ui_sampler_rows() -> tuple[SceneSamplerRow, ...]:
    """Return exactly the UI-visible MolmoSpaces sampler rows."""

    return tuple(row for row in sampler_rows() if row.ui_ready)


def eval_sampler_rows() -> tuple[SceneSamplerRow, ...]:
    """Return rows admitted to the static eval-stress projection."""

    return tuple(row for row in sampler_rows() if row.eval_ready)


def sampler_blocked_rows() -> tuple[SceneSamplerRow, ...]:
    """Return blocked or partial rows used by reports and eval-harness metadata."""

    return tuple(row for row in sampler_rows() if row.readiness_status != READINESS_READY)


def legacy_molmospaces_world_ids() -> tuple[str, ...]:
    """Return all current source-opaque aliases kept launchable for migration."""

    return tuple(f"molmospaces/val_{index}" for index in _CURRENT_ALIAS_INDICES)


def parse_molmospaces_world_id(world_id: str) -> MolmoSpacesSceneRef:
    """Parse legacy and source-aware MolmoSpaces world ids.

    Legacy ids such as ``molmospaces/val_9`` are preserved as
    ``procthor-10k-val`` aliases. New source-aware ids use
    ``molmospaces/<scene_source>/<index>``.
    """

    legacy_prefix = "molmospaces/val_"
    if world_id.startswith(legacy_prefix):
        return MolmoSpacesSceneRef(
            scene_source="procthor-10k-val",
            scene_index=_parse_scene_index(
                world_id.removeprefix(legacy_prefix),
                world_id=world_id,
            ),
        )

    parts = world_id.split("/")
    if len(parts) == 3 and parts[0] == "molmospaces":
        scene_source = parts[1]
        if scene_source not in SUPPORTED_SCENE_SOURCES:
            raise ValueError(f"unsupported MolmoSpaces scene_source {scene_source!r}: {world_id}")
        return MolmoSpacesSceneRef(
            scene_source=scene_source,
            scene_index=_parse_scene_index(parts[2], world_id=world_id),
        )

    raise ValueError(f"unsupported MolmoSpaces world id: {world_id}")


def ui_molmospaces_world_ids() -> tuple[str, ...]:
    """Return the curated operator-console world ids."""

    return tuple(row.world_id for row in ui_sampler_rows())


def eval_sample_id(row: SceneSamplerRow) -> str:
    if row.scene_index is None:
        return f"scene_sampler.{row.scene_source}.blocked"
    return f"scene_sampler.{row.scene_source}.{row.scene_index}.map_build"


def eval_sample_ref(row: SceneSamplerRow) -> str:
    if row.scene_index is None:
        return ""
    return (
        "evals/household_world/samples/scene_sampler/"
        f"{row.scene_source}_{row.scene_index}_map_build.json"
    )


def eval_projection_metadata() -> dict[str, Any]:
    """Return machine-readable sampler stress metadata for suite JSON."""

    rows = eval_sampler_rows()
    by_source: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        ready = [row for row in rows if row.scene_source == source]
        blocked = [
            row
            for row in sampler_rows()
            if row.scene_source == source and row.blocked_reason
        ]
        by_source[source] = {
            "target_count": EVAL_TARGET_PER_SCENE_SOURCE,
            "ready_count": len(ready),
            "status": (
                "complete"
                if len(ready) == EVAL_TARGET_PER_SCENE_SOURCE
                else "partial_or_blocked"
            ),
            "sample_ids": [eval_sample_id(row) for row in ready],
            "blocked_rows": [row.to_dict() for row in blocked],
        }
    return {
        "schema": SAMPLER_PROJECTION_SCHEMA,
        "projection": EVAL_STRESS_LANE,
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "scene_sources": by_source,
    }


def readiness_report() -> dict[str, Any]:
    """Return per-source UI/eval readiness counts for scanner artifacts."""

    rows = sampler_rows()
    by_source: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        scene_family, scene_split = _family_split(source)
        source_rows = [row for row in rows if row.scene_source == source]
        ui_rows = [row for row in source_rows if row.ui_ready]
        eval_rows = [row for row in source_rows if row.eval_ready]
        blocked_rows = [row for row in source_rows if row.blocked_reason]
        ready_rows = [row for row in source_rows if row.readiness_status == READINESS_READY]
        by_source[source] = {
            "scene_family": scene_family,
            "scene_split": scene_split,
            "ui_target_count": UI_TARGET_PER_SCENE_SOURCE,
            "ui_ready_count": len(ui_rows),
            "ui_status": (
                "ready" if len(ui_rows) == UI_TARGET_PER_SCENE_SOURCE else "not_visible"
            ),
            "ui_world_ids": [row.world_id for row in ui_rows],
            "eval_target_count": EVAL_TARGET_PER_SCENE_SOURCE,
            "eval_ready_count": len(eval_rows),
            "eval_status": (
                "complete"
                if len(eval_rows) == EVAL_TARGET_PER_SCENE_SOURCE
                else "partial_or_blocked"
            ),
            "eval_sample_ids": [eval_sample_id(row) for row in eval_rows],
            "ready_rows": [row.to_dict() for row in ready_rows],
            "blocked_rows": [row.to_dict() for row in blocked_rows],
        }
    return {
        "schema": "molmospaces_scene_sampler_readiness_report_v1",
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "primary_backend": PRIMARY_MOLMOSPACES_BACKEND,
        "sources": by_source,
        "summary": {
            "source_count": len(SUPPORTED_SCENE_SOURCES),
            "ui_supported_source_count": sum(
                1
                for source in SUPPORTED_SCENE_SOURCES
                if by_source[source]["ui_status"] == "ready"
            ),
            "eval_complete_source_count": sum(
                1
                for source in SUPPORTED_SCENE_SOURCES
                if by_source[source]["eval_status"] == "complete"
            ),
            "blocked_or_partial_source_count": sum(
                1
                for source in SUPPORTED_SCENE_SOURCES
                if by_source[source]["eval_status"] != "complete"
            ),
        },
    }


def source_availability_report(
    *,
    candidate_indices: tuple[int, ...] = tuple(range(10)),
) -> dict[str, Any]:
    """Return no-download source/asset visibility evidence for scanner readiness."""

    module_available, module_reason = _molmospaces_module_status()
    root, root_reason = _molmospaces_scene_root_status(module_available=module_available)
    sources: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        source_dir = root / source if root is not None else None
        source_exists = bool(source_dir and source_dir.is_dir())
        candidate_files = []
        missing_files = []
        for index in candidate_indices:
            candidate_path = source_dir / f"val_{index}.xml" if source_dir else None
            row = {
                "scene_index": index,
                "path": str(candidate_path) if candidate_path else "",
                "exists": bool(candidate_path and candidate_path.is_file()),
            }
            candidate_files.append(row)
            if not row["exists"]:
                missing_files.append(index)
        status = "available" if source_exists and not missing_files else "blocked"
        sources[source] = {
            "scene_source": source,
            "status": status,
            "module_available": module_available,
            "scene_root": str(root) if root is not None else "",
            "scene_root_available": bool(root and root.is_dir()),
            "source_dir": str(source_dir) if source_dir is not None else "",
            "source_dir_available": source_exists,
            "candidate_indices": list(candidate_indices),
            "candidate_files": candidate_files,
            "missing_candidate_indices": missing_files,
            "blocked_reason": _source_availability_blocked_reason(
                module_available=module_available,
                module_reason=module_reason,
                root=root,
                root_reason=root_reason,
                source=source,
                source_exists=source_exists,
                missing_files=missing_files,
            ),
            "failure_class": "" if status == "available" else "environment_blocked",
        }
    return {
        "schema": "molmospaces_scene_source_availability_report_v1",
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "probe_mode": "no_download_no_vlm",
        "candidate_indices": list(candidate_indices),
        "molmospaces_module_available": module_available,
        "molmospaces_module_reason": module_reason,
        "scene_root": str(root) if root is not None else "",
        "scene_root_reason": root_reason,
        "sources": sources,
    }


def candidate_readiness_report(
    *,
    candidate_indices: tuple[int, ...] = tuple(range(10)),
) -> dict[str, Any]:
    """Return no-download candidate packets for the next scanner/admission step."""

    availability = source_availability_report(candidate_indices=candidate_indices)
    rows_by_source_index = {
        (row.scene_source, row.scene_index): row
        for row in sampler_rows()
        if row.scene_index is not None
    }
    sources: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        source_availability = availability["sources"][source]
        candidates = []
        for index in candidate_indices:
            row = rows_by_source_index.get((source, index))
            if row is not None:
                candidates.append(_candidate_packet_from_sampler_row(row))
                continue
            candidates.append(
                _blocked_candidate_packet(
                    source=source,
                    scene_index=index,
                    source_availability=source_availability,
                )
            )
        ui_ready_count = sum(1 for item in candidates if item["ui_ready"])
        eval_ready_count = sum(1 for item in candidates if item["eval_ready"])
        sources[source] = {
            "scene_source": source,
            "ui_target_count": UI_TARGET_PER_SCENE_SOURCE,
            "ui_ready_count": ui_ready_count,
            "ui_status": "ready" if ui_ready_count == UI_TARGET_PER_SCENE_SOURCE else "not_visible",
            "eval_target_count": EVAL_TARGET_PER_SCENE_SOURCE,
            "eval_ready_count": eval_ready_count,
            "eval_status": (
                "complete"
                if eval_ready_count == EVAL_TARGET_PER_SCENE_SOURCE
                else "partial_or_blocked"
            ),
            "candidate_count": len(candidates),
            "ready_candidate_count": sum(
                1 for item in candidates if item["readiness_status"] == READINESS_READY
            ),
            "blocked_candidate_count": sum(
                1 for item in candidates if item["readiness_status"] == READINESS_BLOCKED
            ),
            "rejected_candidate_count": sum(
                1 for item in candidates if item["readiness_status"] == READINESS_REJECTED
            ),
            "source_availability": source_availability,
            "candidates": candidates,
        }
    return {
        "schema": "molmospaces_scene_sampler_candidate_readiness_v1",
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "probe_mode": "no_download_no_vlm",
        "candidate_indices": list(candidate_indices),
        "sources": sources,
    }


def selection_gap_report(
    *,
    candidate_indices: tuple[int, ...] = tuple(range(10)),
) -> dict[str, Any]:
    """Return deterministic scanner worklist gaps toward UI/eval source targets."""

    candidates = candidate_readiness_report(candidate_indices=candidate_indices)
    sources: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        source_payload = candidates["sources"][source]
        source_candidates = source_payload["candidates"]
        ui_ready_count = int(source_payload["ui_ready_count"])
        eval_ready_count = int(source_payload["eval_ready_count"])
        ui_needed = max(0, UI_TARGET_PER_SCENE_SOURCE - ui_ready_count)
        eval_needed = max(0, EVAL_TARGET_PER_SCENE_SOURCE - eval_ready_count)
        scanner_candidates = [
            item
            for item in source_candidates
            if item["readiness_status"] == READINESS_BLOCKED and not item["eval_ready"]
        ]
        ui_scan_candidates = scanner_candidates[:ui_needed]
        eval_scan_candidates = scanner_candidates[:eval_needed]
        sources[source] = {
            "scene_source": source,
            "ui_target_count": UI_TARGET_PER_SCENE_SOURCE,
            "ui_ready_count": ui_ready_count,
            "ui_needed_count": ui_needed,
            "eval_target_count": EVAL_TARGET_PER_SCENE_SOURCE,
            "eval_ready_count": eval_ready_count,
            "eval_needed_count": eval_needed,
            "status": "complete" if ui_needed == 0 and eval_needed == 0 else "incomplete",
            "source_availability_status": (
                source_payload.get("source_availability") or {}
            ).get("status"),
            "next_ui_scan_world_ids": [item["world_id"] for item in ui_scan_candidates],
            "next_eval_scan_world_ids": [item["world_id"] for item in eval_scan_candidates],
            "next_scan_candidates": [
                _selection_candidate_summary(item)
                for item in _unique_candidates([*ui_scan_candidates, *eval_scan_candidates])
            ],
            "rejected_candidate_indices": [
                item["scene_index"]
                for item in source_candidates
                if item["readiness_status"] == READINESS_REJECTED
            ],
        }
    return {
        "schema": "molmospaces_scene_sampler_selection_gaps_v1",
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "probe_mode": "no_download_no_vlm",
        "candidate_indices": list(candidate_indices),
        "sources": sources,
    }


def load_room_label_manifest(path: Path | None = None) -> dict[str, Any]:
    """Load the prepared room-category label manifest used for admission."""

    manifest_path = path or _LABEL_MANIFEST_PATH
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"room label manifest missing: {manifest_path}") from exc
    if payload.get("schema") != SAMPLER_LABEL_MANIFEST_SCHEMA:
        raise ValueError(
            "room label manifest must use schema "
            f"{SAMPLER_LABEL_MANIFEST_SCHEMA}, got {payload.get('schema')!r}"
        )
    return payload


def validate_sampler_manifest(manifest: dict[str, Any] | None = None) -> None:
    """Validate sampler rows against source-count and provenance gates."""

    payload = manifest or sampler_manifest()
    if payload.get("schema") != SAMPLER_MANIFEST_SCHEMA:
        raise ValueError("invalid sampler manifest schema")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("sampler manifest rows must be a list")
    label_manifest = load_room_label_manifest()
    _validate_label_manifest(label_manifest)
    by_source: dict[str, list[dict[str, Any]]] = {source: [] for source in SUPPORTED_SCENE_SOURCES}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("sampler row must be an object")
        source = str(row.get("scene_source") or "")
        if source not in by_source:
            raise ValueError(f"unsupported scene_source {source!r}")
        status = str(row.get("readiness_status") or "")
        if status == READINESS_READY:
            _validate_ready_row(row, label_manifest=label_manifest)
        elif status == READINESS_BLOCKED:
            if not row.get("blocked_reason") or not row.get("failure_class"):
                raise ValueError(f"blocked sampler row for {source} needs reason and failure_class")
        elif status != READINESS_REJECTED:
            raise ValueError(f"unknown readiness_status {status!r}")
        by_source[source].append(row)

    for source, source_rows in by_source.items():
        ui_ready = [
            row
            for row in source_rows
            if row.get("readiness_status") == READINESS_READY and UI_LANE in row.get("lanes", [])
        ]
        if 0 < len(ui_ready) < 3:
            raise ValueError(f"scene_source {source} exposes fewer than three UI-ready samples")
        if len(ui_ready) > UI_TARGET_PER_SCENE_SOURCE:
            raise ValueError(
                f"scene_source {source} exposes more than "
                f"{UI_TARGET_PER_SCENE_SOURCE} UI samples"
            )
        eval_ready = [
            row
            for row in source_rows
            if row.get("readiness_status") == READINESS_READY
            and EVAL_STRESS_LANE in row.get("lanes", [])
        ]
        if len(eval_ready) > EVAL_TARGET_PER_SCENE_SOURCE:
            raise ValueError(
                f"scene_source {source} exposes more than "
                f"{EVAL_TARGET_PER_SCENE_SOURCE} eval-stress samples"
            )


def _ready_row(scene_index: int) -> SceneSamplerRow:
    preview = _preview_metadata(scene_index)
    room_ids = _room_ids(preview)
    waypoint_count = _waypoint_count(preview)
    view_statuses = _view_statuses(preview)
    all_views_reviewable = all(
        view_statuses.get(view) == "reviewable" for view in _required_views()
    )
    ui_ready = scene_index in _UI_SELECTED_INDICES
    eval_ready = scene_index in _EVAL_READY_INDICES
    rejected_reason = ""
    if len(room_ids) < 3:
        rejected_reason = "fewer_than_three_public_navigation_areas"
    elif not all_views_reviewable:
        rejected_reason = "preview_not_reviewable"
    status = (
        READINESS_READY
        if (ui_ready or eval_ready) and not rejected_reason
        else READINESS_REJECTED
    )
    lanes: list[str] = []
    if ui_ready and status == READINESS_READY:
        lanes.append(UI_LANE)
    if eval_ready and status == READINESS_READY:
        lanes.append(EVAL_STRESS_LANE)
    selected_reason = (
        "selected_by_preview_scanner_for_source_diversity_and_map_actionability_seed"
        if lanes
        else rejected_reason or "alias_preserved_not_selected"
    )
    return SceneSamplerRow(
        scene_family="procthor-10k",
        scene_split="val",
        scene_source="procthor-10k-val",
        scene_index=scene_index,
        backend=PRIMARY_MOLMOSPACES_BACKEND,
        readiness_status=status,
        lanes=tuple(lanes),
        world_id=f"molmospaces/val_{scene_index}",
        legacy_world_id=f"molmospaces/val_{scene_index}",
        room_count=len(room_ids),
        waypoint_count=waypoint_count,
        category_provenance="prepared_visual_label_manifest",
        category_manifest=str(_LABEL_MANIFEST_PATH.relative_to(_repo_root())),
        preview_assets=_preview_assets(scene_index),
        selected_reason=selected_reason,
        blocked_reason=rejected_reason,
        failure_class="map_actionability_failure" if rejected_reason else "",
        quality_score=_quality_score(preview),
        coverage_score=_coverage_score(room_count=len(room_ids), waypoint_count=waypoint_count),
    )


def _blocked_source_row(scene_source: str) -> SceneSamplerRow:
    family, split = _family_split(scene_source)
    return SceneSamplerRow(
        scene_family=family,
        scene_split=split,
        scene_source=scene_source,
        scene_index=None,
        backend=PRIMARY_MOLMOSPACES_BACKEND,
        readiness_status=READINESS_BLOCKED,
        lanes=(),
        world_id=f"molmospaces/{scene_source}/blocked",
        legacy_world_id="",
        room_count=0,
        waypoint_count=0,
        category_provenance="unavailable",
        category_manifest="",
        preview_assets=(),
        selected_reason="blocked_until_assets_and_preview_readiness_exist",
        blocked_reason=(
            "MolmoSpaces source assets or loader metadata are not locally verified by the "
            "no-download sampler fixture; run scene preparation before admission."
        ),
        failure_class="environment_blocked",
    )


def _preview_metadata(scene_index: int) -> dict[str, Any]:
    path = _PREVIEW_ROOT / f"molmospaces-val_{scene_index}-preview.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing preview metadata for scene {scene_index}: {path}") from exc
    if payload.get("scene_source") != "procthor-10k-val":
        raise ValueError(f"preview {path} is not procthor-10k-val")
    if payload.get("backend") != PRIMARY_MOLMOSPACES_BACKEND:
        raise ValueError(f"preview {path} is not for backend={PRIMARY_MOLMOSPACES_BACKEND}")
    return payload


def _view_statuses(preview: dict[str, Any]) -> dict[str, str]:
    views = preview.get("views") if isinstance(preview.get("views"), dict) else {}
    return {
        view: str((payload.get("image_diagnostics") or {}).get("visual_status") or "")
        for view, payload in views.items()
        if isinstance(payload, dict)
    }


def _room_ids(preview: dict[str, Any]) -> tuple[str, ...]:
    semantic_projection = (
        ((preview.get("views") or {}).get("map") or {}).get("semantic_projection") or {}
    )
    waypoints = semantic_projection.get("projected_waypoints") or []
    return tuple(
        sorted(
            {
                str(item.get("room_id") or "")
                for item in waypoints
                if isinstance(item, dict) and item.get("room_id")
            }
        )
    )


def _waypoint_count(preview: dict[str, Any]) -> int:
    semantic_projection = (
        ((preview.get("views") or {}).get("map") or {}).get("semantic_projection") or {}
    )
    return int(
        semantic_projection.get("rendered_waypoint_count")
        or len(semantic_projection.get("projected_waypoints") or [])
    )


def _quality_score(preview: dict[str, Any]) -> float:
    statuses = _view_statuses(preview)
    reviewable_count = sum(1 for view in _required_views() if statuses.get(view) == "reviewable")
    return round(reviewable_count / len(_required_views()), 3)


def _coverage_score(*, room_count: int, waypoint_count: int) -> float:
    return round(min(1.0, (room_count / 10.0 + waypoint_count / 20.0) / 2.0), 3)


def _preview_assets(scene_index: int) -> tuple[tuple[str, str], ...]:
    scene_name = f"val_{scene_index}"
    return (
        ("fpv", f"/previews/molmospaces-{scene_name}-fpv.png"),
        ("map", f"/previews/molmospaces-{scene_name}-map.png"),
        ("chase", f"/previews/molmospaces-{scene_name}-chase.png"),
        ("topdown", f"/previews/molmospaces-{scene_name}-topdown.png"),
    )


def _required_views() -> tuple[str, ...]:
    return ("fpv", "map", "chase", "topdown")


def _family_split(scene_source: str) -> tuple[str, str]:
    if scene_source == "ithor":
        return "ithor", "not_applicable"
    for split in ("-train", "-val", "-test"):
        if scene_source.endswith(split):
            return scene_source[: -len(split)], split.removeprefix("-")
    return scene_source, "not_applicable"


def _molmospaces_module_status() -> tuple[bool, str]:
    try:
        importlib.import_module("molmo_spaces.molmo_spaces_constants")
    except ModuleNotFoundError as exc:
        return False, f"module_not_importable:{exc.name}"
    except Exception as exc:  # pragma: no cover - dependency import failures vary by host.
        return False, f"module_import_failed:{type(exc).__name__}:{exc}"
    return True, "module_importable"


def _molmospaces_scene_root_status(*, module_available: bool) -> tuple[Path | None, str]:
    if not module_available:
        return None, "molmo_spaces_module_unavailable"
    try:
        constants = importlib.import_module("molmo_spaces.molmo_spaces_constants")
        root = Path(constants.get_scenes_root())
    except Exception as exc:  # pragma: no cover - dependency import failures vary by host.
        return None, f"scene_root_unavailable:{type(exc).__name__}:{exc}"
    if not root.is_dir():
        return root, "scene_root_missing"
    return root, "scene_root_available"


def _source_availability_blocked_reason(
    *,
    module_available: bool,
    module_reason: str,
    root: Path | None,
    root_reason: str,
    source: str,
    source_exists: bool,
    missing_files: list[int],
) -> str:
    if not module_available:
        return (
            "MolmoSpaces Python module is not importable in this environment "
            f"({module_reason}); run uv sync --extra dev or install the declared MolmoSpaces "
            "runtime before source admission."
        )
    if root is None or not root.is_dir():
        return (
            "MolmoSpaces scene root is unavailable "
            f"({root_reason}); configure MLSPACES_ASSETS_DIR or install scene assets before "
            "source admission."
        )
    if not source_exists:
        return (
            f"MolmoSpaces scene source directory is missing for {source}: {root / source}; "
            "install that source before scanner admission."
        )
    if missing_files:
        return (
            f"MolmoSpaces scene source {source} is missing candidate XML files for indices "
            f"{missing_files}; run source preparation before sampler admission."
        )
    return ""


def _candidate_packet_from_sampler_row(row: SceneSamplerRow) -> dict[str, Any]:
    preview_statuses: dict[str, str] = {}
    if row.scene_source == "procthor-10k-val" and row.scene_index is not None:
        preview_statuses = _view_statuses(_preview_metadata(row.scene_index))
    return {
        "scene_family": row.scene_family,
        "scene_split": row.scene_split,
        "scene_source": row.scene_source,
        "scene_index": row.scene_index,
        "backend": row.backend,
        "world_id": row.world_id,
        "readiness_status": row.readiness_status,
        "lanes": list(row.lanes),
        "ui_ready": row.ui_ready,
        "eval_ready": row.eval_ready,
        "room_count": row.room_count,
        "waypoint_count": row.waypoint_count,
        "category_provenance": row.category_provenance,
        "category_manifest": row.category_manifest,
        "preview_statuses": preview_statuses,
        "preview_assets": [
            {"view": view, "path": path} for view, path in row.preview_assets
        ],
        "selected_reason": row.selected_reason,
        "blocked_reason": row.blocked_reason,
        "failure_class": row.failure_class,
        "quality_score": row.quality_score,
        "coverage_score": row.coverage_score,
    }


def _blocked_candidate_packet(
    *,
    source: str,
    scene_index: int,
    source_availability: dict[str, Any],
) -> dict[str, Any]:
    family, split = _family_split(source)
    candidate_file = next(
        (
            item
            for item in source_availability.get("candidate_files") or []
            if item.get("scene_index") == scene_index
        ),
        {},
    )
    blocked_reason = str(source_availability.get("blocked_reason") or "")
    if not blocked_reason:
        blocked_reason = (
            f"{source}/{scene_index} has no sampler preview, room, waypoint, or "
            "map-build readiness packet yet; run scene preparation before admission."
        )
    return {
        "scene_family": family,
        "scene_split": split,
        "scene_source": source,
        "scene_index": scene_index,
        "backend": PRIMARY_MOLMOSPACES_BACKEND,
        "world_id": f"molmospaces/{source}/{scene_index}",
        "readiness_status": READINESS_BLOCKED,
        "lanes": [],
        "ui_ready": False,
        "eval_ready": False,
        "room_count": 0,
        "waypoint_count": 0,
        "category_provenance": "unavailable",
        "category_manifest": "",
        "preview_statuses": {},
        "preview_assets": [],
        "selected_reason": "blocked_until_candidate_readiness_packet_exists",
        "blocked_reason": blocked_reason,
        "failure_class": "environment_blocked",
        "quality_score": 0.0,
        "coverage_score": 0.0,
        "source_availability_status": source_availability.get("status"),
        "candidate_file": candidate_file,
    }


def _selection_candidate_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_source": candidate["scene_source"],
        "scene_index": candidate["scene_index"],
        "world_id": candidate["world_id"],
        "readiness_status": candidate["readiness_status"],
        "failure_class": candidate["failure_class"],
        "blocked_reason": candidate["blocked_reason"],
        "source_availability_status": candidate.get("source_availability_status", ""),
        "candidate_file": candidate.get("candidate_file", {}),
    }


def _unique_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int]] = set()
    unique: list[dict[str, Any]] = []
    for candidate in candidates:
        key = (str(candidate["scene_source"]), int(candidate["scene_index"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _parse_scene_index(raw_value: str, *, world_id: str) -> int:
    try:
        scene_index = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"unsupported MolmoSpaces scene index {raw_value!r}: {world_id}") from exc
    if scene_index < 0:
        raise ValueError(f"unsupported negative MolmoSpaces scene index {scene_index}: {world_id}")
    return scene_index


def _validate_ready_row(row: dict[str, Any], *, label_manifest: dict[str, Any]) -> None:
    source = str(row.get("scene_source") or "")
    index = row.get("scene_index")
    if not isinstance(index, int):
        raise ValueError(f"ready sampler row for {source} needs integer scene_index")
    if int(row.get("room_count") or 0) < 3:
        raise ValueError(f"{source}/{index} has fewer than three public rooms")
    if int(row.get("waypoint_count") or 0) < int(row.get("room_count") or 0):
        raise ValueError(f"{source}/{index} lacks one waypoint per public room")
    if str(row.get("category_provenance") or "") not in {
        "source_metadata",
        "prepared_visual_label_manifest",
    }:
        raise ValueError(f"{source}/{index} lacks trusted room-category provenance")
    _validate_no_heuristic_category_provenance(row)
    if not _labels_for_scene(label_manifest, source=source, scene_index=index):
        raise ValueError(f"{source}/{index} lacks prepared room labels")
    views = {item.get("view"): item.get("path") for item in row.get("preview_assets") or []}
    for view in _required_views():
        path = views.get(view)
        if not path:
            raise ValueError(f"{source}/{index} lacks {view} preview path")


def _validate_no_heuristic_category_provenance(row: dict[str, Any]) -> None:
    forbidden = {"heuristic_room_label", "heuristic_room_count", "room_area_fallback"}
    provenance = str(row.get("category_provenance") or "")
    if provenance in forbidden:
        raise ValueError("heuristic room-category provenance cannot satisfy sampler admission")


def _validate_label_manifest(payload: dict[str, Any]) -> None:
    rows = payload.get("labels")
    if not isinstance(rows, list):
        raise ValueError("room label manifest labels must be a list")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("room label rows must be objects")
        _validate_no_heuristic_category_provenance(row)
        provenance = str(row.get("category_provenance") or "")
        if provenance not in {"prepared_visual_label_manifest", "source_metadata"}:
            raise ValueError("room label row must use trusted provenance")


def _labels_for_scene(
    payload: dict[str, Any],
    *,
    source: str,
    scene_index: int,
) -> list[dict[str, Any]]:
    return [
        row
        for row in payload.get("labels") or []
        if isinstance(row, dict)
        and row.get("scene_source") == source
        and row.get("scene_index") == scene_index
    ]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]
