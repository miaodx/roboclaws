from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.semantic_timeline import SEMANTIC_SUBPHASE_LABELS

PLANNER_PROOF_REQUESTS_SCHEMA = "planner_cleanup_proof_requests_v1"
PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA = "planner_cleanup_proof_bundle_run_manifest_v1"
PLANNER_PROOF_RESULT_SUMMARY_SCHEMA = "planner_cleanup_proof_result_summary_v1"


def planner_proof_requests_from_substeps(
    *,
    contract: Any,
    substeps: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build private bound planner-proof requests from semantic cleanup substeps."""
    requests = []
    blockers = []
    for item in substeps:
        object_id = str(item.get("object_id") or "")
        target_receptacle_id = str(item.get("target_receptacle_id") or "")
        source_receptacle_id = str(item.get("source_receptacle_id") or "")
        tools = _cleanup_tools(item.get("steps") or [])
        binding = _planner_binding(
            contract=contract,
            object_id=object_id,
            target_receptacle_id=target_receptacle_id,
            source_receptacle_id=source_receptacle_id,
            tools=tools,
        )
        request = {
            "request_id": f"proof_{len(requests) + 1:03d}",
            "object_id": object_id,
            "target_receptacle_id": target_receptacle_id,
            "source_receptacle_id": source_receptacle_id,
            "tools": tools,
            "ready": bool(binding.get("ok")),
            "binding": binding,
            "planner_probe_args": dict(binding.get("planner_probe_args") or {}),
            "blockers": list(binding.get("blockers") or []),
        }
        if not request["ready"]:
            blockers.extend(_request_blockers(request))
        requests.append(request)
    ready_count = sum(1 for request in requests if request["ready"])
    return {
        "schema": PLANNER_PROOF_REQUESTS_SCHEMA,
        "request_count": len(requests),
        "ready_count": ready_count,
        "planner_scene": _planner_scene(contract),
        "requests": requests,
        "agent_view_exposed": False,
        "blockers": blockers,
        "evidence_note": (
            "Private planner proof requests derived from completed semantic cleanup "
            "substeps. Planner aliases are not part of Agent View."
        ),
    }


def write_planner_proof_requests(
    *,
    output_path: Path,
    contract: Any,
    substeps: list[dict[str, Any]],
) -> dict[str, Any]:
    manifest = planner_proof_requests_from_substeps(contract=contract, substeps=substeps)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def ready_planner_proof_requests(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    assert manifest.get("schema") == PLANNER_PROOF_REQUESTS_SCHEMA, manifest
    return [request for request in manifest.get("requests") or [] if request.get("ready")]


def build_probe_commands(
    *,
    manifest: dict[str, Any],
    output_dir: Path,
    runner_python: Path,
    probe_script: Path,
    molmospaces_python: Path | None = None,
    molmospaces_root: Path | None = None,
    embodiment: str = "rby1m",
    probe_mode: str = "execute",
    steps: int = 2,
    timeout_s: float = 600.0,
    renderer_device_id: int = 0,
    torch_extensions_dir: Path | None = None,
    rby1m_curobo_memory_profile: str = "low",
) -> list[dict[str, Any]]:
    commands = []
    for index, request in enumerate(ready_planner_proof_requests(manifest), start=1):
        proof_dir = output_dir / "proofs" / _proof_dir_name(index, request)
        command = [
            str(runner_python),
            str(probe_script),
            "--output-dir",
            str(proof_dir),
            "--embodiment",
            embodiment,
            "--probe-mode",
            probe_mode,
            "--renderer-device-id",
            str(renderer_device_id),
            "--rby1m-curobo-memory-profile",
            rby1m_curobo_memory_profile,
            "--steps",
            str(steps),
            "--timeout-s",
            str(timeout_s),
        ]
        if molmospaces_python is not None:
            command.extend(["--python-executable", str(molmospaces_python)])
        if molmospaces_root is not None:
            command.extend(["--molmospaces-root", str(molmospaces_root)])
        if torch_extensions_dir is not None:
            command.extend(["--torch-extensions-dir", str(torch_extensions_dir)])
        scene_xml = str((manifest.get("planner_scene") or {}).get("scene_xml") or "")
        if scene_xml:
            command.extend(["--cleanup-scene-xml", scene_xml])
        for flag, value in sorted((request.get("planner_probe_args") or {}).items()):
            command.extend([str(flag), str(value)])
        commands.append(
            {
                "request_id": request.get("request_id"),
                "object_id": request.get("object_id"),
                "target_receptacle_id": request.get("target_receptacle_id"),
                "output_dir": str(proof_dir),
                "run_result": str(proof_dir / "run_result.json"),
                "report": str(proof_dir / "report.html"),
                "command": command,
            }
        )
    return commands


def proof_bundle_run_manifest(
    *,
    cleanup_run_result: Path,
    output_dir: Path,
    proof_requests: dict[str, Any],
    commands: list[dict[str, Any]],
    proof_result_summary: dict[str, Any] | None = None,
    cleanup_command: list[str] | None = None,
    cleanup_rerun: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA,
        "cleanup_run_result": str(cleanup_run_result),
        "output_dir": str(output_dir),
        "proof_request_count": int(proof_requests.get("request_count") or 0),
        "ready_request_count": int(proof_requests.get("ready_count") or 0),
        "planner_scene": proof_requests.get("planner_scene") or {},
        "command_count": len(commands),
        "commands": commands,
        "proof_result_summary": proof_result_summary
        or proof_result_summary_from_commands(commands),
        "cleanup_command": cleanup_command or [],
        "cleanup_rerun": cleanup_rerun or {},
        "evidence_note": (
            "Dry-run manifest for generating bound planner proofs from an ADR-0003 "
            "cleanup artifact. Use --execute-probes in a local RBY1M/CuRobo session."
        ),
    }


def proof_result_summary_from_commands(commands: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize generated proof outputs without replacing strict proof validation."""
    results = [_proof_result_from_command(item) for item in commands]
    return {
        "schema": PLANNER_PROOF_RESULT_SUMMARY_SCHEMA,
        "expected_count": len(commands),
        "result_count": sum(1 for item in results if item["run_result_exists"]),
        "planner_backed_count": sum(1 for item in results if item["planner_backed"]),
        "blocked_count": sum(1 for item in results if item["status"] == "blocked_capability"),
        "missing_result_count": sum(1 for item in results if not item["run_result_exists"]),
        "cleanup_binding_promoted_count": sum(
            1 for item in results if item["cleanup_binding_promoted"]
        ),
        "task_feasibility_blocked_count": sum(
            1 for item in results if item["task_feasibility_status"] == "blocked"
        ),
        "view_artifact_count": sum(len(item.get("views") or []) for item in results),
        "results": results,
        "evidence_note": (
            "Bundle-level summary of generated proof artifacts. Strict per-proof "
            "checkers still decide whether a proof is planner-backed."
        ),
    }


def _proof_result_from_command(item: dict[str, Any]) -> dict[str, Any]:
    run_result_path = Path(str(item.get("run_result") or ""))
    proof_report_path = Path(str(item.get("report") or ""))
    base = run_result_path.parent if str(run_result_path) else Path(".")
    result = {
        "request_id": str(item.get("request_id") or ""),
        "object_id": str(item.get("object_id") or ""),
        "target_receptacle_id": str(item.get("target_receptacle_id") or ""),
        "run_result": str(run_result_path),
        "report": str(proof_report_path),
        "run_result_exists": run_result_path.is_file(),
        "report_exists": proof_report_path.is_file(),
        "status": "not_run",
        "planner_backed": False,
        "cleanup_binding_promoted": False,
        "task_feasibility_status": "not_run",
        "visual_status": "not_run",
        "blockers": [],
        "cleanup_binding_blockers": [],
        "views": [],
    }
    if not run_result_path.is_file():
        return result
    try:
        data = json.loads(run_result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.update(
            {
                "status": "unreadable",
                "task_feasibility_status": "unknown",
                "visual_status": "unknown",
                "blockers": [
                    {
                        "code": "proof_run_result_unreadable",
                        "message": f"{type(exc).__name__}: {exc}",
                    }
                ],
            }
        )
        return result
    evidence = data.get("manipulation_evidence") if isinstance(data, dict) else {}
    evidence = evidence if isinstance(evidence, dict) else {}
    blockers = _blockers(evidence.get("blockers") or [])
    cleanup_binding_blockers = _blockers(evidence.get("cleanup_primitive_binding_blockers") or [])
    cleanup_task_config = evidence.get("cleanup_task_config") or {}
    requested_binding = evidence.get("requested_cleanup_primitive_binding") or {}
    sampled_binding = evidence.get("sampled_task_binding") or {}
    cleanup_binding = evidence.get("cleanup_primitive_binding") or {}
    planner_backed = data.get("status") == "planner_backed"
    views = _proof_views(base, evidence)
    result.update(
        {
            "status": str(data.get("status") or "unknown"),
            "planner_backed": planner_backed,
            "cleanup_binding_promoted": bool(cleanup_binding),
            "task_feasibility_status": _task_feasibility_status(
                status=str(data.get("status") or ""),
                planner_backed=planner_backed,
                cleanup_binding_promoted=bool(cleanup_binding),
                blockers=blockers,
                cleanup_binding_blockers=cleanup_binding_blockers,
                execution_attempted=bool(evidence.get("execution_attempted")),
            ),
            "visual_status": "views_recorded" if views else "no_views_recorded",
            "blockers": blockers,
            "cleanup_binding_blockers": cleanup_binding_blockers,
            "cleanup_task_config": cleanup_task_config,
            "requested_cleanup_primitive_binding": requested_binding,
            "sampled_task_binding": sampled_binding,
            "cleanup_primitive_binding": cleanup_binding,
            "views": views,
        }
    )
    return result


def _task_feasibility_status(
    *,
    status: str,
    planner_backed: bool,
    cleanup_binding_promoted: bool,
    blockers: list[dict[str, Any]],
    cleanup_binding_blockers: list[dict[str, Any]],
    execution_attempted: bool,
) -> str:
    codes = {str(item.get("code") or "") for item in blockers}
    messages = " ".join(str(item.get("message") or "") for item in blockers).lower()
    if "HouseInvalidForTask" in codes or "robot placement" in messages:
        return "blocked"
    if cleanup_binding_promoted:
        return "ready"
    if planner_backed:
        return "binding_not_promoted" if cleanup_binding_blockers else "ready"
    if not execution_attempted:
        return "not_reached"
    if status == "blocked_capability":
        return "blocked"
    return "unknown"


def _proof_views(base: Path, evidence: dict[str, Any]) -> list[dict[str, str]]:
    artifacts = evidence.get("image_artifacts") or {}
    if not isinstance(artifacts, dict):
        return []
    views = []
    for label, value in sorted(artifacts.items()):
        if not value:
            continue
        path = Path(str(value))
        views.append(
            {
                "label": str(label),
                "path": str(path if path.is_absolute() else base / path),
            }
        )
    return views


def _blockers(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict):
        return [dict(raw)]
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, dict)]


