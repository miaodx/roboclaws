from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.semantic_timeline import SEMANTIC_SUBPHASE_LABELS

PLANNER_PROOF_REQUESTS_SCHEMA = "planner_cleanup_proof_requests_v1"
PLANNER_PROOF_BUNDLE_RUN_MANIFEST_SCHEMA = "planner_cleanup_proof_bundle_run_manifest_v1"
PLANNER_PROOF_RESULT_SUMMARY_SCHEMA = "planner_cleanup_proof_result_summary_v1"
PLANNER_PROOF_REQUEST_SELECTION_SCHEMA = "planner_cleanup_proof_request_selection_v1"
PLANNER_PROOF_REQUEST_FALLBACK_GENERATION_SCHEMA = (
    "planner_cleanup_proof_request_fallback_generation_v1"
)


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


def ready_planner_proof_requests(
    manifest: dict[str, Any],
    *,
    request_selection: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    assert manifest.get("schema") == PLANNER_PROOF_REQUESTS_SCHEMA, manifest
    selected_ids = _selected_request_ids(request_selection)
    requests = [
        *(manifest.get("requests") or []),
        *_generated_ready_proof_requests(request_selection),
    ]
    return [
        request
        for request in requests
        if request.get("ready")
        and (selected_ids is None or str(request.get("request_id") or "") in selected_ids)
    ]


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
    request_selection: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    commands = []
    ready_requests = ready_planner_proof_requests(
        manifest,
        request_selection=request_selection,
    )
    for index, request in enumerate(ready_requests, start=1):
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
    proof_request_selection: dict[str, Any] | None = None,
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
        "proof_request_selection": proof_request_selection
        or proof_request_selection_from_summary(proof_requests),
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


def proof_request_selection_from_summary(
    proof_requests: dict[str, Any],
    *,
    prior_proof_result_summary: dict[str, Any] | None = None,
    exclude_task_feasibility_blocked: bool = False,
    generate_fallback_requests: bool = False,
    fallback_alias_limit: int = 4,
) -> dict[str, Any]:
    """Select ready proof requests, optionally excluding known infeasible requests."""
    ready_requests = [
        request for request in proof_requests.get("requests") or [] if request.get("ready")
    ]
    prior_results = _prior_results_by_request_id(prior_proof_result_summary or {})
    selected = []
    excluded = []
    generated = []
    for request in ready_requests:
        request_id = str(request.get("request_id") or "")
        prior_result = prior_results.get(request_id, {})
        if (
            exclude_task_feasibility_blocked
            and prior_result.get("task_feasibility_status") == "blocked"
        ):
            excluded.append(_excluded_request(request, prior_result))
            if generate_fallback_requests:
                generated.extend(
                    _fallback_requests_for_blocked_request(
                        request,
                        prior_result,
                        limit=fallback_alias_limit,
                    )
                )
            continue
        selected.append(_selected_request(request, prior_result))
    selected.extend(_selected_request(request, {}) for request in generated)
    fallback_required = bool(ready_requests) and not selected
    return {
        "schema": PLANNER_PROOF_REQUEST_SELECTION_SCHEMA,
        "mode": _proof_request_selection_mode(
            exclude_task_feasibility_blocked=exclude_task_feasibility_blocked,
            generate_fallback_requests=generate_fallback_requests,
        ),
        "ready_request_count": len(ready_requests),
        "selected_count": len(selected),
        "excluded_count": len(excluded),
        "generated_fallback_request_count": len(generated),
        "fallback_required": fallback_required,
        "selected_request_ids": [item["request_id"] for item in selected],
        "selected_requests": selected,
        "excluded_requests": excluded,
        "fallback_generation": _fallback_generation(
            enabled=generate_fallback_requests,
            ready_request_count=len(ready_requests),
            excluded_requests=excluded,
            generated_requests=generated,
            fallback_alias_limit=fallback_alias_limit,
        ),
        "prior_summary_available": bool(prior_proof_result_summary),
        "prior_result_count": len(prior_results),
        "evidence_note": (
            "Private proof request selection for local proof-bundle execution. "
            "Excluded requests require fallback generation before another exact proof run."
        ),
    }


def _proof_request_selection_mode(
    *,
    exclude_task_feasibility_blocked: bool,
    generate_fallback_requests: bool,
) -> str:
    if exclude_task_feasibility_blocked and generate_fallback_requests:
        return "exclude_task_feasibility_blocked_with_fallbacks"
    if exclude_task_feasibility_blocked:
        return "exclude_task_feasibility_blocked"
    return "all_ready"


def _selected_request_ids(request_selection: dict[str, Any] | None) -> set[str] | None:
    if not request_selection:
        return None
    raw = request_selection.get("selected_request_ids")
    if raw is None:
        return None
    return {str(item) for item in raw}


def _generated_ready_proof_requests(
    request_selection: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not request_selection:
        return []
    fallback_generation = request_selection.get("fallback_generation") or {}
    if not isinstance(fallback_generation, dict):
        return []
    raw = fallback_generation.get("generated_requests") or []
    return [
        dict(item)
        for item in raw
        if isinstance(item, dict) and item.get("ready") and item.get("request_id")
    ]


def _prior_results_by_request_id(summary: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item.get("request_id") or ""): dict(item)
        for item in summary.get("results") or []
        if isinstance(item, dict) and item.get("request_id")
    }


def _selected_request(
    request: dict[str, Any],
    prior_result: dict[str, Any],
) -> dict[str, Any]:
    fallback = request.get("fallback_request") or {}
    is_fallback = isinstance(fallback, dict) and bool(fallback)
    return {
        "request_id": str(request.get("request_id") or ""),
        "request_type": "fallback_generated" if is_fallback else "source",
        "source_request_id": str(fallback.get("source_request_id") or ""),
        "object_id": str(request.get("object_id") or ""),
        "target_receptacle_id": str(request.get("target_receptacle_id") or ""),
        "prior_task_feasibility_status": str(
            prior_result.get("task_feasibility_status")
            or fallback.get("prior_task_feasibility_status")
            or "unknown"
        ),
    }


def _excluded_request(
    request: dict[str, Any],
    prior_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "request_id": str(request.get("request_id") or ""),
        "object_id": str(request.get("object_id") or ""),
        "target_receptacle_id": str(request.get("target_receptacle_id") or ""),
        "reason": "prior_task_feasibility_blocked",
        "prior_status": str(prior_result.get("status") or ""),
        "prior_task_feasibility_status": str(prior_result.get("task_feasibility_status") or ""),
        "prior_blockers": _blockers(prior_result.get("blockers") or []),
    }


def _fallback_generation(
    *,
    enabled: bool,
    ready_request_count: int,
    excluded_requests: list[dict[str, Any]],
    generated_requests: list[dict[str, Any]],
    fallback_alias_limit: int,
) -> dict[str, Any]:
    if not enabled and not generated_requests:
        return {
            "schema": PLANNER_PROOF_REQUEST_FALLBACK_GENERATION_SCHEMA,
            "enabled": False,
            "generated_request_count": 0,
            "generated_requests": [],
        }
    generated_source_ids = {str(item.get("source_request_id") or "") for item in generated_requests}
    unavailable_count = len(excluded_requests) - len(generated_source_ids)
    return {
        "schema": PLANNER_PROOF_REQUEST_FALLBACK_GENERATION_SCHEMA,
        "enabled": enabled,
        "ready_request_count": ready_request_count,
        "excluded_request_count": len(excluded_requests),
        "generated_request_count": len(generated_requests),
        "unavailable_source_request_count": max(unavailable_count, 0),
        "fallback_alias_limit": max(int(fallback_alias_limit or 0), 0),
        "generated_requests": generated_requests,
        "evidence_note": (
            "Private generated fallback proof requests. They preserve cleanup-facing "
            "object and target IDs while trying alternate planner aliases."
        ),
    }


def _fallback_requests_for_blocked_request(
    request: dict[str, Any],
    prior_result: dict[str, Any],
    *,
    limit: int,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    args = request.get("planner_probe_args") or {}
    current_object_alias = _planner_arg(args, "--cleanup-planner-object-id")
    current_target_alias = _planner_arg(args, "--cleanup-planner-target-receptacle-id")
    pickup_candidates = _candidate_aliases(
        request,
        candidate_key="candidate_pickup_names",
        current_alias=current_object_alias,
    )
    target_candidates = _candidate_aliases(
        request,
        candidate_key="candidate_place_receptacle_names",
        current_alias=current_target_alias,
    )
    generated: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for object_alias in pickup_candidates:
        for target_alias in target_candidates:
            pair = (object_alias, target_alias)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            if pair == (current_object_alias, current_target_alias):
                continue
            generated.append(
                _fallback_request_with_planner_aliases(
                    request,
                    prior_result,
                    index=len(generated) + 1,
                    planner_object_id=object_alias,
                    planner_target_receptacle_id=target_alias,
                )
            )
            if len(generated) >= limit:
                return generated
    return generated


def _fallback_request_with_planner_aliases(
    request: dict[str, Any],
    prior_result: dict[str, Any],
    *,
    index: int,
    planner_object_id: str,
    planner_target_receptacle_id: str,
) -> dict[str, Any]:
    source_request_id = str(request.get("request_id") or "")
    fallback = deepcopy(request)
    fallback["request_id"] = f"{source_request_id}_fallback_{index:02d}"
    fallback["ready"] = True
    fallback["source_request_id"] = source_request_id
    fallback["fallback_request"] = {
        "source_request_id": source_request_id,
        "reason": "prior_task_feasibility_blocked",
        "strategy": "alternate_planner_alias",
        "planner_object_id": planner_object_id,
        "planner_target_receptacle_id": planner_target_receptacle_id,
        "prior_status": str(prior_result.get("status") or ""),
        "prior_task_feasibility_status": str(prior_result.get("task_feasibility_status") or ""),
        "prior_blockers": _blockers(prior_result.get("blockers") or []),
        "agent_view_exposed": False,
    }
    args = dict(fallback.get("planner_probe_args") or {})
    if planner_object_id:
        args["--cleanup-planner-object-id"] = planner_object_id
    if planner_target_receptacle_id:
        args["--cleanup-planner-target-receptacle-id"] = planner_target_receptacle_id
    fallback["planner_probe_args"] = args
    binding = fallback.get("binding")
    if isinstance(binding, dict):
        binding["planner_object_id"] = planner_object_id
        binding["planner_target_receptacle_id"] = planner_target_receptacle_id
        binding["planner_probe_args"] = args
        requested = binding.get("requested_cleanup_primitive_binding")
        if isinstance(requested, dict):
            requested["planner_object_id"] = planner_object_id
            requested["planner_target_receptacle_id"] = planner_target_receptacle_id
    return fallback


def _candidate_aliases(
    request: dict[str, Any],
    *,
    candidate_key: str,
    current_alias: str,
) -> list[str]:
    binding = request.get("binding") or {}
    backend_binding = (
        binding.get("backend_planner_task_binding") if isinstance(binding, dict) else {}
    )
    values = [current_alias]
    if isinstance(binding, dict):
        values.extend(str(item) for item in binding.get(candidate_key) or [])
    if isinstance(backend_binding, dict):
        values.extend(str(item) for item in backend_binding.get(candidate_key) or [])
    return _unique_nonempty_values(values)


def _planner_arg(args: Any, key: str) -> str:
    return str(args.get(key) or "") if isinstance(args, dict) else ""


def _unique_nonempty_values(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value) for value in values if str(value)))


