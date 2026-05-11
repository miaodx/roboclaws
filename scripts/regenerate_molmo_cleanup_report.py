#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from roboclaws.molmo_cleanup.artifact_report import rerender_cleanup_report_from_run_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate a MolmoSpaces cleanup report through the shared underlay."
    )
    parser.add_argument("run_result", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_path = rerender_cleanup_report_from_run_result(args.run_result)
    print(json.dumps({"report": str(report_path)}))


if __name__ == "__main__":
    main()
