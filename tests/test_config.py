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


# ------------------------------------------------------------------
# Named styles
# ------------------------------------------------------------------

def test_all_builtin_named_styles_present(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "nonexistent.json")
    for name in ("whisper", "echo", "warning", "memory", "system"):
        assert name in cfg["styles"], f"missing built-in style: {name}"


def test_each_builtin_style_has_required_fields(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "nonexistent.json")
    required = ("color", "dim", "italic", "bold", "prefix")
    for name, style in cfg["styles"].items():
        for field in required:
            assert field in style, f"style '{name}' missing field '{field}'"


def test_named_style_override_in_settings(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"styles": {"warning": {"color": "red"}}}),
        encoding="utf-8",
    )
    cfg = load_settings(path)
    assert cfg["styles"]["warning"]["color"] == "red"
    assert cfg["styles"]["warning"]["bold"] is True   # default preserved


def test_named_style_addition_in_settings(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps({"styles": {"custom": {"color": "green", "dim": True, "italic": False,
                                          "bold": False, "underline": False, "strike": False, "prefix": "» "}}}),
        encoding="utf-8",
    )
    cfg = load_settings(path)
    assert "custom" in cfg["styles"]
    assert cfg["styles"]["custom"]["color"] == "green"


def test_styles_independent_of_overlay_config(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "nonexistent.json")
    assert cfg["styles"]["warning"]["color"] != cfg["overlay"]["color"]


# ------------------------------------------------------------------
# Typewriter config
# ------------------------------------------------------------------

def test_typewriter_defaults_present(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "nonexistent.json")
    assert cfg["typewriter"]["enabled"] is False
    assert cfg["typewriter"]["delay_ms"] == 35
    pauses = cfg["typewriter"]["punctuation_pauses"]
    assert pauses["."] == 550
    assert pauses["—"] == 600
    assert pauses["…"] == 700


def test_typewriter_override_in_settings(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"typewriter": {"enabled": True, "delay_ms": 10}}), encoding="utf-8")
    cfg = load_settings(path)
    assert cfg["typewriter"]["enabled"] is True
    assert cfg["typewriter"]["delay_ms"] == 10


def test_typewriter_partial_override_preserves_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"typewriter": {"enabled": True}}), encoding="utf-8")
    cfg = load_settings(path)
    assert cfg["typewriter"]["enabled"] is True
    assert cfg["typewriter"]["delay_ms"] == 35  # default preserved
