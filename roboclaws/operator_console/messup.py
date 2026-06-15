"""Non-blocking mess-up preview support for the operator console."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from roboclaws.household.generated_mess import TARGET_RULES, select_generated_mess_targets
from roboclaws.launch.environment_setup import (
    ENVIRONMENT_SETUP_RELOCATE_CLEANUP_RELATED_OBJECTS,
    RELOCATION_SETUP_OPTIONS,
)
from roboclaws.launch.scene_sampler import parse_molmospaces_world_id
from roboclaws.launch.worlds import WORLD_SPECS

MESSUP_PREVIEW_SCHEMA = "operator_console_messup_preview_v1"
MESSUP_SUPPORTED_BACKENDS = {"mujoco"}
DEFAULT_CAPACITY_PROBE_COUNT = 999


def preview_messup(
    root: Path,
    *,
    world_id: str,
    backend_id: str,
    scenario_setup: str,
    relocation_count: str | int,
    seed: str | int | None = None,
) -> dict[str, Any]:
    """Return a preview of whether a run can generate the requested mess-up."""

    del root
    requested_count = _nonnegative_int(relocation_count, "relocation_count")
    seed_value = _optional_int(seed)
    if scenario_setup not in RELOCATION_SETUP_OPTIONS:
        scenario_setup = ENVIRONMENT_SETUP_RELOCATE_CLEANUP_RELATED_OBJECTS
    if backend_id not in MESSUP_SUPPORTED_BACKENDS:
        return _preview_payload(
            world_id=world_id,
            backend_id=backend_id,
            scenario_setup=scenario_setup,
            requested_count=requested_count,
            seed=seed_value,
            status="unsupported",
            ok=False,
            message=(
                "Mess-up preview is currently wired for MolmoSpaces MuJoCo scenes only. "
                "The selected route can still start without applying this preview."
            ),
        )
    if not world_id.startswith("molmospaces/"):
        return _preview_payload(
            world_id=world_id,
            backend_id=backend_id,
            scenario_setup=scenario_setup,
            requested_count=requested_count,
            seed=seed_value,
            status="unsupported",
            ok=False,
            message=(
                "Mess-up preview is only available for MolmoSpaces scenes. "
                "The selected route can still start with its normal setup."
            ),
        )
    if requested_count == 0:
        return _preview_payload(
            world_id=world_id,
            backend_id=backend_id,
            scenario_setup=scenario_setup,
            requested_count=requested_count,
            seed=seed_value,
            status="ready",
            ok=True,
            selected_count=0,
            eligible_count=0,
            message="Mess-up count is 0; the route will run without relocated cleanup targets.",
        )

    try:
        objects, receptacles = _load_molmospaces_inventory(world_id)
    except Exception as exc:  # pragma: no cover - exact dependency failures vary by host.
        return _preview_payload(
            world_id=world_id,
            backend_id=backend_id,
            scenario_setup=scenario_setup,
            requested_count=requested_count,
            seed=seed_value,
            status="unavailable",
            ok=False,
            message=(
                "Mess-up preview could not load the MolmoSpaces scene locally. "
                f"{type(exc).__name__}: {exc}"
            ),
        )

    return preview_messup_from_inventory(
        objects,
        receptacles,
        world_id=world_id,
        backend_id=backend_id,
        scenario_setup=scenario_setup,
        requested_count=requested_count,
        seed=seed_value,
    )


def preview_messup_from_inventory(
    objects: list[dict[str, Any]],
    receptacles: list[dict[str, Any]],
    *,
    world_id: str,
    backend_id: str,
    scenario_setup: str,
    requested_count: int,
    seed: int | None,
) -> dict[str, Any]:
    """Preview generated-mess capacity from already-loaded scene inventory."""

    if requested_count < 0:
        raise ValueError("requested_count must be >= 0")
    eligible = select_generated_mess_targets(
        objects,
        receptacles,
        target_count=DEFAULT_CAPACITY_PROBE_COUNT,
        seed=seed,
    )
    selected = (
        select_generated_mess_targets(
            objects,
            receptacles,
            target_count=requested_count,
            seed=seed,
        )
        if requested_count
        else []
    )
    ok = len(selected) >= requested_count
    rule_rows = _rule_diagnostics(objects, receptacles)
    if ok:
        message = (
            f"Mess-up preview can generate {requested_count} cleanup-related target"
            f"{'' if requested_count == 1 else 's'} for this scene."
        )
        status = "ready"
    else:
        message = (
            f"Requested {requested_count} cleanup-related targets, but the current rules can "
            f"generate only {len(eligible)} for this scene. The selected route can still run "
            "without applying this mess-up preview. Baseline remains available."
        )
        status = "partial" if eligible else "unavailable"
    object_category_counts = Counter(str(item.get("category") or "") for item in objects)
    receptacle_category_counts = Counter(str(item.get("category") or "") for item in receptacles)
    return _preview_payload(
        world_id=world_id,
        backend_id=backend_id,
        scenario_setup=scenario_setup,
        requested_count=requested_count,
        seed=seed,
        status=status,
        ok=ok,
        selected_count=len(selected),
        eligible_count=len(eligible),
        object_category_counts=dict(sorted(object_category_counts.items())),
        receptacle_category_counts=dict(sorted(receptacle_category_counts.items())),
        rule_diagnostics=rule_rows,
        message=message,
    )


def _load_molmospaces_inventory(world_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from molmo_spaces.molmo_spaces_constants import get_scenes_root
    from molmo_spaces.utils.scene_metadata_utils import get_scene_metadata

    from scripts.molmo_cleanup.molmospaces_subprocess_worker import (
        _collect_dynamic_objects,
        _collect_receptacles,
        _load_model_data,
    )

    scene_source, scene_index = _molmospaces_scene_ref(world_id)
    scene_xml = get_scenes_root() / scene_source / f"val_{scene_index}.xml"
    if not scene_xml.is_file():
        raise FileNotFoundError(scene_xml)
    model, data = _load_model_data(scene_xml)
    metadata = get_scene_metadata(scene_xml)
    if metadata is None:
        raise RuntimeError(f"missing scene metadata for {scene_xml}")
    return _collect_dynamic_objects(model, data, metadata), _collect_receptacles(
        model,
        data,
        metadata,
    )


def _molmospaces_scene_ref(world_id: str) -> tuple[str, int]:
    spec = WORLD_SPECS.get(world_id)
    if spec is not None:
        overrides = _override_map(spec.default_overrides)
        scene_source = overrides.get("scene_source") or spec.scene_source or "procthor-10k-val"
        raw_index = overrides.get("scene_index")
        if raw_index is not None:
            return scene_source, int(raw_index)
    scene_ref = parse_molmospaces_world_id(world_id)
    return scene_ref.scene_source, scene_ref.scene_index


def _rule_diagnostics(
    objects: list[dict[str, Any]],
    receptacles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for object_categories, receptacle_categories in TARGET_RULES:
        matching_objects = [item for item in objects if item.get("category") in object_categories]
        matching_receptacles = [
            item for item in receptacles if item.get("category") in receptacle_categories
        ]
        rows.append(
            {
                "object_categories": list(object_categories),
                "target_receptacle_categories": list(receptacle_categories),
                "object_count": len(matching_objects),
                "target_receptacle_count": len(matching_receptacles),
                "eligible": bool(matching_objects and matching_receptacles),
            }
        )
    return rows


def _preview_payload(
    *,
    world_id: str,
    backend_id: str,
    scenario_setup: str,
    requested_count: int,
    seed: int | None,
    status: str,
    ok: bool,
    message: str,
    selected_count: int = 0,
    eligible_count: int = 0,
    object_category_counts: dict[str, int] | None = None,
    receptacle_category_counts: dict[str, int] | None = None,
    rule_diagnostics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "schema": MESSUP_PREVIEW_SCHEMA,
        "world_id": world_id,
        "backend_id": backend_id,
        "scenario_setup": scenario_setup,
        "requested_count": requested_count,
        "seed": seed,
        "status": status,
        "ok": ok,
        "selected_count": selected_count,
        "eligible_count": eligible_count,
        "object_category_counts": object_category_counts or {},
        "receptacle_category_counts": receptacle_category_counts or {},
        "rule_diagnostics": rule_diagnostics or [],
        "message": message,
    }


def _override_map(overrides: tuple[str, ...]) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in overrides:
        key, sep, value = item.partition("=")
        if sep:
            result[key] = value
    return result


def _optional_int(value: str | int | None) -> int | None:
    if value is None or value == "":
        return None
    return int(str(value).strip())


def _nonnegative_int(value: str | int, name: str) -> int:
    parsed = int(str(value).strip())
    if parsed < 0:
        raise ValueError(f"{name} must be >= 0")
    return parsed
