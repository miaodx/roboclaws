from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.semantic_timeline import SEMANTIC_SUBPHASE_LABELS

PLANNER_PROOF_REQUESTS_SCHEMA = "planner_cleanup_proof_requests_v1"
PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA = "planner_cleanup_proof_bundle_run_manifest_v1"


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
    cleanup_command: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema": PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA,
        "cleanup_run_result": str(cleanup_run_result),
        "output_dir": str(output_dir),
        "proof_request_count": int(proof_requests.get("request_count") or 0),
        "ready_request_count": int(proof_requests.get("ready_count") or 0),
        "command_count": len(commands),
        "commands": commands,
        "cleanup_command": cleanup_command or [],
        "evidence_note": (
            "Dry-run manifest for generating bound planner proofs from an ADR-0003 "
            "cleanup artifact. Use --execute-probes in a local RBY1M/CuRobo session."
        ),
    }


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
