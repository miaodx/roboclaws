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


def test_local_appliance_run_reuses_host_ai2thor_cache() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "appliance-run: appliance-run-local" in makefile
    assert "APPLIANCE_LOCAL_DATA_VOLUME ?= roboclaws-appliance-data" in makefile
    assert 'mkdir -p "$$HOME/.ai2thor"' in makefile
    assert '-v "$(APPLIANCE_LOCAL_DATA_VOLUME):/data"' in makefile
    assert '-v "$$HOME/.ai2thor:/data/.ai2thor"' in makefile
    assert "-e HOME=/data" in makefile
    assert "-e ROBOCLAWS_HOME=/data" in makefile


def test_railway_parity_appliance_run_uses_host_data_dir() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "APPLIANCE_RAILWAY_DATA_DIR ?= /data" in makefile
    assert 'mkdir -p "$$DATA_DIR/.ai2thor" "$$DATA_DIR/runs"' in makefile
    assert "-e HOME=/data" in makefile
    assert "-e ROBOCLAWS_HOME=/data" in makefile
    assert '-v "$$DATA_DIR:/data"' in makefile
