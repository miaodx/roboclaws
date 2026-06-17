from __future__ import annotations

from pathlib import Path
from typing import Any

from roboclaws.household.scene_camera_comparison import _isaac_view_render_contract
from scripts.molmo_cleanup import robot_camera_apple2apple_object_gate as object_gate

OBJECT_VISUAL_STATE_REGISTRY = {
    "box": {
        "schema": "robot_camera_object_visual_state_registry_entry_v1",
        "category": "box",
        "status": "active_category_contract",
        "protected_by": "prepared_usd_visual_physics_freeze",
        "policy": (
            "MuJoCo box flap joints render at MJCF ref/range endpoints. Prepared Isaac "
            "report USDs must freeze baked visual xforms and remove physics state before "
            "camera capture so the flaps cannot re-open during static visual comparison."
        ),
        "evidence_artifact": (
            "output/molmo/robot-camera-apple2apple/"
            "0603_val1_seed8_2mess_4loc_default_combined_chasefix/report.html"
        ),
        "promotion_rule": (
            "Keep this category-level contract until corpus evidence shows another "
            "visual-state category needs its own registry entry."
        ),
    }
}
OBJECT_VISUAL_STATE_CATEGORIES = set(OBJECT_VISUAL_STATE_REGISTRY)
VISUAL_PHYSICS_PROTECTION = {
    "schema": "robot_camera_visual_physics_protection_policy_v1",
    "protected_by": object_gate.VISUAL_PHYSICS_PROTECTED_BY,
    "policy": (
        "Objects with MuJoCo articulated visual joints or preserved Isaac physics are "
        "visual-physics-sensitive. Stripping PhysX or USD physics is necessary to keep "
        "Isaac from mutating them, but it is not sufficient proof that the frozen visual "
        "pose matches MuJoCo. A protected object must have selected nonblank RGB evidence "
        "from an object-centered robot pose/focus contract before the Object Gate may "
        "classify it as comparable."
    ),
}


def visual_physics_sensitive_target_ids(state: dict[str, Any]) -> set[str]:
    target_ids: set[str] = set()
    explicit = _dict(state.get("joint_states"))
    for target_id, raw_entries in explicit.items():
        entries: list[dict[str, Any]] = []
        if isinstance(raw_entries, list):
            entries = [_dict(item) for item in raw_entries if isinstance(item, dict)]
        elif isinstance(raw_entries, dict):
            entries = [_dict(item) for item in raw_entries.values() if isinstance(item, dict)]
        if any(_mujoco_joint_is_visual_articulation(joint) for joint in entries):
            target_ids.add(str(target_id))
    for target_id in _dict(state.get("objects")):
        category = _object_category_key(_dict(state["objects"].get(target_id)).get("category"))
        if not category:
            category = _object_category_key(str(target_id).split("_", 1)[0])
        if category in OBJECT_VISUAL_STATE_CATEGORIES:
            target_ids.add(str(target_id))
    return target_ids


