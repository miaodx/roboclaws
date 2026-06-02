from __future__ import annotations

import json
from pathlib import Path

from roboclaws.household.scenario import build_cleanup_scenario, write_scenario_bundle
from roboclaws.household.types import PrivateScoringManifest


def test_public_scenario_does_not_expose_private_targets() -> None:
    scenario = build_cleanup_scenario(seed=7)

    public = scenario.public_payload()
    public_json = json.dumps(public, sort_keys=True)

    assert "private_manifest" not in public
    assert "valid_receptacle_ids" not in public_json
    assert "success_threshold" not in public_json
    assert len(public["objects"]) == 6
    assert len(scenario.private_manifest.targets) == 5


def test_cleanup_scenario_is_deterministic_by_seed() -> None:
    first = build_cleanup_scenario(seed=11)
    second = build_cleanup_scenario(seed=11)
    third = build_cleanup_scenario(seed=12)

    assert first.public_payload() == second.public_payload()
    assert first.private_manifest.to_private_dict() == second.private_manifest.to_private_dict()
    assert first.public_payload() != third.public_payload()


def test_write_scenario_bundle_splits_public_and_private_files(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)

    paths = write_scenario_bundle(tmp_path, scenario)

    public = json.loads(paths["scenario"].read_text(encoding="utf-8"))
    private = json.loads(paths["private_manifest"].read_text(encoding="utf-8"))
    round_tripped = PrivateScoringManifest.from_dict(private)

    assert public["scenario_id"] == scenario.scenario_id
    assert "targets" not in public
    assert private["targets"][0]["valid_receptacle_ids"]
    assert round_tripped == scenario.private_manifest
