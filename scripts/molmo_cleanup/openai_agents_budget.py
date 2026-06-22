from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.agents.live_status import LiveAgentFailure
from roboclaws.core.json_sources import read_jsonl_objects


def raw_fpv_budget_failure(
    run_dir: Path,
    timing: dict[str, Any],
    profile: dict[str, Any],
) -> LiveAgentFailure | None:
    if str(timing.get("evidence_lane") or timing.get("profile") or "") != "camera-raw-fpv":
        return None
    limits = _raw_fpv_budget_limits(profile)
    if not limits:
        return None
    trace_events = _read_jsonl_path(run_dir / "trace.jsonl")
    if not trace_events:
        return None
    metrics = raw_fpv_budget_metrics(trace_events)
    reasons = _raw_fpv_budget_reasons(metrics, limits)
    if not reasons:
        return None
    detail = json.dumps(
        {
            "schema": "agent_sdk_raw_fpv_budget_terminal_v1",
            "profile_id": profile.get("profile_id") or "baseline",
            "reasons": reasons,
            "raw_fpv_candidate_budget": limits["candidate_budget"],
            "raw_fpv_repeated_failure_limit": limits["repeated_failure_limit"],
            "max_observe_per_waypoint": limits["observe_budget"],
            **metrics,
        },
        sort_keys=True,
    )
    return LiveAgentFailure(
        _primary_raw_fpv_budget_reason(reasons),
        retryable=False,
        resume_available=False,
        detail=detail,
    )


