from __future__ import annotations

import json
from pathlib import Path

from roboclaws.evals.runner import _load_optional_json_mapping, _load_required_json_mapping


def test_optional_eval_runner_json_artifact_missing_is_empty(tmp_path: Path) -> None:
    payload, reason = _load_optional_json_mapping(tmp_path / "missing.json")

    assert payload == {}
    assert reason == ""


def test_optional_eval_runner_json_artifact_loads_object(tmp_path: Path) -> None:
    path = tmp_path / "live_status.json"
    path.write_text('{"status": "running"}\n', encoding="utf-8")

    payload, reason = _load_optional_json_mapping(path)

    assert payload == {"status": "running"}
    assert reason == ""


def test_optional_eval_runner_json_artifact_reports_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "live_status.json"
    path.write_text("{", encoding="utf-8")

    payload, reason = _load_optional_json_mapping(path)

    assert payload == {}
    assert reason.startswith("invalid_json:Expecting property name enclosed in double quotes")


def test_optional_eval_runner_json_artifact_reports_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "live_status.json"
    path.write_text("[]", encoding="utf-8")

    payload, reason = _load_optional_json_mapping(path)

    assert payload == {}
    assert reason == "invalid_json_object"


def test_required_eval_runner_json_artifact_missing_is_reason(tmp_path: Path) -> None:
    payload, reason = _load_required_json_mapping(tmp_path / "missing.json")

    assert payload == {}
    assert reason == "missing"


def test_required_eval_runner_json_artifact_loads_object(tmp_path: Path) -> None:
    path = tmp_path / "runtime_metric_map.json"
    expected = {"schema": "runtime_metric_map_v1"}
    path.write_text(json.dumps(expected), encoding="utf-8")

    payload, reason = _load_required_json_mapping(path)

    assert payload == expected
    assert reason == ""


def test_required_eval_runner_json_artifact_reports_malformed_json(tmp_path: Path) -> None:
    path = tmp_path / "runtime_metric_map.json"
    path.write_text("{", encoding="utf-8")

    payload, reason = _load_required_json_mapping(path)

    assert payload == {}
    assert reason.startswith("invalid_json:Expecting property name enclosed in double quotes")


def test_required_eval_runner_json_artifact_reports_non_object_json(tmp_path: Path) -> None:
    path = tmp_path / "runtime_metric_map.json"
    path.write_text("[]", encoding="utf-8")

    payload, reason = _load_required_json_mapping(path)

    assert payload == {}
    assert reason == "invalid_json_object"
