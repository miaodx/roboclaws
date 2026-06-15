"""Source-aware MolmoSpaces scene sampler contract."""

from __future__ import annotations

import importlib
import io
import json
import platform
import shlex
import sys
from contextlib import redirect_stdout
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
_EVAL_READY_INDICES: tuple[int, ...] = (0, 2, 3, 5, 9, 10, 11, 12, 13, 15)
_SCANNER_EVAL_READY_METADATA: dict[int, dict[str, Any]] = {
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
}
_PREVIEW_ROOT = Path(__file__).resolve().parents[1] / "operator_console" / "static" / "previews"
_SCANNER_OUTPUT_ROOT = Path("output") / "scene-sampler-scanner"
_SCANNER_PREVIEW_ROOT = _SCANNER_OUTPUT_ROOT / "previews"
_SCANNER_PRODUCT_SMOKE_ROOT = _SCANNER_OUTPUT_ROOT / "product-smoke"
_LABEL_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "molmospaces"
    / ("scene_sampler_room_labels.json")
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
            "preview_assets": [{"view": view, "path": path} for view, path in self.preview_assets],
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

    known_indices = sorted({*_CURRENT_ALIAS_INDICES, *_EVAL_READY_INDICES})
    rows = [_ready_row(index) for index in known_indices]
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
    total_ready_count = 0
    total_blocked_count = 0
    total_rejected_count = 0
    total_blocked_or_rejected_row_count = 0
    total_remaining_count = 0
    for source in SUPPORTED_SCENE_SOURCES:
        ready = [row for row in rows if row.scene_source == source]
        blocked_or_rejected = [
            row for row in sampler_rows() if row.scene_source == source and row.blocked_reason
        ]
        blocked = [row for row in blocked_or_rejected if row.readiness_status == READINESS_BLOCKED]
        rejected = [
            row for row in blocked_or_rejected if row.readiness_status == READINESS_REJECTED
        ]
        ready_count = len(ready)
        blocked_count = len(blocked)
        rejected_count = len(rejected)
        blocked_or_rejected_row_count = len(blocked_or_rejected)
        remaining_count = max(0, EVAL_TARGET_PER_SCENE_SOURCE - ready_count)
        support_status = _eval_projection_support_status(
            ready_count=ready_count,
            blocked_count=blocked_count,
            target_count=EVAL_TARGET_PER_SCENE_SOURCE,
        )
        total_ready_count += ready_count
        total_blocked_count += blocked_count
        total_rejected_count += rejected_count
        total_blocked_or_rejected_row_count += blocked_or_rejected_row_count
        total_remaining_count += remaining_count
        by_source[source] = {
            "target_count": EVAL_TARGET_PER_SCENE_SOURCE,
            "ready_count": ready_count,
            "partial_gap_count": remaining_count,
            "needed_count": remaining_count,
            "blocked_count": blocked_count,
            "rejected_count": rejected_count,
            "blocked_or_rejected_row_count": blocked_or_rejected_row_count,
            "support_status": support_status,
            "status": (
                "complete" if ready_count == EVAL_TARGET_PER_SCENE_SOURCE else "partial_or_blocked"
            ),
            "sample_ids": [eval_sample_id(row) for row in ready],
            "blocked_rows": [row.to_dict() for row in blocked_or_rejected],
        }
    return {
        "schema": SAMPLER_PROJECTION_SCHEMA,
        "projection": EVAL_STRESS_LANE,
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "scene_sources": by_source,
        "summary": {
            "source_count": len(SUPPORTED_SCENE_SOURCES),
            "target_sample_count": len(SUPPORTED_SCENE_SOURCES) * EVAL_TARGET_PER_SCENE_SOURCE,
            "ready_sample_count": total_ready_count,
            "partial_source_count": sum(
                1 for payload in by_source.values() if payload["support_status"] == "partial"
            ),
            "blocked_source_count": sum(
                1 for payload in by_source.values() if payload["support_status"] == "blocked"
            ),
            "complete_source_count": sum(
                1 for payload in by_source.values() if payload["support_status"] == "complete"
            ),
            "blocked_row_count": total_blocked_count,
            "rejected_row_count": total_rejected_count,
            "blocked_or_rejected_row_count": total_blocked_or_rejected_row_count,
            "remaining_sample_count": total_remaining_count,
        },
    }


def eval_suite_payload() -> dict[str, Any]:
    """Return generated scene-sampler eval suite JSON from admitted rows."""

    rows = eval_sampler_rows()
    return {
        "schema": "roboclaws_eval_suite_v1",
        "suite_id": "household_world.scene_sampler_stress",
        "version": "2026-06-15",
        "capability": "household_world_scene_sampling",
        "sample_ids": [eval_sample_id(row) for row in rows],
        "sample_refs": [eval_sample_ref(row) for row in rows],
        "required_graders": [
            "artifacts",
            "privacy",
            "trajectory",
            "sampler_admission",
            "outcome",
        ],
        "thresholds": {
            "pass_at_1": 1.0,
            "private_truth_leak_count": 0,
            "trajectory_policy_violation_count": 0,
        },
        "metadata": {
            "runner_scope": "direct-runner source-aware MolmoSpaces map-build stress projection",
            "live_provider_required": False,
            "sampler_projection": eval_projection_metadata(),
        },
    }