def object_visual_state_contract(
    *,
    target_id: str,
    kind: str,
    mujoco_entry: dict[str, Any],
    isaac_entry: dict[str, Any],
    mujoco_state: dict[str, Any],
    isaac_contract: dict[str, Any],
    usd_prim_path: str,
) -> dict[str, Any]:
    category = _object_category_key(
        mujoco_entry.get("category")
        or isaac_entry.get("category")
        or isaac_entry.get("usd_category")
    )
    if kind != "object":
        return {"status": "not_applicable"}
    registry_entry = dict(OBJECT_VISUAL_STATE_REGISTRY.get(category) or {})
    mujoco_articulation = _mujoco_ref_endpoint_articulation_contract(
        target_id=target_id,
        mujoco_state=mujoco_state,
    )
    isaac_articulation = _isaac_usd_articulation_contract(
        isaac_contract=isaac_contract,
        usd_prim_path=usd_prim_path,
    )
    if (
        mujoco_articulation.get("status") == "mujoco_ref_endpoint_articulation"
        and isaac_articulation.get("status") == "isaac_visual_physics_frozen"
        and isaac_articulation.get("mujoco_visual_joint_endpoint_pose_status")
        == "mujoco_visual_joint_endpoint_pose_applied"
    ):
        status = "visual_state_static_ref_baked"
        reason = (
            "MuJoCo renders this object at articulated visual joint endpoints, and the "
            "prepared Isaac report USD records MuJoCo endpoint pose baking before freezing "
            "physics state, so PhysX will not mutate those baked joints during camera "
            "capture. This is necessary physics-control evidence, but selected "
            "object-centered RGB evidence is still required before the object gate may "
            "claim visual parity."
        )
    elif (
        mujoco_articulation.get("status") == "mujoco_ref_endpoint_articulation"
        and isaac_articulation.get("status") == "isaac_visual_physics_frozen"
    ):
        status = "visual_state_ref_endpoint_unverified_in_isaac"
        reason = (
            "MuJoCo renders this object at articulated visual joint endpoints, and the "
            "Isaac USD has frozen physics state, but the prepared-scene summary does not "
            "prove that the MuJoCo endpoint pose was baked before physics was stripped."
        )
    elif (
        mujoco_articulation.get("status") == "mujoco_ref_endpoint_articulation"
        and isaac_articulation.get("status") == "isaac_articulation_physics_preserved"
    ):
        status = "visual_state_articulation_physics_preserved"
        reason = (
            "MuJoCo articulated visual qpos is at MJCF ref/range endpoints, but the "
            "Isaac USD still contains physics joints or rigid-body APIs under the same "
            "object. Isaac camera capture can re-solve those joints, which can change "
            "the rendered visual state even when pose, material, and texture names match."
        )
    elif mujoco_articulation.get("status") == "mujoco_ref_endpoint_articulation":
        status = "visual_state_ref_endpoint_unverified_in_isaac"
        reason = (
            "MuJoCo articulated visual qpos is at MJCF ref/range endpoints, but this "
            "report lacks enough Isaac USD physics-freeze evidence to control the "
            "rendered visual state."
        )
    else:
        status = "visual_state_unverified"
        reason = (
            "The report does not have enough articulated-state evidence to compare this "
            "object's visual state."
        )
    return {
        "schema": "robot_camera_object_visual_state_contract_v1",
        "status": status,
        "target_id": target_id,
        "category": category,
        "registry": registry_entry,
        "protected_by": registry_entry.get("protected_by")
        or VISUAL_PHYSICS_PROTECTION["protected_by"],
        "evidence_artifact": registry_entry.get("evidence_artifact"),
        "policy": registry_entry.get("policy") or VISUAL_PHYSICS_PROTECTION["policy"],
        "mujoco": mujoco_articulation,
        "isaac": isaac_articulation,
        "reason": reason,
    }


def _mujoco_joint_is_visual_articulation(joint: dict[str, Any]) -> bool:
    joint_type = str(joint.get("joint_type") or joint.get("type") or "").lower()
    joint_name = str(joint.get("joint_name") or "").lower()
    return joint_type in {"hinge", "3", "mjjnt_hinge"} or "flap" in joint_name


def _mujoco_ref_endpoint_articulation_contract(
    *,
    target_id: str,
    mujoco_state: dict[str, Any],
) -> dict[str, Any]:
    joints = _mujoco_joint_state_entries(target_id=target_id, mujoco_state=mujoco_state)
    hinge_joints = [joint for joint in joints if _mujoco_joint_is_visual_articulation(joint)]
    if not hinge_joints:
        return {
            "status": "missing_mujoco_articulation_evidence",
            "joint_count": 0,
            "endpoint_joint_count": 0,
            "joints": [],
        }
    endpoint_count = sum(
        1 for joint in hinge_joints if _mujoco_joint_at_ref_or_range_endpoint(joint)
    )
    status = (
        "mujoco_ref_endpoint_articulation"
        if endpoint_count == len(hinge_joints)
        else "mujoco_articulation_not_at_ref_endpoint"
    )
    return {
        "status": status,
        "joint_count": len(hinge_joints),
        "endpoint_joint_count": endpoint_count,
        "joints": hinge_joints[:8],
    }


