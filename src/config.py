from __future__ import annotations

import json
import math
from pathlib import Path

_STYLE_FIELDS = ("color", "dim", "italic", "bold", "underline", "strike", "prefix")

_DEFAULTS: dict = {
    "player_name": "Felix",
    "picker": {
        "page_size": 5,
    },
    "typewriter": {
        "enabled": True,
        "delay_ms": 35,
        "pause_ms": 500,
        "punctuation_pauses": {
            ".": 550,
            "!": 250,
            "?": 350,
            "…": 700,
            "—": 600,
        },
    },
    "overlay": {
        "color": "cyan",
        "dim": True,
        "italic": True,
        "bold": False,
        "underline": False,
        "strike": False,
        "prefix": "✦ ",
    },
    "styles": {
        "whisper": {"color": "cyan",    "dim": True,  "italic": True,  "bold": False, "underline": False, "strike": False, "prefix": "✦ "},
        "echo":    {"color": "blue",    "dim": True,  "italic": True,  "bold": False, "underline": False, "strike": False, "prefix": "~ "},
        "warning": {"color": "yellow",  "dim": False, "italic": False, "bold": True,  "underline": False, "strike": False, "prefix": "⚠ "},
        "memory":  {"color": "magenta", "dim": True,  "italic": True,  "bold": False, "underline": False, "strike": False, "prefix": "◈ "},
        "system":  {"color": "white",   "dim": True,  "italic": False, "bold": False, "underline": False, "strike": False, "prefix": ""},
    },
    "corruption": {
        "enabled": True,
        "intensity": 0.6,
        "intensity_multiplier": 1.0,
        "mode": "consistent",
        "charset": "blocks",
        "custom_chars": "█▓▒░",
        "animate": True,
        "scramble_frames": 85,
        "scramble_delay_ms": 40,
        "resolve_frames": None,
        "resolve_delay_ms": None,
        "cascade_stagger_ms": None,
    },
}


def _get_draft_value(draft: dict, key: str):
    """Get a value from draft using dot-path notation.

    Handles special cases for nested dicts like punctuation_pauses where
    the character itself is part of the path (e.g., "typewriter.punctuation_pauses..").
    """
    if key.startswith("typewriter.punctuation_pauses."):
        char = key[len("typewriter.punctuation_pauses."):]
        return draft.get("typewriter", {}).get("punctuation_pauses", {}).get(char)
    if key.startswith("typewriter."):
        return draft.get("typewriter", {}).get(key[len("typewriter."):])
    if key.startswith("picker."):
        return draft.get("picker", {}).get(key[len("picker."):])
    if key.startswith("corruption."):
        return draft.get("corruption", {}).get(key[len("corruption."):])
    return draft.get(key)


def _set_draft_value(draft: dict, key: str, value) -> None:
    """Set a value in draft using dot-path notation.

    Handles special cases for nested dicts like punctuation_pauses where
    the character itself is part of the path (e.g., "typewriter.punctuation_pauses..").
    Creates intermediate dicts as needed.
    """
    if key.startswith("typewriter.punctuation_pauses."):
        char = key[len("typewriter.punctuation_pauses."):]
        draft.setdefault("typewriter", {}).setdefault("punctuation_pauses", {})[char] = value
    elif key.startswith("typewriter."):
        draft.setdefault("typewriter", {})[key[len("typewriter."):]] = value
    elif key.startswith("picker."):
        draft.setdefault("picker", {})[key[len("picker."):]] = value
    elif key.startswith("corruption."):
        draft.setdefault("corruption", {})[key[len("corruption."):]] = value
    else:
        draft[key] = value


def apply_section_defaults(draft: dict, section: dict) -> None:
    """Reset all keys in a section back to defaults.

    Takes a section dict (from SETTINGS_SECTIONS) and resets all its
    config_keys to their default values from _DEFAULTS.
    """
    for key in section["config_keys"]:
        draft[key] = _deep_copy(_DEFAULTS[key])


