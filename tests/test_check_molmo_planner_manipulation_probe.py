from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from roboclaws.molmo_cleanup.manipulation_provenance import (
    MANIPULATION_PROBE_CONTRACT,
    blocked_planner_probe_evidence,
    planner_backed_probe_evidence,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER_PATH = REPO_ROOT / "scripts" / "check_molmo_planner_manipulation_probe.py"


def _load_checker_module():
    spec = importlib.util.spec_from_file_location(
        "check_molmo_planner_manipulation_probe", CHECKER_PATH
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_report_files(tmp_path: Path, *, blocked: bool = False) -> dict[str, str]:
    stdout = tmp_path / "planner_probe_stdout.txt"
    stderr = tmp_path / "planner_probe_stderr.txt"
    report = tmp_path / "report.html"
    stdout.write_text("{}", encoding="utf-8")
    stderr.write_text("", encoding="utf-8")
    body = "Planner-Backed Manipulation Probe\nManipulation Provenance\n"
    if blocked:
        body += "Capability Blockers\n"
    report.write_text(body, encoding="utf-8")
    return {"stdout": str(stdout), "stderr": str(stderr), "report": str(report)}


def test_checker_accepts_blocked_capability_only_when_explicit(tmp_path: Path) -> None:
    checker = _load_checker_module()
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": blocked_planner_probe_evidence(
            backend="molmospaces_subprocess",
            embodiment="franka",
            task="pick_and_place",
            probe_mode="config_import",
            blockers=[{"code": "execution_not_attempted", "message": "not attempted"}],
        ),
        "artifacts": _write_report_files(tmp_path, blocked=True),
    }

    checker._assert_probe_result(data, tmp_path, accept_blocked_capability=True)
    with pytest.raises(AssertionError):
        checker._assert_probe_result(data, tmp_path, accept_blocked_capability=False)


def test_checker_rejects_api_semantic_as_planner_proof(tmp_path: Path) -> None:
    checker = _load_checker_module()
    evidence = planner_backed_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="franka",
        task="pick_and_place",
        probe_mode="execute",
        upstream_policy_class="PickAndPlacePlannerPolicy",
        steps_requested=2,
        steps_executed=2,
        max_abs_qpos_delta=0.01,
    )
    evidence["primitive_provenance"] = "api_semantic"
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "planner_backed",
        "primitive_provenance": "api_semantic",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(tmp_path),
    }

    with pytest.raises(AssertionError):
        checker._assert_probe_result(data, tmp_path, require_planner_backed=True)


def test_checker_accepts_strict_planner_backed_evidence(tmp_path: Path) -> None:
    checker = _load_checker_module()
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "planner_backed",
        "primitive_provenance": "planner_backed",
        "manipulation_evidence": planner_backed_probe_evidence(
            backend="molmospaces_subprocess",
            embodiment="franka",
            task="pick_and_place",
            probe_mode="execute",
            upstream_policy_class="PickAndPlacePlannerPolicy",
            steps_requested=2,
            steps_executed=2,
            max_abs_qpos_delta=0.01,
        ),
        "artifacts": _write_report_files(tmp_path),
    }

    checker._assert_probe_result(data, tmp_path, require_planner_backed=True)
