"""Artifact dependency resolution for eval samples."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from roboclaws.evals.models import EvalSample


def resolve_artifact_dependencies(
    sample: EvalSample,
    *,
    repetition_index: int,
    sample_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    dependencies = sample.artifact_dependencies or {}
    launch_overrides = sample.launch_overrides or {}
    explicit_source = None
    if "runtime_map_prior" in dependencies:
        explicit_source = dependencies.get("runtime_map_prior")
    elif "runtime_map_prior" in launch_overrides:
        explicit_source = launch_overrides.get("runtime_map_prior")
    if explicit_source is not None:
        return {
            "runtime_map_prior_path": str(explicit_source or "").strip(),
            "runtime_map_prior_source": "explicit_path",
        }
    source_sample_id = str(
        dependencies.get("runtime_map_prior_from_sample")
        or launch_overrides.get("runtime_map_prior_from_sample")
        or ""
    ).strip()
    if not source_sample_id:
        return {}
    source_artifacts = (
        sample_artifacts.get(sample_artifact_key(source_sample_id, repetition_index))
        or sample_artifacts.get(source_sample_id)
        or {}
    )
    runtime_map_prior_path = str(source_artifacts.get("runtime_metric_map") or "").strip()
    return {
        "runtime_map_prior_path": runtime_map_prior_path,
        "runtime_map_prior_source_sample_id": source_sample_id,
    }


def dependency_failure(dependency_artifacts: dict[str, Any]) -> dict[str, Any] | None:
    prior_path = str(dependency_artifacts.get("runtime_map_prior_path") or "").strip()
    source_sample_id = str(dependency_artifacts.get("runtime_map_prior_source_sample_id") or "")
    explicit_source = dependency_artifacts.get("runtime_map_prior_source") == "explicit_path"
    if not source_sample_id and not explicit_source:
        return None
    if not prior_path:
        message = (
            "explicit runtime_map_prior path was empty"
            if explicit_source
            else "runtime_map_prior source sample did not produce runtime_metric_map"
        )
        return {
            "failure_class": "artifact_missing",
            "missing_dependencies": ["runtime_map_prior_path"],
            "resolved_dependencies": dict(dependency_artifacts),
            "message": message,
        }
    if not Path(prior_path).exists():
        return {
            "failure_class": "artifact_missing",
            "missing_dependencies": ["runtime_map_prior_path"],
            "resolved_dependencies": dict(dependency_artifacts),
            "message": f"runtime_map_prior_path does not exist: {prior_path}",
        }
    return None


def sample_artifact_key(sample_id: str, repetition_index: int) -> str:
    return f"{sample_id}#{repetition_index}"
