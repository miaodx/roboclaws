from __future__ import annotations

import pytest

from roboclaws.household.evidence_lane_policy import evidence_lane_compatibility


def test_raw_fpv_rejects_route_incompatible_model_override() -> None:
    with pytest.raises(
        ValueError,
        match=("model 'mimo-1000' is incompatible with provider_profile 'mimo-mify-responses'"),
    ):
        evidence_lane_compatibility(
            evidence_lane="camera-raw-fpv",
            agent_engine="codex-cli",
            provider_profile="mimo-mify-responses",
            model_id="mimo-1000",
        )


def test_raw_fpv_still_reports_image_transport_for_route_compatible_model() -> None:
    compatibility = evidence_lane_compatibility(
        evidence_lane="camera-raw-fpv",
        agent_engine="codex-cli",
        provider_profile="mimo-mify-responses",
        model_id="xiaomi/mimo-v2.5",
    )

    assert compatibility.allowed is False
    assert "image_transport=unknown" in compatibility.reason
