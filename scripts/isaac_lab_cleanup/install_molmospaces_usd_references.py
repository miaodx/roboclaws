#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.core.json_sources import read_json_object

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
    parser.add_argument(
        "--scene-usd-path",
        action="append",
        type=Path,
        default=[],
        help=(
            "Scan a MolmoSpaces scene USD directory for objects/<source> references "
            "and install only referenced object assets that are missing locally."
        ),
    )
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
    state_assets = _missing_referenced_assets(args.state_path)
    scene_assets = _missing_scene_referenced_assets(
        args.scene_usd_path,
        install_dir=args.install_dir,
        source=args.source,
    )
    asset_paths = _dedupe([*args.asset_path, *state_assets, *scene_assets])
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
    cache_root_links = _ensure_cache_root_asset_links(
        cache_dir=args.cache_dir,
        source=args.source,
        version=version,
        asset_suffixes=plan.asset_suffixes,
        dry_run=args.dry_run,
    )
    status = "ready"
    if plan.unresolved_assets or cache_root_links["conflicts"]:
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
        "scene_usd_paths": [str(path) for path in args.scene_usd_path],
        "scene_missing_referenced_asset_count": len(scene_assets),
        "asset_paths": plan.asset_paths,
        "asset_suffixes": plan.asset_suffixes,
        "packages": plan.packages,
        "package_count": len(plan.packages),
        "unresolved_assets": plan.unresolved_assets,
        "cache_root_links": cache_root_links,
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
        raise SystemExit("molmospaces_resources is required; run `uv sync --extra dev`.") from exc

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
            payload = read_json_object(path, label="USD reference state artifact")
        except (OSError, ValueError) as exc:
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


def _missing_scene_referenced_assets(
    paths: list[Path],
    *,
    install_dir: Path,
    source: str,
) -> list[str]:
    assets: list[str] = []
    for scene_path in paths:
        for layer_path in _scene_layer_paths(scene_path):
            try:
                text = layer_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                raise SystemExit(f"Could not read USD layer {layer_path}: {exc}") from exc
            for suffix in _scene_object_reference_suffixes(text, source=source):
                asset_path = install_dir / "objects" / source / suffix
                if not asset_path.exists():
                    assets.append(str(asset_path))
    return _dedupe(assets)


def _scene_layer_paths(scene_path: Path) -> list[Path]:
    if not scene_path.exists():
        raise SystemExit(f"Scene USD path does not exist: {scene_path}")
    root = scene_path if scene_path.is_dir() else scene_path.parent
    candidates: list[Path] = []
    if scene_path.is_file():
        candidates.append(scene_path)
    for pattern in ("*.usd", "*.usda"):
        candidates.extend(root.rglob(pattern))
    return sorted({path for path in candidates if path.is_file()})


def _scene_object_reference_suffixes(text: str, *, source: str) -> list[str]:
    pattern = re.compile(rf"objects/{re.escape(source)}/([^@\s\"')]+\.usd[ac]?)")
    return _dedupe([match.group(1) for match in pattern.finditer(text)])


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


def _ensure_cache_root_asset_links(
    *,
    cache_dir: Path,
    source: str,
    version: str,
    asset_suffixes: list[str],
    dry_run: bool,
) -> dict[str, Any]:
    """Expose versioned object assets at the cache root for Kit-resolved scene paths.

    MolmoSpaces scene files reference object assets as
    ``../../../../objects/<source>/<asset_dir>/<asset>.usda`` from payload files
    under ``.../scenes/<scene>/<version>/<scene_id>/Payload``. Isaac Kit resolves
    those references under ``.../scenes/objects/<source>/<asset_dir>`` rather
    than the versioned ``.../objects/<source>/<version>/<asset_dir>`` cache used
    by ``molmospaces_resources``.
    """

    object_root = cache_dir / "usd" / "objects" / source
    scene_object_root = cache_dir / "usd" / "scenes" / "objects" / source
    version_root = object_root / version
    asset_roots = _dedupe([suffix.split("/", 1)[0] for suffix in asset_suffixes if "/" in suffix])
    link_roots = [
        ("cache_object_root", object_root),
        ("kit_scene_object_root", scene_object_root),
    ]
    created_links: list[dict[str, str]] = []
    present_links: list[dict[str, str]] = []
    missing: list[str] = []
    conflicts: list[dict[str, str]] = []
    for asset_root in asset_roots:
        target = version_root / asset_root
        if not target.exists():
            missing.append(asset_root)
            continue
        for root_kind, root in link_roots:
            link = root / asset_root
            if link.exists() or link.is_symlink():
                try:
                    if link.resolve() == target.resolve():
                        present_links.append(
                            _cache_link_record(root_kind, asset_root, link, target)
                        )
                        continue
                except OSError:
                    pass
                conflicts.append(
                    {
                        **_cache_link_record(root_kind, asset_root, link, target),
                        "root_kind": root_kind,
                    }
                )
                continue
            if not dry_run:
                root.mkdir(parents=True, exist_ok=True)
                link.symlink_to(target, target_is_directory=target.is_dir())
            created_links.append(_cache_link_record(root_kind, asset_root, link, target))
    created = _dedupe([entry["asset_root"] for entry in created_links])
    present = _dedupe([entry["asset_root"] for entry in present_links])
    missing = _dedupe(missing)
    link_root_reports = []
    for root_kind, root in link_roots:
        link_root_reports.append(
            {
                "kind": root_kind,
                "path": str(root),
                "created": [
                    entry["asset_root"]
                    for entry in created_links
                    if entry["root_kind"] == root_kind
                ],
                "present": [
                    entry["asset_root"]
                    for entry in present_links
                    if entry["root_kind"] == root_kind
                ],
                "conflicts": [entry for entry in conflicts if entry.get("root_kind") == root_kind],
            }
        )
    return {
        "schema": "roboclaws_molmospaces_usd_cache_root_links_v1",
        "cache_object_root": str(object_root),
        "kit_scene_object_root": str(scene_object_root),
        "version_root": str(version_root),
        "requested_count": len(asset_roots),
        "created_count": len(created_links),
        "present_count": len(present_links),
        "missing_count": len(missing),
        "conflict_count": len(conflicts),
        "created": created,
        "present": present,
        "missing": missing,
        "conflicts": conflicts,
        "created_links": created_links,
        "present_links": present_links,
        "link_roots": link_root_reports,
    }


def _cache_link_record(root_kind: str, asset_root: str, link: Path, target: Path) -> dict[str, str]:
    return {
        "root_kind": root_kind,
        "asset_root": asset_root,
        "path": str(link),
        "target": str(target),
    }


def _dedupe(items: list[str]) -> list[str]:
    return list(dict.fromkeys(str(item) for item in items if str(item)))


if __name__ == "__main__":
    raise SystemExit(main())
