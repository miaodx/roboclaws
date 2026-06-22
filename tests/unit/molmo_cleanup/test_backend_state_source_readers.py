from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from roboclaws.household.isaac_lab_backend import IsaacLabSubprocessBackend
from roboclaws.household.subprocess_backend import MolmoSpacesSubprocessBackend


@pytest.mark.parametrize(
    ("backend_cls", "label"),
    (
        (MolmoSpacesSubprocessBackend, "MolmoSpaces backend state"),
        (IsaacLabSubprocessBackend, "Isaac Lab backend state"),
    ),
)
def test_backend_state_readers_preserve_valid_state(
    backend_cls: type[Any],
    label: str,
    tmp_path: Path,
) -> None:
    backend = backend_cls.__new__(backend_cls)
    backend.state_path = tmp_path / "state.json"
    backend.state_path.write_text(json.dumps({"held_object_id": 7}), encoding="utf-8")

    assert backend.held_object_id == "7"


@pytest.mark.parametrize(
    ("backend_cls", "label"),
    (
        (MolmoSpacesSubprocessBackend, "MolmoSpaces backend state"),
        (IsaacLabSubprocessBackend, "Isaac Lab backend state"),
    ),
)
def test_backend_state_readers_reject_missing_state_source(
    backend_cls: type[Any],
    label: str,
    tmp_path: Path,
) -> None:
    backend = backend_cls.__new__(backend_cls)
    backend.state_path = tmp_path / "missing_state.json"

    with pytest.raises(
        FileNotFoundError, match=rf"{label} source is missing: .*missing_state\.json"
    ):
        backend.held_object_id


@pytest.mark.parametrize(
    ("backend_cls", "label"),
    (
        (MolmoSpacesSubprocessBackend, "MolmoSpaces backend state"),
        (IsaacLabSubprocessBackend, "Isaac Lab backend state"),
    ),
)
def test_backend_state_readers_reject_malformed_state_source(
    backend_cls: type[Any],
    label: str,
    tmp_path: Path,
) -> None:
    backend = backend_cls.__new__(backend_cls)
    backend.state_path = tmp_path / "state.json"
    backend.state_path.write_text("{bad json\n", encoding="utf-8")

    with pytest.raises(
        ValueError, match=rf"{label} source must contain valid JSON object: .*state\.json"
    ):
        backend.held_object_id


@pytest.mark.parametrize(
    ("backend_cls", "label"),
    (
        (MolmoSpacesSubprocessBackend, "MolmoSpaces backend state"),
        (IsaacLabSubprocessBackend, "Isaac Lab backend state"),
    ),
)
def test_backend_state_readers_reject_non_object_state_source(
    backend_cls: type[Any],
    label: str,
    tmp_path: Path,
) -> None:
    backend = backend_cls.__new__(backend_cls)
    backend.state_path = tmp_path / "state.json"
    backend.state_path.write_text("[]", encoding="utf-8")

    with pytest.raises(
        ValueError, match=rf"{label} source must contain a JSON object: .*state\.json"
    ):
        backend.held_object_id
