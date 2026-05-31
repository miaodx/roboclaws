from __future__ import annotations

import pytest

from scripts.isaac_lab_cleanup.check_prepared_semantic_usd_summary import (
    assert_prepared_semantic_usd_summary_ready,
)


def test_prepared_semantic_usd_summary_ready() -> None:
    assert_prepared_semantic_usd_summary_ready(
        {
            "status": "ready",
            "matched_entry_count": 2,
            "labeled_entry_count": 2,
            "renderable_labeled_prim_count": 8,
            "scene_metadata_copied": True,
        }
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", "partial"),
        ("matched_entry_count", 0),
        ("labeled_entry_count", 0),
        ("renderable_labeled_prim_count", 0),
        ("scene_metadata_copied", False),
    ],
)
def test_prepared_semantic_usd_summary_rejects_incomplete_evidence(
    field: str,
    value: object,
) -> None:
    summary = {
        "status": "ready",
        "matched_entry_count": 2,
        "labeled_entry_count": 2,
        "renderable_labeled_prim_count": 8,
        "scene_metadata_copied": True,
    }
    summary[field] = value

    with pytest.raises(AssertionError):
        assert_prepared_semantic_usd_summary_ready(summary)
