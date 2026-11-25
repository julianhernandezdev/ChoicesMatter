"""Tests for the phone-sized terminal view of the web player.

The story text used to shrink to about 9px on a phone. These tests pin the
stylesheet rule that keeps it readable, and run the real ruleHtml helper from
web/app.js through Node. The sizes on a real screen were checked by hand in a
browser; a stylesheet cannot be laid out from pytest.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_DRAWN_LINES = (
    ".terminal-rule",
    ".terminal-panel-title",
    ".terminal-separator",
    ".terminal-ending-label",
)


def _run(script: str) -> str:
    """Execute an ES-module snippet via Node stdin and return stdout."""
    result = subprocess.run(
        ["node", "--input-type=module"],
        input=script.encode(),
        capture_output=True,
        cwd=ROOT,
        timeout=10,
    )
    assert result.returncode == 0, result.stderr.decode()
    return result.stdout.decode().strip()


def _css() -> str:
    return (ROOT / "web" / "style.css").read_text(encoding="utf-8")


def _app() -> str:
    return (ROOT / "web" / "app.js").read_text(encoding="utf-8")


def _phone_block() -> str:
    """The whole `@media (max-width: 76ch) { ... }` block, braces included."""
    css = _css()
    start = css.index("@media (max-width: 76ch)")
    depth = 0
    for i in range(css.index("{", start), len(css)):
        if css[i] == "{":
            depth += 1
        elif css[i] == "}":
            depth -= 1
            if depth == 0:
                return css[start:i + 1]
    raise AssertionError("the phone block never closes")


def _phone_rules() -> dict[str, dict[str, str]]:
    """Selector -> declarations for every rule inside the phone block."""
    block = _phone_block()
    inner = block[block.index("{") + 1:block.rindex("}")]
    rules: dict[str, dict[str, str]] = {}
    for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", inner):
        declarations = {
            name.strip(): value.strip()
            for name, value in (d.split(":", 1) for d in body.split(";") if ":" in d)
        }
        for selector in selectors.split(","):
            rules.setdefault(" ".join(selector.split()), {}).update(declarations)
    return rules


def _function_source(name: str) -> str:
    """Cut one top-level function out of app.js (app.js needs a browser to import)."""
    match = re.search(r"^function " + name + r"\(.*?^}$", _app(), re.S | re.M)
    assert match, f"function {name} not found in web/app.js"
    return match.group(0)


def _rule_html(text: str, width: int) -> dict[str, str]:
    """Run the real makeRule and ruleHtml from app.js and return both results."""
    script = "\n".join([
        _function_source("escapeHtml"),
        _function_source("makeRule"),
        _function_source("ruleHtml"),
        f"var text = {json.dumps(text)};",
        f"console.log(JSON.stringify({{ plain: makeRule(text, {width}), html: ruleHtml(text, {width}) }}));",
    ])
    return json.loads(_run(script))


# ---------------------------------------------------------------------------
# Stylesheet: text size on a phone
# ---------------------------------------------------------------------------

def test_phone_terminal_text_is_a_readable_size() -> None:
    size = _phone_rules().get("body:not(.reader-mode)", {}).get("font-size", "")
    assert size.endswith("rem"), f"terminal view has no fixed phone text size: {size!r}"
    pixels = float(size[:-3]) * 16
    assert 15 <= pixels <= 16


def test_phone_small_print_stays_above_12px() -> None:
    # The smallest text in the terminal view is sized as a share of the body text.
    size = _phone_rules().get("body:not(.reader-mode)", {}).get("font-size", "0rem")
    body_pixels = float(size[:-3]) * 16
    shares = [float(s) for s in re.findall(r"font-size:\s*([0-9.]+)em", _css().split("/* === READER MODE")[0])]
    assert shares
    assert body_pixels * min(shares) >= 12


def test_phone_drawn_lines_are_trimmed_to_the_screen() -> None:
    rules = _phone_rules()
    for name in _DRAWN_LINES:
        rule = rules.get("body:not(.reader-mode) " + name, {})
        assert rule.get("overflow") == "hidden", name
        assert rule.get("display") == "flex", name
        assert rule.get("justify-content") == "center", name


def test_phone_rule_words_stay_whole_and_wrap() -> None:
    rule = _phone_rules().get("body:not(.reader-mode) .rule-words", {})
    assert rule.get("flex-shrink") == "0"
    assert rule.get("max-width") == "100%"
    assert rule.get("white-space") == "pre-wrap"


def test_reader_mode_keeps_its_old_phone_rule() -> None:
    assert _phone_rules()["body"] == {"font-size": "clamp(0.55rem, 2.1vw, 1rem)"}


def test_phone_changes_stay_inside_the_phone_block() -> None:
    outside = _css().replace(_phone_block(), "")
    assert ":not(.reader-mode)" not in outside
    assert ".rule-words" not in outside


# ---------------------------------------------------------------------------
# app.js: ruleHtml marks the words inside a drawn line
# ---------------------------------------------------------------------------

def test_rule_html_marks_the_words() -> None:
    result = _rule_html("Select a Story", 74)
    assert result["html"].count('<span class="rule-words">Select a Story</span>') == 1


def test_rule_html_draws_the_same_line_as_make_rule() -> None:
    result = _rule_html("Platform 3 \u2014 Eastfield Station", 74)
    shown = result["html"].replace('<span class="rule-words">', "").replace("</span>", "")
    assert shown == result["plain"]
    assert len(shown) == 74


def test_rule_html_plain_line_has_no_markup() -> None:
    result = _rule_html("", 70)
    assert result["html"] == "\u2500" * 70


def test_rule_html_escapes_the_words() -> None:
    result = _rule_html("<b>Tom & Jerry</b>", 70)
    assert '<span class="rule-words">&lt;b&gt;Tom &amp; Jerry&lt;/b&gt;</span>' in result["html"]
    assert "<b>" not in result["html"]


def test_scene_rule_and_panel_title_use_rule_html() -> None:
    app = _app()
    assert "ruleHtml(text, w)" in _function_source("renderRule")
    assert "ruleHtml(storyTitle(currentRun.entry), PANEL_RULE_WIDTH)" in app
