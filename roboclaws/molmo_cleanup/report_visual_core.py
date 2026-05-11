from __future__ import annotations

VISUAL_CORE_BASE_SECTIONS = ("Before And After", "Object Moves", "Score")
VISUAL_CORE_SEMANTIC_SECTION = "Semantic Substeps"
VISUAL_CORE_ROBOT_SECTION = "Robot View Timeline"
VISUAL_CORE_AGENT_SECTION = "Agent View"
VISUAL_CORE_PRIVATE_SECTION = "Private Evaluation"
CANONICAL_SEMANTIC_SUBPHASES = ("nav/object", "pick/object", "nav/target")
CANONICAL_PLACE_SUBPHASES = ("place/surface", "place/inside")


def assert_cleanup_report_visual_core(
    report_text: str,
    *,
    require_semantic_subphases: bool = False,
    require_robot_timeline: bool = False,
    require_agent_view: bool = False,
    require_private_evaluation: bool = False,
) -> None:
    """Assert the shared Cleanup Artifact Report visual core contract."""
    ordered = [
        VISUAL_CORE_BASE_SECTIONS[0],
        VISUAL_CORE_BASE_SECTIONS[1],
    ]
    if require_semantic_subphases:
        ordered.append(VISUAL_CORE_SEMANTIC_SECTION)
    if require_robot_timeline:
        ordered.append(VISUAL_CORE_ROBOT_SECTION)
    ordered.append(VISUAL_CORE_BASE_SECTIONS[2])
    _assert_sections_in_order(report_text, ordered)

    if require_semantic_subphases:
        _assert_semantic_subphases(report_text)
    if require_robot_timeline:
        assert VISUAL_CORE_ROBOT_SECTION in report_text, report_text[:500]
    if require_agent_view:
        assert VISUAL_CORE_AGENT_SECTION in report_text, report_text[:500]
        _assert_after(report_text, VISUAL_CORE_AGENT_SECTION, VISUAL_CORE_BASE_SECTIONS[2])
    if require_private_evaluation:
        assert VISUAL_CORE_PRIVATE_SECTION in report_text, report_text[:500]
        _assert_after(report_text, VISUAL_CORE_PRIVATE_SECTION, VISUAL_CORE_BASE_SECTIONS[2])


def _assert_sections_in_order(report_text: str, sections: list[str]) -> None:
    previous_index = -1
    for section in sections:
        index = _section_index(report_text, section)
        assert index >= 0, (section, report_text[:500])
        assert index > previous_index, (sections, section, previous_index, index)
        previous_index = index


def _assert_semantic_subphases(report_text: str) -> None:
    assert "phase-rail" in report_text, report_text[:500]
    for subphase in CANONICAL_SEMANTIC_SUBPHASES:
        assert _has_subphase(report_text, subphase), (subphase, report_text[:500])
    assert any(_has_subphase(report_text, subphase) for subphase in CANONICAL_PLACE_SUBPHASES), (
        CANONICAL_PLACE_SUBPHASES,
        report_text[:500],
    )


def _assert_after(report_text: str, later: str, earlier: str) -> None:
    later_index = _section_index(report_text, later)
    earlier_index = _section_index(report_text, earlier)
    assert later_index >= 0 and earlier_index >= 0, (later, earlier, report_text[:500])
    assert later_index > earlier_index, (later, earlier, later_index, earlier_index)


def _section_index(report_text: str, section: str) -> int:
    heading = f"<h2>{section}</h2>"
    index = report_text.find(heading)
    if index >= 0:
        return index
    return report_text.find(section)


def _has_subphase(report_text: str, subphase: str) -> bool:
    if subphase in report_text:
        return True
    label, detail = subphase.split("/", 1)
    return f"<span>{label}</span><small>{detail}</small>" in report_text
