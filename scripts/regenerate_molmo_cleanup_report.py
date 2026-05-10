#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from roboclaws.molmo_cleanup.artifact_report import (
    rerender_cleanup_reports_from_run_results,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenerate a MolmoSpaces cleanup report through the shared underlay."
    )
    parser.add_argument("run_result", type=Path, nargs="+")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_paths = rerender_cleanup_reports_from_run_results(args.run_result)
    payload = {"reports": [str(path) for path in report_paths]}
    if len(report_paths) == 1:
        payload["report"] = str(report_paths[0])
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
