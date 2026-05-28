#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA = "roboclaws_molmospaces_usd_reference_install_v1"
DEFAULT_INSTALL_DIR = Path("output/isaaclab/molmospaces-usd")
DEFAULT_CACHE_DIR = Path.home() / ".molmospaces"
DEFAULT_USD_OBJECT_VERSIONS = {
    "thor": "20260128",
    "objaverse": "20260128",
}
DEFAULT_BUCKET_PREFIX = "isaac"


@dataclass(frozen=True)
class InstallPlan:
    asset_paths: list[str]
    asset_suffixes: list[str]
    packages: list[str]
    unresolved_assets: list[str]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install MolmoSpaces USD object packages referenced by Isaac Lab scene diagnostics."
        )
    )
    parser.add_argument("--install-dir", type=Path, default=DEFAULT_INSTALL_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--source", default="thor", choices=sorted(DEFAULT_USD_OBJECT_VERSIONS))
    parser.add_argument("--version", default="")
    parser.add_argument("--state-path", action="append", type=Path, default=[])
    parser.add_argument("--asset-path", action="append", default=[])
    parser.add_argument("--package", action="append", default=[])
    parser.add_argument("--all-objects", action="store_true")
    parser.add_argument("--use-r2", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--hf-token", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-path", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = install_references(args)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output_path:
        args.output_path.parent.mkdir(parents=True, exist_ok=True)
        args.output_path.write_text(text, encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] != "blocked" else 2


def install_references(args: argparse.Namespace) -> dict[str, Any]:
    version = args.version or DEFAULT_USD_OBJECT_VERSIONS[args.source]
    manager = _build_resource_manager(
        install_dir=args.install_dir,
        cache_dir=args.cache_dir,
        source=args.source,
        version=version,
        use_r2=args.use_r2,
        hf_token=args.hf_token,
    )
    manager.setup()
    available_packages = sorted(
        manager.find_all_packages_for_data_type("objects").get(args.source, [])
    )
    tries = manager.tries("objects", args.source)
    asset_paths = _dedupe([*args.asset_path, *_missing_referenced_assets(args.state_path)])
    plan = _build_install_plan(
        asset_paths=asset_paths,
        package_names=args.package,
        available_packages=available_packages,
        tries=tries,
        install_dir=args.install_dir,
        source=args.source,
        all_objects=args.all_objects,
    )
    installed = False
    if plan.packages and not args.dry_run:
        manager.install_packages("objects", {args.source: plan.packages})
        installed = True
    status = "ready"
    if plan.unresolved_assets:
        status = "blocked"
    elif not plan.packages:
        status = "no_references"
    return {
        "schema": SCHEMA,
        "status": status,
        "install_dir": str(args.install_dir),
        "cache_dir": str(args.cache_dir / "usd"),
        "source": args.source,
        "version": version,
        "remote": "r2" if args.use_r2 else "huggingface",
        "dry_run": bool(args.dry_run),
        "installed": installed,
        "available_package_count": len(available_packages),
        "asset_paths": plan.asset_paths,
        "asset_suffixes": plan.asset_suffixes,
        "packages": plan.packages,
        "package_count": len(plan.packages),
        "unresolved_assets": plan.unresolved_assets,
    }


def _build_resource_manager(
    *,
    install_dir: Path,
    cache_dir: Path,
    source: str,
    version: str,
    use_r2: bool,
    hf_token: str,
) -> Any:
    try:
        from molmospaces_resources import HFRemoteStorage, R2RemoteStorage, ResourceManager
        from molmospaces_resources.manager import InstallMode
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "molmospaces_resources is required; run `uv sync --extra dev --extra molmospaces`."
        ) from exc

    remote_storage = (
        R2RemoteStorage(f"{DEFAULT_BUCKET_PREFIX}-thor-resources")
        if use_r2
        else HFRemoteStorage(
            repo_id="allenai/molmospaces",
            repo_prefix=DEFAULT_BUCKET_PREFIX,
            token=hf_token or os.getenv("HF_TOKEN"),
        )
    )
    return ResourceManager(
        remote_storage=remote_storage,
        data_type_to_source_to_version={"objects": {source: version}},
        symlink_dir=install_dir,
        cache_dir=cache_dir / "usd",
        source_overrides={("objects", source): {"install_mode": InstallMode.ON_DEMAND}},
        force_install=True,
    )


def _build_install_plan(
    *,
    asset_paths: list[str],
    package_names: list[str],
    available_packages: list[str],
    tries: dict[str, Any],
    install_dir: Path,
    source: str,
    all_objects: bool,
) -> InstallPlan:
    if all_objects:
        return InstallPlan(
            asset_paths=_dedupe(asset_paths),
            asset_suffixes=[],
            packages=available_packages,
            unresolved_assets=[],
        )
    requested_packages = _dedupe(package_names)
    unknown_packages = [pkg for pkg in requested_packages if pkg not in set(available_packages)]
    if unknown_packages:
        raise SystemExit(f"Unknown USD object package(s): {', '.join(unknown_packages)}")
    suffixes = _dedupe(
        [
            suffix
            for asset_path in asset_paths
            if (suffix := _asset_suffix(asset_path, install_dir=install_dir, source=source))
        ]
    )
    package_hits: dict[str, str] = {}
    unresolved_assets: list[str] = []
    for asset_path in asset_paths:
        suffix = _asset_suffix(asset_path, install_dir=install_dir, source=source)
        if not suffix:
            unresolved_assets.append(asset_path)
            continue
        package = _package_for_asset_suffix(suffix, tries)
        if not package:
            unresolved_assets.append(asset_path)
            continue
        package_hits[package] = suffix
    packages = _dedupe([*requested_packages, *sorted(package_hits)])
    return InstallPlan(
        asset_paths=_dedupe(asset_paths),
        asset_suffixes=suffixes,
        packages=packages,
        unresolved_assets=_dedupe(unresolved_assets),
    )


def _missing_referenced_assets(paths: list[Path]) -> list[str]:
    assets: list[str] = []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"Could not read JSON artifact {path}: {exc}") from exc
        _collect_missing_referenced_assets(payload, assets)
    return _dedupe(assets)


def _collect_missing_referenced_assets(value: Any, assets: list[str]) -> None:
    if isinstance(value, dict):
        missing = value.get("missing_referenced_assets")
        if isinstance(missing, list):
            assets.extend(str(item) for item in missing if item)
        for item in value.values():
            _collect_missing_referenced_assets(item, assets)
    elif isinstance(value, list):
        for item in value:
            _collect_missing_referenced_assets(item, assets)


def _asset_suffix(asset_path: str, *, install_dir: Path, source: str) -> str:
    raw = str(asset_path or "").strip()
    if not raw:
        return ""
    marker = f"/objects/{source}/"
    normalized = raw.replace("\\", "/")
    if marker in normalized:
        return normalized.rsplit(marker, 1)[1]
    install_prefix = str((install_dir / "objects" / source).resolve()).replace("\\", "/")
    try:
        return str(Path(raw).resolve().relative_to(Path(install_prefix))).replace("\\", "/")
    except (OSError, ValueError):
        return normalized


def _package_for_asset_suffix(suffix: str, tries: dict[str, Any]) -> str:
    for package, trie in tries.items():
        if any(str(leaf) == suffix for leaf in trie.leaf_paths()):
            return str(package)
    return ""


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items if str(item)))


if __name__ == "__main__":
    raise SystemExit(main())
