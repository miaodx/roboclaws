"""Operator safety gates for Agibot physical navigation pilots."""

from __future__ import annotations

from typing import Any

AGIBOT_GDK_RELATIVE_MOVE_PROVENANCE = "agibot_gdk_relative_move"
AGIBOT_BOUNDED_LOCAL_NUDGE_DEFAULTS = {
    "max_distance_m": 0.25,
    "max_yaw_rad": 0.35,
    "timeout_s": 3.0,
    "operator_config_required": True,
}
HUMAN_TAKEOVER_FAILURE_TYPES = {
    "operator_localization_gate_not_confirmed",
    "operator_run_enablement_gate_not_confirmed",
    "map_mismatch",
    "current_map_mismatch",
    "timeout",
    "pnc_busy",
    "pnc_failed",
    "gdk_localization_not_ready",
    "normal_navi_exception",
    "local_motion_failed",
    "relative_move_failed",
    "bounded_local_nudge_failed",
    "robot_obstacle_stop",
    "human_emergency_stop",
}


def operator_localization_gate(context: dict[str, Any]) -> dict[str, Any]:
    gate = context.get("operator_localization_gate")
    if not isinstance(gate, dict):
        return {
            "schema": "operator_localization_gate_v1",
            "ok": False,
            "status": "missing",
            "selected_map_confirmed": False,
            "g02_pad_relocalized": False,
            "localization_ready": False,
            "reason": "operator_localization_gate is missing from the AgiBot context.",
        }
    selected_map_confirmed = bool(
        gate.get("selected_map_confirmed")
        or gate.get("map_selected")
        or gate.get("selected_map_confirmed_at")
    )
    g02_pad_relocalized = bool(
        gate.get("g02_pad_relocalized")
        or gate.get("relocalized_on_g02_pad")
        or gate.get("relocalized")
    )
    localization_ready = bool(gate.get("localization_ready") or gate.get("ready"))
    min_confidence_configured = gate.get("min_localization_confidence") not in (None, "")
    min_confidence = _optional_float(gate.get("min_localization_confidence"))
    confidence = _optional_float(gate.get("localization_confidence"))
    confidence_ok = (
        not min_confidence_configured
        if min_confidence is None
        else confidence is not None and confidence >= min_confidence
    )
    accepted_states = _accepted_localization_states(gate.get("accepted_localization_states"))
    localization_state = str(gate.get("localization_state") or "")
    state_ok = not accepted_states or localization_state in accepted_states
    ok = (
        selected_map_confirmed
        and g02_pad_relocalized
        and localization_ready
        and confidence_ok
        and state_ok
    )
    return {
        "schema": "operator_localization_gate_v1",
        "ok": ok,
        "status": "confirmed" if ok else "incomplete",
        "selected_map_confirmed": selected_map_confirmed,
        "g02_pad_relocalized": g02_pad_relocalized,
        "localization_ready": localization_ready,
        "localization_confidence": confidence,
        "min_localization_confidence": min_confidence,
        "localization_confidence_ok": confidence_ok,
        "localization_state": localization_state,
        "accepted_localization_states": sorted(accepted_states),
        "localization_state_ok": state_ok,
        "operator": str(gate.get("operator") or ""),
        "confirmed_at": str(gate.get("confirmed_at") or ""),
        "reason": ""
        if ok
        else (
            "selected map, G02 Pad relocalization, localization ready, and any "
            "operator-configured confidence/state thresholds are required."
        ),
    }


def operator_run_enablement_gate(
    context: dict[str, Any],
    *,
    movement_enabled: bool,
) -> dict[str, Any]:
    gate = context.get("operator_run_enablement_gate")
    if not movement_enabled:
        return {
            "schema": "operator_run_enablement_gate_v1",
            "ok": False,
            "status": "not_requested",
            "movement_enabled": False,
            "scope": "session",
            "reason": "real movement was not enabled for this rehearsal.",
        }
    if not isinstance(gate, dict):
        return {
            "schema": "operator_run_enablement_gate_v1",
            "ok": False,
            "status": "missing",
            "movement_enabled": True,
            "scope": "session",
            "reason": "operator_run_enablement_gate is missing from the AgiBot context.",
        }
    enabled = bool(
        gate.get("enabled")
        or gate.get("confirmed")
        or gate.get("autonomous_navigation_enabled")
        or gate.get("run_enabled")
    )
    return {
        "schema": "operator_run_enablement_gate_v1",
        "ok": enabled,
        "status": "confirmed" if enabled else "incomplete",
        "movement_enabled": True,
        "scope": str(gate.get("scope") or "session"),
        "operator": str(gate.get("operator") or ""),
        "confirmed_at": str(gate.get("confirmed_at") or ""),
        "reason": "" if enabled else "operator run enablement was not confirmed.",
    }


