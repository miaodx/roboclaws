from __future__ import annotations

import json
import threading
import time
from argparse import Namespace
from pathlib import Path

from pytest import MonkeyPatch

from scripts.molmo_cleanup import run_codex_cleanup_harness8 as harness8


def test_build_harness_has_expected_rows(tmp_path: Path) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )

    assert harness["schema"] == "codex_cleanup_harness8_v1"
    assert [row["row_id"] for row in harness["setup_rows"]] == ["setup-semantic-map-prior-dino"]
    assert [row["row_id"] for row in harness["rows"]] == [
        "direct-world-oracle-labels",
        "direct-world-public-labels",
        "direct-camera-grounded-labels-grounding-dino",
        "direct-camera-raw-fpv",
        "dino-prior-world-oracle-labels",
        "dino-prior-world-public-labels",
        "dino-prior-camera-grounded-labels-grounding-dino",
        "dino-prior-camera-raw-fpv",
    ]
    prior_rows = [row for row in harness["rows"] if row["axes"]["map_mode"] == "dino-prior"]
    assert len(prior_rows) == 4
    assert all(row["requires_runtime_map_prior"] for row in prior_rows)


def test_cleanup_rows_do_not_set_runner_continuation_env(tmp_path: Path) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="output/prior/runtime_metric_map.json",
        visual_grounding_timeout_s="auto",
    )

    rows = {row["row_id"]: row for row in harness["rows"]}
    assert rows["dino-prior-camera-grounded-labels-grounding-dino"]["env"] == {}
    assert rows["dino-prior-camera-raw-fpv"]["env"] == {}
    assert rows["direct-camera-grounded-labels-grounding-dino"]["env"] == {}
    assert rows["dino-prior-world-oracle-labels"]["env"] == {}
    assert (
        "ROBOCLAWS_CODEX_MAX_CONTINUATIONS"
        not in rows["dino-prior-camera-grounded-labels-grounding-dino"]["rerun_command"]
    )


def test_configure_parallelism_assigns_distinct_ports_and_batch_env(tmp_path: Path) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )

    harness8._configure_harness_parallelism(harness, parallelism=2, base_port=18788)

    setup = harness["setup_rows"][0]
    rows = {row["row_id"]: row for row in harness["rows"]}
    assert setup["assigned_port"] == 18788
    assert setup["harness_parallelism"] == 1
    assert rows["direct-world-oracle-labels"]["assigned_port"] == 18788
    assert rows["direct-world-public-labels"]["assigned_port"] == 18790
    assert (
        rows["direct-world-oracle-labels"]["env"]["ROBOCLAWS_MOLMO_ALLOW_BATCH_VISUAL_BACKENDS"]
        == "1"
    )
    assert rows["direct-world-public-labels"]["env"]["ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS"] == "2"


def test_execute_cleanup_rows_uses_bounded_parallelism(monkeypatch: MonkeyPatch) -> None:
    rows = [
        {"row_id": "row-a"},
        {"row_id": "row-b"},
        {"row_id": "row-c"},
    ]
    active = 0
    peak_active = 0
    lock = threading.Lock()
    started: list[str] = []

    def fake_execute(row, _args):
        nonlocal active, peak_active
        with lock:
            started.append(row["row_id"])
            active += 1
            peak_active = max(peak_active, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return 0

    monkeypatch.setattr(harness8, "_execute_row_with_retries", fake_execute)

    failure_count = harness8._execute_cleanup_rows(
        rows,
        Namespace(parallelism=2, continue_on_error=True),
    )

    assert failure_count == 0
    assert peak_active == 2
    assert set(started) == {"row-a", "row-b", "row-c"}


def test_replace_runtime_map_prior_updates_prior_rows_only(tmp_path: Path) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )

    harness8._replace_runtime_map_prior(harness, "output/prior/runtime_metric_map.json")

    direct_rows = [row for row in harness["rows"] if row["axes"]["map_mode"] == "direct"]
    prior_rows = [row for row in harness["rows"] if row["axes"]["map_mode"] == "dino-prior"]
    assert all("runtime_map_prior=" not in " ".join(row["command"]) for row in direct_rows)
    assert all(
        "runtime_map_prior=output/prior/runtime_metric_map.json" in row["command"]
        for row in prior_rows
    )


