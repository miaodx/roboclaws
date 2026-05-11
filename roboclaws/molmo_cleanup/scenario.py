from __future__ import annotations

import json
import random
from pathlib import Path

from roboclaws.molmo_cleanup.types import (
    CleanupObject,
    CleanupReceptacle,
    CleanupScenario,
    PrivateScoringManifest,
    TargetRule,
)

_TASK = "Clean up this room by putting misplaced objects in appropriate places."

_RECEPTACLES = (
    CleanupReceptacle("sofa_01", "sofa", "living_area"),
    CleanupReceptacle("floor_01", "floor", "living_area", kind="surface"),
    CleanupReceptacle("armchair_01", "armchair", "living_area"),
    CleanupReceptacle("desk_01", "desk", "work_area"),
    CleanupReceptacle("coffee_table_01", "coffee table", "living_area"),
    CleanupReceptacle("sink_01", "kitchen sink", "kitchen"),
    CleanupReceptacle("bookshelf_01", "bookshelf", "living_area"),
    CleanupReceptacle("laundry_hamper_01", "laundry hamper", "bedroom"),
    CleanupReceptacle("fridge_01", "fridge", "kitchen"),
    CleanupReceptacle("toy_bin_01", "toy bin", "living_area"),
)

_BASE_OBJECTS = (
    ("mug_01", "ceramic mug", "dish", "sofa_01", ("sink_01",)),
    ("book_01", "paperback book", "book", "floor_01", ("bookshelf_01",)),
    ("towel_01", "hand towel", "linen", "armchair_01", ("laundry_hamper_01",)),
    ("apple_01", "apple", "food", "desk_01", ("fridge_01",)),
    ("toy_car_01", "toy car", "toy", "coffee_table_01", ("toy_bin_01",)),
)


def build_cleanup_scenario(seed: int = 7) -> CleanupScenario:
    """Return the deterministic default room-cleanup scenario."""
    rng = random.Random(seed)
    shuffled = list(_BASE_OBJECTS)
    rng.shuffle(shuffled)
    objects = tuple(
        CleanupObject(
            object_id=object_id,
            name=name,
            category=category,
            location_id=location_id,
        )
        for object_id, name, category, location_id, _valid_targets in shuffled
    ) + (
        CleanupObject(
            object_id="remote_01",
            name="TV remote",
            category="electronics",
            location_id="coffee_table_01",
        ),
    )
    targets = tuple(
        TargetRule(object_id=object_id, valid_receptacle_ids=valid_targets)
        for object_id, _name, _category, _location_id, valid_targets in _BASE_OBJECTS
    )
    scenario_id = f"molmo-cleanup-default-{seed}"
    manifest = PrivateScoringManifest(
        scenario_id=scenario_id,
        targets=targets,
        success_threshold=3,
    )
    return CleanupScenario(
        scenario_id=scenario_id,
        task=_TASK,
        seed=seed,
        objects=objects,
        receptacles=_RECEPTACLES,
        private_manifest=manifest,
    )


def write_scenario_bundle(
    output_dir: Path,
    scenario: CleanupScenario,
) -> dict[str, Path]:
    """Write public scenario and private manifest JSON files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    scenario_path = output_dir / "scenario.json"
    private_manifest_path = output_dir / "private_manifest.json"
    scenario_path.write_text(
        json.dumps(scenario.public_payload(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    private_manifest_path.write_text(
        json.dumps(scenario.private_manifest.to_private_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "scenario": scenario_path,
        "private_manifest": private_manifest_path,
    }
