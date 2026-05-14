"""Utilities for slimming the public GitHub Pages report site."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

_REF_ATTRS = {"action", "href", "poster", "src"}
_SRCSET_ATTRS = {"imagesrcset", "srcset"}
_CSS_URL_RE = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
_KEEP_FILENAMES = {".nojekyll"}


@dataclass(frozen=True)
class MissingReference:
    source: Path
    raw_url: str
    resolved_path: Path


@dataclass(frozen=True)
class PrunePlan:
    site_dir: Path
    html_files: tuple[Path, ...]
    kept_files: tuple[Path, ...]
    delete_files: tuple[Path, ...]
    missing_references: tuple[MissingReference, ...]
    before_files: int
    before_bytes: int
    delete_bytes: int

    @property
    def after_files(self) -> int:
        return self.before_files - len(self.delete_files)

    @property
    def after_bytes(self) -> int:
        return self.before_bytes - self.delete_bytes

    def summary(self) -> dict[str, int]:
        return {
            "html_files": len(self.html_files),
            "before_files": self.before_files,
            "before_bytes": self.before_bytes,
            "kept_files": len(self.kept_files),
            "delete_files": len(self.delete_files),
            "delete_bytes": self.delete_bytes,
            "after_files": self.after_files,
            "after_bytes": self.after_bytes,
            "missing_references": len(self.missing_references),
        }


class _ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []
        self._in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._handle_tag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "style":
            self._in_style = False

    def handle_data(self, data: str) -> None:
        if self._in_style:
            self.urls.extend(_css_urls(data))

    def _handle_tag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "style":
            self._in_style = True
        for raw_name, value in attrs:
            if value is None:
                continue
            name = raw_name.lower()
            if name in _REF_ATTRS:
                self.urls.append(value)
            elif name in _SRCSET_ATTRS:
                self.urls.extend(_srcset_urls(value))
            elif name == "style":
                self.urls.extend(_css_urls(value))


def build_prune_plan(site_dir: Path) -> PrunePlan:
    """Return the files that are required by static HTML and safe to delete."""
    site_dir = site_dir.resolve()
    if not site_dir.is_dir():
        raise FileNotFoundError(f"Pages site directory not found: {site_dir}")

    all_files = tuple(sorted(path for path in site_dir.rglob("*") if path.is_file()))
    html_files = tuple(path for path in all_files if path.suffix.lower() == ".html")
    before_bytes = sum(path.stat().st_size for path in all_files)

    kept: set[Path] = set(html_files)
    kept.update(path for path in all_files if path.name in _KEEP_FILENAMES)
    missing: list[MissingReference] = []

    for html_file in html_files:
        parser = _ReferenceParser()
        parser.feed(html_file.read_text(encoding="utf-8", errors="replace"))
        for raw_url in parser.urls:
            local_path = _local_url_path(raw_url)
            if local_path is None:
                continue
            resolved = _resolve_local_reference(site_dir, html_file, local_path)
            if resolved is None:
                continue
            if not _is_relative_to(resolved, site_dir):
                missing.append(
                    MissingReference(
                        source=html_file,
                        raw_url=raw_url,
                        resolved_path=resolved,
                    )
                )
                continue
            if resolved.is_dir():
                resolved = resolved / "index.html"
            elif local_path.endswith("/"):
                resolved = resolved / "index.html"
            if resolved.is_file():
                kept.add(resolved)
            else:
                missing.append(
                    MissingReference(
                        source=html_file,
                        raw_url=raw_url,
                        resolved_path=resolved,
                    )
                )

    delete_files = tuple(path for path in all_files if path not in kept)
    delete_bytes = sum(path.stat().st_size for path in delete_files)
    return PrunePlan(
        site_dir=site_dir,
        html_files=html_files,
        kept_files=tuple(sorted(kept)),
        delete_files=delete_files,
        missing_references=tuple(missing),
        before_files=len(all_files),
        before_bytes=before_bytes,
        delete_bytes=delete_bytes,
    )


def apply_prune_plan(plan: PrunePlan, *, dry_run: bool = False) -> None:
    if dry_run:
        return
    for path in plan.delete_files:
        path.unlink()
    _remove_empty_dirs(plan.site_dir)


def prune_pages_site(site_dir: Path, *, dry_run: bool = False) -> PrunePlan:
    plan = build_prune_plan(site_dir)
    apply_prune_plan(plan, dry_run=dry_run)
    return plan


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    plan = build_prune_plan(args.site_dir)
    _print_summary(plan, json_output=args.json)
    if plan.missing_references and not args.allow_missing:
        _print_missing(plan)
        return 1
    apply_prune_plan(plan, dry_run=args.dry_run)
    if args.verbose:
        _print_deleted(plan)
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Prune a generated GitHub Pages report site to files referenced by HTML. "
            "All HTML files are kept; unreferenced raw evidence files are removed."
        )
    )
    parser.add_argument("site_dir", type=Path)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the pruning summary without deleting files.",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Do not fail when HTML contains missing local references.",
    )
    parser.add_argument("--json", action="store_true", help="Print machine-readable summary JSON.")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="List files selected for deletion after the summary.",
    )
    return parser.parse_args(argv)


def _local_url_path(raw_url: str) -> str | None:
    raw_url = raw_url.strip()
    if not raw_url or raw_url.startswith("#"):
        return None
    parsed = urlsplit(raw_url)
    if parsed.scheme or parsed.netloc:
        return None
    if not parsed.path:
        return None
    return unquote(parsed.path)


def _resolve_local_reference(site_dir: Path, html_file: Path, local_path: str) -> Path | None:
    if local_path.startswith("/"):
        candidate = site_dir / local_path.lstrip("/")
    else:
        candidate = html_file.parent / local_path
    return candidate.resolve(strict=False)


def _srcset_urls(value: str) -> list[str]:
    value = value.strip()
    if not value or value.startswith("data:"):
        return []
    urls: list[str] = []
    for item in value.split(","):
        parts = item.strip().split()
        if parts:
            urls.append(parts[0])
    return urls


def _css_urls(value: str) -> list[str]:
    return [match.group(2) for match in _CSS_URL_RE.finditer(value)]


def _remove_empty_dirs(root: Path) -> None:
    for path in sorted((path for path in root.rglob("*") if path.is_dir()), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _print_summary(plan: PrunePlan, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(plan.summary(), indent=2, sort_keys=True))
        return
    print(
        "Pages prune: "
        f"html={len(plan.html_files)} "
        f"files={plan.before_files}->{plan.after_files} "
        f"bytes={plan.before_bytes}->{plan.after_bytes} "
        f"removed={plan.delete_bytes} "
        f"missing_refs={len(plan.missing_references)}"
    )


def _print_missing(plan: PrunePlan) -> None:
    print("Missing local HTML references:", file=sys.stderr)
    for item in plan.missing_references[:50]:
        source = item.source.relative_to(plan.site_dir)
        try:
            resolved = item.resolved_path.relative_to(plan.site_dir)
        except ValueError:
            resolved = item.resolved_path
        print(f"- {source}: {item.raw_url!r} -> {resolved}", file=sys.stderr)
    if len(plan.missing_references) > 50:
        print(f"... {len(plan.missing_references) - 50} more", file=sys.stderr)


def _print_deleted(plan: PrunePlan) -> None:
    for path in plan.delete_files:
        print(f"delete {path.relative_to(plan.site_dir)}")
