from __future__ import annotations

import importlib.util
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
PROBE_PATH = REPO_ROOT / "scripts" / "run_molmo_planner_manipulation_probe.py"


def _load_probe_module():
    spec = importlib.util.spec_from_file_location(
        "run_molmo_planner_manipulation_probe", PROBE_PATH
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_renderer_device_id_only_applies_to_execute_mode() -> None:
    probe = _load_probe_module()

    assert (
        probe._renderer_device_id_for_probe(
            probe_mode="execute",
            renderer_device_id=0,
        )
        == 0
    )
    assert (
        probe._renderer_device_id_for_probe(
            probe_mode="config_import",
            renderer_device_id=0,
        )
        is None
    )
    assert (
        probe._renderer_device_id_for_probe(
            probe_mode="execute",
            renderer_device_id=-1,
        )
        is None
    )


def test_configure_headless_renderer_env_sets_egl(monkeypatch) -> None:
    probe = _load_probe_module()
    monkeypatch.delenv("MUJOCO_GL", raising=False)
    monkeypatch.delenv("PYOPENGL_PLATFORM", raising=False)
    monkeypatch.delenv("ROBOCLAWS_MOLMOSPACES_RENDERER_DEVICE_ID", raising=False)

    probe._configure_headless_renderer_env(Namespace(probe_mode="execute", renderer_device_id=0))

    assert "egl" == probe.os.environ["MUJOCO_GL"]
    assert "egl" == probe.os.environ["PYOPENGL_PLATFORM"]
    assert "0" == probe.os.environ["ROBOCLAWS_MOLMOSPACES_RENDERER_DEVICE_ID"]


def test_patch_renderer_constructor_injects_missing_device_id() -> None:
    probe = _load_probe_module()
    calls: list[dict[str, Any]] = []

    class FakeRenderer:
        def __init__(self, **kwargs: Any) -> None:
            calls.append(kwargs)

    env_module = SimpleNamespace(MjOpenGLRenderer=FakeRenderer)

    probe._patch_renderer_constructor(env_module, renderer_device_id=0)

    env_module.MjOpenGLRenderer()
    env_module.MjOpenGLRenderer(device_id=None)
    env_module.MjOpenGLRenderer(device_id=2)

    assert calls[0]["device_id"] == 0
    assert calls[1]["device_id"] == 0
    assert calls[2]["device_id"] == 2
    assert env_module.MjOpenGLRenderer._roboclaws_renderer_adapter is True
    assert env_module.MjOpenGLRenderer._roboclaws_renderer_device_id == 0


def test_runtime_diagnostics_records_renderer_override(monkeypatch) -> None:
    probe = _load_probe_module()
    monkeypatch.setenv("MUJOCO_GL", "egl")
    monkeypatch.setenv("PYOPENGL_PLATFORM", "egl")

    diagnostics = probe._runtime_diagnostics(
        Namespace(
            embodiment="franka",
            probe_mode="execute",
            renderer_device_id=0,
        )
    )

    assert diagnostics["renderer_adapter_enabled"] is True
    assert diagnostics["renderer_device_id"] == 0
    assert diagnostics["mujoco_gl_env"] == "egl"
    assert diagnostics["pyopengl_platform_env"] == "egl"


def test_process_output_text_handles_timeout_bytes() -> None:
    probe = _load_probe_module()

    assert probe._process_output_text(None) == ""
    assert probe._process_output_text("already text") == "already text"
    assert probe._process_output_text(b"byte text") == "byte text"
    assert "\ufffd" in probe._process_output_text(b"\xff")


def test_parse_last_json_object_preserves_timeout_diagnostics() -> None:
    probe = _load_probe_module()

    payload = probe._parse_last_json_object(
        'log line\n{"event": "runtime_diagnostics", "runtime_diagnostics": {"renderer": true}}\n'
    )

    assert payload == {
        "event": "runtime_diagnostics",
        "runtime_diagnostics": {"renderer": True},
    }
