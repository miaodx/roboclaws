from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from roboclaws.household.types import CleanupScore, CleanupStatus, PrivateScoringManifest


def score_cleanup(
    final_locations: Mapping[str, str],
    private_manifest: PrivateScoringManifest,
) -> CleanupScore:
    """Score a final object-location map against a private manifest."""
    restored: list[str] = []
    missed: list[str] = []
    object_results: list[dict[str, Any]] = []

    for target in private_manifest.targets:
        actual_location = final_locations.get(target.object_id)
        is_restored = actual_location in target.valid_receptacle_ids
        if is_restored:
            restored.append(target.object_id)
        else:
            missed.append(target.object_id)
        object_results.append(
            {
                "object_id": target.object_id,
                "actual_location_id": actual_location,
                "restored": is_restored,
            }
        )

    status = _status_for_count(
        restored_count=len(restored),
        success_threshold=private_manifest.success_threshold,
        target_count=len(private_manifest.targets),
    )
    return CleanupScore(
        status=status,
        restored_count=len(restored),
        total_targets=len(private_manifest.targets),
        success_threshold=private_manifest.success_threshold,
        restored_object_ids=tuple(restored),
        missed_object_ids=tuple(missed),
        object_results=tuple(object_results),
    )


def _status_for_count(
    *,
    restored_count: int,
    success_threshold: int,
    target_count: int,
) -> CleanupStatus:
    if target_count <= 0:
        return "success"
    if restored_count >= success_threshold:
        return "success"
    if restored_count > 0:
        return "partial_success"
    return "failed"
