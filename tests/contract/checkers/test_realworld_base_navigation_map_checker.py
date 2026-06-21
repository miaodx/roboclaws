from __future__ import annotations

import pytest

from roboclaws.maps.base_waypoints import (
    BASE_WAYPOINT_GENERATION_POLICY,
    BASE_WAYPOINT_PURPOSE,
    BASE_WAYPOINT_SOURCE,
)
from scripts.molmo_cleanup import check_molmo_realworld_cleanup_result as result_checker
from scripts.molmo_cleanup.realworld_base_navigation_map_checker import (
    assert_base_navigation_map,
)


def test_checker_accepts_canonical_base_area_inspection_waypoints() -> None:
    agent_view = _agent_view_with_waypoint(_canonical_base_waypoint())
    data = {"runtime_metric_map": agent_view["runtime_metric_map"]}

    assert_base_navigation_map(data, agent_view)


def test_checker_rejects_fixture_fields_on_canonical_base_waypoints() -> None:
    waypoint = _canonical_base_waypoint()
    waypoint["fixture_id"] = "private_fixture"
    agent_view = _agent_view_with_waypoint(waypoint)
    data = {"runtime_metric_map": agent_view["runtime_metric_map"]}

    with pytest.raises(AssertionError):
        assert_base_navigation_map(data, agent_view)


def test_semantic_success_gate_uses_score_acceptability_not_substep_count() -> None:
    opts = result_checker._result_assert_options(
        {
            "min_generated_mess_count": 5,
            "min_semantic_accepted_count": 5,
        }
    )
    data = {
        "generated_mess_count": 5,
        "sweep_coverage_rate": 1.0,
        "disturbance_count": 0,
        "private_evaluation": {
            "generated_mess_count": 5,
            "acceptable_destination_sets": {"obj": ["sink"]},
        },
        "score": {
            "semantic_acceptability": {
                "status": "success",
                "accepted_count": 5,
                "accepted_levels": ["preferred", "acceptable"],
            }
        },
        "semantic_substeps": [
            {"steps": [{"phase": "navigate_to_object", "ok": True}]},
        ],
    }

    result_checker._assert_core_cleanup_success(data, opts, semantic_success_gate=True)
    result_checker._assert_core_thresholds(data, opts)
    result_checker._assert_private_evaluation_and_semantic_success(
        data,
        opts,
        enforce_success=True,
        semantic_success_gate=True,
    )


def _canonical_base_waypoint() -> dict[str, object]:
    return {
        "waypoint_id": "room_2_inspection",
        "waypoint_source": BASE_WAYPOINT_SOURCE,
        "purpose": BASE_WAYPOINT_PURPOSE,
        "generation_policy": BASE_WAYPOINT_GENERATION_POLICY,
        "navigation_area_id": "room_2",
        "frame_id": "map",
        "x": 6.4,
        "y": 7.5,
        "yaw": 0.0,
        "room_id": "room_2",
        "room_label": "Kitchen",
        "label": "Kitchen",
        "sweep_index": 1,
    }


def _agent_view_with_waypoint(waypoint: dict[str, object]) -> dict[str, object]:
    room = {
        "room_id": "room_2",
        "room_label": "Kitchen",
        "navigation_area_id": "room_2",
    }
    runtime_map = {
        "schema": "runtime_metric_map_v1",
        "source_map_mutated": False,
        "static_map": {
            "rooms": [dict(room)],
            "fixtures": [],
            "driveable_ways": [],
        },
        "generated_exploration_candidates": [dict(waypoint)],
        "generated_target_inspection_candidates": [],
        "public_semantic_anchors": [
            {
                "anchor_id": "anchor_waypoint_room_2_inspection",
                "anchor_type": "observation_waypoint",
                "waypoint_id": "room_2_inspection",
            }
        ],
    }
    return {
        "metric_map": {
            "base_navigation_map": {"enabled": True},
            "rooms": [room],
            "driveable_ways": [],
            "room_category_hints": [
                {
                    "anchor_id": "anchor_room_2",
                    "anchor_type": "room_area",
                    "room_id": "room_2",
                }
            ],
            "inspection_waypoints": [dict(waypoint)],
        },
        "static_fixture_projection": {
            "schema": "static_fixture_projection_v1",
            "rooms": [],
        },
        "runtime_metric_map": runtime_map,
    }
