#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from scripts.visual_grounding.build_visual_grounding_corpus_from_cleanup_run import (  # noqa: E402
    CORPUS_SCHEMA,
    DEFAULT_CATEGORY_FAMILY_MAP,
    VISUAL_GROUNDING_CATEGORY_HINTS,
    _fixtures_by_room,
    _private_labels_by_room,
    _raw_fpv_image_path,
    _raw_fpv_observations,
    _room_by_fixture_id,
)

DEFAULT_MIN_RAW_FPV = 5
DEFAULT_MAX_OBSERVATIONS = 96


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a representative visual-grounding benchmark corpus from multiple "
            "stored MolmoSpaces cleanup runs with RAW_FPV artifacts."
        )
    )
    parser.add_argument(
        "roots",
        nargs="+",
        type=Path,
        help="Output roots, cleanup run directories, or run_result.json files to scan.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Output corpus JSON path.")
    parser.add_argument(
        "--name",
        default="representative-raw-fpv",
        help="Corpus name.",
    )
    parser.add_argument(
        "--max-observations",
        type=int,
        default=DEFAULT_MAX_OBSERVATIONS,
        help="Maximum exported observations after filtering; 0 means all.",
    )
    parser.add_argument(
        "--min-raw-fpv",
        type=int,
        default=DEFAULT_MIN_RAW_FPV,
        help="Minimum RAW_FPV observations required for a source run.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=7,
        help="Deterministic sampling seed.",
    )
    parser.add_argument(
        "--include-no-label-observations",
        action="store_true",
        help="Keep observations whose room has no private labels.",
    )
    parser.add_argument(
        "--keep-image-duplicates",
        action="store_true",
        help="Do not remove observations with identical image bytes.",
    )
    parser.add_argument(
        "--skip-missing-images",
        action="store_true",
        help="Skip source observations whose referenced image is missing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    source_paths = discover_run_results(args.roots)
    source_corpora = [
        corpus
        for path in source_paths
        if (corpus := build_source_corpus(path, skip_missing_images=args.skip_missing_images))
        is not None
    ]
    eligible_sources = [
        corpus for corpus in source_corpora if len(corpus["observations"]) >= args.min_raw_fpv
    ]
    selected, sampling = select_representative_observations(
        eligible_sources,
        max_observations=args.max_observations,
        include_no_label_observations=args.include_no_label_observations,
        keep_image_duplicates=args.keep_image_duplicates,
        seed=args.seed,
    )
    if not selected:
        raise SystemExit("no eligible RAW_FPV observations selected")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    observations = write_selected_observations(selected, output_dir=args.output.parent)
    corpus = {
        "schema": CORPUS_SCHEMA,
        "name": args.name,
        "description": (
            "Representative corpus generated from multiple stored MolmoSpaces "
            "RAW_FPV cleanup artifacts. Private labels are benchmark scoring data "
            "only and are not sent to the visual-grounding service."
        ),
        "source_run_results": [str(corpus["source_run_result"]) for corpus in eligible_sources],
        "label_source": "private_evaluation_room_presence",
        "category_family_map": DEFAULT_CATEGORY_FAMILY_MAP,
        "sampling": {
            **sampling,
            "seed": args.seed,
            "min_raw_fpv": args.min_raw_fpv,
            "max_observations": args.max_observations,
            "include_no_label_observations": args.include_no_label_observations,
            "deduplicate_image_hashes": not args.keep_image_duplicates,
        },
        "observations": observations,
    }
    args.output.write_text(json.dumps(corpus, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"visual grounding representative corpus: {args.output}")
    print(f"source run_results scanned: {len(source_paths)}")
    print(f"eligible source run_results: {len(eligible_sources)}")
    print(f"observations: {len(observations)}")
    print(f"unique image hashes: {sampling['selected_unique_image_hash_count']}")
    return 0


def discover_run_results(roots: list[Path]) -> list[Path]:
    paths: set[Path] = set()
    for root in roots:
        if root.is_file() and root.name == "run_result.json":
            paths.add(root)
            continue
        if root.is_dir() and (root / "run_result.json").is_file():
            paths.add(root / "run_result.json")
            continue
        if root.is_dir():
            paths.update(root.rglob("run_result.json"))
    return sorted(paths)


def build_source_corpus(path: Path, *, skip_missing_images: bool) -> dict[str, Any] | None:
    try:
        run_result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not _has_private_labels(run_result):
        return None
    observations = build_source_observations(
        run_result=run_result,
        run_dir=path.parent,
        skip_missing_images=skip_missing_images,
    )
    if not observations:
        return None
    return {
        "source_run_result": path,
        "source_id": _source_id(path),
        "observations": observations,
    }


def build_source_observations(
    *,
    run_result: dict[str, Any],
    run_dir: Path,
    skip_missing_images: bool,
) -> list[dict[str, Any]]:
    raw_observations = _raw_fpv_observations(run_result)
    fixtures_by_room = _fixtures_by_room(run_result)
    room_by_fixture_id = _room_by_fixture_id(fixtures_by_room)
    labels_by_room = _private_labels_by_room(
        run_result,
        room_by_fixture_id=room_by_fixture_id,
    )
    output: list[dict[str, Any]] = []
    for raw in raw_observations:
        image_path = _raw_fpv_image_path(raw, run_dir)
        if image_path is None or not image_path.is_file():
            if skip_missing_images:
                continue
            return []
        room_id = str(raw.get("room_id") or "")
        output.append(
            {
                "observation_id": str(raw.get("observation_id") or f"raw_fpv_{len(output) + 1}"),
                "waypoint_id": str(raw.get("waypoint_id") or ""),
                "room_id": room_id,
                "capture_context": {
                    "discovered_during": "waypoint_observe",
                    "source_artifact_status": str(raw.get("artifact_status") or ""),
                },
                "category_hints": list(VISUAL_GROUNDING_CATEGORY_HINTS),
                "static_fixture_projection": fixtures_by_room.get(room_id, []),
                "image": {
                    "source": "path",
                    "path": str(image_path),
                },
                "private_labels": labels_by_room.get(room_id, []),
            }
        )
    return output


def select_representative_observations(
    source_corpora: list[dict[str, Any]],
    *,
    max_observations: int,
    include_no_label_observations: bool,
    keep_image_duplicates: bool,
    seed: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = flatten_source_observations(source_corpora)
    input_count = len(rows)
    rows = [row for row in rows if include_no_label_observations or row["label_families"]]
    label_filtered_count = len(rows)
    if not keep_image_duplicates:
        rows = dedupe_by_image_hash(rows)
    deduped_count = len(rows)

    rng = random.Random(seed)
    selected = stratified_sample(rows, max_observations=max_observations, rng=rng)
    selected_hashes = {str(row["image_sha256"]) for row in selected}
    sampling = {
        "candidate_observation_count": input_count,
        "post_label_filter_observation_count": label_filtered_count,
        "post_image_dedupe_observation_count": deduped_count,
        "removed_duplicate_image_count": label_filtered_count - deduped_count,
        "selected_observation_count": len(selected),
        "selected_unique_image_hash_count": len(selected_hashes),
        "source_run_count": len({str(row["source_run_result"]) for row in selected}),
        "room_distribution": dict(sorted(Counter(str(row["room_id"]) for row in selected).items())),
        "label_family_distribution": dict(
            sorted(Counter(family for row in selected for family in row["label_families"]).items())
        ),
    }
    return selected, sampling


def flatten_source_observations(source_corpora: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for corpus in source_corpora:
        source_path = Path(corpus["source_run_result"])
        source_id = str(corpus["source_id"])
        for index, observation in enumerate(corpus["observations"], start=1):
            image_path = _resolve_observation_image_path(observation, source_path.parent)
            if not image_path.is_file():
                continue
            labels = list(observation.get("private_labels") or [])
            label_families = sorted(
                {
                    str(label.get("category_family") or label.get("category") or "")
                    for label in labels
                    if str(label.get("category_family") or label.get("category") or "")
                }
            )
            rows.append(
                {
                    "source_run_result": source_path,
                    "source_id": source_id,
                    "source_index": index,
                    "source_observation_id": str(observation.get("observation_id") or ""),
                    "observation": observation,
                    "image_path": image_path,
                    "image_sha256": _sha256(image_path),
                    "room_id": str(observation.get("room_id") or ""),
                    "label_families": label_families,
                    "label_count": len(labels),
                }
            )
    return rows


def dedupe_by_image_hash(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_hash: dict[str, dict[str, Any]] = {}
    for row in rows:
        image_hash = str(row["image_sha256"])
        current = best_by_hash.get(image_hash)
        if current is None or _row_quality_key(row) > _row_quality_key(current):
            best_by_hash[image_hash] = row
    return sorted(best_by_hash.values(), key=_stable_row_key)


def stratified_sample(
    rows: list[dict[str, Any]],
    *,
    max_observations: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    if max_observations <= 0 or len(rows) <= max_observations:
        return sorted(rows, key=_stable_row_key)

    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        families = row["label_families"] or ["no_label"]
        for family in families:
            groups[(str(row["room_id"]), str(family))].append(row)

    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for group_rows in groups.values():
        ordered = sorted(group_rows, key=_stable_row_key)
        row = ordered[rng.randrange(len(ordered))]
        selected[_row_identity(row)] = row
        if len(selected) >= max_observations:
            return sorted(selected.values(), key=_stable_row_key)

    ordered_rows = sorted(
        rows,
        key=lambda row: (_selection_pressure(row, selected), _stable_row_key(row)),
    )
    for row in ordered_rows:
        selected.setdefault(_row_identity(row), row)
        if len(selected) >= max_observations:
            break
    return sorted(selected.values(), key=_stable_row_key)


def write_selected_observations(
    selected: list[dict[str, Any]],
    *,
    output_dir: Path,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index, row in enumerate(selected, start=1):
        source = Path(row["image_path"])
        suffix = source.suffix.lower() or ".png"
        observation_id = f"raw_fpv_rep_{index:03d}"
        image_rel = Path("raw_fpv_representative") / f"{observation_id}{suffix}"
        target = output_dir / image_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        width, height = _image_dimensions(target)
        observation = dict(row["observation"])
        observation["observation_id"] = observation_id
        observation["image"] = {
            "source": "path",
            "path": str(image_rel),
            "width": width,
            "height": height,
        }
        capture_context = dict(observation.get("capture_context") or {})
        capture_context.update(
            {
                "source_run_result": str(row["source_run_result"]),
                "source_observation_id": row["source_observation_id"],
                "source_image_sha256": row["image_sha256"],
            }
        )
        observation["capture_context"] = capture_context
        output.append(observation)
    return output


def _has_private_labels(run_result: dict[str, Any]) -> bool:
    private_evaluation = run_result.get("private_evaluation")
    if not isinstance(private_evaluation, dict):
        return False
    return bool(private_evaluation.get("object_results"))


def _source_id(path: Path) -> str:
    parts = path.parent.parts[-4:]
    return "__".join(_safe_id(part) for part in parts)


def _safe_id(value: str) -> str:
    cleaned = "".join(char if char.isalnum() or char in "._-" else "_" for char in value.strip())
    return cleaned or "source"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return int(image.width), int(image.height)


def _resolve_observation_image_path(observation: dict[str, Any], run_dir: Path) -> Path:
    image_path = Path(str((observation.get("image") or {}).get("path") or ""))
    if image_path.is_absolute() or image_path.is_file():
        return image_path
    return run_dir / image_path


def _row_quality_key(row: dict[str, Any]) -> tuple[int, int]:
    return (
        int(row["label_count"]),
        len(row["label_families"]),
    )


def _stable_row_key(row: dict[str, Any]) -> tuple[str, str, str, int, str]:
    return (
        str(row["room_id"]),
        ",".join(row["label_families"]),
        str(row["source_run_result"]),
        int(row["source_index"]),
        str(row["source_observation_id"]),
    )


def _row_identity(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row["source_run_result"]), str(row["source_observation_id"]))


def _selection_pressure(
    row: dict[str, Any],
    selected: dict[tuple[str, str], dict[str, Any]],
) -> tuple[int, int, int]:
    selected_rows = list(selected.values())
    source_count = sum(
        1 for item in selected_rows if item["source_run_result"] == row["source_run_result"]
    )
    room_count = sum(1 for item in selected_rows if item["room_id"] == row["room_id"])
    family_count = sum(
        1
        for item in selected_rows
        if set(item["label_families"]).intersection(set(row["label_families"]))
    )
    return (source_count, room_count, family_count)


if __name__ == "__main__":
    raise SystemExit(main())