def _mujoco_joint_state_entries(
    *,
    target_id: str,
    mujoco_state: dict[str, Any],
) -> list[dict[str, Any]]:
    explicit = _dict(mujoco_state.get("joint_states"))
    raw_entries = explicit.get(target_id)
    if isinstance(raw_entries, list):
        return [_dict(item) for item in raw_entries if isinstance(item, dict)]
    if isinstance(raw_entries, dict):
        return [_dict(item) for item in raw_entries.values() if isinstance(item, dict)]
    scene_xml = str(mujoco_state.get("scene_xml") or "")
    robot_xml = str(mujoco_state.get("robot_xml") or "")
    qpos = mujoco_state.get("qpos")
    if not scene_xml or not isinstance(qpos, list):
        return []
    try:
        import mujoco

        if mujoco_state.get("robot_included") and robot_xml:
            from scripts.molmo_cleanup.molmospaces_subprocess_worker import _load_robot_model_data

            model, _ = _load_robot_model_data(Path(scene_xml), Path(robot_xml))
        else:
            model = mujoco.MjModel.from_xml_path(scene_xml)
    except Exception:
        return []
    entries: list[dict[str, Any]] = []
    joint_prefixes = _mujoco_joint_target_prefixes(target_id)
    for joint_id in range(model.njnt):
        joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id) or ""
        if not any(joint_name.startswith(prefix) for prefix in joint_prefixes):
            continue
        qposadr = int(model.jnt_qposadr[joint_id])
        qpos_value = float(qpos[qposadr]) if 0 <= qposadr < len(qpos) else None
        joint_range = [float(value) for value in model.jnt_range[joint_id]]
        ref_value = _mujoco_joint_ref_from_scene_xml(scene_xml, joint_name)
        entries.append(
            {
                "joint_name": joint_name,
                "joint_type": str(int(model.jnt_type[joint_id])),
                "qposadr": qposadr,
                "qpos": qpos_value,
                "ref": ref_value,
                "range": joint_range,
                "axis": [float(value) for value in model.jnt_axis[joint_id]],
            }
        )
    return entries


def _mujoco_joint_target_prefixes(target_id: str) -> tuple[str, ...]:
    parts = str(target_id or "").split("_")
    prefixes = [str(target_id or "")]
    if len(parts) >= 4 and parts[-1].isdigit() and parts[-2].isdigit() and parts[-3].isdigit():
        prefixes.append("_".join(parts[:-2]) + "_")
    return tuple(dict.fromkeys(prefix for prefix in prefixes if prefix))


def _mujoco_joint_ref_from_scene_xml(scene_xml: str, joint_name: str) -> float | None:
    try:
        from xml.etree import ElementTree

        root = ElementTree.parse(scene_xml).getroot()
    except Exception:
        return None
    for joint in root.findall(".//joint"):
        if str(joint.attrib.get("name") or "") != joint_name:
            continue
        raw_ref = joint.attrib.get("ref")
        if raw_ref is None:
            return None
        try:
            return float(raw_ref)
        except ValueError:
            return None
    return None


def _mujoco_joint_at_ref_or_range_endpoint(joint: dict[str, Any]) -> bool:
    qpos = _float_or_none(joint.get("qpos"))
    if qpos is None:
        return False
    ref = _float_or_none(joint.get("ref"))
    if ref is not None and abs(qpos - ref) <= 1e-4:
        return True
    raw_range = joint.get("range")
    if isinstance(raw_range, list) and len(raw_range) >= 2:
        lower = _float_or_none(raw_range[0])
        upper = _float_or_none(raw_range[1])
        if lower is not None and abs(qpos - lower) <= 1e-4:
            return True
        if upper is not None and abs(qpos - upper) <= 1e-4:
            return True
    return False


def _isaac_usd_articulation_contract(
    *,
    isaac_contract: dict[str, Any],
    usd_prim_path: str,
) -> dict[str, Any]:
    view_contract = _isaac_view_render_contract(isaac_contract, usd_prim_path=usd_prim_path)
    joint_count = int(view_contract.get("physics_joint_count") or 0)
    api_count = int(view_contract.get("physics_api_schema_prim_count") or 0)
    property_count = int(view_contract.get("physics_property_prim_count") or 0)
    if joint_count or api_count or property_count:
        status = "isaac_articulation_physics_preserved"
    else:
        status = "isaac_visual_physics_frozen"
    return {
        "status": status,
        "usd_prim_path": usd_prim_path,
        "physics_joint_count": joint_count,
        "physics_api_schema_prim_count": api_count,
        "physics_property_prim_count": property_count,
        "physics_joint_paths": view_contract.get("physics_joint_paths") or [],
        "physics_api_schema_prim_paths": view_contract.get("physics_api_schema_prim_paths") or [],
        "physics_property_prim_paths": view_contract.get("physics_property_prim_paths") or [],
        "visual_physics_status": view_contract.get("visual_physics_status"),
        "prepared_summary_status": view_contract.get("prepared_summary_status"),
        "mujoco_visual_joint_endpoint_pose_status": view_contract.get(
            "mujoco_visual_joint_endpoint_pose_status"
        ),
        "mujoco_visual_joint_endpoint_pose_corrected_count": view_contract.get(
            "mujoco_visual_joint_endpoint_pose_corrected_count"
        ),
        "mujoco_visual_joint_endpoint_pose_missing_count": view_contract.get(
            "mujoco_visual_joint_endpoint_pose_missing_count"
        ),
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _object_category_key(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())