SETTINGS_SECTIONS: list[dict] = [
    {
        "id": "typewriter",
        "label": "Typewriter",
        "preserve_on_global_reset": False,
        "has_subscreen": True,
        "config_keys": ["typewriter"],
        "rows": [
            {"key": "typewriter.enabled",                     "label": "Enabled",           "type": "boolean"},
            {"key": "typewriter.delay_ms",                    "label": "Speed",             "type": "speed_presets", "unit": "ms"},
            {"key": "typewriter.punctuation_pauses..",        "label": "Pause after  .",    "type": "number",  "unit": "ms", "range": (0, 2000)},
            {"key": "typewriter.punctuation_pauses.!",        "label": "Pause after  !",    "type": "number",  "unit": "ms", "range": (0, 2000)},
            {"key": "typewriter.punctuation_pauses.?",        "label": "Pause after  ?",    "type": "number",  "unit": "ms", "range": (0, 2000)},
            {"key": "typewriter.punctuation_pauses.…",   "label": "Pause after  …", "type": "number", "unit": "ms", "range": (0, 2000)},
            {"key": "typewriter.punctuation_pauses.—",   "label": "Pause after  —", "type": "number", "unit": "ms", "range": (0, 2000)},
        ],
    },
    {
        "id": "display",
        "label": "Display",
        "preserve_on_global_reset": False,
        "has_subscreen": False,
        "config_keys": ["picker"],
        "rows": [
            {"key": "picker.page_size", "label": "Stories per page", "type": "number", "unit": "", "range": (1, 50)},
        ],
    },
    {
        "id": "corruption",
        "label": "Corruption",
        "preserve_on_global_reset": False,
        "has_subscreen": True,
        "config_keys": ["corruption"],
        "rows": [
            {"key": "corruption.enabled",              "label": "Enabled",              "type": "boolean"},
            {"key": "corruption.intensity",             "label": "Intensity Default",    "type": "float",  "unit": "×", "range": (0.0, 1.0)},
            {"key": "corruption.intensity_multiplier",  "label": "Intensity Multiplier", "type": "float",  "unit": "×", "range": (0.0, 1.0)},
            {"key": "corruption.mode",                  "label": "Mode Default",         "type": "cycle",  "values": ["consistent", "random"]},
            {"key": "corruption.charset",                "label": "Character set",        "type": "cycle",  "values": ["blocks", "symbols", "diacritics", "custom"]},
            {"key": "corruption.custom_chars",           "label": "Custom chars",         "type": "custom_chars"},
            {"key": "corruption.animate",                "label": "Animate",              "type": "boolean"},
            {"key": "corruption.scramble_frames",        "label": "Scramble frames",      "type": "number", "unit": "",   "range": (1, 200)},
            {"key": "corruption.scramble_delay_ms",      "label": "Scramble delay",       "type": "number", "unit": "ms", "range": (0, 1000)},
            {"key": "corruption.resolve_frames",         "label": "Resolve frames",       "type": "number", "unit": "",   "range": (1, 200)},
            {"key": "corruption.resolve_delay_ms",       "label": "Resolve delay",        "type": "number", "unit": "ms", "range": (0, 1000)},
            {"key": "corruption.cascade_stagger_ms",     "label": "Cascade stagger",      "type": "number", "unit": "ms", "range": (0, 1000)},
        ],
    },
    {
        "id": "player",
        "label": "Player",
        "preserve_on_global_reset": True,
        "has_subscreen": False,
        "config_keys": ["player_name"],
        "rows": [
            {"key": "player_name", "label": "Player name Default", "type": "text"},
        ],
    },
]


SETTING_RANGES: dict[str, tuple] = {
    row["key"]: row["range"]
    for section in SETTINGS_SECTIONS
    for row in section["rows"]
    if "range" in row
}


def clamp_setting(key: str, value):
    """Clamp a numeric setting to its registry range.

    Non-numbers (None, str, bool) and keys without a range pass through unchanged.
    """
    rng = SETTING_RANGES.get(key)
    if rng is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    lo, hi = rng
    return min(max(value, lo), hi)


def corruption_timing(cfg_corruption: dict) -> dict[str, int]:
    """Corruption animation frame counts and delays (ms), clamped to their ranges.

    resolve_frames / resolve_delay_ms / cascade_stagger_ms fall back to the
    (clamped) scramble values when unset (None).
    """
    scramble_frames = clamp_setting("corruption.scramble_frames", cfg_corruption.get("scramble_frames", 8))
    scramble_delay = clamp_setting("corruption.scramble_delay_ms", cfg_corruption.get("scramble_delay_ms", 60))

    def _or_fallback(key: str, fallback):
        raw = cfg_corruption.get(key)
        return clamp_setting(f"corruption.{key}", raw if raw is not None else fallback)

    return {
        "scramble_frames": scramble_frames,
        "scramble_delay_ms": scramble_delay,
        "resolve_frames": _or_fallback("resolve_frames", scramble_frames),
        "resolve_delay_ms": _or_fallback("resolve_delay_ms", scramble_delay),
        "cascade_stagger_ms": _or_fallback("cascade_stagger_ms", scramble_delay),
    }


# settings.json lives in the game folder (one level up from src/), so it is the
# same file no matter which folder the game was started from.
SETTINGS_PATH = Path(__file__).resolve().parent.parent / "settings.json"


def save_settings(data: dict, path: Path = SETTINGS_PATH) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_settings(path: Path = SETTINGS_PATH) -> dict:
    if not path.exists():
        return _deep_copy(_DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _deep_copy(_DEFAULTS)
        return _merge(_DEFAULTS, data)
    except (json.JSONDecodeError, OSError):
        return _deep_copy(_DEFAULTS)


# Settings the game counts with, like frames or stories per page. 2.5 frames is not a thing.
_WHOLE_NUMBER_KEYS = {
    row["key"]
    for section in SETTINGS_SECTIONS
    for row in section["rows"]
    if row["type"] == "number"
}


def _same_kind(default, value) -> bool:
    """True when a value from settings.json is the same kind of thing as its default."""
    if isinstance(default, bool):
        return isinstance(value, bool)
    if isinstance(default, str):
        return isinstance(value, str)
    # What is left are the numbers, plus the "Auto" settings whose default is None.
    if value is None:
        return default is None
    if isinstance(value, float):
        return math.isfinite(value)
    return isinstance(value, int) and not isinstance(value, bool)


def _merge(defaults: dict, overrides: dict, path: str = "") -> dict:
    # People edit settings.json by hand, and people type "ten" where a 10 belongs.
    # A value of the wrong kind is skipped, so that one setting keeps its default
    # and the rest of the file still counts. Keys we do not know pass through as before.
    result = _deep_copy(defaults)
    for key, value in overrides.items():
        if key not in result:
            result[key] = value
        elif isinstance(result[key], dict):
            if isinstance(value, dict):
                result[key] = _merge(result[key], value, f"{path}{key}.")
        elif _same_kind(result[key], value):
            if isinstance(value, float) and f"{path}{key}" in _WHOLE_NUMBER_KEYS:
                value = int(value)
            result[key] = value
    return result


def _deep_copy(d: dict) -> dict:
    return json.loads(json.dumps(d))
