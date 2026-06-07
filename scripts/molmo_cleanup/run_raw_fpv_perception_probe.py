#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]

from roboclaws.household.raw_fpv_guidance import (  # noqa: E402
    RAW_FPV_CATEGORY_HINT,
    RAW_FPV_HIGH_CONFIDENCE_TARGETS,
)

REPORT_SCHEMA = "raw_fpv_perception_probe_report_v1"
PUBLIC_INPUT_SCHEMA = "raw_fpv_perception_probe_public_input_v1"
PRIVATE_LABEL_SCHEMA = "raw_fpv_private_label_manifest_v1"
PREDICTION_SCHEMA = "raw_fpv_probe_predictions_v1"
RESPONSE_SCHEMA = "raw_fpv_probe_response_v1"

DEFAULT_RAW_RUN_DIRS = (
    Path("output/household/household-cleanup/codex-camera-raw/0606_1537/seed-7"),
    Path("output/household/household-cleanup/codex-camera-raw/0606_1156/seed-7"),
)
DEFAULT_CONTRAST_RUN_DIRS = (
    Path("output/household/household-cleanup/codex-camera-labels/0606_1227/seed-7"),
)
DEFAULT_SEMANTIC_MAP_PRIOR = Path(
    "output/molmo/codex-harness8/0607_0943-codexenv-cleanwt/"
    "_semantic-map-prior-dino/0607_0943/seed-7/runtime_metric_map.json"
)
DEFAULT_OUTPUT_ROOT = Path("output/molmo/raw-fpv-perception-probe")
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_CODEX_BASE_URL = "https://api.openai.com/v1"

SCREEN_GRID_REGIONS = (
    "upper_left",
    "upper_center",
    "upper_right",
    "middle_left",
    "center",
    "middle_right",
    "lower_left",
    "lower_center",
    "lower_right",
)
SURFACE_HINTS = (
    "floor",
    "table",
    "shelf",
    "counter",
    "bed",
    "sofa",
    "unknown",
)
FAILURE_CLASSES = (
    "schema_failure",
    "locality_too_coarse_or_invalid",
    "semantic_mismatch/unresolved",
    "missing_private_label",
)


@dataclass(frozen=True)
class ObservationFrame:
    frame_id: str
    source_run_id: str
    source_kind: str
    source_observation_id: str
    waypoint_id: str
    room_id: str
    image_path: Path
    image_artifact: str
    width: int
    height: int
    image_sha256: str

    def public_payload(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "source_run_id": self.source_run_id,
            "source_kind": self.source_kind,
            "source_observation_id": self.source_observation_id,
            "waypoint_id": self.waypoint_id,
            "room_id": self.room_id,
            "image_artifact": self.image_artifact,
            "image_sha256": self.image_sha256,
            "image_dimensions": {"width": self.width, "height": self.height},
        }


