from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


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
    assert "proxy_set_header X-Forwarded-For $remote_addr;" in nginx
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
    assert 'ROBOCLAWS_TAIL_HINT="${ROBOCLAWS_TAIL_HINT:-just appliance::tail}"' in run_wrapper
    assert (
        'OPENCLAW_GATEWAY_CONTAINER="${OPENCLAW_GATEWAY_CONTAINER:-roboclaws-appliance}"'
        in run_wrapper
    )


def test_local_appliance_run_reuses_host_ai2thor_cache() -> None:
    appliance = (ROOT / "just" / "appliance.just").read_text(encoding="utf-8")

    # `run` is the canonical appliance entrypoint.
    assert "\nbuild:\n" in appliance
    assert "\nrun mode=" in appliance
    assert "\nsmoke:\n" in appliance
    assert "\ntail:\n" in appliance
    # Env-overridable defaults match the historical Makefile vars.
    assert (
        'default_container := env_var_or_default("APPLIANCE_CONTAINER", "roboclaws-appliance")'
        in appliance
    )
    assert (
        "default_local_data_volume := env_var_or_default("
        '"APPLIANCE_LOCAL_DATA_VOLUME", "roboclaws-appliance-data")' in appliance
    )
    assert (
        'smoke_url := env_var_or_default("APPLIANCE_SMOKE_URL", "http://127.0.0.1:8080")'
        in appliance
    )
    assert '--name "$container"' in appliance
    assert 'mkdir -p "$HOME/.ai2thor"' in appliance
    assert '-v "$local_data_volume:/data"' in appliance
    assert '-v "$HOME/.ai2thor:/data/.ai2thor"' in appliance
    assert "-e HOME=/data" in appliance
    assert "-e ROBOCLAWS_HOME=/data" in appliance


def test_railway_parity_appliance_run_uses_host_data_dir() -> None:
    appliance = (ROOT / "just" / "appliance.just").read_text(encoding="utf-8")

    assert (
        'default_railway_data_dir := env_var_or_default("APPLIANCE_RAILWAY_DATA_DIR", "/data")'
        in appliance
    )
    assert 'mkdir -p "$DATA_DIR/.ai2thor" "$DATA_DIR/runs"' in appliance
    assert "-e HOME=/data" in appliance
    assert "-e ROBOCLAWS_HOME=/data" in appliance
    assert '-v "$DATA_DIR:/data"' in appliance


def test_appliance_tail_targets_named_container() -> None:
    appliance = (ROOT / "just" / "appliance.just").read_text(encoding="utf-8")

    assert "\ntail:\n" in appliance
    assert 'python scripts/tail-openclaw-chat.py --container "{{default_container}}"' in appliance


def test_appliance_smoke_target_checks_control_ui_websocket() -> None:
    appliance = (ROOT / "just" / "appliance.just").read_text(encoding="utf-8")

    assert "\nsmoke:\n" in appliance
    assert "scripts/appliance_control_ui_smoke.py" in appliance
    assert '--url "{{smoke_url}}"' in appliance
    assert '--token "${OPENCLAW_TOKEN:-${DEMO_PASSWORD:-demo}}"' in appliance