def bounded_local_nudge_status(
    *,
    enabled: bool,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = _operator_bounded_local_nudge_config(context or {})
    return {
        "schema": "agibot_bounded_local_nudge_v1",
        "status": "not_requested",
        "enabled": enabled,
        "primitive_provenance": AGIBOT_GDK_RELATIVE_MOVE_PROVENANCE if enabled else "",
        "max_distance_m": config["max_distance_m"],
        "max_yaw_rad": config["max_yaw_rad"],
        "timeout_s": config["timeout_s"],
        "operator_config_required": config["operator_config_required"],
        "operator_config_present": config["operator_config_present"],
        "operator_config_valid": config["operator_config_valid"],
        "operator_config_source": config["operator_config_source"],
        "config_reason": config["reason"],
        "safety_model": "Pnc.relative_move simple obstacle stop; no obstacle avoidance",
        "agent_facing_tool": False,
    }


def human_takeover_stop_required(
    observation: dict[str, Any],
    navigation: dict[str, Any],
) -> bool:
    failure_types = {
        str(observation.get("failure_type") or ""),
        str(navigation.get("failure_type") or ""),
    }
    return bool(HUMAN_TAKEOVER_FAILURE_TYPES & failure_types)


def _operator_bounded_local_nudge_config(context: dict[str, Any]) -> dict[str, Any]:
    raw = context.get("operator_bounded_local_nudge")
    if raw is None:
        raw = context.get("bounded_local_nudge")
    if not isinstance(raw, dict):
        return {
            **AGIBOT_BOUNDED_LOCAL_NUDGE_DEFAULTS,
            "operator_config_present": False,
            "operator_config_valid": False,
            "operator_config_source": "",
            "reason": (
                "operator bounded local nudge config is missing; conservative defaults apply."
            ),
        }

    max_distance = _optional_float(raw.get("max_distance_m"))
    max_yaw = _optional_float(raw.get("max_yaw_rad"))
    timeout = _optional_float(raw.get("timeout_s"))
    valid = (
        bool(raw.get("operator_configured") or raw.get("confirmed"))
        and max_distance is not None
        and 0.0 < max_distance <= AGIBOT_BOUNDED_LOCAL_NUDGE_DEFAULTS["max_distance_m"]
        and max_yaw is not None
        and 0.0 < max_yaw <= AGIBOT_BOUNDED_LOCAL_NUDGE_DEFAULTS["max_yaw_rad"]
        and timeout is not None
        and 0.0 < timeout <= AGIBOT_BOUNDED_LOCAL_NUDGE_DEFAULTS["timeout_s"]
    )
    if not valid:
        return {
            **AGIBOT_BOUNDED_LOCAL_NUDGE_DEFAULTS,
            "operator_config_present": True,
            "operator_config_valid": False,
            "operator_config_source": str(raw.get("source") or "operator_bounded_local_nudge"),
            "reason": (
                "operator bounded local nudge config must be confirmed and no larger "
                "than conservative defaults."
            ),
        }
    return {
        "max_distance_m": max_distance,
        "max_yaw_rad": max_yaw,
        "timeout_s": timeout,
        "operator_config_required": True,
        "operator_config_present": True,
        "operator_config_valid": True,
        "operator_config_source": str(raw.get("source") or "operator_bounded_local_nudge"),
        "reason": "",
    }


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _accepted_localization_states(value: Any) -> set[str]:
    if isinstance(value, str):
        return {item.strip() for item in value.split(",") if item.strip()}
    if isinstance(value, list | tuple | set):
        return {str(item).strip() for item in value if str(item).strip()}
    return set()