def proof_result_summary_from_commands(commands: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize generated proof outputs without replacing strict proof validation."""
    results = [_proof_result_from_command(item) for item in commands]
    return {
        "schema": PLANNER_PROOF_RESULT_SUMMARY_SCHEMA,
        "expected_count": len(commands),
        "result_count": sum(1 for item in results if item["run_result_exists"]),
        "planner_backed_count": sum(1 for item in results if item["planner_backed"]),
        "blocked_count": sum(1 for item in results if item["status"] == "blocked_capability"),
        "timeout_count": sum(1 for item in results if _has_blocker_code(item, "timeout")),
        "rby1m_config_import_timeout_count": sum(
            1
            for item in results
            if _has_blocker_code(item, "timeout")
            and item.get("last_worker_stage") == "rby1m_config_import"
        ),
        "missing_result_count": sum(1 for item in results if not item["run_result_exists"]),
        "cleanup_binding_promoted_count": sum(
            1 for item in results if item["cleanup_binding_promoted"]
        ),
        "execution_attempted_count": sum(1 for item in results if item["execution_attempted"]),
        "task_feasibility_blocked_count": sum(
            1 for item in results if item["task_feasibility_status"] == "blocked"
        ),
        "worker_stage_event_count": sum(
            int(item.get("worker_stage_event_count") or 0) for item in results
        ),
        "last_worker_stage_counts": _last_worker_stage_counts(results),
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
        "execution_attempted": False,
        "task_feasibility_status": "not_run",
        "visual_status": "not_run",
        "blockers": [],
        "cleanup_binding_blockers": [],
        "last_worker_stage": "",
        "worker_stage_event_count": 0,
        "worker_stage_events": [],
        "stdout": "",
        "stderr": "",
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
    artifacts = data.get("artifacts") if isinstance(data, dict) else {}
    artifacts = artifacts if isinstance(artifacts, dict) else {}
    blockers = _blockers(evidence.get("blockers") or [])
    cleanup_binding_blockers = _blockers(evidence.get("cleanup_primitive_binding_blockers") or [])
    cleanup_task_config = evidence.get("cleanup_task_config") or {}
    requested_binding = evidence.get("requested_cleanup_primitive_binding") or {}
    sampled_binding = evidence.get("sampled_task_binding") or {}
    cleanup_binding = evidence.get("cleanup_primitive_binding") or {}
    planner_backed = data.get("status") == "planner_backed"
    views = _proof_views(base, evidence)
    worker_stage_events = _compact_worker_stage_events(evidence.get("worker_stage_events") or [])
    result.update(
        {
            "status": str(data.get("status") or "unknown"),
            "planner_backed": planner_backed,
            "cleanup_binding_promoted": bool(cleanup_binding),
            "execution_attempted": bool(evidence.get("execution_attempted")),
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
            "last_worker_stage": str(evidence.get("last_worker_stage") or ""),
            "worker_stage_event_count": len(worker_stage_events),
            "worker_stage_events": worker_stage_events,
            "stdout": _proof_artifact_path(base, artifacts, "stdout"),
            "stderr": _proof_artifact_path(base, artifacts, "stderr"),
            "cleanup_task_config": cleanup_task_config,
            "requested_cleanup_primitive_binding": requested_binding,
            "sampled_task_binding": sampled_binding,
            "cleanup_primitive_binding": cleanup_binding,
            "views": views,
        }
    )
    return result


def _has_blocker_code(result: dict[str, Any], code: str) -> bool:
    blockers = [*(result.get("blockers") or []), *(result.get("cleanup_binding_blockers") or [])]
    return any(isinstance(item, dict) and str(item.get("code") or "") == code for item in blockers)


def _last_worker_stage_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in results:
        stage = str(item.get("last_worker_stage") or "")
        if stage:
            counts[stage] = counts.get(stage, 0) + 1
    return counts


def _compact_worker_stage_events(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    events = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        compact = {}
        for key in ("elapsed_s", "event", "stage", "embodiment", "probe_mode"):
            value = item.get(key)
            if value not in (None, "", []):
                compact[key] = value
        if compact:
            events.append(compact)
    return events


def _proof_artifact_path(base: Path, artifacts: dict[str, Any], key: str) -> str:
    value = artifacts.get(key)
    if not value:
        return ""
    path = Path(str(value))
    return str(path if path.is_absolute() else base / path)


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
