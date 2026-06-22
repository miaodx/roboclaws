from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "check_molmo_realworld_cleanup_result.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "check_molmo_realworld_cleanup_result", CHECKER_PATH
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "{not-json\n",
            r"planner proof requests source must contain valid JSON object: .*requests\.json",
        ),
        (
            "[]\n",
            r"planner proof requests source must contain a JSON object: .*requests\.json",
        ),
    ],
)
def test_checker_rejects_malformed_declared_planner_proof_request_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    checker = _load_checker()
    request_path = tmp_path / "requests.json"
    request_path.write_text(source, encoding="utf-8")
    run_result = {
        "artifacts": {"planner_proof_requests": "requests.json"},
    }

    with pytest.raises(ValueError, match=message):
        checker._assert_planner_proof_requests(
            run_result,
            tmp_path,
            report_text="Planner Proof Requests",
        )


def test_checker_rejects_missing_declared_planner_proof_request_source(
    tmp_path: Path,
) -> None:
    checker = _load_checker()
    run_result = {
        "artifacts": {"planner_proof_requests": "missing_requests.json"},
    }

    with pytest.raises(
        FileNotFoundError,
        match=r"planner proof requests source is missing: .*missing_requests\.json",
    ):
        checker._assert_planner_proof_requests(
            run_result,
            tmp_path,
            report_text="Planner Proof Requests",
        )


def test_checker_accepts_declared_planner_proof_request_source(
    tmp_path: Path,
) -> None:
    checker = _load_checker()
    request_path = tmp_path / "requests.json"
    request_path.write_text(
        json.dumps(
            {
                "schema": checker.PLANNER_PROOF_REQUESTS_SCHEMA,
                "agent_view_exposed": False,
                "request_count": 1,
                "requests": [
                    {
                        "object_id": "apple_1",
                        "ready": True,
                        "target_receptacle_id": "countertop",
                        "planner_probe_args": ["--object-id", "apple_1"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    run_result = {
        "artifacts": {"planner_proof_requests": "requests.json"},
        "agent_view": {},
    }

    checker._assert_planner_proof_requests(
        run_result,
        tmp_path,
        report_text="Planner Proof Requests",
    )
