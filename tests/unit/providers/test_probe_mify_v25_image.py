from __future__ import annotations

import importlib.util
import sys
import urllib.error
from pathlib import Path

import pytest


def _load_script_module():
    path = Path("scripts/dev/probe_mify_v25_image.py")
    spec = importlib.util.spec_from_file_location("probe_mify_v25_image", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_parse_json_object_text_rejects_non_object_provider_source() -> None:
    script = _load_script_module()

    with pytest.raises(
        ValueError,
        match="mify image probe response source must contain a JSON object",
    ):
        script.parse_json_object_text(
            '["not-an-object"]',
            label="mify image probe response",
            source="https://provider.example/v1/responses",
        )


def test_post_json_rejects_malformed_provider_success(monkeypatch) -> None:
    script = _load_script_module()

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            return None

        @staticmethod
        def read() -> bytes:
            return b"not-json"

    monkeypatch.setattr(script.urllib.request, "urlopen", lambda *_args, **_kwargs: FakeResponse())

    with pytest.raises(ValueError, match="must contain valid JSON object"):
        script.post_json(
            url="https://provider.example/v1/responses",
            payload={"model": "m"},
            api_key="key",
            timeout_s=1,
        )


def test_http_error_payload_preserves_source_when_body_is_bad() -> None:
    script = _load_script_module()
    exc = urllib.error.HTTPError(
        url="https://provider.example/v1/responses",
        code=502,
        msg="Bad Gateway",
        hdrs={},
        fp=None,
    )

    payload = script.http_error_payload(exc)

    assert payload == {
        "error": {
            "message": "Bad Gateway",
            "status": 502,
            "source": "HTTP 502 Bad Gateway",
        }
    }
