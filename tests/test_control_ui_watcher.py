"""Tests for scripts/control_ui_watcher.py — WS lifecycle parsing + hint policy."""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pytest

_WATCHER_PATH = Path(__file__).resolve().parent.parent / "scripts" / "control_ui_watcher.py"
_spec = importlib.util.spec_from_file_location("control_ui_watcher", _WATCHER_PATH)
assert _spec is not None and _spec.loader is not None
watcher = importlib.util.module_from_spec(_spec)
sys.modules["control_ui_watcher"] = watcher  # dataclasses needs module in sys.modules
_spec.loader.exec_module(watcher)


# Real lines copied verbatim from the appliance log paste in the cold-start
# investigation — keep these exact so the regexes stay honest.
CONNECT_LINE = (
    "2026-04-28T05:57:31.334+00:00 [ws] webchat connected "
    "conn=91574c78-df45-4e58-bd11-6613b621ea31 remote=127.0.0.1 "
    "client=openclaw-control-ui webchat v2026.4.25-beta.11"
)
DISCONNECT_LINE = (
    "2026-04-28T05:57:49.426+00:00 [ws] webchat disconnected "
    "code=1001 reason=n/a conn=efbceb30-e437-40d8-a67a-e5032e367ad7"
)
CLOSED_BEFORE_CONNECT_LINE = (
    "2026-04-28T05:57:49.424+00:00 [ws] closed before connect "
    "conn=50486a6e-e5a4-4469-bbfd-560302530edf peer=127.0.0.1:48778->127.0.0.1:18789"
)


@pytest.fixture
def state():
    return watcher.WatcherState()


def _process(lines: list[str], state) -> str:
    sink = io.StringIO()
    for line in lines:
        watcher.process_line(line, state, sink=sink)
    return sink.getvalue()


def test_connected_increments_active(state):
    _process([CONNECT_LINE], state)
    assert "91574c78-df45-4e58-bd11-6613b621ea31" in state.active
    assert state.peak_concurrent == 1


def test_disconnected_removes_from_active(state):
    state.active["efbceb30-e437-40d8-a67a-e5032e367ad7"] = 0.0
    _process([DISCONNECT_LINE], state)
    assert "efbceb30-e437-40d8-a67a-e5032e367ad7" not in state.active


def test_closed_before_connect_is_ignored(state):
    """Half-open WS handshakes never reach 'connected' — counting them
    would double-warn during the cold-start storm."""
    _process([CLOSED_BEFORE_CONNECT_LINE], state)
    assert state.active == {}
    assert state.peak_concurrent == 0


def test_no_hint_for_single_connection(state):
    out = _process([CONNECT_LINE], state)
    assert out == ""
    assert state.hint_count == 0


def test_hint_fires_at_two_concurrent(state):
    second = CONNECT_LINE.replace(
        "91574c78-df45-4e58-bd11-6613b621ea31",
        "7fb2c675-e568-4735-b517-d17ec495bfed",
    )
    out = _process([CONNECT_LINE, second], state)
    assert "control-ui-watcher" in out
    assert "2 Control UI connections" in out
    assert state.hint_count == 1


def test_hint_only_fires_once_per_lifetime(state):
    """Default policy: one hint per gateway lifetime. After the first hint,
    subsequent multi-connect events stay quiet — covered by the disconnect/
    reconnect dance during cold start."""
    second = CONNECT_LINE.replace(
        "91574c78-df45-4e58-bd11-6613b621ea31",
        "7fb2c675-e568-4735-b517-d17ec495bfed",
    )
    third = CONNECT_LINE.replace(
        "91574c78-df45-4e58-bd11-6613b621ea31",
        "d7d3e3ea-8a63-403e-a41e-8de44217f8af",
    )
    out = _process([CONNECT_LINE, second, third], state)
    assert out.count("control-ui-watcher") == 1
    assert state.hint_count == 1


def test_unrelated_line_is_ignored(state):
    _process(["2026-04-28T05:56:41.715+00:00 [gateway] agent model: foo"], state)
    assert state.active == {}
    assert state.hint_count == 0