def build_cleanup_rerun_command(
    *,
    runner_python: Path,
    cleanup_script: Path,
    cleanup_output_dir: Path,
    source_run_result: dict[str, Any],
    proof_run_results: list[Path],
) -> list[str]:
    command = [
        str(runner_python),
        str(cleanup_script),
        "--output-dir",
        str(cleanup_output_dir),
        "--seed",
        str(source_run_result.get("seed", 1)),
        "--fixture-hint-mode",
        str(source_run_result.get("fixture_hint_mode") or "room_only"),
        "--perception-mode",
        str(source_run_result.get("perception_mode") or "visible_object_detections"),
        "--generated-mess-count",
        str(source_run_result.get("requested_generated_mess_count") or 10),
        "--use-planner-proof-for-cleanup-primitives",
    ]
    backend = source_run_result.get("backend")
    if backend:
        command.extend(["--backend", str(backend)])
    if source_run_result.get("robot_name"):
        command.extend(["--include-robot", "--robot-name", str(source_run_result["robot_name"])])
    if source_run_result.get("robot_view_steps"):
        command.append("--record-robot-views")
    for proof in proof_run_results:
        command.extend(["--planner-proof-run-result", str(proof)])
    return command


def _planner_binding(
    *,
    contract: Any,
    object_id: str,
    target_receptacle_id: str,
    source_receptacle_id: str,
    tools: list[str],
) -> dict[str, Any]:
    binder = getattr(contract, "planner_observed_handle_binding", None)
    if not callable(binder):
        return {
            "ok": False,
            "status": "blocked_capability",
            "object_id": object_id,
            "target_receptacle_id": target_receptacle_id,
            "source_receptacle_id": source_receptacle_id,
            "tools": tools,
            "blockers": [
                {
                    "code": "planner_binding_unavailable",
                    "message": "Cleanup contract does not expose planner observed-handle binding.",
                }
            ],
        }
    return dict(
        binder(
            object_id,
            target_receptacle_id,
            source_receptacle_id=source_receptacle_id,
            tools=tools,
        )
    )