def raw_fpv_budget_metrics(trace_events: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_attempts: list[dict[str, str]] = []
    observe_count_by_waypoint: dict[str, int] = {}
    failure_fingerprints: dict[str, int] = {}
    failure_fingerprint_details: dict[str, dict[str, str]] = {}
    for event in trace_events:
        tool = str(event.get("tool") or "")
        event_type = str(event.get("event") or "")
        if tool == "observe" and event_type == "response":
            _record_observe_response(event, observe_count_by_waypoint)
            continue
        if tool not in {"navigate_to_visual_candidate", "declare_visual_candidates"}:
            continue
        raw_event = _raw_fpv_candidate_event(event)
        if raw_event is None:
            continue
        if event_type == "request":
            candidate_attempts.append(raw_event.attempt)
        if event_type == "response" and raw_event.failure_reason:
            failure_fingerprints[raw_event.fingerprint] = (
                failure_fingerprints.get(raw_event.fingerprint, 0) + 1
            )
            failure_fingerprint_details.setdefault(raw_event.fingerprint, raw_event.detail)
    return {
        "candidate_attempt_count": len(candidate_attempts),
        "candidate_attempts_sample": candidate_attempts[-12:],
        "observe_count_by_waypoint": dict(sorted(observe_count_by_waypoint.items())),
        "repeated_failure_fingerprints": _repeated_failure_fingerprints(
            failure_fingerprints,
            failure_fingerprint_details,
        ),
    }


class _RawFpvCandidateEvent:
    def __init__(
        self,
        *,
        source_id: str,
        category: str,
        region: str,
        candidate_id: str,
        failure_reason: str,
    ) -> None:
        self.failure_reason = failure_reason
        self.attempt = {
            "source_observation_id": source_id,
            "category": category,
            "region": region,
            "candidate_id": candidate_id,
        }
        self.fingerprint = "|".join((source_id, category, region, candidate_id, failure_reason))
        self.detail = {
            "source_observation_id": source_id,
            "category": category,
            "region": region,
            "candidate_id": candidate_id,
            "failure_reason": failure_reason,
        }


def _raw_fpv_budget_limits(profile: dict[str, Any]) -> dict[str, int | None]:
    limits = {
        "candidate_budget": _int_or_none(profile.get("raw_fpv_candidate_budget")),
        "repeated_failure_limit": _int_or_none(profile.get("raw_fpv_repeated_failure_limit")),
        "observe_budget": _int_or_none(profile.get("max_observe_per_waypoint")),
    }
    return {} if all(value is None for value in limits.values()) else limits


def _raw_fpv_budget_reasons(
    metrics: dict[str, Any],
    limits: dict[str, int | None],
) -> list[str]:
    reasons: list[str] = []
    repeated_failure_limit = limits["repeated_failure_limit"]
    if repeated_failure_limit is not None:
        repeated_failures = [
            item
            for item in metrics["repeated_failure_fingerprints"]
            if int(item.get("count") or 0) >= repeated_failure_limit
        ]
        if repeated_failures:
            metrics["repeated_failure_limit"] = repeated_failure_limit
            metrics["repeated_failure_limit_hits"] = repeated_failures[:12]
            reasons.append("raw_fpv_repeated_candidate_failure")
    candidate_budget = limits["candidate_budget"]
    if candidate_budget is not None and metrics["candidate_attempt_count"] >= candidate_budget:
        reasons.append("raw_fpv_candidate_budget_exhausted")
    observe_budget = limits["observe_budget"]
    if observe_budget is not None:
        over_budget = {
            waypoint_id: count
            for waypoint_id, count in metrics["observe_count_by_waypoint"].items()
            if waypoint_id and count > observe_budget
        }
        if over_budget:
            metrics["observe_over_budget_by_waypoint"] = dict(sorted(over_budget.items()))
            reasons.append("raw_fpv_observe_budget_exhausted")
    return reasons


def _primary_raw_fpv_budget_reason(reasons: list[str]) -> str:
    for reason in (
        "raw_fpv_repeated_candidate_failure",
        "raw_fpv_candidate_budget_exhausted",
        "raw_fpv_observe_budget_exhausted",
    ):
        if reason in reasons:
            return reason
    return "raw_fpv_candidate_budget_exhausted"


def _record_observe_response(
    event: dict[str, Any],
    observe_count_by_waypoint: dict[str, int],
) -> None:
    response = event.get("response") if isinstance(event.get("response"), dict) else {}
    waypoint_id = _waypoint_from_response(response)
    observe_count_by_waypoint[waypoint_id] = observe_count_by_waypoint.get(waypoint_id, 0) + 1


def _raw_fpv_candidate_event(event: dict[str, Any]) -> _RawFpvCandidateEvent | None:
    request = event.get("request") if isinstance(event.get("request"), dict) else {}
    response = event.get("response") if isinstance(event.get("response"), dict) else {}
    source_id = str(
        request.get("source_observation_id")
        or request.get("observation_id")
        or response.get("observation_id")
        or response.get("source_observation_id")
        or ""
    )
    if not source_id and "raw_fpv" not in json.dumps(event, sort_keys=True, ensure_ascii=True):
        return None
    category = str(request.get("category") or response.get("category") or "")
    region = _region_fingerprint(request.get("image_region"))
    candidate_id = str(response.get("candidate_id") or response.get("object_id") or "")
    failure_reason = str(
        response.get("error_reason")
        or response.get("failure_reason")
        or response.get("status")
        or ""
    )
    return _RawFpvCandidateEvent(
        source_id=source_id,
        category=category,
        region=region,
        candidate_id=candidate_id,
        failure_reason=failure_reason,
    )


def _repeated_failure_fingerprints(
    failure_fingerprints: dict[str, int],
    failure_fingerprint_details: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    return [
        {
            "fingerprint": key,
            "count": count,
            **failure_fingerprint_details.get(key, {}),
        }
        for key, count in sorted(failure_fingerprints.items())
        if count > 1
    ][:12]


def _waypoint_from_response(response: dict[str, Any]) -> str:
    waypoint_id = str(response.get("waypoint_id") or "")
    if waypoint_id:
        return waypoint_id
    raw_payload = response.get("raw_fpv_observation")
    raw = raw_payload if isinstance(raw_payload, dict) else {}
    return str(raw.get("waypoint_id") or "unknown")


def _region_fingerprint(value: Any) -> str:
    if isinstance(value, dict):
        region_type = str(value.get("type") or "")
        region_value = value.get("value")
        if isinstance(region_value, list):
            compact = ",".join(str(item) for item in region_value[:4])
        else:
            compact = str(region_value or "")
        return f"{region_type}:{compact}"[:120]
    return str(value or "")[:120]


def _read_jsonl_path(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    return read_jsonl_objects(path, label="OpenAI Agents budget trace")


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
