#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.ci_live_reports import (  # noqa: E402
    MODEL_ENTRIES,
    collect_entry_statuses,
    write_manifest,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assemble downloaded Molmo live CI artifacts into the Pages site."
    )
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("site_live_dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.site_live_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for entry in MODEL_ENTRIES:
        source = args.source_dir / entry.name
        if not source.is_dir():
            continue
        destination = args.site_live_dir / entry.name
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
        copied += 1
    statuses = collect_entry_statuses(args.site_live_dir)
    if statuses:
        manifest = write_manifest(args.site_live_dir, statuses)
        print(f"molmo-live-pages manifest: {manifest}")
    else:
        print("molmo-live-pages: no status artifacts found")
    return 0 if copied or not args.source_dir.exists() else 0


if __name__ == "__main__":
    raise SystemExit(main())
