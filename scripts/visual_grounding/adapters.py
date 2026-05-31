from __future__ import annotations

import base64
import importlib.util
import io
import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from PIL import Image

from roboclaws.molmo_cleanup.visual_grounding import (
    VISUAL_GROUNDING_RESPONSE_SCHEMA,
    validate_visual_grounding_response,
)
from scripts.visual_grounding.serve_fake_visual_grounding import (
    contract_fake_stages_for_pipeline,
    contract_fake_visual_grounding_response,
)

ADAPTER_MODE_AUTO = "auto"
ADAPTER_MODE_CONTRACT_FAKE = "contract-fake"
ADAPTER_MODE_REAL = "real"
ADAPTER_MODE_UNAVAILABLE = "unavailable"
CONTRACT_FAKE_PIPELINE_ID = "contract-fake"
FAKE_HTTP_PIPELINE_ID = "fake-http"
REAL_ROUTER_PIPELINE_ID = "real-router"
ADAPTER_CATALOG_SCHEMA = "visual_grounding_adapter_catalog_v1"
_MIMO_OPENAI_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
_PROVIDER_PREFIXED_HOSTED_VLM_MODEL_IDS = (
    "xiaomi/mimo-v2-omni",
    "vertex_ai/gemini-3.1-flash-lite-preview",
    "vertex_ai/gemini-3-flash-preview",
    "tongyi/qwen3-vl-flash",
    "tongyi/qwen3-vl-plus",
    "siliconflow/Qwen/Qwen3-VL-8B-Instruct",
)
_HOSTED_VLM_MODEL_IDS = {
    "mimo-v2-omni": "mimo-v2-omni",
    "qwen3-vl": "Qwen/Qwen3-VL-8B-Instruct",
    **{model_id: model_id for model_id in _PROVIDER_PREFIXED_HOSTED_VLM_MODEL_IDS},
}


@dataclass(frozen=True)
class AdapterSpec:
    producer_id: str
    role: str
    status: str
    model_id: str
    optional_extra: str
    setup_hint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "producer_id": self.producer_id,
            "role": self.role,
            "status": self.status,
            "model_id": self.model_id,
            "optional_extra": self.optional_extra,
            "runtime": adapter_runtime_status(self.producer_id),
            "setup_hint": self.setup_hint,
        }


ADAPTER_SPECS: dict[str, AdapterSpec] = {
    "fake-http": AdapterSpec(
        producer_id="fake-http",
        role="contract_fake",
        status="available",
        model_id="deterministic-public-metadata",
        optional_extra="",
        setup_hint="Built in for CI-safe visual-grounding contract tests.",
    ),
    "grounding-dino": AdapterSpec(
        producer_id="grounding-dino",
        role="proposer",
        status="adapter_unavailable",
        model_id="IDEA-Research/grounding-dino-tiny",
        optional_extra="visual-grounding-dino",
        setup_hint=(
            "Run the sidecar adapter with --adapter-mode real after explicitly installing "
            "Transformers, Torch, and the selected Grounding DINO model weights."
        ),
    ),
    "yoloe": AdapterSpec(
        producer_id="yoloe",
        role="proposer",
        status="adapter_unavailable",
        model_id="yoloe-11s-seg.pt",
        optional_extra="visual-grounding-yoloe",
        setup_hint=(
            "Run the sidecar adapter with --adapter-mode real after explicitly installing "
            "Ultralytics, the CLIP tokenizer package, and approved YOLOE weights."
        ),
    ),
    "yolo-custom": AdapterSpec(
        producer_id="yolo-custom",
        role="proposer",
        status="adapter_unavailable",
        model_id="custom-yolo-cleanup-ontology",
        optional_extra="visual-grounding-yolo-custom",
        setup_hint="Provide trained weights through an explicit sidecar setup step.",
    ),
    "mimo-v2-omni": AdapterSpec(
        producer_id="mimo-v2-omni",
        role="refiner_or_direct_producer",
        status="requires_hosted_config",
        model_id="mimo-v2-omni",
        optional_extra="",
        setup_hint=(
            "Configure MIMO_TP_KEY or VISUAL_GROUNDING_MIMO_API_KEY for the "
            "hosted OpenAI-compatible MiMo route."
        ),
    ),
    "qwen3-vl": AdapterSpec(
        producer_id="qwen3-vl",
        role="refiner_or_direct_producer",
        status="requires_hosted_or_local_config",
        model_id="Qwen/Qwen3-VL-8B-Instruct",
        optional_extra="visual-grounding-qwen3vl",
        setup_hint=(
            "Configure VISUAL_GROUNDING_QWEN_BASE_URL for a local or remote "
            "Qwen3-VL OpenAI-compatible sidecar probe."
        ),
    ),
    "xiaomi/mimo-v2-omni": AdapterSpec(
        producer_id="xiaomi/mimo-v2-omni",
        role="direct_producer",
        status="requires_hosted_config",
        model_id="xiaomi/mimo-v2-omni",
        optional_extra="",
        setup_hint=(
            "Configure VISUAL_GROUNDING_VLM_* or XM_LLM_* for the internal "
            "OpenAI-compatible aggregation route."
        ),
    ),
    "vertex_ai/gemini-3.1-flash-lite-preview": AdapterSpec(
        producer_id="vertex_ai/gemini-3.1-flash-lite-preview",
        role="direct_producer",
        status="requires_hosted_config",
        model_id="vertex_ai/gemini-3.1-flash-lite-preview",
        optional_extra="",
        setup_hint=(
            "Configure VISUAL_GROUNDING_VLM_* or XM_LLM_* for the internal "
            "OpenAI-compatible aggregation route."
        ),
    ),
    "vertex_ai/gemini-3-flash-preview": AdapterSpec(
        producer_id="vertex_ai/gemini-3-flash-preview",
        role="direct_producer",
        status="requires_hosted_config",
        model_id="vertex_ai/gemini-3-flash-preview",
        optional_extra="",
        setup_hint=(
            "Configure VISUAL_GROUNDING_VLM_* or XM_LLM_* for the internal "
            "OpenAI-compatible aggregation route."
        ),
    ),
    "tongyi/qwen3-vl-flash": AdapterSpec(
        producer_id="tongyi/qwen3-vl-flash",
        role="direct_producer",
        status="requires_hosted_config",
        model_id="tongyi/qwen3-vl-flash",
        optional_extra="",
        setup_hint=(
            "Configure VISUAL_GROUNDING_VLM_* or XM_LLM_* for the internal "
            "OpenAI-compatible aggregation route."
        ),
    ),
    "tongyi/qwen3-vl-plus": AdapterSpec(
        producer_id="tongyi/qwen3-vl-plus",
        role="direct_producer",
        status="requires_hosted_config",
        model_id="tongyi/qwen3-vl-plus",
        optional_extra="",
        setup_hint=(
            "Configure VISUAL_GROUNDING_VLM_* or XM_LLM_* for the internal "
            "OpenAI-compatible aggregation route."
        ),
    ),
    "siliconflow/Qwen/Qwen3-VL-8B-Instruct": AdapterSpec(
        producer_id="siliconflow/Qwen/Qwen3-VL-8B-Instruct",
        role="direct_producer",
        status="requires_hosted_config",
        model_id="siliconflow/Qwen/Qwen3-VL-8B-Instruct",
        optional_extra="",
        setup_hint=(
            "Configure VISUAL_GROUNDING_VLM_* or XM_LLM_* for the internal "
            "OpenAI-compatible aggregation route."
        ),
    ),
}


