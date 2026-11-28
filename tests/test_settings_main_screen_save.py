"""Saving on the main Settings screen has to stick for the rest of the session."""
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config import load_settings, save_settings
from src.display import Display


@pytest.fixture
def display(tmp_path: Path, monkeypatch) -> Display:
    # Give the game a settings file of its own in an empty folder. Nobody wants a
    # test scribbling over their real settings, wherever the game keeps them.
    path = tmp_path / "settings.json"
    monkeypatch.setattr("src.display.load_settings", lambda: load_settings(path))
    monkeypatch.setattr("src.display.save_settings", lambda data: save_settings(data, path))
    d = Display()
    d.console = MagicMock()
    return d


def _on_disk(tmp_path: Path) -> dict:
    return json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))


def _printed_row(display: Display, label: str) -> str:
    """The last line the screen printed for the row with this label."""
    lines = [str(c.args[0]) for c in display.console.print.call_args_list if c.args]
    return [line for line in lines if label in line][-1]


def test_save_on_main_screen_reaches_the_running_game(display: Display) -> None:
    # "2" edits Stories per page, "10" sets it, "s" saves, "" is press-enter-to-return
    display.console.input.side_effect = ["2", "10", "s", ""]
    display.show_settings_screen()
    assert display.get_page_size() == 10


def test_running_game_holds_what_was_written_to_disk(display: Display, tmp_path: Path) -> None:
    display.console.input.side_effect = ["2", "10", "s", ""]
    display.show_settings_screen()
    assert display._cfg == _on_disk(tmp_path)


def test_second_visit_shows_the_saved_value(display: Display) -> None:
    display.console.input.side_effect = ["2", "10", "s", "", "x"]
    display.show_settings_screen()
    display.console.print.reset_mock()
    display.show_settings_screen()  # second visit, "x" leaves without touching anything
    assert "[bold]10[/bold]" in _printed_row(display, "Stories per page")


def test_second_save_keeps_the_first_change(display: Display, tmp_path: Path) -> None:
    # The exact steps from the bug report: save a page size, come back, save a name.
    display.console.input.side_effect = ["2", "10", "s", "", "4", "Ana", "s", ""]
    display.show_settings_screen()
    assert _on_disk(tmp_path)["picker"]["page_size"] == 10
    display.show_settings_screen()
    saved = _on_disk(tmp_path)
    assert saved["player_name"] == "Ana"
    assert saved["picker"]["page_size"] == 10


def test_discard_on_main_screen_still_changes_nothing(display: Display, tmp_path: Path) -> None:
    before = display.get_page_size()
    assert before != 10
    display.console.input.side_effect = ["2", "10", "x"]
    display.show_settings_screen()
    assert display.get_page_size() == before
    assert not (tmp_path / "settings.json").exists()
