#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.planner_proof_requests import (  # noqa: E402
    PLANNER_PROOF_REQUESTS_SCHEMA,
    build_cleanup_rerun_command,
    build_probe_commands,
    build_probe_warmup_command,
    proof_bundle_run_manifest,
    proof_request_selection_from_summary,
)
from roboclaws.molmo_cleanup.report import render_planner_proof_bundle_runner_report  # noqa: E402
from roboclaws.molmo_cleanup.subprocess_backend import DEFAULT_MOLMOSPACES_PYTHON  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBE_SCRIPT = REPO_ROOT / "scripts" / "run_molmo_planner_manipulation_probe.py"
DEFAULT_CLEANUP_SCRIPT = REPO_ROOT / "examples" / "molmospaces_realworld_cleanup.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or run bound planner proof bundle commands from a cleanup artifact."
    )
    parser.add_argument("cleanup_run_result", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runner-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--probe-script", type=Path, default=DEFAULT_PROBE_SCRIPT)
    parser.add_argument("--cleanup-script", type=Path, default=DEFAULT_CLEANUP_SCRIPT)
    parser.add_argument("--molmospaces-python", type=Path, default=DEFAULT_MOLMOSPACES_PYTHON)
    parser.add_argument("--molmospaces-root", type=Path)
    parser.add_argument("--embodiment", choices=("franka", "rby1m"), default="rby1m")
    parser.add_argument("--probe-mode", choices=("config_import", "execute"), default="execute")
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--timeout-s", type=float, default=600.0)
    parser.add_argument("--renderer-device-id", type=int, default=0)
    parser.add_argument("--torch-extensions-dir", type=Path)
    parser.add_argument(
        "--rby1m-curobo-memory-profile",
        choices=("none", "low"),
        default="low",
    )
    parser.add_argument("--execute-probes", action="store_true")
    parser.add_argument(
        "--warmup-rby1m-curobo",
        action="store_true",
        help="Run a visible config-import warmup before proof commands.",
    )
    parser.add_argument("--rerun-cleanup", action="store_true")
    parser.add_argument("--cleanup-output-dir", type=Path)
    parser.add_argument("--prior-proof-bundle-manifest", type=Path, action="append")
    parser.add_argument("--exclude-task-feasibility-blocked", action="store_true")
    parser.add_argument("--generate-fallback-requests", action="store_true")
    parser.add_argument("--fallback-alias-limit", type=int, default=4)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_from_cleanup_result(
        cleanup_run_result=args.cleanup_run_result,
        output_dir=args.output_dir,
        runner_python=args.runner_python,
        probe_script=args.probe_script,
        cleanup_script=args.cleanup_script,
        molmospaces_python=args.molmospaces_python,
        molmospaces_root=args.molmospaces_root,
        embodiment=args.embodiment,
        probe_mode=args.probe_mode,
        steps=args.steps,
        timeout_s=args.timeout_s,
        renderer_device_id=args.renderer_device_id,
        torch_extensions_dir=args.torch_extensions_dir,
        rby1m_curobo_memory_profile=args.rby1m_curobo_memory_profile,
        execute_probes=args.execute_probes,
        warmup_rby1m_curobo=args.warmup_rby1m_curobo,
        rerun_cleanup=args.rerun_cleanup,
        cleanup_output_dir=args.cleanup_output_dir,
        prior_proof_bundle_manifest=args.prior_proof_bundle_manifest,
        exclude_task_feasibility_blocked=args.exclude_task_feasibility_blocked,
        generate_fallback_requests=args.generate_fallback_requests,
        fallback_alias_limit=args.fallback_alias_limit,
    )
    print(
        json.dumps(
            {
                "manifest": str(result["manifest_path"]),
                "report": str(result["report_path"]),
                "status": result["status"],
            }
        )
    )


def run_from_cleanup_result(
    *,
    cleanup_run_result: Path,
    output_dir: Path,
    runner_python: Path,
    probe_script: Path,
    cleanup_script: Path,
    molmospaces_python: Path | None,
    molmospaces_root: Path | None,
    embodiment: str,
    probe_mode: str,
    steps: int,
    timeout_s: float,
    renderer_device_id: int,
    torch_extensions_dir: Path | None,
    rby1m_curobo_memory_profile: str,
    execute_probes: bool = False,
    warmup_rby1m_curobo: bool = False,
    rerun_cleanup: bool = False,
    cleanup_output_dir: Path | None = None,
    prior_proof_bundle_manifest: Path | Sequence[Path] | None = None,
    exclude_task_feasibility_blocked: bool = False,
    generate_fallback_requests: bool = False,
    fallback_alias_limit: int = 4,
) -> dict[str, Any]:
    cleanup_run_result = cleanup_run_result.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_run = json.loads(cleanup_run_result.read_text(encoding="utf-8"))
    requests = _load_proof_requests(source_run, cleanup_run_result.parent)
    prior_summary = _load_prior_proof_result_summary(prior_proof_bundle_manifest)
    proof_request_selection = proof_request_selection_from_summary(
        requests,
        prior_proof_result_summary=prior_summary,
        exclude_task_feasibility_blocked=exclude_task_feasibility_blocked,
        generate_fallback_requests=generate_fallback_requests,
        fallback_alias_limit=fallback_alias_limit,
    )
    effective_torch_extensions_dir = _effective_torch_extensions_dir(
        output_dir=output_dir,
        torch_extensions_dir=torch_extensions_dir,
        warmup_rby1m_curobo=warmup_rby1m_curobo,
    )
    warmup = (
        build_probe_warmup_command(
            output_dir=output_dir,
            runner_python=runner_python,
            probe_script=probe_script,
            molmospaces_python=molmospaces_python,
            molmospaces_root=molmospaces_root,
            embodiment=embodiment,
            timeout_s=timeout_s,
            renderer_device_id=renderer_device_id,
            torch_extensions_dir=effective_torch_extensions_dir,
            rby1m_curobo_memory_profile=rby1m_curobo_memory_profile,
        )
        if warmup_rby1m_curobo
        else {}
    )
    commands = build_probe_commands(
        manifest=requests,
        output_dir=output_dir,
        runner_python=runner_python,
        probe_script=probe_script,
        molmospaces_python=molmospaces_python,
        molmospaces_root=molmospaces_root,
        embodiment=embodiment,
        probe_mode=probe_mode,
        steps=steps,
        timeout_s=timeout_s,
        renderer_device_id=renderer_device_id,
        torch_extensions_dir=effective_torch_extensions_dir,
        rby1m_curobo_memory_profile=rby1m_curobo_memory_profile,
        request_selection=proof_request_selection,
    )
    proof_results: list[Path] = []
    status = "dry_run"
    if execute_probes:
        status = "probes_executed"
        if warmup:
            _run_command(warmup["command"])
        for item in commands:
            _run_command(item["command"])
            proof_results.append(Path(item["run_result"]))
    cleanup_command: list[str] = []
    cleanup_rerun: dict[str, Any] = {}
    if rerun_cleanup:
        if not execute_probes:
            raise ValueError("--rerun-cleanup requires --execute-probes")
        cleanup_output = cleanup_output_dir or output_dir / "cleanup_with_planner_proof_bundle"
        cleanup_command = build_cleanup_rerun_command(
            runner_python=runner_python,
            cleanup_script=cleanup_script,
            cleanup_output_dir=cleanup_output,
            source_run_result=source_run,
            proof_run_results=proof_results,
        )
        _run_command(cleanup_command)
        status = "cleanup_rerun"
        cleanup_rerun = {
            "output_dir": str(cleanup_output),
            "run_result": str(cleanup_output / "run_result.json"),
            "report": str(cleanup_output / "report.html"),
        }
    manifest = proof_bundle_run_manifest(
        cleanup_run_result=cleanup_run_result,
        output_dir=output_dir,
        proof_requests=requests,
        commands=commands,
        warmup=warmup,
        proof_request_selection=proof_request_selection,
        cleanup_command=cleanup_command,
        cleanup_rerun=cleanup_rerun,
    )
    manifest["status"] = status
    report_path = output_dir / "report.html"
    manifest["report"] = str(report_path)
    manifest_path = output_dir / "proof_bundle_run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path = render_planner_proof_bundle_runner_report(
        output_dir=output_dir,
        manifest=manifest,
    )
    return {
        "status": status,
        "manifest_path": manifest_path,
        "report_path": report_path,
        "manifest": manifest,
    }


