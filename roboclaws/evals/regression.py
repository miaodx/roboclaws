"""Failure replay and regression sample promotion helpers."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from roboclaws.evals.models import (
    EVAL_SAMPLE_SCHEMA,
    MISSING_NOT_APPLICABLE,
    MISSING_UNAVAILABLE,
    EvalSample,
    EvalSuite,
    load_eval_sample,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

PROMOTION_SCHEMA = "roboclaws_eval_regression_promotion_v1"
PROMOTION_REVIEW_LABELS = frozenset(
    {
        "eval-regression:accepted",
        "eval-regression:needs-human-review",
        "eval-regression:do-not-promote",
    }
)


def promote_regression_sample_from_eval_result(
    eval_results_path: Path,
    *,
    source_sample_id: str | None = None,
    source_trial_id: str | None = None,
    regression_sample_id: str | None = None,
    review_label: str = "eval-regression:accepted",
    sample_output_path: Path | None = None,
    suite_path: Path | None = None,
    suite_output_path: Path | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    """Promote a failed eval result into a durable sample and suite manifest entry."""

    if review_label not in PROMOTION_REVIEW_LABELS:
        expected = "|".join(sorted(PROMOTION_REVIEW_LABELS))
        raise ValueError(f"unsupported review_label {review_label!r}; expected {expected}")
    if review_label == "eval-regression:do-not-promote":
        raise ValueError("review_label eval-regression:do-not-promote cannot write a sample")

    eval_results_path = Path(eval_results_path)
    bundle = _load_json(eval_results_path)
    result = _select_result(
        bundle,
        source_sample_id=source_sample_id,
        source_trial_id=source_trial_id,
    )
    identity = _mapping(result.get("identity"))
    failure_class = str(result.get("failure_class") or MISSING_UNAVAILABLE)
    sample_id = regression_sample_id or _default_regression_sample_id(identity, failure_class)
    sample_output_path = sample_output_path or _default_sample_output_path(sample_id)
    suite_payload = _suite_payload(bundle, suite_path=suite_path)
    source_sample = _source_sample(bundle, identity)
    sample_payload = _regression_sample_payload(
        source_sample=source_sample,
        identity=identity,
        result=result,
        bundle=bundle,
        eval_results_path=eval_results_path,
        sample_id=sample_id,
        review_label=review_label,
        version=version or date.today().isoformat(),
    )
    EvalSample.from_mapping(sample_payload)

    sample_output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(sample_output_path, sample_payload)

    suite_output_path = Path(suite_output_path or suite_path or _default_suite_path(bundle))
    updated_suite = _updated_suite_payload(
        suite_payload,
        sample_id=sample_id,
        sample_ref=_sample_ref(sample_output_path),
        result=result,
        review_label=review_label,
    )
    EvalSuite.from_mapping(updated_suite)
    suite_output_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(suite_output_path, updated_suite)

    promotion = {
        "schema": PROMOTION_SCHEMA,
        "review_label": review_label,
        "sample": {
            "sample_id": sample_id,
            "path": str(sample_output_path),
        },
        "suite": {
            "suite_id": updated_suite["suite_id"],
            "path": str(suite_output_path),
        },
        "source": {
            "eval_results": str(eval_results_path),
            "suite_id": str(bundle.get("suite", {}).get("suite_id") or MISSING_UNAVAILABLE),
            "sample_id": str(identity.get("sample_id") or MISSING_UNAVAILABLE),
            "trial_id": str(identity.get("trial_id") or MISSING_UNAVAILABLE),
            "status": str(result.get("status") or MISSING_UNAVAILABLE),
            "failure_class": failure_class,
        },
    }
    return promotion


def _select_result(
    bundle: dict[str, Any],
    *,
    source_sample_id: str | None,
    source_trial_id: str | None,
) -> dict[str, Any]:
    results = bundle.get("results")
    if not isinstance(results, list):
        raise ValueError("eval results bundle is missing results[]")
    for item in results:
        result = item if isinstance(item, dict) else {}
        identity = _mapping(result.get("identity"))
        if source_sample_id and identity.get("sample_id") != source_sample_id:
            continue
        if source_trial_id and identity.get("trial_id") != source_trial_id:
            continue
        if result.get("status") == "passed":
            continue
        if result.get("status") in {"failed", "blocked", "inconclusive"}:
            return result
    selector = "matching " if source_sample_id or source_trial_id else ""
    raise ValueError(f"no {selector}failed, blocked, or inconclusive eval result found")


def _regression_sample_payload(
    *,
    source_sample: EvalSample | None,
    identity: dict[str, Any],
    result: dict[str, Any],
    bundle: dict[str, Any],
    eval_results_path: Path,
    sample_id: str,
    review_label: str,
    version: str,
) -> dict[str, Any]:
    if source_sample is not None:
        payload = source_sample.to_dict()
    else:
        payload = _sample_payload_from_identity(identity, bundle)
    payload["sample_id"] = sample_id
    payload["version"] = version
    payload["trial_count"] = 1
    provider_profile = str(identity.get("provider_profile") or MISSING_UNAVAILABLE)
    if provider_profile and provider_profile not in set(payload.get("provider_profiles") or []):
        payload["provider_profiles"] = [*payload.get("provider_profiles", []), provider_profile]
    payload["private_goal_reference"] = _private_goal_reference(
        payload.get("private_goal_reference"),
        result=result,
        bundle=bundle,
        eval_results_path=eval_results_path,
        identity=identity,
        review_label=review_label,
    )
    return payload


def _sample_payload_from_identity(
    identity: dict[str, Any],
    bundle: dict[str, Any],
) -> dict[str, Any]:
    suite = _mapping(bundle.get("suite"))
    provider_profile = str(identity.get("provider_profile") or MISSING_UNAVAILABLE)
    return {
        "schema": EVAL_SAMPLE_SCHEMA,
        "sample_id": str(identity.get("sample_id") or MISSING_UNAVAILABLE),
        "version": str(identity.get("sample_version") or MISSING_UNAVAILABLE),
        "surface": str(identity.get("surface") or MISSING_UNAVAILABLE),
        "intent": str(identity.get("intent") or MISSING_UNAVAILABLE),
        "preset": str(identity.get("preset") or MISSING_NOT_APPLICABLE),
        "world": str(identity.get("world") or MISSING_UNAVAILABLE),
        "backend": str(identity.get("backend") or MISSING_UNAVAILABLE),
        "evidence_lane": str(identity.get("evidence_lane") or MISSING_UNAVAILABLE),
        "camera_labeler": str(identity.get("camera_labeler") or MISSING_NOT_APPLICABLE),
        "scenario_setup": str(identity.get("scenario_setup") or MISSING_UNAVAILABLE),
        "seed": int(identity.get("seed") or 0),
        "prompt": str(identity.get("prompt") or MISSING_NOT_APPLICABLE),
        "goal_contract_hash": str(identity.get("goal_contract_hash") or MISSING_UNAVAILABLE),
        "allowed_agent_engines": [str(identity.get("agent_engine") or MISSING_UNAVAILABLE)],
        "provider_profiles": [provider_profile],
        "trial_count": 1,
        "required_graders": list(suite.get("required_graders") or ("artifacts", "privacy")),
        "private_goal_reference": {
            "schema": "household_eval_private_goal_reference_v1",
            "private_truth_scope": "grader_only",
        },
        "launch_overrides": {
            "agent_engine": str(identity.get("agent_engine") or MISSING_UNAVAILABLE),
            "evidence_lane": str(identity.get("evidence_lane") or MISSING_UNAVAILABLE),
            "seed": int(identity.get("seed") or 0),
            "scenario_setup": str(identity.get("scenario_setup") or MISSING_UNAVAILABLE),
        },
    }


def _private_goal_reference(
    value: Any,
    *,
    result: dict[str, Any],
    bundle: dict[str, Any],
    eval_results_path: Path,
    identity: dict[str, Any],
    review_label: str,
) -> dict[str, Any]:
    reference = dict(value) if isinstance(value, dict) else {}
    reference.setdefault("schema", "household_eval_private_goal_reference_v1")
    reference["private_truth_scope"] = "grader_only"
    artifacts = _mapping(result.get("artifacts"))
    reference["regression_promotion"] = {
        "schema": PROMOTION_SCHEMA,
        "review_label": review_label,
        "source_eval_results": str(eval_results_path),
        "source_suite_id": str(bundle.get("suite", {}).get("suite_id") or MISSING_UNAVAILABLE),
        "source_sample_id": str(identity.get("sample_id") or MISSING_UNAVAILABLE),
        "source_trial_id": str(identity.get("trial_id") or MISSING_UNAVAILABLE),
        "source_status": str(result.get("status") or MISSING_UNAVAILABLE),
        "source_failure_class": str(result.get("failure_class") or MISSING_UNAVAILABLE),
        "source_artifacts": {
            key: str(artifacts[key])
            for key in ("run_result", "report", "trace", "run_dir")
            if key in artifacts
        },
        "private_truth_scope": "grader_only",
        "agent_input_policy": "do_not_expose_private_goal_reference",
    }
    return reference


def _updated_suite_payload(
    suite_payload: dict[str, Any],
    *,
    sample_id: str,
    sample_ref: str,
    result: dict[str, Any],
    review_label: str,
) -> dict[str, Any]:
    payload = json.loads(json.dumps(suite_payload))
    sample_ids = [str(item) for item in payload.get("sample_ids") or []]
    sample_refs = [str(item) for item in payload.get("sample_refs") or []]
    if sample_id in sample_ids:
        index = sample_ids.index(sample_id)
        if index < len(sample_refs):
            sample_refs[index] = sample_ref
    else:
        sample_ids.append(sample_id)
        sample_refs.append(sample_ref)
    payload["sample_ids"] = sample_ids
    payload["sample_refs"] = sample_refs
    metadata = dict(payload.get("metadata") or {})
    promotions = list(metadata.get("regression_promotions") or [])
    identity = _mapping(result.get("identity"))
    promotions = [
        item
        for item in promotions
        if not (isinstance(item, dict) and item.get("sample_id") == sample_id)
    ]
    promotions.append(
        {
            "sample_id": sample_id,
            "review_label": review_label,
            "source_sample_id": str(identity.get("sample_id") or MISSING_UNAVAILABLE),
            "source_failure_class": str(result.get("failure_class") or MISSING_UNAVAILABLE),
            "private_truth_scope": "grader_only",
        }
    )
    metadata["regression_promotions"] = promotions
    metadata["regression_sample_count"] = len(promotions)
    payload["metadata"] = metadata
    return payload


def _source_sample(bundle: dict[str, Any], identity: dict[str, Any]) -> EvalSample | None:
    sample_id = str(identity.get("sample_id") or "")
    suite = _mapping(bundle.get("suite"))
    for ref in suite.get("sample_refs") or ():
        path = _repo_path(str(ref))
        try:
            sample = load_eval_sample(path)
        except (OSError, ValueError):
            continue
        if sample.sample_id == sample_id:
            return sample
    return None


def _suite_payload(bundle: dict[str, Any], *, suite_path: Path | None) -> dict[str, Any]:
    if suite_path is not None:
        return _load_json(Path(suite_path))
    return dict(_mapping(bundle.get("suite")))


def _default_suite_path(bundle: dict[str, Any]) -> Path:
    suite = _mapping(bundle.get("suite"))
    suite_id = str(suite.get("suite_id") or "")
    short = suite_id.removeprefix("household_world.")
    if short:
        return REPO_ROOT / "evals" / "household_world" / "suites" / f"{short}.json"
    raise ValueError("suite_output_path is required when eval bundle has no suite_id")


def _default_sample_output_path(sample_id: str) -> Path:
    return (
        REPO_ROOT
        / "evals"
        / "household_world"
        / "samples"
        / "regressions"
        / (_path_token(sample_id) + ".json")
    )


def _default_regression_sample_id(identity: dict[str, Any], failure_class: str) -> str:
    source = str(identity.get("sample_id") or "unknown_sample")
    return f"regression.{source}.{failure_class}"


def _sample_ref(path: Path) -> str:
    path = Path(path)
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def _repo_path(ref: str) -> Path:
    path = Path(ref)
    return path if path.is_absolute() else REPO_ROOT / path


def _path_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON file {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return payload


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