def _planner_scene(contract: Any) -> dict[str, Any]:
    backend = getattr(contract, "backend", None)
    scene_xml = str(getattr(backend, "scene_xml", "") or "")
    if not scene_xml:
        return {
            "schema": "planner_cleanup_proof_scene_v1",
            "available": False,
            "scene_xml": "",
            "backend": str(getattr(backend, "backend", "") or ""),
        }
    return {
        "schema": "planner_cleanup_proof_scene_v1",
        "available": True,
        "scene_xml": scene_xml,
        "backend": str(getattr(backend, "backend", "") or ""),
        "evidence_note": (
            "Real MolmoSpaces cleanup scene used to sample exact planner proof tasks."
        ),
    }


def _cleanup_tools(steps: list[dict[str, Any]]) -> list[str]:
    return [
        phase
        for phase in (str(step.get("phase") or "") for step in steps)
        if phase in SEMANTIC_SUBPHASE_LABELS
    ]


def _request_blockers(request: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = []
    for blocker in request.get("blockers") or []:
        item = dict(blocker)
        item.setdefault("request_id", str(request.get("request_id") or ""))
        item.setdefault("object_id", str(request.get("object_id") or ""))
        item.setdefault("target_receptacle_id", str(request.get("target_receptacle_id") or ""))
        blockers.append(item)
    return blockers


def _proof_dir_name(index: int, request: dict[str, Any]) -> str:
    object_id = _safe_path_part(str(request.get("object_id") or "object"))
    target_id = _safe_path_part(str(request.get("target_receptacle_id") or "target"))
    return f"{index:03d}_{object_id}_to_{target_id}"


def _safe_path_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in value)[:96]
