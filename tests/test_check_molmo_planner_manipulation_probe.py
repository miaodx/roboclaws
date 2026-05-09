from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from roboclaws.molmo_cleanup.manipulation_provenance import (
    MANIPULATION_PROBE_CONTRACT,
    blocked_planner_probe_evidence,
    planner_backed_probe_evidence,
)
from roboclaws.molmo_cleanup.rby1m_curobo_gate import (
    rby1m_curobo_gate_from_planner_probe,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
CHECKER_PATH = REPO_ROOT / "scripts" / "check_molmo_planner_manipulation_probe.py"
RUNNER_PATH = REPO_ROOT / "scripts" / "run_molmo_planner_manipulation_probe.py"


def _load_checker_module():
    spec = importlib.util.spec_from_file_location(
        "check_molmo_planner_manipulation_probe", CHECKER_PATH
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_runner_module():
    spec = importlib.util.spec_from_file_location(
        "run_molmo_planner_manipulation_probe", RUNNER_PATH
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _write_report_files(
    tmp_path: Path,
    *,
    blocked: bool = False,
    diagnostics: bool = False,
    cleanup_binding: bool = False,
    rby1m_gate: bool = False,
    worker_stages: bool = False,
    curobo_cache: bool = False,
    warp_compatibility: bool = False,
    cuda_memory: bool = False,
    curobo_memory_profile: bool = False,
) -> dict[str, str]:
    stdout = tmp_path / "planner_probe_stdout.txt"
    stderr = tmp_path / "planner_probe_stderr.txt"
    report = tmp_path / "report.html"
    stdout.write_text("{}", encoding="utf-8")
    stderr.write_text("", encoding="utf-8")
    body = "Planner-Backed Manipulation Probe\nManipulation Provenance\n"
    if blocked:
        body += "Capability Blockers\n"
    if diagnostics:
        body += "Runtime Diagnostics\n"
    if cleanup_binding:
        body += "Planner Probe Cleanup Binding\n"
    if worker_stages:
        body += "Worker Stage Timeline\n"
    if curobo_cache:
        body += "CuRobo Extension Cache\n"
    if warp_compatibility:
        body += "Warp Compatibility\n"
    if cuda_memory:
        body += "CUDA Memory Headroom\n"
    if curobo_memory_profile:
        body += "CuRobo Memory Profile\n"
    if rby1m_gate:
        body += "RBY1M CuRobo Gate\n"
    report.write_text(body, encoding="utf-8")
    return {"stdout": str(stdout), "stderr": str(stderr), "report": str(report)}


def test_runner_preserves_last_worker_stage_from_timeout_stdout() -> None:
    runner = _load_runner_module()
    stdout = "\n".join(
        [
            '{"elapsed_s": 0.01, "event": "worker_start", "stage": "worker_start"}',
            (
                '{"elapsed_s": 0.02, "event": "runtime_diagnostics", '
                '"stage": "runtime_diagnostics", "runtime_diagnostics": '
                '{"modules": {"curobo": {"available": true}}}}'
            ),
            (
                '{"elapsed_s": 0.03, "event": "rby1m_config_import_start", '
                '"stage": "rby1m_config_import"}'
            ),
        ]
    )

    payload = runner._worker_payload_from_stdout(stdout)

    assert payload["last_worker_stage"] == "rby1m_config_import"
    assert payload["runtime_diagnostics"]["modules"]["curobo"]["available"] is True
    assert [item["event"] for item in payload["worker_stage_events"]] == [
        "worker_start",
        "runtime_diagnostics",
        "rby1m_config_import_start",
    ]


def test_runner_configures_exact_cleanup_task_scene_and_aliases(tmp_path: Path) -> None:
    runner = _load_runner_module()
    scene_xml = tmp_path / "scene.xml"
    scene_xml.write_text("<mujoco/>", encoding="utf-8")
    config = SimpleNamespace(
        scene_dataset="procthor-10k",
        data_split="train",
        task_sampler_config=SimpleNamespace(
            house_inds=[8],
            samples_per_house=20,
            max_tasks=10,
            pickup_obj_name=None,
            place_target_name=None,
        ),
        task_config=SimpleNamespace(
            pickup_obj_name=None,
            place_receptacle_name=None,
            place_target_name=None,
        ),
        task_config_preset_exp="stale",
        task_config_preset_scn="stale",
    )
    args = SimpleNamespace(
        cleanup_scene_xml=str(scene_xml),
        cleanup_object_id="observed_001",
        cleanup_target_receptacle_id="sink_01",
        cleanup_source_receptacle_id="counter_01",
        cleanup_planner_object_id="pickup/body",
        cleanup_planner_target_receptacle_id="sink/body",
        cleanup_tools="pick,place",
    )

    result = runner._configure_exact_cleanup_task(config, args)

    assert result["applied"] is True
    assert config.scene_dataset == str(scene_xml)
    assert config.data_split == "val"
    assert config.task_sampler_config.house_inds == [0]
    assert config.task_sampler_config.max_tasks == 1
    assert config.task_config.pickup_obj_name == "pickup/body"
    assert config.task_config.place_receptacle_name == "sink/body"
    assert config.task_config_preset_exp is None
    assert config.task_config_preset_scn is None


def test_runner_exact_cleanup_task_sampler_adapter_forces_target() -> None:
    runner = _load_runner_module()

    class FakeObjectManager:
        def get_object_by_name(self, name: str) -> object:
            assert name == "sink/body"
            return object()

    class FakeSampler:
        place_receptacle_name = None

        def _get_place_target_candidates(self, env, pickup_obj_name, supporting_geom_id):
            return ["random/target"]

        def _prepare_place_target(
            self,
            env,
            place_target_name,
            pickup_obj_name,
            pickup_obj_pos,
            supporting_geom_id,
        ):
            return False

    sampler = FakeSampler()
    env = SimpleNamespace(current_batch_index=0, object_managers=[FakeObjectManager()])

    result = runner._apply_exact_cleanup_task_sampler_adapter(
        sampler,
        {
            "planner_target_receptacle_id": "sink/body",
            "target_receptacle_id": "sink_01",
        },
    )

    assert result["applied"] is True
    assert sampler._get_place_target_candidates(env, "pickup/body", 1) == ["sink/body"]
    assert sampler._prepare_place_target(env, "ignored", "pickup/body", None, 1) is True
    assert sampler.place_receptacle_name == "sink/body"


def test_runner_worker_exception_context_preserves_sampler_adapter(tmp_path: Path) -> None:
    runner = _load_runner_module()
    args = SimpleNamespace(
        cleanup_scene_xml=str(tmp_path / "scene.xml"),
        cleanup_object_id="observed_001",
        cleanup_target_receptacle_id="sink_01",
        cleanup_source_receptacle_id="counter_01",
        cleanup_planner_object_id="pickup/body",
        cleanup_planner_target_receptacle_id="sink/body",
        cleanup_tools="navigate_to_object,pick,navigate_to_receptacle,place",
    )
    cleanup_task_config = {
        "schema": "planner_probe_exact_cleanup_task_config_v1",
        "applied": True,
        "scene_xml": str(tmp_path / "scene.xml"),
        "planner_object_id": "pickup/body",
        "planner_target_receptacle_id": "sink/body",
    }
    sampler_adapter = {
        "schema": "planner_probe_exact_cleanup_task_sampler_adapter_v1",
        "applied": True,
        "task_sampler_class": "FakeSampler",
        "planner_target_receptacle_id": "sink/body",
    }

    runner._WORKER_EXCEPTION_CONTEXT.clear()
    runner._record_worker_exception_context(
        cleanup_task_config=cleanup_task_config,
        cleanup_task_sampler_adapter=sampler_adapter,
        requested_cleanup_primitive_binding={
            "requested": True,
            "planner_object_id": "pickup/body",
            "planner_target_receptacle_id": "sink/body",
        },
    )
    context = runner._worker_exception_probe_context(args)

    assert context["cleanup_task_config"] == cleanup_task_config
    assert context["cleanup_task_sampler_adapter"] == sampler_adapter
    assert context["requested_cleanup_primitive_binding"]["planner_target_receptacle_id"] == (
        "sink/body"
    )


def test_checker_accepts_blocked_capability_only_when_explicit(tmp_path: Path) -> None:
    checker = _load_checker_module()
    evidence = blocked_planner_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="franka",
        task="pick_and_place",
        probe_mode="config_import",
        blockers=[{"code": "execution_not_attempted", "message": "not attempted"}],
    )
    evidence["runtime_diagnostics"] = {
        "python_version": "3.11.8",
        "modules": {"curobo": {"available": False, "version": None}},
    }
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(tmp_path, blocked=True, diagnostics=True),
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


def test_checker_requires_cleanup_binding_report_when_evidence_exists(tmp_path: Path) -> None:
    checker = _load_checker_module()
    evidence = planner_backed_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="rby1m",
        task="pick_and_place",
        probe_mode="execute",
        upstream_policy_class="CuroboPickAndPlacePlannerPolicy",
        steps_requested=2,
        steps_executed=2,
        max_abs_qpos_delta=0.01,
    )
    evidence["sampled_task_binding"] = {
        "schema": "planner_probe_sampled_task_binding_v1",
        "pickup_obj_name": "pickup/body",
        "place_receptacle_name": "sink/body",
    }
    evidence["cleanup_primitive_binding"] = {
        "schema": "planner_probe_cleanup_primitive_binding_v1",
        "object_id": "pickup/body",
        "target_receptacle_id": "sink/body",
        "tools": ["pick", "place"],
    }
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "planner_backed",
        "primitive_provenance": "planner_backed",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(tmp_path),
    }

    with pytest.raises(AssertionError):
        checker._assert_probe_result(data, tmp_path, require_planner_backed=True)

    data["artifacts"] = _write_report_files(tmp_path, cleanup_binding=True)
    checker._assert_probe_result(data, tmp_path, require_planner_backed=True)


