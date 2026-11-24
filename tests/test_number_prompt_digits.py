# Some keys type things that look like digits and are not numbers. The French
# keyboard has a 2 in superscript sitting right next to the 1. Typing one of
# those at a number prompt used to crash the game. It should be a wrong answer
# like any other wrong answer.

from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
from rich.console import Console

from src.config import SETTINGS_SECTIONS, load_settings
from src.display import Display
from src.story import Choice


def _real_display() -> tuple[Display, StringIO]:
    d = Display()
    d._cfg.setdefault("typewriter", {})["enabled"] = False
    buf = StringIO()
    d.console = Console(file=buf, width=100, force_terminal=False)
    return d, buf


_CHOICES = [Choice(label="Go", next="a"), Choice(label="Stay", next="b"), Choice(label="Wait", next="c")]
_CORRUPTION = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
_PAGE_SIZE_ROW = next(
    row for s in SETTINGS_SECTIONS for row in s["rows"] if row["key"] == "picker.page_size"
)

# One line per number prompt in the game:
# (name, typed before the number, a number the prompt accepts, typed afterwards to get out, the prompt)
_PROMPTS = [
    ("story_picker", [], "3", ["q"], lambda d, draft: d.prompt_story_select(3)),
    ("settings_screen", [], "3", ["x", "x"], lambda d, draft: d.show_settings_screen()),
    ("settings_number_row", [], "3", [""], lambda d, draft: d._edit_row(draft, _PAGE_SIZE_ROW)),
    ("settings_section", [], "3", ["", "x"], lambda d, draft: d._section_subscreen(_CORRUPTION, draft)),
    ("custom_speed", ["6"], "30", ["50"], lambda d, draft: d._settings_edit_speed(draft["typewriter"])),
    ("reset_selector", [], "3", ["x"], lambda d, draft: d._show_reset_selector(draft)),
    ("story_choice", [], "3", ["q"], lambda d, draft: d.prompt_choice(_CHOICES)),
    ("saga_chapter", [], "3", ["b"], lambda d, draft: d.prompt_saga_select(3, 1)),
]
_PROMPT_NAMES = [p[0] for p in _PROMPTS]

_FULL_WIDTH = str.maketrans("0123456789", "０１２３４５６７８９")
_ARABIC_INDIC = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def _answer(prompt, typed: str):
    """Type one answer at a prompt, then leave. Return what the prompt gave back,
    what it did to the settings, and everything it put on screen."""
    _name, before, _good, way_out, call = prompt
    d, buf = _real_display()
    draft = load_settings(Path("nonexistent_settings.json"))
    with patch("builtins.input", side_effect=before + [typed] + way_out):
        result = call(d, draft)
    return result, draft, buf.getvalue()


@pytest.mark.parametrize("typed", ["²", "³", "¹", "①"])
@pytest.mark.parametrize("prompt", _PROMPTS, ids=_PROMPT_NAMES)
def test_lookalike_digit_is_just_a_wrong_answer(prompt, typed):
    # "zz" is plainly wrong at every one of these prompts. The lookalike must get the same treatment.
    assert _answer(prompt, typed) == _answer(prompt, "zz")


# Full-width and Arabic-Indic digits are real numbers. They worked before and they have to keep working.
@pytest.mark.parametrize("alphabet", [_FULL_WIDTH, _ARABIC_INDIC], ids=["full_width", "arabic_indic"])
@pytest.mark.parametrize("prompt", _PROMPTS, ids=_PROMPT_NAMES)
def test_digits_from_other_scripts_still_count(prompt, alphabet):
    good = prompt[2]
    assert _answer(prompt, good.translate(alphabet)) == _answer(prompt, good)