def test_setup_row_refresh_treats_runtime_map_as_artifact_success(tmp_path: Path) -> None:
    run_dir = tmp_path / "_semantic-map-prior-dino" / "0603_2209" / "seed-7"
    run_dir.mkdir(parents=True)
    (run_dir / "runtime_metric_map.json").write_text(
        json.dumps({"public_semantic_anchors": [{"id": "anchor_fixture_001"}]}),
        encoding="utf-8",
    )
    (run_dir / "report.html").write_text("<html></html>", encoding="utf-8")
    (run_dir / "run_result.json").write_text(
        json.dumps(
            {
                "completion_status": "failed",
                "score": {"status": "failed", "restored_count": 0, "total_targets": 10},
                "runtime_metric_map": {"public_semantic_anchors": [{"id": "anchor_fixture_001"}]},
                "sweep_coverage_rate": 1.0,
                "disturbance_count": 0,
                "visual_grounding_pipeline_id": "grounding-dino",
            }
        ),
        encoding="utf-8",
    )

    row = harness8._semantic_map_prior_row(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        visual_grounding_timeout_s="auto",
    )
    harness8._refresh_row_from_evidence(row, status=0, run_dir=run_dir)

    assert row["status"] == "artifact_success"
    assert row["behavior_status"] == "artifact_success"
    assert row["metrics"]["runtime_semantic_anchor_count"] == 1
    assert "exact_restored" not in row["metrics"]


def test_provider_transient_evidence_reads_explicit_live_status() -> None:
    live_status = {
        "phase": "failed",
        "exit_status": 1,
        "reason": "provider_transient_failure",
        "provider_reason": "rate_limit",
        "retryable": True,
        "resume_available": True,
    }

    evidence = harness8._provider_transient_evidence({"live_status": live_status})

    assert evidence is not None
    assert evidence["provider_reason"] == "rate_limit"
    assert evidence["source"] == "live_status.json"


