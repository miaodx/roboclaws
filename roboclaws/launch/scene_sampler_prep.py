"""Source-preparation helpers for the MolmoSpaces scene sampler."""

from __future__ import annotations

import importlib
import io
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any


def molmospaces_module_status() -> tuple[bool, str, str]:
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            importlib.import_module("molmo_spaces.molmo_spaces_constants")
    except ModuleNotFoundError as exc:
        return False, f"module_not_importable:{exc.name}", stdout.getvalue()
    except Exception as exc:  # pragma: no cover - dependency import failures vary by host.
        return False, f"module_import_failed:{type(exc).__name__}:{exc}", stdout.getvalue()
    return True, "module_importable", stdout.getvalue()


def molmospaces_scene_root_status(
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


def source_availability_blocked_reason(
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


def source_availability_summary(
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


def molmospaces_get_scenes_args(scene_source: str) -> tuple[str, str]:
    if scene_source == "ithor":
        return "ithor", "train"
    family, split = _family_split(scene_source)
    if split == "not_applicable":
        split = "train"
    return family, split


def molmospaces_scene_index_map(
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


def candidate_scene_ref_from_availability(candidate_file: dict[str, Any]) -> dict[str, Any]:
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


def missing_source_resources(
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


def source_prep_status(
    *,
    source_availability: dict[str, Any],
    source_selection: dict[str, Any],
    missing_resources: list[dict[str, Any]],
    metadata_worklist_candidate_count: int = 0,
) -> str:
    if source_selection.get("status") == "complete":
        return "complete"
    if (
        source_selection.get("selection_capacity_status") == "rejected_exhausted"
        and metadata_worklist_candidate_count <= 0
    ):
        return "rejected_exhausted"
    if source_availability.get("module_available") is False:
        return "blocked_molmospaces_module"
    if not source_availability.get("scene_root_available"):
        return "blocked_scene_root"
    if missing_resources:
        return "blocked_missing_resources"
    if source_selection.get("status") != "complete":
        return "ready_for_scanner"
    return "complete"


def resource_reason_counts(resources: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
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


def source_prep_status_counts(sources: dict[str, dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for source in sources.values():
        status = str(source.get("prep_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def source_prep_worklist(sources: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "scene_source": source.get("scene_source", ""),
            "prep_status": source.get("prep_status", ""),
            "next_action": _source_prep_worklist_next_action(source),
            "missing_resource_count": int(source.get("missing_resource_count") or 0),
            "missing_resource_summary": source.get("missing_resource_summary") or {},
            "next_scan_world_ids": source.get("next_scan_world_ids") or [],
            "metadata_worklist_candidate_count": int(
                source.get("metadata_worklist_candidate_count") or 0
            ),
            "metadata_worklist_world_ids": source.get("metadata_worklist_world_ids") or [],
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


def _source_prep_worklist_next_action(source: dict[str, Any]) -> str:
    profile_action = str(source.get("candidate_profile_next_action") or "")
    if (
        profile_action == "metadata_first_human_curation"
        and source.get("prep_status") == "rejected_exhausted"
    ):
        return profile_action
    return _source_prep_next_action(str(source.get("prep_status") or ""))


def source_prep_operator_commands(
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


def source_prep_install_candidates(
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
                "prefilter_status": candidate.get("prefilter_status", ""),
                "prefilter_reason": candidate.get("prefilter_reason", ""),
                "prefilter_score": int(candidate.get("prefilter_score") or 0),
                "cheap_room_count": int(candidate.get("cheap_room_count") or 0),
                "install_command": install_candidate_command(
                    dataset_name=dataset_name,
                    split=split,
                    scene_index=scene_index,
                ),
            }
        )
    return install_candidates


def install_candidate_command(
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


def _family_split(scene_source: str) -> tuple[str, str]:
    if scene_source == "ithor":
        return "ithor", "not_applicable"
    for split in ("-train", "-val", "-test"):
        if scene_source.endswith(split):
            return scene_source[: -len(split)], split.removeprefix("-")
    return scene_source, "not_applicable"


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


def _source_prep_next_action(prep_status: str) -> str:
    if prep_status == "complete":
        return "none"
    if prep_status == "rejected_exhausted":
        return "do_not_scan_without_new_human_curation"
    if prep_status == "gate_mismatch":
        return "do_not_scan_without_gate_change"
    if prep_status == "ready_for_scanner":
        return "run_scanner_admission"
    if prep_status == "blocked_prefilter_inconclusive":
        return "run_scene_only_prefilter_or_stop"
    if prep_status == "blocked_molmospaces_module":
        return "install_repo_dev_runtime"
    if prep_status == "blocked_scene_root":
        return "configure_or_install_molmospaces_scene_root"
    if prep_status == "blocked_missing_resources":
        return "run_manual_source_prep"
    return "inspect_source_prep"


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
