from __future__ import annotations

import json

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE
from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario


def test_tool_contract_exposes_expected_direct_call_methods() -> None:
    contract = MolmoCleanupToolContract(build_cleanup_scenario(seed=7))

    names = {spec["name"] for spec in contract.tool_specs()}

    assert names == {"observe", "scene_objects", "goto", "pick", "place", "done"}


def test_tool_contract_public_results_do_not_leak_private_targets() -> None:
    contract = MolmoCleanupToolContract(build_cleanup_scenario(seed=7))

    observe = contract.observe()
    scene_objects = contract.scene_objects()
    public_json = json.dumps({"observe": observe, "scene_objects": scene_objects})

    assert observe["ok"] is True
    assert "valid_receptacle_ids" not in public_json
    assert "private_manifest" not in public_json
    assert "success_threshold" not in public_json


def test_tool_contract_cleanup_loop_returns_private_score_only_at_done() -> None:
    contract = MolmoCleanupToolContract(build_cleanup_scenario(seed=7))

    assert contract.goto("sink_01")["primitive_provenance"] == API_SEMANTIC_PROVENANCE
    assert contract.pick("mug_01")["primitive_provenance"] == API_SEMANTIC_PROVENANCE
    assert contract.place("sink_01")["primitive_provenance"] == API_SEMANTIC_PROVENANCE
    assert contract.pick("book_01")["ok"] is True
    assert contract.place("bookshelf_01")["ok"] is True
    assert contract.pick("towel_01")["ok"] is True
    assert contract.place("laundry_hamper_01")["ok"] is True

    done = contract.done("three targets restored")

    assert done["cleanup_status"] == "success"
    assert done["score"]["restored_count"] == 3
