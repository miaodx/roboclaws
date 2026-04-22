#!/usr/bin/env python3
"""Local probe helper for Phase 02.7 Gateway transcript capture.

Hits the OpenClaw Gateway's OpenAI-compatible chat-completions endpoint in
streaming and/or terminal-body mode, then writes raw/parsed captures to a local
output directory for later write-up.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

DEFAULT_GATEWAY_URL = "http://127.0.0.1:18789/v1/chat/completions"
DEFAULT_MODEL = "openclaw/agent-0"
DEFAULT_PROMPT = (
    "Reply with three short numbered lines about what you are about to do. "
    "Keep each line under 12 words."
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe Gateway transcript capture via stream and/or body mode.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--mode", choices=("stream", "body", "both"), default="both")
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--token-env", default="OPENCLAW_GATEWAY_TOKEN")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=180.0)
    return parser.parse_args(argv)


def resolve_chat_url(url: str) -> str:
    trimmed = url.rstrip("/")
    if trimmed.endswith("/v1/chat/completions"):
        return trimmed
    return f"{trimmed}/v1/chat/completions"


def require_token(env_name: str) -> str:
    token = os.environ.get(env_name, "").strip()
    if token:
        return token
    print(f"missing bearer token env: {env_name}", file=sys.stderr)
    raise SystemExit(2)


def build_payload(*, model: str, prompt: str, stream: bool) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
        "max_tokens": 1024,
    }


def extract_visible_content(body: dict[str, Any]) -> str:
    choices = body.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    if content is None:
        return ""
    return str(content)


def visible_text_from_stream_payload(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    delta = choices[0].get("delta") or {}
    content = delta.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        return "".join(parts)
    if isinstance(content, str):
        return content
    if content is None:
        return ""
    return str(content)


def run_stream_probe(
    client: httpx.Client,
    *,
    url: str,
    payload: dict[str, Any],
    output_dir: Path,
    timeout: float,
) -> dict[str, Any]:
    raw_path = output_dir / "stream.raw.txt"
    parsed_path = output_dir / "stream.parsed.jsonl"
    parsed_count = 0
    candidate_data_lines = 0
    visible_fragments = 0

    with client.stream("POST", url, json=payload, timeout=timeout) as response:
        response.raise_for_status()
        with raw_path.open("w", encoding="utf-8") as raw_fp, parsed_path.open(
            "w", encoding="utf-8"
        ) as parsed_fp:
            for line in response.iter_lines():
                raw_fp.write(line + "\n")
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    continue
                candidate_data_lines += 1
                try:
                    decoded = json.loads(data)
                except json.JSONDecodeError:
                    continue
                parsed_fp.write(json.dumps(decoded) + "\n")
                parsed_count += 1
                if visible_text_from_stream_payload(decoded).strip():
                    visible_fragments += 1

    return {
        "http_status": 200,
        "raw_file": raw_path.name,
        "parsed_file": parsed_path.name,
        "candidate_data_lines": candidate_data_lines,
        "parsed_json_lines": parsed_count,
        "assistant_visible_fragments": visible_fragments,
    }


def run_body_probe(
    client: httpx.Client,
    *,
    url: str,
    payload: dict[str, Any],
    output_dir: Path,
    timeout: float,
) -> dict[str, Any]:
    response = client.post(url, json=payload, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    body_path = output_dir / "body.response.json"
    extracted_path = output_dir / "body.extracted.txt"
    extracted = extract_visible_content(body)
    body_path.write_text(json.dumps(body, indent=2), encoding="utf-8")
    extracted_path.write_text(extracted, encoding="utf-8")
    return {
        "http_status": int(response.status_code),
        "response_file": body_path.name,
        "extracted_file": extracted_path.name,
        "extracted_chars": len(extracted),
        "assistant_visible_fragments": int(bool(extracted.strip())),
    }


def write_request(output_dir: Path, payload: dict[str, Any], url: str) -> str:
    request_path = output_dir / "request.json"
    request_path.write_text(
        json.dumps(
            {
                "url": url,
                "payload": payload,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return request_path.name


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    token = require_token(args.token_env)
    url = resolve_chat_url(args.gateway_url)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    results: dict[str, Any] = {}
    request_files: dict[str, str] = {}

    with httpx.Client(headers=headers) as client:
        if args.mode in {"stream", "both"}:
            stream_dir = output_dir if args.mode == "stream" else output_dir / "stream"
            stream_dir.mkdir(parents=True, exist_ok=True)
            payload = build_payload(model=args.model, prompt=args.prompt, stream=True)
            request_files["stream"] = write_request(stream_dir, payload, url)
            results["stream"] = run_stream_probe(
                client,
                url=url,
                payload=payload,
                output_dir=stream_dir,
                timeout=args.timeout,
            )
            results["stream"]["request_file"] = request_files["stream"]

        if args.mode in {"body", "both"}:
            body_dir = output_dir if args.mode == "body" else output_dir / "body"
            body_dir.mkdir(parents=True, exist_ok=True)
            payload = build_payload(model=args.model, prompt=args.prompt, stream=False)
            request_files["body"] = write_request(body_dir, payload, url)
            results["body"] = run_body_probe(
                client,
                url=url,
                payload=payload,
                output_dir=body_dir,
                timeout=args.timeout,
            )
            results["body"]["request_file"] = request_files["body"]

    summary = {
        "mode": args.mode,
        "gateway_url": url,
        "model": args.model,
        "output_files": results,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except httpx.HTTPStatusError as exc:
        print(
            f"HTTP {exc.response.status_code} from {exc.request.url}: {exc.response.text[:400]}",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc
    except httpx.HTTPError as exc:
        print(f"http error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
