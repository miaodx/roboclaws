from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

DEFAULT_B1_NUREC_CACHE_ROOT = Path("output/b1-map12/prepared-nurec-scene")
_USDZ_REFERENCE = "@./xm_large_scene.usdz@"
_SCENE_REFERENCE = "@./scene.usd@"
_USDZ_MEMBERS = ("default.usda", "gauss.usda", "xm_large_scene.nurec")


def prepare_b1_nurec_scene_usd(
    scene_usd_path: Path | None,
    *,
    cache_root: Path | None = None,
) -> Path | None:
    if scene_usd_path is None:
        return None
    scene_usd_path = Path(scene_usd_path)
    usdz_path = scene_usd_path.with_name("xm_large_scene.usdz")
    if scene_usd_path.name != "scene_gs.usda" or not usdz_path.is_file():
        return scene_usd_path
    source_text = scene_usd_path.read_text(encoding="utf-8")
    if _USDZ_REFERENCE not in source_text:
        return scene_usd_path

    cache_dir = _cache_root(cache_root) / scene_usd_path.parent.name
    unpack_dir = cache_dir / "xm_large_scene_unpacked"
    unpack_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(usdz_path) as archive:
        for member in _USDZ_MEMBERS:
            _extract_if_needed(archive, member, unpack_dir / member)

    prepared_scene = cache_dir / "scene_gs.unpacked_nurec.usda"
    prepared_text = source_text.replace(
        _SCENE_REFERENCE,
        f"@{scene_usd_path.with_name('scene.usd').resolve().as_posix()}@",
    ).replace(
        _USDZ_REFERENCE,
        f"@{(unpack_dir / 'default.usda').resolve().as_posix()}@",
    )
    _write_if_changed(prepared_scene, prepared_text)
    return prepared_scene


def _cache_root(cache_root: Path | None) -> Path:
    if cache_root is not None:
        return cache_root
    return Path(os.environ.get("ROBOCLAWS_B1_NUREC_CACHE_DIR", str(DEFAULT_B1_NUREC_CACHE_ROOT)))


def _extract_if_needed(archive: zipfile.ZipFile, member: str, output_path: Path) -> None:
    info = archive.getinfo(member)
    if output_path.is_file() and output_path.stat().st_size == info.file_size:
        return
    tmp_path = output_path.with_name(f"{output_path.name}.tmp.{os.getpid()}")
    try:
        with archive.open(member) as src, tmp_path.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        tmp_path.replace(output_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _write_if_changed(path: Path, text: str) -> None:
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