def visual_grounding_service_response(
    *,
    payload: dict[str, Any],
    configured_pipeline_id: str,
    adapter_mode: str,
    latency_ms: int,
) -> dict[str, Any]:
    requested_pipeline_id = request_pipeline_id(payload)
    selected_pipeline_id = effective_pipeline_id(
        configured_pipeline_id=configured_pipeline_id,
        requested_pipeline_id=requested_pipeline_id,
    )
    if not pipeline_request_is_allowed(
        configured_pipeline_id=configured_pipeline_id,
        requested_pipeline_id=requested_pipeline_id,
        effective_pipeline_id=selected_pipeline_id,
    ):
        return pipeline_mismatch_response(
            configured_pipeline_id=configured_pipeline_id,
            requested_pipeline_id=requested_pipeline_id,
        )
    if should_use_contract_fake(
        configured_pipeline_id=configured_pipeline_id,
        effective_pipeline_id=selected_pipeline_id,
        adapter_mode=adapter_mode,
    ):
        response = contract_fake_visual_grounding_response(
            payload=payload,
            pipeline_id=selected_pipeline_id,
            latency_ms=latency_ms,
        )
        return validate_visual_grounding_response(response)

    if adapter_mode == ADAPTER_MODE_REAL:
        return real_adapter_response(
            payload=payload,
            pipeline_id=selected_pipeline_id,
            latency_ms=latency_ms,
        )

    return adapter_unavailable_response(
        pipeline_id=selected_pipeline_id,
        adapter_mode=adapter_mode,
        latency_ms=latency_ms,
    )


def visual_grounding_adapter_catalog() -> dict[str, Any]:
    return {
        "schema": ADAPTER_CATALOG_SCHEMA,
        "contract_fake_pipeline_id": CONTRACT_FAKE_PIPELINE_ID,
        "real_router_pipeline_id": REAL_ROUTER_PIPELINE_ID,
        "default_pipeline_id": FAKE_HTTP_PIPELINE_ID,
        "adapter_modes": [
            ADAPTER_MODE_AUTO,
            ADAPTER_MODE_CONTRACT_FAKE,
            ADAPTER_MODE_REAL,
            ADAPTER_MODE_UNAVAILABLE,
        ],
        "adapters": [spec.as_dict() for spec in ADAPTER_SPECS.values()],
        "private_truth_included": False,
    }


def adapter_runtime_status(producer_id: str) -> dict[str, Any]:
    if producer_id == "fake-http":
        return {
            "status": "available",
            "checks": [],
            "auth_mode": "none",
            "model_weights_verified": True,
            "message": "Built-in deterministic contract adapter is available.",
        }
    if producer_id == "grounding-dino":
        checks = _module_checks("torch", "transformers")
        return _dependency_runtime_status(
            checks=checks,
            ready_message=(
                "Grounding DINO Python dependencies are importable; model weights "
                "are verified only by a real adapter run."
            ),
            missing_message=(
                "Grounding DINO real mode requires importable torch and transformers "
                "in the sidecar environment."
            ),
        )
    if producer_id in {"yoloe", "yolo-custom"}:
        checks = _module_checks("ultralytics")
        return _dependency_runtime_status(
            checks=checks,
            ready_message=(
                "Ultralytics is importable; YOLO-family weights are verified only "
                "by a real adapter run."
            ),
            missing_message=(
                f"{producer_id} real mode requires importable ultralytics in the "
                "sidecar environment."
            ),
        )
    if _is_hosted_vlm_producer(producer_id):
        return _hosted_runtime_status(producer_id)
    return {
        "status": "unknown_adapter",
        "checks": [],
        "auth_mode": "none",
        "model_weights_verified": False,
        "message": "No runtime readiness probe is registered for this adapter.",
    }


def _dependency_runtime_status(
    *,
    checks: list[dict[str, Any]],
    ready_message: str,
    missing_message: str,
) -> dict[str, Any]:
    missing = [str(item["name"]) for item in checks if not item["available"]]
    if missing:
        return {
            "status": "missing_dependency",
            "checks": checks,
            "missing_dependencies": missing,
            "auth_mode": "none",
            "model_weights_verified": False,
            "message": missing_message,
        }
    return {
        "status": "dependency_ready_model_unverified",
        "checks": checks,
        "missing_dependencies": [],
        "auth_mode": "none",
        "model_weights_verified": False,
        "message": ready_message,
    }


def _is_hosted_vlm_producer(producer_id: str) -> bool:
    return producer_id in _HOSTED_VLM_MODEL_IDS


def _hosted_vlm_spec(producer_id: str) -> AdapterSpec:
    spec = ADAPTER_SPECS.get(producer_id)
    if spec is not None:
        return spec
    model_id = _HOSTED_VLM_MODEL_IDS.get(producer_id, producer_id)
    return AdapterSpec(
        producer_id=producer_id,
        role="direct_producer",
        status="requires_hosted_config",
        model_id=model_id,
        optional_extra="",
        setup_hint=(
            "Configure VISUAL_GROUNDING_VLM_* or XM_LLM_* for an "
            "OpenAI-compatible hosted visual model route."
        ),
    )


def _hosted_runtime_status(producer_id: str) -> dict[str, Any]:
    base_url_configured = bool(_hosted_vlm_base_url(producer_id))
    api_key_configured = bool(_hosted_vlm_api_key(producer_id))
    allow_no_api_key = _bool_env("VISUAL_GROUNDING_VLM_ALLOW_NO_API_KEY")
    checks = [
        {"name": "base_url_configured", "available": base_url_configured},
        {
            "name": "api_key_or_local_no_key_policy",
            "available": api_key_configured or allow_no_api_key,
        },
    ]
    if base_url_configured and (api_key_configured or allow_no_api_key):
        return {
            "status": "configured",
            "checks": checks,
            "auth_mode": "bearer_configured" if api_key_configured else "none",
            "model_weights_verified": False,
            "message": (
                f"{producer_id} hosted route is configured; endpoint behavior is "
                "verified only by a real adapter run."
            ),
        }
    return {
        "status": "missing_config",
        "checks": checks,
        "auth_mode": "bearer_configured" if api_key_configured else "none",
        "model_weights_verified": False,
        "message": (
            f"{producer_id} hosted route requires a base URL and either a bearer "
            "key or VISUAL_GROUNDING_VLM_ALLOW_NO_API_KEY=true for a local test server."
        ),
    }


def _module_checks(*module_names: str) -> list[dict[str, Any]]:
    return [
        {
            "name": module_name,
            "available": importlib.util.find_spec(module_name) is not None,
        }
        for module_name in module_names
    ]


def request_pipeline_id(payload: dict[str, Any]) -> str:
    pipeline_request = payload.get("pipeline_request") or {}
    return str(pipeline_request.get("pipeline_id") or "").strip()


def effective_pipeline_id(
    *,
    configured_pipeline_id: str,
    requested_pipeline_id: str,
) -> str:
    configured = str(configured_pipeline_id or "").strip()
    requested = str(requested_pipeline_id or "").strip()
    if configured in {CONTRACT_FAKE_PIPELINE_ID, REAL_ROUTER_PIPELINE_ID}:
        return requested or FAKE_HTTP_PIPELINE_ID
    return configured or requested or FAKE_HTTP_PIPELINE_ID


def pipeline_request_is_allowed(
    *,
    configured_pipeline_id: str,
    requested_pipeline_id: str,
    effective_pipeline_id: str,
) -> bool:
    if configured_pipeline_id in {CONTRACT_FAKE_PIPELINE_ID, REAL_ROUTER_PIPELINE_ID}:
        return True
    if not requested_pipeline_id:
        return True
    return requested_pipeline_id == effective_pipeline_id


def should_use_contract_fake(
    *,
    configured_pipeline_id: str,
    effective_pipeline_id: str,
    adapter_mode: str,
) -> bool:
    if adapter_mode == ADAPTER_MODE_CONTRACT_FAKE:
        return True
    if adapter_mode == ADAPTER_MODE_UNAVAILABLE:
        return False
    return configured_pipeline_id == CONTRACT_FAKE_PIPELINE_ID or (
        effective_pipeline_id == FAKE_HTTP_PIPELINE_ID
    )


