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
            r"cleanup run result source must contain valid JSON object: .*run_result\.json",
        ),
        (
            "[]\n",
            r"cleanup run result source must contain a JSON object: .*run_result\.json",
        ),
    ],
)
def test_checker_rejects_malformed_top_level_run_result_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    checker = _load_checker()
    run_result_path = tmp_path / "run_result.json"
    run_result_path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        checker._load_run_results(run_result_path)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "{not-json\n",
            r"cleanup run result source must contain valid JSON object: .*seed-7/run_result\.json",
        ),
        (
            "[]\n",
            r"cleanup run result source must contain a JSON object: .*seed-7/run_result\.json",
        ),
    ],
)
def test_checker_rejects_malformed_seed_run_result_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    checker = _load_checker()
    run_result_path = tmp_path / "seed-7" / "run_result.json"
    run_result_path.parent.mkdir()
    run_result_path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        checker._load_run_results(tmp_path)


def test_checker_accepts_json_object_run_result_source(tmp_path: Path) -> None:
    checker = _load_checker()
    run_result_path = tmp_path / "run_result.json"
    run_result_path.write_text('{"seed": 7}\n', encoding="utf-8")

    assert checker._load_run_results(run_result_path) == [({"seed": 7}, run_result_path)]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "{not-json\n",
            r"goal contract source must contain valid JSON object: .*goal_contract\.json",
        ),
        (
            "[]\n",
            r"goal contract source must contain a JSON object: .*goal_contract\.json",
        ),
    ],
)
def test_checker_rejects_malformed_goal_contract_artifact_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    checker = _load_checker()
    contract = _goal_contract()
    contract_path = tmp_path / "goal_contract.json"
    contract_path.write_text(source, encoding="utf-8")
    run_result = {
        "goal_contract": contract,
        "artifacts": {"goal_contract": "goal_contract.json"},
    }

    with pytest.raises(ValueError, match=message):
        checker._assert_goal_contract(run_result, tmp_path)


def test_checker_rejects_missing_goal_contract_artifact_source(tmp_path: Path) -> None:
    checker = _load_checker()
    run_result = {
        "goal_contract": _goal_contract(),
        "artifacts": {"goal_contract": "missing_goal_contract.json"},
    }

    with pytest.raises(
        FileNotFoundError,
        match=r"goal contract source is missing: .*missing_goal_contract\.json",
    ):
        checker._assert_goal_contract(run_result, tmp_path)


def test_checker_accepts_matching_goal_contract_artifact_source(tmp_path: Path) -> None:
    checker = _load_checker()
    contract = _goal_contract()
    contract_path = tmp_path / "goal_contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")

    checker._assert_goal_contract(
        {
            "goal_contract": contract,
            "artifacts": {"goal_contract": "goal_contract.json"},
        },
        tmp_path,
    )


def _goal_contract() -> dict[str, object]:
    return {
        "schema": "roboclaws_goal_contract_v1",
        "surface": "household-world",
        "intent": "open-ended",
        "normalized_goal": "find something useful to drink",
        "goal_scope": "agent-declared",
    }
