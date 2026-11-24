"""Reader mode: paragraph breaks written by the author must survive on screen.

This is a styling rule, so there is nothing to run in Node. These tests read
web/style.css and pin the rule, the same way tests/test_web_player_assets.py does.
The real proof is a look at the page in a browser.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rule(selector: str) -> str:
    css = (ROOT / "web" / "style.css").read_text(encoding="utf-8")
    match = re.search(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", css)
    assert match, f"No CSS rule for {selector}"
    return match.group(1)


def test_reader_story_and_ending_text_keeps_paragraph_breaks() -> None:
    # Story text and ending text both sit in an r-prose paragraph.
    assert "white-space: pre-wrap" in _rule(".reader-screen .r-prose")


def test_reader_insets_keep_paragraph_breaks() -> None:
    assert "white-space: pre-wrap" in _rule(".reader-screen .r-inset")
