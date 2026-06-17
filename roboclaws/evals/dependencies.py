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
    explicit = str(
        dependencies.get("runtime_map_prior") or launch_overrides.get("runtime_map_prior") or ""
    ).strip()
    if explicit:
        return {
            "runtime_map_prior_path": explicit,
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
    if "runtime_map_prior_source_sample_id" not in dependency_artifacts:
        return None
    if not prior_path:
        return {
            "failure_class": "artifact_missing",
            "missing_dependencies": ["runtime_map_prior_path"],
            "resolved_dependencies": dict(dependency_artifacts),
            "message": "runtime_map_prior source sample did not produce runtime_metric_map",
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
