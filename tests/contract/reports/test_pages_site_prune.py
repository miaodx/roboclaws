from __future__ import annotations

from pathlib import Path

from roboclaws.devtools.pages_site import build_prune_plan, main, prune_pages_site


def test_prune_pages_site_keeps_html_and_referenced_molmo_images(tmp_path: Path) -> None:
    site = tmp_path / "site"
    molmo_seed = site / "molmo" / "live" / "kimi-k2.6" / "seed-7"
    robot_views = molmo_seed / "robot_views"
    diagnostics = site / "molmo" / "live" / "kimi-k2.6" / "diagnostics" / "seed-7"
    robot_views.mkdir(parents=True)
    diagnostics.mkdir(parents=True)

    _write(
        site / "index.html",
        """
        <a href="molmo/live/">Molmo live</a>
        <a href="molmo/live/kimi-k2.6/diagnostics/seed-7/diagnostics.html">Diagnostics</a>
        """,
    )
    _write(
        site / "molmo" / "live" / "index.html",
        '<a href="kimi-k2.6/seed-7/report.html">Kimi report</a>',
    )
    _write(
        molmo_seed / "report.html",
        """
        <img src="before.png">
        <img src="after.png">
        <img src="robot_views/step-001.fpv.png"
             srcset="robot_views/step-001.map.png 1x, robot_views/step-001.chase.png 2x">
        <div style="background-image:url('robot_views/step-001.verify.png')"></div>
        """,
    )
    _write(diagnostics / "diagnostics.html", "<h1>self-contained diagnostics report</h1>")

    referenced = [
        molmo_seed / "before.png",
        molmo_seed / "after.png",
        robot_views / "step-001.fpv.png",
        robot_views / "step-001.map.png",
        robot_views / "step-001.chase.png",
        robot_views / "step-001.verify.png",
    ]
    for path in referenced:
        _write_bytes(path, b"referenced")

    unreferenced = [
        robot_views / "unused.png",
        molmo_seed / "claude-events.jsonl",
        molmo_seed / "status.json",
        diagnostics / "claude-events.jsonl",
        diagnostics / "raw-status.json",
    ]
    for path in unreferenced:
        _write_bytes(path, b"raw evidence")

    plan = prune_pages_site(site)

    assert not plan.missing_references
    for path in referenced:
        assert path.is_file()
    for path in unreferenced:
        assert not path.exists()
    assert (site / "index.html").is_file()
    assert (site / "molmo" / "live" / "index.html").is_file()
    assert (diagnostics / "diagnostics.html").is_file()


def test_prune_pages_site_reports_missing_local_references(tmp_path: Path) -> None:
    site = tmp_path / "site"
    _write(site / "index.html", '<img src="missing.png"><a href="https://example.com">external</a>')

    plan = build_prune_plan(site)

    assert len(plan.missing_references) == 1
    assert plan.missing_references[0].raw_url == "missing.png"
    assert main([str(site)]) == 1


def test_prune_pages_site_does_not_allow_references_outside_site(tmp_path: Path) -> None:
    site = tmp_path / "site"
    _write(site / "nested" / "report.html", '<a href="../../secret.txt">bad</a>')

    plan = build_prune_plan(site)

    assert len(plan.missing_references) == 1
    assert plan.missing_references[0].raw_url == "../../secret.txt"


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
