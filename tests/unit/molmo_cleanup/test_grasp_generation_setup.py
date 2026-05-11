from __future__ import annotations

import json
from pathlib import Path

from roboclaws.molmo_cleanup.grasp_generation_setup import (
    DEFAULT_GRASP_GENERATION_PYTHON_PACKAGES,
    DEFAULT_MANIFOLD_SUBMODULE_URL,
    GRASP_GENERATION_SETUP_SCHEMA,
    build_grasp_generation_setup_commands,
    load_availability_preflight_from_manifest,
    run_grasp_generation_setup,
)


def test_build_grasp_generation_setup_commands_uses_official_manifold_submodule(
    tmp_path: Path,
) -> None:
    root = tmp_path / "molmospaces"
    python = tmp_path / ".venv" / "bin" / "python"
    commands = build_grasp_generation_setup_commands(
        molmospaces_python=python,
        molmospaces_root=root,
        parallel_jobs=3,
    )

    assert [item["name"] for item in commands] == [
        "install_python_prerequisites",
        "ensure_manifold_source",
        "configure_manifold",
        "build_manifold",
    ]
    install_command = commands[0]["command"]
    assert all(package in install_command for package in DEFAULT_GRASP_GENERATION_PYTHON_PACKAGES)
    assert str(python) in install_command
    assert commands[1]["command"] == ["git", "submodule", "update", "--init", "--recursive"]
    assert commands[1]["expected_path"] == "external_src/Manifold"
    assert commands[1]["fallback_command"] == [
        "git",
        "clone",
        DEFAULT_MANIFOLD_SUBMODULE_URL,
        "external_src/Manifold",
    ]
    assert commands[2]["command"] == [
        "cmake",
        "-S",
        "external_src/Manifold",
        "-B",
        "external_src/Manifold/build",
    ]
    assert commands[3]["command"][-2:] == ["--parallel", "3"]


def test_run_grasp_generation_setup_dry_run_records_commands(tmp_path: Path) -> None:
    root = tmp_path / "molmospaces"
    root.mkdir()
    python = tmp_path / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/usr/bin/env python\n", encoding="utf-8")

    result = run_grasp_generation_setup(
        molmospaces_python=python,
        molmospaces_root=root,
        dry_run=True,
        parallel_jobs=2,
    )

    assert result["schema"] == GRASP_GENERATION_SETUP_SCHEMA
    assert result["status"] == "dry_run"
    assert result["ready"] is False
    assert result["command_count"] == 4
    assert {item["status"] for item in result["commands"]} == {"not_run"}
    assert result["blockers"] == []


def test_load_availability_preflight_from_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "proof_bundle_run_manifest.json"
    manifest.write_text(
        json.dumps({"grasp_cache_availability_preflight": {"schema": "example"}}),
        encoding="utf-8",
    )

    assert load_availability_preflight_from_manifest(manifest) == {"schema": "example"}
