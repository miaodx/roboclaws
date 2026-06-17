from __future__ import annotations

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "dev" / "check_python_quality_ratchet.py"


def load_module():
    spec = importlib.util.spec_from_file_location("check_python_quality_ratchet", SCRIPT)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def baseline_state() -> dict:
    return {
        "schema": "roboclaws_python_quality_ratchet_v1",
        "ruff_complexity": {
            "violations": [
                {
                    "key": "roboclaws/example.py|C901|too_big",
                    "path": "roboclaws/example.py",
                    "code": "C901",
                    "symbol": "too_big",
                    "value": 11,
                    "limit": 10,
                    "message": "`too_big` is too complex (11 > 10)",
                }
            ]
        },
        "pylint_too_many_lines": {
            "files": [
                {
                    "path": "roboclaws/large.py",
                    "lines": 900,
                    "max_module_lines": 800,
                }
            ]
        },
    }


def test_ratchet_allows_debt_at_or_below_baseline() -> None:
    module = load_module()
    current = baseline_state()

    assert module.compare_to_baseline(current, baseline_state()) == []


def test_ratchet_rejects_new_complexity_violation() -> None:
    module = load_module()
    current = baseline_state()
    current["ruff_complexity"]["violations"].append(
        {
            "key": "roboclaws/new.py|PLR0912|branchy",
            "path": "roboclaws/new.py",
            "code": "PLR0912",
            "symbol": "branchy",
            "value": 13,
            "limit": 12,
            "message": "Too many branches (13 > 12)",
        }
    )

    failures = module.compare_to_baseline(current, baseline_state())

    assert failures == [
        "new Ruff complexity violation roboclaws/new.py:branchy PLR0912 Too many branches (13 > 12)"
    ]


def test_ratchet_rejects_existing_complexity_growth() -> None:
    module = load_module()
    current = baseline_state()
    current["ruff_complexity"]["violations"][0]["value"] = 12

    failures = module.compare_to_baseline(current, baseline_state())

    assert failures == ["Ruff complexity grew roboclaws/example.py:too_big C901 11 -> 12"]


def test_ratchet_rejects_new_or_growing_oversized_modules() -> None:
    module = load_module()
    current = baseline_state()
    current["pylint_too_many_lines"]["files"][0]["lines"] = 901
    current["pylint_too_many_lines"]["files"].append(
        {
            "path": "scripts/new_big_module.py",
            "lines": 801,
            "max_module_lines": 800,
        }
    )

    failures = module.compare_to_baseline(current, baseline_state())

    assert failures == [
        "oversized module grew roboclaws/large.py 900 -> 901 lines",
        "new oversized module scripts/new_big_module.py has 801 lines",
    ]


def test_quality_debt_summary_ranks_top_debt() -> None:
    module = load_module()
    state = baseline_state()
    state["ruff_complexity"]["violations"].extend(
        [
            {
                "key": "roboclaws/b.py|PLR0915|longer",
                "path": "roboclaws/b.py",
                "code": "PLR0915",
                "symbol": "longer",
                "value": 80,
                "limit": 50,
                "message": "Too many statements (80 > 50)",
            },
            {
                "key": "roboclaws/b.py|PLR0912|branchy",
                "path": "roboclaws/b.py",
                "code": "PLR0912",
                "symbol": "branchy",
                "value": 14,
                "limit": 12,
                "message": "Too many branches (14 > 12)",
            },
        ]
    )
    state["pylint_too_many_lines"]["files"].append(
        {
            "path": "roboclaws/biggest.py",
            "lines": 1200,
            "max_module_lines": 800,
        }
    )

    summary = module.quality_debt_summary(state, top_n=1)

    assert summary["ruff_total"] == 3
    assert summary["oversized_total"] == 2
    assert summary["top_oversized_modules"] == [
        {
            "path": "roboclaws/biggest.py",
            "lines": 1200,
            "max_module_lines": 800,
        }
    ]
    assert summary["top_complexity_entries"][0]["symbol"] == "longer"
    assert summary["complexity_by_file"] == [
        {
            "path": "roboclaws/b.py",
            "violations": 2,
            "max_value": 80,
            "max_limit": 50,
            "codes": [
                {"code": "PLR0912", "count": 1},
                {"code": "PLR0915", "count": 1},
            ],
        }
    ]


def test_format_quality_debt_summary_is_readable() -> None:
    module = load_module()
    summary = module.quality_debt_summary(baseline_state(), top_n=5)

    text = module.format_quality_debt_summary(summary)

    assert "python-quality-ratchet: summary" in text
    assert "- Ruff complexity violations: 1" in text
    assert "- oversized modules: 1" in text
    assert "- 900 lines roboclaws/large.py" in text
    assert "- 11>10 C901 roboclaws/example.py::too_big" in text
    assert "- 1 violations roboclaws/example.py (max 11>10; C901:1)" in text