def test_checker_accepts_rby1m_curobo_blocked_gate(tmp_path: Path) -> None:
    checker = _load_checker_module()
    evidence = blocked_planner_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="rby1m",
        task="pick_and_place",
        probe_mode="config_import",
        blockers=[{"code": "ModuleNotFoundError", "message": "No module named 'curobo'"}],
    )
    evidence["runtime_diagnostics"] = {
        "modules": {"curobo": {"available": False, "version": None}},
    }
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(
            tmp_path,
            blocked=True,
            diagnostics=True,
            rby1m_gate=True,
        ),
    }
    data["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(data)

    checker._assert_probe_result(
        data,
        tmp_path,
        accept_blocked_capability=True,
        accept_rby1m_curobo_blocked=True,
    )
    with pytest.raises(AssertionError):
        checker._assert_probe_result(
            data,
            tmp_path,
            accept_blocked_capability=True,
            require_rby1m_curobo_ready=True,
        )


def test_checker_requires_worker_stage_report_when_stage_events_exist(
    tmp_path: Path,
) -> None:
    checker = _load_checker_module()
    evidence = blocked_planner_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="rby1m",
        task="pick_and_place",
        probe_mode="config_import",
        blockers=[{"code": "timeout", "message": "Probe exceeded 300.0s"}],
    )
    evidence["runtime_diagnostics"] = {
        "modules": {"curobo": {"available": True, "version": None}},
    }
    evidence["worker_stage_events"] = [
        {"event": "worker_start", "stage": "worker_start", "elapsed_s": 0.01},
        {
            "event": "rby1m_config_import_start",
            "stage": "rby1m_config_import",
            "elapsed_s": 0.02,
        },
    ]
    evidence["last_worker_stage"] = "rby1m_config_import"
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(
            tmp_path,
            blocked=True,
            diagnostics=True,
            rby1m_gate=True,
            worker_stages=True,
        ),
    }
    data["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(data)

    checker._assert_probe_result(
        data,
        tmp_path,
        accept_blocked_capability=True,
        accept_rby1m_curobo_blocked=True,
    )
    data["artifacts"] = _write_report_files(
        tmp_path,
        blocked=True,
        diagnostics=True,
        rby1m_gate=True,
        worker_stages=False,
    )
    with pytest.raises(AssertionError):
        checker._assert_probe_result(
            data,
            tmp_path,
            accept_blocked_capability=True,
            accept_rby1m_curobo_blocked=True,
        )


def test_checker_requires_curobo_extension_cache_report_when_requested(
    tmp_path: Path,
) -> None:
    checker = _load_checker_module()
    evidence = blocked_planner_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="rby1m",
        task="pick_and_place",
        probe_mode="config_import",
        blockers=[{"code": "timeout", "message": "Probe exceeded 300.0s"}],
    )
    evidence["runtime_diagnostics"] = {
        "curobo_extension_cache": {
            "configured_dir": str(tmp_path / "torch_extensions"),
            "extensions": {
                "lbfgs_step_cu": {
                    "build_dir": str(tmp_path / "torch_extensions" / "lbfgs_step_cu"),
                    "so_exists": False,
                    "lock_exists": True,
                    "files": [{"name": "lock", "size_bytes": 0}],
                }
            },
        }
    }
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(
            tmp_path,
            blocked=True,
            diagnostics=True,
            rby1m_gate=True,
            curobo_cache=True,
        ),
    }
    data["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(data)

    checker._assert_probe_result(
        data,
        tmp_path,
        accept_blocked_capability=True,
        accept_rby1m_curobo_blocked=True,
        require_curobo_extension_cache=True,
    )
    data["artifacts"] = _write_report_files(
        tmp_path,
        blocked=True,
        diagnostics=True,
        rby1m_gate=True,
        curobo_cache=False,
    )
    with pytest.raises(AssertionError):
        checker._assert_probe_result(
            data,
            tmp_path,
            accept_blocked_capability=True,
            accept_rby1m_curobo_blocked=True,
            require_curobo_extension_cache=True,
        )


def test_checker_requires_warp_compatibility_report_when_requested(
    tmp_path: Path,
) -> None:
    checker = _load_checker_module()
    evidence = blocked_planner_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="rby1m",
        task="pick_and_place",
        probe_mode="execute",
        blockers=[{"code": "AttributeError", "message": "module warp has no torch"}],
        execution_attempted=True,
    )
    evidence["runtime_diagnostics"] = {
        "warp_compatibility": {
            "available": True,
            "version": "1.13.0",
            "has_torch_attr": True,
            "has_device_from_torch": True,
            "adapter": {
                "applied": True,
                "provided": ["warp.torch.device_from_torch"],
            },
        }
    }
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(
            tmp_path,
            blocked=True,
            diagnostics=True,
            rby1m_gate=True,
            warp_compatibility=True,
        ),
    }
    data["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(data)

    checker._assert_probe_result(
        data,
        tmp_path,
        accept_blocked_capability=True,
        accept_rby1m_curobo_blocked=True,
        require_warp_compatibility=True,
    )
    data["artifacts"] = _write_report_files(
        tmp_path,
        blocked=True,
        diagnostics=True,
        rby1m_gate=True,
        warp_compatibility=False,
    )
    with pytest.raises(AssertionError):
        checker._assert_probe_result(
            data,
            tmp_path,
            accept_blocked_capability=True,
            accept_rby1m_curobo_blocked=True,
            require_warp_compatibility=True,
        )


def test_checker_requires_cuda_memory_report_when_requested(tmp_path: Path) -> None:
    checker = _load_checker_module()
    evidence = blocked_planner_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="rby1m",
        task="pick_and_place",
        probe_mode="execute",
        blockers=[{"code": "OutOfMemoryError", "message": "CUDA out of memory"}],
        execution_attempted=True,
    )
    evidence["runtime_diagnostics"] = {
        "cuda_memory": {
            "available": True,
            "device_count": 1,
            "current_device_index": 0,
            "current_snapshot": {
                "stage": "runtime_diagnostics",
                "device_index": 0,
                "device_name": "Fake GPU",
                "free_bytes": 268435456,
                "total_bytes": 1073741824,
                "torch_allocated_bytes": 536870912,
                "torch_reserved_bytes": 805306368,
            },
        }
    }
    evidence["cuda_memory_snapshots"] = [
        {
            "stage": "execute_policy_run_start",
            "device_index": 0,
            "device_name": "Fake GPU",
            "free_bytes": 268435456,
            "total_bytes": 1073741824,
            "torch_allocated_bytes": 536870912,
            "torch_reserved_bytes": 805306368,
        }
    ]
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(
            tmp_path,
            blocked=True,
            diagnostics=True,
            rby1m_gate=True,
            cuda_memory=True,
        ),
    }
    data["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(data)

    checker._assert_probe_result(
        data,
        tmp_path,
        accept_blocked_capability=True,
        accept_rby1m_curobo_blocked=True,
        require_cuda_memory=True,
    )
    data["artifacts"] = _write_report_files(
        tmp_path,
        blocked=True,
        diagnostics=True,
        rby1m_gate=True,
        cuda_memory=False,
    )
    with pytest.raises(AssertionError):
        checker._assert_probe_result(
            data,
            tmp_path,
            accept_blocked_capability=True,
            accept_rby1m_curobo_blocked=True,
            require_cuda_memory=True,
        )


def test_checker_requires_curobo_memory_profile_report_when_requested(
    tmp_path: Path,
) -> None:
    checker = _load_checker_module()
    evidence = blocked_planner_probe_evidence(
        backend="molmospaces_subprocess",
        embodiment="rby1m",
        task="pick_and_place",
        probe_mode="execute",
        blockers=[{"code": "OutOfMemoryError", "message": "CUDA out of memory"}],
        execution_attempted=True,
    )
    evidence["curobo_memory_profile"] = {
        "profile": "low",
        "applied": True,
        "after": {
            "policy": {
                "batch_size": 1,
                "max_batch_plan_attempts": 1,
                "enable_collision_avoidance": True,
            },
            "planners": {
                "left": {
                    "num_trajopt_seeds": 1,
                    "num_ik_seeds": 16,
                    "max_attempts": 1,
                    "trajopt_tsteps": 24,
                    "enable_finetune_trajopt": False,
                }
            },
        },
    }
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "blocked_capability",
        "primitive_provenance": "blocked_capability",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(
            tmp_path,
            blocked=True,
            rby1m_gate=True,
            curobo_memory_profile=True,
        ),
    }
    data["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(data)

    checker._assert_probe_result(
        data,
        tmp_path,
        accept_blocked_capability=True,
        accept_rby1m_curobo_blocked=True,
        require_curobo_memory_profile=True,
    )
    data["artifacts"] = _write_report_files(
        tmp_path,
        blocked=True,
        rby1m_gate=True,
        curobo_memory_profile=False,
    )
    with pytest.raises(AssertionError):
        checker._assert_probe_result(
            data,
            tmp_path,
            accept_blocked_capability=True,
            accept_rby1m_curobo_blocked=True,
            require_curobo_memory_profile=True,
        )


def test_checker_rejects_franka_as_rby1m_curobo_ready(tmp_path: Path) -> None:
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
    evidence["runtime_diagnostics"] = {
        "modules": {"curobo": {"available": True, "version": "1.0.0"}},
    }
    data = {
        "contract": MANIPULATION_PROBE_CONTRACT,
        "status": "planner_backed",
        "primitive_provenance": "planner_backed",
        "manipulation_evidence": evidence,
        "artifacts": _write_report_files(tmp_path, diagnostics=True, rby1m_gate=True),
    }
    data["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(data)

    with pytest.raises(AssertionError):
        checker._assert_probe_result(
            data,
            tmp_path,
            require_planner_backed=True,
            require_rby1m_curobo_ready=True,
        )
