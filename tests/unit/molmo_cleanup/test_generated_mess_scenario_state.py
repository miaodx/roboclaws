from __future__ import annotations

import pytest

from scripts.isaac_lab_cleanup import isaac_scenario_state


class _Hooks:
    @staticmethod
    def receptacle_prefers_inside(_receptacle: dict[str, object]) -> bool:
        return True


def test_molmospaces_manifest_target_rejects_invalid_relation() -> None:
    pytest.importorskip("mujoco")
    from scripts.molmo_cleanup import molmospaces_scenario_state

    with pytest.raises(
        ValueError,
        match="generated mess manifest relation must be 'on' or 'inside'",
    ):
        molmospaces_scenario_state.target_relation(
            {},
            {"object_id": "mug_01", "relation": "beside"},
            hooks=_Hooks(),
        )


def test_molmospaces_manifest_target_rejects_invalid_placement_index() -> None:
    pytest.importorskip("mujoco")
    from scripts.molmo_cleanup import molmospaces_scenario_state

    for placement_index in (None, 1.2, True):
        with pytest.raises(
            ValueError,
            match="generated mess manifest placement_index must be an integer",
        ):
            molmospaces_scenario_state.target_placement_index(
                4,
                {"object_id": "mug_01", "placement_index": placement_index},
            )


def test_molmospaces_non_manifest_seed_keeps_backend_fallbacks() -> None:
    pytest.importorskip("mujoco")
    from scripts.molmo_cleanup import molmospaces_scenario_state

    assert (
        molmospaces_scenario_state.target_relation(
            {},
            None,
            hooks=_Hooks(),
        )
        == "inside"
    )
    assert molmospaces_scenario_state.target_placement_index(4, None) == 4


def test_isaac_manifest_target_rejects_invalid_relation() -> None:
    with pytest.raises(
        ValueError,
        match="generated mess manifest relation must be 'on' or 'inside'",
    ):
        isaac_scenario_state.target_relation(
            {},
            {"object_id": "mug_01", "relation": "beside"},
            hooks=_Hooks(),
        )


def test_isaac_manifest_target_rejects_invalid_placement_index() -> None:
    for placement_index in (None, 1.2, True):
        with pytest.raises(
            ValueError,
            match="generated mess manifest placement_index must be an integer",
        ):
            isaac_scenario_state.target_placement_index(
                4,
                {"object_id": "mug_01", "placement_index": placement_index},
            )


def test_isaac_non_manifest_seed_keeps_backend_fallbacks() -> None:
    assert isaac_scenario_state.target_relation({}, None, hooks=_Hooks()) == "inside"
    assert isaac_scenario_state.target_placement_index(4, None) == 4
