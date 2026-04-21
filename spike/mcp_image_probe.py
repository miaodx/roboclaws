"""Throwaway MCP server for Fork B spike — answers U1.

Exposes a single tool `spike_get_red_square` that returns:
  - a text marker (SPIKE_MARKER_A7K) so we can find it in logs
  - a 96x96 solid RED image as ImageContent

If the agent calls this tool and reports the image is red, MCP ImageContent
flows through to Kimi as real multimodal input (U1 = YES).
If the agent reports "image omitted" / "cannot see" / guesses the wrong
color, MCP ImageContent is being dropped somewhere in Gateway (U1 = NO).

Transport: streamable-http on port 18790 so the Gateway (in Docker) can
reach it via host.docker.internal:18790/mcp.

Run:
    .venv/bin/python spike/mcp_image_probe.py
"""

from __future__ import annotations

import io
import logging

from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
log = logging.getLogger("mcp-image-probe")

mcp = FastMCP("roboclaws-spike", host="0.0.0.0", port=18790)


@mcp.tool()
def spike_get_red_square() -> list:
    """Return SPIKE_MARKER_A7K plus a 96x96 solid RED PNG.

    The caller should identify the image color as red.
    """
    img = PILImage.new("RGB", (96, 96), color=(220, 20, 20))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    png_bytes = buf.getvalue()
    log.info("spike_get_red_square called; returning %d-byte PNG", len(png_bytes))
    return [
        "SPIKE_MARKER_A7K: the attached image contains a single solid color. "
        "Identify the color in one word.",
        Image(data=png_bytes, format="png"),
    ]


if __name__ == "__main__":
    log.info("starting MCP server on 0.0.0.0:18790 (path /mcp)")
    mcp.run(transport="streamable-http")
