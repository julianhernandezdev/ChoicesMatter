"""A hand-edited settings.json with the wrong kind of value must not stop the game.

The bad value falls back to its default, and the rest of the file still counts.
"""
import json
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from src.config import load_settings, _DEFAULTS
from src.corruption import CHARSETS, effective_intensity
from src.display import Display
from src.story import Overlay


def _load(tmp_path: Path, text: str) -> dict:
    path = tmp_path / "settings.json"
    path.write_text(text, encoding="utf-8")
    return load_settings(path)


def _dig(cfg: dict, keys: tuple):
    for key in keys:
        cfg = cfg[key]
    return cfg


def _display_with(tmp_path: Path, monkeypatch, settings: dict) -> Display:
    """A Display that read its settings from this settings.json, the way the game reads its own."""
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(settings), encoding="utf-8")
    monkeypatch.setattr("src.display.load_settings", lambda: load_settings(path))
    return Display()


# ------------------------------------------------------------------
# The whole file is the wrong kind of thing
# ------------------------------------------------------------------

@pytest.mark.parametrize("text", ["[]", "null", '"x"', "5"])
def test_file_that_is_not_an_object_gives_the_defaults(tmp_path: Path, text: str) -> None:
    assert _load(tmp_path, text) == _DEFAULTS


# ------------------------------------------------------------------
# One setting is the wrong kind of thing
# ------------------------------------------------------------------

@pytest.mark.parametrize("settings, keys", [
    ({"picker": {"page_size": "ten"}},                            ("picker", "page_size")),
    ({"picker": {"page_size": None}},                             ("picker", "page_size")),
    ({"picker": None},                                            ("picker",)),
    ({"typewriter": None},                                        ("typewriter",)),
    ({"typewriter": "off"},                                       ("typewriter",)),
    ({"typewriter": {"enabled": "yes"}},                          ("typewriter", "enabled")),
    ({"typewriter": {"delay_ms": "fast"}},                        ("typewriter", "delay_ms")),
    ({"typewriter": {"delay_ms": None}},                          ("typewriter", "delay_ms")),
    ({"typewriter": {"pause_ms": "long"}},                        ("typewriter", "pause_ms")),
    ({"typewriter": {"punctuation_pauses": None}},                ("typewriter", "punctuation_pauses")),
    ({"typewriter": {"punctuation_pauses": {".": "long"}}},       ("typewriter", "punctuation_pauses", ".")),
    ({"overlay": None},                                           ("overlay",)),
    ({"overlay": "cyan"},                                         ("overlay",)),
    ({"overlay": {"color": None}},                                ("overlay", "color")),
    ({"overlay": {"dim": "no"}},                                  ("overlay", "dim")),
    ({"styles": None},                                            ("styles",)),
    ({"styles": {"warning": "red"}},                              ("styles", "warning")),
    ({"styles": {"warning": {"color": None}}},                    ("styles", "warning", "color")),
    ({"corruption": None},                                        ("corruption",)),
    ({"corruption": {"intensity": "high"}},                       ("corruption", "intensity")),
    ({"corruption": {"intensity": None}},                         ("corruption", "intensity")),
    ({"corruption": {"intensity_multiplier": "1"}},               ("corruption", "intensity_multiplier")),
    ({"corruption": {"custom_chars": 5}},                         ("corruption", "custom_chars")),
    ({"corruption": {"charset": ["a"]}},                          ("corruption", "charset")),
    ({"corruption": {"scramble_frames": "many"}},                 ("corruption", "scramble_frames")),
    ({"corruption": {"scramble_frames": None}},                   ("corruption", "scramble_frames")),
    ({"corruption": {"scramble_frames": True}},                   ("corruption", "scramble_frames")),
    ({"corruption": {"scramble_delay_ms": "slow"}},               ("corruption", "scramble_delay_ms")),
    ({"corruption": {"resolve_frames": "many"}},                  ("corruption", "resolve_frames")),
    ({"player_name": None},                                       ("player_name",)),
    ({"player_name": 42},                                         ("player_name",)),
])
def test_wrong_kind_of_value_falls_back_to_its_default(tmp_path: Path, settings: dict, keys: tuple) -> None:
    cfg = _load(tmp_path, json.dumps(settings))
    assert _dig(cfg, keys) == _dig(_DEFAULTS, keys)


@pytest.mark.parametrize("text", [
    '{"picker": {"page_size": NaN}}',
    '{"picker": {"page_size": Infinity}}',
])
def test_not_a_real_number_falls_back_to_its_default(tmp_path: Path, text: str) -> None:
    assert _load(tmp_path, text)["picker"]["page_size"] == 5


