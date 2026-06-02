from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from roboclaws.household.grasp_cache_generation import (
    ensure_molmospaces_assets_symlink,
    generation_xml_path,
    objects_list_from_generation_preflight,
)
from roboclaws.household.planner_task_feasibility import validate_grasp_cache_file

GRASP_FILTER_DIAGNOSTICS_SCHEMA = "molmospaces_grasp_filter_diagnostics_v1"

DEFAULT_FILTER_VARIANTS = (
    {"name": "initial_contact", "num_shakes": 0, "rotate": False},
    {"name": "translation_shake", "num_shakes": 1, "rotate": False},
    {"name": "upstream_like", "num_shakes": 2, "rotate": True},
)


def run_grasp_filter_diagnostics(
    *,
    generation_preflight: dict[str, Any],
    output_dir: Path,
    molmospaces_python: Path | None = None,
    candidate_grasps_path: Path | None = None,
    sample_size: int = 64,
    num_samples: int = 512,
    num_workers: int = 1,
    approach_steps: int = 30,
    shake_steps: int = 10,
    timeout_s: float = 900.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    if generation_preflight.get("status") != "ready":
        return _blocked_result(
            output_dir=output_dir,
            blockers=[
                {
                    "code": "generation_preflight_not_ready",
                    "message": "Grasp filter diagnostics require a ready generation preflight.",
                }
            ],
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    objects = objects_list_from_generation_preflight(generation_preflight)
    if not objects:
        return _blocked_result(
            output_dir=output_dir,
            blockers=[
                {
                    "code": "no_generation_objects",
                    "message": "Generation preflight did not expose any rigid objects.",
                }
            ],
        )

    target_object = objects[0]
    object_name = target_object["name"]
    xml_path = generation_xml_path(target_object["xml"])
    python = Path(molmospaces_python or generation_preflight.get("molmospaces_python") or "python")
    working_dir = Path(str(generation_preflight.get("working_dir") or ""))
    artifact_dir = (output_dir / "grasp_filter_diagnostics" / object_name).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)

    assets_symlink = ensure_molmospaces_assets_symlink(
        generation_preflight,
        working_dir=working_dir,
        dry_run=dry_run,
    )
    pipeline = _prepare_candidate_artifacts(
        artifact_dir=artifact_dir,
        object_name=object_name,
        xml_path=xml_path,
        candidate_grasps_path=candidate_grasps_path,
        working_dir=working_dir,
        molmospaces_python=python,
        num_samples=num_samples,
        num_workers=num_workers,
        timeout_s=timeout_s,
        dry_run=dry_run,
    )

    subset_path = artifact_dir / f"{object_name}_diagnostic_subset.json"
    subset = _make_candidate_subset(
        source_path=Path(pipeline["candidate_grasps_path"]),
        subset_path=subset_path,
        sample_size=sample_size,
        dry_run=dry_run,
    )

    variants = [
        _run_filter_variant(
            variant=variant,
            object_name=object_name,
            xml_path=xml_path,
            subset_path=subset_path,
            artifact_dir=artifact_dir,
            working_dir=working_dir,
            molmospaces_python=python,
            num_workers=num_workers,
            approach_steps=approach_steps,
            shake_steps=shake_steps,
            timeout_s=timeout_s,
            dry_run=dry_run,
        )
        for variant in DEFAULT_FILTER_VARIANTS
    ]

    blockers: list[dict[str, Any]] = []
    if assets_symlink.get("status") == "blocked":
        blockers.append(
            {
                "code": "molmospaces_assets_symlink_blocked",
                "message": assets_symlink.get("message") or "assets symlink setup failed",
            }
        )
    blockers.extend(pipeline.get("blockers") or [])
    blockers.extend(subset.get("blockers") or [])
    blockers.extend(_variant_blockers(variants))

    successful_variants = [
        item for item in variants if item.get("successful_transform_count", 0) > 0
    ]
    if not dry_run and not successful_variants and not any(blockers):
        blockers.append(
            {
                "code": "all_filter_variants_zero_success",
                "message": (
                    "All diagnostic filter variants completed with zero successful transforms."
                ),
            }
        )

    status = "dry_run" if dry_run else ("ready" if successful_variants else "blocked")
    return {
        "schema": GRASP_FILTER_DIAGNOSTICS_SCHEMA,
        "status": status,
        "ready": status == "ready",
        "output_dir": str(output_dir),
        "object_name": object_name,
        "object_xml": str(xml_path),
        "artifact_dir": str(artifact_dir),
        "assets_symlink": assets_symlink,
        "pipeline": pipeline,
        "candidate_subset": subset,
        "variants": variants,
        "variant_count": len(variants),
        "successful_variant_count": len(successful_variants),
        "blockers": blockers,
        "blocker_count": len(blockers),
        "evidence_note": (
            "Preserves MolmoSpaces grasp-generation intermediates and reruns "
            "bounded perturbation-filter variants so zero-success failures can "
            "be diagnosed before any loader cache is installed."
        ),
    }


def _blocked_result(*, output_dir: Path, blockers: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": GRASP_FILTER_DIAGNOSTICS_SCHEMA,
        "status": "blocked",
        "ready": False,
        "output_dir": str(output_dir),
        "object_name": "",
        "object_xml": "",
        "artifact_dir": "",
        "pipeline": {},
        "candidate_subset": {},
        "variants": [],
        "variant_count": 0,
        "successful_variant_count": 0,
        "blockers": blockers,
        "blocker_count": len(blockers),
    }


def _prepare_candidate_artifacts(
    *,
    artifact_dir: Path,
    object_name: str,
    xml_path: Path,
    candidate_grasps_path: Path | None,
    working_dir: Path,
    molmospaces_python: Path,
    num_samples: int,
    num_workers: int,
    timeout_s: float,
    dry_run: bool,
) -> dict[str, Any]:
    combined_mesh = artifact_dir / f"{object_name}_combined.obj"
    manifold_mesh = artifact_dir / f"{object_name}_manifold.obj"
    simplified_mesh = artifact_dir / f"{object_name}_simplified.obj"
    generated_grasps = artifact_dir / f"{object_name}_grasps.json"
    top_level_dir = working_dir.parents[1] if len(working_dir.parents) > 1 else working_dir
    manifold_dir = top_level_dir / "external_src" / "Manifold" / "build"
    if candidate_grasps_path is not None:
        candidate_path = Path(candidate_grasps_path)
        return {
            "source": "provided_candidate_grasps",
            "candidate_grasps_path": str(candidate_path),
            "candidate_count": _candidate_count(candidate_path, dry_run=dry_run),
            "commands": [],
            "blockers": [],
        }

    commands = [
        {
            "stage": "combine_meshes",
            "command": [
                str(molmospaces_python),
                str(working_dir / "pipeline" / "combine_meshes.py"),
                str(xml_path),
                str(combined_mesh),
                "--only_collision",
            ],
            "cwd": str(working_dir),
        },
        {
            "stage": "manifold",
            "command": [
                str(manifold_dir / "manifold"),
                str(combined_mesh),
                str(manifold_mesh),
                "-s",
            ],
            "cwd": str(manifold_dir),
        },
        {
            "stage": "simplify",
            "command": [
                str(manifold_dir / "simplify"),
                "-i",
                str(manifold_mesh),
                "-o",
                str(simplified_mesh),
                "-m",
                "-r",
                "0.5",
            ],
            "cwd": str(manifold_dir),
        },
        {
            "stage": "generate_grasps",
            "command": [
                str(molmospaces_python),
                str(working_dir / "pipeline" / "generate_grasps.py"),
                "--object_file",
                str(simplified_mesh),
                "--quality",
                "antipodal",
                "--output",
                str(generated_grasps),
                "--num_workers",
                str(num_workers),
                "--num_samples",
                str(num_samples),
            ],
            "cwd": str(working_dir),
        },
    ]
    command_results = [
        {
            **item,
            "result": _run_command(
                item["command"],
                cwd=Path(item["cwd"]),
                molmospaces_python=molmospaces_python,
                timeout_s=timeout_s,
                dry_run=dry_run,
            ),
        }
        for item in commands
    ]
    blockers = [
        {
            "code": f"{item['stage']}_failed",
            "message": (item["result"].get("stderr") or item["result"].get("stdout") or ""),
        }
        for item in command_results
        if item["result"].get("status") == "blocked"
    ]
    return {
        "source": "generated_candidate_grasps",
        "candidate_grasps_path": str(generated_grasps),
        "candidate_count": _candidate_count(generated_grasps, dry_run=dry_run),
        "commands": command_results,
        "blockers": blockers,
    }


def _make_candidate_subset(
    *,
    source_path: Path,
    subset_path: Path,
    sample_size: int,
    dry_run: bool,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "source_path": str(source_path),
        "subset_path": str(subset_path),
        "requested_sample_size": sample_size,
        "candidate_count": 0,
        "subset_count": 0,
        "blockers": [],
    }
    if dry_run:
        return {**result, "status": "not_run"}
    if not source_path.is_file():
        return {
            **result,
            "status": "blocked",
            "blockers": [
                {
                    "code": "candidate_grasps_missing",
                    "message": f"Candidate grasp JSON is missing: {source_path}",
                }
            ],
        }
    data = json.loads(source_path.read_text(encoding="utf-8"))
    transforms = data.get("transforms") or []
    candidate_count = len(transforms)
    indices = _candidate_subset_indices(data, sample_size=sample_size)
    subset = _subset_candidate_json(data, indices)
    subset_path.write_text(json.dumps(subset, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        **result,
        "status": "ready",
        "candidate_count": candidate_count,
        "subset_count": len(indices),
    }


def _candidate_subset_indices(data: dict[str, Any], *, sample_size: int) -> list[int]:
    transforms = data.get("transforms") or []
    count = len(transforms)
    if sample_size <= 0 or sample_size >= count:
        return list(range(count))
    qualities = data.get("quality_antipodal") or data.get("qualities") or []
    if isinstance(qualities, list) and len(qualities) == count:
        return sorted(range(count), key=lambda idx: qualities[idx], reverse=True)[:sample_size]
    return list(range(sample_size))


def _subset_candidate_json(data: dict[str, Any], indices: list[int]) -> dict[str, Any]:
    transforms = data.get("transforms") or []
    count = len(transforms)
    index_set = set(indices)
    subset: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, list) and len(value) == count:
            subset[key] = [item for idx, item in enumerate(value) if idx in index_set]
        else:
            subset[key] = value
    return subset


def _run_filter_variant(
    *,
    variant: dict[str, Any],
    object_name: str,
    xml_path: Path,
    subset_path: Path,
    artifact_dir: Path,
    working_dir: Path,
    molmospaces_python: Path,
    num_workers: int,
    approach_steps: int,
    shake_steps: int,
    timeout_s: float,
    dry_run: bool,
) -> dict[str, Any]:
    name = str(variant["name"])
    variant_grasps = artifact_dir / f"{object_name}_{name}_grasps.json"
    if not dry_run and subset_path.is_file():
        shutil.copy2(subset_path, variant_grasps)
    else:
        variant_grasps = subset_path
    output_npz = variant_grasps.with_name(variant_grasps.stem + "_filtered.npz")
    command = [
        str(molmospaces_python),
        str(working_dir / "pipeline" / "perturbations_test.py"),
        "--object_name",
        object_name,
        "--grasps_path",
        str(variant_grasps),
        "--xml_file",
        str(xml_path),
        "--approach_steps",
        str(approach_steps),
        "--shake_steps",
        str(shake_steps),
        "--num_workers",
        str(num_workers),
        "--max_successful",
        "1",
        "--num_shakes",
        str(variant.get("num_shakes", 0)),
    ]
    if variant.get("rotate"):
        command.append("--rotate")
    command_result = _run_command(
        command,
        cwd=working_dir,
        molmospaces_python=molmospaces_python,
        timeout_s=timeout_s,
        dry_run=dry_run,
    )
    validation = validate_grasp_cache_file(output_npz) if not dry_run else {}
    return {
        "name": name,
        "num_shakes": variant.get("num_shakes", 0),
        "rotate": bool(variant.get("rotate")),
        "candidate_subset_path": str(variant_grasps),
        "output_npz_path": str(output_npz),
        "command": command,
        "command_result": command_result,
        "validation": validation,
        "successful_transform_count": int(validation.get("transform_count", 0) or 0),
        "classification": _variant_classification(command_result, validation, dry_run=dry_run),
    }


def _variant_classification(
    command_result: dict[str, Any],
    validation: dict[str, Any],
    *,
    dry_run: bool,
) -> str:
    if dry_run:
        return "not_run"
    if command_result.get("status") == "blocked":
        return "command_failed"
    if validation.get("valid"):
        return "success"
    if validation.get("validation_status") == "empty":
        return "zero_success"
    return str(validation.get("validation_status") or "invalid")


def _variant_blockers(variants: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = []
    for variant in variants:
        if variant.get("classification") == "command_failed":
            command_result = variant.get("command_result") or {}
            blockers.append(
                {
                    "code": "filter_variant_command_failed",
                    "message": command_result.get("stderr") or command_result.get("stdout") or "",
                    "variant": variant.get("name"),
                }
            )
    return blockers


def _candidate_count(path: Path, *, dry_run: bool) -> int:
    if dry_run or not path.is_file():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    return len(data.get("transforms") or [])


def _run_command(
    command: list[str],
    *,
    cwd: Path,
    molmospaces_python: Path,
    timeout_s: float,
    dry_run: bool,
) -> dict[str, Any]:
    if dry_run:
        return {"status": "not_run", "returncode": "", "stdout": "", "stderr": ""}
    env = os.environ.copy()
    env["PATH"] = str(molmospaces_python.parent) + os.pathsep + env.get("PATH", "")
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "status": "blocked",
            "returncode": "",
            "stdout": str(exc.stdout or "").strip(),
            "stderr": str(exc.stderr or "").strip(),
            "code": "command_timeout",
            "message": f"Command exceeded {timeout_s:.1f}s.",
        }
    except OSError as exc:
        return {
            "status": "blocked",
            "returncode": "",
            "stdout": "",
            "stderr": str(exc),
            "code": "command_os_error",
            "message": str(exc),
        }
    return {
        "status": "ready" if completed.returncode == 0 else "blocked",
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
