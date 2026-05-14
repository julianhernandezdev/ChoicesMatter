import json
from pathlib import Path

from config import load_settings


def test_returns_defaults_when_file_missing(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "nonexistent.json")
    assert cfg["overlay"]["color"] == "cyan"
    assert cfg["overlay"]["dim"] is True
    assert cfg["overlay"]["italic"] is True
    assert "prefix" in cfg["overlay"]


def test_partial_override_merges_with_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"overlay": {"color": "magenta"}}), encoding="utf-8")
    cfg = load_settings(path)
    assert cfg["overlay"]["color"] == "magenta"
    assert cfg["overlay"]["dim"] is True      # default preserved
    assert cfg["overlay"]["italic"] is True   # default preserved


def test_multiple_overrides_merge_with_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"overlay": {"color": "red", "dim": False, "italic": False, "prefix": ">> "}}),
        encoding="utf-8",
    )
    cfg = load_settings(path)
    assert cfg["overlay"]["color"] == "red"
    assert cfg["overlay"]["dim"] is False
    assert cfg["overlay"]["italic"] is False
    assert cfg["overlay"]["prefix"] == ">> "
    assert cfg["overlay"]["bold"] is False
    assert cfg["overlay"]["underline"] is False
    assert cfg["overlay"]["strike"] is False


def test_malformed_json_returns_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{ not valid json }", encoding="utf-8")
    cfg = load_settings(path)
    assert cfg["overlay"]["color"] == "cyan"


def test_defaults_are_independent_copies(tmp_path: Path) -> None:
    cfg1 = load_settings(tmp_path / "missing.json")
    cfg2 = load_settings(tmp_path / "missing.json")
    cfg1["overlay"]["color"] = "mutated"
    assert cfg2["overlay"]["color"] == "cyan"
