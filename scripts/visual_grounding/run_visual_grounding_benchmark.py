#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import io
import json
import os
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.household.visual_grounding import (  # noqa: E402
    DEFAULT_VISUAL_GROUNDING_BASE_URL,
    DEFAULT_VISUAL_GROUNDING_TIMEOUT_S,
    HttpVisualGroundingClient,
    VisualGroundingClientConfig,
    VisualGroundingContractError,
    pipeline_summary_from_response,
    validate_visual_grounding_response,
    visual_grounding_failure_response,
    visual_grounding_request,
)

CORPUS_SCHEMA = "visual_grounding_benchmark_corpus_v1"
RESULT_SCHEMA = "visual_grounding_benchmark_result_v1"
PREDICTION_SCHEMA = "visual_grounding_prediction_v1"
BBOX_MATCH_IOU_THRESHOLD = 0.3


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a perception-isolated visual-grounding HTTP benchmark."
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("harness/visual_grounding/smoke_corpus.json"),
        help="Visual-grounding benchmark corpus manifest.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for result, report, predictions, and overlays.",
    )
    parser.add_argument(
        "--pipeline",
        action="append",
        default=[],
        help="Pipeline id to run. May be repeated or comma-separated.",
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=None,
        help=(
            "Optional benchmark matrix JSON. Rows version model ids, size tiers, "
            "and runtime knobs; --pipeline then acts as a row/pipeline filter."
        ),
    )
    parser.add_argument(
        "--base-url",
        default=os.environ.get("VISUAL_GROUNDING_BASE_URL", DEFAULT_VISUAL_GROUNDING_BASE_URL),
        help="External visual-grounding service base URL.",
    )
    parser.add_argument(
        "--timeout-s",
        type=float,
        default=float(
            os.environ.get("VISUAL_GROUNDING_TIMEOUT_S", DEFAULT_VISUAL_GROUNDING_TIMEOUT_S)
        ),
    )
    parser.add_argument(
        "--include-private-label-details",
        action="store_true",
        help="Include per-observation private label details in the benchmark result/report.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir or Path("output/visual-grounding-benchmark") / _stamp()
    output_dir.mkdir(parents=True, exist_ok=True)

    corpus = _load_corpus(args.corpus)
    benchmark_rows = _benchmark_rows(args)
    predictions_path = output_dir / "visual_grounding_predictions.jsonl"
    all_predictions: list[dict[str, Any]] = []
    pipeline_results: list[dict[str, Any]] = []

    with predictions_path.open("w", encoding="utf-8") as predictions_file:
        for row in benchmark_rows:
            pipeline_id = str(row["pipeline_id"])
            config = VisualGroundingClientConfig(
                pipeline_id=pipeline_id,
                base_url=args.base_url,
                timeout_s=args.timeout_s,
                api_key=os.environ.get("VISUAL_GROUNDING_API_KEY", ""),
                proposer_id=str(
                    row.get("producer_id")
                    or row.get("proposer_id")
                    or os.environ.get("VISUAL_GROUNDING_PROPOSER_ID", "")
                ),
                proposer_model_id=str(
                    row.get("model_id")
                    or row.get("proposer_model_id")
                    or os.environ.get("VISUAL_GROUNDING_PROPOSER_MODEL_ID", "")
                ),
            )
            client = HttpVisualGroundingClient(config)
            predictions = _run_pipeline(
                corpus=corpus,
                corpus_path=args.corpus,
                output_dir=output_dir,
                benchmark_row=row,
                client=client,
            )
            for prediction in predictions:
                predictions_file.write(json.dumps(prediction, sort_keys=True) + "\n")
            all_predictions.extend(predictions)
            pipeline_results.append(
                _summarize_pipeline(
                    pipeline_id=pipeline_id,
                    benchmark_row=row,
                    predictions=predictions,
                    corpus=corpus,
                    auth_mode=config.auth_mode,
                    service_config=config.redacted_metadata(),
                    include_private_label_details=args.include_private_label_details,
                )
            )

    ranking = _rank_pipelines(pipeline_results)
    recommendation = ranking[0] if ranking else {}
    detector_probe_recommendation = _detector_probe_recommendation(pipeline_results, ranking)
    result = {
        "schema": RESULT_SCHEMA,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "corpus": {
            "path": str(args.corpus),
            "schema": corpus["schema"],
            "name": corpus.get("name", ""),
            "observation_count": len(corpus["observations"]),
            "private_labels_in_requests": False,
            "private_label_details_included": bool(args.include_private_label_details),
        },
        "pipelines": pipeline_results,
        "family_sweep": _family_sweep_summary(pipeline_results),
        "ranking": ranking,
        "recommendation": {
            "pipeline_id": recommendation.get("pipeline_id", ""),
            "score": recommendation.get("score", 0.0),
            "reason": _recommendation_reason(recommendation),
        },
        "detector_probe_recommendation": detector_probe_recommendation,
        "artifacts": {
            "predictions_jsonl": predictions_path.name,
            "report_html": "visual_grounding_benchmark_report.html",
            "overlays_dir": "overlays",
        },
    }
    result_path = output_dir / "visual_grounding_benchmark_result.json"
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path = output_dir / "visual_grounding_benchmark_report.html"
    report_path.write_text(
        _render_report(result=result, predictions=all_predictions),
        encoding="utf-8",
    )
    print(f"visual grounding benchmark result: {result_path}")
    print(f"visual grounding benchmark report: {report_path}")
    return 0


def _load_corpus(path: Path) -> dict[str, Any]:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    if corpus.get("schema") != CORPUS_SCHEMA:
        raise SystemExit(f"unsupported corpus schema in {path}")
    observations = corpus.get("observations")
    if not isinstance(observations, list) or not observations:
        raise SystemExit(f"corpus has no observations: {path}")
    return corpus


def _benchmark_rows(args: argparse.Namespace) -> list[dict[str, Any]]:
    filters = set(_pipeline_ids(args.pipeline)) if args.pipeline else set()
    if args.matrix is None:
        pipeline_ids = _pipeline_ids(args.pipeline)
        return [_default_benchmark_row(pipeline_id) for pipeline_id in pipeline_ids]

    matrix = json.loads(args.matrix.read_text(encoding="utf-8"))
    if matrix.get("schema") != "visual_grounding_benchmark_matrix_v1":
        raise SystemExit(f"unsupported benchmark matrix schema in {args.matrix}")
    rows = [_normalize_benchmark_row(row) for row in matrix.get("rows") or []]
    if not rows:
        raise SystemExit(f"benchmark matrix has no rows: {args.matrix}")
    if filters:
        rows = [
            row
            for row in rows
            if str(row.get("row_id") or "") in filters
            or str(row.get("pipeline_id") or "") in filters
            or str(row.get("model_family") or "") in filters
        ]
    if not rows:
        raise SystemExit(f"benchmark matrix filters selected no rows: {sorted(filters)}")
    return rows


def _default_benchmark_row(pipeline_id: str) -> dict[str, Any]:
    family = _pipeline_family(pipeline_id)
    return {
        "row_id": pipeline_id,
        "pipeline_id": pipeline_id,
        "model_family": family,
        "model_id": "",
        "size_tier": "unspecified",
        "runtime_parameters": {},
        "under_sampled_reason": "ad-hoc pipeline run without a matrix row",
    }


def _normalize_benchmark_row(row: dict[str, Any]) -> dict[str, Any]:
    pipeline_id = str(row.get("pipeline_id") or "").strip()
    if not pipeline_id:
        raise SystemExit(f"benchmark matrix row missing pipeline_id: {row}")
    runtime_parameters = _safe_runtime_parameters(
        row.get("runtime_parameters") or row.get("knobs") or {}
    )
    model_family = str(
        row.get("model_family") or row.get("family") or _pipeline_family(pipeline_id)
    )
    model_id = str(row.get("model_id") or row.get("proposer_model_id") or "")
    size_tier = str(row.get("size_tier") or row.get("size") or "unspecified")
    row_id = str(row.get("row_id") or "").strip()
    if not row_id:
        row_id = _safe_id("-".join(part for part in (pipeline_id, model_family, size_tier) if part))
    normalized = {
        "row_id": row_id,
        "pipeline_id": pipeline_id,
        "model_family": model_family,
        "model_id": model_id,
        "size_tier": size_tier,
        "producer_id": str(row.get("producer_id") or row.get("proposer_id") or ""),
        "proposer_model_id": model_id,
        "runtime_parameters": runtime_parameters,
        "under_sampled_reason": str(row.get("under_sampled_reason") or ""),
        "notes": str(row.get("notes") or ""),
    }
    return normalized


def _pipeline_family(pipeline_id: str) -> str:
    first = pipeline_id.split("+", maxsplit=1)[0]
    return first.removesuffix("-direct")


def _safe_runtime_parameters(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    safe: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, (str, int, float, bool)) or item is None:
            safe[str(key)] = item
        elif isinstance(item, list):
            safe[str(key)] = [
                child
                for child in item
                if isinstance(child, (str, int, float, bool)) or child is None
            ]
    return safe


def _pipeline_ids(raw_values: list[str]) -> list[str]:
    values = raw_values or [os.environ.get("VISUAL_GROUNDING_PIPELINE_ID", "fake-http")]
    pipeline_ids: list[str] = []
    for value in values:
        pipeline_ids.extend(part.strip() for part in str(value).split(",") if part.strip())
    seen: set[str] = set()
    unique = [item for item in pipeline_ids if not (item in seen or seen.add(item))]
    return unique or ["fake-http"]


def _run_pipeline(
    *,
    corpus: dict[str, Any],
    corpus_path: Path,
    output_dir: Path,
    benchmark_row: dict[str, Any],
    client: HttpVisualGroundingClient,
) -> list[dict[str, Any]]:
    predictions: list[dict[str, Any]] = []
    pipeline_id = str(benchmark_row["pipeline_id"])
    category_family_map = {
        str(key): str(value) for key, value in (corpus.get("category_family_map") or {}).items()
    }
    for observation in corpus["observations"]:
        observation_id = _safe_id(str(observation.get("observation_id") or "observation"))
        image, image_bytes = _load_observation_image(observation, corpus_path.parent)
        raw_rel = Path("raw_fpv") / f"{observation_id}.jpg"
        _write_jpeg(output_dir / raw_rel, image)
        request = visual_grounding_request(
            run_id=str(corpus.get("name") or "visual-grounding-benchmark"),
            raw_observation={
                "observation_id": str(observation.get("observation_id") or ""),
                "waypoint_id": str(observation.get("waypoint_id") or ""),
                "room_id": str(observation.get("room_id") or ""),
                "artifact_status": "benchmark_fixture",
            },
            category_hints=[str(item) for item in observation.get("category_hints") or []],
            fixture_hints=list(observation.get("fixture_hints") or []),
            pipeline_id=pipeline_id,
            image={
                "mime_type": "image/jpeg",
                "bytes_base64": base64.b64encode(image_bytes).decode("ascii"),
                "width": int(image.width),
                "height": int(image.height),
            },
            proposer=_proposer_request(benchmark_row, client.config),
        )

        started = time.monotonic()
        parse_failed = False
        try:
            response = client.request_candidates(request)
            validate_visual_grounding_response(response)
        except VisualGroundingContractError as exc:
            parse_failed = True
            response = visual_grounding_failure_response(
                pipeline_id=pipeline_id,
                reason="parse_failure",
                message=str(exc),
                latency_ms=round((time.monotonic() - started) * 1000),
            )
        elapsed_ms = round((time.monotonic() - started) * 1000)
        pipeline_summary = pipeline_summary_from_response(
            response,
            auth_mode=client.config.auth_mode,
        )
        pipeline_summary["request_latency_ms"] = elapsed_ms
        pipeline_summary["parse_failed"] = parse_failed
        candidates = list(response.get("candidates") or [])
        diagnostics = _public_diagnostics(response.get("diagnostics") or {})
        overlay_rel = Path("overlays") / observation_id / f"{_safe_id(pipeline_id)}.jpg"
        _write_overlay(output_dir / overlay_rel, image, candidates)
        prediction = {
            "schema": PREDICTION_SCHEMA,
            "benchmark_row_id": str(benchmark_row.get("row_id") or pipeline_id),
            "pipeline_id": pipeline_id,
            "observation_id": str(observation.get("observation_id") or ""),
            "waypoint_id": str(observation.get("waypoint_id") or ""),
            "room_id": str(observation.get("room_id") or ""),
            "capture_context": dict(observation.get("capture_context") or {}),
            "public_context": {
                "category_hints": list(observation.get("category_hints") or []),
                "fixture_hint_count": len(observation.get("fixture_hints") or []),
            },
            "raw_fpv_path": str(raw_rel),
            "overlay_path": str(overlay_rel),
            "pipeline": pipeline_summary,
            "benchmark_row": _public_benchmark_row(benchmark_row),
            "candidate_count": len(candidates),
            "candidates": _public_candidates(candidates, category_family_map),
            "diagnostic_evidence": diagnostics,
        }
        if response.get("status") == "failed":
            prediction["error"] = dict(response.get("error") or {})
        predictions.append(prediction)
    return predictions


def _summarize_pipeline(
    *,
    pipeline_id: str,
    benchmark_row: dict[str, Any],
    predictions: list[dict[str, Any]],
    corpus: dict[str, Any],
    auth_mode: str,
    service_config: dict[str, Any],
    include_private_label_details: bool,
) -> dict[str, Any]:
    observation_by_id = {
        str(item.get("observation_id") or ""): item for item in corpus.get("observations") or []
    }
    category_family_map = {
        str(key): str(value) for key, value in (corpus.get("category_family_map") or {}).items()
    }
    stage_summary = _stage_summary(predictions)
    score = _score_predictions(predictions, observation_by_id, category_family_map)
    failure_count = sum(1 for item in predictions if item["pipeline"].get("status") == "failed")
    parse_failure_count = sum(1 for item in predictions if item["pipeline"].get("parse_failed"))
    timeout_count = sum(1 for item in predictions if _prediction_timed_out(item))
    candidate_count = sum(int(item.get("candidate_count") or 0) for item in predictions)
    latencies = [int(item["pipeline"].get("request_latency_ms") or 0) for item in predictions]
    overlays = [str(item["overlay_path"]) for item in predictions]
    result = {
        "benchmark_row_id": str(benchmark_row.get("row_id") or pipeline_id),
        "pipeline_id": pipeline_id,
        "model_family": str(benchmark_row.get("model_family") or _pipeline_family(pipeline_id)),
        "model_id": str(benchmark_row.get("model_id") or ""),
        "size_tier": str(benchmark_row.get("size_tier") or "unspecified"),
        "runtime_parameters": dict(benchmark_row.get("runtime_parameters") or {}),
        "under_sampled_reason": str(benchmark_row.get("under_sampled_reason") or ""),
        "status": "completed",
        "auth_mode": _pipeline_auth_mode(predictions, fallback=auth_mode),
        "service_config": service_config,
        "observation_count": len(predictions),
        "candidate_count": candidate_count,
        "failure_count": failure_count,
        "parse_failure_count": parse_failure_count,
        "timeout_count": timeout_count,
        "failure_rate": _ratio(failure_count, len(predictions)),
        "timeout_rate": _ratio(timeout_count, len(predictions)),
        "latency_ms": {
            "total": sum(latencies),
            "avg": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
            "max": max(latencies) if latencies else 0,
        },
        "api_cost": _api_cost_summary(predictions),
        "memory_profile": _memory_profile_summary(predictions),
        "evidence_level": _pipeline_evidence_level(predictions),
        "stage_summary": stage_summary,
        "metrics": score["metrics"],
        "overlays": overlays,
    }
    if include_private_label_details:
        result["private_label_details"] = score["private_label_details"]
    return result


def _pipeline_auth_mode(predictions: list[dict[str, Any]], *, fallback: str) -> str:
    modes = [
        str((prediction.get("pipeline") or {}).get("auth_mode") or "") for prediction in predictions
    ]
    for mode in modes:
        if mode and mode != "none":
            return mode
    return fallback


def _stage_summary(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    summaries: dict[tuple[str, str, str], dict[str, Any]] = {}
    for prediction in predictions:
        for stage in prediction["pipeline"].get("stages") or []:
            key = (
                str(stage.get("stage") or ""),
                str(stage.get("producer_id") or ""),
                str(stage.get("model_id") or ""),
            )
            row = summaries.setdefault(
                key,
                {
                    "stage": key[0],
                    "producer_id": key[1],
                    "model_id": key[2],
                    "status_counts": defaultdict(int),
                    "latencies": [],
                    "observation_count": 0,
                    "runtime": {},
                    "runtime_parameters": {},
                },
            )
            row["observation_count"] += 1
            row["status_counts"][str(stage.get("status") or "ok")] += 1
            row["latencies"].append(int(stage.get("latency_ms") or 0))
            if isinstance(stage.get("runtime"), dict) and not row["runtime"]:
                row["runtime"] = dict(stage["runtime"])
            if isinstance(stage.get("runtime_parameters"), dict):
                row["runtime_parameters"].update(stage["runtime_parameters"])

    output: list[dict[str, Any]] = []
    for row in summaries.values():
        latencies = list(row.pop("latencies"))
        status_counts = dict(row.pop("status_counts"))
        output.append(
            {
                **row,
                "status": "ok" if set(status_counts) <= {"ok"} else "mixed",
                "status_counts": status_counts,
                "latency_ms_total": sum(latencies),
                "latency_ms_avg": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
                "latency_ms_max": max(latencies) if latencies else 0,
            }
        )
    return sorted(output, key=lambda item: (item["stage"], item["producer_id"]))


def _score_predictions(
    predictions: list[dict[str, Any]],
    observation_by_id: dict[str, dict[str, Any]],
    category_family_map: dict[str, str],
) -> dict[str, Any]:
    label_count = 0
    candidate_count = 0
    matched_label_count = 0
    matched_candidate_count = 0
    bbox_label_count = 0
    bbox_candidate_count = 0
    bbox_matched_label_count = 0
    bbox_matched_candidate_count = 0
    bbox_category_correct_count = 0
    bbox_ious: list[float] = []
    duplicate_count = 0
    rejected_proposal_count = 0
    destination_hint_count = 0
    destination_hint_known_fixture_count = 0
    destination_hint_plausible_count = 0
    actionability_proxy_count = 0
    private_label_details: list[dict[str, Any]] = []
    for prediction in predictions:
        observation = observation_by_id.get(str(prediction.get("observation_id") or ""), {})
        fixture_hints = list(observation.get("fixture_hints") or [])
        labels = [
            _private_label(label, category_family_map)
            for label in observation.get("private_labels") or []
        ]
        label_count += len(labels)
        bbox_labels = [label for label in labels if label.get("bbox") is not None]
        bbox_label_count += len(bbox_labels)
        candidates = list(prediction.get("candidates") or [])
        candidate_count += len(candidates)
        bbox_candidate_count += sum(1 for candidate in candidates if candidate.get("bbox"))
        duplicate_count += _duplicate_count(candidates)
        rejected_proposal_count += int(
            ((prediction.get("diagnostic_evidence") or {}).get("rejected_proposal_count")) or 0
        )
        remaining = list(labels)
        matched_categories: list[str] = []
        for candidate in candidates:
            candidate_family = _category_family(
                str(candidate.get("category") or ""),
                category_family_map,
            )
            match_index = next(
                (
                    index
                    for index, label in enumerate(remaining)
                    if label["family"] == candidate_family
                ),
                None,
            )
            if match_index is None:
                continue
            label = remaining.pop(match_index)
            matched_label_count += 1
            matched_candidate_count += 1
            matched_categories.append(candidate_family)
            iou = _bbox_iou(candidate.get("bbox"), label.get("bbox"))
            if iou is not None and not bbox_labels:
                bbox_ious.append(iou)
        bbox_match_summary = _match_bbox_labels(
            labels=bbox_labels,
            candidates=candidates,
            category_family_map=category_family_map,
            iou_threshold=BBOX_MATCH_IOU_THRESHOLD,
        )
        bbox_matched_label_count += int(bbox_match_summary["matched_label_count"])
        bbox_matched_candidate_count += int(bbox_match_summary["matched_candidate_count"])
        bbox_category_correct_count += int(bbox_match_summary["category_correct_count"])
        bbox_ious.extend(float(value) for value in bbox_match_summary["matched_ious"])
        for candidate in candidates:
            hint_quality = _destination_hint_quality(candidate, fixture_hints)
            if hint_quality["has_hint"]:
                destination_hint_count += 1
            if hint_quality["known_fixture"]:
                destination_hint_known_fixture_count += 1
            if hint_quality["plausible"]:
                destination_hint_plausible_count += 1
            if hint_quality["actionable_proxy"]:
                actionability_proxy_count += 1
        private_label_details.append(
            {
                "observation_id": prediction.get("observation_id", ""),
                "private_category_families": [label["family"] for label in labels],
                "matched_category_families": matched_categories,
                "bbox_private_category_families": [label["family"] for label in bbox_labels],
                "bbox_matched_label_count": bbox_match_summary["matched_label_count"],
            }
        )
    false_positive_count = max(0, candidate_count - matched_candidate_count)
    bbox_false_positive_count = max(0, bbox_candidate_count - bbox_matched_candidate_count)
    bbox_metrics_available = bbox_label_count > 0
    metrics = {
        "label_count": label_count,
        "matched_label_count": matched_label_count,
        "candidate_count": candidate_count,
        "matched_candidate_count": matched_candidate_count,
        "false_positive_count": false_positive_count,
        "recall": _ratio(matched_label_count, label_count),
        "precision": _ratio(matched_candidate_count, candidate_count),
        "category_family_accuracy": _ratio(matched_candidate_count, candidate_count),
        "duplicate_count": duplicate_count,
        "duplicate_rate": _ratio(duplicate_count, candidate_count),
        "bbox_metrics_available": bbox_metrics_available,
        "bbox_iou_threshold": BBOX_MATCH_IOU_THRESHOLD,
        "bbox_label_count": bbox_label_count,
        "bbox_candidate_count": bbox_candidate_count,
        "bbox_matched_label_count": bbox_matched_label_count,
        "bbox_matched_candidate_count": bbox_matched_candidate_count,
        "bbox_false_positive_count": bbox_false_positive_count,
        "bbox_recall_at_iou": _ratio(bbox_matched_label_count, bbox_label_count),
        "bbox_precision_at_iou": _ratio(bbox_matched_candidate_count, bbox_candidate_count),
        "bbox_category_family_accuracy_at_iou": _ratio(
            bbox_category_correct_count,
            bbox_matched_label_count,
        ),
        "bbox_false_positive_rate": _ratio(bbox_false_positive_count, bbox_candidate_count),
        "bbox_quality_available_count": len(bbox_ious),
        "mean_bbox_iou": round(sum(bbox_ious) / len(bbox_ious), 6) if bbox_ious else None,
        "bbox_quality_note": "overlay_review_required" if not bbox_ious else "iou_available",
        "identity_stability_available": False,
        "identity_collision_rate": None,
        "rejected_proposal_count": rejected_proposal_count,
        "cleanup_relevance_quality_available": rejected_proposal_count > 0,
        "cleanup_relevance_reject_rate": _ratio(
            rejected_proposal_count,
            rejected_proposal_count + candidate_count,
        ),
        "destination_hint_count": destination_hint_count,
        "destination_hint_rate": _ratio(destination_hint_count, candidate_count),
        "destination_hint_known_fixture_count": destination_hint_known_fixture_count,
        "destination_hint_known_fixture_rate": _ratio(
            destination_hint_known_fixture_count,
            destination_hint_count,
        ),
        "destination_hint_plausible_count": destination_hint_plausible_count,
        "destination_hint_plausible_rate": _ratio(
            destination_hint_plausible_count,
            destination_hint_count,
        ),
        "actionability_proxy_count": actionability_proxy_count,
        "actionability_proxy_rate": _ratio(actionability_proxy_count, candidate_count),
        "structured_output_parse_failure_rate": _ratio(
            sum(1 for item in predictions if item["pipeline"].get("parse_failed")),
            len(predictions),
        ),
    }
    return {"metrics": metrics, "private_label_details": private_label_details}


def _rank_pipelines(pipeline_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ranking: list[dict[str, Any]] = []
    for result in pipeline_results:
        metrics = result.get("metrics") or {}
        if metrics.get("bbox_metrics_available"):
            score_basis = "bbox_iou"
            score = (
                0.60 * float(metrics.get("bbox_recall_at_iou") or 0.0)
                + 0.20 * float(metrics.get("bbox_precision_at_iou") or 0.0)
                + 0.10 * float(metrics.get("bbox_category_family_accuracy_at_iou") or 0.0)
                + 0.10 * (1.0 - float(result.get("failure_rate") or 0.0))
            )
        else:
            score_basis = "category_presence"
            score = (
                0.55 * float(metrics.get("recall") or 0.0)
                + 0.25 * float(metrics.get("precision") or 0.0)
                + 0.10 * float(metrics.get("category_family_accuracy") or 0.0)
                + 0.10 * (1.0 - float(result.get("failure_rate") or 0.0))
            )
        ranking.append(
            {
                "benchmark_row_id": result.get("benchmark_row_id", result.get("pipeline_id", "")),
                "pipeline_id": result.get("pipeline_id", ""),
                "model_family": result.get("model_family", ""),
                "model_id": result.get("model_id", ""),
                "size_tier": result.get("size_tier", ""),
                "runtime_parameters": result.get("runtime_parameters", {}),
                "score": round(score, 6),
                "score_basis": score_basis,
                "recall": metrics.get("recall", 0.0),
                "precision": metrics.get("precision", 0.0),
                "bbox_recall_at_iou": metrics.get("bbox_recall_at_iou", 0.0),
                "bbox_precision_at_iou": metrics.get("bbox_precision_at_iou", 0.0),
                "bbox_category_family_accuracy_at_iou": metrics.get(
                    "bbox_category_family_accuracy_at_iou",
                    0.0,
                ),
                "bbox_iou_threshold": metrics.get("bbox_iou_threshold"),
                "actionability_proxy_rate": metrics.get("actionability_proxy_rate", 0.0),
                "failure_rate": result.get("failure_rate", 0.0),
                "timeout_rate": result.get("timeout_rate", 0.0),
                "mean_latency_ms": (result.get("latency_ms") or {}).get("avg", 0.0),
                "api_cost_usd": (result.get("api_cost") or {}).get("total_usd"),
                "memory_peak_mb": (result.get("memory_profile") or {}).get("peak_mb"),
                "evidence_level": result.get("evidence_level", ""),
            }
        )
    return sorted(
        ranking,
        key=lambda item: (
            -float(item["score"]),
            float(item["failure_rate"]),
            float(item["mean_latency_ms"]),
            str(item["pipeline_id"]),
        ),
    )


def _family_sweep_summary(pipeline_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    families: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in pipeline_results:
        family = str(
            result.get("model_family") or _pipeline_family(str(result.get("pipeline_id") or ""))
        )
        families[family].append(result)

    summaries: list[dict[str, Any]] = []
    for family, rows in sorted(families.items()):
        size_tiers = sorted({str(row.get("size_tier") or "unspecified") for row in rows})
        model_ids = sorted({str(row.get("model_id") or "") for row in rows if row.get("model_id")})
        row_ids = [str(row.get("benchmark_row_id") or row.get("pipeline_id") or "") for row in rows]
        successful_rows = [row for row in rows if _benchmark_row_succeeded(row)]
        successful_row_ids = [
            str(row.get("benchmark_row_id") or row.get("pipeline_id") or "")
            for row in successful_rows
        ]
        under_sampled = len(successful_rows) < 2
        explicit_reasons = [
            str(row.get("under_sampled_reason") or "")
            for row in rows
            if str(row.get("under_sampled_reason") or "")
        ]
        reason = ""
        if under_sampled:
            reason = (
                explicit_reasons[0]
                if explicit_reasons
                else _family_under_sampled_reason(rows, len(successful_rows))
            )
        summaries.append(
            {
                "model_family": family,
                "tested_config_count": len(rows),
                "successful_config_count": len(successful_rows),
                "row_ids": row_ids,
                "successful_row_ids": successful_row_ids,
                "size_tiers": size_tiers,
                "model_ids": model_ids,
                "under_sampled": under_sampled,
                "under_sampled_reason": reason,
            }
        )
    return summaries


def _benchmark_row_succeeded(row: dict[str, Any]) -> bool:
    return (
        int(row.get("failure_count") or 0) == 0
        and int(row.get("parse_failure_count") or 0) == 0
        and int(row.get("timeout_count") or 0) == 0
    )


def _family_under_sampled_reason(rows: list[dict[str, Any]], successful_count: int) -> str:
    failure_reasons: set[str] = set()
    for row in rows:
        if _benchmark_row_succeeded(row):
            continue
        for stage in row.get("stage_summary") or []:
            status_counts = stage.get("status_counts") or {}
            for status, count in status_counts.items():
                if str(status) != "ok" and int(count or 0) > 0:
                    failure_reasons.add(str(status))
    if failure_reasons:
        return (
            f"fewer than two successful configs ({successful_count}); "
            f"failure statuses: {', '.join(sorted(failure_reasons))}"
        )
    return f"fewer than two successful configs ({successful_count})"


def _detector_probe_recommendation(
    pipeline_results: list[dict[str, Any]],
    ranking: list[dict[str, Any]],
) -> dict[str, Any]:
    by_row_id = {str(item.get("benchmark_row_id") or ""): item for item in pipeline_results}

    def result_for_rank(row: dict[str, Any]) -> dict[str, Any]:
        row_id = str(row.get("benchmark_row_id") or "")
        if row_id in by_row_id:
            return by_row_id[row_id]
        pipeline_id = str(row.get("pipeline_id") or "")
        return next(
            (
                result
                for result in pipeline_results
                if str(result.get("pipeline_id") or "") == pipeline_id
            ),
            {},
        )

    def best_for(kind: str) -> dict[str, Any]:
        for row in ranking:
            result = result_for_rank(row)
            if _pipeline_kind(result) == kind:
                return row
        return {}

    best_proposer = best_for("proposer_only")
    selected = [
        {
            "slot": "control",
            "pipeline_id": "sim",
            "benchmark_row_id": "sim",
            "reason": "Pipeline-control baseline for end-to-end cleanup comparison.",
        }
    ]
    for slot, row, reason in (
        (
            "best_proposer_only",
            best_proposer,
            "Highest-ranked proposer-only benchmark pipeline.",
        ),
    ):
        pipeline_id = str(row.get("pipeline_id") or "")
        if pipeline_id and pipeline_id not in {item["pipeline_id"] for item in selected}:
            selected.append(
                {
                    "slot": slot,
                    "pipeline_id": pipeline_id,
                    "benchmark_row_id": str(row.get("benchmark_row_id") or pipeline_id),
                    "reason": reason,
                }
            )

    selected_pipeline_ids = [item["pipeline_id"] for item in selected]
    evidence_levels = {
        str(row.get("pipeline_id") or ""): str(result_for_rank(row).get("evidence_level") or "")
        for row in (best_proposer,)
        if str(row.get("pipeline_id") or "") in selected_pipeline_ids
    }
    non_sim_evidence_levels = list(evidence_levels.values())
    real_stage_provenance_present = any(
        level == "real_detector_sidecar" for level in non_sim_evidence_levels
    )
    selected_real_stage_provenance_complete = bool(non_sim_evidence_levels) and all(
        level == "real_detector_sidecar" for level in non_sim_evidence_levels
    )
    return {
        "schema": "visual_grounding_detector_probe_recommendation_v1",
        "policy": {
            "control_pipeline_id": "sim",
            "max_proposer_only_pipelines": 1,
            "max_total_pipelines": 2,
        },
        "selected_end_to_end_pipelines": selected_pipeline_ids,
        "selected": selected,
        "best_proposer_only_pipeline_id": str(best_proposer.get("pipeline_id") or ""),
        "evidence_levels": evidence_levels,
        "real_stage_provenance_present": real_stage_provenance_present,
        "selected_real_stage_provenance_complete": selected_real_stage_provenance_complete,
        "requires_real_stage_provenance_before_probe": (
            not selected_real_stage_provenance_complete
        ),
        "rationale": (
            "End-to-end probes stay capped to the sim control and one detector-only "
            "proposer pipeline."
        ),
    }


def _pipeline_kind(pipeline: dict[str, Any]) -> str:
    pipeline_id = str(pipeline.get("pipeline_id") or "")
    if pipeline_id == "sim":
        return "control"
    return "proposer_only"


def _render_report(*, result: dict[str, Any], predictions: list[dict[str, Any]]) -> str:
    pipeline_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(row.get('benchmark_row_id', '')))}</td>"
        f"<td>{escape(str(row.get('pipeline_id', '')))}</td>"
        f"<td>{escape(str(row.get('model_family', '')))}</td>"
        f"<td>{escape(str(row.get('size_tier', '')))}</td>"
        f"<td>{escape(str(row.get('score', 0)))}</td>"
        f"<td>{escape(str(row.get('score_basis', '')))}</td>"
        f"<td>{escape(str(row.get('bbox_recall_at_iou', 0)))}</td>"
        f"<td>{escape(str(row.get('bbox_precision_at_iou', 0)))}</td>"
        f"<td>{escape(str(row.get('recall', 0)))}</td>"
        f"<td>{escape(str(row.get('precision', 0)))}</td>"
        f"<td>{escape(str(row.get('failure_rate', 0)))}</td>"
        f"<td>{escape(str(row.get('timeout_rate', 0)))}</td>"
        f"<td>{escape(str(row.get('mean_latency_ms', 0)))}</td>"
        f"<td>{escape(str(row.get('evidence_level', '')))}</td>"
        "</tr>"
        for row in result.get("ranking") or []
    )
    observation_rows = "\n".join(
        "<tr>"
        f"<td>{escape(str(item.get('pipeline_id', '')))}</td>"
        f"<td>{escape(str(item.get('observation_id', '')))}</td>"
        f"<td>{escape(str((item.get('pipeline') or {}).get('status', '')))}</td>"
        f"<td>{escape(str(item.get('candidate_count', 0)))}</td>"
        f'<td><a href="{escape(str(item.get("overlay_path", "")))}">overlay</a></td>'
        "</tr>"
        for item in predictions
    )
    stage_rows = "\n".join(
        _stage_report_rows(pipeline) for pipeline in result.get("pipelines") or []
    )
    destination_rows = "\n".join(
        _destination_report_rows(pipeline) for pipeline in result.get("pipelines") or []
    )
    telemetry_rows = "\n".join(
        _telemetry_report_rows(pipeline) for pipeline in result.get("pipelines") or []
    )
    detector_probe_rows = "\n".join(
        _detector_probe_report_rows(result.get("detector_probe_recommendation") or {})
    )
    family_rows = "\n".join(
        _family_sweep_report_rows(row) for row in result.get("family_sweep") or []
    )
    detector_probe = result.get("detector_probe_recommendation") or {}
    detector_probe_gate_text = (
        "Real stage provenance present: "
        f"{detector_probe.get('real_stage_provenance_present', False)}. "
        "Selected real-stage provenance complete: "
        f"{detector_probe.get('selected_real_stage_provenance_complete', False)}. "
        "Requires real detector-sidecar provenance before full cleanup probe: "
        f"{detector_probe.get('requires_real_stage_provenance_before_probe', True)}."
    )
    private_note = (
        "Per-item private label details included."
        if any("private_label_details" in pipeline for pipeline in result.get("pipelines") or [])
        else "Per-item private label details omitted; only aggregate private metrics are shown."
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Visual Grounding Benchmark</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #202124; }}
    table {{ border-collapse: collapse; margin: 1rem 0; width: 100%; }}
    th, td {{ border: 1px solid #d0d7de; padding: 0.45rem 0.55rem; text-align: left; }}
    th {{ background: #f6f8fa; }}
    code {{ background: #f6f8fa; padding: 0.1rem 0.25rem; }}
  </style>
</head>
<body>
  <h1>Visual Grounding Benchmark</h1>
  <p>Corpus: <code>{escape(str((result.get("corpus") or {}).get("name", "")))}</code></p>
  <h2>Pipeline Ranking</h2>
  <table>
    <tr>
      <th>Row</th><th>Pipeline</th><th>Family</th><th>Size</th>
      <th>Score</th><th>Basis</th><th>Bbox recall</th><th>Bbox precision</th>
      <th>Recall</th><th>Precision</th>
      <th>Failure rate</th><th>Timeout rate</th><th>Mean latency ms</th>
      <th>Evidence level</th>
    </tr>
    {pipeline_rows}
  </table>
  <h2>Family Sweep Coverage</h2>
  <table>
    <tr>
      <th>Family</th><th>Rows tested</th><th>Size tiers</th>
      <th>Under-sampled</th><th>Reason</th>
    </tr>
    {family_rows}
  </table>
  <h2>End-To-End Probe Recommendation</h2>
  <p>
    The recommended full-cleanup probe set is capped to the sim control and one
    detector-only proposer pipeline.
  </p>
  <p>{escape(detector_probe_gate_text)}</p>
  <table>
    <tr><th>Slot</th><th>Pipeline</th><th>Evidence level</th><th>Reason</th></tr>
    {detector_probe_rows}
  </table>
  <h2>Visual Grounding Quality</h2>
  <p>{escape(private_note)}</p>
  <h2>Destination Hint Quality</h2>
  <p>
    Destination hints are recorded as producer evidence only. The cleanup runtime's
    destination hint resolver remains authoritative.
  </p>
  <table>
    <tr>
      <th>Pipeline</th><th>Hint rate</th><th>Known fixture rate</th>
      <th>Plausible hint rate</th><th>Actionability proxy rate</th>
    </tr>
    {destination_rows}
  </table>
  <h2>Cost And Resource Telemetry</h2>
  <table>
    <tr>
      <th>Pipeline</th><th>API cost available</th><th>Total USD</th>
      <th>Token usage available</th><th>Memory profile available</th><th>Peak MB</th>
    </tr>
    {telemetry_rows}
  </table>
  <h2>Stage Provenance</h2>
  <table>
    <tr>
      <th>Pipeline</th><th>Stage</th><th>Producer</th><th>Model</th>
      <th>Status</th><th>Latency avg ms</th><th>Device</th><th>Dtype</th><th>CUDA</th>
    </tr>
    {stage_rows}
  </table>
  <h2>Observation Overlays</h2>
  <table>
    <tr><th>Pipeline</th><th>Observation</th><th>Status</th><th>Candidates</th><th>Overlay</th></tr>
    {observation_rows}
  </table>
</body>
</html>
"""


def _stage_report_rows(pipeline: dict[str, Any]) -> str:
    rows = []
    pipeline_id = str(pipeline.get("pipeline_id") or "")
    for stage in pipeline.get("stage_summary") or []:
        runtime = stage.get("runtime") or {}
        rows.append(
            "<tr>"
            f"<td>{escape(pipeline_id)}</td>"
            f"<td>{escape(str(stage.get('stage', '')))}</td>"
            f"<td>{escape(str(stage.get('producer_id', '')))}</td>"
            f"<td>{escape(str(stage.get('model_id', '')))}</td>"
            f"<td>{escape(str(stage.get('status', '')))}</td>"
            f"<td>{escape(str(stage.get('latency_ms_avg', 0)))}</td>"
            f"<td>{escape(str(runtime.get('device', '')))}</td>"
            f"<td>{escape(str(runtime.get('dtype', '')))}</td>"
            f"<td>{escape(str(runtime.get('cuda_available', '')))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _destination_report_rows(pipeline: dict[str, Any]) -> str:
    metrics = pipeline.get("metrics") or {}
    return (
        "<tr>"
        f"<td>{escape(str(pipeline.get('pipeline_id') or ''))}</td>"
        f"<td>{escape(str(metrics.get('destination_hint_rate', 0)))}</td>"
        f"<td>{escape(str(metrics.get('destination_hint_known_fixture_rate', 0)))}</td>"
        f"<td>{escape(str(metrics.get('destination_hint_plausible_rate', 0)))}</td>"
        f"<td>{escape(str(metrics.get('actionability_proxy_rate', 0)))}</td>"
        "</tr>"
    )


def _telemetry_report_rows(pipeline: dict[str, Any]) -> str:
    api_cost = pipeline.get("api_cost") or {}
    memory = pipeline.get("memory_profile") or {}
    return (
        "<tr>"
        f"<td>{escape(str(pipeline.get('pipeline_id') or ''))}</td>"
        f"<td>{escape(str(api_cost.get('available', False)))}</td>"
        f"<td>{escape(str(api_cost.get('total_usd')))}</td>"
        f"<td>{escape(str(api_cost.get('token_usage_available', False)))}</td>"
        f"<td>{escape(str(memory.get('available', False)))}</td>"
        f"<td>{escape(str(memory.get('peak_mb')))}</td>"
        "</tr>"
    )


def _detector_probe_report_rows(detector_probe: dict[str, Any]) -> str:
    rows = []
    evidence_levels = detector_probe.get("evidence_levels") or {}
    for row in detector_probe.get("selected") or []:
        pipeline_id = str(row.get("pipeline_id") or "")
        evidence_level = (
            "control" if pipeline_id == "sim" else str(evidence_levels.get(pipeline_id) or "")
        )
        rows.append(
            "<tr>"
            f"<td>{escape(str(row.get('slot') or ''))}</td>"
            f"<td>{escape(pipeline_id)}</td>"
            f"<td>{escape(evidence_level)}</td>"
            f"<td>{escape(str(row.get('reason') or ''))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _family_sweep_report_rows(row: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{escape(str(row.get('model_family') or ''))}</td>"
        f"<td>{escape(str(row.get('tested_config_count') or 0))}</td>"
        f"<td>{escape(', '.join(str(item) for item in row.get('size_tiers') or []))}</td>"
        f"<td>{escape(str(row.get('under_sampled', False)))}</td>"
        f"<td>{escape(str(row.get('under_sampled_reason') or ''))}</td>"
        "</tr>"
    )


def _load_observation_image(
    observation: dict[str, Any],
    corpus_dir: Path,
) -> tuple[Image.Image, bytes]:
    image_spec = observation.get("image") or {}
    if image_spec.get("source") == "path":
        path = corpus_dir / str(image_spec.get("path") or "")
        image = Image.open(path).convert("RGB")
    elif image_spec.get("source") == "base64":
        data = base64.b64decode(str(image_spec.get("bytes_base64") or ""))
        image = Image.open(io.BytesIO(data)).convert("RGB")
    else:
        image = _synthetic_image(image_spec)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=80)
    return image, buffer.getvalue()


def _synthetic_image(image_spec: dict[str, Any]) -> Image.Image:
    width = int(image_spec.get("width") or 320)
    height = int(image_spec.get("height") or 240)
    background = _rgb(image_spec.get("background"), default=(220, 220, 220))
    image = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(image)
    for item in image_spec.get("objects") or []:
        bbox = item.get("bbox") or [0.25, 0.25, 0.25, 0.2]
        x, y, w, h = _bbox_pixels(bbox, width, height)
        color = _rgb(item.get("color"), default=(240, 80, 80))
        draw.rectangle((x, y, x + w, y + h), fill=color, outline=(34, 34, 34), width=2)
        label = str(item.get("label") or "")
        if label:
            draw.text((x + 4, y + 4), label, fill=(20, 20, 20))
    return image


def _write_jpeg(path: Path, image: Image.Image) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="JPEG", quality=80)


def _write_overlay(path: Path, image: Image.Image, candidates: list[dict[str, Any]]) -> None:
    overlay = image.copy()
    draw = ImageDraw.Draw(overlay)
    for candidate in candidates:
        region = candidate.get("image_region") or {}
        if region.get("type") != "bbox":
            continue
        x, y, w, h = _bbox_pixels(region.get("value") or [0, 0, 0, 0], image.width, image.height)
        draw.rectangle((x, y, x + w, y + h), outline=(26, 115, 232), width=3)
        label = str(candidate.get("category") or "candidate")
        draw.text((x + 4, max(0, y - 14)), label, fill=(26, 77, 160))
    _write_jpeg(path, overlay)


def _bbox_pixels(value: Any, width: int, height: int) -> tuple[int, int, int, int]:
    numbers = [float(item) for item in value]
    return (
        round(numbers[0] * width),
        round(numbers[1] * height),
        round(numbers[2] * width),
        round(numbers[3] * height),
    )


def _public_candidates(
    candidates: list[dict[str, Any]],
    category_family_map: dict[str, str],
) -> list[dict[str, Any]]:
    public: list[dict[str, Any]] = []
    for candidate in candidates:
        region = candidate.get("image_region") or {}
        bbox = region.get("value") if region.get("type") == "bbox" else None
        public.append(
            {
                "category": str(candidate.get("category") or ""),
                "category_family": _category_family(
                    str(candidate.get("category") or ""),
                    category_family_map,
                ),
                "image_region": region,
                "bbox": bbox,
                "confidence": candidate.get("confidence"),
                "evidence_note": str(candidate.get("evidence_note") or ""),
                "source_fixture_id": str(candidate.get("source_fixture_id") or ""),
                "destination_hint": dict(candidate.get("destination_hint") or {}),
            }
        )
    return public


def _public_diagnostics(diagnostics: dict[str, Any]) -> dict[str, Any]:
    if not diagnostics:
        return {
            "schema": "visual_grounding_diagnostics_v1",
            "raw_proposal_count": 0,
            "rejected_proposal_count": 0,
            "rejection_reasons": [],
            "raw_proposals": [],
            "rejected_proposals": [],
            "private_truth_included": False,
        }
    raw_proposals = list(diagnostics.get("raw_proposals") or [])
    rejected = list(diagnostics.get("rejected_proposals") or [])
    return {
        "schema": str(diagnostics.get("schema") or "visual_grounding_diagnostics_v1"),
        "diagnostic_mode": str(diagnostics.get("diagnostic_mode") or ""),
        "raw_proposal_count": len(raw_proposals),
        "rejected_proposal_count": len(rejected),
        "rejection_reasons": sorted(
            {str(item.get("reason") or "") for item in rejected if str(item.get("reason") or "")}
        ),
        "raw_proposals": raw_proposals,
        "rejected_proposals": rejected,
        "private_truth_included": bool(diagnostics.get("private_truth_included", False)),
    }


def _api_cost_summary(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    total_cost = 0.0
    cost_count = 0
    usage_totals = {
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0,
    }
    usage_count = 0
    for stage in _prediction_stages(predictions):
        cost = _float_or_none(stage.get("api_cost_usd"))
        if cost is not None:
            total_cost += cost
            cost_count += 1
        usage = stage.get("token_usage") or {}
        if isinstance(usage, dict):
            collected = False
            for key in usage_totals:
                value = _int_or_none(usage.get(key))
                if value is not None:
                    usage_totals[key] += value
                    collected = True
            if collected:
                usage_count += 1
    return {
        "available": cost_count > 0,
        "source": "service_stage_metadata" if cost_count else "not_reported_by_service",
        "reported_stage_count": cost_count,
        "total_usd": round(total_cost, 8) if cost_count else None,
        "token_usage_available": usage_count > 0,
        "token_usage_reported_stage_count": usage_count,
        "token_usage": usage_totals if usage_count else {},
    }


def _memory_profile_summary(predictions: list[dict[str, Any]]) -> dict[str, Any]:
    peak_values: list[float] = []
    for stage in _prediction_stages(predictions):
        memory = stage.get("memory_profile") or {}
        if isinstance(memory, dict):
            value = _float_or_none(memory.get("peak_mb") or memory.get("rss_peak_mb"))
            if value is not None:
                peak_values.append(value)
        value = _float_or_none(stage.get("memory_peak_mb"))
        if value is not None:
            peak_values.append(value)
    return {
        "available": bool(peak_values),
        "source": "service_stage_metadata" if peak_values else "not_reported_by_service",
        "reported_stage_count": len(peak_values),
        "peak_mb": round(max(peak_values), 3) if peak_values else None,
    }


def _prediction_stages(predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stages: list[dict[str, Any]] = []
    for prediction in predictions:
        pipeline = prediction.get("pipeline") or {}
        for stage in pipeline.get("stages") or []:
            if isinstance(stage, dict):
                stages.append(stage)
    return stages


def _prediction_timed_out(prediction: dict[str, Any]) -> bool:
    pipeline = prediction.get("pipeline") or {}
    if str(pipeline.get("failure_reason") or "") == "timeout":
        return True
    if str((prediction.get("error") or {}).get("reason") or "") == "timeout":
        return True
    return any(
        str(stage.get("status") or "") == "timeout" for stage in pipeline.get("stages") or []
    )


def _pipeline_evidence_level(predictions: list[dict[str, Any]]) -> str:
    diagnostics_modes = {
        str((prediction.get("diagnostic_evidence") or {}).get("diagnostic_mode") or "")
        for prediction in predictions
    }
    stage_versions = {
        str(stage.get("version") or "")
        for stage in _prediction_stages(predictions)
        if str(stage.get("version") or "")
    }
    producer_ids = {
        str(stage.get("producer_id") or "")
        for stage in _prediction_stages(predictions)
        if str(stage.get("producer_id") or "")
    }
    if "real-sidecar-adapter-v1" in stage_versions:
        return "real_detector_sidecar"
    if any(mode.startswith("real_") for mode in diagnostics_modes):
        return "real_detector_sidecar"
    if "deterministic_contract_fake" in diagnostics_modes or "fake-http" in producer_ids:
        return "contract_fake"
    if all(
        (prediction.get("pipeline") or {}).get("status") == "failed" for prediction in predictions
    ):
        return "failure_only"
    return "service_reported"


def _public_benchmark_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "row_id": str(row.get("row_id") or ""),
        "pipeline_id": str(row.get("pipeline_id") or ""),
        "model_family": str(row.get("model_family") or ""),
        "model_id": str(row.get("model_id") or ""),
        "size_tier": str(row.get("size_tier") or ""),
        "runtime_parameters": dict(row.get("runtime_parameters") or {}),
    }


def _proposer_request(
    benchmark_row: dict[str, Any],
    config: VisualGroundingClientConfig,
) -> dict[str, Any]:
    pipeline_id = str(benchmark_row["pipeline_id"])
    first = pipeline_id.split("+", maxsplit=1)[0]
    request = {
        "producer_id": config.proposer_id or first,
        "model_id": config.proposer_model_id or str(benchmark_row.get("model_id") or ""),
    }
    runtime_parameters = dict(benchmark_row.get("runtime_parameters") or {})
    if runtime_parameters:
        request["runtime_parameters"] = runtime_parameters
    return request


def _private_label(label: dict[str, Any], category_family_map: dict[str, str]) -> dict[str, Any]:
    category = str(label.get("category") or "")
    family = str(label.get("category_family") or _category_family(category, category_family_map))
    return {
        "category": category,
        "family": family,
        "bbox": label.get("bbox"),
        "visible": bool(label.get("visible", True)),
    }


def _match_bbox_labels(
    *,
    labels: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    category_family_map: dict[str, str],
    iou_threshold: float,
) -> dict[str, Any]:
    candidate_rows = []
    for index, candidate in enumerate(candidates):
        bbox = candidate.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            continue
        candidate_rows.append(
            {
                "index": index,
                "family": _category_family(
                    str(candidate.get("category") or ""),
                    category_family_map,
                ),
                "bbox": bbox,
            }
        )

    possible_matches: list[tuple[float, int, int, bool]] = []
    for label_index, label in enumerate(labels):
        if not label.get("visible", True):
            continue
        for candidate in candidate_rows:
            iou = _bbox_iou(candidate["bbox"], label.get("bbox"))
            if iou is None or iou < iou_threshold:
                continue
            category_correct = candidate["family"] == label["family"]
            possible_matches.append((iou, label_index, int(candidate["index"]), category_correct))

    matched_labels: set[int] = set()
    matched_candidates: set[int] = set()
    matched_ious: list[float] = []
    category_correct_count = 0
    for iou, label_index, candidate_index, category_correct in sorted(
        possible_matches,
        key=lambda item: (item[0], item[3]),
        reverse=True,
    ):
        if label_index in matched_labels or candidate_index in matched_candidates:
            continue
        matched_labels.add(label_index)
        matched_candidates.add(candidate_index)
        matched_ious.append(iou)
        if category_correct:
            category_correct_count += 1

    return {
        "matched_label_count": len(matched_labels),
        "matched_candidate_count": len(matched_candidates),
        "category_correct_count": category_correct_count,
        "matched_ious": matched_ious,
    }


def _category_family(category: str, category_family_map: dict[str, str]) -> str:
    return category_family_map.get(category, category)


def _bbox_iou(candidate_bbox: Any, label_bbox: Any) -> float | None:
    if not isinstance(candidate_bbox, list) or not isinstance(label_bbox, list):
        return None
    if len(candidate_bbox) != 4 or len(label_bbox) != 4:
        return None
    cx, cy, cw, ch = [float(item) for item in candidate_bbox]
    lx, ly, lw, lh = [float(item) for item in label_bbox]
    c2x, c2y = cx + cw, cy + ch
    l2x, l2y = lx + lw, ly + lh
    ix = max(0.0, min(c2x, l2x) - max(cx, lx))
    iy = max(0.0, min(c2y, l2y) - max(cy, ly))
    intersection = ix * iy
    union = (cw * ch) + (lw * lh) - intersection
    if union <= 0:
        return None
    return round(intersection / union, 6)


def _duplicate_count(candidates: list[dict[str, Any]]) -> int:
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    for candidate in candidates:
        key = (
            str(candidate.get("category") or ""),
            json.dumps(candidate.get("image_region") or {}, sort_keys=True),
        )
        if key in seen:
            duplicates += 1
        seen.add(key)
    return duplicates


def _destination_hint_quality(
    candidate: dict[str, Any],
    fixture_hints: list[dict[str, Any]],
) -> dict[str, bool]:
    hint = candidate.get("destination_hint") or {}
    fixture_id = str(hint.get("candidate_fixture_id") or "")
    known_fixture = next(
        (
            fixture
            for fixture in fixture_hints
            if str(fixture.get("fixture_id") or "") == fixture_id
        ),
        None,
    )
    plausible = False
    if known_fixture is not None:
        preferences = _destination_preferences(str(candidate.get("category") or ""))
        fixture_text = " ".join(
            [
                str(known_fixture.get("fixture_id") or ""),
                str(known_fixture.get("category") or ""),
                str(known_fixture.get("name") or ""),
                " ".join(str(item) for item in known_fixture.get("affordances") or []),
            ]
        ).lower()
        plausible = not preferences or any(preference in fixture_text for preference in preferences)
    region = candidate.get("image_region") or {}
    return {
        "has_hint": bool(fixture_id),
        "known_fixture": known_fixture is not None,
        "plausible": plausible,
        "actionable_proxy": known_fixture is not None
        and plausible
        and region.get("type") in {"bbox", "point", "verbal_region"},
    }


def _destination_preferences(category: str) -> tuple[str, ...]:
    category_norm = "".join(ch for ch in str(category).lower() if ch.isalnum())
    if category_norm in {"dish", "cup", "mug", "plate", "bowl", "utensil"}:
        return ("sink", "countertop")
    if category_norm in {"food", "apple", "bread", "potato", "fruit", "vegetable"}:
        return ("fridge", "refrigerator")
    if category_norm in {"book", "paper", "magazine", "newspaper"}:
        return ("shelf", "bookshelf", "desk")
    if category_norm in {"linen", "towel", "cloth", "blanket", "clothing"}:
        return ("hamper", "laundry")
    if category_norm in {"toy", "ball", "plush", "teddy"}:
        return ("toy", "bin", "shelf")
    if category_norm in {"remotecontrol", "remote", "electronics", "phone"}:
        return ("tv", "stand", "desk")
    if category_norm in {"pillow", "cushion"}:
        return ("bed", "sofa")
    return ()


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 6)


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _recommendation_reason(row: dict[str, Any]) -> str:
    if not row:
        return "No successful pipeline result was available."
    if row.get("score_basis") == "bbox_iou":
        return (
            "Highest weighted bbox-aware benchmark score from visible-object "
            "recall at IoU threshold, bbox precision, category-family accuracy, "
            "and failure-rate metrics."
        )
    return (
        "Highest weighted benchmark score from recall, precision, category-family "
        "accuracy, and failure-rate metrics."
    )


def _rgb(value: Any, *, default: tuple[int, int, int]) -> tuple[int, int, int]:
    if isinstance(value, list) and len(value) == 3:
        return tuple(max(0, min(255, int(item))) for item in value)
    return default


def _safe_id(value: str) -> str:
    safe = [char if char.isalnum() or char in {"-", "_"} else "-" for char in value]
    return "".join(safe).strip("-") or "item"


def _stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


if __name__ == "__main__":
    raise SystemExit(main())