def _load_proof_requests(source_run: dict[str, Any], base: Path) -> dict[str, Any]:
    inline = source_run.get("planner_proof_requests")
    if isinstance(inline, dict) and inline.get("schema") == PLANNER_PROOF_REQUESTS_SCHEMA:
        return _with_source_planner_scene(inline, source_run)
    artifacts = source_run.get("artifacts") or {}
    request_path = _resolve_path(base, str(artifacts.get("planner_proof_requests") or ""))
    if request_path.is_file():
        data = json.loads(request_path.read_text(encoding="utf-8"))
        assert data.get("schema") == PLANNER_PROOF_REQUESTS_SCHEMA, data
        return _with_source_planner_scene(data, source_run)
    raise ValueError("cleanup run_result does not include planner proof requests")


def _with_source_planner_scene(
    requests: dict[str, Any],
    source_run: dict[str, Any],
) -> dict[str, Any]:
    planner_scene = requests.get("planner_scene") or {}
    if planner_scene.get("scene_xml"):
        return requests
    runtime = source_run.get("molmospaces_runtime") or {}
    scene_xml = str(runtime.get("scene_xml") or "")
    if not scene_xml:
        return requests
    enriched = dict(requests)
    enriched["planner_scene"] = {
        "schema": "planner_cleanup_proof_scene_v1",
        "available": True,
        "scene_xml": scene_xml,
        "backend": str(source_run.get("backend") or ""),
        "evidence_note": (
            "Real MolmoSpaces cleanup scene inferred from source run_result for "
            "backward-compatible proof-bundle command generation."
        ),
    }
    return enriched