def real_adapter_response(
    *,
    payload: dict[str, Any],
    pipeline_id: str,
    latency_ms: int,
) -> dict[str, Any]:
    if pipeline_id.endswith("-direct"):
        producer_id = pipeline_id.removesuffix("-direct")
        if _is_hosted_vlm_producer(producer_id):
            return _hosted_vlm_direct_response(
                payload=payload,
                pipeline_id=pipeline_id,
                producer_id=producer_id,
                latency_ms=latency_ms,
            )
        return adapter_unavailable_response(
            pipeline_id=pipeline_id,
            adapter_mode=ADAPTER_MODE_REAL,
            latency_ms=latency_ms,
        )
    if "+" in pipeline_id:
        proposer_id, refiner_id = pipeline_id.split("+", maxsplit=1)
        if _is_hosted_vlm_producer(refiner_id):
            return _hosted_vlm_refiner_pipeline_response(
                payload=payload,
                pipeline_id=pipeline_id,
                proposer_id=proposer_id,
                refiner_id=refiner_id,
                latency_ms=latency_ms,
            )
        return adapter_unavailable_response(
            pipeline_id=pipeline_id,
            adapter_mode=ADAPTER_MODE_REAL,
            latency_ms=latency_ms,
        )
    proposer_id = pipeline_id.split("+", maxsplit=1)[0]
    proposer_response = _real_proposer_response(
        payload=payload,
        pipeline_id=pipeline_id,
        producer_id=proposer_id,
        latency_ms=latency_ms,
    )
    if proposer_response is not None:
        return proposer_response
    return adapter_unavailable_response(
        pipeline_id=pipeline_id,
        adapter_mode=ADAPTER_MODE_REAL,
        latency_ms=latency_ms,
    )


def _real_proposer_response(
    *,
    payload: dict[str, Any],
    pipeline_id: str,
    producer_id: str,
    latency_ms: int,
) -> dict[str, Any] | None:
    if producer_id == "grounding-dino":
        return _grounding_dino_real_response(
            payload=payload,
            pipeline_id=pipeline_id,
            latency_ms=latency_ms,
        )
    if producer_id in {"yoloe", "yolo-custom"}:
        return _yolo_real_response(
            payload=payload,
            pipeline_id=pipeline_id,
            producer_id=producer_id,
            latency_ms=latency_ms,
        )
    return None


def _grounding_dino_real_response(
    *,
    payload: dict[str, Any],
    pipeline_id: str,
    latency_ms: int,
) -> dict[str, Any]:
    started = time.monotonic()
    producer_id = "grounding-dino"
    spec = ADAPTER_SPECS[producer_id]
    model_id = _request_model_id(payload, producer_id) or os.environ.get(
        "VISUAL_GROUNDING_DINO_MODEL_ID",
        spec.model_id,
    )
    try:
        image = _decode_request_image(payload)
        labels = _category_hints(payload)
        if not labels:
            return _real_adapter_ok_response(
                pipeline_id=pipeline_id,
                stage="proposer",
                producer_id=producer_id,
                model_id=model_id,
                latency_ms=_elapsed_ms(started, minimum=latency_ms),
                candidates=[],
                raw_proposals=[],
                diagnostic_mode="real_grounding_dino",
            )
        processor, model, torch_module = _load_grounding_dino(model_id)
        text_labels = [[_label_prompt(label) for label in labels]]
        inputs = processor(images=image, text=text_labels, return_tensors="pt")
        device = getattr(model, "device", None)
        if device is not None and hasattr(inputs, "to"):
            inputs = inputs.to(device)
        with torch_module.no_grad():
            outputs = model(**inputs)
        threshold = _float_env("VISUAL_GROUNDING_DINO_BOX_THRESHOLD", 0.35)
        text_threshold = _float_env("VISUAL_GROUNDING_DINO_TEXT_THRESHOLD", 0.25)
        try:
            results = processor.post_process_grounded_object_detection(
                outputs,
                getattr(inputs, "input_ids", None),
                box_threshold=threshold,
                text_threshold=text_threshold,
                target_sizes=[(image.height, image.width)],
            )
        except TypeError:
            results = processor.post_process_grounded_object_detection(
                outputs,
                getattr(inputs, "input_ids", None),
                threshold=threshold,
                text_threshold=text_threshold,
                target_sizes=[(image.height, image.width)],
            )
        candidates = _grounding_dino_candidates_from_result(
            payload=payload,
            image=image,
            result=(results or [{}])[0],
            category_hints=labels,
        )
        return _real_adapter_ok_response(
            pipeline_id=pipeline_id,
            stage="proposer",
            producer_id=producer_id,
            model_id=model_id,
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            candidates=candidates,
            raw_proposals=candidates,
            diagnostic_mode="real_grounding_dino",
        )
    except ImportError as exc:
        return _real_adapter_failure_response(
            pipeline_id=pipeline_id,
            stage="proposer",
            producer_id=producer_id,
            model_id=model_id,
            reason="missing_dependency",
            message=str(exc),
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            diagnostic_mode="real_grounding_dino",
            required_adapter=_required_adapter_record(
                {"stage": "proposer", "producer_id": producer_id},
                spec,
            ),
        )
    except Exception as exc:
        return _real_adapter_failure_response(
            pipeline_id=pipeline_id,
            stage="proposer",
            producer_id=producer_id,
            model_id=model_id,
            reason="adapter_error",
            message=str(exc),
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            diagnostic_mode="real_grounding_dino",
        )


def _yolo_real_response(
    *,
    payload: dict[str, Any],
    pipeline_id: str,
    producer_id: str,
    latency_ms: int,
) -> dict[str, Any]:
    started = time.monotonic()
    spec = ADAPTER_SPECS[producer_id]
    env_name = (
        "VISUAL_GROUNDING_YOLO_CUSTOM_MODEL_ID"
        if producer_id == "yolo-custom"
        else "VISUAL_GROUNDING_YOLOE_MODEL_ID"
    )
    model_id = _request_model_id(payload, producer_id) or os.environ.get(env_name, spec.model_id)
    try:
        image = _decode_request_image(payload)
        labels = _yolo_prompt_labels(_category_hints(payload))
        if not labels:
            return _real_adapter_ok_response(
                pipeline_id=pipeline_id,
                stage="proposer",
                producer_id=producer_id,
                model_id=model_id,
                latency_ms=_elapsed_ms(started, minimum=latency_ms),
                candidates=[],
                raw_proposals=[],
                diagnostic_mode=f"real_{producer_id}",
            )
        model = _load_yolo_model(model_id, producer_id=producer_id)
        if hasattr(model, "set_classes"):
            model.set_classes(labels)
        candidates = _yolo_candidates_from_model(
            payload=payload,
            image=image,
            model=model,
            category_hints=labels,
        )
        return _real_adapter_ok_response(
            pipeline_id=pipeline_id,
            stage="proposer",
            producer_id=producer_id,
            model_id=model_id,
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            candidates=candidates,
            raw_proposals=candidates,
            diagnostic_mode=f"real_{producer_id}",
        )
    except ImportError as exc:
        return _real_adapter_failure_response(
            pipeline_id=pipeline_id,
            stage="proposer",
            producer_id=producer_id,
            model_id=model_id,
            reason="missing_dependency",
            message=str(exc),
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            diagnostic_mode=f"real_{producer_id}",
            required_adapter=_required_adapter_record(
                {"stage": "proposer", "producer_id": producer_id},
                spec,
            ),
        )
    except Exception as exc:
        return _real_adapter_failure_response(
            pipeline_id=pipeline_id,
            stage="proposer",
            producer_id=producer_id,
            model_id=model_id,
            reason="adapter_error",
            message=str(exc),
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            diagnostic_mode=f"real_{producer_id}",
        )


