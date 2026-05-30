#!/usr/bin/env python3
"""Probe mify MiMo v2.5 image understanding through chat and responses APIs.

This script intentionally uses only the Python standard library so it can be
shared as a small standalone reproducer.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_MODEL = "xiaomi/mimo-v2.5"
DEFAULT_BASE_URL = "https://api.llm.mioffice.cn/v1"
DEFAULT_PROMPT = (
    "Inspect the attached real robot FPV image. Output only strict JSON with "
    'this shape: {"image_received": boolean, '
    '"visible_cleanup_objects": [string], "approx_locations": [string], '
    '"scene_summary": string}. Do not include markdown. If you cannot inspect '
    "the image, set image_received=false and explain briefly in scene_summary."
)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_dotenv(args.env_file)

    api_key = os.environ.get(args.api_key_env, "").strip()
    if not api_key:
        print(
            f"error: missing {args.api_key_env}; source .env or pass --api-key-env",
            file=sys.stderr,
        )
        return 2

    image_path = args.image.expanduser().resolve()
    if not image_path.is_file():
        print(f"error: image not found: {image_path}", file=sys.stderr)
        return 2

    base_url = args.base_url.rstrip("/")
    image_bytes = image_path.read_bytes()
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    image_data_url = f"data:{args.mime_type};base64,{image_b64}"
    prompt = args.prompt

    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir / stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    apis = ["chat", "responses"] if args.api == "both" else [args.api]
    results: list[dict[str, Any]] = []
    for api in apis:
        started = time.monotonic()
        try:
            if api == "chat":
                payload = chat_payload(args.model, prompt, image_data_url)
                response = post_json(
                    url=f"{base_url}/chat/completions",
                    payload=payload,
                    api_key=api_key,
                    timeout_s=args.timeout_s,
                )
                output_text = chat_output_text(response)
            elif api == "responses":
                payload = responses_payload(args.model, prompt, image_data_url)
                response = post_json(
                    url=f"{base_url}/responses",
                    payload=payload,
                    api_key=api_key,
                    timeout_s=args.timeout_s,
                )
                output_text = responses_output_text(response)
            else:
                raise AssertionError(api)
            elapsed_ms = round((time.monotonic() - started) * 1000)
            status = "ok"
            error: dict[str, Any] | None = None
        except urllib.error.HTTPError as exc:
            elapsed_ms = round((time.monotonic() - started) * 1000)
            response = http_error_payload(exc)
            output_text = ""
            status = "http_error"
            error = {"code": exc.code, "reason": exc.reason}
        except Exception as exc:  # noqa: BLE001 - standalone diagnostic script
            elapsed_ms = round((time.monotonic() - started) * 1000)
            response = {}
            output_text = ""
            status = "error"
            error = {"type": type(exc).__name__, "message": str(exc)}

        (output_dir / f"{api}_response.json").write_text(
            json.dumps(response, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output_dir / f"{api}_output.txt").write_text(output_text + "\n", encoding="utf-8")
        (output_dir / f"{api}_request_meta.json").write_text(
            json.dumps(
                {
                    "api": api,
                    "url": f"{base_url}/{'chat/completions' if api == 'chat' else 'responses'}",
                    "model": args.model,
                    "prompt": prompt,
                    "image_path": str(image_path),
                    "image_mime_type": args.mime_type,
                    "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
                    "image_bytes": len(image_bytes),
                    "api_key_env": args.api_key_env,
                    "api_key_present": bool(api_key),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        results.append(
            {
                "api": api,
                "status": status,
                "elapsed_ms": elapsed_ms,
                "output_text": output_text,
                "error": error,
                "response_path": str(output_dir / f"{api}_response.json"),
                "output_path": str(output_dir / f"{api}_output.txt"),
            }
        )

    summary = {
        "model": args.model,
        "base_url": base_url,
        "image_path": str(image_path),
        "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
        "output_dir": str(output_dir),
        "results": results,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(item["status"] == "ok" for item in results) else 1


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe mify MiMo v2.5 image input with one image.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--api", choices=("chat", "responses", "both"), default="both")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--base-url", default=os.environ.get("XM_LLM_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--api-key-env", default="XM_LLM_API_KEY")
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument("--mime-type", default="image/png")
    parser.add_argument("--timeout-s", type=float, default=90.0)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--output-dir", type=Path, default=Path(".tmp/mify-v25-image-probe"))
    return parser.parse_args(argv)


def load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def chat_payload(model: str, prompt: str, image_data_url: str) -> dict[str, Any]:
    return {
        "model": model,
        "temperature": 0,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_data_url}},
                ],
            }
        ],
    }


def responses_payload(model: str, prompt: str, image_data_url: str) -> dict[str, Any]:
    return {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": image_data_url},
                ],
            }
        ],
    }


def post_json(
    *,
    url: str,
    payload: dict[str, Any],
    api_key: str,
    timeout_s: float,
) -> dict[str, Any]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "roboclaws-mify-v25-image-probe/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def chat_output_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = (choices[0] or {}).get("message") or {}
    return content_to_text(message.get("content"))


def responses_output_text(payload: dict[str, Any]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text
    parts: list[str] = []
    for item in payload.get("output") or []:
        for content in (item or {}).get("content") or []:
            if isinstance(content, dict):
                parts.append(content_to_text(content.get("text") or content.get("content")))
            else:
                parts.append(str(content))
    return "\n".join(part for part in parts if part)


def content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or ""))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    if content is None:
        return ""
    return str(content)


def http_error_payload(exc: urllib.error.HTTPError) -> dict[str, Any]:
    try:
        return json.loads(exc.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - preserve best-effort diagnostic payload
        return {"error": {"message": exc.reason, "status": exc.code}}


if __name__ == "__main__":
    raise SystemExit(main())
