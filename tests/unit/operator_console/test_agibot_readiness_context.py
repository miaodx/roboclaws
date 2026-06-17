from __future__ import annotations

import socket
from pathlib import Path

from roboclaws.operator_console.launcher import route_readiness
from roboclaws.operator_console.routes import get_selection

CODEX_ENV = {
    "CODEX_BASE_URL": "https://codex.example.test/v1",
    "CODEX_API_KEY": "key",
}
AGIBOT_CODEX_MAP_BUILD = (
    "agibot-g2/map-12::agibot-gdk::map-build::codex-cli::camera-grounded-labels"
)
AGIBOT_GATES = {"localization_ready": True, "run_enabled": True, "estop_ready": True}


def test_agibot_readiness_requires_readable_context_json(tmp_path: Path) -> None:
    missing = _agibot_readiness(tmp_path, context_json=tmp_path / "context.json")
    assert missing["can_start"] is False
    missing_context_gate = _gate(missing, "context_json")
    assert missing_context_gate["status"] == "needs_action"
    assert "was not found" in missing_context_gate["message"]

    context_path = tmp_path / "context.json"
    context_path.write_text("{}", encoding="utf-8")
    ready = _agibot_readiness(tmp_path, context_json=context_path)
    assert ready["can_start"] is True
    assert _gate(ready, "context_json")["evidence"] == str(context_path)

    relative = _agibot_readiness(tmp_path, context_json="context.json")
    assert relative["can_start"] is True
    assert _gate(relative, "context_json")["evidence"] == str(context_path)

    invalid_context = tmp_path / "invalid-context.json"
    invalid_context.write_text("{", encoding="utf-8")
    invalid = _agibot_readiness(tmp_path, context_json=invalid_context)
    assert invalid["can_start"] is False
    invalid_context_gate = _gate(invalid, "context_json")
    assert invalid_context_gate["status"] == "needs_action"
    assert "not readable JSON" in invalid_context_gate["message"]


def _agibot_readiness(tmp_path: Path, *, context_json: str | Path) -> dict[str, object]:
    return route_readiness(
        tmp_path,
        get_selection(AGIBOT_CODEX_MAP_BUILD),
        overrides={"context_json": str(context_json), "port": _free_port()},
        gates=AGIBOT_GATES,
        env=CODEX_ENV,
    )


def _gate(readiness: dict[str, object], gate_id: str) -> dict[str, object]:
    gates = readiness["gates"]
    assert isinstance(gates, list)
    return next(gate for gate in gates if gate["id"] == gate_id)


def _free_port() -> str:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return str(listener.getsockname()[1])
