from __future__ import annotations

import html
from typing import Any


def action_evidence_summary(step: dict[str, Any]) -> str:
    evidence = step.get("action_evidence")
    if not isinstance(evidence, dict) or not evidence:
        return ""
    badges = _action_evidence_badges(evidence)
    note = str(evidence.get("evidence_note") or evidence.get("grounding_basis") or "")
    note_html = f'<p class="note action-evidence-note">{html.escape(note)}</p>' if note else ""
    if not badges and not note_html:
        return ""
    return '<div class="action-evidence-badges">' + "".join(badges) + f"</div>{note_html}"


def _action_evidence_badges(evidence: dict[str, Any]) -> list[str]:
    badges = []
    for label, value in _simple_action_evidence_badges(evidence):
        if value:
            badges.append(_badge(label, value))
    grounding = _grounding_badge_value(evidence)
    if grounding:
        badges.append(_badge("Grounding", grounding))
    for label, value in _resolved_action_evidence_badges(evidence):
        if value:
            badges.append(_badge(label, value))
    return badges


def _simple_action_evidence_badges(evidence: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        ("Agent tool", evidence.get("agent_tool")),
        ("Source observe", evidence.get("source_observation_id")),
        ("Source FPV bbox", _format_bbox(evidence.get("source_image_bbox"))),
        ("BBox review", evidence.get("reviewability_status")),
        ("Locality", evidence.get("locality_status")),
        ("Candidate state", evidence.get("candidate_state")),
        ("Authorization", evidence.get("actionability_status")),
    ]


def _resolved_action_evidence_badges(evidence: dict[str, Any]) -> list[tuple[str, Any]]:
    return [
        ("Resolved handle", evidence.get("resolved_object_id")),
        ("Backend primitive", evidence.get("backend_primitive")),
        ("Declared category", evidence.get("declared_category")),
        ("Public target", evidence.get("target_fixture_id")),
    ]


def _grounding_badge_value(evidence: dict[str, Any]) -> str:
    if not evidence.get("grounding_status"):
        return ""
    grounding = str(evidence["grounding_status"])
    if evidence.get("grounding_confidence") is not None:
        grounding += f" ({evidence['grounding_confidence']})"
    return grounding


def _format_bbox(value: Any) -> str:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        return ""
    return "[" + ", ".join(_format_bbox_value(item) for item in value) + "]"


def _format_bbox_value(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _badge(label: str, value: Any) -> str:
    return (
        f'<span class="badge">{html.escape(str(label))}: '
        f"<strong>{html.escape(str(value))}</strong></span>"
    )
