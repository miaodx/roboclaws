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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate MolmoSpaces planner-backed manipulation probe artifacts."
    )
    parser.add_argument("path", type=Path, help="run_result.json or probe output directory")
    parser.add_argument("--accept-blocked-capability", action="store_true")
    parser.add_argument("--require-planner-backed", action="store_true")
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
    )
    print(f"molmo-planner-manipulation-probe ok: {path}")


def _assert_probe_result(
    data: dict[str, Any],
    base: Path,
    *,
    accept_blocked_capability: bool = False,
    require_planner_backed: bool = False,
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


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return base / path


if __name__ == "__main__":
    main()
