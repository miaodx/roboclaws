#!/usr/bin/env python3
"""Temporary MCP image server for Codex provider image-transport probes."""

from __future__ import annotations

import argparse
import hashlib
import io
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Image as MCPImage
from PIL import Image, ImageDraw


def make_synthetic_png() -> bytes:
    image = Image.new("RGB", (360, 240), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((28, 44, 148, 164), fill=(220, 20, 60))
    draw.ellipse((210, 54, 320, 164), fill=(30, 100, 220))
    draw.text((40, 190), "RAW_FPV_OK", fill=(0, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_server(*, host: str, port: int, fpv_paths: tuple[Path, ...]) -> FastMCP:
    mcp = FastMCP("vision_smoke", host=host, port=port)

    @mcp.tool(structured_output=False)
    def synthetic_image_probe() -> Any:
        """Return a deterministic synthetic PNG for image transport testing."""

        return [
            "Inspect the attached image. It contains a red square, a blue circle, "
            "and the text RAW_FPV_OK.",
            MCPImage(data=make_synthetic_png(), format="png"),
        ]

    @mcp.tool(structured_output=False)
    def fpv_image_probe(index: int = 1) -> Any:
        """Return one indexed FPV PNG for image transport testing."""

        if index < 1 or index > len(fpv_paths):
            return [f"FPV image index out of range: {index}; expected 1..{len(fpv_paths)}"]
        resolved = fpv_paths[index - 1].expanduser().resolve()
        if not resolved.is_file():
            return [f"FPV image not found: {resolved}"]
        data = resolved.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        return [
            f"Inspect robot FPV image {index} of {len(fpv_paths)}. "
            "List visible cleanup-relevant objects and approximate locations. "
            f"basename={resolved.name} sha256={digest}",
            MCPImage(data=data, format="png"),
        ]

    return mcp


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18891)
    parser.add_argument("--fpv-path", type=Path, action="append", required=True)
    args = parser.parse_args()

    make_server(host=args.host, port=args.port, fpv_paths=tuple(args.fpv_path)).run(
        transport="streamable-http"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
