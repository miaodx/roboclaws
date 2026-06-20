from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "realworld_agibot_map_build_checker.py"


def _load_checker():
    spec = importlib.util.spec_from_file_location(
        "realworld_agibot_map_build_checker", CHECKER_PATH
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            '{"tool": "observe", "event": "response"}\n{not-json\n',
            r"Agibot map-build trace source row must contain valid JSON object: "
            r".*trace\.jsonl:2",
        ),
        (
            '{"tool": "observe", "event": "response"}\n[]\n',
            r"Agibot map-build trace source row must contain a JSON object: "
            r".*trace\.jsonl:2",
        ),
    ],
)
def test_agibot_checker_rejects_malformed_trace_rows(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    checker = _load_checker()
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(source, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        checker._assert_trace_is_public(trace_path)


def test_agibot_checker_accepts_object_trace_rows(tmp_path: Path) -> None:
    checker = _load_checker()
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        "\n".join(
            json.dumps(row, sort_keys=True)
            for row in (
                {"tool": "observe", "event": "response", "response": {"ok": True}},
                {"tool": "done", "event": "response", "response": {"ok": True}},
            )
        ),
        encoding="utf-8",
    )

    checker._assert_trace_is_public(trace_path)


def test_agibot_checker_rejects_malformed_duplicate_navigation_trace_rows(
    tmp_path: Path,
) -> None:
    checker = _load_checker()
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text('{"tool": "observe", "event": "response"}\n[]\n', encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"Agibot map-build trace source row must contain a JSON object: "
        r".*trace\.jsonl:2",
    ):
        checker._assert_no_duplicate_post_place_navigation(trace_path)
