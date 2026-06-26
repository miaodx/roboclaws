"""MapBuild eval matrix report aggregation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.evals.map_build_report_rendering import (
    render_map_build_matrix_report,
    render_map_build_review_section,
)
from roboclaws.evals.models import MISSING_UNAVAILABLE

MAP_BUILD_MATRIX_REPORT_SCHEMA = "map_build_matrix_report_v1"
__all__ = [
    "MAP_BUILD_MATRIX_REPORT_SCHEMA",
    "discover_eval_results_paths",
    "map_build_matrix_summary_from_bundles",
    "render_map_build_matrix_report",
    "render_map_build_review_section",
    "write_map_build_matrix_report",
]


def write_map_build_matrix_report(
    *,
    eval_results_paths: list[Path],
    output_dir: Path,
) -> dict[str, str]:
    bundles = [_load_eval_results_bundle(path) for path in eval_results_paths]
    summary = map_build_matrix_summary_from_bundles(bundles)
    if not summary["map_build_rows"]:
        raise ValueError("map-build report requires at least one map_build.* result row")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "map_build_matrix_summary.json"
    report_path = output_dir / "map_build_matrix_report.html"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(
        render_map_build_matrix_report(summary, output_dir=output_dir),
        encoding="utf-8",
    )
    return {"report": str(report_path), "summary": str(summary_path)}


def discover_eval_results_paths(raw_refs: str) -> list[Path]:
    paths: list[Path] = []
    for raw_ref in raw_refs.split(","):
        ref = raw_ref.strip()
        if not ref:
            continue
        path = Path(ref)
        if path.is_dir():
            paths.extend(sorted(path.rglob("eval_results.json")))
        else:
            paths.append(path)
    if not paths:
        raise ValueError("map-build-report requires eval_results=<path-or-dir>[,<path-or-dir>...]")
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"missing eval result file(s): {', '.join(missing)}")
    return sorted(dict.fromkeys(paths))


def map_build_matrix_summary_from_bundles(bundles: list[dict[str, Any]]) -> dict[str, Any]:
    sources = [_bundle_source(bundle) for bundle in bundles]
    results: list[dict[str, Any]] = []
    for bundle in bundles:
        bundle_source = _bundle_source(bundle)
        for result in _bundle_results(bundle):
            payload = dict(result)
            payload["_bundle_source"] = bundle_source
            results.append(payload)

    map_build_rows = [
        _map_build_quality_row(result) for result in results if _is_map_build_result(result)
    ]
    downstream_rows = _map_build_downstream_rows(results)
    failure_rows = _map_build_failure_rows(map_build_rows, downstream_rows)
    return {
        "schema": MAP_BUILD_MATRIX_REPORT_SCHEMA,
        "sources": sources,
        "overview": _map_build_overview(map_build_rows, downstream_rows),
        "map_build_rows": map_build_rows,
        "downstream_rows": downstream_rows,
        "failure_rows": failure_rows,
    }


def _load_eval_results_bundle(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed eval result JSON at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"eval result file must contain a JSON object: {path}")
    payload["_source_path"] = str(path)
    return payload


def _bundle_source(bundle: dict[str, Any]) -> dict[str, Any]:
    suite = bundle.get("suite") if isinstance(bundle.get("suite"), dict) else {}
    artifacts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    source_path = str(bundle.get("_source_path") or "")
    if not source_path:
        source_path = str(artifacts.get("results") or artifacts.get("eval_results") or "")
    return {
        "path": source_path,
        "suite_id": str(suite.get("suite_id") or MISSING_UNAVAILABLE),
        "output_dir": str(artifacts.get("output_dir") or ""),
        "eval_report": str(artifacts.get("eval_report") or ""),
    }


def _bundle_results(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    results = bundle.get("results")
    if not isinstance(results, list):
        raise ValueError("eval results bundle must contain results list")
    return [result for result in results if isinstance(result, dict)]


def _is_map_build_result(result: dict[str, Any]) -> bool:
    identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
    sample_id = str(identity.get("sample_id") or "")
    return sample_id.startswith("map_build.")


def _map_build_profile_key(result: dict[str, Any]) -> tuple[str, str, str, str, str, str, str]:
    identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
    return (
        str(identity.get("agent_engine") or MISSING_UNAVAILABLE),
        str(identity.get("provider_profile") or MISSING_UNAVAILABLE),
        str(identity.get("model") or MISSING_UNAVAILABLE),
        str(identity.get("evidence_lane") or MISSING_UNAVAILABLE),
        str(identity.get("camera_labeler") or MISSING_UNAVAILABLE),
        str(identity.get("backend") or MISSING_UNAVAILABLE),
        str(identity.get("seed") or MISSING_UNAVAILABLE),
    )


def _map_build_profile_label_from_identity(identity: dict[str, Any]) -> str:
    agent_engine = str(identity.get("agent_engine") or MISSING_UNAVAILABLE)
    provider_profile = str(identity.get("provider_profile") or MISSING_UNAVAILABLE)
    model = str(identity.get("model") or MISSING_UNAVAILABLE)
    evidence_lane = str(identity.get("evidence_lane") or MISSING_UNAVAILABLE)
    camera_labeler = str(identity.get("camera_labeler") or MISSING_UNAVAILABLE)
    backend = str(identity.get("backend") or MISSING_UNAVAILABLE)
    seed = str(identity.get("seed") or MISSING_UNAVAILABLE)
    if provider_profile == "not_applicable":
        label = agent_engine
    elif model and model != "not_applicable":
        label = f"{provider_profile} / {model}"
    else:
        label = provider_profile
    for setting in (evidence_lane, camera_labeler, backend):
        if setting not in {"", "not_applicable", MISSING_UNAVAILABLE}:
            label = f"{label} / {setting}"
    return f"{label} / seed {seed}"


def _map_build_quality_row(result: dict[str, Any]) -> dict[str, Any]:
    identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    outcome = _outcome(result)
    attempts = (
        metrics.get("model_attempt_summary")
        if isinstance(metrics.get("model_attempt_summary"), dict)
        else {}
    )
    tool_counts = (
        metrics.get("comparison_tool_counts")
        if isinstance(metrics.get("comparison_tool_counts"), dict)
        else {}
    )
    public_anchor_count = _int_value(outcome.get("public_semantic_anchor_count"))
    base_anchor_count = _int_value(outcome.get("base_map_anchor_like_count"))
    runtime_anchor_count = _int_value(outcome.get("runtime_enrichment_anchor_count"))
    return {
        "sample_id": str(identity.get("sample_id") or ""),
        "profile_key": list(_map_build_profile_key(result)),
        "profile_label": _map_build_profile_label_from_identity(identity),
        "agent_engine": str(identity.get("agent_engine") or MISSING_UNAVAILABLE),
        "provider_profile": str(identity.get("provider_profile") or MISSING_UNAVAILABLE),
        "model": str(identity.get("model") or MISSING_UNAVAILABLE),
        "seed": identity.get("seed", MISSING_UNAVAILABLE),
        "status": str(result.get("status") or MISSING_UNAVAILABLE),
        "failure_class": str(result.get("failure_class") or MISSING_UNAVAILABLE),
        "base_map_anchor_like_count": base_anchor_count,
        "public_semantic_anchor_count": public_anchor_count,
        "runtime_enrichment_anchor_count": runtime_anchor_count,
        "semantic_enrichment_over_base": bool(outcome.get("semantic_enrichment_over_base")),
        "richer_than_base": public_anchor_count > base_anchor_count and runtime_anchor_count > 0,
        "stable_semantic_anchor_category_count": _int_value(
            outcome.get("stable_semantic_anchor_category_count")
        ),
        "stable_semantic_anchor_categories": _string_list(
            outcome.get("stable_semantic_anchor_categories")
        ),
        "observed_object_count": _int_value(outcome.get("observed_object_count")),
        "target_candidate_count": _int_value(outcome.get("target_candidate_count")),
        "generated_exploration_candidate_count": _int_value(
            outcome.get("generated_exploration_candidate_count")
        ),
        "sim_truth_fixture_category_recall": outcome.get(
            "sim_truth_fixture_category_recall",
            MISSING_UNAVAILABLE,
        ),
        "sim_truth_fixture_category_precision": outcome.get(
            "sim_truth_fixture_category_precision",
            MISSING_UNAVAILABLE,
        ),
        "sim_truth_best_view_waypoint_accuracy": outcome.get(
            "sim_truth_best_view_waypoint_accuracy",
            MISSING_UNAVAILABLE,
        ),
        "duplicate_fixture_viewpoint_group_count": _int_value(
            outcome.get("duplicate_fixture_viewpoint_group_count")
        ),
        "rgb_only_object_pose_claim_count": _int_value(
            outcome.get("rgb_only_object_pose_claim_count")
        ),
        "private_truth_absent": outcome.get("private_truth_absent", MISSING_UNAVAILABLE),
        "source_map_not_mutated": outcome.get("source_map_not_mutated", MISSING_UNAVAILABLE),
        "tool_call_count": metrics.get("tool_call_count", MISSING_UNAVAILABLE),
        "tool_event_count": metrics.get("tool_event_count", MISSING_UNAVAILABLE),
        "request_event_count": _request_event_count(metrics),
        "wall_time_s": metrics.get("wall_time_s", MISSING_UNAVAILABLE),
        "model_attempt_count": attempts.get("attempt_count", MISSING_UNAVAILABLE),
        "observe_count": _int_value(tool_counts.get("observe")),
        "navigate_to_waypoint_count": _int_value(tool_counts.get("navigate_to_waypoint")),
        "navigate_to_relative_pose_count": _int_value(tool_counts.get("navigate_to_relative_pose")),
        "adjust_camera_count": _int_value(tool_counts.get("adjust_camera")),
        "artifacts": _resolved_result_artifacts(result),
        "source": result.get("_bundle_source", {}),
    }


def _outcome(result: dict[str, Any]) -> dict[str, Any]:
    grader_outputs = (
        result.get("grader_outputs") if isinstance(result.get("grader_outputs"), dict) else {}
    )
    outcome = (
        grader_outputs.get("outcome") if isinstance(grader_outputs.get("outcome"), dict) else {}
    )
    return outcome


def _request_event_count(metrics: dict[str, Any]) -> Any:
    event_counts = metrics.get("tool_event_counts")
    if not isinstance(event_counts, dict):
        return MISSING_UNAVAILABLE
    return sum(
        _int_value(count) for name, count in event_counts.items() if str(name).endswith(":request")
    )


def _map_build_downstream_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[
        tuple[tuple[str, str, str, str, str, str, str], str],
        dict[str, dict[str, Any]],
    ] = {}
    for result in results:
        identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
        sample_id = str(identity.get("sample_id") or "")
        variant_id = _variant_id_from_identity(identity)
        task_family = _map_build_task_family(sample_id)
        if task_family == "not_applicable" or variant_id == "not_applicable":
            continue
        key = (_map_build_profile_key(result), task_family)
        grouped.setdefault(key, {})[variant_id] = result

    rows: list[dict[str, Any]] = []
    for (profile_key, task_family), variants in sorted(grouped.items()):
        no_prior = variants.get("no_prior")
        prior = variants.get("fixture_focused_prior")
        identity_source = prior or no_prior or {}
        identity = (
            identity_source.get("identity")
            if isinstance(identity_source.get("identity"), dict)
            else {}
        )
        label = _pair_comparison_label(no_prior, prior)
        rows.append(
            {
                "profile_key": list(profile_key),
                "profile_label": _map_build_profile_label_from_identity(identity),
                "agent_engine": str(identity.get("agent_engine") or MISSING_UNAVAILABLE),
                "provider_profile": str(identity.get("provider_profile") or MISSING_UNAVAILABLE),
                "model": str(identity.get("model") or MISSING_UNAVAILABLE),
                "seed": identity.get("seed", MISSING_UNAVAILABLE),
                "task_family": task_family,
                "comparison_label": label,
                "reason": _pair_comparison_reason(no_prior, prior, label),
                "no_prior": _downstream_variant_summary(no_prior),
                "fixture_focused_prior": _downstream_variant_summary(prior),
                "tool_deltas": _downstream_tool_deltas(no_prior, prior),
                "outcome_delta": _downstream_outcome_delta(no_prior, prior),
                "evidence": {
                    "no_prior": _downstream_artifacts(no_prior),
                    "fixture_focused_prior": _downstream_artifacts(prior),
                },
            }
        )
    return rows


def _variant_id_from_identity(identity: dict[str, Any]) -> str:
    sample_metadata = identity.get("sample_metadata")
    if isinstance(sample_metadata, dict):
        variant_id = sample_metadata.get("variant_id") or sample_metadata.get("prior_variant")
        if variant_id:
            return str(variant_id)
    sample_id = str(identity.get("sample_id") or "")
    if ".no_prior" in sample_id or "_no_prior_" in sample_id or sample_id.endswith("_no_prior"):
        return "no_prior"
    if (
        ".fixture_focused_prior" in sample_id
        or "_fixture_focused_prior_" in sample_id
        or sample_id.endswith("_fixture_focused_prior")
    ):
        return "fixture_focused_prior"
    return "not_applicable"


def _map_build_task_family(sample_id: str) -> str:
    if sample_id.startswith("open_ended."):
        return "open-ended"
    if sample_id.startswith("cleanup."):
        return "cleanup"
    return "not_applicable"


def _pair_comparison_label(
    no_prior: dict[str, Any] | None,
    prior: dict[str, Any] | None,
) -> str:
    if no_prior is None or prior is None:
        return "inconclusive"
    if str(no_prior.get("status") or "") != "passed":
        return "inconclusive"
    prior_status = str(prior.get("status") or "")
    if prior_status == "failed":
        return "regressed"
    if prior_status != "passed":
        return "inconclusive"
    delta = _downstream_tool_deltas(no_prior, prior)
    if any(
        _int_value(delta.get(key)) < 0
        for key in ("observe", "navigate_to_waypoint", "adjust_camera")
    ):
        return "improved"
    outcome_delta = _downstream_outcome_delta(no_prior, prior)
    restoration_delta = _float_or_none(outcome_delta.get("mess_restoration_rate"))
    if restoration_delta is not None and restoration_delta > 0:
        return "improved"
    return "no_regression"


def _pair_comparison_reason(
    no_prior: dict[str, Any] | None,
    prior: dict[str, Any] | None,
    label: str,
) -> str:
    if no_prior is None:
        return "missing without-MapBuild-prior baseline"
    if prior is None:
        return "missing with-MapBuild-prior row"
    no_prior_status = str(no_prior.get("status") or MISSING_UNAVAILABLE)
    if no_prior_status != "passed":
        failure_class = str(no_prior.get("failure_class") or MISSING_UNAVAILABLE)
        return f"without MapBuild prior baseline {no_prior_status}: {failure_class}"
    prior_status = str(prior.get("status") or MISSING_UNAVAILABLE)
    if prior_status != "passed":
        failure_class = str(prior.get("failure_class") or MISSING_UNAVAILABLE)
        return f"with MapBuild prior {prior_status}: {failure_class}"
    if label == "improved":
        return "lower search cost or better cleanup score than no-prior"
    if label == "no_regression":
        return _variant_prior_verdict(prior)
    return "inconclusive"


def _downstream_variant_summary(result: dict[str, Any] | None) -> dict[str, Any]:
    if result is None:
        return {
            "status": MISSING_UNAVAILABLE,
            "failure_class": MISSING_UNAVAILABLE,
            "sample_id": MISSING_UNAVAILABLE,
            "prior_use_verdict": MISSING_UNAVAILABLE,
            "tool_counts": {},
            "tool_call_count": MISSING_UNAVAILABLE,
            "tool_event_count": MISSING_UNAVAILABLE,
            "request_event_count": MISSING_UNAVAILABLE,
            "wall_time_s": MISSING_UNAVAILABLE,
            "mess_restoration_rate": MISSING_UNAVAILABLE,
        }
    identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return {
        "sample_id": str(identity.get("sample_id") or MISSING_UNAVAILABLE),
        "status": str(result.get("status") or MISSING_UNAVAILABLE),
        "failure_class": str(result.get("failure_class") or MISSING_UNAVAILABLE),
        "prior_use_verdict": _variant_prior_verdict(result),
        "tool_counts": dict(metrics.get("comparison_tool_counts") or {}),
        "tool_call_count": metrics.get("tool_call_count", MISSING_UNAVAILABLE),
        "tool_event_count": metrics.get("tool_event_count", MISSING_UNAVAILABLE),
        "request_event_count": _request_event_count(metrics),
        "wall_time_s": metrics.get("wall_time_s", MISSING_UNAVAILABLE),
        "mess_restoration_rate": metrics.get("mess_restoration_rate", MISSING_UNAVAILABLE),
    }


def _variant_prior_verdict(result: dict[str, Any]) -> str:
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    return str(metrics.get("prior_use_verdict") or "prior_ignored")


def _downstream_artifacts(result: dict[str, Any] | None) -> dict[str, Any]:
    return {} if result is None else _resolved_result_artifacts(result)


def _resolved_result_artifacts(result: dict[str, Any]) -> dict[str, Any]:
    artifacts = result.get("artifacts") if isinstance(result.get("artifacts"), dict) else {}
    source = result.get("_bundle_source") if isinstance(result.get("_bundle_source"), dict) else {}
    output_dir = str(source.get("output_dir") or "")
    base_dir = Path(output_dir) if output_dir else None
    resolved: dict[str, Any] = {}
    for key, value in artifacts.items():
        path_text = str(value or "")
        if not path_text:
            resolved[str(key)] = value
            continue
        path = Path(path_text)
        if (
            not path.is_absolute()
            and base_dir is not None
            and not path.exists()
            and not path_text.startswith("output/")
        ):
            path = base_dir / path
        resolved[str(key)] = str(path)
    return resolved


def _downstream_tool_deltas(
    no_prior: dict[str, Any] | None,
    prior: dict[str, Any] | None,
) -> dict[str, Any]:
    no_summary = _downstream_variant_summary(no_prior)
    prior_summary = _downstream_variant_summary(prior)
    no_counts = (
        no_summary.get("tool_counts") if isinstance(no_summary.get("tool_counts"), dict) else {}
    )
    prior_counts = (
        prior_summary.get("tool_counts")
        if isinstance(prior_summary.get("tool_counts"), dict)
        else {}
    )
    deltas: dict[str, Any] = {}
    for key in ("observe", "navigate_to_waypoint", "navigate_to_relative_pose", "adjust_camera"):
        if key in no_counts or key in prior_counts:
            deltas[key] = _int_value(prior_counts.get(key)) - _int_value(no_counts.get(key))
        else:
            deltas[key] = MISSING_UNAVAILABLE
    deltas["tool_call_count"] = _number_delta(
        no_summary.get("tool_call_count"),
        prior_summary.get("tool_call_count"),
    )
    deltas["wall_time_s"] = _number_delta(
        no_summary.get("wall_time_s"),
        prior_summary.get("wall_time_s"),
    )
    return deltas


def _downstream_outcome_delta(
    no_prior: dict[str, Any] | None,
    prior: dict[str, Any] | None,
) -> dict[str, Any]:
    no_summary = _downstream_variant_summary(no_prior)
    prior_summary = _downstream_variant_summary(prior)
    return {
        "mess_restoration_rate": _number_delta(
            no_summary.get("mess_restoration_rate"),
            prior_summary.get("mess_restoration_rate"),
        )
    }


def _number_delta(before: Any, after: Any) -> Any:
    before_value = _float_or_none(before)
    after_value = _float_or_none(after)
    if before_value is None or after_value is None:
        return MISSING_UNAVAILABLE
    return round(after_value - before_value, 3)


def _map_build_failure_rows(
    map_build_rows: list[dict[str, Any]],
    downstream_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in map_build_rows:
        if row["status"] != "passed":
            rows.append(
                {
                    "profile_label": row["profile_label"],
                    "kind": "map_build",
                    "label": row["status"],
                    "reason": row["failure_class"],
                    "artifacts": row.get("artifacts", {}),
                }
            )
    for row in downstream_rows:
        if row["comparison_label"] in {"regressed", "inconclusive"}:
            artifacts = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
            rows.append(
                {
                    "profile_label": row["profile_label"],
                    "kind": row["task_family"],
                    "label": row["comparison_label"],
                    "reason": row["reason"],
                    "artifacts": artifacts.get("fixture_focused_prior")
                    or artifacts.get("no_prior")
                    or {},
                }
            )
    return rows


def _map_build_overview(
    map_build_rows: list[dict[str, Any]],
    downstream_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    profile_keys = {tuple(row.get("profile_key") or []) for row in map_build_rows}
    labels = [str(row.get("comparison_label") or "") for row in downstream_rows]
    return {
        "profile_count": len(profile_keys),
        "map_build_row_count": len(map_build_rows),
        "map_build_passed": sum(1 for row in map_build_rows if row.get("status") == "passed"),
        "richer_than_base": sum(1 for row in map_build_rows if row.get("richer_than_base")),
        "downstream_row_count": len(downstream_rows),
        "downstream_improved": labels.count("improved"),
        "downstream_no_regression": labels.count("no_regression"),
        "downstream_regressed": labels.count("regressed"),
        "downstream_inconclusive": labels.count("inconclusive"),
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