def _hosted_vlm_refiner_pipeline_response(
    *,
    payload: dict[str, Any],
    pipeline_id: str,
    proposer_id: str,
    refiner_id: str,
    latency_ms: int,
) -> dict[str, Any]:
    started = time.monotonic()
    config = _hosted_vlm_config(
        payload=payload,
        producer_id=refiner_id,
        stage="refiner",
    )
    if config["error_reason"]:
        return _hosted_vlm_missing_config_response(
            pipeline_id=pipeline_id,
            stage="refiner",
            producer_id=refiner_id,
            config=config,
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            diagnostic_mode=f"real_{refiner_id}_refiner",
            raw_proposals=[],
        )

    proposer_response = _real_proposer_response(
        payload=payload,
        pipeline_id=proposer_id,
        producer_id=proposer_id,
        latency_ms=latency_ms,
    )
    if proposer_response is None:
        return adapter_unavailable_response(
            pipeline_id=pipeline_id,
            adapter_mode=ADAPTER_MODE_REAL,
            latency_ms=latency_ms,
        )
    if proposer_response.get("status") == "failed":
        return _pipeline_failure_from_stage_response(
            pipeline_id=pipeline_id,
            response=proposer_response,
            diagnostic_mode=f"real_{refiner_id}_refiner",
        )

    proposals = list(proposer_response.get("candidates") or [])
    try:
        image = _decode_request_image(payload)
        vlm_result = _call_hosted_vlm_json(
            payload=payload,
            image=image,
            config=config,
            task="refiner",
            proposals=proposals,
        )
        candidates, rejected = _candidates_from_hosted_vlm_result(
            payload=payload,
            image=image,
            result=vlm_result,
            fallback_candidates=proposals,
        )
        refiner_stage = {
            "stage": "refiner",
            "producer_id": refiner_id,
            "model_id": config["model_id"],
            "version": "hosted-openai-compatible-v1",
            "status": "ok",
            "latency_ms": _elapsed_ms(started, minimum=latency_ms),
            **_stage_telemetry_from_vlm_result(vlm_result),
        }
        stages = list((proposer_response.get("pipeline") or {}).get("stages") or [])
        stages.append(refiner_stage)
        return _real_adapter_pipeline_ok_response(
            pipeline_id=pipeline_id,
            stages=stages,
            candidates=candidates,
            raw_proposals=proposals,
            rejected_proposals=rejected,
            diagnostic_mode=f"real_{refiner_id}_refiner",
            auth_mode=config["auth_mode"],
        )
    except Exception as exc:
        return _hosted_vlm_failure_response(
            pipeline_id=pipeline_id,
            stage="refiner",
            producer_id=refiner_id,
            config=config,
            reason="adapter_error",
            message=str(exc),
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            diagnostic_mode=f"real_{refiner_id}_refiner",
            raw_proposals=proposals,
        )


def _hosted_vlm_direct_response(
    *,
    payload: dict[str, Any],
    pipeline_id: str,
    producer_id: str,
    latency_ms: int,
) -> dict[str, Any]:
    started = time.monotonic()
    config = _hosted_vlm_config(
        payload=payload,
        producer_id=producer_id,
        stage="direct_producer",
    )
    if config["error_reason"]:
        return _hosted_vlm_missing_config_response(
            pipeline_id=pipeline_id,
            stage="direct_producer",
            producer_id=producer_id,
            config=config,
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            diagnostic_mode=f"real_{producer_id}_direct",
            raw_proposals=[],
        )
    try:
        image = _decode_request_image(payload)
        vlm_result = _call_hosted_vlm_json(
            payload=payload,
            image=image,
            config=config,
            task="direct_producer",
            proposals=[],
        )
        candidates, rejected = _candidates_from_hosted_vlm_result(
            payload=payload,
            image=image,
            result=vlm_result,
            fallback_candidates=[],
        )
        return _real_adapter_pipeline_ok_response(
            pipeline_id=pipeline_id,
            stages=[
                {
                    "stage": "direct_producer",
                    "producer_id": producer_id,
                    "model_id": config["model_id"],
                    "version": "hosted-openai-compatible-v1",
                    "status": "ok",
                    "latency_ms": _elapsed_ms(started, minimum=latency_ms),
                    **_stage_telemetry_from_vlm_result(vlm_result),
                }
            ],
            candidates=candidates,
            raw_proposals=candidates,
            rejected_proposals=rejected,
            diagnostic_mode=f"real_{producer_id}_direct",
            auth_mode=config["auth_mode"],
        )
    except Exception as exc:
        return _hosted_vlm_failure_response(
            pipeline_id=pipeline_id,
            stage="direct_producer",
            producer_id=producer_id,
            config=config,
            reason="adapter_error",
            message=str(exc),
            latency_ms=_elapsed_ms(started, minimum=latency_ms),
            diagnostic_mode=f"real_{producer_id}_direct",
            raw_proposals=[],
        )


def adapter_unavailable_response(
    *,
    pipeline_id: str,
    adapter_mode: str,
    latency_ms: int,
) -> dict[str, Any]:
    stages = []
    required_adapters = []
    for stage in contract_fake_stages_for_pipeline(pipeline_id, latency_ms):
        producer_id = str(stage.get("producer_id") or "")
        spec = ADAPTER_SPECS.get(producer_id)
        unavailable_stage = dict(stage)
        unavailable_stage["status"] = "adapter_unavailable"
        unavailable_stage["version"] = "adapter-stub-v1"
        if spec is not None:
            unavailable_stage["model_id"] = spec.model_id
            unavailable_stage["optional_extra"] = spec.optional_extra
        stages.append(unavailable_stage)
        required_adapters.append(_required_adapter_record(stage, spec))
    response = {
        "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
        "status": "failed",
        "pipeline": {
            "pipeline_id": pipeline_id,
            "stages": stages,
        },
        "candidates": [],
        "error": {
            "reason": "adapter_unavailable",
            "message": (
                f"visual grounding adapter for '{pipeline_id}' is not installed; "
                "install the optional sidecar adapter or run with "
                "--adapter-mode contract-fake for contract tests"
            ),
        },
        "diagnostics": {
            "schema": "visual_grounding_diagnostics_v1",
            "diagnostic_mode": "adapter_registry_stub",
            "adapter_mode": adapter_mode,
            "required_adapters": required_adapters,
            "raw_proposals": [],
            "rejected_proposals": [],
            "private_truth_included": False,
        },
    }
    return validate_visual_grounding_response(response)


def pipeline_mismatch_response(
    *,
    configured_pipeline_id: str,
    requested_pipeline_id: str,
) -> dict[str, Any]:
    response = {
        "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
        "status": "failed",
        "pipeline": {
            "pipeline_id": requested_pipeline_id or configured_pipeline_id,
            "stages": [
                {
                    "stage": "router",
                    "producer_id": configured_pipeline_id,
                    "model_id": "",
                    "status": "pipeline_mismatch",
                    "latency_ms": 0,
                }
            ],
        },
        "candidates": [],
        "error": {
            "reason": "pipeline_mismatch",
            "message": (
                f"service pipeline '{configured_pipeline_id}' cannot satisfy "
                f"request pipeline '{requested_pipeline_id}'"
            ),
        },
    }
    return validate_visual_grounding_response(response)


def _required_adapter_record(
    stage: dict[str, Any],
    spec: AdapterSpec | None,
) -> dict[str, Any]:
    producer_id = str(stage.get("producer_id") or "")
    if spec is None:
        return {
            "stage": str(stage.get("stage") or ""),
            "producer_id": producer_id,
            "status": "adapter_unavailable",
            "model_id": str(stage.get("model_id") or ""),
            "optional_extra": "",
            "setup_hint": "No adapter spec is registered for this producer id.",
        }
    return {
        "stage": str(stage.get("stage") or ""),
        "producer_id": producer_id,
        "status": spec.status,
        "model_id": spec.model_id,
        "optional_extra": spec.optional_extra,
        "setup_hint": spec.setup_hint,
    }


