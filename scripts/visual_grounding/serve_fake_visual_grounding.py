#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.household.visual_grounding import (  # noqa: E402
    VISUAL_GROUNDING_RESPONSE_SCHEMA,
    validate_visual_grounding_request,
    visual_grounding_failure_response,
)

ENDPOINT = "/v1/visual-grounding/candidates"
DETECTOR_ONLY_PIPELINES = frozenset(
    {
        "fake-http",
        "contract-fake",
        "grounding-dino",
        "yoloe",
        "yolo-world",
        "omdet-turbo",
    }
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Serve a deterministic fake visual-grounding HTTP endpoint."
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18880)
    parser.add_argument("--mode", choices=("success", "failure"), default="success")
    parser.add_argument("--latency-ms", type=int, default=3)
    return parser.parse_args(argv)


def make_handler(*, mode: str, latency_ms: int) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "roboclaws-fake-visual-grounding/1.0"

        def do_POST(self) -> None:  # noqa: N802
            if self.path != ENDPOINT:
                self.send_error(404, "not found")
                return
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                validate_visual_grounding_request(payload)
            except Exception as exc:
                self._write_json(
                    400,
                    visual_grounding_failure_response(
                        pipeline_id="fake-http",
                        reason="bad_request",
                        message=str(exc),
                        latency_ms=0,
                    ),
                )
                return

            if latency_ms > 0:
                time.sleep(latency_ms / 1000)

            pipeline_id = str((payload.get("pipeline_request") or {}).get("pipeline_id") or "")
            if mode == "failure":
                self._write_json(
                    200,
                    visual_grounding_failure_response(
                        pipeline_id=pipeline_id or "fake-http",
                        reason="fake_failure",
                        message="fake visual grounding failure requested",
                        latency_ms=latency_ms,
                    ),
                )
                return

            self._write_json(
                200,
                contract_fake_visual_grounding_response(
                    payload=payload,
                    pipeline_id=pipeline_id or "fake-http",
                    latency_ms=latency_ms,
                ),
            )

        def log_message(self, _format: str, *_args: Any) -> None:
            return

        def _write_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def contract_fake_visual_grounding_response(
    *,
    payload: dict[str, Any],
    pipeline_id: str,
    latency_ms: int,
) -> dict[str, Any]:
    if pipeline_id not in DETECTOR_ONLY_PIPELINES:
        return visual_grounding_failure_response(
            pipeline_id=pipeline_id,
            reason="unsupported_pipeline",
            message=(
                f"visual grounding pipeline '{pipeline_id}' is not in the detector-only "
                "contract fake catalog"
            ),
            latency_ms=latency_ms,
        )
    pipeline = _fake_pipeline_result(
        payload=payload,
        pipeline_id=pipeline_id,
        latency_ms=latency_ms,
    )
    return {
        "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
        "status": "ok",
        "pipeline": pipeline["pipeline"],
        "candidates": pipeline["candidates"],
        "diagnostics": pipeline["diagnostics"],
    }


def contract_fake_stages_for_pipeline(pipeline_id: str, latency_ms: int) -> list[dict[str, Any]]:
    return _stages_for_pipeline(pipeline_id, latency_ms)


def _fake_pipeline_result(
    *,
    payload: dict[str, Any],
    pipeline_id: str,
    latency_ms: int,
) -> dict[str, Any]:
    stages = _stages_for_pipeline(pipeline_id, latency_ms)
    proposals = _proposals_for_pipeline(payload, pipeline_id)
    return {
        "pipeline": {"pipeline_id": pipeline_id, "stages": stages},
        "candidates": proposals,
        "diagnostics": {
            "schema": "visual_grounding_diagnostics_v1",
            "diagnostic_mode": "deterministic_contract_fake",
            "raw_proposals": proposals,
            "rejected_proposals": [],
            "private_truth_included": False,
        },
    }


def _stages_for_pipeline(pipeline_id: str, latency_ms: int) -> list[dict[str, Any]]:
    return [
        _stage(
            name="proposer",
            producer_id=pipeline_id,
            model_id=_model_id_for_producer(pipeline_id),
            latency_ms=latency_ms,
        ),
    ]


def _stage(*, name: str, producer_id: str, model_id: str, latency_ms: int) -> dict[str, Any]:
    return {
        "stage": name,
        "producer_id": producer_id,
        "model_id": model_id,
        "version": "contract-fake-v1",
        "status": "ok",
        "latency_ms": latency_ms,
    }


def _model_id_for_producer(producer_id: str) -> str:
    return {
        "fake-http": "deterministic-public-metadata",
        "grounding-dino": "contract-stub:IDEA-Research/grounding-dino-tiny",
        "yoloe": "contract-stub:ultralytics/yoloe",
        "yolo-world": "contract-stub:ultralytics/yolo-world",
        "omdet-turbo": "contract-stub:omlab/omdet-turbo-swin-tiny-hf",
    }.get(producer_id, f"contract-stub:{producer_id}")