def _load_prior_proof_result_summary(
    paths: Path | Sequence[Path] | None,
) -> dict[str, Any]:
    manifest_paths = _prior_manifest_paths(paths)
    if not manifest_paths:
        return {}
    summaries = [_load_one_prior_proof_result_summary(path) for path in manifest_paths]
    return _merge_prior_proof_result_summaries(summaries)


def _prior_manifest_paths(paths: Path | Sequence[Path] | None) -> list[Path]:
    if paths is None:
        return []
    if isinstance(paths, (str, Path)):
        return [Path(paths)]
    return [Path(item) for item in paths]


def _load_one_prior_proof_result_summary(path: Path) -> dict[str, Any]:
    manifest_path = path / "proof_bundle_run_manifest.json" if path.is_dir() else path
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = data.get("proof_result_summary")
    prior = dict(summary) if isinstance(summary, dict) else {}
    fallback_generation = (data.get("proof_request_selection") or {}).get("fallback_generation")
    if isinstance(fallback_generation, dict):
        prior["fallback_generation"] = dict(fallback_generation)
    prior["results"] = _merged_prior_results(
        prior.get("results") or [],
        (data.get("proof_request_selection") or {}).get("excluded_requests") or [],
    )
    return prior


def _merge_prior_proof_result_summaries(summaries: list[dict[str, Any]]) -> dict[str, Any]:
    results_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    discovered_aliases: list[dict[str, Any]] = []
    filtered_aliases: list[dict[str, Any]] = []
    filtered_pairs: list[dict[str, Any]] = []
    normalized_aliases: list[dict[str, Any]] = []
    generated_requests: list[dict[str, Any]] = []
    for summary in summaries:
        for item in summary.get("results") or []:
            if not isinstance(item, dict):
                continue
            request_id = str(item.get("request_id") or "")
            if not request_id:
                continue
            key = _prior_result_merge_key(item)
            existing = results_by_key.get(key)
            candidate = dict(item)
            if existing is None or _prior_result_rank(candidate) >= _prior_result_rank(existing):
                results_by_key[key] = candidate
        fallback_generation = summary.get("fallback_generation") or {}
        if not isinstance(fallback_generation, dict):
            continue
        discovered_aliases.extend(_dict_items(fallback_generation.get("discovered_aliases")))
        filtered_aliases.extend(_dict_items(fallback_generation.get("filtered_aliases")))
        filtered_pairs.extend(_dict_items(fallback_generation.get("filtered_pairs")))
        normalized_aliases.extend(_dict_items(fallback_generation.get("normalized_aliases")))
        generated_requests.extend(_dict_items(fallback_generation.get("generated_requests")))
    fallback_generation = _merged_fallback_generation(
        discovered_aliases=discovered_aliases,
        filtered_aliases=filtered_aliases,
        filtered_pairs=filtered_pairs,
        normalized_aliases=normalized_aliases,
        generated_requests=generated_requests,
    )
    return {
        "schema": "merged_prior_planner_proof_result_summary_v1",
        "result_count": len(results_by_key),
        "prior_manifest_count": len(summaries),
        "results": list(results_by_key.values()),
        "fallback_generation": fallback_generation,
    }


