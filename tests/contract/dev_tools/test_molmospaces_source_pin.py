from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MOLMOSPACES_URL = "https://github.com/allenai/molmospaces.git"
MOLMOSPACES_PIN = "3c50ae6093f7e4a4ef32529f8a773715da410a2f"
MOLMOSPACES_SUBMODULE_PATH = "vendors/molmospaces"


def test_molmospaces_git_dependency_matches_submodule_pin() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    uv_lock = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    gitmodules = (REPO_ROOT / ".gitmodules").read_text(encoding="utf-8")

    assert f"path = {MOLMOSPACES_SUBMODULE_PATH}" in gitmodules
    assert f"url = {MOLMOSPACES_URL}" in gitmodules
    assert _pyproject_molmospaces_pin(pyproject) == MOLMOSPACES_PIN
    assert _uv_lock_molmospaces_pin(uv_lock) == MOLMOSPACES_PIN
    assert _gitlink_pin(MOLMOSPACES_SUBMODULE_PATH) == MOLMOSPACES_PIN


def _pyproject_molmospaces_pin(text: str) -> str:
    pattern = rf"molmo-spaces\[mujoco\] @ git\+{re.escape(MOLMOSPACES_URL)}@([0-9a-f]{{40}})"
    match = re.search(pattern, text)
    assert match, "missing pyproject molmo-spaces git dependency pin"
    return match.group(1)


def _uv_lock_molmospaces_pin(text: str) -> str:
    pattern = rf"{re.escape(MOLMOSPACES_URL)}\?rev=([0-9a-f]{{40}})#([0-9a-f]{{40}})"
    matches = re.findall(pattern, text)
    assert matches, "missing uv.lock molmo-spaces git source pin"
    for revision, resolved in matches:
        assert revision == resolved
    pins = {revision for revision, _ in matches}
    assert len(pins) == 1
    return pins.pop()


def _gitlink_pin(path: str) -> str:
    result = subprocess.run(
        ["git", "ls-files", "--stage", "--", path],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    line = result.stdout.strip()
    assert line, f"missing gitlink for {path}"
    mode, object_id, stage_path = line.split(maxsplit=2)
    assert mode == "160000"
    assert stage_path.endswith(f"\t{path}") or stage_path == path
    return object_id
