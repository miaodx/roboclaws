#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.manipulation_provenance import (
    BLOCKED_CAPABILITY_PROVENANCE,
    MANIPULATION_PROBE_CONTRACT,
    PLANNER_BACKED_PROVENANCE,
)
from roboclaws.molmo_cleanup.rby1m_curobo_gate import (
    rby1m_curobo_gate_from_planner_probe,
    validate_rby1m_curobo_gate,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate MolmoSpaces planner-backed manipulation probe artifacts."
    )
    parser.add_argument("path", type=Path, help="run_result.json or probe output directory")
    parser.add_argument("--accept-blocked-capability", action="store_true")
    parser.add_argument("--require-planner-backed", action="store_true")
    parser.add_argument("--accept-rby1m-curobo-blocked", action="store_true")
    parser.add_argument("--require-rby1m-curobo-ready", action="store_true")
    parser.add_argument("--require-curobo-extension-cache", action="store_true")
    parser.add_argument("--require-warp-compatibility", action="store_true")
    parser.add_argument("--require-cuda-memory", action="store_true")
    parser.add_argument("--require-curobo-memory-profile", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = args.path / "run_result.json" if args.path.is_dir() else args.path
    data = json.loads(path.read_text(encoding="utf-8"))
    _assert_probe_result(
        data,
        path.parent,
        accept_blocked_capability=args.accept_blocked_capability,
        require_planner_backed=args.require_planner_backed,
        accept_rby1m_curobo_blocked=args.accept_rby1m_curobo_blocked,
        require_rby1m_curobo_ready=args.require_rby1m_curobo_ready,
        require_curobo_extension_cache=args.require_curobo_extension_cache,
        require_warp_compatibility=args.require_warp_compatibility,
        require_cuda_memory=args.require_cuda_memory,
        require_curobo_memory_profile=args.require_curobo_memory_profile,
    )
    print(f"molmo-planner-manipulation-probe ok: {path}")


def _assert_probe_result(
    data: dict[str, Any],
    base: Path,
    *,
    accept_blocked_capability: bool = False,
    require_planner_backed: bool = False,
    accept_rby1m_curobo_blocked: bool = False,
    require_rby1m_curobo_ready: bool = False,
    require_curobo_extension_cache: bool = False,
    require_warp_compatibility: bool = False,
    require_cuda_memory: bool = False,
    require_curobo_memory_profile: bool = False,
) -> None:
    assert data.get("contract") == MANIPULATION_PROBE_CONTRACT, data
    evidence = data.get("manipulation_evidence") or {}
    assert evidence, data
    assert evidence.get("api_semantic_state_edits") is False, evidence
    assert evidence.get("primitive_provenance") != API_SEMANTIC_PROVENANCE, evidence
    assert data.get("primitive_provenance") != API_SEMANTIC_PROVENANCE, data
    artifacts = data.get("artifacts") or {}
    for key in ("stdout", "stderr", "report"):
        path = _resolve_path(base, artifacts.get(key, ""))
        assert path.is_file(), path
    report_text = _resolve_path(base, artifacts["report"]).read_text(encoding="utf-8")
    assert "Planner-Backed Manipulation Probe" in report_text, report_text[:500]
    assert "Manipulation Provenance" in report_text, report_text[:500]
    if evidence.get("runtime_diagnostics"):
        assert "Runtime Diagnostics" in report_text, report_text[:500]
        cache = (evidence.get("runtime_diagnostics") or {}).get("curobo_extension_cache") or {}
        if cache.get("extensions"):
            assert "CuRobo Extension Cache" in report_text, report_text[:500]
        warp = (evidence.get("runtime_diagnostics") or {}).get("warp_compatibility") or {}
        if warp:
            assert "Warp Compatibility" in report_text, report_text[:500]
        cuda_memory = (evidence.get("runtime_diagnostics") or {}).get("cuda_memory") or {}
        if cuda_memory:
            assert "CUDA Memory Headroom" in report_text, report_text[:500]
    if evidence.get("curobo_memory_profile"):
        assert "CuRobo Memory Profile" in report_text, report_text[:500]
    robot_placement_profile = evidence.get("task_sampler_robot_placement_profile") or {}
    if robot_placement_profile:
        assert "Task Sampler Robot Placement Profile" in report_text, report_text[:500]
        profile = str(robot_placement_profile.get("profile") or "")
        if profile:
            assert profile in report_text, (
                "task_sampler_robot_placement_profile",
                report_text[:500],
            )
        overrides = robot_placement_profile.get("place_robot_near_overrides") or {}
        max_tries = str(overrides.get("max_tries") or "")
        if max_tries:
            assert max_tries in report_text, ("place_robot_near_overrides", report_text[:500])
    task_sampler_failure = evidence.get("task_sampler_failure_diagnostics") or {}
    if task_sampler_failure:
        assert "Task Sampler Failure Diagnostics" in report_text, report_text[:500]
        for key in ("task_sampler_class",):
            value = str(task_sampler_failure.get(key) or "")
            if value:
                assert value in report_text, (key, report_text[:500])
        for item in task_sampler_failure.get("robot_placement_attempts") or []:
            for key in ("pickup_obj_name", "message"):
                value = str(item.get(key) or "")
                if value:
                    assert value in report_text, (key, report_text[:500])
    if (
        evidence.get("sampled_task_binding")
        or evidence.get("requested_cleanup_primitive_binding")
        or evidence.get("cleanup_primitive_binding")
        or evidence.get("cleanup_primitive_binding_blockers")
        or evidence.get("cleanup_task_config")
        or evidence.get("cleanup_task_sampler_adapter")
    ):
        assert "Planner Probe Cleanup Binding" in report_text, report_text[:500]
    if require_curobo_extension_cache:
        diagnostics = evidence.get("runtime_diagnostics") or {}
        cache = diagnostics.get("curobo_extension_cache") or {}
        assert cache.get("extensions"), diagnostics
        assert "CuRobo Extension Cache" in report_text, report_text[:500]
    if require_warp_compatibility:
        diagnostics = evidence.get("runtime_diagnostics") or {}
        warp = diagnostics.get("warp_compatibility") or {}
        assert warp, diagnostics
        assert "Warp Compatibility" in report_text, report_text[:500]
    if require_cuda_memory:
        diagnostics = evidence.get("runtime_diagnostics") or {}
        cuda_memory = diagnostics.get("cuda_memory") or {}
        snapshots = evidence.get("cuda_memory_snapshots") or []
        assert cuda_memory or snapshots, diagnostics
        assert "CUDA Memory Headroom" in report_text, report_text[:500]
    if require_curobo_memory_profile:
        profile = evidence.get("curobo_memory_profile") or {}
        assert profile, evidence
        assert profile.get("applied") is True, profile
        assert "CuRobo Memory Profile" in report_text, report_text[:500]
    if evidence.get("worker_stage_events"):
        assert evidence.get("last_worker_stage"), evidence
        assert "Worker Stage Timeline" in report_text, report_text[:500]
    if accept_rby1m_curobo_blocked or require_rby1m_curobo_ready:
        _assert_rby1m_curobo_gate(
            data,
            report_text,
            accept_blocked=accept_rby1m_curobo_blocked,
            require_ready=require_rby1m_curobo_ready,
        )

    if require_planner_backed:
        _assert_planner_backed(data, evidence)
        return

    if data.get("status") == BLOCKED_CAPABILITY_PROVENANCE:
        assert accept_blocked_capability, data
        assert evidence.get("planner_backed") is False, evidence
        assert evidence.get("strict_proof_eligible") is False, evidence
        assert evidence.get("blockers"), evidence
        assert "Capability Blockers" in report_text, report_text[:500]
        return

    if data.get("status") == PLANNER_BACKED_PROVENANCE:
        _assert_planner_backed(data, evidence)
        return

    raise AssertionError(data)


def _assert_planner_backed(data: dict[str, Any], evidence: dict[str, Any]) -> None:
    assert data.get("status") == PLANNER_BACKED_PROVENANCE, data
    assert data.get("primitive_provenance") == PLANNER_BACKED_PROVENANCE, data
    assert evidence.get("primitive_provenance") == PLANNER_BACKED_PROVENANCE, evidence
    assert evidence.get("planner_backed") is True, evidence
    assert evidence.get("strict_proof_eligible") is True, evidence
    assert evidence.get("execution_attempted") is True, evidence
    assert int(evidence.get("steps_executed") or 0) >= 1, evidence
    assert float(evidence.get("max_abs_qpos_delta") or 0.0) > 0.0, evidence
    assert not evidence.get("blockers"), evidence
    assert evidence.get("upstream_policy_class"), evidence


def _assert_rby1m_curobo_gate(
    data: dict[str, Any],
    report_text: str,
    *,
    accept_blocked: bool = False,
    require_ready: bool = False,
) -> None:
    gate = data.get("rby1m_curobo_gate") or rby1m_curobo_gate_from_planner_probe(data)
    validate_rby1m_curobo_gate(
        gate,
        accept_blocked=accept_blocked,
        require_ready=require_ready,
    )
    assert "RBY1M CuRobo Gate" in report_text, report_text[:500]


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base / path


if __name__ == "__main__":
    main()