def test_provider_transient_evidence_ignores_matching_log_without_live_status(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "seed-7"
    run_dir.mkdir()
    (run_dir / "driver.log").write_text(
        '{"type":"error","message":"exceeded retry limit, last status: 429 Too Many Requests"}',
        encoding="utf-8",
    )

    assert harness8._provider_transient_evidence({"run_dir": str(run_dir)}) is None


def test_execute_row_with_retries_marks_exhausted_provider_transient(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    row = {"row_id": "dino-prior-world-oracle-labels", "run_dir": str(tmp_path)}

    def fake_execute_row(row_arg, _args):
        row_arg["run_dir"] = str(tmp_path)
        row_arg["status"] = "failed"
        row_arg["behavior_status"] = "failed"
        row_arg["reason"] = "command exited with status 1"
        return 1

    monkeypatch.setattr(harness8, "_execute_row", fake_execute_row)
    monkeypatch.setattr(
        harness8,
        "_provider_transient_evidence",
        lambda _row: {
            "source": "live_status.json",
            "provider_reason": "rate_limit",
            "retryable": True,
            "resume_available": True,
        },
    )

    status = harness8._execute_row_with_retries(
        row,
        Namespace(provider_retry_attempts=1, provider_retry_sleep_s=0),
    )

    assert status == 1
    assert row["status"] == "provider_transient_failed"
    assert row["behavior_status"] == "infra_failure"
    assert row["provider_reason"] == "rate_limit"
    assert row["retryable"] is True
    assert row["resume_available"] is True
    assert row["retry_count"] == 1
    assert len(row["attempts"]) == 2


def test_execute_row_does_not_apply_operator_codex_continuation_env(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    run_dir = tmp_path / "dino-prior-camera-grounded-labels-grounding-dino" / "0604_1030" / "seed-7"
    run_dir.mkdir(parents=True)
    (run_dir / "live_status.json").write_text(
        json.dumps({"phase": "finished", "exit_status": 0}),
        encoding="utf-8",
    )
    captured_envs: list[dict[str, str]] = []

    class Completed:
        returncode = 0

    def fake_run(_command, *, env, check):
        captured_envs.append(dict(env))
        return Completed()

    monkeypatch.setattr(harness8.subprocess, "run", fake_run)
    monkeypatch.setattr(harness8, "_latest_seed_dir", lambda *_args, **_kwargs: run_dir)

    row = {
        "row_id": "dino-prior-camera-grounded-labels-grounding-dino",
        "grid_role": "cleanup",
        "command": [
            "just",
            "run::surface",
            "surface=household-world",
            "world=molmospaces/val_0",
            "backend=mujoco",
            "intent=cleanup",
            "agent_engine=codex-cli",
            "provider_profile=codex-env",
            "evidence_lane=camera-grounded-labels",
        ],
        "output_dir": str(tmp_path / "dino-prior-camera-grounded-labels-grounding-dino"),
        "env": {},
    }
    status = harness8._execute_row(
        row,
        Namespace(
            just_bin="just",
            seed=7,
            live_wait_timeout_s=1,
            live_wait_poll_s=0.1,
        ),
    )

    assert status == 0
    assert "ROBOCLAWS_CODEX_MAX_CONTINUATIONS" not in captured_envs[0]


def test_visual_grounding_connection_error_is_infra_failure(tmp_path: Path) -> None:
    run_dir = tmp_path / "seed-7"
    run_dir.mkdir()
    (run_dir / "report.html").write_text("<html></html>", encoding="utf-8")
    (run_dir / "run_result.json").write_text(
        json.dumps(
            {
                "completion_status": "failed",
                "score": {"status": "failed", "restored_count": 0, "total_targets": 10},
                "sweep_coverage_rate": 1.0,
                "disturbance_count": 0,
                "trace": [
                    {
                        "visual_grounding_pipeline": {
                            "pipeline_id": "grounding-dino",
                            "status": "failed",
                            "failure_reason": "connection_error",
                            "failure_message": "<urlopen error [Errno 111] Connection refused>",
                            "candidate_count": 0,
                        }
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    row = harness8._cleanup_row(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        map_mode=harness8.PRIOR_MAP_MODE,
        lane={
            "lane_id": "camera-grounded-labels-grounding-dino",
            "label": "Grounding DINO camera labels",
            "profile": "camera-grounded-labels",
            "camera_labeler": "grounding-dino",
        },
        runtime_map_prior="output/prior/runtime_metric_map.json",
        visual_grounding_timeout_s="auto",
    )
    harness8._refresh_row_from_evidence(row, status=1, run_dir=run_dir)

    assert row["status"] == "infra_failed"
    assert row["behavior_status"] == "infra_failure"
    assert "grounding-dino visual grounding infra failure" in row["reason"]


def test_prior_setup_provider_transient_blocks_prior_rows(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )
    selected = [row for row in harness["rows"] if row["row_id"] == "dino-prior-world-oracle-labels"]

    executed_cleanup_rows: list[str] = []

    def fake_execute_row_with_retries(row_arg, _args):
        if row_arg["row_id"] == "setup-semantic-map-prior-dino":
            row_arg["status"] = "provider_transient_failed"
            row_arg["behavior_status"] = "infra_failure"
            row_arg["reason"] = "provider transient failure after 2 attempt(s): rate_limit"
            return 1
        executed_cleanup_rows.append(row_arg["row_id"])
        return 0

    monkeypatch.setattr(
        harness8,
        "_execute_row_with_retries",
        fake_execute_row_with_retries,
    )

    status = harness8._execute_harness(
        harness,
        Namespace(
            runtime_map_prior="",
            seed=7,
            provider_retry_attempts=1,
            provider_retry_sleep_s=0,
            continue_on_error=True,
            row=["dino-prior-world-oracle-labels"],
            dino_sidecar_lifecycle="off",
        ),
    )

    assert status == 1
    assert executed_cleanup_rows == []
    assert harness["setup_status"] == "provider_transient_failed"
    assert selected[0]["status"] == "blocked"
    assert selected[0]["behavior_status"] == "infra_failure"


def test_execute_harness_non_dino_row_does_not_probe_or_start_sidecar(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )
    probed = False
    executed: list[str] = []

    def fake_probe(_base_url: str):
        nonlocal probed
        probed = True
        return {"healthy": True}

    monkeypatch.setattr(harness8, "_probe_dino_sidecar", fake_probe)
    monkeypatch.setattr(
        harness8,
        "_execute_row_with_retries",
        lambda row, _args: executed.append(row["row_id"]) or 0,
    )

    status = harness8._execute_harness(
        harness,
        Namespace(
            runtime_map_prior="",
            seed=7,
            continue_on_error=True,
            row=["direct-world-oracle-labels"],
            dino_sidecar_lifecycle="auto",
            dino_sidecar_startup_timeout_s=1,
        ),
    )

    assert status == 0
    assert probed is False
    assert executed == ["direct-world-oracle-labels"]
    assert harness["dino_sidecar"]["status"] == "not_required"


def test_execute_harness_reuses_healthy_external_dino_sidecar(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )
    starts: list[tuple[str, int]] = []
    executed: list[str] = []

    monkeypatch.setattr(
        harness8,
        "_probe_dino_sidecar",
        lambda _base_url: {
            "healthy": True,
            "pipeline_id": "grounding-dino",
            "diagnostic_mode": "real_grounding_dino",
        },
    )
    monkeypatch.setattr(
        harness8._DinoSidecarForHarness,
        "_start_owned_sidecar",
        lambda _self, *, host, port: starts.append((host, port)),
    )
    monkeypatch.setattr(
        harness8,
        "_execute_row_with_retries",
        lambda row, _args: executed.append(row["row_id"]) or 0,
    )

    status = harness8._execute_harness(
        harness,
        Namespace(
            runtime_map_prior="",
            seed=7,
            continue_on_error=True,
            row=["direct-camera-grounded-labels-grounding-dino"],
            dino_sidecar_lifecycle="auto",
            dino_sidecar_startup_timeout_s=1,
        ),
    )

    assert status == 0
    assert starts == []
    assert executed == ["direct-camera-grounded-labels-grounding-dino"]
    assert harness["dino_sidecar"]["status"] == "reused"
    assert harness["dino_sidecar"]["owner"] == "external"
    assert harness["dino_sidecar"]["started_by_harness"] is False


def test_execute_harness_starts_and_stops_owned_dino_sidecar(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )
    lifecycle: list[str] = []

    class FakeProcess:
        pid = 12345
        returncode = None

        def poll(self):
            return self.returncode

        def terminate(self):
            lifecycle.append("terminate")
            self.returncode = -15

        def wait(self, timeout=None):
            lifecycle.append(f"wait:{timeout}")
            if self.returncode is None:
                self.returncode = 0
            return self.returncode

        def kill(self):
            lifecycle.append("kill")
            self.returncode = -9

    probes = [
        {"healthy": False, "reason": "connection_error"},
        {
            "healthy": True,
            "pipeline_id": "grounding-dino",
            "diagnostic_mode": "real_grounding_dino",
        },
    ]

    def fake_probe(_base_url: str):
        return probes.pop(0)

    def fake_popen(*_args, **_kwargs):
        lifecycle.append("start")
        return FakeProcess()

    monkeypatch.setattr(harness8, "_probe_dino_sidecar", fake_probe)
    monkeypatch.setattr(harness8, "_dino_sidecar_python_bin", lambda: Path("/bin/python"))
    monkeypatch.setattr(harness8, "_tcp_accepting", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(harness8.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(
        harness8,
        "_execute_row_with_retries",
        lambda _row, _args: 0,
    )

    status = harness8._execute_harness(
        harness,
        Namespace(
            output_dir=tmp_path,
            runtime_map_prior="",
            seed=7,
            continue_on_error=True,
            row=["direct-camera-grounded-labels-grounding-dino"],
            dino_sidecar_lifecycle="auto",
            dino_sidecar_startup_timeout_s=1,
        ),
    )

    assert status == 0
    assert lifecycle == ["start", "terminate", "wait:10"]
    assert harness["dino_sidecar"]["started_by_harness"] is True
    assert harness["dino_sidecar"]["status"] == "stopped"
    assert harness["dino_sidecar"]["stop_exit_status"] == -15


def test_execute_harness_blocks_dino_row_when_port_bound_by_wrong_service(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )
    executed: list[str] = []

    monkeypatch.setattr(
        harness8,
        "_probe_dino_sidecar",
        lambda _base_url: {
            "healthy": False,
            "pipeline_id": "fake-http",
            "reason": "sidecar did not report the real Grounding DINO adapter",
        },
    )
    monkeypatch.setattr(harness8, "_tcp_accepting", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        harness8,
        "_execute_row_with_retries",
        lambda row, _args: executed.append(row["row_id"]) or 0,
    )

    status = harness8._execute_harness(
        harness,
        Namespace(
            output_dir=tmp_path,
            runtime_map_prior="",
            seed=7,
            continue_on_error=True,
            row=["direct-camera-grounded-labels-grounding-dino"],
            dino_sidecar_lifecycle="auto",
            dino_sidecar_startup_timeout_s=1,
        ),
    )

    row = next(
        row
        for row in harness["rows"]
        if row["row_id"] == "direct-camera-grounded-labels-grounding-dino"
    )
    assert status == 1
    assert executed == []
    assert harness["dino_sidecar"]["status"] == "infra_failed"
    assert row["status"] == "infra_failed"
    assert row["behavior_status"] == "infra_failure"
    assert "not a healthy real Grounding DINO sidecar" in row["reason"]


def test_prior_rows_require_dino_setup_sidecar_only_without_explicit_prior(
    tmp_path: Path,
) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )
    prior_world_row = next(
        row for row in harness["rows"] if row["row_id"] == "dino-prior-world-oracle-labels"
    )

    required_without_prior = harness8._selected_rows_requiring_dino_sidecar(
        harness,
        [prior_world_row],
        explicit_runtime_map_prior="",
    )
    required_with_prior = harness8._selected_rows_requiring_dino_sidecar(
        harness,
        [prior_world_row],
        explicit_runtime_map_prior="output/prior/runtime_metric_map.json",
    )

    assert [row["row_id"] for row in required_without_prior] == [
        "setup-semantic-map-prior-dino",
        "dino-prior-world-oracle-labels",
    ]
    assert required_with_prior == []