def _prior_result_merge_key(item: dict[str, Any]) -> tuple[str, str, str]:
    request_id = str(item.get("request_id") or "")
    if "_fallback_" not in request_id:
        return (request_id, "", "")
    config = item.get("cleanup_task_config")
    if not isinstance(config, dict):
        config = item.get("requested_cleanup_primitive_binding")
    config = config if isinstance(config, dict) else {}
    object_alias = str(config.get("planner_object_id") or "")
    target_alias = str(config.get("planner_target_receptacle_id") or "")
    if object_alias or target_alias:
        return (request_id, object_alias, target_alias)
    return (request_id, "", "")


def _prior_result_rank(item: dict[str, Any]) -> tuple[int, int, int, int]:
    task_status = str(item.get("task_feasibility_status") or "")
    status = str(item.get("status") or "")
    blockers = item.get("blockers") or []
    return (
        1 if task_status == "blocked" else 0,
        1 if status not in {"", "not_run"} else 0,
        1 if item.get("run_result_exists") else 0,
        len(blockers) if isinstance(blockers, list) else 0,
    )


def _dict_items(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, dict)]


def _merged_fallback_generation(
    *,
    discovered_aliases: list[dict[str, Any]],
    filtered_aliases: list[dict[str, Any]],
    filtered_pairs: list[dict[str, Any]],
    normalized_aliases: list[dict[str, Any]],
    generated_requests: list[dict[str, Any]],
) -> dict[str, Any]:
    discovered = _dedupe_by_keys(
        discovered_aliases,
        ("source_request_id", "axis", "alias"),
    )
    aliases = _dedupe_by_keys(
        filtered_aliases,
        ("source_request_id", "axis", "alias", "reason"),
    )
    pairs = _dedupe_by_keys(
        filtered_pairs,
        ("source_request_id", "object_alias", "target_alias", "reason"),
    )
    normalized = _dedupe_by_keys(
        normalized_aliases,
        ("source_request_id", "axis", "alias", "normalized_alias"),
    )
    generated = _dedupe_by_keys(generated_requests, ("request_id",))
    return {
        "schema": "merged_planner_cleanup_proof_request_fallback_generation_v1",
        "enabled": any([discovered, aliases, pairs, normalized, generated]),
        "generated_request_count": len(generated),
        "generated_requests": generated,
        "discovered_alias_count": len(discovered),
        "discovered_aliases": discovered,
        "filtered_alias_count": len(aliases),
        "filtered_aliases": aliases,
        "filtered_pair_count": len(pairs),
        "filtered_pairs": pairs,
        "normalized_alias_count": len(normalized),
        "normalized_aliases": normalized,
        "evidence_note": (
            "Merged fallback candidate memory from one or more prior proof-bundle "
            "manifests. This is private runner evidence and is not exposed to Agent View."
        ),
    }


def _dedupe_by_keys(
    items: list[dict[str, Any]],
    keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    deduped = []
    seen: set[tuple[str, ...]] = set()
    for item in items:
        key = tuple(str(item.get(name) or "") for name in keys)
        if not any(key) or key in seen:
            continue
        deduped.append(dict(item))
        seen.add(key)
    return deduped


def _merged_prior_results(
    results: list[dict[str, Any]],
    excluded_requests: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = [dict(item) for item in results if isinstance(item, dict)]
    result_ids = {str(item.get("request_id") or "") for item in merged}
    for item in excluded_requests:
        if not isinstance(item, dict):
            continue
        request_id = str(item.get("request_id") or "")
        if not request_id or request_id in result_ids:
            continue
        merged.append(
            {
                "request_id": request_id,
                "status": str(item.get("prior_status") or "blocked_capability"),
                "task_feasibility_status": str(
                    item.get("prior_task_feasibility_status") or "blocked"
                ),
                "blockers": list(item.get("prior_blockers") or []),
            }
        )
        result_ids.add(request_id)
    return merged


def _effective_torch_extensions_dir(
    *,
    output_dir: Path,
    torch_extensions_dir: Path | None,
    warmup_rby1m_curobo: bool,
) -> Path | None:
    if torch_extensions_dir is not None:
        return torch_extensions_dir
    if warmup_rby1m_curobo:
        return output_dir / "torch_extensions"
    return None


def _run_command(command: list[str]) -> None:
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or path.exists():
        return path
    repo_path = REPO_ROOT / path
    if repo_path.exists():
        return repo_path
    return base / path


if __name__ == "__main__":
    main()
