#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = REPO_ROOT / "scripts" / "dev" / "python_quality_baseline.json"
RUFF_COMPLEXITY_RULES = ("C901", "PLR0912", "PLR0915")
MAX_MODULE_LINES = 800
SCHEMA = "roboclaws_python_quality_ratchet_v1"
_MEASURE_RE = re.compile(r"\((?P<value>\d+)\s*>\s*(?P<limit>\d+)\)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Ratchet Ruff complexity and Pylint-compatible too-many-lines debt "
            "against an explicit baseline."
        )
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=DEFAULT_BASELINE,
        help="Quality baseline JSON path.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Replace the baseline with the current quality debt.",
    )
    args = parser.parse_args(argv)

    baseline_path = args.baseline if args.baseline.is_absolute() else REPO_ROOT / args.baseline
    current = collect_quality_state()

    if args.write_baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n")
        print(
            "python-quality-ratchet: wrote baseline "
            f"{baseline_path.relative_to(REPO_ROOT)} "
            f"({len(current['ruff_complexity']['violations'])} Ruff violations, "
            f"{len(current['pylint_too_many_lines']['files'])} oversized modules)"
        )
        return 0

    if not baseline_path.exists():
        print(
            "python-quality-ratchet: missing baseline; run "
            f"{Path(__file__).relative_to(REPO_ROOT)} --write-baseline",
            file=sys.stderr,
        )
        return 1

    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    failures = compare_to_baseline(current, baseline)
    if failures:
        print("python-quality-ratchet: failed", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        print(
            "Refactor the new debt, or deliberately refresh the baseline after review.",
            file=sys.stderr,
        )
        return 1

    print(
        "python-quality-ratchet: ok "
        f"({len(current['ruff_complexity']['violations'])} Ruff violations at/below baseline, "
        f"{len(current['pylint_too_many_lines']['files'])} oversized modules at/below baseline)"
    )
    return 0


def collect_quality_state() -> dict[str, Any]:
    files = tracked_python_files()
    return {
        "schema": SCHEMA,
        "generated_by": "scripts/dev/check_python_quality_ratchet.py",
        "ruff_complexity": {
            "rules": list(RUFF_COMPLEXITY_RULES),
            "violations": collect_ruff_complexity(files),
        },
        "pylint_too_many_lines": {
            "max_module_lines": MAX_MODULE_LINES,
            "files": collect_oversized_modules(files),
            "note": (
                "Pylint-compatible too-many-lines ratchet. Existing files over "
                "800 lines are baselined; new oversize files or line-count growth fail."
            ),
        },
    }


def tracked_python_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--", "*.py"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths = []
    for line in result.stdout.splitlines():
        path = Path(line)
        if path.parts and path.parts[0] == "vendors":
            continue
        absolute_path = REPO_ROOT / path
        if not absolute_path.exists():
            continue
        paths.append(absolute_path)
    return sorted(paths)


def collect_ruff_complexity(files: list[Path]) -> list[dict[str, Any]]:
    ruff = ruff_command()
    command = [
        ruff,
        "check",
        "--select",
        ",".join(RUFF_COMPLEXITY_RULES),
        "--output-format",
        "json",
        *[str(path.relative_to(REPO_ROOT)) for path in files],
    ]
    result = subprocess.run(command, cwd=REPO_ROOT, check=False, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)

    diagnostics = json.loads(result.stdout or "[]")
    symbols = SymbolIndex()
    rows: dict[str, dict[str, Any]] = {}
    for diagnostic in diagnostics:
        code = str(diagnostic.get("code") or "")
        if code not in RUFF_COMPLEXITY_RULES:
            continue
        path = Path(diagnostic["filename"]).resolve().relative_to(REPO_ROOT)
        message = str(diagnostic.get("message") or "")
        location = diagnostic.get("location") or {}
        row = int(location.get("row") or 0)
        value, limit = _measure_from_message(message)
        symbol = symbols.symbol_for(path, row)
        key = _ruff_key(path.as_posix(), code, symbol)
        current = rows.get(key)
        item = {
            "key": key,
            "path": path.as_posix(),
            "code": code,
            "symbol": symbol,
            "value": value,
            "limit": limit,
            "row": row,
            "message": message,
        }
        if current is None or int(item["value"]) > int(current["value"]):
            rows[key] = item
    return [rows[key] for key in sorted(rows)]


def collect_oversized_modules(files: list[Path]) -> list[dict[str, Any]]:
    oversized = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        lines = text.count("\n") + (0 if text.endswith("\n") or not text else 1)
        if lines > MAX_MODULE_LINES:
            oversized.append(
                {
                    "path": path.relative_to(REPO_ROOT).as_posix(),
                    "lines": lines,
                    "max_module_lines": MAX_MODULE_LINES,
                }
            )
    return sorted(oversized, key=lambda item: item["path"])


def compare_to_baseline(current: dict[str, Any], baseline: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if baseline.get("schema") != SCHEMA:
        failures.append(f"baseline schema is {baseline.get('schema')!r}, expected {SCHEMA!r}")
        return failures

    base_ruff = {item["key"]: item for item in baseline["ruff_complexity"]["violations"]}
    for item in current["ruff_complexity"]["violations"]:
        base = base_ruff.get(item["key"])
        if base is None:
            failures.append(
                "new Ruff complexity violation "
                f"{item['path']}:{item['symbol']} {item['code']} {item['message']}"
            )
            continue
        if int(item["value"]) > int(base["value"]):
            failures.append(
                "Ruff complexity grew "
                f"{item['path']}:{item['symbol']} {item['code']} "
                f"{base['value']} -> {item['value']}"
            )

    base_modules = {
        item["path"]: int(item["lines"]) for item in baseline["pylint_too_many_lines"]["files"]
    }
    for item in current["pylint_too_many_lines"]["files"]:
        path = item["path"]
        lines = int(item["lines"])
        base_lines = base_modules.get(path)
        if base_lines is None:
            failures.append(f"new oversized module {path} has {lines} lines")
            continue
        if lines > base_lines:
            failures.append(f"oversized module grew {path} {base_lines} -> {lines} lines")

    return failures


def ruff_command() -> str:
    override = os.environ.get("ROBOCLAWS_RUFF")
    if override:
        return override
    local = REPO_ROOT / ".venv" / "bin" / "ruff"
    if local.exists():
        return str(local)
    return "ruff"


def _measure_from_message(message: str) -> tuple[int, int]:
    match = _MEASURE_RE.search(message)
    if not match:
        return 1, 0
    return int(match.group("value")), int(match.group("limit"))


def _ruff_key(path: str, code: str, symbol: str) -> str:
    return f"{path}|{code}|{symbol}"


class SymbolIndex:
    def __init__(self) -> None:
        self._cache: dict[Path, list[tuple[int, int, str]]] = {}

    def symbol_for(self, path: Path, row: int) -> str:
        spans = self._cache.setdefault(path, self._load(path))
        matches = [span for span in spans if span[0] <= row <= span[1]]
        if not matches:
            return f"line:{row}"
        return max(matches, key=lambda span: span[0])[2]

    def _load(self, path: Path) -> list[tuple[int, int, str]]:
        source_path = REPO_ROOT / path
        try:
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
        except SyntaxError:
            return []
        spans: list[tuple[int, int, str]] = []

        def visit(node: ast.AST, parents: list[str]) -> None:
            name = getattr(node, "name", None)
            is_named_scope = isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            next_parents = parents
            if is_named_scope and isinstance(name, str):
                next_parents = [*parents, name]
                spans.append(
                    (
                        int(getattr(node, "lineno", 0)),
                        int(getattr(node, "end_lineno", getattr(node, "lineno", 0))),
                        ".".join(next_parents),
                    )
                )
            for child in ast.iter_child_nodes(node):
                visit(child, next_parents)

        visit(tree, [])
        return spans


if __name__ == "__main__":
    raise SystemExit(main())
