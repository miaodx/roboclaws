from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_railway_ai2thor_cache_uses_data_root_home() -> None:
    entrypoint = (ROOT / "deploy" / "railway" / "entrypoint.sh").read_text(encoding="utf-8")
    supervisord = (ROOT / "deploy" / "railway" / "supervisord.conf").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile.railway").read_text(encoding="utf-8")

    assert 'ROBOCLAWS_HOME="${ROBOCLAWS_HOME:-${DATA_DIR}}"' in entrypoint
    assert 'export HOME="$ROBOCLAWS_HOME"' in entrypoint
    assert '"$ROBOCLAWS_AI2THOR_DIR"' in entrypoint
    assert 'HOME="%(ENV_ROBOCLAWS_HOME)s"' in supervisord
    assert "ROBOCLAWS_AI2THOR_DIR=/data/.ai2thor" in dockerfile


def test_local_appliance_run_uses_data_home() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "-e HOME=/data/home" in makefile
    assert "-e ROBOCLAWS_HOME=/data/home" in makefile
