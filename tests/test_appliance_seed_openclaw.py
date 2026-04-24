from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED_PATH = ROOT / "scripts" / "appliance_seed_openclaw.py"


def _load_seed_module():
    spec = importlib.util.spec_from_file_location("appliance_seed_openclaw", SEED_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["appliance_seed_openclaw"] = module
    spec.loader.exec_module(module)
    return module


def _make_skill(tmp_path: Path) -> Path:
    skill = tmp_path / "skill" / "ai2thor-navigator"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("navigator\n", encoding="utf-8")
    return skill


def test_seed_writes_mimo_openclaw_config_and_snapshot_symlink(tmp_path: Path) -> None:
    module = _load_seed_module()
    skill = _make_skill(tmp_path)
    env = {
        "OPENCLAW_HOME": str(tmp_path / "openclaw"),
        "DATA_DIR": str(tmp_path / "data"),
        "SKILLS_DIR": str(skill),
        "DEMO_PASSWORD": "demo-pass",
        "MIMO_TP_KEY": "mimo-key",
    }

    runtime = module.seed(env)

    config = json.loads((runtime.base_dir / "openclaw.json").read_text(encoding="utf-8"))
    assert config["gateway"]["auth"] == {"mode": "token", "token": "demo-pass"}
    assert config["mcp"]["servers"]["roboclaws"]["url"] == "http://127.0.0.1:18788/mcp"
    assert config["agents"]["list"][0]["id"] == "agent-0"
    assert config["agents"]["list"][0]["tools"]["profile"] == "minimal"
    assert config["agents"]["defaults"]["model"]["primary"] == "mimo_openai/mimo-v2-omni"
    assert config["models"]["mode"] == "replace"
    assert "mimo_openai" in config["models"]["providers"]

    workspace = runtime.base_dir / "workspaces" / "agent-0"
    assert (workspace / "skills" / "ai2thor-navigator" / "SKILL.md").exists()
    assert (workspace / "snapshots").is_symlink()
    assert (workspace / "snapshots").resolve() == (runtime.snapshots_root / "agent-0").resolve()


def test_seed_uses_openclaw_token_when_password_is_absent(tmp_path: Path) -> None:
    module = _load_seed_module()
    skill = _make_skill(tmp_path)
    env = {
        "OPENCLAW_HOME": str(tmp_path / "openclaw"),
        "DATA_DIR": str(tmp_path / "data"),
        "SKILLS_DIR": str(skill),
        "OPENCLAW_TOKEN": "fixed-token",
        "MIMO_TP_KEY": "mimo-key",
    }

    runtime = module.seed(env)

    config = json.loads((runtime.base_dir / "openclaw.json").read_text(encoding="utf-8"))
    assert config["gateway"]["auth"]["token"] == "fixed-token"
    runtime_env = runtime.env_file.read_text(encoding="utf-8")
    assert "export OPENCLAW_GATEWAY_TOKEN=fixed-token" in runtime_env


def test_seed_rejects_missing_provider_key(tmp_path: Path) -> None:
    module = _load_seed_module()
    skill = _make_skill(tmp_path)
    env = {
        "OPENCLAW_HOME": str(tmp_path / "openclaw"),
        "DATA_DIR": str(tmp_path / "data"),
        "SKILLS_DIR": str(skill),
        "DEMO_PASSWORD": "demo-pass",
    }

    try:
        module.seed(env)
    except SystemExit as exc:
        assert "MIMO_TP_KEY" in str(exc)
    else:
        raise AssertionError("seed() should reject missing MIMO_TP_KEY")
