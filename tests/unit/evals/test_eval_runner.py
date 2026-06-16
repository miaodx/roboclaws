from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from roboclaws.evals.live_runtime import live_surface_command, live_surface_env
from roboclaws.evals.regression import (
    promote_regression_from_cli_overrides,
    promote_regression_sample_from_eval_result,
)
from roboclaws.evals.runner import run_eval_suite
from roboclaws.launch.catalog import resolve_surface_launch


def test_eval_runner_writes_result_bundle_and_report(tmp_path: Path) -> None:
    run = run_eval_suite(
        "smoke_regression",
        output_root=tmp_path,
        stamp="unit",
        product_runner=_passing_product_runner,
    )

    assert run.results_path.exists()
    assert run.report_path.exists()
    payload = json.loads(run.results_path.read_text())
    assert payload["schema"] == "roboclaws_eval_results_bundle_v1"
    assert payload["suite"]["suite_id"] == "household_world.smoke_regression"
    assert payload["aggregate"]["total"] == 1
    assert payload["aggregate"]["trial_count"] == 1
    assert payload["aggregate"]["sample_count"] == 1
    assert payload["aggregate"]["passed"] == 1
    assert payload["aggregate"]["pass_at_1"] == 1.0
    assert payload["aggregate"]["pass_at_k"] == {"1": 1.0}
    assert payload["aggregate"]["pass_caret_k"] == {"1": 1.0}
    assert "sampler_projection" not in payload["aggregate"]

    result = payload["results"][0]
    assert result["status"] == "passed"
    assert result["failure_class"] == "not_applicable"
    assert result["grader_outputs"]["outcome"]["completion_status"] == "success"
    assert result["identity"]["agent_engine"] == "direct-runner"
    assert result["identity"]["provider_profile"] == "not_applicable"
    assert result["artifacts"]["run_result"].endswith("run_result.json")
    assert result["artifacts"]["report"].endswith("report.html")
    report_html = run.report_path.read_text()
    assert "run_result" in report_html
    assert 'href="runs/cleanup_smoke_seed7/trial-0000/run_result.json"' in report_html
    assert "Scene Sampler Projection" not in report_html


