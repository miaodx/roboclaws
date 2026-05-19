from __future__ import annotations

from typing import Any

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.semantic_cleanup_loop import run_semantic_cleanup_loop
from roboclaws.molmo_cleanup.semantic_timeline import (
    robot_view_capture_for_tool,
    visual_grounding_status,
)


def test_semantic_cleanup_loop_runs_canonical_fridge_sequence() -> None:
    contract = _FakeCleanupContract()
    calls: list[tuple[str, dict[str, Any]]] = []
    recorded: list[str] = []

    result = run_semantic_cleanup_loop(
        targets=[
            {
                "object_id": "apple_01",
                "target_receptacle_id": "fridge_01",
                "target_receptacle": {"category": "Fridge", "fixture_id": "fridge_01"},
                "source_receptacle_id": "counter_01",
            }
        ],
        contract=contract,
        call_tool=lambda tool, request, fn: _record_call(calls, tool, request, fn),
        record_tool_view=lambda tool, _request, _response: recorded.append(tool),
    )

    assert result.attempted_objects == 1
    assert result.completed_objects == 1
    assert result.failed_objects == ()
    assert [tool for tool, _request in calls] == [
        "navigate_to_object",
        "pick",
        "navigate_to_receptacle",
        "open_receptacle",
        "place_inside",
        "close_receptacle",
    ]
    assert recorded == [tool for tool, _request in calls]
    assert calls[0][1] == {
        "object_id": "apple_01",
        "source_receptacle_id": "counter_01",
    }
    assert calls[3][1] == {
        "object_id": "apple_01",
        "receptacle_id": "fridge_01",
    }
    assert calls[4][1] == {
        "object_id": "apple_01",
        "receptacle_id": "fridge_01",
    }
    assert calls[5][1] == {
        "object_id": "apple_01",
        "receptacle_id": "fridge_01",
    }


def test_semantic_cleanup_loop_preserves_fixture_style_target_requests() -> None:
    contract = _FakeCleanupContract()
    calls: list[tuple[str, dict[str, Any]]] = []

    result = run_semantic_cleanup_loop(
        targets=[
            {
                "object_id": "observed_001",
                "target_receptacle_id": "sink_01",
                "target_receptacle": {"category": "Sink", "fixture_id": "sink_01"},
            }
        ],
        contract=contract,
        target_request_key="fixture_id",
        include_object_id_in_receptacle_request=False,
        include_object_id_in_target_requests=False,
        call_tool=lambda tool, request, fn: _record_call(calls, tool, request, fn),
    )

    assert result.completed_objects == 1
    assert [tool for tool, _request in calls] == [
        "navigate_to_object",
        "pick",
        "navigate_to_receptacle",
        "place",
    ]
    assert calls[2][1] == {"receptacle_id": "sink_01"}
    assert calls[3][1] == {"fixture_id": "sink_01"}


def test_semantic_cleanup_loop_places_inside_open_shelf_without_close() -> None:
    contract = _FakeCleanupContract()
    calls: list[tuple[str, dict[str, Any]]] = []

    result = run_semantic_cleanup_loop(
        targets=[
            {
                "object_id": "book_01",
                "target_receptacle_id": "bookshelf_01",
                "target_receptacle": {"category": "bookshelf", "fixture_id": "bookshelf_01"},
            }
        ],
        contract=contract,
        call_tool=lambda tool, request, fn: _record_call(calls, tool, request, fn),
    )

    assert result.completed_objects == 1
    assert [tool for tool, _request in calls] == [
        "navigate_to_object",
        "pick",
        "navigate_to_receptacle",
        "place_inside",
    ]


def test_robot_view_capture_can_translate_public_handles_to_focus_ids() -> None:
    capture = robot_view_capture_for_tool(
        "place_inside",
        {"fixture_id": "fridge_01"},
        {
            "ok": True,
            "object_id": "observed_001",
            "receptacle_id": "fridge_01",
        },
        object_id_transform=lambda value: "apple_01" if value == "observed_001" else value,
    )

    assert capture is not None
    assert capture["action"] == "place_inside observed_001"
    assert capture["label_suffix"] == "place_inside_observed_001"
    assert capture["focus_object_id"] == "apple_01"
    assert capture["focus_receptacle_id"] == "fridge_01"


def test_robot_view_capture_records_close_receptacle_focus() -> None:
    capture = robot_view_capture_for_tool(
        "close_receptacle",
        {"fixture_id": "fridge_01", "object_id": "observed_001"},
        {
            "ok": True,
            "object_id": "observed_001",
            "receptacle_id": "fridge_01",
        },
    )

    assert capture is not None
    assert capture["action"] == "close_receptacle fridge_01"
    assert capture["label_suffix"] == "close_receptacle_fridge_01"
    assert capture["focus_object_id"] == "observed_001"
    assert capture["focus_receptacle_id"] == "fridge_01"


def test_visual_grounding_only_hides_closed_container_contents() -> None:
    visibility = {"status": "ok", "object_pixels": 0}

    assert (
        visual_grounding_status(
            {
                "object_id": "apple_01",
                "receptacle_id": "fridge_01",
                "receptacle_category": "Fridge",
                "object_contained_in": "fridge_01",
                "object_location_relation": "inside",
            },
            visibility,
        )
        == "contained_inside"
    )
    assert (
        visual_grounding_status(
            {
                "object_id": "book_01",
                "receptacle_id": "shelf_01",
                "receptacle_category": "ShelvingUnit",
                "object_contained_in": "shelf_01",
                "object_location_relation": "inside",
            },
            visibility,
        )
        == "weak_object_visibility"
    )


def _record_call(
    calls: list[tuple[str, dict[str, Any]]],
    tool: str,
    request: dict[str, Any],
    fn: Any,
) -> dict[str, Any]:
    calls.append((tool, dict(request)))
    return fn()


class _FakeCleanupContract:
    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        return _ok(
            "navigate_to_object",
            object_id=object_id,
            source_receptacle_id="counter_01",
        )

    def pick(self, object_id: str) -> dict[str, Any]:
        return _ok(
            "pick",
            object_id=object_id,
            previous_location_id="counter_01",
        )

    def navigate_to_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return _ok(
            "navigate_to_receptacle",
            object_id="held_object",
            receptacle_id=receptacle_id,
        )

    def open_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return _ok("open_receptacle", receptacle_id=receptacle_id, opened=True)

    def place(self, receptacle_id: str) -> dict[str, Any]:
        return _ok("place", object_id="held_object", receptacle_id=receptacle_id)

    def place_inside(self, receptacle_id: str) -> dict[str, Any]:
        return _ok("place_inside", object_id="held_object", receptacle_id=receptacle_id)

    def close_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return _ok("close_receptacle", object_id="held_object", receptacle_id=receptacle_id)


def _ok(tool: str, **payload: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "tool": tool,
        "status": "ok",
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        **payload,
    }
