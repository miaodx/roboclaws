from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

PrimitiveProvenance = Literal[
    "api_semantic",
    "isaac_semantic_pose",
    "real",
    "scripted",
    "shim",
    "planner_backed",
    "blocked_capability",
]
CleanupStatus = Literal["success", "partial_success", "failed"]


@dataclass(frozen=True)
class CleanupReceptacle:
    receptacle_id: str
    name: str
    room_area: str
    kind: str = "receptacle"
    category: str | None = None

    def to_public_dict(self) -> dict[str, Any]:
        payload = {
            "receptacle_id": self.receptacle_id,
            "name": self.name,
            "room_area": self.room_area,
            "kind": self.kind,
        }
        if self.category is not None:
            payload["category"] = self.category
        return payload


@dataclass(frozen=True)
class CleanupObject:
    object_id: str
    name: str
    category: str
    location_id: str
    pickupable: bool = True

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "name": self.name,
            "category": self.category,
            "location_id": self.location_id,
            "pickupable": self.pickupable,
        }


@dataclass(frozen=True)
class TargetRule:
    object_id: str
    valid_receptacle_ids: tuple[str, ...]

    def to_private_dict(self) -> dict[str, Any]:
        return {
            "object_id": self.object_id,
            "valid_receptacle_ids": list(self.valid_receptacle_ids),
        }


@dataclass(frozen=True)
class PrivateScoringManifest:
    scenario_id: str
    targets: tuple[TargetRule, ...]
    success_threshold: int

    def to_private_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "success_threshold": self.success_threshold,
            "targets": [target.to_private_dict() for target in self.targets],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PrivateScoringManifest":
        return cls(
            scenario_id=str(data["scenario_id"]),
            success_threshold=int(data["success_threshold"]),
            targets=tuple(
                TargetRule(
                    object_id=str(target["object_id"]),
                    valid_receptacle_ids=tuple(
                        str(value) for value in target["valid_receptacle_ids"]
                    ),
                )
                for target in data["targets"]
            ),
        )


@dataclass(frozen=True)
class CleanupScenario:
    scenario_id: str
    task: str
    seed: int
    objects: tuple[CleanupObject, ...]
    receptacles: tuple[CleanupReceptacle, ...]
    private_manifest: PrivateScoringManifest

    def public_payload(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "task": self.task,
            "seed": self.seed,
            "objects": [obj.to_public_dict() for obj in self.objects],
            "receptacles": [receptacle.to_public_dict() for receptacle in self.receptacles],
        }

    def object_locations(self) -> dict[str, str]:
        return {obj.object_id: obj.location_id for obj in self.objects}


@dataclass(frozen=True)
class CleanupScore:
    status: CleanupStatus
    restored_count: int
    total_targets: int
    success_threshold: int
    restored_object_ids: tuple[str, ...]
    missed_object_ids: tuple[str, ...]
    object_results: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "restored_count": self.restored_count,
            "total_targets": self.total_targets,
            "success_threshold": self.success_threshold,
            "restored_object_ids": list(self.restored_object_ids),
            "missed_object_ids": list(self.missed_object_ids),
            "object_results": list(self.object_results),
        }