def test_eval_runner_classifies_missing_product_artifacts(tmp_path: Path) -> None:
    run = run_eval_suite(
        "smoke_regression",
        output_root=tmp_path,
        stamp="artifact-failure",
        product_runner=_missing_artifact_product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    result = payload["results"][0]
    assert result["status"] == "failed"
    assert result["failure_class"] == "artifact_missing"
    assert payload["aggregate"]["failure_classes"] == {"artifact_missing": 1}
    assert "report" in result["grader_outputs"]["artifacts"]["missing"]


def test_eval_runner_classifies_environment_blocked_exception(tmp_path: Path) -> None:
    run = run_eval_suite(
        "smoke_regression",
        output_root=tmp_path,
        stamp="blocked",
        product_runner=_blocked_product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    result = payload["results"][0]
    assert result["status"] == "blocked"
    assert result["failure_class"] == "environment_blocked"
    assert result["grader_outputs"]["runner"]["error_type"] == "ModuleNotFoundError"


def test_eval_runner_records_repetition_metrics(tmp_path: Path) -> None:
    run = run_eval_suite(
        "cleanup_capability",
        output_root=tmp_path,
        stamp="repeat",
        product_runner=_passing_product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["total"] == 3
    assert payload["aggregate"]["sample_count"] == 1
    assert payload["aggregate"]["max_repetition_count"] == 3
    assert payload["aggregate"]["pass_at_k"] == {"1": 1.0, "2": 1.0, "3": 1.0}
    assert payload["aggregate"]["pass_caret_k"] == {"1": 1.0, "2": 1.0, "3": 1.0}
    assert payload["aggregate"]["pass_caret_k_eligible"] == {"1": 1, "2": 1, "3": 1}
    sample = payload["aggregate"]["samples"]["cleanup.repeated_seed7"]
    assert sample["trial_count"] == 3
    assert sample["pass_all"] is True
    assert [
        result["identity"]["repetition_index"]
        for result in payload["results"]
        if result["identity"]["sample_id"] == "cleanup.repeated_seed7"
    ] == [0, 1, 2]


def test_eval_runner_records_live_agent_blocked_identity(tmp_path: Path) -> None:
    run = run_eval_suite(
        "cleanup_capability",
        output_root=tmp_path,
        stamp="live-blocked",
        agent_engine="codex-cli",
        provider_profile="codex-env",
        product_runner=_passing_product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["total"] == 3
    assert payload["aggregate"]["blocked"] == 3
    assert payload["aggregate"]["pass_at_k"] == {"1": 0.0, "2": 0.0, "3": 0.0}
    assert payload["aggregate"]["pass_caret_k"] == {"1": 0.0, "2": 0.0, "3": 0.0}
    assert payload["aggregate"]["failure_classes"] == {"model_or_provider_unavailable": 3}
    result = payload["results"][0]
    assert result["status"] == "blocked"
    assert result["failure_class"] == "model_or_provider_unavailable"
    assert result["identity"]["agent_engine"] == "codex-cli"
    assert result["identity"]["runner_class"] == "live-agent"
    assert result["identity"]["provider_profile"] == "codex-env"
    assert result["grader_outputs"]["runner"]["error_type"] == "LiveAgentEvalNotExecuted"
    preflight = result["grader_outputs"]["runner"]["preflight"]
    assert preflight["schema"] == "roboclaws_live_eval_preflight_v1"
    assert preflight["provider_readiness"]["provider_profile"] == "codex-env"
    assert preflight["provider_readiness"]["required_env"] == ["CODEX_BASE_URL", "CODEX_API_KEY"]
    assert preflight["runtime_readiness"]["required_runtime"] == "docker-backed coding-agent CLI"
    assert preflight["blocker"] == "live_execution_not_requested"
    assert preflight["runtime_readiness"]["repo_native_live_eval_runner"] == (
        "opt_in_via_live_execution_run"
    )
    assert "live_agent_eval_execution_not_requested" in result["limitations"]


def test_eval_runner_runs_live_agent_when_explicitly_enabled(tmp_path: Path) -> None:
    seen_kwargs: list[dict[str, Any]] = []

    def live_product_runner(**kwargs: Any) -> dict[str, Any]:
        seen_kwargs.append(kwargs)
        surface_run_dir = Path(kwargs["output_dir"]) / "surface-run" / f"seed-{kwargs['seed']}"
        _write_product_artifacts(surface_run_dir, completion_status="success")
        result = _run_result(surface_run_dir, completion_status="success")
        result["eval_effective_run_dir"] = str(surface_run_dir)
        return result

    run = run_eval_suite(
        "cleanup_capability",
        output_root=tmp_path,
        stamp="live-run",
        agent_engine="openai-agents-sdk",
        provider_profile="codex-env",
        live_execution="run",
        live_timeout_s=12.5,
        live_product_runner=live_product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["passed"] == 3
    assert payload["aggregate"]["blocked"] == 0
    assert seen_kwargs[0]["agent_engine"] == "openai-agents-sdk"
    assert seen_kwargs[0]["provider_profile"] == "codex-env"
    assert seen_kwargs[0]["live_timeout_s"] == 12.5
    result = payload["results"][0]
    assert result["identity"]["runner_class"] == "live-agent"
    assert result["artifacts"]["run_result"].endswith(
        "runs/cleanup_repeated_seed7/trial-0000/surface-run/seed-7/run_result.json"
    )


def test_eval_runner_classifies_live_provider_failures_as_blocked(tmp_path: Path) -> None:
    def live_product_runner(**_kwargs: Any) -> dict[str, Any]:
        raise RuntimeError(
            "OpenAI Agents SDK runtime failed: provider_transient_failure; "
            "Error code: 502 - bad_response_status_code"
        )

    run = run_eval_suite(
        "cleanup_capability",
        output_root=tmp_path,
        stamp="live-provider-blocked",
        agent_engine="openai-agents-sdk",
        provider_profile="codex-env",
        live_execution="run",
        live_product_runner=live_product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["blocked"] == 3
    assert payload["aggregate"]["failed"] == 0
    assert payload["aggregate"]["failure_classes"] == {"model_or_provider_unavailable": 3}
    result = payload["results"][0]
    assert result["status"] == "blocked"
    assert result["failure_class"] == "model_or_provider_unavailable"
    assert result["grader_outputs"]["runner"]["status"] == "blocked"


def test_live_surface_product_discovers_timestamped_run_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from roboclaws.evals import live_runtime

    command_log: list[list[str]] = []

    def fake_run(
        command: list[str],
        **_kwargs: Any,
    ) -> Any:
        command_log.append(command)
        output_arg = next(item for item in command if item.startswith("output_dir="))
        output_dir = Path(output_arg.removeprefix("output_dir="))
        timestamped_run_dir = output_dir / "0615_0305" / "seed-7"
        _write_product_artifacts(timestamped_run_dir, completion_status="success")
        (timestamped_run_dir / "run_result.json").write_text(
            json.dumps(_run_result(timestamped_run_dir, completion_status="success")) + "\n"
        )
        return _completed_process(returncode=0)

    monkeypatch.setattr(live_runtime.subprocess, "run", fake_run)

    result = live_runtime.run_live_surface_product(**_live_surface_kwargs(tmp_path / "trial-0000"))

    assert command_log
    assert result["eval_effective_run_dir"].endswith("surface-run/0615_0305/seed-7")
    assert (tmp_path / "trial-0000" / "live_eval_command.json").exists()


def test_live_surface_product_waits_for_detached_codex_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from roboclaws.evals import live_runtime

    sleeps: list[float] = []
    status_reads = 0

    def fake_run(
        command: list[str],
        **_kwargs: Any,
    ) -> Any:
        output_arg = next(item for item in command if item.startswith("output_dir="))
        output_dir = Path(output_arg.removeprefix("output_dir="))
        run_dir = output_dir / "0615_0310" / "seed-7"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "live_status.json").write_text('{"phase": "queued"}\n')
        return _completed_process(returncode=0)

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        run_dir = tmp_path / "trial-0000" / "surface-run" / "0615_0310" / "seed-7"
        nonlocal status_reads
        status_reads += 1
        if status_reads == 2:
            _write_product_artifacts(run_dir, completion_status="success")
            (run_dir / "run_result.json").write_text(
                json.dumps(_run_result(run_dir, completion_status="success")) + "\n"
            )
            (run_dir / "live_status.json").write_text('{"phase": "finished", "exit_status": 0}\n')

    clock = {"now": 0.0}

    def fake_monotonic() -> float:
        clock["now"] += 0.25
        return clock["now"]

    monkeypatch.setattr(live_runtime.subprocess, "run", fake_run)
    monkeypatch.setattr(live_runtime.time, "sleep", fake_sleep)
    monkeypatch.setattr(live_runtime.time, "monotonic", fake_monotonic)

    result = live_runtime.run_live_surface_product(
        **_live_surface_kwargs(tmp_path / "trial-0000", live_timeout_s=5.0)
    )

    assert sleeps
    assert result["eval_effective_run_dir"].endswith("surface-run/0615_0310/seed-7")


def test_live_surface_product_recovers_completed_artifact_after_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from roboclaws.evals import live_runtime

    clock = {"now": 0.0}
    poll_count = {"value": 0}
    timeout_run_dir: Path | None = None

    def fake_monotonic() -> float:
        return clock["now"]

    def fake_sleep(seconds: float) -> None:
        clock["now"] += seconds
        poll_count["value"] += 1
        if poll_count["value"] == 2 and timeout_run_dir is not None:
            _write_product_artifacts(timeout_run_dir, completion_status="success")
            (timeout_run_dir / "run_result.json").write_text(
                json.dumps(_run_result(timeout_run_dir, completion_status="success")) + "\n"
            )
            (timeout_run_dir / "live_status.json").write_text(
                '{"phase": "finished", "exit_status": 0}\n'
            )

    def fake_run(command: list[str], **_kwargs: Any) -> Any:
        output_arg = next(item for item in command if item.startswith("output_dir="))
        output_dir = Path(output_arg.removeprefix("output_dir="))
        run_dir = output_dir / "0615_0311" / "seed-7"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "live_status.json").write_text('{"phase": "running"}\n')
        nonlocal timeout_run_dir
        timeout_run_dir = run_dir
        raise live_runtime.subprocess.TimeoutExpired(
            cmd=command,
            timeout=5.0,
            output=f"Artifacts: {run_dir}\n",
            stderr="",
        )

    monkeypatch.setattr(live_runtime.subprocess, "run", fake_run)
    monkeypatch.setattr(live_runtime.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(live_runtime.time, "sleep", fake_sleep)

    result = live_runtime.run_live_surface_product(
        **_live_surface_kwargs(tmp_path / "trial-0000", live_timeout_s=5.0)
    )

    assert result["eval_effective_run_dir"].endswith("surface-run/0615_0311/seed-7")
    record = json.loads((tmp_path / "trial-0000" / "live_eval_command.json").read_text())
    assert record["returncode"] == "timeout_after_completion"
    assert record["timeout_completion_grace_s"] == 30.0


def test_live_surface_product_recovers_after_detached_wait_deadline(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from roboclaws.evals import live_runtime

    clock = {"now": 0.0}
    sleep_count = {"value": 0}
    detached_run_dir: Path | None = None

    def fake_run(command: list[str], **_kwargs: Any) -> Any:
        output_arg = next(item for item in command if item.startswith("output_dir="))
        output_dir = Path(output_arg.removeprefix("output_dir="))
        run_dir = output_dir / "0615_0312" / "seed-7"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "live_status.json").write_text('{"phase": "running-codex"}\n')
        nonlocal detached_run_dir
        detached_run_dir = run_dir
        return _completed_process(returncode=0)

    def fake_monotonic() -> float:
        return clock["now"]

    def fake_sleep(seconds: float) -> None:
        clock["now"] += seconds
        sleep_count["value"] += 1
        if sleep_count["value"] == 3 and detached_run_dir is not None:
            _write_product_artifacts(detached_run_dir, completion_status="success")
            (detached_run_dir / "run_result.json").write_text(
                json.dumps(_run_result(detached_run_dir, completion_status="success")) + "\n"
            )

    monkeypatch.setattr(live_runtime.subprocess, "run", fake_run)
    monkeypatch.setattr(live_runtime.time, "monotonic", fake_monotonic)
    monkeypatch.setattr(live_runtime.time, "sleep", fake_sleep)

    result = live_runtime.run_live_surface_product(
        **_live_surface_kwargs(tmp_path / "trial-0000", live_timeout_s=1.0)
    )

    assert result["eval_effective_run_dir"].endswith("surface-run/0615_0312/seed-7")


def test_live_open_ended_eval_grades_artifacts_after_checker_nonzero_exit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from roboclaws.evals import live_runtime

    def fake_run(command: list[str], **_kwargs: Any) -> Any:
        output_arg = next(item for item in command if item.startswith("output_dir="))
        output_dir = Path(output_arg.removeprefix("output_dir="))
        run_dir = output_dir / "seed-7"
        _write_product_artifacts(
            run_dir,
            completion_status="failed",
            include_goal_contract=True,
        )
        (run_dir / "run_result.json").write_text(
            json.dumps(
                _run_result(
                    run_dir,
                    completion_status="failed",
                    task_intent="open-ended",
                    include_completion_claim=True,
                )
            )
            + "\n"
        )
        (run_dir / "live_status.json").write_text(
            '{"phase": "failed", "exit_status": 1, '
            '"reason": "cleanup checker exited with status 1"}\n'
        )
        return _completed_process(
            returncode=1,
            stderr="cleanup checker exited with status 1",
        )

    monkeypatch.setattr(live_runtime.subprocess, "run", fake_run)

    run = run_eval_suite(
        "open_ended_goals",
        output_root=tmp_path,
        stamp="live-open-ended-checker-nonzero",
        agent_engine="openai-agents-sdk",
        provider_profile="codex-env",
        live_execution="run",
        live_timeout_s=12.5,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["passed"] == 3
    assert payload["aggregate"]["failed"] == 0
    result = payload["results"][0]
    assert result["status"] == "passed"
    assert result["identity"]["agent_engine"] == "openai-agents-sdk"
    assert result["grader_outputs"]["open_ended"]["completion_claim_present"] is True
    assert result["artifacts"]["run_result"].endswith(
        "runs/open_ended_drink_seed7/trial-0000/surface-run/seed-7/run_result.json"
    )
    command_record = json.loads(
        (
            tmp_path
            / "household_world_open_ended_goals"
            / "live-open-ended-checker-nonzero"
            / "runs"
            / "open_ended_drink_seed7"
            / "trial-0000"
            / "live_eval_command.json"
        ).read_text()
    )
    assert command_record["returncode"] == 1


def test_live_open_ended_eval_waits_for_detached_checker_status_after_recovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from roboclaws.evals import live_runtime
    from roboclaws.evals.models import load_eval_sample

    sleeps: list[float] = []
    current_run_dir: Path | None = None
    clock = {"now": 0.0}

    def fake_run(command: list[str], **_kwargs: Any) -> Any:
        output_arg = next(item for item in command if item.startswith("output_dir="))
        output_dir = Path(output_arg.removeprefix("output_dir="))
        run_dir = output_dir / "0616_1405" / "seed-7"
        nonlocal current_run_dir
        current_run_dir = run_dir
        _write_product_artifacts(
            run_dir,
            completion_status="failed",
            include_goal_contract=True,
        )
        (run_dir / "run_result.json").write_text(
            json.dumps(
                _run_result(
                    run_dir,
                    completion_status="failed",
                    task_intent="open-ended",
                    include_completion_claim=True,
                )
            )
            + "\n"
        )
        (run_dir / "live_status.json").write_text('{"phase": "running-codex"}\n')
        return _completed_process(returncode=1, stderr="cleanup checker exited with status 1")

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)
        clock["now"] += seconds
        assert current_run_dir is not None
        run_dir = current_run_dir
        (run_dir / "live_status.json").write_text(
            '{"phase": "failed", "exit_status": 1, '
            '"reason": "cleanup checker exited with status 1"}\n'
        )

    def fake_monotonic() -> float:
        return clock["now"]

    monkeypatch.setattr(live_runtime.subprocess, "run", fake_run)
    monkeypatch.setattr(live_runtime.time, "sleep", fake_sleep)
    monkeypatch.setattr(live_runtime.time, "monotonic", fake_monotonic)
    sample = load_eval_sample(
        Path(__file__).resolve().parents[3]
        / "evals"
        / "household_world"
        / "samples"
        / "open_ended"
        / "drink_seed7.json"
    )
    kwargs = _live_surface_kwargs(tmp_path / "trial-0000", live_timeout_s=12.5)
    kwargs["eval_sample"] = sample

    result = live_runtime.run_live_surface_product(**kwargs)

    assert sleeps
    assert result["eval_effective_run_dir"].endswith("surface-run/0616_1405/seed-7")
    command_record = json.loads((tmp_path / "trial-0000" / "live_eval_command.json").read_text())
    assert command_record["returncode"] == 1


def test_open_ended_positive_predicates_pass_with_public_runtime_evidence(
    tmp_path: Path,
) -> None:
    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        _write_product_artifacts(
            run_dir,
            completion_status="success",
            include_goal_contract=True,
        )
        return _run_result(
            run_dir,
            completion_status="success",
            task_intent="open-ended",
            include_completion_claim=True,
            wall_time_s=1.25,
        )

    run = run_eval_suite(
        "open_ended_goals",
        output_root=tmp_path,
        stamp="open-ended-positive-predicate",
        product_runner=product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["passed"] == 3
    assert payload["aggregate"]["failed"] == 0
    assert payload["aggregate"]["open_ended"]["by_category"]["negative_search"]["passed"] == 1
    assert payload["aggregate"]["open_ended"]["by_category"]["area_inspection"]["passed"] == 1
    assert (
        payload["aggregate"]["open_ended"]["by_category"]["positive_observable"]["passed"] == 1
    )
    assert payload["aggregate"]["open_ended"]["telemetry"]["tool_call_count"] == 3
    results = {result["identity"]["sample_id"]: result for result in payload["results"]}
    room_predicate = results["open_ended.room4_anchor_seed7"]["grader_outputs"][
        "open_ended"
    ]["success_predicate"]
    living_predicate = results["open_ended.living_waypoint_seed7"]["grader_outputs"][
        "open_ended"
    ]["success_predicate"]
    assert room_predicate["passed"] is True
    assert room_predicate["evidence"]["anchor_id"] == "anchor_waypoint_generated_exploration_005"
    assert living_predicate["passed"] is True
    assert "generated_exploration_005" in living_predicate["evidence"]["visited_waypoint_ids"]


def test_open_ended_authoritative_predicate_failure_is_behavior_failure(
    tmp_path: Path,
) -> None:
    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        _write_product_artifacts(
            run_dir,
            completion_status="success",
            include_goal_contract=True,
            include_open_ended_public_evidence=False,
        )
        (run_dir / "trace.jsonl").write_text(
            "\n".join(
                [
                    '{"event": "request", "tool": "metric_map"}',
                    '{"event": "response", "tool": "metric_map"}',
                    '{"event": "request", "tool": "done"}',
                    '{"event": "response", "tool": "done"}',
                ]
            )
            + "\n"
        )
        return _run_result(
            run_dir,
            completion_status="success",
            task_intent="open-ended",
            include_completion_claim=True,
        )

    run = run_eval_suite(
        "open_ended_goals",
        output_root=tmp_path,
        stamp="open-ended-positive-predicate-fail",
        product_runner=product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["passed"] == 1
    assert payload["aggregate"]["failed"] == 2
    assert payload["aggregate"]["failure_classes"] == {"private_goal_not_satisfied": 2}
    results = {result["identity"]["sample_id"]: result for result in payload["results"]}
    assert results["open_ended.drink_seed7"]["status"] == "passed"
    assert results["open_ended.room4_anchor_seed7"]["status"] == "failed"
    assert results["open_ended.room4_anchor_seed7"]["failure_class"] == (
        "private_goal_not_satisfied"
    )


def test_open_ended_waypoint_predicate_accepts_trace_visit_without_runtime_anchor(
    tmp_path: Path,
) -> None:
    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        sample_id = kwargs["run_metadata_overrides"]["eval_sample_id"]
        _write_product_artifacts(
            run_dir,
            completion_status="success",
            include_goal_contract=True,
            include_open_ended_public_evidence=sample_id != "open_ended.living_waypoint_seed7",
        )
        if sample_id == "open_ended.room4_anchor_seed7":
            (run_dir / "trace.jsonl").write_text(
                "\n".join(
                    [
                        '{"event": "request", "tool": "resolve_target_query"}',
                        '{"event": "response", "tool": "resolve_target_query"}',
                        (
                            '{"event": "request", "tool": "navigate_to_waypoint", '
                            '"request": {"waypoint_id": "generated_exploration_005"}}'
                        ),
                        '{"event": "response", "tool": "navigate_to_waypoint"}',
                        '{"event": "request", "tool": "observe"}',
                        '{"event": "response", "tool": "observe"}',
                        '{"event": "request", "tool": "done"}',
                        '{"event": "response", "tool": "done"}',
                    ]
                )
                + "\n"
            )
        if sample_id == "open_ended.living_waypoint_seed7":
            (run_dir / "trace.jsonl").write_text(
                "\n".join(
                    [
                        '{"event": "request", "tool": "metric_map"}',
                        '{"event": "response", "tool": "metric_map"}',
                        (
                            '{"event": "request", "tool": "navigate_to_waypoint", '
                            '"request": {"waypoint_id": "generated_exploration_005"}}'
                        ),
                        '{"event": "response", "tool": "navigate_to_waypoint"}',
                        '{"event": "request", "tool": "done"}',
                        '{"event": "response", "tool": "done"}',
                    ]
                )
                + "\n"
            )
        return _run_result(
            run_dir,
            completion_status="success",
            task_intent="open-ended",
            include_completion_claim=True,
        )

    run = run_eval_suite(
        "open_ended_goals",
        output_root=tmp_path,
        stamp="open-ended-trace-visit",
        product_runner=product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["passed"] == 3
    results = {result["identity"]["sample_id"]: result for result in payload["results"]}
    assert results["open_ended.room4_anchor_seed7"]["grader_outputs"]["trajectory"]["status"] == (
        "passed"
    )
    assert results["open_ended.living_waypoint_seed7"]["grader_outputs"]["open_ended"][
        "success_predicate"
    ]["passed"] is True


def test_live_surface_command_uses_current_public_launch_axes(tmp_path: Path) -> None:
    seen_kwargs: list[dict[str, Any]] = []

    def live_product_runner(**kwargs: Any) -> dict[str, Any]:
        seen_kwargs.append(kwargs)
        run_dir = Path(kwargs["output_dir"])
        _write_product_artifacts(run_dir, completion_status="success")
        return _run_result(run_dir, completion_status="success")

    run_eval_suite(
        "cleanup_capability",
        output_root=tmp_path,
        stamp="live-command",
        agent_engine="codex-cli",
        provider_profile="codex-env",
        live_execution="run",
        live_product_runner=live_product_runner,
    )

    command = live_surface_command(seen_kwargs[0], output_dir=tmp_path / "surface-run")
    assert "backend=mujoco" in command
    assert "agent_engine=codex-cli" in command
    assert "provider_profile=codex-env" in command
    assert "evidence_lane=world-oracle-labels" in command
    assert "run_preset=smoke" in command
    assert "preset=cleanup" in command
    assert not any(item.startswith("generated_mess_count=") for item in command)
    plan = resolve_surface_launch(command[5:])
    assert plan.agent_engine == "codex-cli"
    assert plan.backend == "mujoco"
    assert plan.mode == "smoke"


def test_live_surface_command_uses_no_preset_public_open_task_route(tmp_path: Path) -> None:
    seen_kwargs: list[dict[str, Any]] = []

    def live_product_runner(**kwargs: Any) -> dict[str, Any]:
        seen_kwargs.append(kwargs)
        run_dir = Path(kwargs["output_dir"])
        _write_product_artifacts(
            run_dir,
            completion_status="success",
            include_goal_contract=True,
        )
        return _run_result(
            run_dir,
            completion_status="success",
            task_intent="open-ended",
            include_completion_claim=True,
        )

    run_eval_suite(
        "open_ended_goals",
        output_root=tmp_path,
        stamp="live-open-task-command",
        agent_engine="codex-cli",
        provider_profile="codex-env",
        live_execution="run",
        live_product_runner=live_product_runner,
    )

    command = live_surface_command(seen_kwargs[0], output_dir=tmp_path / "surface-run")
    assert "surface=household-world" in command
    assert "agent_engine=codex-cli" in command
    assert "provider_profile=codex-env" in command
    assert "run_preset=smoke" in command
    assert not any(item.startswith("preset=") for item in command)
    assert any(item.startswith("prompt=") for item in command)
    plan = resolve_surface_launch(command[5:])
    assert plan.intent == "open-ended"
    assert plan.preset is None


def test_live_surface_env_sets_provider_and_model_keys(tmp_path: Path) -> None:
    kwargs: dict[str, Any] = {
        "agent_engine": "claude-code",
        "provider_profile": "mimo-anthropic",
        "model": "mimo-v2.5",
    }

    env = live_surface_env(kwargs, base_env={"PATH": "/bin"})

    assert env["PATH"] == "/bin"
    assert env["ROBOCLAWS_CLAUDE_PROVIDER"] == "mimo-anthropic"
    assert env["ROBOCLAWS_CLAUDE_MODEL"] == "mimo-v2.5"


def test_map_build_consumer_suite_passes_runtime_map_prior_between_samples(
    tmp_path: Path,
) -> None:
    seen_runtime_priors: list[str] = []

    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        sample_id = kwargs["run_metadata_overrides"]["eval_sample_id"]
        if "runtime_map_prior_path" in kwargs:
            seen_runtime_priors.append(str(kwargs["runtime_map_prior_path"]))
        if sample_id == "map_build.baseline_seed7":
            _write_product_artifacts(run_dir, completion_status="semantic_sweep_complete")
            return _run_result(
                run_dir,
                completion_status="semantic_sweep_complete",
                semantic_sweep=True,
            )
        if sample_id == "open_ended.drink_seed7":
            _write_product_artifacts(
                run_dir,
                completion_status="failed",
                include_goal_contract=True,
            )
            return _run_result(
                run_dir,
                completion_status="failed",
                task_intent="open-ended",
                final_status="success",
                include_completion_claim=True,
            )
        _write_product_artifacts(run_dir, completion_status="success")
        return _run_result(run_dir, completion_status="success")

    run = run_eval_suite(
        "map_build_consumer",
        output_root=tmp_path,
        stamp="map-consumer",
        product_runner=product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["passed"] == 3
    assert payload["aggregate"]["failed"] == 0
    assert len(seen_runtime_priors) == 1
    assert seen_runtime_priors[0].endswith(
        "runs/map_build_baseline_seed7/trial-0000/runtime_metric_map.json"
    )
    results = {result["identity"]["sample_id"]: result for result in payload["results"]}
    map_result = results["map_build.baseline_seed7"]
    assert map_result["grader_outputs"]["outcome"]["runtime_metric_map_schema"] == (
        "runtime_metric_map_v1"
    )
    assert map_result["grader_outputs"]["outcome"]["public_semantic_anchor_count"] >= 1
    open_result = results["open_ended.drink_seed7"]
    assert open_result["status"] == "passed"
    assert open_result["grader_outputs"]["outcome"]["completion_claim_present"] is True
    assert open_result["grader_outputs"]["outcome"]["artifact_readiness"] == "ready"
    assert (
        open_result["grader_outputs"]["open_ended"]["semantic_satisfaction_authoritative"] is False
    )


def test_map_build_eval_catches_unusable_runtime_metric_map(tmp_path: Path) -> None:
    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        _write_product_artifacts(run_dir, completion_status="semantic_sweep_complete")
        (run_dir / "runtime_metric_map.json").write_text('{"schema": "wrong"}\n')
        return _run_result(run_dir, completion_status="semantic_sweep_complete")

    run = run_eval_suite(
        "evals/household_world/suites/map_build_consumer.json",
        output_root=tmp_path,
        stamp="bad-map",
        product_runner=product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    result = payload["results"][0]
    assert result["identity"]["sample_id"] == "map_build.baseline_seed7"
    assert result["status"] == "failed"
    assert result["failure_class"] == "map_actionability_failure"
    assert result["grader_outputs"]["outcome"]["schema_ok"] is False


def test_scene_sampler_stress_records_sampler_admission(tmp_path: Path) -> None:
    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        _write_product_artifacts(
            run_dir,
            completion_status="semantic_sweep_complete",
            generated_exploration_candidate_count=20,
        )
        return _run_result(
            run_dir,
            completion_status="semantic_sweep_complete",
            semantic_sweep=True,
        )

    run = run_eval_suite(
        "scene_sampler_stress",
        output_root=tmp_path,
        stamp="scene-sampler",
        product_runner=product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["sample_count"] == 20
    assert payload["aggregate"]["passed"] == 20
    assert payload["aggregate"]["failed"] == 0
    sampler_projection = payload["aggregate"]["sampler_projection"]
    assert sampler_projection["summary"]["ready_sample_count"] == 20
    assert sampler_projection["summary"]["remaining_sample_count"] == 20
    assert sampler_projection["summary"]["partial_source_count"] == 0
    assert sampler_projection["summary"]["blocked_source_count"] == 0
    assert sampler_projection["summary"]["rejected_source_count"] == 2
    assert sampler_projection["scene_sources"]["procthor-10k-val"]["ready_count"] == 10
    assert sampler_projection["scene_sources"]["procthor-10k-val"]["needed_count"] == 0
    assert sampler_projection["scene_sources"]["procthor-objaverse-val"]["ready_count"] == 10
    assert sampler_projection["scene_sources"]["procthor-objaverse-val"]["needed_count"] == 0
    assert sampler_projection["scene_sources"]["ithor"]["support_status"] == "rejected"
    result = payload["results"][0]
    assert result["grader_outputs"]["sampler_admission"]["status"] == "passed"
    assert result["grader_outputs"]["sampler_admission"]["scene_source"] == "procthor-10k-val"
    assert result["grader_outputs"]["sampler_admission"]["category_provenance"] == (
        "prepared_visual_label_manifest"
    )
    report_html = run.report_path.read_text()
    assert "Scene Sampler Projection" in report_html
    assert "Ready samples: 20 /" in report_html
    assert "remaining:\n    20" in report_html


def test_sampler_admission_rejects_heuristic_category_provenance(tmp_path: Path) -> None:
    sample = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "evals/household_world/samples/scene_sampler/procthor-10k-val_0_map_build.json"
        ).read_text(encoding="utf-8")
    )
    sample["sample_id"] = "scene_sampler.heuristic_rejected"
    sample["grader_config"]["sampler_admission"]["category_provenance"] = "room_area_fallback"
    sample_path = tmp_path / "heuristic_scene_sampler_sample.json"
    sample_path.write_text(json.dumps(sample), encoding="utf-8")
    suite_path = tmp_path / "heuristic_scene_sampler_suite.json"
    suite_path.write_text(
        json.dumps(
            {
                "schema": "roboclaws_eval_suite_v1",
                "suite_id": "household_world.scene_sampler_heuristic_rejected",
                "version": "2026-06-15",
                "capability": "household_world_scene_sampling",
                "sample_ids": [sample["sample_id"]],
                "sample_refs": [str(sample_path)],
                "required_graders": [
                    "artifacts",
                    "privacy",
                    "trajectory",
                    "sampler_admission",
                    "outcome",
                ],
                "thresholds": {"pass_at_1": 1.0},
            }
        ),
        encoding="utf-8",
    )

    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        _write_product_artifacts(
            run_dir,
            completion_status="semantic_sweep_complete",
            generated_exploration_candidate_count=20,
        )
        return _run_result(
            run_dir,
            completion_status="semantic_sweep_complete",
            semantic_sweep=True,
        )

    run = run_eval_suite(
        str(suite_path),
        output_root=tmp_path,
        stamp="heuristic-rejected",
        product_runner=product_runner,
    )

    result = json.loads(run.results_path.read_text())["results"][0]
    assert result["status"] == "failed"
    assert result["failure_class"] == "map_actionability_failure"
    assert result["grader_outputs"]["sampler_admission"]["failures"] == [
        "untrusted_room_category_provenance"
    ]


def test_cleanup_consumer_fails_when_runtime_map_dependency_is_missing(tmp_path: Path) -> None:
    launched_samples: list[str] = []

    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        sample_id = kwargs["run_metadata_overrides"]["eval_sample_id"]
        launched_samples.append(sample_id)
        if sample_id == "map_build.baseline_seed7":
            _write_product_artifacts(run_dir, completion_status="semantic_sweep_complete")
            (run_dir / "runtime_metric_map.json").unlink()
            return _run_result(
                run_dir,
                completion_status="semantic_sweep_complete",
                semantic_sweep=True,
                include_runtime_map=False,
            )
        if sample_id == "open_ended.drink_seed7":
            _write_product_artifacts(
                run_dir,
                completion_status="failed",
                include_goal_contract=True,
            )
            return _run_result(
                run_dir,
                completion_status="failed",
                task_intent="open-ended",
                final_status="success",
                include_completion_claim=True,
            )
        raise AssertionError("cleanup consumer should not launch without runtime_map_prior_path")

    run = run_eval_suite(
        "evals/household_world/suites/map_build_consumer.json",
        output_root=tmp_path,
        stamp="missing-map-prior",
        product_runner=product_runner,
    )

    results = json.loads(run.results_path.read_text())["results"]
    cleanup_result = next(
        result
        for result in results
        if result["identity"]["sample_id"] == "cleanup.consume_map_seed7"
    )
    assert launched_samples == ["map_build.baseline_seed7", "open_ended.drink_seed7"]
    assert cleanup_result["status"] == "failed"
    assert cleanup_result["failure_class"] == "artifact_missing"
    assert cleanup_result["grader_outputs"]["runner"]["error_type"] == "EvalDependencyError"
    assert cleanup_result["grader_outputs"]["artifacts"]["missing_dependencies"] == [
        "runtime_map_prior_path"
    ]


def test_open_ended_eval_separates_claim_from_artifact_readiness(tmp_path: Path) -> None:
    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        sample_id = kwargs["run_metadata_overrides"]["eval_sample_id"]
        if sample_id == "map_build.baseline_seed7":
            _write_product_artifacts(run_dir, completion_status="semantic_sweep_complete")
            return _run_result(
                run_dir,
                completion_status="semantic_sweep_complete",
                semantic_sweep=True,
            )
        if sample_id == "cleanup.consume_map_seed7":
            _write_product_artifacts(run_dir, completion_status="success")
            return _run_result(run_dir, completion_status="success")
        _write_product_artifacts(run_dir, completion_status="failed")
        return _run_result(run_dir, completion_status="failed", task_intent="open-ended")

    run = run_eval_suite(
        "evals/household_world/suites/map_build_consumer.json",
        output_root=tmp_path,
        stamp="open-ended-missing-claim",
        product_runner=product_runner,
    )

    results = json.loads(run.results_path.read_text())["results"]
    open_result = next(
        result for result in results if result["identity"]["sample_id"] == "open_ended.drink_seed7"
    )
    assert open_result["status"] == "failed"
    assert open_result["failure_class"] == "agent_no_completion_claim"
    assert open_result["grader_outputs"]["open_ended"]["completion_claim_present"] is False
    assert open_result["grader_outputs"]["open_ended"]["artifact_readiness"] == "missing"


def test_failed_eval_result_promotes_to_regression_sample_and_suite(tmp_path: Path) -> None:
    run = run_eval_suite(
        "smoke_regression",
        output_root=tmp_path,
        stamp="artifact-failure",
        product_runner=_missing_artifact_product_runner,
    )
    sample_output = tmp_path / "samples" / "regression_cleanup_missing_report.json"
    suite_output = tmp_path / "suites" / "smoke_regression_with_regression.json"

    promotion = promote_regression_sample_from_eval_result(
        run.results_path,
        regression_sample_id="regression.cleanup_missing_report",
        sample_output_path=sample_output,
        suite_output_path=suite_output,
        review_label="eval-regression:accepted",
        version="2026-06-15",
    )

    assert promotion["schema"] == "roboclaws_eval_regression_promotion_v1"
    assert promotion["source"]["failure_class"] == "artifact_missing"
    sample = json.loads(sample_output.read_text())
    assert sample["sample_id"] == "regression.cleanup_missing_report"
    assert sample["trial_count"] == 1
    assert sample["private_goal_reference"]["private_truth_scope"] == "grader_only"
    regression = sample["private_goal_reference"]["regression_promotion"]
    assert regression["review_label"] == "eval-regression:accepted"
    assert regression["source_failure_class"] == "artifact_missing"
    assert regression["agent_input_policy"] == "do_not_expose_private_goal_reference"
    assert "run_result" in regression["source_artifacts"]
    suite = json.loads(suite_output.read_text())
    assert "regression.cleanup_missing_report" in suite["sample_ids"]
    assert str(sample_output) in suite["sample_refs"]
    assert suite["metadata"]["regression_sample_count"] == 1
    assert suite["metadata"]["regression_promotions"][0]["private_truth_scope"] == "grader_only"


def test_regression_promotion_rejects_passed_results(tmp_path: Path) -> None:
    run = run_eval_suite(
        "smoke_regression",
        output_root=tmp_path,
        stamp="passed",
        product_runner=_passing_product_runner,
    )

    with pytest.raises(ValueError, match="no failed, blocked, or inconclusive"):
        promote_regression_sample_from_eval_result(run.results_path)


def test_regression_promotion_stop_label_does_not_write_outputs(tmp_path: Path) -> None:
    run = run_eval_suite(
        "smoke_regression",
        output_root=tmp_path,
        stamp="artifact-failure",
        product_runner=_missing_artifact_product_runner,
    )
    sample_output = tmp_path / "samples" / "should_not_exist.json"
    suite_output = tmp_path / "suites" / "should_not_exist.json"

    with pytest.raises(ValueError, match="cannot write a sample"):
        promote_regression_from_cli_overrides(
            {
                "eval_results": str(run.results_path),
                "review_label": "eval-regression:do-not-promote",
                "sample_output_path": str(sample_output),
                "suite_output_path": str(suite_output),
            }
        )

    assert not sample_output.exists()
    assert not suite_output.exists()


def _passing_product_runner(**kwargs: Any) -> dict[str, Any]:
    run_dir = Path(kwargs["output_dir"])
    _write_product_artifacts(run_dir, completion_status="success")
    return _run_result(run_dir, completion_status="success")


def _missing_artifact_product_runner(**kwargs: Any) -> dict[str, Any]:
    run_dir = Path(kwargs["output_dir"])
    _write_product_artifacts(run_dir, completion_status="success")
    (run_dir / "report.html").unlink()
    return _run_result(run_dir, completion_status="success")


def _blocked_product_runner(**kwargs: Any) -> dict[str, Any]:
    raise ModuleNotFoundError("No module named 'molmospaces'")


def _live_surface_kwargs(run_dir: Path, *, live_timeout_s: float | None = None) -> dict[str, Any]:
    return {
        "output_dir": run_dir,
        "seed": 7,
        "task_prompt": "帮我收拾这个房间",
        "backend": "api_semantic_synthetic",
        "cleanup_profile": "smoke",
        "scene_source": "procthor-10k-val",
        "scene_index": 0,
        "agent_engine": "codex-cli",
        "provider_profile": "codex-env",
        "model": None,
        "live_timeout_s": live_timeout_s,
    }


def _completed_process(*, returncode: int, stdout: str = "", stderr: str = "") -> Any:
    return type(
        "Completed",
        (),
        {
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        },
    )()


def _write_product_artifacts(
    run_dir: Path,
    *,
    completion_status: str,
    include_goal_contract: bool = False,
    generated_exploration_candidate_count: int = 1,
    include_open_ended_public_evidence: bool = True,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_result.json").write_text("{}\n")
    (run_dir / "report.html").write_text("<html>report</html>\n")
    (run_dir / "agent_view.json").write_text("{}\n")
    public_anchors = [{"anchor_id": "anchor_fridge"}]
    generated_candidates = [
        {"waypoint_id": f"generated_exploration_{index:03d}"}
        for index in range(1, generated_exploration_candidate_count + 1)
    ]
    target_search_summary: dict[str, Any] = {}
    if include_open_ended_public_evidence:
        public_anchors.extend(
            [
                {
                    "anchor_id": "anchor_room_kitchen",
                    "anchor_type": "room_area",
                    "room_id": "kitchen",
                    "waypoint_id": "generated_exploration_003",
                    "evidence": {"visited": True},
                },
                {
                    "anchor_id": "anchor_room_living_area",
                    "anchor_type": "room_area",
                    "room_id": "living_area",
                    "waypoint_id": "generated_exploration_005",
                    "evidence": {"visited": True},
                },
                {
                    "anchor_id": "anchor_waypoint_generated_exploration_005",
                    "anchor_type": "observation_waypoint",
                    "room_id": "room_4",
                    "waypoint_id": "generated_exploration_005",
                    "evidence": {"visited": True},
                },
            ]
        )
        generated_candidates.extend(
            [
                {
                    "waypoint_id": "generated_exploration_003",
                    "room_id": "kitchen",
                    "visited": True,
                },
                {
                    "waypoint_id": "generated_exploration_005",
                    "room_id": "room_4",
                    "visited": True,
                },
            ]
        )
        target_search_summary = {
            "viewpoint_budget": {
                "observed_waypoint_ids": [
                    "generated_exploration_003",
                    "generated_exploration_005",
                ],
            },
            "inspection_observations": [
                {"room_id": "kitchen", "waypoint_id": "generated_exploration_003"},
                {"room_id": "room_4", "waypoint_id": "generated_exploration_005"},
            ],
        }
    (run_dir / "runtime_metric_map.json").write_text(
        json.dumps(
            {
                "schema": "runtime_metric_map_v1",
                "public_semantic_anchors": public_anchors,
                "generated_exploration_candidates": generated_candidates,
                "target_search_summary": target_search_summary,
                "private_truth_included": False,
                "source_map_mutated": False,
            }
        )
        + "\n"
    )
    (run_dir / "private_evaluation.json").write_text("{}\n")
    (run_dir / "advisory_evaluation.json").write_text('{"authoritative": false}\n')
    if include_goal_contract:
        (run_dir / "goal_contract.json").write_text('{"intent": "open-ended"}\n')
    (run_dir / "trace.jsonl").write_text(
        "\n".join(
            [
                '{"event": "request", "tool": "metric_map"}',
                '{"event": "response", "tool": "metric_map"}',
                (
                    '{"event": "request", "tool": "navigate_to_waypoint", '
                    '"request": {"waypoint_id": "generated_exploration_005"}}'
                ),
                '{"event": "response", "tool": "done"}',
            ]
        )
        + "\n"
    )


def _run_result(
    run_dir: Path,
    *,
    completion_status: str,
    semantic_sweep: bool = False,
    task_intent: str = "cleanup",
    final_status: str | None = None,
    include_completion_claim: bool = False,
    include_runtime_map: bool = True,
    wall_time_s: float | None = None,
) -> dict[str, Any]:
    completion_claim = (
        {
            "schema": "roboclaws_agent_completion_claim_v1",
            "completion_summary": "direct runner declared task complete",
        }
        if include_completion_claim
        else {}
    )
    result = {
        "score": {
            "completion_status": completion_status,
            "mess_restoration_rate": 1.0,
            "disturbance_count": 0,
            "failed_or_noop_tool_count": 0,
        },
        "completion_status": completion_status,
        "cleanup_status": completion_status,
        "task_intent": task_intent,
        "final_status": final_status or completion_status,
        "semantic_sweep_mode": semantic_sweep,
        "agent_completion_claim": completion_claim,
        "tool_event_counts": {
            "metric_map:request": 1,
            "metric_map:response": 1,
            "done:response": 1,
        },
        "artifacts": {
            "run_result": str(run_dir / "run_result.json"),
            "report": str(run_dir / "report.html"),
        },
        "runtime_metric_map": (
            json.loads((run_dir / "runtime_metric_map.json").read_text())
            if include_runtime_map and (run_dir / "runtime_metric_map.json").exists()
            else {}
        ),
        "advisory_evaluation": json.loads((run_dir / "advisory_evaluation.json").read_text()),
        "policy_uses_private_truth": False,
        "planner_uses_private_manifest": False,
        "agent_view": {},
    }
    if wall_time_s is not None:
        result["wall_time_s"] = wall_time_s
    return result
