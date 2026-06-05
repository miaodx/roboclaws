"""Canonical RAW_FPV visual-candidate guidance shared by prompts and contract."""

from __future__ import annotations

from typing import Any

RAW_FPV_DECLARATION_STRATEGY = "inline_on_navigate"
RAW_FPV_CATEGORY_HINT = "food, dish, book, linen, toy, electronics, or pillow"
RAW_FPV_ACCEPTED_IMAGE_REGION_FORMS: tuple[dict[str, Any], ...] = (
    {"type": "bbox", "value": [0.1, 0.2, 0.3, 0.4]},
    {"type": "point", "value": [390, 230]},
    {"type": "verbal_region", "value": "front of desk"},
)
RAW_FPV_INVALID_FIELDS_TO_AVOID: tuple[str, ...] = (
    "bbox_normalized",
    "bare x/y/width/height fields",
    'target_fixture_id=""',
    'target_fixture_id="None"',
    "target_fixture_id=null",
)


def raw_fpv_inline_candidate_instruction(observation_id: str | None = None) -> str:
    subject = (
        f"observation_id={observation_id}" if observation_id else "the current raw FPV observation"
    )
    return (
        f"Raw FPV-only mode uses {RAW_FPV_DECLARATION_STRATEGY}: inspect the FPV "
        f"image block for {subject}, do not batch-register candidates first, "
        "and call navigate_to_visual_candidate only when acting on a plausible "
        "cleanup object. Use the exact visual class when the image makes it clear "
        "(for example plate, cup, potato, remotecontrol, book, or pillow). Use "
        "broader cleanup categories such as "
        f"{RAW_FPV_CATEGORY_HINT} only when the exact object class is uncertain. "
        "Call navigate_to_visual_candidate with source_observation_id, category, "
        "evidence_note, and image_region before pick. In minimal map mode, omit "
        "target_fixture_id; do not invent fixture ids from empty fixture_hints. "
        "Use the candidate_fixture_id/recommended_tool returned by "
        "navigate_to_visual_candidate plus runtime_metric_map.public_semantic_anchors. "
        "In explicit rich legacy/debug mode only, target_fixture_id may come from "
        "non-empty fixture_hints. For any candidate you want to navigate to or pick, "
        "use image_region={type:bbox,value:[x,y,width,height]} from the visible "
        "agent-facing FPV object. Verbal regions are accepted for clarification but "
        "are not actionable without a reviewable bbox. Never send bbox_normalized, "
        "bare x/y/width/height fields, "
        'target_fixture_id="", target_fixture_id="None", or target_fixture_id=null. '
        "After a successful pick/place for an observed handle, do not act on "
        "that same handle again; if grounding resolves to an already-handled "
        "object, continue the waypoint sweep."
    )


def raw_fpv_visual_candidate_recovery(
    *,
    source_observation_id: str | None = None,
    map_mode: str = "minimal",
) -> dict[str, Any]:
    example: dict[str, Any] = {
        "source_observation_id": source_observation_id or "<raw_fpv_observation_id>",
        "category": "toy",
        "evidence_note": "small object visible on the bed",
        "image_region": {"type": "bbox", "value": [0.1, 0.2, 0.3, 0.4]},
    }
    minimal_map = map_mode == "minimal"
    if not minimal_map:
        example["target_fixture_id"] = "<fixture_id_from_non_empty_fixture_hints>"
    return {
        "schema": "raw_fpv_visual_candidate_recovery_v1",
        "required_tool": "navigate_to_visual_candidate",
        "required_next_action": "retry_navigate_to_visual_candidate",
        "declaration_strategy": RAW_FPV_DECLARATION_STRATEGY,
        "minimal_map_target_fixture_rule": "omit_target_fixture_id"
        if minimal_map
        else "target_fixture_id_may_come_from_non_empty_fixture_hints",
        "accepted_image_region_forms": [dict(item) for item in RAW_FPV_ACCEPTED_IMAGE_REGION_FORMS],
        "invalid_fields_to_avoid": list(RAW_FPV_INVALID_FIELDS_TO_AVOID),
        "valid_example": example,
        "instruction": raw_fpv_inline_candidate_instruction(source_observation_id),
    }


def raw_fpv_visual_candidate_recovery_hint(
    *,
    source_observation_id: str | None = None,
    map_mode: str = "minimal",
) -> str:
    target_rule = (
        "omit target_fixture_id in minimal map mode"
        if map_mode == "minimal"
        else "use target_fixture_id only from non-empty fixture_hints"
    )
    observation = source_observation_id or "<raw_fpv_observation_id>"
    return (
        "Retry with a valid navigate_to_visual_candidate example: "
        f"source_observation_id={observation}, category=toy, evidence_note='small object "
        "visible on the bed', image_region={type:bbox,value:[0.1,0.2,0.3,0.4]}; "
        f"{target_rule}. Avoid bbox_normalized, bare x/y/width/height fields, "
        'target_fixture_id="", target_fixture_id="None", and target_fixture_id=null.'
    )
