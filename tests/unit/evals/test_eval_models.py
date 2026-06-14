from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.evals.models import (
    EVAL_RESULT_SCHEMA,
    EVAL_SAMPLE_SCHEMA,
    EVAL_SUITE_SCHEMA,
    EVAL_TRIAL_SCHEMA,
    FAILURE_CLASSES,
    MISSING_NOT_APPLICABLE,
    MISSING_UNAVAILABLE,
    EvalResult,
    EvalSample,
    EvalSuite,
    EvalTrial,
    load_eval_sample,
    load_eval_suite,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SMOKE_SUITE = REPO_ROOT / "evals" / "household_world" / "suites" / "smoke_regression.json"


def test_direct_runner_eval_sample_and_result_round_trip(tmp_path: Path) -> None:
    suite = EvalSuite.from_mapping(
        {
            "schema": EVAL_SUITE_SCHEMA,
            "suite_id": "household_world.smoke_regression",
            "version": "2026-06-15",
            "capability": "household_world",
            "sample_ids": ["cleanup.smoke_seed7"],
            "required_graders": ["artifacts", "privacy", "trajectory"],
            "thresholds": {"pass_at_1": 1.0},
        }
    )
    sample = EvalSample.from_mapping(
        {
            "schema": EVAL_SAMPLE_SCHEMA,
            "sample_id": "cleanup.smoke_seed7",
            "version": "2026-06-15",
            "surface": "household-world",
            "intent": "cleanup",
            "preset": "cleanup",
            "world": "molmospaces/val_0",
            "backend": "mujoco",
            "evidence_lane": "world-oracle-labels",
            "camera_labeler": MISSING_NOT_APPLICABLE,
            "scenario_setup": "relocate-cleanup-related-objects",
            "seed": 7,
            "prompt": MISSING_NOT_APPLICABLE,
            "goal_contract_hash": MISSING_UNAVAILABLE,
            "allowed_agent_engines": ["direct-runner"],
            "trial_count": 1,
            "required_graders": ["artifacts", "privacy", "trajectory"],
            "private_goal_reference": {
                "schema": "household_eval_private_goal_reference_v1",
                "scorer_input": "private",
            },
        }
    )
    trial = EvalTrial.from_sample(
        sample,
        suite=suite,
        trial_id="trial-cleanup-smoke-seed7-0001",
        repetition_index=0,
        agent_engine="direct-runner",
        runner_class="direct_runner",
        provider_profile=MISSING_NOT_APPLICABLE,
        model=MISSING_NOT_APPLICABLE,
        skill_name="molmo-realworld-cleanup",
        prompt_source=MISSING_NOT_APPLICABLE,
        mcp_profile="household_world_v1+household_manipulation_v1",
        tool_surface=["metric_map", "observe", "done"],
        budgets={"steps": 50, "time_s": 120, "token": MISSING_NOT_APPLICABLE},
        runtime={"host": MISSING_UNAVAILABLE, "network": MISSING_UNAVAILABLE},
        limitations=["simulator_not_executed_in_schema_slice"],
    )

    assert EvalSuite.from_mapping(suite.to_dict()) == suite
    assert EvalSample.from_mapping(sample.to_dict()) == sample
    assert EvalTrial.from_mapping(trial.to_dict()) == trial

    result = EvalResult.from_trial(
        trial,
        status="passed",
        failure_class=MISSING_NOT_APPLICABLE,
        grader_outputs={
            "artifacts": {"status": "passed", "required_artifacts": ["run_result.json"]},
            "privacy": {"status": "passed", "private_truth_leak_count": 0},
        },
        artifacts={
            "run_result": "runs/cleanup-smoke-seed7/run_result.json",
            "report": "runs/cleanup-smoke-seed7/report.html",
        },
        artifact_schema_versions={"run_result": MISSING_UNAVAILABLE},
        metrics={"pass": 1.0, "private_truth_leak_count": 0},
    )

    result_path = tmp_path / "eval_result.json"
    result_path.write_text(json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n")

    loaded = EvalResult.from_mapping(json.loads(result_path.read_text()))
    assert loaded == result
    payload = loaded.to_dict()
    assert payload["schema"] == EVAL_RESULT_SCHEMA
    assert trial.to_dict()["schema"] == EVAL_TRIAL_SCHEMA
    assert payload["identity"]["suite_id"] == suite.suite_id
    assert payload["identity"]["sample_id"] == sample.sample_id
    assert payload["identity"]["trial_id"] == trial.trial_id
    assert payload["identity"]["provider_profile"] == MISSING_NOT_APPLICABLE
    assert payload["identity"]["model"] == MISSING_NOT_APPLICABLE
    assert payload["identity"]["runtime"]["host"] == MISSING_UNAVAILABLE
    assert payload["identity"]["budgets"]["cost"] == MISSING_UNAVAILABLE
    assert payload["artifact_schema_versions"]["report"] == MISSING_UNAVAILABLE


def test_eval_result_requires_known_failure_class_for_failed_trials() -> None:
    sample = EvalSample.from_mapping(_minimal_sample_payload())
    suite = EvalSuite.from_mapping(_minimal_suite_payload(sample.sample_id))
    trial = EvalTrial.from_sample(
        sample,
        suite=suite,
        trial_id="trial-1",
        repetition_index=0,
        agent_engine="direct-runner",
        runner_class="direct_runner",
    )

    result = EvalResult.from_trial(
        trial,
        status="failed",
        failure_class="private_truth_leak",
        grader_outputs={"privacy": {"status": "failed"}},
    )

    assert result.failure_class == "private_truth_leak"
    assert result.identity["budgets"]["steps"] == MISSING_UNAVAILABLE
    assert result.identity["runtime"]["network"] == MISSING_UNAVAILABLE
    assert "private_truth_leak" in FAILURE_CLASSES
    with pytest.raises(ValueError, match="unknown failure_class"):
        EvalResult.from_trial(
            trial,
            status="failed",
            failure_class="vague_agent_failure",
            grader_outputs={},
        )
    with pytest.raises(ValueError, match="failed eval_result requires failure_class"):
        EvalResult.from_trial(
            trial,
            status="failed",
            failure_class=MISSING_NOT_APPLICABLE,
            grader_outputs={},
        )


def test_eval_result_from_mapping_validates_status_and_normalizes_artifact_schemas() -> None:
    sample = EvalSample.from_mapping(_minimal_sample_payload())
    suite = EvalSuite.from_mapping(_minimal_suite_payload(sample.sample_id))
    trial = EvalTrial.from_sample(
        sample,
        suite=suite,
        trial_id="trial-1",
        repetition_index=0,
        agent_engine="direct-runner",
        runner_class="direct_runner",
    )
    payload = EvalResult.from_trial(
        trial,
        status="passed",
        failure_class=MISSING_NOT_APPLICABLE,
        grader_outputs={"artifacts": {"status": "passed"}},
        artifacts={"report": "runs/trial-1/report.html"},
    ).to_dict()
    payload["artifact_schema_versions"] = {}

    loaded = EvalResult.from_mapping(payload)

    assert loaded.artifact_schema_versions["report"] == MISSING_UNAVAILABLE
    payload["status"] = "success"
    with pytest.raises(ValueError, match="unknown eval_result status"):
        EvalResult.from_mapping(payload)


def test_eval_trial_from_sample_rejects_disallowed_agent_engine() -> None:
    sample = EvalSample.from_mapping(_minimal_sample_payload())
    suite = EvalSuite.from_mapping(_minimal_suite_payload(sample.sample_id))

    with pytest.raises(ValueError, match="is not allowed for sample"):
        EvalTrial.from_sample(
            sample,
            suite=suite,
            trial_id="trial-1",
            repetition_index=0,
            agent_engine="codex-cli",
            runner_class="direct_runner",
        )


def test_eval_sample_requires_explicit_missing_identity_fields() -> None:
    payload = _minimal_sample_payload()
    payload.pop("goal_contract_hash")

    with pytest.raises(ValueError, match="goal_contract_hash"):
        EvalSample.from_mapping(payload)

    payload["goal_contract_hash"] = MISSING_UNAVAILABLE
    sample = EvalSample.from_mapping(payload)
    assert sample.goal_contract_hash == MISSING_UNAVAILABLE


def test_eval_sample_rejects_non_string_identity_values() -> None:
    payload = _minimal_sample_payload()
    payload["prompt"] = 123

    with pytest.raises(ValueError, match="prompt must be a non-empty string"):
        EvalSample.from_mapping(payload)

    payload = _minimal_sample_payload()
    payload["provider_profiles"] = ["not_applicable", 3]
    with pytest.raises(ValueError, match="provider_profiles must be a list of non-empty strings"):
        EvalSample.from_mapping(payload)


def test_direct_runner_fixture_suite_loads_sample_contract() -> None:
    suite = load_eval_suite(SMOKE_SUITE)
    sample = load_eval_sample(REPO_ROOT / suite.sample_refs[0])

    assert suite.schema == EVAL_SUITE_SCHEMA
    assert suite.suite_id == "household_world.smoke_regression"
    assert suite.sample_ids == ("cleanup.smoke_seed7",)
    assert suite.sample_refs == ("evals/household_world/samples/cleanup/smoke_seed7.json",)
    assert sample.schema == EVAL_SAMPLE_SCHEMA
    assert sample.sample_id == "cleanup.smoke_seed7"
    assert sample.allowed_agent_engines == ("direct-runner",)
    assert sample.provider_profiles == (MISSING_NOT_APPLICABLE,)
    assert sample.goal_contract_hash == MISSING_UNAVAILABLE
    assert "artifacts" in sample.required_graders


def test_all_household_world_sample_fixtures_are_schema_valid() -> None:
    sample_paths = sorted((REPO_ROOT / "evals" / "household_world" / "samples").glob("*/*.json"))

    assert sample_paths
    loaded = [load_eval_sample(path) for path in sample_paths]
    assert {sample.sample_id for sample in loaded} == {
        "cleanup.smoke_seed7",
        "map_build.baseline_seed7",
    }


def _minimal_suite_payload(sample_id: str) -> dict:
    return {
        "schema": EVAL_SUITE_SCHEMA,
        "suite_id": "household_world.smoke_regression",
        "version": "2026-06-15",
        "capability": "household_world",
        "sample_ids": [sample_id],
        "required_graders": ["artifacts"],
        "thresholds": {"pass_at_1": 1.0},
    }


def _minimal_sample_payload() -> dict:
    return {
        "schema": EVAL_SAMPLE_SCHEMA,
        "sample_id": "cleanup.smoke_seed7",
        "version": "2026-06-15",
        "surface": "household-world",
        "intent": "cleanup",
        "preset": "cleanup",
        "world": "molmospaces/val_0",
        "backend": "mujoco",
        "evidence_lane": "world-oracle-labels",
        "camera_labeler": MISSING_NOT_APPLICABLE,
        "scenario_setup": "relocate-cleanup-related-objects",
        "seed": 7,
        "prompt": MISSING_NOT_APPLICABLE,
        "goal_contract_hash": MISSING_UNAVAILABLE,
        "allowed_agent_engines": ["direct-runner"],
        "trial_count": 1,
        "required_graders": ["artifacts"],
        "private_goal_reference": {
            "schema": "household_eval_private_goal_reference_v1",
            "scorer_input": "private",
        },
    }
