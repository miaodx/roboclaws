#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _load_ci_live_reports() -> ModuleType:
    module_path = (
        Path(__file__).resolve().parents[2] / "roboclaws" / "household" / ("ci_live_reports.py")
    )
    spec = importlib.util.spec_from_file_location("_roboclaws_ci_live_reports", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_ci_live_reports = _load_ci_live_reports()
MODEL_ENTRIES = _ci_live_reports.MODEL_ENTRIES
collect_entry_statuses = _ci_live_reports.collect_entry_statuses
write_live_index = _ci_live_reports.write_live_index
write_manifest = _ci_live_reports.write_manifest


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
        index = write_live_index(args.site_live_dir, statuses)
        print(f"molmo-live-pages manifest: {manifest}")
        print(f"molmo-live-pages index: {index}")
    else:
        print("molmo-live-pages: no status artifacts found")
    return 0 if copied or not args.source_dir.exists() else 0


if __name__ == "__main__":
    raise SystemExit(main())
