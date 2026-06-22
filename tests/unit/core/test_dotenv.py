from __future__ import annotations

from pathlib import Path

from roboclaws.core.dotenv import clean_dotenv_value, load_dotenv_file


def test_load_dotenv_file_preserves_existing_env_and_cleans_values(tmp_path: Path) -> None:
    dotenv = tmp_path / "custom.env"
    dotenv.write_text(
        "\n".join(
            [
                "# ignored",
                "KEEP=from-file",
                'QUOTED="quoted value"',
                "EXPORTED=export exported-value",
                "BLANK=",
                "MALFORMED",
            ]
        ),
        encoding="utf-8",
    )

    loaded = load_dotenv_file(dotenv, {"KEEP": "already-present"})

    assert loaded["KEEP"] == "already-present"
    assert loaded["QUOTED"] == "quoted value"
    assert loaded["EXPORTED"] == "exported-value"
    assert loaded["BLANK"] == ""
    assert "MALFORMED" not in loaded


def test_load_dotenv_file_missing_source_returns_env_copy(tmp_path: Path) -> None:
    existing = {"KEY": "value"}
    loaded = load_dotenv_file(tmp_path / "missing.env", existing)

    assert loaded == existing
    assert loaded is not existing


def test_clean_dotenv_value_strips_matching_quotes_and_export_prefix() -> None:
    assert clean_dotenv_value(' "quoted" ') == "quoted"
    assert clean_dotenv_value("export VALUE") == "VALUE"
