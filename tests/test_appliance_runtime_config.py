from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_railway_ai2thor_cache_uses_data_root_home() -> None:
    entrypoint = (ROOT / "deploy" / "railway" / "entrypoint.sh").read_text(encoding="utf-8")
    supervisord = (ROOT / "deploy" / "railway" / "supervisord.conf").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile.railway").read_text(encoding="utf-8")
    nginx = (ROOT / "deploy" / "railway" / "nginx.conf.template").read_text(encoding="utf-8")
    run_wrapper = (ROOT / "scripts" / "appliance-run-interactive.sh").read_text(encoding="utf-8")

    assert 'ROBOCLAWS_HOME="${ROBOCLAWS_HOME:-${DATA_DIR}}"' in entrypoint
    assert 'export HOME="$ROBOCLAWS_HOME"' in entrypoint
    assert '"$ROBOCLAWS_AI2THOR_DIR"' in entrypoint
    assert "DEMO_USERNAME" not in entrypoint
    assert "htpasswd" not in entrypoint
    assert "auth_basic" not in nginx
    assert 'HOME="%(ENV_ROBOCLAWS_HOME)s"' in supervisord
    assert "ROBOCLAWS_AI2THOR_DIR=/data/.ai2thor" in dockerfile
    assert "apache2-utils" not in dockerfile
    assert "RAILWAY_PUBLIC_DOMAIN" in entrypoint
    assert 'ROBOCLAWS_PUBLIC_URL="http://127.0.0.1:${PORT}"' in entrypoint
    assert (
        'ROBOCLAWS_VIEWER_HINT="${ROBOCLAWS_VIEWER_HINT:-${ROBOCLAWS_PUBLIC_URL%/}/views/}"'
        in entrypoint
    )
    assert 'ROBOCLAWS_PUBLIC_URL="http://127.0.0.1:${PORT}"' in run_wrapper
    assert 'ROBOCLAWS_TAIL_HINT="${ROBOCLAWS_TAIL_HINT:-make appliance-tail}"' in run_wrapper
    assert (
        'OPENCLAW_GATEWAY_CONTAINER="${OPENCLAW_GATEWAY_CONTAINER:-roboclaws-appliance}"'
        in run_wrapper
    )


def test_local_appliance_run_reuses_host_ai2thor_cache() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "appliance-build appliance-run-local appliance-run-railway appliance-tail" in makefile
    assert "appliance-run:" not in makefile
    assert "APPLIANCE_CONTAINER ?= roboclaws-appliance" in makefile
    assert "APPLIANCE_LOCAL_DATA_VOLUME ?= roboclaws-appliance-data" in makefile
    assert '--name "$(APPLIANCE_CONTAINER)"' in makefile
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


def test_appliance_tail_targets_named_container() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    assert "appliance-tail:" in makefile
    assert 'python scripts/tail-openclaw-chat.py --container "$(APPLIANCE_CONTAINER)"' in makefile