def _proposals_for_pipeline(payload: dict[str, Any], pipeline_id: str) -> list[dict[str, Any]]:
    if pipeline_id == "grounding-dino":
        return _grounding_dino_contract_proposals(payload)
    if pipeline_id == "yoloe":
        return _yoloe_contract_proposals(payload)
    return _generic_fake_candidates(payload)


def _grounding_dino_contract_proposals(payload: dict[str, Any]) -> list[dict[str, Any]]:
    category = _positive_category_for_request(payload)
    if not category:
        return []
    return [
        _candidate(
            payload=payload,
            category=category,
            bbox=_positive_bbox_for_category(category),
            confidence=0.78,
            note="contract fake Grounding DINO proposal from public frame metadata",
        )
    ]


def _yoloe_contract_proposals(payload: dict[str, Any]) -> list[dict[str, Any]]:
    category = _positive_category_for_request(payload) or _category_for_request(payload)
    proposals = [
        _candidate(
            payload=payload,
            category=category,
            bbox=_positive_bbox_for_category(category),
            confidence=0.69,
            note="contract fake YOLOE proposal from public frame metadata",
        )
    ]
    if "living" in str(payload.get("room_id") or ""):
        duplicate = dict(proposals[0])
        duplicate["confidence"] = 0.52
        duplicate["evidence_note"] = "contract fake YOLOE near-duplicate proposal"
        proposals.append(duplicate)
    return proposals


def _generic_fake_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    category = _category_for_request(payload)
    return [
        _candidate(
            payload=payload,
            category=category,
            bbox=[0.42, 0.45, 0.18, 0.16],
            confidence=0.74,
            note=f"fake HTTP candidate from waypoint {payload.get('waypoint_id', '')}",
        )
    ]


def _positive_category_for_request(payload: dict[str, Any]) -> str:
    hints = [str(item) for item in payload.get("category_hints") or [] if str(item)]
    room_id = str(payload.get("room_id") or "")
    observation_id = str(payload.get("observation_id") or "")
    if "negative" in observation_id:
        return ""
    if "kitchen" in room_id and "dish" in hints:
        return "dish"
    if "living" in room_id and "toy" in hints:
        return "toy"
    if "book" in observation_id and "book" in hints:
        return "book"
    return ""


def _positive_bbox_for_category(category: str) -> list[float]:
    return {
        "dish": [0.40, 0.42, 0.22, 0.18],
        "toy": [0.39, 0.43, 0.22, 0.18],
        "book": [0.38, 0.40, 0.20, 0.16],
    }.get(category, [0.42, 0.45, 0.18, 0.16])


def _candidate(
    *,
    payload: dict[str, Any],
    category: str,
    bbox: list[float],
    confidence: float,
    note: str,
) -> dict[str, Any]:
    fixture_id = _destination_fixture_for_category(payload, category)
    return {
        "category": category,
        "image_region": {"type": "bbox", "value": bbox},
        "confidence": confidence,
        "evidence_note": note,
        "source_fixture_id": _source_fixture_for_request(payload),
        "destination_hint": {
            "candidate_fixture_id": fixture_id,
            "confidence": 0.51,
        },
    }


def _category_for_request(payload: dict[str, Any]) -> str:
    hints = [str(item) for item in payload.get("category_hints") or [] if str(item)]
    room_id = str(payload.get("room_id") or "")
    if "kitchen" in room_id and "dish" in hints:
        return "dish"
    if "work" in room_id and "food" in hints:
        return "food"
    if "living" in room_id and "toy" in hints:
        return "toy"
    return hints[0] if hints else "object"


def _destination_fixture_for_category(payload: dict[str, Any], category: str) -> str:
    fixtures = list(payload.get("fixture_hints") or [])
    target_terms = {
        "dish": ("sink",),
        "food": ("fridge", "refrigerator"),
        "book": ("shelf", "bookshelf"),
        "toy": ("toy", "sofa"),
        "electronics": ("tvstand", "tv stand"),
        "pillow": ("bed", "sofa"),
        "linen": ("hamper", "laundry"),
    }
    terms = target_terms.get(category, ())
    for fixture in fixtures:
        text = " ".join(
            str(fixture.get(key) or "") for key in ("fixture_id", "category", "name")
        ).lower()
        if any(term in text for term in terms):
            return str(fixture.get("fixture_id") or "")
    return str((fixtures[0] if fixtures else {}).get("fixture_id") or "")


def _source_fixture_for_request(payload: dict[str, Any]) -> str:
    fixtures = list(payload.get("fixture_hints") or [])
    return str((fixtures[0] if fixtures else {}).get("fixture_id") or "")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    server = ThreadingHTTPServer(
        (args.host, args.port),
        make_handler(mode=args.mode, latency_ms=args.latency_ms),
    )
    print(f"fake visual grounding service: http://{args.host}:{args.port}{ENDPOINT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