@lru_cache(maxsize=4)
def _load_grounding_dino(model_id: str) -> tuple[Any, Any, Any]:
    try:
        import torch
        from transformers import AutoModelForZeroShotObjectDetection, AutoProcessor
    except ImportError as exc:
        raise ImportError(
            "Grounding DINO real mode requires sidecar dependencies: transformers and torch"
        ) from exc

    processor = AutoProcessor.from_pretrained(model_id)
    model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id)
    model.eval()
    return processor, model, torch


@lru_cache(maxsize=4)
def _load_yolo_model(model_id: str, *, producer_id: str) -> Any:
    try:
        if producer_id == "yolo-custom":
            from ultralytics import YOLO

            return YOLO(model_id)
        from ultralytics import YOLOE

        return YOLOE(model_id)
    except ImportError as exc:
        raise ImportError(
            f"{producer_id} real mode requires the sidecar dependency: ultralytics"
        ) from exc


def _hosted_vlm_config(
    *,
    payload: dict[str, Any],
    producer_id: str,
    stage: str,
) -> dict[str, Any]:
    spec = _hosted_vlm_spec(producer_id)
    base_url = _hosted_vlm_base_url(producer_id)
    api_key = _hosted_vlm_api_key(producer_id)
    model_id = (
        _request_model_id(payload, producer_id)
        or _hosted_vlm_model_env(producer_id)
        or spec.model_id
    )
    error_reason = ""
    error_message = ""
    allow_no_api_key = _bool_env("VISUAL_GROUNDING_VLM_ALLOW_NO_API_KEY")
    if not base_url:
        error_reason = "missing_config"
        error_message = (
            f"{producer_id} {stage} real mode requires "
            "VISUAL_GROUNDING_*_BASE_URL, VISUAL_GROUNDING_VLM_BASE_URL, "
            "or XM_LLM_BASE_URL"
        )
    elif not api_key and not allow_no_api_key:
        error_reason = "missing_config"
        error_message = (
            f"{producer_id} {stage} real mode requires "
            "VISUAL_GROUNDING_*_API_KEY, VISUAL_GROUNDING_VLM_API_KEY, "
            "XM_LLM_API_KEY, or VISUAL_GROUNDING_VLM_ALLOW_NO_API_KEY=true "
            "for local test servers"
        )
    return {
        "producer_id": producer_id,
        "model_id": model_id,
        "base_url": base_url,
        "api_key": api_key,
        "timeout_s": _float_env("VISUAL_GROUNDING_VLM_TIMEOUT_S", 60.0),
        "auth_mode": "bearer_configured" if api_key else "none",
        "error_reason": error_reason,
        "error_message": error_message,
        "required_adapter": _required_adapter_record(
            {"stage": stage, "producer_id": producer_id},
            spec,
        ),
    }


def _hosted_vlm_base_url(producer_id: str) -> str:
    prefixes = _hosted_vlm_env_prefixes(producer_id)
    configured = _first_env(
        [
            *(f"VISUAL_GROUNDING_{prefix}_BASE_URL" for prefix in prefixes),
            "VISUAL_GROUNDING_VLM_BASE_URL",
        ]
    )
    if configured:
        return configured
    if producer_id in _PROVIDER_PREFIXED_HOSTED_VLM_MODEL_IDS:
        return os.environ.get("XM_LLM_BASE_URL", "").strip()
    if producer_id == "mimo-v2-omni":
        return _MIMO_OPENAI_BASE_URL
    return ""


def _hosted_vlm_api_key(producer_id: str) -> str:
    prefixes = _hosted_vlm_env_prefixes(producer_id)
    configured = _first_env(
        [
            *(f"VISUAL_GROUNDING_{prefix}_API_KEY" for prefix in prefixes),
            "VISUAL_GROUNDING_VLM_API_KEY",
        ]
    )
    if configured:
        return configured
    if producer_id in _PROVIDER_PREFIXED_HOSTED_VLM_MODEL_IDS:
        return os.environ.get("XM_LLM_API_KEY", "").strip()
    if producer_id == "mimo-v2-omni":
        return os.environ.get("MIMO_TP_KEY", "").strip()
    return ""


def _hosted_vlm_model_env(producer_id: str) -> str:
    prefixes = _hosted_vlm_env_prefixes(producer_id)
    return _first_env(
        [
            *(f"VISUAL_GROUNDING_{prefix}_MODEL_ID" for prefix in prefixes),
            "VISUAL_GROUNDING_VLM_MODEL_ID",
        ]
    )


def _hosted_vlm_env_prefixes(producer_id: str) -> tuple[str, ...]:
    if producer_id == "mimo-v2-omni" or producer_id.startswith("xiaomi/"):
        return ("MIMO",)
    if producer_id == "qwen3-vl" or producer_id.startswith("tongyi/"):
        return ("QWEN",)
    if producer_id.startswith("siliconflow/"):
        return ("QWEN", "SILICONFLOW")
    if producer_id.startswith("vertex_ai/"):
        return ("GEMINI",)
    return ()


