#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from roboclaws.openclaw.diagnostics import run_latency_probe


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replay one saved turn through OpenClaw and a direct provider to compare latency.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("replay_dir", help="Replay directory containing replay.json + saved PNG frames")
    parser.add_argument("--step", type=int, default=0, help="Replay step number to probe")
    parser.add_argument("--model", default="kimi-coding", help="Direct provider model alias")
    parser.add_argument(
        "--gateway-url",
        default=None,
        help="OpenClaw Gateway base URL override (default: env or localhost)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = run_latency_probe(
        args.replay_dir,
        step=args.step,
        model=args.model,
        gateway_url=args.gateway_url,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