def eval_sample_payload(row: SceneSamplerRow) -> dict[str, Any]:
    """Return generated scene-sampler eval sample JSON for one admitted row."""

    if not row.eval_ready or row.scene_index is None:
        raise ValueError("eval sample payload requires an eval-ready sampler row")
    return {
        "schema": "roboclaws_eval_sample_v1",
        "sample_id": eval_sample_id(row),
        "version": "2026-06-15",
        "surface": "household-world",
        "intent": "map-build",
        "preset": "map-build",
        "world": row.world_id,
        "backend": row.backend,
        "evidence_lane": "world-oracle-labels",
        "camera_labeler": "not_applicable",
        "scenario_setup": "baseline",
        "seed": 7,
        "prompt": "not_applicable",
        "goal_contract_hash": "unavailable",
        "allowed_agent_engines": ["direct-runner"],
        "provider_profiles": ["not_applicable"],
        "trial_count": 1,
        "required_graders": [
            "artifacts",
            "privacy",
            "trajectory",
            "sampler_admission",
            "outcome",
        ],
        "private_goal_reference": {
            "schema": "household_eval_private_goal_reference_v1",
            "private_truth_scope": "grader_only",
            "expected_runtime_metric_map": True,
        },
        "grader_config": {
            "min_public_semantic_anchors": 1,
            "min_generated_exploration_candidates": 1,
            "require_runtime_metric_map_schema": "runtime_metric_map_v1",
            "require_private_truth_absent": True,
            "require_source_map_not_mutated": True,
            "sampler_admission": {
                "schema": "molmospaces_scene_sampler_admission_v1",
                "scene_family": row.scene_family,
                "scene_split": row.scene_split,
                "scene_source": row.scene_source,
                "scene_index": row.scene_index,
                "room_count": row.room_count,
                "waypoint_count": row.waypoint_count,
                "category_provenance": row.category_provenance,
                "category_manifest": row.category_manifest,
                "generator_version": SAMPLER_GENERATOR_VERSION,
            },
        },
        "launch_overrides": _eval_sample_launch_overrides(row),
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
            "ui_status": ("ready" if len(ui_rows) == UI_TARGET_PER_SCENE_SOURCE else "not_visible"),
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
                1 for source in SUPPORTED_SCENE_SOURCES if by_source[source]["ui_status"] == "ready"
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

    module_available, module_reason, module_stdout = _molmospaces_module_status()
    root, root_reason, root_stdout = _molmospaces_scene_root_status(
        module_available=module_available
    )
    sources: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        dataset_name, split = _molmospaces_get_scenes_args(source)
        scene_index_map = _molmospaces_scene_index_map(
            source=source,
            dataset_name=dataset_name,
            split=split,
            candidate_indices=candidate_indices,
            module_available=module_available,
        )
        scene_refs_by_index = {
            item["scene_index"]: item for item in scene_index_map["candidate_scene_refs"]
        }
        source_dir = root / source if root is not None else None
        source_exists = bool(source_dir and source_dir.is_dir())
        candidate_files = []
        missing_files = []
        invalid_candidate_indices = []
        for index in candidate_indices:
            scene_ref = scene_refs_by_index.get(index)
            if scene_ref is not None:
                row = {
                    "scene_source": source,
                    "scene_index": index,
                    "path": scene_ref.get("primary_path", ""),
                    "exists": bool(scene_ref.get("all_paths_exist")),
                    "status": scene_ref.get("status", ""),
                    "source": "molmospaces_get_scenes",
                    "raw_ref_type": scene_ref.get("raw_ref_type", ""),
                    "paths": scene_ref.get("paths", []),
                    "missing_paths": scene_ref.get("missing_paths", []),
                }
                candidate_files.append(row)
                if scene_ref.get("status") == "missing_from_index_map":
                    invalid_candidate_indices.append(index)
                elif not row["exists"]:
                    missing_files.append(index)
                continue
            candidate_path = source_dir / f"val_{index}.xml" if source_dir else None
            row = {
                "scene_source": source,
                "scene_index": index,
                "path": str(candidate_path) if candidate_path else "",
                "exists": bool(candidate_path and candidate_path.is_file()),
                "status": "fallback_path_checked",
                "source": "legacy_val_xml_path",
            }
            candidate_files.append(row)
            if not row["exists"]:
                missing_files.append(index)
        status = (
            "available"
            if (
                source_exists
                and scene_index_map["status"] == "available"
                and not missing_files
                and not invalid_candidate_indices
            )
            else "blocked"
        )
        sources[source] = {
            "scene_source": source,
            "status": status,
            "module_available": module_available,
            "scene_root": str(root) if root is not None else "",
            "scene_root_available": bool(root and root.is_dir()),
            "molmospaces_dataset_name": dataset_name,
            "molmospaces_split": split,
            "molmospaces_scene_version": scene_index_map["version"],
            "scene_index_map_status": scene_index_map["status"],
            "scene_index_map_reason": scene_index_map["reason"],
            "scene_index_map_stdout": scene_index_map["stdout"],
            "source_dir": str(source_dir) if source_dir is not None else "",
            "source_dir_available": source_exists,
            "candidate_indices": list(candidate_indices),
            "candidate_files": candidate_files,
            "missing_candidate_indices": missing_files,
            "invalid_candidate_indices": invalid_candidate_indices,
            "blocked_reason": _source_availability_blocked_reason(
                module_available=module_available,
                module_reason=module_reason,
                root=root,
                root_reason=root_reason,
                source=source,
                source_exists=source_exists,
                missing_files=missing_files,
                invalid_candidate_indices=invalid_candidate_indices,
                scene_index_map=scene_index_map,
            ),
            "failure_class": "" if status == "available" else "environment_blocked",
        }
    return {
        "schema": "molmospaces_scene_source_availability_report_v1",
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "probe_mode": "no_download_no_vlm",
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "candidate_indices": list(candidate_indices),
        "molmospaces_module_available": module_available,
        "molmospaces_module_reason": module_reason,
        "molmospaces_module_stdout": module_stdout,
        "scene_root": str(root) if root is not None else "",
        "scene_root_reason": root_reason,
        "scene_root_stdout": root_stdout,
        "summary": _source_availability_summary(sources),
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
        source_candidate_indices = sorted(
            {
                *candidate_indices,
                *(
                    int(row.scene_index)
                    for row in sampler_rows()
                    if row.scene_source == source and row.scene_index is not None
                ),
            }
        )
        for index in source_candidate_indices:
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
        candidates = _assign_dynamic_candidate_lanes(
            source=source,
            candidates=candidates,
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
        "summary": _candidate_readiness_summary(sources),
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
            if (
                item["readiness_status"] == READINESS_BLOCKED
                and not item["eval_ready"]
                and (item.get("candidate_file") or {}).get("status") != "missing_from_index_map"
            )
        ]
        ui_scan_candidates = scanner_candidates[:ui_needed]
        eval_scan_candidates = scanner_candidates[:eval_needed]
        source_availability_status = (source_payload.get("source_availability") or {}).get("status")
        capacity_status = _selection_capacity_status(
            ui_needed=ui_needed,
            ui_available=len(ui_scan_candidates),
            eval_needed=eval_needed,
            eval_available=len(eval_scan_candidates),
        )
        sources[source] = {
            "scene_source": source,
            "ui_target_count": UI_TARGET_PER_SCENE_SOURCE,
            "ui_ready_count": ui_ready_count,
            "ui_needed_count": ui_needed,
            "ui_scan_candidate_count": len(ui_scan_candidates),
            "eval_target_count": EVAL_TARGET_PER_SCENE_SOURCE,
            "eval_ready_count": eval_ready_count,
            "eval_needed_count": eval_needed,
            "eval_scan_candidate_count": len(eval_scan_candidates),
            "status": "complete" if ui_needed == 0 and eval_needed == 0 else "incomplete",
            "source_availability_status": source_availability_status,
            "selection_capacity_status": capacity_status,
            "next_action": _selection_next_action(
                capacity_status=capacity_status,
                source_availability_status=source_availability_status,
            ),
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
        "summary": _selection_gap_summary(sources),
        "sources": sources,
    }


def source_prep_report(
    *,
    candidate_indices: tuple[int, ...] = tuple(range(10)),
) -> dict[str, Any]:
    """Return a no-download source-preparation plan for scanner admission work."""

    availability = source_availability_report(candidate_indices=candidate_indices)
    selection = selection_gap_report(candidate_indices=candidate_indices)
    max_candidate_index = max(candidate_indices) if candidate_indices else -1
    sources: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        source_availability = availability["sources"][source]
        source_selection = selection["sources"][source]
        dataset_name, split = _molmospaces_get_scenes_args(source)
        candidate_scene_refs = [
            _candidate_scene_ref_from_availability(item)
            for item in source_availability.get("candidate_files") or []
            if isinstance(item, dict)
        ]
        source_complete = source_selection.get("status") == "complete"
        missing_resources = (
            []
            if source_complete
            else _missing_source_resources(
                source=source,
                source_availability=source_availability,
                candidate_scene_refs=candidate_scene_refs,
            )
        )
        recommended_end = max_candidate_index
        next_eval_count = len(source_selection.get("next_eval_scan_world_ids") or [])
        eval_needed = int(source_selection.get("eval_needed_count") or 0)
        if next_eval_count < eval_needed:
            recommended_end = max(recommended_end, 19)
        next_scan_candidates = (
            [] if source_complete else source_selection.get("next_scan_candidates") or []
        )
        sources[source] = {
            "scene_source": source,
            "scene_family": _family_split(source)[0],
            "scene_split": _family_split(source)[1],
            "prep_status": _source_prep_status(
                source_availability=source_availability,
                source_selection=source_selection,
                missing_resources=missing_resources,
            ),
            "download_policy": "manual_operator_only",
            "molmospaces_scene_source": source,
            "molmospaces_dataset_name": dataset_name,
            "molmospaces_split": split,
            "molmospaces_get_scenes_call": f'get_scenes("{dataset_name}", "{split}")',
            "molmospaces_scene_version": source_availability.get("molmospaces_scene_version", ""),
            "scene_index_map_status": source_availability.get("scene_index_map_status", ""),
            "scene_index_map_reason": source_availability.get("scene_index_map_reason", ""),
            "scene_index_map_stdout": source_availability.get("scene_index_map_stdout", ""),
            "scene_asset_id": source,
            "source_dir": source_availability.get("source_dir", ""),
            "source_dir_available": bool(source_availability.get("source_dir_available")),
            "candidate_indices": list(candidate_indices),
            "candidate_scene_refs": [
                item
                for item in candidate_scene_refs
                if item.get("source") == "molmospaces_get_scenes"
            ],
            "missing_resource_count": len(missing_resources),
            "missing_resource_summary": _resource_reason_counts(missing_resources),
            "missing_resources": missing_resources,
            "next_scan_world_ids": [item.get("world_id") for item in next_scan_candidates],
            "install_candidates": [] if source_complete else _source_prep_install_candidates(
                dataset_name=dataset_name,
                split=split,
                candidates=next_scan_candidates,
            ),
            "recommended_candidate_range": f"0:{recommended_end}" if recommended_end >= 0 else "",
            "operator_commands": _source_prep_operator_commands(
                source=source,
                dataset_name=dataset_name,
                split=split,
                recommended_end=recommended_end,
            ),
        }
    worklist = _source_prep_worklist(sources)
    return {
        "schema": "molmospaces_scene_sampler_source_prep_v1",
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "probe_mode": "no_download_no_vlm",
        "download_policy": "manual_operator_only",
        "candidate_indices": list(candidate_indices),
        "worklist": worklist,
        "summary": {
            "source_count": len(SUPPORTED_SCENE_SOURCES),
            "sources_requiring_operator_prep_count": sum(
                1
                for source in sources.values()
                if str(source.get("prep_status", "")).startswith("blocked_")
            ),
            "missing_resource_count": sum(
                int(source.get("missing_resource_count") or 0) for source in sources.values()
            ),
            "missing_resource_summary": _resource_reason_counts(
                [
                    resource
                    for source in sources.values()
                    for resource in source.get("missing_resources", [])
                    if isinstance(resource, dict)
                ]
            ),
            "prep_status_counts": _source_prep_status_counts(sources),
            "worklist": worklist,
        },
        "sources": sources,
    }


def scanner_execution_plan(
    *,
    candidate_indices: tuple[int, ...] = tuple(range(10)),
) -> dict[str, Any]:
    """Return a no-download executable plan for the next scanner/product-smoke step."""

    source_prep = source_prep_report(candidate_indices=candidate_indices)
    scanner_admission = scanner_admission_report(candidate_indices=candidate_indices)
    sources: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        prep_source = source_prep["sources"][source]
        admission_by_world_id = {
            row.get("world_id"): row
            for row in scanner_admission["sources"][source].get("admission_rows") or []
            if isinstance(row, dict)
        }
        candidates = []
        for install_candidate in prep_source.get("install_candidates") or []:
            if not isinstance(install_candidate, dict):
                continue
            world_id = str(install_candidate.get("world_id") or "")
            admission = admission_by_world_id.get(world_id) or {}
            candidates.append(
                _scanner_execution_candidate(
                    install_candidate=install_candidate,
                    admission=admission,
                )
            )
        sources[source] = {
            "scene_source": source,
            "prep_status": prep_source.get("prep_status", ""),
            "download_policy": "manual_operator_only",
            "candidate_count": len(candidates),
            "ready_for_product_smoke_count": sum(
                1 for item in candidates if item["scanner_status"] == "ready_for_product_smoke"
            ),
            "blocked_count": sum(
                1 for item in candidates if item["scanner_status"].startswith("blocked_")
            ),
            "candidates": candidates,
        }
    return {
        "schema": "molmospaces_scene_sampler_scanner_execution_plan_v1",
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "probe_mode": "no_download_no_backend_no_vlm",
        "download_policy": "manual_operator_only",
        "candidate_indices": list(candidate_indices),
        "summary": _scanner_execution_summary(sources),
        "sources": sources,
    }


def next_flow_worklist_report(
    *,
    candidate_indices: tuple[int, ...] = tuple(range(10)),
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Return one next-Flow worklist across sampler selection, prep, and scanner gates."""

    artifact_paths = _next_flow_artifact_paths(output_dir=output_dir)
    projection = eval_projection_metadata()
    readiness = readiness_report()
    selection = selection_gap_report(candidate_indices=candidate_indices)
    source_prep = source_prep_report(candidate_indices=candidate_indices)
    scanner_admission = scanner_admission_report(candidate_indices=candidate_indices)
    scanner_execution = scanner_execution_plan(candidate_indices=candidate_indices)
    sources: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        source_projection = projection["scene_sources"][source]
        source_readiness = readiness["sources"][source]
        source_selection = selection["sources"][source]
        source_prep_payload = source_prep["sources"][source]
        source_admission = scanner_admission["sources"][source]
        source_execution = scanner_execution["sources"][source]
        scanner_ready_world_ids = [
            item.get("world_id")
            for item in source_execution.get("candidates") or []
            if isinstance(item, dict)
            and item.get("scanner_status") == "ready_for_product_smoke"
            and item.get("world_id")
        ]
        missing_gate_counts = _next_flow_missing_gate_counts(source_admission)
        next_action = _next_flow_next_action(
            readiness_source=source_readiness,
            selection_source=source_selection,
            prep_source=source_prep_payload,
            scanner_source=source_execution,
        )
        sources[source] = {
            "scene_source": source,
            "scene_family": source_prep_payload.get("scene_family", ""),
            "scene_split": source_prep_payload.get("scene_split", ""),
            "flow_status": _next_flow_status(
                readiness_source=source_readiness,
                prep_source=source_prep_payload,
                scanner_source=source_execution,
            ),
            "next_action": next_action,
            "ui_target_count": UI_TARGET_PER_SCENE_SOURCE,
            "ui_ready_count": int(source_readiness.get("ui_ready_count") or 0),
            "ui_needed_count": int(source_selection.get("ui_needed_count") or 0),
            "ui_status": source_readiness.get("ui_status", ""),
            "ui_world_ids": source_readiness.get("ui_world_ids") or [],
            "eval_target_count": EVAL_TARGET_PER_SCENE_SOURCE,
            "eval_ready_count": int(source_readiness.get("eval_ready_count") or 0),
            "eval_needed_count": int(source_selection.get("eval_needed_count") or 0),
            "eval_status": source_readiness.get("eval_status", ""),
            "eval_support_status": source_projection.get("support_status", ""),
            "eval_sample_ids": source_readiness.get("eval_sample_ids") or [],
            "selection_capacity_status": source_selection.get("selection_capacity_status", ""),
            "source_availability_status": source_selection.get("source_availability_status", ""),
            "prep_status": source_prep_payload.get("prep_status", ""),
            "scanner_candidate_count": int(source_execution.get("candidate_count") or 0),
            "scanner_ready_candidate_count": int(
                source_execution.get("ready_for_product_smoke_count") or 0
            ),
            "scanner_blocked_candidate_count": int(source_execution.get("blocked_count") or 0),
            "scanner_ready_world_ids": scanner_ready_world_ids,
            "next_scan_world_ids": _next_flow_scan_world_ids(source_selection),
            "missing_resource_count": int(source_prep_payload.get("missing_resource_count") or 0),
            "missing_resource_summary": source_prep_payload.get("missing_resource_summary") or {},
            "missing_gate_counts": missing_gate_counts,
            "blocked_reason_samples": _next_flow_blocked_reason_samples(
                projection_source=source_projection,
                prep_source=source_prep_payload,
                scanner_source=source_execution,
            ),
            "operator_command_names": [
                command.get("name")
                for command in source_prep_payload.get("operator_commands") or []
                if isinstance(command, dict) and command.get("name")
            ],
            "recommended_candidate_range": source_prep_payload.get(
                "recommended_candidate_range", ""
            ),
            "recommended_commands": _next_flow_recommended_commands(
                source=source,
                next_action=next_action,
                recommended_candidate_range=str(
                    source_prep_payload.get("recommended_candidate_range") or ""
                ),
                artifact_paths=artifact_paths,
            ),
        }
    summary = _next_flow_summary(sources)
    return {
        "schema": "molmospaces_scene_sampler_next_flow_worklist_v1",
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "probe_mode": "no_download_no_backend_no_vlm",
        "download_policy": "manual_operator_only",
        "candidate_indices": list(candidate_indices),
        "artifact_paths": artifact_paths,
        "worklist": summary["worklist"],
        "summary": summary,
        "sources": sources,
    }


def scanner_admission_report(
    *,
    candidate_indices: tuple[int, ...] = tuple(range(10)),
) -> dict[str, Any]:
    """Return no-download scanner admission rows for candidate readiness work."""

    candidates = candidate_readiness_report(candidate_indices=candidate_indices)
    selection = selection_gap_report(candidate_indices=candidate_indices)
    sources: dict[str, dict[str, Any]] = {}
    for source in SUPPORTED_SCENE_SOURCES:
        source_candidates = candidates["sources"][source]
        source_selection = selection["sources"][source]
        admission_rows = [
            _scanner_admission_row(candidate)
            for candidate in source_candidates.get("candidates") or []
        ]
        sources[source] = {
            "scene_source": source,
            "ui_target_count": UI_TARGET_PER_SCENE_SOURCE,
            "eval_target_count": EVAL_TARGET_PER_SCENE_SOURCE,
            "ready_ui_count": int(source_candidates.get("ui_ready_count") or 0),
            "ready_eval_count": int(source_candidates.get("eval_ready_count") or 0),
            "needed_ui_count": int(source_selection.get("ui_needed_count") or 0),
            "needed_eval_count": int(source_selection.get("eval_needed_count") or 0),
            "next_scan_world_ids": [
                item.get("world_id") for item in source_selection.get("next_scan_candidates") or []
            ],
            "admission_rows": admission_rows,
            "summary": {
                "admitted_count": sum(
                    1 for item in admission_rows if item["admission_status"] == "admitted"
                ),
                "rejected_count": sum(
                    1 for item in admission_rows if item["admission_status"] == "rejected"
                ),
                "blocked_count": sum(
                    1 for item in admission_rows if item["admission_status"] == "blocked"
                ),
            },
        }
    return {
        "schema": "molmospaces_scene_sampler_scanner_admission_v1",
        "generator_version": SAMPLER_GENERATOR_VERSION,
        "probe_mode": "no_download_no_backend_no_vlm",
        "candidate_indices": list(candidate_indices),
        "required_gates": list(_scanner_required_gates()),
        "summary": _scanner_admission_summary(sources),
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
                f"scene_source {source} exposes more than {UI_TARGET_PER_SCENE_SOURCE} UI samples"
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
    scanner_metadata = _SCANNER_EVAL_READY_METADATA.get(scene_index)
    preview = _ready_row_preview_metadata(scene_index)
    room_ids = _room_ids(preview)
    room_count = int((scanner_metadata or {}).get("room_count") or len(room_ids))
    waypoint_count = int((scanner_metadata or {}).get("waypoint_count") or _waypoint_count(preview))
    view_statuses = _view_statuses(preview)
    all_views_reviewable = all(
        view_statuses.get(view) == "reviewable" for view in _required_views()
    )
    ui_ready = scene_index in _UI_SELECTED_INDICES
    eval_ready = scene_index in _EVAL_READY_INDICES
    rejected_reason = ""
    if room_count < 3:
        rejected_reason = "fewer_than_three_public_navigation_areas"
    elif not all_views_reviewable:
        rejected_reason = "preview_not_reviewable"
    status = (
        READINESS_READY if (ui_ready or eval_ready) and not rejected_reason else READINESS_REJECTED
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
        world_id=_procthor_world_id(scene_index),
        legacy_world_id=_procthor_legacy_world_id(scene_index),
        room_count=room_count,
        waypoint_count=waypoint_count,
        category_provenance="prepared_visual_label_manifest",
        category_manifest=str(_LABEL_MANIFEST_PATH.relative_to(_repo_root())),
        preview_assets=_ready_row_preview_assets(scene_index),
        selected_reason=selected_reason,
        blocked_reason=rejected_reason,
        failure_class="map_actionability_failure" if rejected_reason else "",
        quality_score=float(
            (scanner_metadata or {}).get("quality_score") or _quality_score(preview)
        ),
        coverage_score=float(
            (scanner_metadata or {}).get("coverage_score")
            or _coverage_score(room_count=room_count, waypoint_count=waypoint_count)
        ),
    )


def _procthor_world_id(scene_index: int) -> str:
    if scene_index in _CURRENT_ALIAS_INDICES:
        return f"molmospaces/val_{scene_index}"
    return f"molmospaces/procthor-10k-val/{scene_index}"


def _procthor_legacy_world_id(scene_index: int) -> str:
    if scene_index in _CURRENT_ALIAS_INDICES:
        return f"molmospaces/val_{scene_index}"
    return ""


def _eval_sample_launch_overrides(row: SceneSamplerRow) -> dict[str, Any]:
    overrides: dict[str, Any] = {
        "agent_engine": "direct-runner",
        "evidence_lane": "world-oracle-labels",
        "seed": 7,
        "scenario_setup": "baseline",
        "scene_source": row.scene_source,
        "scene_index": int(row.scene_index),
    }
    return overrides


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


def _eval_projection_support_status(
    *,
    ready_count: int,
    blocked_count: int,
    target_count: int,
) -> str:
    if ready_count == target_count:
        return "complete"
    if ready_count > 0:
        return "partial"
    if blocked_count > 0:
        return "blocked"
    return "not_started"


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


def _ready_row_preview_metadata(scene_index: int) -> dict[str, Any]:
    if scene_index in _SCANNER_EVAL_READY_METADATA:
        preview = _scanner_preview_metadata("procthor-10k-val", scene_index)
        return preview or _static_scanner_preview_metadata(scene_index)
    return _preview_metadata(scene_index)


def _static_scanner_preview_metadata(scene_index: int) -> dict[str, Any]:
    metadata = _SCANNER_EVAL_READY_METADATA[scene_index]
    room_count = int(metadata["room_count"])
    waypoint_count = int(metadata["waypoint_count"])
    room_ids = [f"room_{index}" for index in range(room_count)]
    projected_waypoints = [
        {"waypoint_id": f"wp_{index}", "room_id": room_ids[index % room_count]}
        for index in range(waypoint_count)
    ]
    views = {
        view: {"image_diagnostics": {"visual_status": "reviewable"}}
        for view in _required_views()
    }
    views["map"]["semantic_projection"] = {
        "rendered_waypoint_count": waypoint_count,
        "projected_waypoints": projected_waypoints,
    }
    return {
        "scene_source": "procthor-10k-val",
        "scene_index": scene_index,
        "backend": PRIMARY_MOLMOSPACES_BACKEND,
        "views": views,
    }


def _view_statuses(preview: dict[str, Any]) -> dict[str, str]:
    views = preview.get("views") if isinstance(preview.get("views"), dict) else {}
    return {
        view: str((payload.get("image_diagnostics") or {}).get("visual_status") or "")
        for view, payload in views.items()
        if isinstance(payload, dict)
    }


def _room_ids(preview: dict[str, Any]) -> tuple[str, ...]:
    semantic_projection = ((preview.get("views") or {}).get("map") or {}).get(
        "semantic_projection"
    ) or {}
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
    semantic_projection = ((preview.get("views") or {}).get("map") or {}).get(
        "semantic_projection"
    ) or {}
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


def _ready_row_preview_assets(scene_index: int) -> tuple[tuple[str, str], ...]:
    if scene_index not in _SCANNER_EVAL_READY_METADATA:
        return _preview_assets(scene_index)
    slug = _world_id_slug(f"molmospaces/procthor-10k-val/{scene_index}")
    return tuple(
        (view, str(_SCANNER_PREVIEW_ROOT / f"{slug}-{view}.png"))
        for view in _required_views()
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


def _molmospaces_module_status() -> tuple[bool, str, str]:
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            importlib.import_module("molmo_spaces.molmo_spaces_constants")
    except ModuleNotFoundError as exc:
        return False, f"module_not_importable:{exc.name}", stdout.getvalue()
    except Exception as exc:  # pragma: no cover - dependency import failures vary by host.
        return False, f"module_import_failed:{type(exc).__name__}:{exc}", stdout.getvalue()
    return True, "module_importable", stdout.getvalue()


def _molmospaces_scene_root_status(
    *,
    module_available: bool,
) -> tuple[Path | None, str, str]:
    if not module_available:
        return None, "molmo_spaces_module_unavailable", ""
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            constants = importlib.import_module("molmo_spaces.molmo_spaces_constants")
            root = Path(constants.get_scenes_root())
    except Exception as exc:  # pragma: no cover - dependency import failures vary by host.
        return None, f"scene_root_unavailable:{type(exc).__name__}:{exc}", stdout.getvalue()
    if not root.is_dir():
        return root, "scene_root_missing", stdout.getvalue()
    return root, "scene_root_available", stdout.getvalue()


def _source_availability_blocked_reason(
    *,
    module_available: bool,
    module_reason: str,
    root: Path | None,
    root_reason: str,
    source: str,
    source_exists: bool,
    missing_files: list[int],
    invalid_candidate_indices: list[int],
    scene_index_map: dict[str, Any],
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
    if scene_index_map.get("status") != "available":
        return (
            f"MolmoSpaces get_scenes index map is unavailable for {source} "
            f"({scene_index_map.get('reason')}); source preparation must resolve the index "
            "map before sampler admission."
        )
    if invalid_candidate_indices:
        return (
            f"MolmoSpaces scene source {source} has no get_scenes entries for candidate "
            f"indices {invalid_candidate_indices}; choose valid source-specific indices before "
            "scanner admission."
        )
    if missing_files:
        return (
            f"MolmoSpaces scene source {source} has missing get_scenes file paths for indices "
            f"{missing_files}; run source preparation before sampler admission."
        )
    return ""


def _source_availability_summary(
    sources: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "source_count": len(sources),
        "available_source_count": sum(
            1 for source in sources.values() if source.get("status") == "available"
        ),
        "blocked_source_count": sum(
            1 for source in sources.values() if source.get("status") != "available"
        ),
        "scene_root_available_source_count": sum(
            1 for source in sources.values() if source.get("scene_root_available")
        ),
        "source_dir_available_count": sum(
            1 for source in sources.values() if source.get("source_dir_available")
        ),
        "scene_index_map_available_count": sum(
            1 for source in sources.values() if source.get("scene_index_map_status") == "available"
        ),
        "missing_candidate_count": sum(
            len(source.get("missing_candidate_indices") or []) for source in sources.values()
        ),
        "invalid_candidate_count": sum(
            len(source.get("invalid_candidate_indices") or []) for source in sources.values()
        ),
    }


def _molmospaces_get_scenes_args(scene_source: str) -> tuple[str, str]:
    if scene_source == "ithor":
        return "ithor", "train"
    family, split = _family_split(scene_source)
    if split == "not_applicable":
        split = "train"
    return family, split


def _molmospaces_scene_index_map(
    *,
    source: str,
    dataset_name: str,
    split: str,
    candidate_indices: tuple[int, ...],
    module_available: bool,
) -> dict[str, Any]:
    if not module_available:
        return {
            "source": source,
            "dataset_name": dataset_name,
            "split": split,
            "status": "blocked",
            "reason": "molmo_spaces_module_unavailable",
            "version": "",
            "stdout": "",
            "candidate_scene_refs": [],
        }
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            constants = importlib.import_module("molmo_spaces.molmo_spaces_constants")
            mapping, version = constants.get_scenes(dataset_name, split, return_version=True)
    except Exception as exc:  # pragma: no cover - dependency failures vary by host.
        return {
            "source": source,
            "dataset_name": dataset_name,
            "split": split,
            "status": "blocked",
            "reason": f"get_scenes_failed:{type(exc).__name__}:{exc}",
            "version": "",
            "stdout": stdout.getvalue(),
            "candidate_scene_refs": [],
        }
    split_mapping = mapping.get(split) if isinstance(mapping, dict) else None
    if not isinstance(split_mapping, dict):
        return {
            "source": source,
            "dataset_name": dataset_name,
            "split": split,
            "status": "blocked",
            "reason": "split_map_missing",
            "version": str(version or ""),
            "stdout": stdout.getvalue(),
            "candidate_scene_refs": [],
        }
    candidate_scene_refs = [
        _candidate_scene_ref(
            source=source,
            scene_index=index,
            raw_ref=split_mapping.get(index),
        )
        for index in candidate_indices
    ]
    return {
        "source": source,
        "dataset_name": dataset_name,
        "split": split,
        "status": "available",
        "reason": "",
        "version": str(version or ""),
        "stdout": stdout.getvalue(),
        "candidate_scene_refs": candidate_scene_refs,
    }


def _candidate_scene_ref(
    *,
    source: str,
    scene_index: int,
    raw_ref: Any,
) -> dict[str, Any]:
    paths = _scene_ref_paths(raw_ref)
    return {
        "scene_source": source,
        "scene_index": scene_index,
        "status": "available" if paths else "missing_from_index_map",
        "raw_ref_type": type(raw_ref).__name__,
        "paths": paths,
        "primary_path": _primary_scene_ref_path(paths),
        "all_paths_exist": bool(paths) and all(path["exists"] for path in paths),
        "missing_paths": [
            path["path"] for path in paths if path.get("path") and not path["exists"]
        ],
    }


def _candidate_scene_ref_from_availability(candidate_file: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_source": candidate_file.get("scene_source", ""),
        "scene_index": candidate_file.get("scene_index"),
        "status": candidate_file.get("status", ""),
        "source": candidate_file.get("source", ""),
        "raw_ref_type": candidate_file.get("raw_ref_type", ""),
        "paths": candidate_file.get("paths", []),
        "primary_path": candidate_file.get("path", ""),
        "all_paths_exist": bool(candidate_file.get("exists")),
        "missing_paths": candidate_file.get("missing_paths", []),
    }


def _scene_ref_paths(raw_ref: Any) -> list[dict[str, Any]]:
    if raw_ref is None:
        return []
    if isinstance(raw_ref, str | Path):
        path = Path(raw_ref)
        return [{"role": "base", "path": str(raw_ref), "exists": path.is_file()}]
    if isinstance(raw_ref, dict):
        paths = []
        for role, raw_path in sorted(raw_ref.items()):
            if raw_path is None:
                continue
            path = Path(str(raw_path))
            paths.append({"role": str(role), "path": str(raw_path), "exists": path.is_file()})
        return paths
    return []


def _primary_scene_ref_path(paths: list[dict[str, Any]]) -> str:
    for role in ("base", "physics", "ceiling"):
        for path in paths:
            if path.get("role") == role:
                return str(path.get("path") or "")
    if paths:
        return str(paths[0].get("path") or "")
    return ""


def _missing_source_resources(
    *,
    source: str,
    source_availability: dict[str, Any],
    candidate_scene_refs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    source_dir = str(source_availability.get("source_dir") or "")
    if not source_availability.get("source_dir_available"):
        resources.append(
            {
                "resource_type": "scene_source_dir",
                "scene_source": source,
                "path": source_dir,
                "reason": "source_dir_missing",
            }
        )
    for scene_ref in candidate_scene_refs:
        if not isinstance(scene_ref, dict):
            continue
        scene_index = scene_ref.get("scene_index")
        if scene_ref.get("status") == "missing_from_index_map":
            resources.append(
                {
                    "resource_type": "scene_index_map_entry",
                    "scene_source": source,
                    "scene_index": scene_index,
                    "path": "",
                    "reason": "scene_index_missing_from_get_scenes",
                }
            )
        for missing_path in scene_ref.get("missing_paths") or []:
            resources.append(
                {
                    "resource_type": "molmospaces_scene_path",
                    "scene_source": source,
                    "scene_index": scene_index,
                    "path": missing_path,
                    "reason": "get_scenes_path_missing",
                }
            )
    for item in source_availability.get("candidate_files") or []:
        if not isinstance(item, dict) or item.get("exists"):
            continue
        resources.append(
            {
                "resource_type": "scene_xml",
                "scene_source": source,
                "scene_index": item.get("scene_index"),
                "path": item.get("path", ""),
                "reason": "candidate_xml_missing",
            }
        )
    return resources


def _source_prep_status(
    *,
    source_availability: dict[str, Any],
    source_selection: dict[str, Any],
    missing_resources: list[dict[str, Any]],
) -> str:
    if source_selection.get("status") == "complete":
        return "complete"
    if source_availability.get("module_available") is False:
        return "blocked_molmospaces_module"
    if not source_availability.get("scene_root_available"):
        return "blocked_scene_root"
    if missing_resources:
        return "blocked_missing_resources"
    if source_selection.get("status") != "complete":
        return "ready_for_scanner"
    return "complete"


def _resource_reason_counts(resources: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    by_type: dict[str, int] = {}
    by_reason: dict[str, int] = {}
    for resource in resources:
        resource_type = str(resource.get("resource_type") or "unknown")
        reason = str(resource.get("reason") or "unknown")
        by_type[resource_type] = by_type.get(resource_type, 0) + 1
        by_reason[reason] = by_reason.get(reason, 0) + 1
    return {
        "by_resource_type": dict(sorted(by_type.items())),
        "by_reason": dict(sorted(by_reason.items())),
    }


def _source_prep_status_counts(sources: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for source in sources.values():
        status = str(source.get("prep_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def _source_prep_worklist(sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scene_source": source.get("scene_source", ""),
            "prep_status": source.get("prep_status", ""),
            "next_action": _source_prep_next_action(str(source.get("prep_status") or "")),
            "missing_resource_count": int(source.get("missing_resource_count") or 0),
            "missing_resource_summary": source.get("missing_resource_summary") or {},
            "next_scan_world_ids": source.get("next_scan_world_ids") or [],
            "install_candidate_count": len(source.get("install_candidates") or []),
            "recommended_candidate_range": source.get("recommended_candidate_range", ""),
            "operator_command_names": [
                command.get("name")
                for command in source.get("operator_commands") or []
                if isinstance(command, dict) and command.get("name")
            ],
        }
        for source in sources.values()
        if source.get("prep_status") != "complete"
    ]


def _source_prep_next_action(prep_status: str) -> str:
    if prep_status == "complete":
        return "none"
    if prep_status == "ready_for_scanner":
        return "run_scanner_admission"
    if prep_status == "blocked_molmospaces_module":
        return "install_repo_dev_runtime"
    if prep_status == "blocked_scene_root":
        return "configure_or_install_molmospaces_scene_root"
    if prep_status == "blocked_missing_resources":
        return "run_manual_source_prep"
    return "inspect_source_prep"


def _source_prep_operator_commands(
    *,
    source: str,
    dataset_name: str,
    split: str,
    recommended_end: int,
) -> list[dict[str, str]]:
    return [
        {
            "name": "inspect_scene_index_map",
            "description": (
                "List the MolmoSpaces scene map for this source without forcing downloads."
            ),
            "command": (
                ".venv/bin/python - <<'PY'\n"
                "from molmo_spaces.molmo_spaces_constants import get_scenes\n"
                f'mapping = get_scenes("{dataset_name}", "{split}")\n'
                f'print(mapping["{split}"])\n'
                "PY"
            ),
        },
        {
            "name": "install_single_scene_example",
            "description": (
                "Operator-run example for installing one scene and its object/grasp assets."
            ),
            "command": (
                ".venv/bin/python - <<'PY'\n"
                "from molmo_spaces.molmo_spaces_constants import get_scenes\n"
                "from molmo_spaces.molmo_spaces_constants import get_scenes_root\n"
                "from molmo_spaces.utils.lazy_loading_utils import "
                "install_scene_with_objects_and_grasps_from_path\n"
                f"{_install_command_ref_helper()}"
                f'mapping = get_scenes("{dataset_name}", "{split}")["{split}"]\n'
                "scene_index, scene_ref = next(\n"
                "    (index, ref) for index, ref in sorted(mapping.items()) if ref\n"
                ")\n"
                "scene_path = _scene_xml_path_from_ref(scene_ref, get_scenes_root())\n"
                "install_scene_with_objects_and_grasps_from_path(scene_path)\n"
                "PY"
            ),
        },
        {
            "name": "rerun_readiness_after_prep",
            "description": "Refresh scanner prep artifacts after manual asset preparation.",
            "command": (
                ".venv/bin/python scripts/operator_console/"
                "export_scene_sampler_readiness.py "
                f"--candidate-range 0:{recommended_end} "
                f"--require-selection-capacity-source {source}"
            ),
        },
    ]


def _source_prep_install_candidates(
    *,
    dataset_name: str,
    split: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    install_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_file = candidate.get("candidate_file")
        if not isinstance(candidate_file, dict):
            candidate_file = {}
        scene_index = candidate.get("scene_index")
        install_candidates.append(
            {
                "scene_source": candidate.get("scene_source", ""),
                "scene_index": scene_index,
                "world_id": candidate.get("world_id", ""),
                "primary_path": candidate_file.get("path", ""),
                "path_source": candidate_file.get("source", ""),
                "path_status": candidate_file.get("status", ""),
                "paths": candidate_file.get("paths", []),
                "missing_paths": candidate_file.get("missing_paths", []),
                "install_command": _install_candidate_command(
                    dataset_name=dataset_name,
                    split=split,
                    scene_index=scene_index,
                ),
            }
        )
    return install_candidates


def _install_candidate_command(
    *,
    dataset_name: str,
    split: str,
    scene_index: Any,
) -> str:
    try:
        parsed_index = int(scene_index)
    except (TypeError, ValueError):
        return ""
    return (
        ".venv/bin/python - <<'PY'\n"
        "from molmo_spaces.molmo_spaces_constants import get_scenes\n"
        "from molmo_spaces.molmo_spaces_constants import get_scenes_root\n"
        "from molmo_spaces.utils.lazy_loading_utils import "
        "install_scene_with_objects_and_grasps_from_path\n"
        f"{_install_command_ref_helper()}"
        f'mapping = get_scenes("{dataset_name}", "{split}")["{split}"]\n'
        f"scene_ref = mapping[{parsed_index}]\n"
        "scene_path = _scene_xml_path_from_ref(scene_ref, get_scenes_root())\n"
        "install_scene_with_objects_and_grasps_from_path(scene_path)\n"
        "PY"
    )


def _install_command_ref_helper() -> str:
    return (
        "from pathlib import Path\n"
        "\n"
        "def _scene_xml_path_from_ref(scene_ref, scenes_root):\n"
        "    if isinstance(scene_ref, dict):\n"
        "        for role in ('base', 'physics', 'ceiling'):\n"
        "            raw_path = scene_ref.get(role)\n"
        "            if raw_path:\n"
        "                return _scene_path(raw_path, scenes_root)\n"
        "        for raw_path in scene_ref.values():\n"
        "            if raw_path:\n"
        "                return _scene_path(raw_path, scenes_root)\n"
        "    return _scene_path(scene_ref, scenes_root)\n"
        "\n"
        "def _scene_path(raw_path, scenes_root):\n"
        "    path = Path(str(raw_path))\n"
        "    if path.is_absolute():\n"
        "        return path\n"
        "    return Path(scenes_root) / path\n"
        "\n"
    )


def _scanner_required_gates() -> tuple[str, ...]:
    return (
        "source_asset_available",
        "preview_metadata",
        "public_room_count",
        "public_waypoints",
        "trusted_category_provenance",
        "map_build_artifacts",
    )


def _scanner_admission_row(candidate: dict[str, Any]) -> dict[str, Any]:
    status = str(candidate.get("readiness_status") or "")
    if status == READINESS_READY:
        return {
            **_scanner_admission_row_base(candidate),
            "admission_status": "admitted",
            "lanes": candidate.get("lanes") or [],
            "passed_gates": list(_scanner_required_gates()),
            "missing_gates": [],
            "next_action": "none",
        }
    if status == READINESS_REJECTED:
        return {
            **_scanner_admission_row_base(candidate),
            "admission_status": "rejected",
            "lanes": candidate.get("lanes") or [],
            "passed_gates": [],
            "missing_gates": [],
            "next_action": "do_not_scan_without_new_human_curation",
        }
    missing_gates = _scanner_missing_gates(candidate)
    return {
        **_scanner_admission_row_base(candidate),
        "admission_status": "blocked",
        "lanes": [],
        "passed_gates": [gate for gate in _scanner_required_gates() if gate not in missing_gates],
        "missing_gates": missing_gates,
        "next_action": _scanner_next_action(candidate, missing_gates=missing_gates),
    }


def _scanner_admission_row_base(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_family": candidate.get("scene_family", ""),
        "scene_split": candidate.get("scene_split", ""),
        "scene_source": candidate.get("scene_source", ""),
        "scene_index": candidate.get("scene_index"),
        "world_id": candidate.get("world_id", ""),
        "readiness_status": candidate.get("readiness_status", ""),
        "failure_class": candidate.get("failure_class", ""),
        "blocked_reason": candidate.get("blocked_reason", ""),
        "selected_reason": candidate.get("selected_reason", ""),
        "room_count": candidate.get("room_count", 0),
        "waypoint_count": candidate.get("waypoint_count", 0),
        "category_provenance": candidate.get("category_provenance", ""),
        "preview_statuses": candidate.get("preview_statuses", {}),
        "candidate_file": candidate.get("candidate_file", {}),
        "required_gates": list(_scanner_required_gates()),
    }


def _scanner_missing_gates(candidate: dict[str, Any]) -> list[str]:
    missing = []
    candidate_file = candidate.get("candidate_file")
    if not isinstance(candidate_file, dict) or not candidate_file.get("exists"):
        missing.append("source_asset_available")
    preview_statuses = candidate.get("preview_statuses")
    if not isinstance(preview_statuses, dict) or not all(
        _scanner_preview_status_passes(preview_statuses.get(view)) for view in _required_views()
    ):
        missing.append("preview_metadata")
    if int(candidate.get("room_count") or 0) < 3:
        missing.append("public_room_count")
    if int(candidate.get("waypoint_count") or 0) < 3:
        missing.append("public_waypoints")
    if candidate.get("category_provenance") not in {
        "source_metadata",
        "prepared_visual_label_manifest",
        "prepared_visual_room_label_manifest",
    }:
        missing.append("trusted_category_provenance")
    if not candidate.get("eval_ready"):
        missing.append("map_build_artifacts")
    return missing


def _scanner_next_action(candidate: dict[str, Any], *, missing_gates: list[str]) -> str:
    candidate_file = candidate.get("candidate_file")
    if "source_asset_available" in missing_gates:
        if (
            isinstance(candidate_file, dict)
            and candidate_file.get("status") == "missing_from_index_map"
        ):
            return "choose_valid_source_specific_candidate_index"
        return "run_manual_source_prep_before_scanner"
    if "preview_metadata" in missing_gates:
        return "render_preview_metadata_with_explicit_operator_command"
    if "map_build_artifacts" in missing_gates:
        return "run_map_build_product_smoke_before_eval_admission"
    return "run_scanner_admission_checks"


def _scanner_preview_status_passes(status: Any) -> bool:
    return str(status or "") in {"available", "reviewable"}


def _scanner_execution_candidate(
    *,
    install_candidate: dict[str, Any],
    admission: dict[str, Any],
) -> dict[str, Any]:
    world_id = str(install_candidate.get("world_id") or "")
    scene_source = str(install_candidate.get("scene_source") or "")
    scene_index = install_candidate.get("scene_index")
    missing_paths = [str(path) for path in install_candidate.get("missing_paths") or [] if path]
    candidate_file_exists = not missing_paths and bool(install_candidate.get("primary_path"))
    missing_gates = [str(gate) for gate in admission.get("missing_gates") or [] if gate]
    scanner_status = (
        "ready_for_product_smoke"
        if candidate_file_exists and "source_asset_available" not in missing_gates
        else "blocked_missing_resources"
    )
    if admission.get("next_action") == "choose_valid_source_specific_candidate_index":
        scanner_status = "blocked_invalid_candidate_index"
    return {
        "scene_family": admission.get("scene_family", ""),
        "scene_split": admission.get("scene_split", ""),
        "scene_source": scene_source,
        "scene_index": scene_index,
        "world_id": world_id,
        "scanner_status": scanner_status,
        "admission_status": admission.get("admission_status", ""),
        "readiness_status": admission.get("readiness_status", ""),
        "lanes": admission.get("lanes") or [],
        "failure_class": admission.get("failure_class", ""),
        "blocked_reason": admission.get("blocked_reason", ""),
        "selected_reason": admission.get("selected_reason", ""),
        "room_count": admission.get("room_count", 0),
        "waypoint_count": admission.get("waypoint_count", 0),
        "category_provenance": admission.get("category_provenance", ""),
        "preview_statuses": admission.get("preview_statuses", {}),
        "passed_gates": admission.get("passed_gates") or [],
        "required_gates": admission.get("required_gates") or list(_scanner_required_gates()),
        "missing_gates": missing_gates,
        "missing_paths": missing_paths,
        "candidate_file": admission.get("candidate_file", {}),
        "primary_path": install_candidate.get("primary_path", ""),
        "path_status": install_candidate.get("path_status", ""),
        "install_command": install_candidate.get("install_command", ""),
        "preview_command": _preview_scanner_command(world_id),
        "map_build_product_smoke_command": _map_build_product_smoke_command(world_id),
        "next_action": (
            "run_preview_then_map_build_product_smoke"
            if scanner_status == "ready_for_product_smoke"
            else admission.get("next_action", "run_manual_source_prep_before_scanner")
        ),
    }


def _scanner_execution_summary(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "source_count": len(sources),
        "candidate_count": sum(
            int(source.get("candidate_count") or 0) for source in sources.values()
        ),
        "ready_for_product_smoke_count": sum(
            int(source.get("ready_for_product_smoke_count") or 0) for source in sources.values()
        ),
        "blocked_count": sum(int(source.get("blocked_count") or 0) for source in sources.values()),
        "blocked_source_count": sum(
            1
            for source in sources.values()
            if int(source.get("ready_for_product_smoke_count") or 0) == 0
            and int(source.get("candidate_count") or 0) > 0
        ),
        "ready_source_count": sum(
            1
            for source in sources.values()
            if int(source.get("ready_for_product_smoke_count") or 0) > 0
        ),
    }


def _next_flow_status(
    *,
    readiness_source: dict[str, Any],
    prep_source: dict[str, Any],
    scanner_source: dict[str, Any],
) -> str:
    if (
        readiness_source.get("ui_status") == "ready"
        and readiness_source.get("eval_status") == "complete"
    ):
        return "complete"
    if int(scanner_source.get("ready_for_product_smoke_count") or 0) > 0:
        return "scanner_ready"
    prep_status = str(prep_source.get("prep_status") or "")
    if prep_status.startswith("blocked_"):
        return prep_status
    return "needs_scanner_or_selection"


def _next_flow_next_action(
    *,
    readiness_source: dict[str, Any],
    selection_source: dict[str, Any],
    prep_source: dict[str, Any],
    scanner_source: dict[str, Any],
) -> str:
    if (
        readiness_source.get("ui_status") == "ready"
        and readiness_source.get("eval_status") == "complete"
    ):
        return "none"
    if int(scanner_source.get("ready_for_product_smoke_count") or 0) > 0:
        return "run_scanner_plan_for_ready_candidates"
    selection_action = str(selection_source.get("next_action") or "")
    if selection_action == "expand_candidate_range":
        return "expand_candidate_range"
    prep_action = _source_prep_next_action(str(prep_source.get("prep_status") or ""))
    if prep_action != "inspect_source_prep":
        return prep_action
    if selection_action:
        return selection_action
    return "inspect_next_flow_worklist"


def _next_flow_missing_gate_counts(source_admission: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in source_admission.get("admission_rows") or []:
        if not isinstance(row, dict):
            continue
        for gate in row.get("missing_gates") or []:
            key = str(gate)
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def _next_flow_blocked_reason_samples(
    *,
    projection_source: dict[str, Any],
    prep_source: dict[str, Any],
    scanner_source: dict[str, Any],
) -> list[str]:
    reasons: list[str] = []
    for row in projection_source.get("blocked_rows") or []:
        if isinstance(row, dict) and row.get("blocked_reason"):
            reasons.append(str(row["blocked_reason"]))
    for resource in prep_source.get("missing_resources") or []:
        if not isinstance(resource, dict):
            continue
        reason = str(resource.get("reason") or "")
        path = str(resource.get("path") or "")
        if reason and path:
            reasons.append(f"{reason}: {path}")
        elif reason:
            reasons.append(reason)
    for candidate in scanner_source.get("candidates") or []:
        if isinstance(candidate, dict) and candidate.get("blocked_reason"):
            reasons.append(str(candidate["blocked_reason"]))
    deduped: list[str] = []
    for reason in reasons:
        if reason and reason not in deduped:
            deduped.append(reason)
        if len(deduped) == 3:
            break
    return deduped


def _next_flow_artifact_paths(*, output_dir: Path | None) -> dict[str, str]:
    base = output_dir or Path("output/scene-sampler-readiness")
    scanner_dir = Path("output/scene-sampler-scanner")
    return {
        "readiness_output_dir": str(base),
        "source_prep": str(base / "scene_sampler_source_prep.json"),
        "scanner_execution_plan": str(base / "scene_sampler_scanner_execution_plan.json"),
        "next_flow_worklist": str(base / "scene_sampler_next_flow_worklist.json"),
        "source_prep_run": str(scanner_dir / "source_prep_run.json"),
        "scanner_run": str(scanner_dir / "scanner_run.json"),
    }


def _next_flow_recommended_commands(
    *,
    source: str,
    next_action: str,
    recommended_candidate_range: str,
    artifact_paths: dict[str, str],
) -> list[dict[str, str]]:
    source_arg = shlex.quote(source)
    candidate_range = recommended_candidate_range or "0:19"
    commands = [
        {
            "name": "source_prep_dry_run",
            "command": (
                ".venv/bin/python scripts/operator_console/run_scene_sampler_source_prep.py "
                f"--prep {_quote_artifact_path(artifact_paths, 'source_prep')} "
                f"--worklist {_quote_artifact_path(artifact_paths, 'next_flow_worklist')} "
                f"--output {_quote_artifact_path(artifact_paths, 'source_prep_run')} "
                f"--source {source_arg}"
            ),
            "execution_policy": "dry_run_default",
        },
        {
            "name": "source_prep_execute",
            "command": (
                ".venv/bin/python scripts/operator_console/run_scene_sampler_source_prep.py "
                f"--prep {_quote_artifact_path(artifact_paths, 'source_prep')} "
                f"--worklist {_quote_artifact_path(artifact_paths, 'next_flow_worklist')} "
                f"--output {_quote_artifact_path(artifact_paths, 'source_prep_run')} "
                f"--source {source_arg} --execute"
            ),
            "execution_policy": "manual_operator_only",
        },
        {
            "name": "refresh_readiness_after_prep",
            "command": (
                ".venv/bin/python scripts/operator_console/export_scene_sampler_readiness.py "
                f"--output-dir {_quote_artifact_path(artifact_paths, 'readiness_output_dir')} "
                f"--candidate-range {shlex.quote(candidate_range)} "
                f"--require-selection-capacity-source {source_arg} "
                f"--require-scanner-ready-source {source_arg} "
                "--no-generated-eval"
            ),
            "execution_policy": "no_download_no_vlm_gate",
        },
        {
            "name": "scanner_dry_run",
            "command": (
                ".venv/bin/python scripts/operator_console/run_scene_sampler_scanner_plan.py "
                f"--plan {_quote_artifact_path(artifact_paths, 'scanner_execution_plan')} "
                f"--worklist {_quote_artifact_path(artifact_paths, 'next_flow_worklist')} "
                f"--output {_quote_artifact_path(artifact_paths, 'scanner_run')} "
                f"--source {source_arg} --dry-run"
            ),
            "execution_policy": "dry_run_default",
        },
        {
            "name": "scanner_execute_ready_candidates",
            "command": (
                ".venv/bin/python scripts/operator_console/run_scene_sampler_scanner_plan.py "
                f"--plan {_quote_artifact_path(artifact_paths, 'scanner_execution_plan')} "
                f"--worklist {_quote_artifact_path(artifact_paths, 'next_flow_worklist')} "
                f"--output {_quote_artifact_path(artifact_paths, 'scanner_run')} "
                f"--source {source_arg}"
            ),
            "execution_policy": "ready_candidates_only",
        },
    ]
    if next_action == "expand_candidate_range":
        commands.insert(
            0,
            {
                "name": "expand_candidate_range",
                "command": (
                    ".venv/bin/python scripts/operator_console/"
                    "export_scene_sampler_readiness.py "
                    f"--output-dir {_quote_artifact_path(artifact_paths, 'readiness_output_dir')} "
                    f"--candidate-range {shlex.quote(candidate_range)} "
                    f"--require-selection-capacity-source {source_arg} --no-generated-eval"
                ),
                "execution_policy": "no_download_no_vlm_gate",
            },
        )
    return commands


def _quote_artifact_path(artifact_paths: dict[str, str], key: str) -> str:
    return shlex.quote(str(artifact_paths[key]))


def _next_flow_scan_world_ids(selection_source: dict[str, Any]) -> list[str]:
    world_ids: list[str] = []
    for key in ("next_ui_scan_world_ids", "next_eval_scan_world_ids"):
        for world_id in selection_source.get(key) or []:
            raw_world_id = str(world_id or "")
            if raw_world_id and raw_world_id not in world_ids:
                world_ids.append(raw_world_id)
    for candidate in selection_source.get("next_scan_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        raw_world_id = str(candidate.get("world_id") or "")
        if raw_world_id and raw_world_id not in world_ids:
            world_ids.append(raw_world_id)
    return world_ids


def _next_flow_summary(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    actionable_sources = [
        source for source in sources.values() if source.get("next_action") != "none"
    ]
    return {
        "source_count": len(sources),
        "complete_source_count": sum(
            1 for source in sources.values() if source.get("flow_status") == "complete"
        ),
        "incomplete_source_count": len(actionable_sources),
        "ui_supported_source_count": sum(
            1 for source in sources.values() if source.get("ui_status") == "ready"
        ),
        "eval_complete_source_count": sum(
            1 for source in sources.values() if source.get("eval_status") == "complete"
        ),
        "ui_needed_count": sum(
            int(source.get("ui_needed_count") or 0) for source in sources.values()
        ),
        "eval_needed_count": sum(
            int(source.get("eval_needed_count") or 0) for source in sources.values()
        ),
        "scanner_ready_source_count": sum(
            1
            for source in sources.values()
            if int(source.get("scanner_ready_candidate_count") or 0) > 0
        ),
        "source_prep_required_count": sum(
            1
            for source in sources.values()
            if str(source.get("next_action") or "")
            in {
                "run_manual_source_prep",
                "configure_or_install_molmospaces_scene_root",
                "install_repo_dev_runtime",
            }
        ),
        "next_actions": _next_flow_action_counts(actionable_sources),
        "worklist": [_next_flow_worklist_item(source) for source in actionable_sources],
    }


def _next_flow_action_counts(sources: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for source in sources:
        action = str(source.get("next_action") or "unknown")
        counts[action] = counts.get(action, 0) + 1
    return dict(sorted(counts.items()))


def _next_flow_worklist_item(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_source": source.get("scene_source", ""),
        "flow_status": source.get("flow_status", ""),
        "next_action": source.get("next_action", ""),
        "ui_needed_count": int(source.get("ui_needed_count") or 0),
        "eval_needed_count": int(source.get("eval_needed_count") or 0),
        "selection_capacity_status": source.get("selection_capacity_status", ""),
        "prep_status": source.get("prep_status", ""),
        "scanner_ready_candidate_count": int(source.get("scanner_ready_candidate_count") or 0),
        "next_scan_world_ids": source.get("next_scan_world_ids") or [],
        "recommended_candidate_range": source.get("recommended_candidate_range", ""),
    }


def _scanner_admission_summary(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    missing_gate_counts: dict[str, int] = {}
    for source in sources.values():
        for row in source.get("admission_rows") or []:
            if not isinstance(row, dict):
                continue
            for gate in row.get("missing_gates") or []:
                key = str(gate)
                missing_gate_counts[key] = missing_gate_counts.get(key, 0) + 1
    return {
        "source_count": len(sources),
        "admitted_count": sum(
            int((source.get("summary") or {}).get("admitted_count") or 0)
            for source in sources.values()
        ),
        "blocked_count": sum(
            int((source.get("summary") or {}).get("blocked_count") or 0)
            for source in sources.values()
        ),
        "rejected_count": sum(
            int((source.get("summary") or {}).get("rejected_count") or 0)
            for source in sources.values()
        ),
        "missing_gate_counts": dict(sorted(missing_gate_counts.items())),
    }


def _preview_scanner_command(world_id: str) -> str:
    return (
        ".venv/bin/python scripts/operator_console/render_scene_previews.py "
        f"--world {world_id} "
        "--output-dir output/scene-sampler-scanner/previews "
        "--work-dir output/scene-sampler-scanner/work"
    )


def _map_build_product_smoke_command(world_id: str) -> str:
    return (
        "just run::surface surface=household-world "
        f"world={world_id} "
        "backend=mujoco preset=map-build agent_engine=direct-runner "
        "evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline "
        f"output_dir=output/scene-sampler-scanner/product-smoke/{_world_id_slug(world_id)}"
    )


def _world_id_slug(world_id: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in world_id).strip("-")


def _scanner_preview_metadata(source: str, scene_index: int) -> dict[str, Any] | None:
    """Load operator-run scanner preview metadata when it exists."""

    world_id = f"molmospaces/{source}/{scene_index}"
    path = _SCANNER_PREVIEW_ROOT / f"{_world_id_slug(world_id)}-preview.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    if payload.get("scene_source") != source:
        return None
    if payload.get("scene_index") != scene_index:
        return None
    if payload.get("backend") != PRIMARY_MOLMOSPACES_BACKEND:
        return None
    return payload


def _scanner_product_smoke_artifacts(source: str, scene_index: int) -> dict[str, Any]:
    """Return the latest map-build smoke artifacts for a scanner candidate."""

    world_id = f"molmospaces/{source}/{scene_index}"
    root = _SCANNER_PRODUCT_SMOKE_ROOT / _world_id_slug(world_id)
    run_dirs = sorted(
        [path for path in root.glob("*/seed-*") if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for run_dir in run_dirs:
        runtime_map_path = run_dir / "runtime_metric_map.json"
        run_result_path = run_dir / "run_result.json"
        runtime_map = _read_json_if_exists(runtime_map_path)
        run_result = _read_json_if_exists(run_result_path)
        if (runtime_map or {}).get("schema") != "runtime_metric_map_v1":
            continue
        return {
            "status": "available",
            "run_dir": str(run_dir),
            "runtime_metric_map": str(runtime_map_path),
            "run_result": str(run_result_path) if run_result_path.exists() else "",
            "runtime_map": runtime_map,
            "run_result_payload": run_result,
        }
    return {
        "status": "missing",
        "run_dir": "",
        "runtime_metric_map": "",
        "run_result": "",
        "runtime_map": {},
        "run_result_payload": {},
    }


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def _scanner_candidate_packet(
    *,
    packet: dict[str, Any],
    preview: dict[str, Any],
    smoke: dict[str, Any],
) -> dict[str, Any]:
    room_count = max(_preview_room_count(preview), _runtime_room_count(smoke))
    waypoint_count = max(_waypoint_count(preview), _runtime_waypoint_count(smoke))
    preview_statuses = _view_statuses(preview)
    category_provenance = _scanner_category_provenance(smoke)
    map_build_ready = _scanner_map_build_ready(smoke)
    missing_gates = _scanner_missing_gates(
        {
            **packet,
            "preview_statuses": preview_statuses,
            "room_count": room_count,
            "waypoint_count": waypoint_count,
            "category_provenance": category_provenance,
            "eval_ready": map_build_ready,
        }
    )
    quality_issue = _scanner_quality_issue(missing_gates)
    readiness_status = READINESS_BLOCKED
    failure_class = "environment_blocked"
    blocked_reason = _scanner_blocked_reason(
        source=str(packet.get("scene_source") or ""),
        scene_index=packet.get("scene_index"),
        missing_gates=missing_gates,
        smoke=smoke,
    )
    if map_build_ready and not quality_issue and not missing_gates:
        readiness_status = READINESS_READY
        failure_class = ""
        blocked_reason = ""
    elif quality_issue:
        readiness_status = READINESS_REJECTED
        failure_class = "map_actionability_failure"
        blocked_reason = quality_issue
    selected_reason = (
        "scanner_evidence_admitted_for_source_sampler"
        if readiness_status == READINESS_READY
        else quality_issue or "scanner_evidence_incomplete_for_source_sampler"
    )
    return {
        **packet,
        "readiness_status": readiness_status,
        "lanes": [],
        "ui_ready": False,
        "eval_ready": readiness_status == READINESS_READY,
        "room_count": room_count,
        "waypoint_count": waypoint_count,
        "category_provenance": category_provenance,
        "category_manifest": "",
        "preview_statuses": preview_statuses,
        "preview_assets": _scanner_preview_assets(
            source=str(packet.get("scene_source") or ""),
            scene_index=int(packet.get("scene_index") or 0),
        ),
        "selected_reason": selected_reason,
        "blocked_reason": blocked_reason,
        "failure_class": failure_class,
        "quality_score": _quality_score(preview),
        "coverage_score": _coverage_score(room_count=room_count, waypoint_count=waypoint_count),
        "scanner_evidence": {
            "preview_metadata": str(
                _SCANNER_PREVIEW_ROOT
                / f"{_world_id_slug(str(packet.get('world_id') or ''))}-preview.json"
            ),
            "product_smoke_status": smoke.get("status", ""),
            "product_smoke_run_dir": smoke.get("run_dir", ""),
            "runtime_metric_map": smoke.get("runtime_metric_map", ""),
            "run_result": smoke.get("run_result", ""),
        },
    }


def _assign_dynamic_candidate_lanes(
    *,
    source: str,
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if source == "procthor-10k-val":
        return candidates
    eligible = [
        candidate
        for candidate in candidates
        if candidate.get("readiness_status") == READINESS_READY
        and candidate.get("eval_ready")
        and candidate.get("scene_index") is not None
    ]
    eligible.sort(key=lambda item: int(item.get("scene_index") or 0))
    ui_ids = {
        int(candidate.get("scene_index") or 0)
        for candidate in eligible[:UI_TARGET_PER_SCENE_SOURCE]
        if len(eligible) >= UI_TARGET_PER_SCENE_SOURCE
    }
    eval_ids = {
        int(candidate.get("scene_index") or 0)
        for candidate in eligible[:EVAL_TARGET_PER_SCENE_SOURCE]
    }
    updated: list[dict[str, Any]] = []
    for candidate in candidates:
        scene_index = candidate.get("scene_index")
        lanes: list[str] = []
        if candidate.get("readiness_status") == READINESS_READY and scene_index is not None:
            parsed_index = int(scene_index)
            if parsed_index in ui_ids:
                lanes.append(UI_LANE)
            if parsed_index in eval_ids:
                lanes.append(EVAL_STRESS_LANE)
        updated.append(
            {
                **candidate,
                "lanes": lanes,
                "ui_ready": UI_LANE in lanes,
                "eval_ready": EVAL_STRESS_LANE in lanes,
            }
        )
    return updated


def _scanner_quality_issue(missing_gates: list[str]) -> str:
    if "source_asset_available" in missing_gates or "map_build_artifacts" in missing_gates:
        return ""
    if "preview_metadata" in missing_gates:
        return "preview_not_reviewable"
    if "public_room_count" in missing_gates:
        return "fewer_than_three_public_navigation_areas"
    if "public_waypoints" in missing_gates:
        return "fewer_than_three_public_waypoints"
    if "trusted_category_provenance" in missing_gates:
        return "missing_trusted_category_provenance"
    return ""


def _scanner_blocked_reason(
    *,
    source: str,
    scene_index: Any,
    missing_gates: list[str],
    smoke: dict[str, Any],
) -> str:
    if "source_asset_available" in missing_gates:
        return (
            f"{source}/{scene_index} source asset is unavailable; run manual source prep "
            "before scanner admission."
        )
    if "map_build_artifacts" in missing_gates:
        if smoke.get("status") == "available":
            return (
                f"{source}/{scene_index} map-build smoke artifact did not satisfy scanner "
                "admission."
            )
        return (
            f"{source}/{scene_index} is missing map-build product-smoke runtime_metric_map.json; "
            "run scanner product smoke before eval admission."
        )
    if missing_gates:
        return f"{source}/{scene_index} is missing scanner gates: {', '.join(missing_gates)}"
    return ""


def _preview_room_count(preview: dict[str, Any]) -> int:
    return len(_room_ids(preview))


def _runtime_room_count(smoke: dict[str, Any]) -> int:
    runtime_map = smoke.get("runtime_map")
    if not isinstance(runtime_map, dict):
        return 0
    return len(
        {
            str(room.get("room_id") or "")
            for room in runtime_map.get("rooms") or []
            if isinstance(room, dict) and room.get("room_id")
        }
    )


def _runtime_waypoint_count(smoke: dict[str, Any]) -> int:
    runtime_map = smoke.get("runtime_map")
    if not isinstance(runtime_map, dict):
        return 0
    waypoint_ids = {
        str(candidate.get("waypoint_id") or "")
        for candidate in runtime_map.get("generated_exploration_candidates") or []
        if isinstance(candidate, dict) and candidate.get("waypoint_id")
    }
    if waypoint_ids:
        return len(waypoint_ids)
    return len(
        [
            candidate
            for candidate in runtime_map.get("target_candidates") or []
            if isinstance(candidate, dict)
            and candidate.get("candidate_type") == "generated_exploration_candidate"
        ]
    )


def _scanner_category_provenance(smoke: dict[str, Any]) -> str:
    runtime_map = smoke.get("runtime_map")
    if not isinstance(runtime_map, dict):
        return "unavailable"
    rooms = [room for room in runtime_map.get("rooms") or [] if isinstance(room, dict)]
    if any(room.get("public_room_source") == "base_navigation_map" for room in rooms):
        return "source_metadata"
    hints = [
        hint for hint in runtime_map.get("room_category_hints") or [] if isinstance(hint, dict)
    ]
    if any(hint.get("classification_status") == "map_prior" for hint in hints):
        return "source_metadata"
    return "unavailable"


def _scanner_map_build_ready(smoke: dict[str, Any]) -> bool:
    runtime_map = smoke.get("runtime_map")
    if not isinstance(runtime_map, dict) or runtime_map.get("schema") != "runtime_metric_map_v1":
        return False
    run_result = smoke.get("run_result_payload")
    if isinstance(run_result, dict) and run_result.get("terminate_reason"):
        return str(run_result.get("terminate_reason") or "").endswith("complete")
    return True


def _scanner_preview_assets(source: str, scene_index: int) -> list[dict[str, str]]:
    slug = _world_id_slug(f"molmospaces/{source}/{scene_index}")
    return [
        {"view": view, "path": str(_SCANNER_PREVIEW_ROOT / f"{slug}-{view}.png")}
        for view in _required_views()
    ]


def _candidate_packet_from_sampler_row(row: SceneSamplerRow) -> dict[str, Any]:
    preview_statuses: dict[str, str] = {}
    if row.scene_source == "procthor-10k-val" and row.scene_index is not None:
        preview_statuses = _view_statuses(_ready_row_preview_metadata(row.scene_index))
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
        "preview_assets": [{"view": view, "path": path} for view, path in row.preview_assets],
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
    packet = {
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
    if not isinstance(candidate_file, dict) or not candidate_file.get("exists"):
        return packet
    preview = _scanner_preview_metadata(source, scene_index)
    if preview is None:
        return packet
    return _scanner_candidate_packet(
        packet=packet,
        preview=preview,
        smoke=_scanner_product_smoke_artifacts(source, scene_index),
    )


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


def _candidate_readiness_summary(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "source_count": len(sources),
        "candidate_count": sum(
            int(source.get("candidate_count") or 0) for source in sources.values()
        ),
        "ready_candidate_count": sum(
            int(source.get("ready_candidate_count") or 0) for source in sources.values()
        ),
        "blocked_candidate_count": sum(
            int(source.get("blocked_candidate_count") or 0) for source in sources.values()
        ),
        "rejected_candidate_count": sum(
            int(source.get("rejected_candidate_count") or 0) for source in sources.values()
        ),
        "ui_ready_count": sum(
            int(source.get("ui_ready_count") or 0) for source in sources.values()
        ),
        "ui_needed_count": sum(
            max(
                0,
                UI_TARGET_PER_SCENE_SOURCE - int(source.get("ui_ready_count") or 0),
            )
            for source in sources.values()
        ),
        "eval_ready_count": sum(
            int(source.get("eval_ready_count") or 0) for source in sources.values()
        ),
        "eval_needed_count": sum(
            max(
                0,
                EVAL_TARGET_PER_SCENE_SOURCE - int(source.get("eval_ready_count") or 0),
            )
            for source in sources.values()
        ),
        "ui_supported_source_count": sum(
            1 for source in sources.values() if source.get("ui_status") == "ready"
        ),
        "eval_complete_source_count": sum(
            1 for source in sources.values() if source.get("eval_status") == "complete"
        ),
        "blocked_source_count": sum(
            1 for source in sources.values() if int(source.get("blocked_candidate_count") or 0) > 0
        ),
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


def _selection_capacity_status(
    *,
    ui_needed: int,
    ui_available: int,
    eval_needed: int,
    eval_available: int,
) -> str:
    if ui_needed == 0 and eval_needed == 0:
        return "complete"
    if ui_available < ui_needed or eval_available < eval_needed:
        return "candidate_range_insufficient"
    return "candidate_range_sufficient"


def _selection_next_action(
    *,
    capacity_status: str,
    source_availability_status: Any,
) -> str:
    if capacity_status == "complete":
        return "none"
    if capacity_status == "candidate_range_insufficient":
        return "expand_candidate_range"
    if source_availability_status != "available":
        return "run_source_prep_before_scanner"
    return "run_scanner_admission"


def _selection_gap_summary(sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    worklist = [
        _selection_source_worklist_item(source)
        for source in sources.values()
        if source.get("status") != "complete"
    ]
    return {
        "source_count": len(sources),
        "complete_source_count": sum(
            1 for source in sources.values() if source.get("status") == "complete"
        ),
        "incomplete_source_count": sum(
            1 for source in sources.values() if source.get("status") != "complete"
        ),
        "ui_needed_count": sum(
            int(source.get("ui_needed_count") or 0) for source in sources.values()
        ),
        "eval_needed_count": sum(
            int(source.get("eval_needed_count") or 0) for source in sources.values()
        ),
        "ui_scan_candidate_count": sum(
            int(source.get("ui_scan_candidate_count") or 0) for source in sources.values()
        ),
        "eval_scan_candidate_count": sum(
            int(source.get("eval_scan_candidate_count") or 0) for source in sources.values()
        ),
        "candidate_range_sufficient_source_count": sum(
            1
            for source in sources.values()
            if source.get("selection_capacity_status") == "candidate_range_sufficient"
        ),
        "candidate_range_insufficient_source_count": sum(
            1
            for source in sources.values()
            if source.get("selection_capacity_status") == "candidate_range_insufficient"
        ),
        "source_prep_required_count": sum(
            1
            for source in sources.values()
            if source.get("next_action") == "run_source_prep_before_scanner"
        ),
        "next_actions": _selection_action_counts(worklist),
        "worklist": worklist,
    }


def _selection_source_worklist_item(source: dict[str, Any]) -> dict[str, Any]:
    return {
        "scene_source": source.get("scene_source", ""),
        "next_action": source.get("next_action", ""),
        "selection_capacity_status": source.get("selection_capacity_status", ""),
        "source_availability_status": source.get("source_availability_status", ""),
        "ui_needed_count": int(source.get("ui_needed_count") or 0),
        "ui_scan_candidate_count": int(source.get("ui_scan_candidate_count") or 0),
        "eval_needed_count": int(source.get("eval_needed_count") or 0),
        "eval_scan_candidate_count": int(source.get("eval_scan_candidate_count") or 0),
        "next_scan_world_ids": [
            item.get("world_id")
            for item in source.get("next_scan_candidates") or []
            if isinstance(item, dict) and item.get("world_id")
        ],
    }


def _selection_action_counts(worklist: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in worklist:
        action = str(item.get("next_action") or "unknown")
        counts[action] = counts.get(action, 0) + 1
    return dict(sorted(counts.items()))


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