def _first_env(names: list[str]) -> str:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def _call_hosted_vlm_json(
    *,
    payload: dict[str, Any],
    image: Image.Image,
    config: dict[str, Any],
    task: str,
    proposals: list[dict[str, Any]],
) -> dict[str, Any]:
    image_payload = payload.get("image") or {}
    image_url = (
        f"data:{image_payload.get('mime_type') or 'image/jpeg'};base64,"
        f"{image_payload.get('bytes_base64') or ''}"
    )
    request_payload = {
        "model": config["model_id"],
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a visual grounding producer for a robotics cleanup "
                    "benchmark. Return only strict JSON. Do not include private "
                    "labels, local file paths, service credentials, or prose."
                ),
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": _hosted_vlm_prompt(
                            payload=payload,
                            image=image,
                            task=task,
                            proposals=proposals,
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            },
        ],
    }
    body = json.dumps(request_payload).encode("utf-8")
    request = urllib.request.Request(
        _chat_completions_url(str(config["base_url"])),
        data=body,
        headers=_hosted_vlm_headers(config),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=float(config["timeout_s"])) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        message = exc.reason or f"HTTP {exc.code}"
        try:
            error_payload = json.loads(exc.read().decode("utf-8"))
            message = str((error_payload.get("error") or {}).get("message") or message)
        except Exception:
            pass
        raise RuntimeError(f"hosted VLM returned HTTP {exc.code}: {message}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("hosted VLM response was not valid JSON") from exc

    parsed = _json_object_from_text(_chat_completion_content(response_payload))
    telemetry = _hosted_vlm_response_telemetry(response_payload)
    if telemetry:
        parsed["_telemetry"] = telemetry
    return parsed


def _hosted_vlm_response_telemetry(response_payload: dict[str, Any]) -> dict[str, Any]:
    usage = response_payload.get("usage") or {}
    if not isinstance(usage, dict):
        return {}
    token_usage: dict[str, int] = {}
    for source_key, output_key in (
        ("prompt_tokens", "prompt_tokens"),
        ("completion_tokens", "completion_tokens"),
        ("total_tokens", "total_tokens"),
    ):
        value = _int_or_none(usage.get(source_key))
        if value is not None:
            token_usage[output_key] = value
    telemetry: dict[str, Any] = {}
    if token_usage:
        telemetry["token_usage"] = token_usage
    cost = _hosted_vlm_cost_usd(token_usage)
    if cost is not None:
        telemetry["api_cost_usd"] = cost
    return telemetry


def _stage_telemetry_from_vlm_result(vlm_result: dict[str, Any]) -> dict[str, Any]:
    telemetry = vlm_result.get("_telemetry") or {}
    if not isinstance(telemetry, dict):
        return {}
    output: dict[str, Any] = {}
    token_usage = telemetry.get("token_usage")
    if isinstance(token_usage, dict) and token_usage:
        output["token_usage"] = token_usage
    cost = _float_or_none(telemetry.get("api_cost_usd"))
    if cost is not None:
        output["api_cost_usd"] = cost
    return output


def _hosted_vlm_cost_usd(token_usage: dict[str, int]) -> float | None:
    if not token_usage:
        return None
    input_rate = _float_env_optional("VISUAL_GROUNDING_VLM_INPUT_USD_PER_1K_TOKENS")
    output_rate = _float_env_optional("VISUAL_GROUNDING_VLM_OUTPUT_USD_PER_1K_TOKENS")
    flat_rate = _float_env_optional("VISUAL_GROUNDING_VLM_USD_PER_1K_TOKENS")
    if input_rate is not None or output_rate is not None:
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total = ((input_rate or 0.0) * prompt_tokens) + ((output_rate or 0.0) * completion_tokens)
        return round(total / 1000.0, 8)
    if flat_rate is not None:
        return round((flat_rate * token_usage.get("total_tokens", 0)) / 1000.0, 8)
    return None


def _hosted_vlm_prompt(
    *,
    payload: dict[str, Any],
    image: Image.Image,
    task: str,
    proposals: list[dict[str, Any]],
) -> str:
    common = {
        "task": task,
        "schema": "visual_grounding_hosted_vlm_json_v1",
        "observation_id": payload.get("observation_id"),
        "waypoint_id": payload.get("waypoint_id"),
        "room_id": payload.get("room_id"),
        "image_dimensions": {"width": image.width, "height": image.height},
        "category_hints": payload.get("category_hints") or [],
        "fixture_hints": payload.get("fixture_hints") or [],
        "output_contract": {
            "candidates": [
                {
                    "category": "one public category",
                    "image_region": {
                        "type": "bbox",
                        "value": [0.0, 0.0, 0.0, 0.0],
                    },
                    "confidence": 0.0,
                    "evidence_note": "visible evidence only",
                    "destination_hint": {"candidate_fixture_id": "optional public fixture id"},
                }
            ],
            "rejected_proposals": [{"proposal_id": "proposal_001", "reason": "why rejected"}],
        },
        "rules": [
            "Use normalized bbox [x, y, width, height] in [0, 1] when returning boxes.",
            "Reject proposals that are not visibly supported by the image.",
            "Use destination_hint only as public fixture-affordance evidence.",
            "Return JSON only.",
        ],
    }
    if proposals:
        common["proposals"] = [
            {"proposal_id": f"proposal_{index:03d}", **proposal}
            for index, proposal in enumerate(proposals, start=1)
        ]
    return json.dumps(common, sort_keys=True)


def _candidates_from_hosted_vlm_result(
    *,
    payload: dict[str, Any],
    image: Image.Image,
    result: dict[str, Any],
    fallback_candidates: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    proposal_map = {
        f"proposal_{index:03d}": proposal
        for index, proposal in enumerate(fallback_candidates, start=1)
    }
    candidates = []
    for item in result.get("candidates") or []:
        if not isinstance(item, dict):
            continue
        base = dict(proposal_map.get(str(item.get("proposal_id") or ""), {}))
        merged = {**base, **item}
        candidate = _candidate_from_hosted_vlm_candidate(
            payload=payload,
            image=image,
            raw_candidate=merged,
        )
        if candidate is not None:
            candidates.append(candidate)
    rejected = []
    for item in result.get("rejected_proposals") or []:
        if isinstance(item, dict):
            rejected.append(
                {
                    "proposal_id": str(item.get("proposal_id") or ""),
                    "category": str(item.get("category") or ""),
                    "reason": str(item.get("reason") or "rejected_by_hosted_vlm"),
                }
            )
    return _top_candidates(candidates), rejected


def _candidate_from_hosted_vlm_candidate(
    *,
    payload: dict[str, Any],
    image: Image.Image,
    raw_candidate: dict[str, Any],
) -> dict[str, Any] | None:
    category = str(raw_candidate.get("category") or "object").strip() or "object"
    region = _hosted_vlm_image_region(raw_candidate.get("image_region"), image=image)
    if region is None:
        return None
    confidence = _float_or_none(raw_candidate.get("confidence"))
    destination_hint = raw_candidate.get("destination_hint")
    return {
        "category": category,
        "image_region": region,
        "confidence": _clamp_float(confidence if confidence is not None else 0.5, 0.0, 1.0),
        "evidence_note": str(
            raw_candidate.get("evidence_note")
            or f"hosted VLM visually grounded {category} from RAW_FPV pixels"
        ),
        "source_fixture_id": str(raw_candidate.get("source_fixture_id") or ""),
        "destination_hint": destination_hint
        if isinstance(destination_hint, dict)
        else _destination_hint(payload, category),
        "tracking": raw_candidate.get("tracking")
        if isinstance(raw_candidate.get("tracking"), dict)
        else {},
    }


def _hosted_vlm_image_region(value: Any, *, image: Image.Image) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    region_type = str(value.get("type") or "")
    raw = value.get("value")
    if region_type == "bbox":
        numbers = [_float_or_none(item) for item in _vector(raw)[:4]]
        if len(numbers) != 4 or any(item is None for item in numbers):
            return None
        bbox = [float(item) for item in numbers]
        if any(number > 1.0 for number in bbox):
            normalized = _normalized_xyxy_to_xywh(bbox, width=image.width, height=image.height)
            return {"type": "bbox", "value": normalized} if normalized else None
        if any(number < 0.0 for number in bbox):
            return None
        return {"type": "bbox", "value": [_clamp_float(number, 0.0, 1.0) for number in bbox]}
    if region_type == "point":
        numbers = [_float_or_none(item) for item in _vector(raw)[:2]]
        if len(numbers) != 2 or any(item is None for item in numbers):
            return None
        return {
            "type": "point",
            "value": [_clamp_float(float(item), 0.0, 1.0) for item in numbers],
        }
    if region_type == "verbal_region" and str(raw or "").strip():
        return {"type": "verbal_region", "value": str(raw)}
    return None


def _hosted_vlm_headers(config: dict[str, Any]) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "roboclaws-visual-grounding-vlm-sidecar/1.0",
    }
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"
    return headers


def _chat_completions_url(base_url: str) -> str:
    cleaned = base_url.rstrip("/")
    if cleaned.endswith("/chat/completions"):
        return cleaned
    return cleaned + "/chat/completions"


def _chat_completion_content(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("hosted VLM response did not include choices")
    message = (choices[0] or {}).get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content or "")


def _json_object_from_text(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("hosted VLM response did not contain a JSON object")
        payload = json.loads(cleaned[start : end + 1])
    if not isinstance(payload, dict):
        raise RuntimeError("hosted VLM response JSON must be an object")
    return payload


def _decode_request_image(payload: dict[str, Any]) -> Image.Image:
    image_payload = payload.get("image") or {}
    data = base64.b64decode(str(image_payload.get("bytes_base64") or ""), validate=True)
    if not data:
        raise ValueError("visual grounding request image has no bytes")
    return Image.open(io.BytesIO(data)).convert("RGB")


def _category_hints(payload: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    hints: list[str] = []
    for value in payload.get("category_hints") or []:
        label = str(value or "").strip()
        if not label:
            continue
        key = _norm(label)
        if key in seen:
            continue
        seen.add(key)
        hints.append(label)
    return hints


def _request_model_id(payload: dict[str, Any], producer_id: str) -> str:
    pipeline_request = payload.get("pipeline_request") or {}
    for key in ("proposer", "refiner"):
        item = pipeline_request.get(key) or {}
        if str(item.get("producer_id") or "") == producer_id:
            return str(item.get("model_id") or "")
    return ""


def _label_prompt(label: str) -> str:
    cleaned = str(label or "").strip()
    if not cleaned:
        return "object"
    return cleaned if cleaned.lower().startswith(("a ", "an ")) else f"a {cleaned}"


def _grounding_dino_candidates_from_result(
    *,
    payload: dict[str, Any],
    image: Image.Image,
    result: dict[str, Any],
    category_hints: list[str],
) -> list[dict[str, Any]]:
    boxes = _rows(result.get("boxes"))
    scores = _vector(result.get("scores"))
    labels = _vector(result.get("text_labels") or result.get("labels"))
    candidates: list[dict[str, Any]] = []
    for index, box in enumerate(boxes):
        confidence = _float_at(scores, index, default=0.0)
        category = _category_from_model_label(
            _value_at(labels, index, default=""),
            category_hints,
        )
        candidate = _candidate_from_xyxy(
            payload=payload,
            image=image,
            category=category,
            xyxy=box,
            confidence=confidence,
            evidence_note=f"Grounding DINO detected {category} from RAW_FPV pixels",
        )
        if candidate is not None:
            candidates.append(candidate)
    return _top_candidates(candidates)


def _yolo_candidates_from_model(
    *,
    payload: dict[str, Any],
    image: Image.Image,
    model: Any,
    category_hints: list[str],
) -> list[dict[str, Any]]:
    threshold = _float_env("VISUAL_GROUNDING_YOLO_CONFIDENCE_THRESHOLD", 0.25)
    predict_kwargs: dict[str, Any] = {
        "conf": threshold,
        "verbose": False,
    }
    imgsz = _int_env_optional("VISUAL_GROUNDING_YOLO_IMAGE_SIZE")
    if imgsz is not None:
        predict_kwargs["imgsz"] = imgsz
    iou = _float_env_optional("VISUAL_GROUNDING_YOLO_IOU_THRESHOLD")
    if iou is not None:
        predict_kwargs["iou"] = iou
    max_det = _int_env_optional("VISUAL_GROUNDING_YOLO_MAX_DET")
    if max_det is not None:
        predict_kwargs["max_det"] = max_det
    if _env_is_set("VISUAL_GROUNDING_YOLO_AGNOSTIC_NMS"):
        predict_kwargs["agnostic_nms"] = _bool_env("VISUAL_GROUNDING_YOLO_AGNOSTIC_NMS")
    if _env_is_set("VISUAL_GROUNDING_YOLO_AUGMENT"):
        predict_kwargs["augment"] = _bool_env("VISUAL_GROUNDING_YOLO_AUGMENT")
    if _env_is_set("VISUAL_GROUNDING_YOLO_RETINA_MASKS"):
        predict_kwargs["retina_masks"] = _bool_env("VISUAL_GROUNDING_YOLO_RETINA_MASKS")
    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_image:
        image.save(temp_image.name, format="JPEG", quality=90)
        if hasattr(model, "predict"):
            results = model.predict(source=temp_image.name, **predict_kwargs)
        else:
            results = model(temp_image.name)
    candidates: list[dict[str, Any]] = []
    for result in results or []:
        candidates.extend(
            _yolo_candidates_from_result(
                payload=payload,
                image=image,
                result=result,
                category_hints=category_hints,
            )
        )
    return _top_candidates(candidates)


def _yolo_candidates_from_result(
    *,
    payload: dict[str, Any],
    image: Image.Image,
    result: Any,
    category_hints: list[str],
) -> list[dict[str, Any]]:
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return []
    rows = _rows(getattr(boxes, "xyxy", []))
    confidences = _vector(getattr(boxes, "conf", []))
    classes = _vector(getattr(boxes, "cls", []))
    names = getattr(result, "names", {}) or {}
    candidates: list[dict[str, Any]] = []
    for index, box in enumerate(rows):
        class_id = int(_float_at(classes, index, default=index))
        category = _category_from_yolo_class(
            class_id=class_id,
            names=names,
            category_hints=category_hints,
        )
        candidate = _candidate_from_xyxy(
            payload=payload,
            image=image,
            category=category,
            xyxy=box,
            confidence=_float_at(confidences, index, default=0.0),
            evidence_note=f"YOLOE detected {category} from RAW_FPV pixels",
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates


def _yolo_prompt_labels(category_hints: list[str]) -> list[str]:
    if not _bool_env_default("VISUAL_GROUNDING_YOLO_EXPAND_CLEANUP_HINTS", True):
        return category_hints
    expansions = {
        "dish": ("dish", "plate", "bowl", "cup", "mug", "utensil"),
        "food": ("food", "apple", "potato", "bread", "fruit", "vegetable"),
        "book": ("book", "paper", "magazine", "newspaper"),
        "linen": ("linen", "towel", "cloth", "blanket"),
        "toy": ("toy", "ball", "plush toy", "teddy bear"),
        "electronics": ("electronics", "remote control", "remote", "phone"),
        "pillow": ("pillow", "cushion"),
    }
    labels: list[str] = []
    seen: set[str] = set()
    for hint in category_hints:
        for label in expansions.get(_norm(hint), (hint,)):
            key = _norm(label)
            if not key or key in seen:
                continue
            seen.add(key)
            labels.append(label)
    return labels


def _candidate_from_xyxy(
    *,
    payload: dict[str, Any],
    image: Image.Image,
    category: str,
    xyxy: Any,
    confidence: float,
    evidence_note: str,
) -> dict[str, Any] | None:
    bbox = _normalized_xyxy_to_xywh(xyxy, width=image.width, height=image.height)
    if bbox is None:
        return None
    return {
        "category": category or "object",
        "image_region": {"type": "bbox", "value": bbox},
        "confidence": _clamp_float(confidence, 0.0, 1.0),
        "evidence_note": evidence_note,
        "source_fixture_id": "",
        "destination_hint": _destination_hint(payload, category),
    }


def _real_adapter_ok_response(
    *,
    pipeline_id: str,
    stage: str,
    producer_id: str,
    model_id: str,
    latency_ms: int,
    candidates: list[dict[str, Any]],
    raw_proposals: list[dict[str, Any]],
    diagnostic_mode: str,
) -> dict[str, Any]:
    response = {
        "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
        "status": "ok",
        "pipeline": {
            "pipeline_id": pipeline_id,
            "stages": [
                {
                    "stage": stage,
                    "producer_id": producer_id,
                    "model_id": model_id,
                    "version": "real-sidecar-adapter-v1",
                    "status": "ok",
                    "latency_ms": latency_ms,
                }
            ],
        },
        "candidates": candidates,
        "diagnostics": {
            "schema": "visual_grounding_diagnostics_v1",
            "diagnostic_mode": diagnostic_mode,
            "raw_proposals": raw_proposals,
            "rejected_proposals": [],
            "private_truth_included": False,
        },
    }
    return validate_visual_grounding_response(response)


def _real_adapter_pipeline_ok_response(
    *,
    pipeline_id: str,
    stages: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    raw_proposals: list[dict[str, Any]],
    rejected_proposals: list[dict[str, Any]],
    diagnostic_mode: str,
    auth_mode: str = "",
) -> dict[str, Any]:
    diagnostics = {
        "schema": "visual_grounding_diagnostics_v1",
        "diagnostic_mode": diagnostic_mode,
        "raw_proposals": raw_proposals,
        "rejected_proposals": rejected_proposals,
        "private_truth_included": False,
    }
    if auth_mode:
        diagnostics["auth_mode"] = auth_mode
    response = {
        "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
        "status": "ok",
        "pipeline": {
            "pipeline_id": pipeline_id,
            "stages": stages,
        },
        "candidates": candidates,
        "diagnostics": diagnostics,
    }
    return validate_visual_grounding_response(response)


def _hosted_vlm_missing_config_response(
    *,
    pipeline_id: str,
    stage: str,
    producer_id: str,
    config: dict[str, Any],
    latency_ms: int,
    diagnostic_mode: str,
    raw_proposals: list[dict[str, Any]],
) -> dict[str, Any]:
    return _hosted_vlm_failure_response(
        pipeline_id=pipeline_id,
        stage=stage,
        producer_id=producer_id,
        config=config,
        reason=str(config.get("error_reason") or "missing_config"),
        message=str(config.get("error_message") or "hosted VLM adapter is not configured"),
        latency_ms=latency_ms,
        diagnostic_mode=diagnostic_mode,
        raw_proposals=raw_proposals,
        required_adapter=config.get("required_adapter"),
    )


def _hosted_vlm_failure_response(
    *,
    pipeline_id: str,
    stage: str,
    producer_id: str,
    config: dict[str, Any],
    reason: str,
    message: str,
    latency_ms: int,
    diagnostic_mode: str,
    raw_proposals: list[dict[str, Any]],
    required_adapter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostics = {
        "schema": "visual_grounding_diagnostics_v1",
        "diagnostic_mode": diagnostic_mode,
        "auth_mode": config.get("auth_mode", "none"),
        "required_adapters": [required_adapter] if required_adapter is not None else [],
        "raw_proposals": raw_proposals,
        "rejected_proposals": [],
        "private_truth_included": False,
    }
    response = {
        "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
        "status": "failed",
        "pipeline": {
            "pipeline_id": pipeline_id,
            "stages": [
                {
                    "stage": stage,
                    "producer_id": producer_id,
                    "model_id": str(config.get("model_id") or ""),
                    "version": "hosted-openai-compatible-v1",
                    "status": reason,
                    "latency_ms": latency_ms,
                }
            ],
        },
        "candidates": [],
        "error": {"reason": reason, "message": message},
        "diagnostics": diagnostics,
    }
    return validate_visual_grounding_response(response)


def _pipeline_failure_from_stage_response(
    *,
    pipeline_id: str,
    response: dict[str, Any],
    diagnostic_mode: str,
) -> dict[str, Any]:
    copied = dict(response)
    copied["pipeline"] = dict(response.get("pipeline") or {})
    copied["pipeline"]["pipeline_id"] = pipeline_id
    diagnostics = dict(copied.get("diagnostics") or {})
    diagnostics.setdefault("schema", "visual_grounding_diagnostics_v1")
    diagnostics["diagnostic_mode"] = diagnostic_mode
    diagnostics.setdefault("private_truth_included", False)
    copied["diagnostics"] = diagnostics
    return validate_visual_grounding_response(copied)


def _real_adapter_failure_response(
    *,
    pipeline_id: str,
    stage: str,
    producer_id: str,
    model_id: str,
    reason: str,
    message: str,
    latency_ms: int,
    diagnostic_mode: str,
    required_adapter: dict[str, Any] | None = None,
) -> dict[str, Any]:
    diagnostics = {
        "schema": "visual_grounding_diagnostics_v1",
        "diagnostic_mode": diagnostic_mode,
        "required_adapters": [required_adapter] if required_adapter is not None else [],
        "raw_proposals": [],
        "rejected_proposals": [],
        "private_truth_included": False,
    }
    response = {
        "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
        "status": "failed",
        "pipeline": {
            "pipeline_id": pipeline_id,
            "stages": [
                {
                    "stage": stage,
                    "producer_id": producer_id,
                    "model_id": model_id,
                    "version": "real-sidecar-adapter-v1",
                    "status": reason,
                    "latency_ms": latency_ms,
                }
            ],
        },
        "candidates": [],
        "error": {
            "reason": reason,
            "message": message,
        },
        "diagnostics": diagnostics,
    }
    return validate_visual_grounding_response(response)


def _normalized_xyxy_to_xywh(
    value: Any,
    *,
    width: int,
    height: int,
) -> list[float] | None:
    numbers = [_float_or_none(item) for item in _vector(value)[:4]]
    if len(numbers) != 4 or any(item is None for item in numbers):
        return None
    x1, y1, x2, y2 = [float(item) for item in numbers]
    x1, x2 = sorted((_clamp_float(x1, 0.0, float(width)), _clamp_float(x2, 0.0, float(width))))
    y1, y2 = sorted(
        (
            _clamp_float(y1, 0.0, float(height)),
            _clamp_float(y2, 0.0, float(height)),
        )
    )
    box_width = max(0.0, x2 - x1)
    box_height = max(0.0, y2 - y1)
    if box_width <= 0.0 or box_height <= 0.0 or width <= 0 or height <= 0:
        return None
    return [
        round(x1 / width, 6),
        round(y1 / height, 6),
        round(box_width / width, 6),
        round(box_height / height, 6),
    ]


def _destination_hint(payload: dict[str, Any], category: str) -> dict[str, Any]:
    preferences = _destination_preferences(category)
    if not preferences:
        return {}
    for fixture in payload.get("fixture_hints") or []:
        searchable = " ".join(
            [
                str(fixture.get("fixture_id") or ""),
                str(fixture.get("category") or ""),
                str(fixture.get("name") or ""),
                " ".join(str(item) for item in fixture.get("affordances") or []),
            ]
        ).lower()
        if any(preference in searchable for preference in preferences):
            return {
                "candidate_fixture_id": str(fixture.get("fixture_id") or ""),
                "confidence": 0.45,
                "basis": "sidecar_public_fixture_affordance_hint",
            }
    return {}


def _destination_preferences(category: str) -> tuple[str, ...]:
    category_norm = _norm(category)
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


def _category_from_model_label(raw_label: Any, category_hints: list[str]) -> str:
    if isinstance(raw_label, (int, float)):
        index = int(raw_label)
        if 0 <= index < len(category_hints):
            return category_hints[index]
    label = str(raw_label or "").strip()
    if not label:
        return category_hints[0] if category_hints else "object"
    label_norm = _norm(label.removeprefix("a ").removeprefix("an "))
    for hint in category_hints:
        hint_norm = _norm(hint)
        if hint_norm and (hint_norm == label_norm or hint_norm in label_norm):
            return hint
    return label.replace("a ", "", 1).replace("an ", "", 1) or "object"


def _category_from_yolo_class(
    *,
    class_id: int,
    names: Any,
    category_hints: list[str],
) -> str:
    if isinstance(names, dict) and class_id in names:
        return str(names[class_id])
    if isinstance(names, list) and 0 <= class_id < len(names):
        return str(names[class_id])
    if 0 <= class_id < len(category_hints):
        return category_hints[class_id]
    return category_hints[0] if category_hints else "object"


def _top_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    max_candidates = max(1, int(_float_env("VISUAL_GROUNDING_MAX_CANDIDATES", 8)))
    return sorted(
        candidates,
        key=lambda item: -float(item.get("confidence") or 0.0),
    )[:max_candidates]


def _rows(value: Any) -> list[list[Any]]:
    raw = _as_list(value)
    if not raw:
        return []
    if isinstance(raw[0], (list, tuple)):
        return [list(item) for item in raw]
    return [raw]


def _vector(value: Any) -> list[Any]:
    raw = _as_list(value)
    if raw and isinstance(raw[0], (list, tuple)):
        return [item[0] if item else None for item in raw]
    return raw


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return value
    return [value]


def _value_at(values: list[Any], index: int, *, default: Any) -> Any:
    return values[index] if index < len(values) else default


def _float_at(values: list[Any], index: int, *, default: float) -> float:
    return _float_or_none(_value_at(values, index, default=default)) or default


def _float_or_none(value: Any) -> float | None:
    try:
        if hasattr(value, "item"):
            value = value.item()
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> int | None:
    try:
        if hasattr(value, "item"):
            value = value.item()
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _float_env_optional(name: str) -> float | None:
    raw = os.environ.get(name)
    if raw in {None, ""}:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _int_env_optional(name: str) -> int | None:
    raw = os.environ.get(name)
    if raw in {None, ""}:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _bool_env(name: str) -> bool:
    return str(os.environ.get(name, "")).strip().lower() in {"1", "true", "yes", "on"}


def _bool_env_default(name: str, default: bool) -> bool:
    if not _env_is_set(name):
        return default
    return _bool_env(name)


def _env_is_set(name: str) -> bool:
    return os.environ.get(name) not in {None, ""}


def _clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _elapsed_ms(started: float, *, minimum: int) -> int:
    return max(int(minimum), round((time.monotonic() - started) * 1000))


def _norm(value: str) -> str:
    return "".join(ch for ch in str(value).lower() if ch.isalnum())
