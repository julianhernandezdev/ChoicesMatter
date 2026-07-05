import json
from pathlib import Path

import pytest

from src.config import load_settings, save_settings, _get_draft_value, _set_draft_value, apply_section_defaults, SETTINGS_SECTIONS


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
    assert cfg["typewriter"]["enabled"] is True
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


def test_save_settings_writes_file(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    save_settings({"typewriter": {"enabled": False, "delay_ms": 10}}, path)
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["typewriter"]["enabled"] is False
    assert loaded["typewriter"]["delay_ms"] == 10


def test_save_settings_roundtrips_with_load(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    data = load_settings(tmp_path / "nonexistent.json")
    data["typewriter"]["delay_ms"] = 99
    save_settings(data, path)
    assert load_settings(path)["typewriter"]["delay_ms"] == 99


def test_typewriter_partial_override_preserves_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"typewriter": {"enabled": True}}), encoding="utf-8")
    cfg = load_settings(path)
    assert cfg["typewriter"]["enabled"] is True
    assert cfg["typewriter"]["delay_ms"] == 35  # default preserved


def test_typewriter_pause_ms_default_present(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "nonexistent.json")
    assert cfg["typewriter"]["pause_ms"] == 500


# ------------------------------------------------------------------
# Player name config
# ------------------------------------------------------------------

def test_player_name_default_is_felix(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "nonexistent.json")
    assert cfg["player_name"] == "Felix"


def test_player_name_override_in_settings(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"player_name": "Zara"}), encoding="utf-8")
    cfg = load_settings(path)
    assert cfg["player_name"] == "Zara"


# ------------------------------------------------------------------
# Corruption config
# ------------------------------------------------------------------

def test_corruption_defaults_present(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "nonexistent.json")
    c = cfg["corruption"]
    assert c["enabled"] is True
    assert c["intensity"] == pytest.approx(0.6)
    assert c["mode"] == "consistent"
    assert c["charset"] == "blocks"
    assert c["custom_chars"] == "█▓▒░"
    assert c["animate"] is True
    assert c["scramble_frames"] == 85
    assert c["scramble_delay_ms"] == 40


def test_corruption_partial_override_preserves_defaults(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"corruption": {"intensity": 0.5}}), encoding="utf-8")
    cfg = load_settings(path)
    assert cfg["corruption"]["intensity"] == pytest.approx(0.5)
    assert cfg["corruption"]["enabled"] is True      # preserved
    assert cfg["corruption"]["charset"] == "blocks"  # preserved


def test_corruption_enabled_false_override(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"corruption": {"enabled": False}}), encoding="utf-8")
    cfg = load_settings(path)
    assert cfg["corruption"]["enabled"] is False


# ------------------------------------------------------------------
# Draft value helpers
# ------------------------------------------------------------------

def test_get_draft_value_top_level() -> None:
    draft = {"player_name": "Alice"}
    assert _get_draft_value(draft, "player_name") == "Alice"


def test_get_draft_value_nested() -> None:
    draft = {"typewriter": {"enabled": True, "delay_ms": 35}}
    assert _get_draft_value(draft, "typewriter.enabled") is True
    assert _get_draft_value(draft, "typewriter.delay_ms") == 35


def test_get_draft_value_punctuation_pause() -> None:
    draft = {"typewriter": {"punctuation_pauses": {".": 550, "!": 250}}}
    assert _get_draft_value(draft, "typewriter.punctuation_pauses..") == 550
    assert _get_draft_value(draft, "typewriter.punctuation_pauses.!") == 250


def test_get_draft_value_corruption() -> None:
    draft = {"corruption": {"enabled": True, "intensity": 0.8}}
    assert _get_draft_value(draft, "corruption.enabled") is True
    assert _get_draft_value(draft, "corruption.intensity") == 0.8


def test_get_draft_value_picker() -> None:
    draft = {"picker": {"page_size": 10}}
    assert _get_draft_value(draft, "picker.page_size") == 10


def test_set_draft_value_top_level() -> None:
    draft = {"player_name": "Felix"}
    _set_draft_value(draft, "player_name", "Alice")
    assert draft["player_name"] == "Alice"


def test_set_draft_value_nested() -> None:
    draft = {"typewriter": {"enabled": False}}
    _set_draft_value(draft, "typewriter.enabled", True)
    assert draft["typewriter"]["enabled"] is True


def test_set_draft_value_punctuation_pause() -> None:
    draft = {"typewriter": {"punctuation_pauses": {".": 550}}}
    _set_draft_value(draft, "typewriter.punctuation_pauses..", 300)
    assert draft["typewriter"]["punctuation_pauses"]["."] == 300