@dataclass(frozen=True)
class ProbeLabel:
    frame_id: str
    source_observation_id: str
    object_id: str
    category: str
    bbox: tuple[float, float, float, float] | None
    coarse_regions: tuple[str, ...]
    surface_hint: str
    label_source: str
    private: bool

    def score_payload(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "source_observation_id": self.source_observation_id,
            "object_id": self.object_id,
            "category": self.category,
            "bbox": list(self.bbox) if self.bbox is not None else None,
            "coarse_regions": list(self.coarse_regions),
            "surface_hint": self.surface_hint,
            "label_source": self.label_source,
            "private": self.private,
        }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_dotenv(args.env_file)
    report = run_probe(args)
    print(json.dumps(_console_summary(report), indent=2, sort_keys=True))
    status = str(report.get("status") or "")
    if status == "blocked_needs_decision":
        return 2
    if any(
        str(item.get("execution_status") or "").endswith("_error")
        for item in report.get("matrix", [])
    ):
        return 1
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run a perception-only RAW-FPV probe over fixed cleanup frames. The probe "
            "keeps public model prompts separate from offline private scoring labels."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--raw-run-dir", action="append", type=Path, default=[])
    parser.add_argument("--contrast-run-dir", action="append", type=Path, default=[])
    parser.add_argument("--semantic-map-prior", type=Path, default=DEFAULT_SEMANTIC_MAP_PRIOR)
    parser.add_argument("--private-labels", action="append", type=Path, default=[])
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--provider",
        choices=("offline", "codex-env"),
        default="offline",
        help="offline scores supplied predictions only; codex-env calls a Responses endpoint.",
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument(
        "--prompt-variant",
        choices=("both", "baseline_json", "skill_json_semantic_map"),
        default="both",
    )
    parser.add_argument("--max-frames-per-source", type=int, default=18)
    parser.add_argument("--threshold", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    return parser.parse_args(argv)


def run_probe(args: argparse.Namespace) -> dict[str, Any]:
    output_run_dir = _output_run_dir(args.output_dir, args.run_id)
    output_run_dir.mkdir(parents=True, exist_ok=True)

    raw_run_dirs = tuple(args.raw_run_dir or DEFAULT_RAW_RUN_DIRS)
    contrast_run_dirs = tuple(args.contrast_run_dir or DEFAULT_CONTRAST_RUN_DIRS)
    frames = collect_observation_frames(
        raw_run_dirs=raw_run_dirs,
        contrast_run_dirs=contrast_run_dirs,
        max_frames_per_source=max(1, int(args.max_frames_per_source)),
    )
    semantic_map_prior = _load_json_if_exists(args.semantic_map_prior)
    public_inputs = build_public_inputs(
        frames,
        semantic_map_prior=semantic_map_prior,
        max_candidates=max(1, min(3, int(args.max_candidates))),
    )
    labels = load_probe_labels(
        tuple(args.private_labels or ()),
        frames=frames,
        contrast_run_dirs=contrast_run_dirs,
    )
    predictions = load_predictions(args.predictions)

    variants = _selected_variants(args.prompt_variant)
    matrix = []
    response_dir = output_run_dir / "responses"
    response_dir.mkdir(exist_ok=True)
    for variant_id in variants:
        variant_predictions = dict(predictions.get(variant_id) or {})
        execution_status = "predictions_loaded" if variant_predictions else "not_run_offline"
        provider_errors: list[dict[str, Any]] = []
        if args.provider != "offline":
            execution_status, provider_errors, variant_predictions = execute_provider_variant(
                variant_id=variant_id,
                public_inputs=public_inputs,
                output_dir=response_dir / variant_id,
                provider=args.provider,
                model=args.model,
                timeout_s=float(args.timeout_s),
            )
        metrics = score_variant(
            variant_id=variant_id,
            frames=frames,
            labels=labels,
            predictions=variant_predictions,
            threshold=max(1, int(args.threshold)),
        )
        matrix.append(
            {
                "variant_id": variant_id,
                "provider": args.provider,
                "model": args.model if args.provider != "offline" else "",
                "execution_status": execution_status,
                "provider_errors": provider_errors,
                "metrics": metrics,
            }
        )

    prompt_inputs_path = output_run_dir / "prompt_inputs.json"
    prompt_inputs_path.write_text(
        json.dumps(public_inputs, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    score_path = output_run_dir / "private_score.json"
    score_path.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_perception_probe_private_score_v1",
                "label_count": len(labels),
                "private_label_count": sum(1 for item in labels if item.private),
                "labels": [item.score_payload() for item in labels],
                "matrix": matrix,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    recommendation = route_recommendation(matrix)
    status = _probe_status(matrix, labels=labels, provider=args.provider)
    report = {
        "schema": REPORT_SCHEMA,
        "status": status,
        "generated_at": _utc_timestamp(),
        "output_dir": str(output_run_dir),
        "threshold": max(1, int(args.threshold)),
        "source_runs": {
            "raw": [str(path) for path in raw_run_dirs],
            "contrast": [str(path) for path in contrast_run_dirs],
        },
        "frame_count": len(frames),
        "label_count": len(labels),
        "private_label_count": sum(1 for item in labels if item.private),
        "missing_label_frame_count": _missing_label_frame_count(frames, labels),
        "semantic_map_context": {
            "provided": bool(semantic_map_prior),
            "source": str(args.semantic_map_prior) if semantic_map_prior else "",
            "compressed_context_only": True,
            "needs_current_frame_confirm": True,
        },
        "privacy": {
            "private_labels_in_prompt_inputs": _contains_private_label_leak(public_inputs, labels),
            "agent_facing_input_contains_executable_prior_handles": (
                _contains_executable_prior_handle(public_inputs)
            ),
        },
        "artifacts": {
            "prompt_inputs": str(prompt_inputs_path),
            "private_score": str(score_path),
            "html_report": str(output_run_dir / "report.html"),
        },
        "matrix": matrix,
        "route_recommendation": recommendation,
    }
    report_path = output_run_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_run_dir / "report.html").write_text(render_html_report(report), encoding="utf-8")
    return report


def collect_observation_frames(
    *,
    raw_run_dirs: tuple[Path, ...],
    contrast_run_dirs: tuple[Path, ...],
    max_frames_per_source: int,
) -> list[ObservationFrame]:
    frames: list[ObservationFrame] = []
    for source_kind, run_dirs in (
        ("raw_failure", raw_run_dirs),
        ("contrast", contrast_run_dirs),
    ):
        for run_dir in run_dirs:
            run_dir = run_dir.expanduser()
            if not run_dir.exists():
                continue
            collected = _collect_frames_from_run_dir(run_dir, source_kind=source_kind)
            frames.extend(collected[:max_frames_per_source])
    return frames


def build_public_inputs(
    frames: list[ObservationFrame],
    *,
    semantic_map_prior: dict[str, Any],
    max_candidates: int,
) -> dict[str, Any]:
    return {
        "schema": PUBLIC_INPUT_SCHEMA,
        "prompt_contract": {
            "response_schema": RESPONSE_SCHEMA,
            "json_only": True,
            "max_candidates_per_observation": max_candidates,
            "required_candidate_fields": [
                "source_observation_id",
                "category",
                "evidence_note",
                "confidence",
                "locality",
            ],
            "coarse_locality": {
                "screen_grid_regions": list(SCREEN_GRID_REGIONS),
                "surface_hints": list(SURFACE_HINTS),
            },
            "actionability_boundary": (
                "This probe does not authorize cleanup actions. Current-frame RAW-FPV "
                "confirmation would still be required by live cleanup tools."
            ),
        },
        "variants": {
            "baseline_json": {
                "description": "Strict JSON RAW-FPV prompt without semantic-map planning context.",
                "frames": [
                    _prompt_payload_for_frame(frame, semantic_context={}) for frame in frames
                ],
            },
            "skill_json_semantic_map": {
                "description": (
                    "Skill-shaped strict JSON prompt with compressed semantic-map planning "
                    "context only. Prior context is not executable."
                ),
                "frames": [
                    _prompt_payload_for_frame(
                        frame,
                        semantic_context=_compressed_semantic_context(
                            frame,
                            semantic_map_prior=semantic_map_prior,
                        ),
                    )
                    for frame in frames
                ],
            },
        },
    }


def load_probe_labels(
    paths: Path | tuple[Path, ...] | list[Path] | None,
    *,
    frames: list[ObservationFrame],
    contrast_run_dirs: tuple[Path, ...],
) -> list[ProbeLabel]:
    labels: list[ProbeLabel] = []
    frame_ids = {frame.frame_id for frame in frames}
    if paths is None:
        label_paths: tuple[Path, ...] = ()
    elif isinstance(paths, Path):
        label_paths = (paths,)
    else:
        label_paths = tuple(paths)
    for path in label_paths:
        if not path.is_file():
            continue
        payload = _load_json(path)
        for item in payload.get("labels") or []:
            label = _label_from_payload(item, private=True)
            if label.frame_id in frame_ids:
                labels.append(label)
    labels.extend(
        _derive_resolved_contrast_labels(
            contrast_run_dirs=contrast_run_dirs,
            frame_ids=frame_ids,
        )
    )
    unique: dict[tuple[str, str], ProbeLabel] = {}
    for label in labels:
        unique.setdefault((label.frame_id, label.object_id), label)
    return list(unique.values())


def load_predictions(path: Path | None) -> dict[str, dict[str, dict[str, Any]]]:
    if path is None or not path.is_file():
        return {}
    payload = _load_json(path)
    rows = payload.get("predictions") or payload.get("runs") or []
    predictions: dict[str, dict[str, dict[str, Any]]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        variant_id = str(row.get("variant_id") or "baseline_json")
        frame_id = str(row.get("frame_id") or "")
        if not frame_id:
            continue
        response = row.get("response")
        if response is None:
            response = row.get("output")
        if isinstance(response, str):
            response = _json_object_from_text(response)
        if not isinstance(response, dict):
            response = {"schema": RESPONSE_SCHEMA, "candidates": []}
        predictions.setdefault(variant_id, {})[frame_id] = response
    return predictions


def score_variant(
    *,
    variant_id: str,
    frames: list[ObservationFrame],
    labels: list[ProbeLabel],
    predictions: dict[str, dict[str, Any]],
    threshold: int,
) -> dict[str, Any]:
    labels_by_frame: dict[str, list[ProbeLabel]] = {}
    for label in labels:
        labels_by_frame.setdefault(label.frame_id, []).append(label)

    evaluated_frames = []
    strict_unique: set[str] = set()
    coarse_unique: set[str] = set()
    diagnostic_unique: set[str] = set()
    duplicate_count = 0
    schema_failure_count = 0
    failure_counts = {key: 0 for key in FAILURE_CLASSES}
    candidate_count = 0

    for frame in frames:
        response = predictions.get(frame.frame_id) or {"schema": RESPONSE_SCHEMA, "candidates": []}
        normalized = normalize_response(response, frame=frame)
        schema_errors = normalized["schema_errors"]
        if schema_errors:
            schema_failure_count += len(schema_errors)
            failure_counts["schema_failure"] += len(schema_errors)
        frame_labels = labels_by_frame.get(frame.frame_id, [])
        frame_scores = []
        for index, candidate in enumerate(normalized["candidates"]):
            candidate_count += 1
            score = score_candidate(candidate, frame_labels)
            score["rank"] = index + 1
            frame_scores.append(score)
            matched_id = str(score.get("matched_object_id") or "")
            if score["coarse_confirmable"] and matched_id:
                if matched_id in diagnostic_unique:
                    duplicate_count += 1
                diagnostic_unique.add(matched_id)
            if index > 0:
                continue
            if score["strict_bbox_confirmable"] and matched_id:
                if matched_id in strict_unique:
                    duplicate_count += 1
                strict_unique.add(matched_id)
            if score["coarse_confirmable"] and matched_id:
                if matched_id in coarse_unique:
                    duplicate_count += 1
                coarse_unique.add(matched_id)
            if not score["strict_bbox_confirmable"] and not score["coarse_confirmable"]:
                reason = str(score.get("failure_class") or "")
                if reason in failure_counts:
                    failure_counts[reason] += 1
        if not frame_labels:
            failure_counts["missing_private_label"] += 1
        evaluated_frames.append(
            {
                "frame_id": frame.frame_id,
                "source_observation_id": frame.source_observation_id,
                "candidate_count": len(normalized["candidates"]),
                "schema_errors": schema_errors,
                "label_count": len(frame_labels),
                "scores": frame_scores,
            }
        )

    strict_count = len(strict_unique)
    coarse_count = len(coarse_unique)
    return {
        "variant_id": variant_id,
        "candidate_count": candidate_count,
        "schema_failure_count": schema_failure_count,
        "failure_class_counts": failure_counts,
        "strict_bbox_unique_confirmable_count": strict_count,
        "coarse_unique_confirmable_count": coarse_count,
        "unique_confirmable_count": coarse_count,
        "duplicate_count": duplicate_count,
        "diagnostic_candidate_unique_confirmable_count": len(diagnostic_unique),
        "live_like_top_candidate": {
            "threshold": threshold,
            "strict_bbox_unique_confirmable_count": strict_count,
            "coarse_unique_confirmable_count": coarse_count,
            "strict_bbox_threshold_met": strict_count >= threshold,
            "coarse_threshold_met": coarse_count >= threshold,
        },
        "evaluated_frames": evaluated_frames,
    }


def normalize_response(response: dict[str, Any], *, frame: ObservationFrame) -> dict[str, Any]:
    errors = []
    if response.get("schema") not in {RESPONSE_SCHEMA, "", None}:
        errors.append(f"schema mismatch: {response.get('schema')}")
    raw_candidates = response.get("candidates")
    if raw_candidates is None:
        raw_candidates = []
    if not isinstance(raw_candidates, list):
        errors.append("candidates must be a list")
        raw_candidates = []
    candidates = []
    for item in raw_candidates[:3]:
        if not isinstance(item, dict):
            errors.append("candidate must be an object")
            continue
        candidate, item_errors = _normalize_candidate(item, frame=frame)
        errors.extend(item_errors)
        if candidate:
            candidates.append(candidate)
    return {"schema_errors": errors, "candidates": candidates}


def score_candidate(candidate: dict[str, Any], labels: list[ProbeLabel]) -> dict[str, Any]:
    if not labels:
        return {
            "strict_bbox_confirmable": False,
            "coarse_confirmable": False,
            "matched_object_id": "",
            "failure_class": "missing_private_label",
            "category_match": False,
            "bbox_iou": 0.0,
            "coarse_region_match": False,
        }
    best: dict[str, Any] | None = None
    for label in labels:
        category_match = category_matches(candidate.get("category", ""), label.category)
        bbox_iou = _bbox_iou(candidate.get("bbox"), label.bbox)
        candidate_regions = set(candidate.get("coarse_regions") or [])
        label_regions = set(label.coarse_regions or ())
        coarse_region_match = bool(candidate_regions.intersection(label_regions))
        strict_confirmable = category_match and bbox_iou > 0.1
        coarse_confirmable = category_match and coarse_region_match
        score_value = (10 if strict_confirmable else 0) + (5 if coarse_confirmable else 0)
        score_value += bbox_iou
        item = {
            "strict_bbox_confirmable": strict_confirmable,
            "coarse_confirmable": coarse_confirmable,
            "matched_object_id": (
                label.object_id if strict_confirmable or coarse_confirmable else ""
            ),
            "category_match": category_match,
            "bbox_iou": round(bbox_iou, 6),
            "coarse_region_match": coarse_region_match,
            "label_category": label.category,
            "label_coarse_regions": list(label.coarse_regions),
        }
        if best is None or score_value > float(best["_score_value"]):
            item["_score_value"] = score_value
            best = item
    assert best is not None
    best.pop("_score_value", None)
    if not best["strict_bbox_confirmable"] and not best["coarse_confirmable"]:
        if not candidate.get("bbox") and not candidate.get("coarse_regions"):
            best["failure_class"] = "locality_too_coarse_or_invalid"
        elif not best["category_match"]:
            best["failure_class"] = "semantic_mismatch/unresolved"
        else:
            best["failure_class"] = "locality_too_coarse_or_invalid"
    else:
        best["failure_class"] = ""
    return best


def route_recommendation(matrix: list[dict[str, Any]]) -> str:
    strict_met = any(
        ((item.get("metrics") or {}).get("live_like_top_candidate") or {}).get(
            "strict_bbox_threshold_met"
        )
        for item in matrix
    )
    coarse_met = any(
        ((item.get("metrics") or {}).get("live_like_top_candidate") or {}).get(
            "coarse_threshold_met"
        )
        for item in matrix
    )
    if strict_met:
        return "keep_raw_fpv_baseline_only"
    if coarse_met:
        return "try_live_coarse_locality_contract"
    if any((item.get("metrics") or {}).get("candidate_count") for item in matrix):
        return "prefer_camera_grounded_labels"
    return "keep_raw_fpv_baseline_only"


def execute_provider_variant(
    *,
    variant_id: str,
    public_inputs: dict[str, Any],
    output_dir: Path,
    provider: str,
    model: str,
    timeout_s: float,
) -> tuple[str, list[dict[str, Any]], dict[str, dict[str, Any]]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    errors = []
    predictions = {}
    frames = (((public_inputs.get("variants") or {}).get(variant_id) or {}).get("frames")) or []
    api_config = _provider_config(provider)
    if api_config.get("error"):
        return "provider_config_error", [api_config["error"]], predictions
    for frame in frames:
        frame_id = str(frame.get("frame_id") or "")
        image_path = Path(str(frame.get("image_path") or ""))
        started = time.monotonic()
        try:
            prompt = render_prompt(frame, variant_id=variant_id)
            response_payload = _call_responses_api(
                base_url=str(api_config["base_url"]),
                api_key=str(api_config["api_key"]),
                model=model,
                prompt=prompt,
                image_path=image_path,
                timeout_s=timeout_s,
            )
            output_text = _responses_output_text(response_payload)
            parsed = _json_object_from_text(output_text)
            elapsed_ms = round((time.monotonic() - started) * 1000)
            predictions[frame_id] = parsed
            _write_provider_artifacts(
                output_dir,
                frame_id=frame_id,
                prompt=prompt,
                response_payload=response_payload,
                output_text=output_text,
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:  # noqa: BLE001 - provider probes should report and continue
            elapsed_ms = round((time.monotonic() - started) * 1000)
            error = {
                "frame_id": frame_id,
                "type": type(exc).__name__,
                "message": str(exc),
                "elapsed_ms": elapsed_ms,
            }
            errors.append(error)
            (output_dir / f"{_safe_filename(frame_id)}.error.json").write_text(
                json.dumps(error, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    if errors and predictions:
        return "provider_partial_error", errors, predictions
    if errors:
        return "provider_error", errors, predictions
    return "provider_ok", [], predictions


def render_prompt(frame_payload: dict[str, Any], *, variant_id: str) -> str:
    contract = (
        "Return only strict JSON with schema raw_fpv_probe_response_v1. "
        "Return at most three candidates. Each candidate must include "
        "source_observation_id, category, evidence_note, confidence, and locality. "
        "locality may include bbox as normalized [x,y,width,height] and must include "
        "coarse_region from the fixed 3x3 screen grid when bbox is uncertain. "
        "Allowed coarse_region values: "
        + ", ".join(SCREEN_GRID_REGIONS)
        + ". Allowed surface_hint values: "
        + ", ".join(SURFACE_HINTS)
        + ". Do not include markdown, private labels, object handles, fixture ids, "
        "world-label detections, detector outputs, or cleanup action commands."
    )
    target_text = "; ".join(RAW_FPV_HIGH_CONFIDENCE_TARGETS)
    context = frame_payload.get("semantic_map_context") or {}
    semantic_text = ""
    if variant_id == "skill_json_semantic_map":
        semantic_text = (
            "\nCompressed public planning context, not executable handles: "
            + json.dumps(context, sort_keys=True)
        )
    return (
        f"{contract}\nObservation: {frame_payload.get('source_observation_id')} "
        f"at waypoint {frame_payload.get('waypoint_id') or 'unknown'}.\n"
        f"Look only for current-frame cleanup objects: {RAW_FPV_CATEGORY_HINT}. "
        f"Prioritize: {target_text}.{semantic_text}\n"
        'Output shape: {"schema":"raw_fpv_probe_response_v1",'
        '"source_observation_id":"...","candidates":[{"source_observation_id":"...",'
        '"category":"book","evidence_note":"visible book on lower shelf",'
        '"confidence":0.72,"locality":{"bbox":[0.1,0.2,0.3,0.4],'
        '"coarse_region":"lower_left","surface_hint":"shelf"}}]}'
    )


def render_html_report(report: dict[str, Any]) -> str:
    rows = []
    for item in report.get("matrix") or []:
        metrics = item.get("metrics") or {}
        live_like = metrics.get("live_like_top_candidate") or {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('variant_id') or ''))}</td>"
            f"<td>{html.escape(str(item.get('execution_status') or ''))}</td>"
            f"<td>{metrics.get('candidate_count', 0)}</td>"
            f"<td>{metrics.get('strict_bbox_unique_confirmable_count', 0)}</td>"
            f"<td>{metrics.get('coarse_unique_confirmable_count', 0)}</td>"
            f"<td>{metrics.get('duplicate_count', 0)}</td>"
            f"<td>{html.escape(str(live_like.get('coarse_threshold_met', False)))}</td>"
            "</tr>"
        )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>RAW-FPV Perception Probe</title>"
        "<style>body{font-family:sans-serif;max-width:1100px;margin:32px auto;padding:0 16px;}"
        "table{border-collapse:collapse;width:100%;}td,th{border:1px solid #ccc;padding:6px;}"
        "th{text-align:left;background:#f4f4f4;}code{background:#f4f4f4;padding:2px 4px;}"
        "</style></head><body>"
        "<h1>RAW-FPV Perception Probe</h1>"
        f"<p>Status: <code>{html.escape(str(report.get('status') or ''))}</code></p>"
        "<p>Route recommendation: <code>"
        f"{html.escape(str(report.get('route_recommendation') or ''))}</code></p>"
        f"<p>Frames: {report.get('frame_count', 0)}; labels: {report.get('label_count', 0)}; "
        f"private labels: {report.get('private_label_count', 0)}; "
        f"missing label frames: {report.get('missing_label_frame_count', 0)}</p>"
        "<table><thead><tr><th>Variant</th><th>Execution</th><th>Candidates</th>"
        "<th>Strict unique</th><th>Coarse unique</th><th>Duplicates</th>"
        "<th>Coarse threshold met</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        "<h2>Privacy</h2><pre>"
        + html.escape(json.dumps(report.get("privacy") or {}, indent=2, sort_keys=True))
        + "</pre></body></html>"
    )


def _collect_frames_from_run_dir(run_dir: Path, *, source_kind: str) -> list[ObservationFrame]:
    run_id = _run_id_for_path(run_dir)
    raw_items: dict[str, dict[str, Any]] = {}
    for item in _raw_observations_from_json_artifacts(run_dir):
        raw_items.setdefault(str(item.get("observation_id") or ""), item)
    for item in _raw_observations_from_codex_events(run_dir):
        raw_items.setdefault(str(item.get("observation_id") or ""), item)
    for item in _raw_observations_from_robot_view_files(run_dir):
        raw_items.setdefault(str(item.get("observation_id") or ""), item)
    frames = []
    for observation_id in sorted(raw_items):
        item = raw_items[observation_id]
        image_artifacts = item.get("image_artifacts") or {}
        image_value = str(image_artifacts.get("fpv") or item.get("fpv_image") or "")
        image_path = _resolve_artifact_path(run_dir, image_value)
        if not image_path.is_file():
            continue
        width, height = _image_dimensions(image_path)
        frame_id = f"{run_id}/{observation_id}"
        frames.append(
            ObservationFrame(
                frame_id=frame_id,
                source_run_id=run_id,
                source_kind=source_kind,
                source_observation_id=observation_id,
                waypoint_id=str(item.get("waypoint_id") or ""),
                room_id=str(item.get("room_id") or ""),
                image_path=image_path,
                image_artifact=image_value,
                width=width,
                height=height,
                image_sha256=hashlib.sha256(image_path.read_bytes()).hexdigest(),
            )
        )
    return frames


def _raw_observations_from_json_artifacts(run_dir: Path) -> list[dict[str, Any]]:
    observations = []
    for name in ("raw_fpv_observations.json", "agent_view.json", "run_result.json"):
        path = run_dir / name
        if not path.is_file():
            continue
        payload = _load_json(path)
        observations.extend(
            item
            for item in payload.get("raw_fpv_observations") or []
            if isinstance(item, dict) and item.get("observation_id")
        )
        agent_view = payload.get("agent_view") or {}
        observations.extend(
            item
            for item in agent_view.get("raw_fpv_observations") or []
            if isinstance(item, dict) and item.get("observation_id")
        )
    return observations


def _raw_observations_from_codex_events(run_dir: Path) -> list[dict[str, Any]]:
    observations = []
    for path in sorted(run_dir.glob("codex-events*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                item = event.get("item") or {}
                if item.get("type") != "mcp_tool_call" or item.get("tool") != "observe":
                    continue
                if event.get("type") != "item.completed":
                    continue
                payload = _mcp_text_result_json(item.get("result") or {})
                raw = (payload.get("raw_fpv_observation") or {}) if payload else {}
                if raw.get("observation_id"):
                    observations.append(raw)
    return observations


def _raw_observations_from_robot_view_files(run_dir: Path) -> list[dict[str, Any]]:
    robot_views = run_dir / "robot_views"
    if not robot_views.is_dir():
        return []
    observations = []
    pattern = re.compile(r"(?P<label>\d+_raw_fpv_(?P<num>\d{3}))\.fpv\.png$")
    for path in sorted(robot_views.glob("*_raw_fpv_*.fpv.png")):
        match = pattern.search(path.name)
        if not match:
            continue
        observation_id = f"raw_fpv_{match.group('num')}"
        observations.append(
            {
                "observation_id": observation_id,
                "waypoint_id": "",
                "room_id": "generated_area",
                "image_artifacts": {"fpv": f"robot_views/{path.name}"},
                "robot_view_label": match.group("label"),
            }
        )
    return observations


def _derive_resolved_contrast_labels(
    *,
    contrast_run_dirs: tuple[Path, ...],
    frame_ids: set[str],
) -> list[ProbeLabel]:
    labels = []
    for run_dir in contrast_run_dirs:
        run_id = _run_id_for_path(run_dir.expanduser())
        for payload_name in ("run_result.json", "agent_view.json"):
            path = run_dir / payload_name
            if not path.is_file():
                continue
            payload = _load_json(path)
            for item in payload.get("model_declared_observations") or []:
                if item.get("grounding_status") != "resolved":
                    continue
                observation_id = str(item.get("source_observation_id") or "")
                frame_id = f"{run_id}/{observation_id}"
                if frame_id not in frame_ids:
                    continue
                bbox = _bbox_tuple((item.get("image_region") or {}).get("value"))
                labels.append(
                    ProbeLabel(
                        frame_id=frame_id,
                        source_observation_id=observation_id,
                        object_id=str(item.get("object_id") or ""),
                        category=str(item.get("category") or "object"),
                        bbox=bbox,
                        coarse_regions=tuple(_coarse_regions_from_bbox(bbox)),
                        surface_hint="unknown",
                        label_source="resolved_camera_label_contrast",
                        private=False,
                    )
                )
    return labels


def _label_from_payload(item: dict[str, Any], *, private: bool) -> ProbeLabel:
    bbox = _bbox_tuple(item.get("bbox") or item.get("image_bbox"))
    coarse_regions = tuple(
        region
        for region in (item.get("coarse_regions") or _coarse_regions_from_bbox(bbox))
        if region in SCREEN_GRID_REGIONS
    )
    surface_hint = str(item.get("surface_hint") or "unknown")
    if surface_hint not in SURFACE_HINTS:
        surface_hint = "unknown"
    return ProbeLabel(
        frame_id=str(item.get("frame_id") or ""),
        source_observation_id=str(item.get("source_observation_id") or ""),
        object_id=str(item.get("object_id") or ""),
        category=str(item.get("category") or "object"),
        bbox=bbox,
        coarse_regions=coarse_regions,
        surface_hint=surface_hint,
        label_source=str(item.get("label_source") or "private_manifest"),
        private=private,
    )


def _prompt_payload_for_frame(
    frame: ObservationFrame,
    *,
    semantic_context: dict[str, Any],
) -> dict[str, Any]:
    payload = frame.public_payload()
    payload["image_path"] = str(frame.image_path)
    payload["semantic_map_context"] = semantic_context
    payload["needs_confirm"] = True
    payload["private_truth_included"] = False
    payload["executable_prior_handles_included"] = False
    return payload


def _compressed_semantic_context(
    frame: ObservationFrame,
    *,
    semantic_map_prior: dict[str, Any],
) -> dict[str, Any]:
    categories = set()
    historical_directions = []
    for item in semantic_map_prior.get("observed_objects") or []:
        if item.get("source_observation_id") == frame.source_observation_id:
            category = str(item.get("category") or "")
            if category:
                categories.add(category.lower())
    for anchor in semantic_map_prior.get("public_semantic_anchors") or []:
        if anchor.get("waypoint_id") != frame.waypoint_id:
            continue
        category = str(anchor.get("category") or "")
        if category and category not in {"room_area", "observation_waypoint"}:
            categories.add(category.lower())
        pose = anchor.get("pose") or {}
        if "yaw" in pose:
            historical_directions.append({"yaw": pose.get("yaw")})
    if not categories:
        categories.update(("food", "dish", "book", "linen", "toy", "electronics", "pillow"))
    return {
        "waypoint_id": frame.waypoint_id,
        "area": frame.room_id or "generated_area",
        "likely_categories": sorted(categories)[:10],
        "historical_observation_direction": historical_directions[:2],
        "needs_confirm": True,
        "non_executable_planning_context_only": True,
    }


def _normalize_candidate(
    item: dict[str, Any],
    *,
    frame: ObservationFrame,
) -> tuple[dict[str, Any], list[str]]:
    errors = []
    observation_id = str(item.get("source_observation_id") or "")
    if observation_id and observation_id != frame.source_observation_id:
        errors.append("source_observation_id does not match frame")
    category = str(item.get("category") or "").strip().lower()
    if not category:
        errors.append("category is required")
    evidence_note = str(item.get("evidence_note") or "").strip()
    if not evidence_note:
        errors.append("evidence_note is required")
    locality = item.get("locality") or {}
    image_region = item.get("image_region") or {}
    bbox = _bbox_tuple(locality.get("bbox") or image_region.get("value") or item.get("bbox"))
    coarse = locality.get("coarse_region") or locality.get("screen_grid_region")
    coarse_regions = []
    if str(coarse or "") in SCREEN_GRID_REGIONS:
        coarse_regions.append(str(coarse))
    coarse_regions.extend(region for region in _coarse_regions_from_bbox(bbox) if region)
    surface_hint = str(locality.get("surface_hint") or "unknown")
    if surface_hint not in SURFACE_HINTS:
        surface_hint = "unknown"
    try:
        confidence = float(item.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
        errors.append("confidence must be numeric")
    candidate = {
        "source_observation_id": observation_id or frame.source_observation_id,
        "category": category,
        "evidence_note": evidence_note,
        "confidence": confidence,
        "bbox": bbox,
        "coarse_regions": sorted(set(coarse_regions)),
        "surface_hint": surface_hint,
    }
    if not bbox and not coarse_regions:
        errors.append("locality must include bbox or coarse_region")
    return candidate, errors


def category_matches(candidate: str, label: str) -> bool:
    candidate_norm = _category_norm(candidate)
    label_norm = _category_norm(label)
    if candidate_norm == label_norm:
        return True
    families = {
        "dish": {"dish", "plate", "bowl", "cup", "mug"},
        "food": {"food", "potato", "apple", "fruit", "vegetable"},
        "electronics": {"electronics", "remote", "remotecontrol", "phone", "laptop"},
        "linen": {"linen", "pillow", "towel", "blanket", "cloth"},
        "toy": {"toy"},
        "book": {"book"},
        "pillow": {"pillow"},
    }
    return any(candidate_norm in members and label_norm in members for members in families.values())


def _category_norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _bbox_iou(
    first: tuple[float, float, float, float] | None,
    second: tuple[float, float, float, float] | None,
) -> float:
    if first is None or second is None:
        return 0.0
    ax, ay, aw, ah = first
    bx, by, bw, bh = second
    ax2, ay2 = ax + aw, ay + ah
    bx2, by2 = bx + bw, by + bh
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    intersection = iw * ih
    union = aw * ah + bw * bh - intersection
    if union <= 0:
        return 0.0
    return intersection / union


def _bbox_tuple(value: Any) -> tuple[float, float, float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return None
    try:
        x, y, width, height = (float(item) for item in value)
    except (TypeError, ValueError):
        return None
    if width <= 0 or height <= 0:
        return None
    return (
        max(0.0, min(1.0, x)),
        max(0.0, min(1.0, y)),
        max(0.0, min(1.0, width)),
        max(0.0, min(1.0, height)),
    )


def _coarse_regions_from_bbox(
    bbox: tuple[float, float, float, float] | None,
) -> list[str]:
    if bbox is None:
        return []
    x, y, width, height = bbox
    center_x = max(0.0, min(0.999, x + width / 2.0))
    center_y = max(0.0, min(0.999, y + height / 2.0))
    col = 0 if center_x < 1 / 3 else 1 if center_x < 2 / 3 else 2
    row = 0 if center_y < 1 / 3 else 1 if center_y < 2 / 3 else 2
    return [SCREEN_GRID_REGIONS[row * 3 + col]]


def _call_responses_api(
    *,
    base_url: str,
    api_key: str,
    model: str,
    prompt: str,
    image_path: Path,
    timeout_s: float,
) -> dict[str, Any]:
    image_bytes = image_path.read_bytes()
    mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    image_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    payload = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": image_url},
                ],
            }
        ],
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + "/responses",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "roboclaws-raw-fpv-perception-probe/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            message = str((payload.get("error") or {}).get("message") or exc.reason)
        except Exception:
            message = str(exc.reason)
        raise RuntimeError(f"responses API returned HTTP {exc.code}: {message}") from exc


def _provider_config(provider: str) -> dict[str, Any]:
    if provider != "codex-env":
        return {"error": {"type": "unsupported_provider", "provider": provider}}
    base_url = os.environ.get("CODEX_BASE_URL", DEFAULT_CODEX_BASE_URL)
    api_key = os.environ.get("CODEX_API_KEY", "")
    if not api_key:
        return {"error": {"type": "missing_env", "env": "CODEX_API_KEY"}}
    return {"base_url": base_url, "api_key": api_key}


def _write_provider_artifacts(
    output_dir: Path,
    *,
    frame_id: str,
    prompt: str,
    response_payload: dict[str, Any],
    output_text: str,
    elapsed_ms: int,
) -> None:
    stem = _safe_filename(frame_id)
    (output_dir / f"{stem}.prompt.txt").write_text(prompt + "\n", encoding="utf-8")
    (output_dir / f"{stem}.response.json").write_text(
        json.dumps(response_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / f"{stem}.output.txt").write_text(output_text + "\n", encoding="utf-8")
    (output_dir / f"{stem}.meta.json").write_text(
        json.dumps({"elapsed_ms": elapsed_ms}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _responses_output_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return str(payload["output_text"])
    parts = []
    for item in payload.get("output") or []:
        for content in (item or {}).get("content") or []:
            if isinstance(content, dict):
                value = content.get("text") or content.get("content") or ""
                if isinstance(value, str):
                    parts.append(value)
    return "\n".join(parts)


def _json_object_from_text(text: str) -> dict[str, Any]:
    stripped = str(text or "").strip()
    if not stripped:
        return {"schema": RESPONSE_SCHEMA, "candidates": []}
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", stripped, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return {"schema": RESPONSE_SCHEMA, "candidates": []}


def _selected_variants(value: str) -> tuple[str, ...]:
    if value == "both":
        return ("baseline_json", "skill_json_semantic_map")
    return (value,)


def _probe_status(
    matrix: list[dict[str, Any]],
    *,
    labels: list[ProbeLabel],
    provider: str,
) -> str:
    if not labels:
        return "partial"
    if any(str(item.get("execution_status") or "") == "provider_config_error" for item in matrix):
        return "blocked_needs_decision"
    if provider == "offline" and not any(
        (item.get("metrics") or {}).get("candidate_count") for item in matrix
    ):
        return "partial"
    return "success"


def _missing_label_frame_count(frames: list[ObservationFrame], labels: list[ProbeLabel]) -> int:
    labeled = {item.frame_id for item in labels}
    return sum(1 for frame in frames if frame.frame_id not in labeled)


def _contains_private_label_leak(public_inputs: dict[str, Any], labels: list[ProbeLabel]) -> bool:
    text = json.dumps(public_inputs, sort_keys=True)
    return any(label.private and label.object_id and label.object_id in text for label in labels)


def _contains_executable_prior_handle(public_inputs: dict[str, Any]) -> bool:
    text = json.dumps(public_inputs, sort_keys=True)
    return bool(re.search(r"\b(observed_\d+|anchor_fixture_\d+)\b", text))


def _console_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "report": report.get("artifacts", {}).get("html_report"),
        "report_json": str(Path(str(report.get("output_dir", ""))) / "report.json"),
        "frame_count": report.get("frame_count"),
        "label_count": report.get("label_count"),
        "route_recommendation": report.get("route_recommendation"),
    }


def _mcp_text_result_json(result: dict[str, Any]) -> dict[str, Any]:
    for content in result.get("content") or []:
        if not isinstance(content, dict) or content.get("type") != "text":
            continue
        try:
            return json.loads(str(content.get("text") or ""))
        except json.JSONDecodeError:
            return {}
    return {}


def _image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return image.size


def _resolve_artifact_path(run_dir: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return run_dir / path


def _run_id_for_path(path: Path) -> str:
    parts = [part for part in path.parts[-4:] if part not in {"output", "household"}]
    return _safe_filename("-".join(parts))


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "item"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_json_if_exists(path: Path) -> dict[str, Any]:
    if path and path.is_file():
        return _load_json(path)
    return {}


def _output_run_dir(output_root: Path, run_id: str) -> Path:
    if run_id:
        return output_root / _safe_filename(run_id)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    return output_root / stamp


def _utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


if __name__ == "__main__":
    raise SystemExit(main())
