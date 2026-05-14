from __future__ import annotations

import json
from pathlib import Path

_STYLE_FIELDS = ("color", "dim", "italic", "bold", "underline", "strike", "prefix")

_DEFAULTS: dict = {
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
}


def load_settings(path: Path = Path("settings.json")) -> dict:
    if not path.exists():
        return _deep_copy(_DEFAULTS)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return _merge(_DEFAULTS, data)
    except (json.JSONDecodeError, OSError):
        return _deep_copy(_DEFAULTS)


def _merge(defaults: dict, overrides: dict) -> dict:
    result = _deep_copy(defaults)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _merge(result[key], value)
        else:
            result[key] = value
    return result


def _deep_copy(d: dict) -> dict:
    return json.loads(json.dumps(d))
