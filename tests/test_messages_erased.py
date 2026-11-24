"""One-line messages must still be on screen when the game next waits for the player.

These messages used to be printed and then wiped by the very next screen redraw,
so the player never got to read them. Each test plays a short session and looks at
what was on screen every time the game stopped to wait for a key.
"""
import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

import main as main_module
from src.config import SETTINGS_SECTIONS, load_settings
from src.display import Display

# What rich writes to the terminal when the screen is cleared.
CLEAR = "\x1b[2J"
PAUSE = "Press Enter to return."


def _play(answers, run):
    """Run `run(display)` on a real Display, typing `answers` one per prompt.

    Returns one string per prompt: what was on screen while the game waited there,
    which is everything printed since the last screen clear.
    """
    d = Display()
    d._cfg.setdefault("typewriter", {})["enabled"] = False
    buf = StringIO()
    d.console = Console(file=buf, width=100, force_terminal=True, legacy_windows=False, color_system=None)
    pending = list(answers)
    screens = []

    def typed():
        screens.append(buf.getvalue().rsplit(CLEAR, 1)[-1])
        return pending.pop(0)

    with patch("builtins.input", side_effect=typed):
        run(d)
    return screens


def _assert_readable(screens, message):
    """The message must be on screen at a pause, not just printed and wiped."""
    showing = [s for s in screens if message in s]
    assert showing, f"{message!r} was never on screen while the game waited for the player"
    assert showing[0].rstrip().endswith(PAUSE)


def _broken_story(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    story = {
        "meta": {"id": "broken", "title": "Broken", "version": "1.0", "author": "Tester", "start_node": "nowhere"},
        "nodes": {"start": {"text": "You begin here.", "choices": []}},
    }
    (folder / "broken.json").write_text(json.dumps(story), encoding="utf-8")


def _play_main(tmp_path: Path, answers, folder: str | None = None):
    """Play the real story picker in main.py against a stories folder holding one broken story."""
    stories = tmp_path / "stories"
    saves = tmp_path / "saves"
    saves.mkdir()
    _broken_story(stories / folder if folder else stories)

    def run(display):
        with patch.object(sys, "argv", ["main.py"]), \
             patch.object(main_module, "STORIES_DIR", stories), \
             patch.object(main_module, "SAVES_DIR", saves), \
             patch("main.Display", return_value=display):
            main_module.main()

    return _play(answers, run)


def _corruption_section() -> dict:
    return next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")


# ------------------------------------------------------------------
# Story picker
# ------------------------------------------------------------------

def test_story_load_error_stays_until_enter(tmp_path: Path) -> None:
    # 1 = open the broken story, Enter = done reading, Q = quit
    screens = _play_main(tmp_path, ["1", "", "q"])
    _assert_readable(screens, "Error loading 'broken.json':")


def test_story_load_error_inside_a_folder_stays_until_enter(tmp_path: Path) -> None:
    # 1 = open the folder, 1 = open the broken story, Enter = done reading, B = back, Q = quit
    screens = _play_main(tmp_path, ["1", "1", "", "b", "q"], folder="drafts")
    _assert_readable(screens, "Error loading 'broken.json':")


def test_save_data_cleared_message_stays_until_enter(tmp_path: Path) -> None:
    # C = clear saves, Y = yes really, Enter = done reading, Q = quit
    screens = _play_main(tmp_path, ["c", "y", "", "q"])
    _assert_readable(screens, "All save data cleared.")


# ------------------------------------------------------------------
# Settings screens
# ------------------------------------------------------------------

def test_custom_characters_hint_stays_until_enter() -> None:
    section = _corruption_section()
    row = next(i for i, r in enumerate(section["rows"], start=1) if r["type"] == "custom_chars")
    draft = load_settings(Path("nonexistent_settings.json"))
    draft["corruption"]["charset"] = "blocks"
    # custom characters row, Enter = done reading, X = back
    screens = _play([str(row), "", "x"], lambda d: d._section_subscreen(section, draft))
    _assert_readable(screens, "Set character set to 'custom' first.")


def test_section_reset_message_stays_until_enter() -> None:
    section = _corruption_section()
    draft = load_settings(Path("nonexistent_settings.json"))
    # R = reset section, Y = yes really, Enter = done reading, X = back
    screens = _play(["r", "y", "", "x"], lambda d: d._section_subscreen(section, draft))
    _assert_readable(screens, "Corruption reset to defaults.")


def test_nothing_selected_message_stays_until_enter() -> None:
    draft = load_settings(Path("nonexistent_settings.json"))
    # Y = confirm with no box ticked, Enter = done reading, X = cancel
    screens = _play(["y", "", "x"], lambda d: d._show_reset_selector(draft))
    _assert_readable(screens, "Nothing selected.")