def test_one_bad_value_does_not_cost_you_the_rest_of_the_file(tmp_path: Path) -> None:
    cfg = _load(tmp_path, json.dumps({
        "player_name": "Ana",
        "picker": {"page_size": "ten"},
        "typewriter": {"delay_ms": "fast", "pause_ms": 900, "punctuation_pauses": {".": "long", "!": 100}},
        "styles": {"warning": "red", "echo": {"color": "green"}},
        "corruption": None,
    }))
    assert cfg["picker"]["page_size"] == 5
    assert cfg["typewriter"]["delay_ms"] == 35
    assert cfg["typewriter"]["punctuation_pauses"]["."] == 550
    assert cfg["styles"]["warning"] == _DEFAULTS["styles"]["warning"]
    assert cfg["corruption"] == _DEFAULTS["corruption"]
    # The good values next to the bad ones are still honoured.
    assert cfg["player_name"] == "Ana"
    assert cfg["typewriter"]["pause_ms"] == 900
    assert cfg["typewriter"]["punctuation_pauses"]["!"] == 100
    assert cfg["styles"]["echo"]["color"] == "green"


# ------------------------------------------------------------------
# Whole-number settings given a number with a decimal point
# ------------------------------------------------------------------

@pytest.mark.parametrize("settings, keys", [
    ({"corruption": {"scramble_frames": 2.5}},                    ("corruption", "scramble_frames")),
    ({"corruption": {"resolve_frames": 2.5}},                     ("corruption", "resolve_frames")),
    ({"picker": {"page_size": 2.5}},                              ("picker", "page_size")),
    ({"typewriter": {"punctuation_pauses": {".": 2.5}}},          ("typewriter", "punctuation_pauses", ".")),
])
def test_whole_number_setting_drops_the_decimals(tmp_path: Path, settings: dict, keys: tuple) -> None:
    value = _dig(_load(tmp_path, json.dumps(settings)), keys)
    assert value == 2
    assert isinstance(value, int)


# ------------------------------------------------------------------
# Things that were fine before and must stay fine
# ------------------------------------------------------------------

def test_good_values_are_kept_as_written(tmp_path: Path) -> None:
    cfg = _load(tmp_path, json.dumps({
        "accessible_mode": True,
        "typewriter": {"enabled": False, "delay_ms": 2.5},
        "styles": {"classified": {"color": "green", "prefix": "[REDACTED] "}},
        "corruption": {"intensity": 1, "scramble_frames": 500, "resolve_frames": 12, "cascade_stagger_ms": None},
    }))
    assert cfg["accessible_mode"] is True                    # a key this player does not use
    assert cfg["typewriter"]["enabled"] is False
    assert cfg["typewriter"]["delay_ms"] == 2.5              # not a whole-number setting
    assert cfg["styles"]["classified"] == {"color": "green", "prefix": "[REDACTED] "}
    assert cfg["corruption"]["intensity"] == 1
    assert cfg["corruption"]["scramble_frames"] == 500       # out of range is the clamps' job, not this one's
    assert cfg["corruption"]["resolve_frames"] == 12
    assert cfg["corruption"]["cascade_stagger_ms"] is None   # "Auto"


def test_the_example_settings_file_loads_as_written() -> None:
    example = Path(__file__).parent.parent / "settings.example.json"
    written = json.loads(example.read_text(encoding="utf-8"))
    cfg = load_settings(example)
    for group in ("picker", "typewriter", "overlay", "corruption"):
        assert cfg[group] == written[group]


def test_loading_does_not_rewrite_the_players_file(tmp_path: Path) -> None:
    text = '{"picker": {"page_size": "ten"}, "typewriter": null}'
    _load(tmp_path, text)
    assert (tmp_path / "settings.json").read_text(encoding="utf-8") == text


# ------------------------------------------------------------------
# The places where the game used to fall over
# ------------------------------------------------------------------

def test_story_picker_survives_a_page_size_in_words(tmp_path: Path, monkeypatch) -> None:
    display = _display_with(tmp_path, monkeypatch, {"picker": {"page_size": "ten"}})
    assert display.get_page_size() == 5


def test_typewriter_survives_a_speed_in_words(tmp_path: Path, monkeypatch) -> None:
    display = _display_with(tmp_path, monkeypatch, {"typewriter": {"delay_ms": "fast"}})
    assert display._typewriter_delay() == pytest.approx(0.035)


def test_charset_survives_a_missing_corruption_group(tmp_path: Path, monkeypatch) -> None:
    display = _display_with(tmp_path, monkeypatch, {"corruption": None})
    assert display._get_charset() == CHARSETS["blocks"]


def test_corruption_survives_an_intensity_in_words(tmp_path: Path, monkeypatch) -> None:
    display = _display_with(tmp_path, monkeypatch, {"corruption": {"intensity": "high"}})
    assert effective_intensity(None, display._cfg["corruption"]) == pytest.approx(0.6)


@pytest.mark.parametrize("settings", [
    {"styles": {"warning": "red"}},
    {"styles": {"warning": {"color": None}}},
    {"styles": None},
])
def test_overlay_survives_a_broken_style(tmp_path: Path, monkeypatch, settings: dict) -> None:
    display = _display_with(tmp_path, monkeypatch, settings)
    display.console = Console(file=StringIO(), width=80, legacy_windows=False)
    display._render_overlay(Overlay(text="Mind the step.", style="warning"))
    assert "Mind the step." in display.console.file.getvalue()
