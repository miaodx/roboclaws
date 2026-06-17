from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "import_rby1m_robot_usd.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_urdf_tree_records_visuals_and_link_transforms(tmp_path: Path) -> None:
    module = _load_module(SCRIPT_PATH, "import_rby1m_robot_usd_parser")
    mesh_path = tmp_path / "head.obj"
    mesh_path.write_text("v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n", encoding="utf-8")
    urdf_path = tmp_path / "robot.urdf"
    urdf_path.write_text(
        """<robot name="rby1m">
  <link name="base"/>
  <link name="head">
    <visual>
      <origin xyz="0.1 0.2 0.3" rpy="0 0 0"/>
      <geometry><mesh filename="head.obj"/></geometry>
    </visual>
  </link>
  <joint name="base_to_head" type="fixed">
    <parent link="base"/>
    <child link="head"/>
    <origin xyz="1 2 3" rpy="0 0 0"/>
  </joint>
</robot>
""",
        encoding="utf-8",
    )

    robot = module._parse_urdf_tree(urdf_path)

    assert set(robot["link_transforms"]) == {"base", "head"}
    assert robot["link_transforms"]["base"] == module._identity_matrix()
    assert robot["link_transforms"]["head"][0][3] == 1.0
    assert robot["link_transforms"]["head"][1][3] == 2.0
    assert robot["link_transforms"]["head"][2][3] == 3.0
    assert robot["visuals"]["head"][0]["mesh_path"] == mesh_path.resolve()
    assert robot["visuals"]["head"][0]["origin_matrix"][0][3] == 0.1
    assert robot["child_to_parent"]["head"][0] == "base"