def test_set_draft_value_corruption() -> None:
    draft = {"corruption": {"intensity": 1.0}}
    _set_draft_value(draft, "corruption.intensity", 0.5)
    assert draft["corruption"]["intensity"] == 0.5


# ------------------------------------------------------------------
# Section defaults and registry
# ------------------------------------------------------------------

def test_apply_section_defaults_typewriter() -> None:
    draft = {"typewriter": {"enabled": False, "delay_ms": 999}}
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "typewriter")
    apply_section_defaults(draft, section)
    assert draft["typewriter"]["enabled"] is True
    assert draft["typewriter"]["delay_ms"] == 35


def test_apply_section_defaults_corruption() -> None:
    draft = {"corruption": {"intensity": 0.1, "animate": False}}
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    apply_section_defaults(draft, section)
    assert draft["corruption"]["intensity"] == 0.6
    assert draft["corruption"]["animate"] is True


def test_apply_section_defaults_display() -> None:
    draft = {"picker": {"page_size": 20}}
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "display")
    apply_section_defaults(draft, section)
    assert draft["picker"]["page_size"] == 5


def test_apply_section_defaults_preserves_other_keys() -> None:
    draft = {"typewriter": {"enabled": False}, "player_name": "Zara"}
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "typewriter")
    apply_section_defaults(draft, section)
    assert draft["player_name"] == "Zara"  # untouched


def test_settings_sections_ids() -> None:
    ids = [s["id"] for s in SETTINGS_SECTIONS]
    assert "typewriter" in ids
    assert "display" in ids
    assert "corruption" in ids
    assert "player" in ids


def test_settings_sections_preserve_flags() -> None:
    by_id = {s["id"]: s for s in SETTINGS_SECTIONS}
    assert by_id["typewriter"]["preserve_on_global_reset"] is False
    assert by_id["corruption"]["preserve_on_global_reset"] is False
    assert by_id["display"]["preserve_on_global_reset"] is False
    assert by_id["player"]["preserve_on_global_reset"] is True


def test_settings_sections_subscreen_flags() -> None:
    by_id = {s["id"]: s for s in SETTINGS_SECTIONS}
    assert by_id["typewriter"]["has_subscreen"] is True
    assert by_id["corruption"]["has_subscreen"] is True
    assert by_id["display"]["has_subscreen"] is False
    assert by_id["player"]["has_subscreen"] is False


def test_settings_sections_all_have_rows() -> None:
    for section in SETTINGS_SECTIONS:
        assert len(section["rows"]) > 0, f"Section '{section['id']}' has no rows"


def test_settings_sections_rows_have_required_fields() -> None:
    for section in SETTINGS_SECTIONS:
        for row in section["rows"]:
            assert "key" in row
            assert "label" in row
            assert "type" in row


# ------------------------------------------------------------------
# Task 5: New corruption keys and relabeled rows
# ------------------------------------------------------------------

def test_corruption_defaults_include_new_keys(tmp_path: Path) -> None:
    cfg = load_settings(tmp_path / "nonexistent.json")
    assert cfg["corruption"]["intensity_multiplier"] == 1.0
    assert cfg["corruption"]["resolve_frames"] is None
    assert cfg["corruption"]["resolve_delay_ms"] is None
    assert cfg["corruption"]["cascade_stagger_ms"] is None


def test_corruption_section_mode_row_relabeled() -> None:
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    mode_row = next(r for r in section["rows"] if r["key"] == "corruption.mode")
    assert mode_row["label"] == "Mode Default"


def test_corruption_section_intensity_row_relabeled() -> None:
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    intensity_row = next(r for r in section["rows"] if r["key"] == "corruption.intensity")
    assert intensity_row["label"] == "Intensity Default"


def test_corruption_section_has_intensity_multiplier_row() -> None:
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    row = next(r for r in section["rows"] if r["key"] == "corruption.intensity_multiplier")
    assert row["label"] == "Intensity Multiplier"
    assert row["type"] == "float"


def test_corruption_section_has_resolve_timing_rows() -> None:
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    keys = {r["key"] for r in section["rows"]}
    assert "corruption.resolve_frames" in keys
    assert "corruption.resolve_delay_ms" in keys
    assert "corruption.cascade_stagger_ms" in keys


def test_player_name_row_relabeled() -> None:
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "player")
    row = next(r for r in section["rows"] if r["key"] == "player_name")
    assert row["label"] == "Player name Default"


def test_apply_section_defaults_resets_new_corruption_keys(tmp_path: Path) -> None:
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = load_settings(tmp_path / "nonexistent.json")
    draft["corruption"]["intensity_multiplier"] = 0.2
    draft["corruption"]["resolve_frames"] = 20
    apply_section_defaults(draft, section)
    assert draft["corruption"]["intensity_multiplier"] == 1.0
    assert draft["corruption"]["resolve_frames"] is None
