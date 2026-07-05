import copy
from unittest.mock import MagicMock, patch
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console
from rich.panel import Panel

from src.display import Display, _strip_pause_tokens, _truncate_author, MAX_AUTHOR_LEN
from src.story import Choice, Inset, Overlay
from src.corruption import CorruptedSpan, TextSegments


@pytest.fixture
def display():
    d = Display()
    d.console = MagicMock()
    return d


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def test_typewriter_delay_zero_when_disabled(display):
    display._cfg["typewriter"]["enabled"] = False
    assert display._typewriter_delay() == 0.0


def test_typewriter_delay_converts_ms_to_seconds(display):
    display._cfg["typewriter"]["enabled"] = True
    display._cfg["typewriter"]["delay_ms"] = 40
    assert display._typewriter_delay() == pytest.approx(0.04)


def test_style_cfg_returns_named_style(display):
    result = display._style_cfg("warning")
    assert result["color"] == "yellow"


def test_style_cfg_falls_back_to_overlay_for_unknown(display):
    assert display._style_cfg("no_such_style") == display._cfg["overlay"]


def test_style_cfg_empty_string_falls_back_to_overlay(display):
    assert display._style_cfg("") == display._cfg["overlay"]


def test_inset_renderable_named_style_includes_text(display):
    inset = Inset(text="Vault memory.", style="memory")
    assert "Vault memory." in display._inset_renderable(inset).plain


def test_inset_renderable_empty_style_includes_text(display):
    inset = Inset(text="Ambient note.")
    assert "Ambient note." in display._inset_renderable(inset).plain


def test_render_overlay_calls_console_print(display):
    display._render_overlay(Overlay(text="A whisper.", style="whisper"))
    display.console.print.assert_called()


def test_render_overlay_default_style(display):
    display._render_overlay(Overlay(text="Plain overlay."))
    display.console.print.assert_called()


def test_node_panel_returns_panel(display):
    assert isinstance(display._node_panel("Title", "Body.", [], []), Panel)


def test_node_panel_with_insets_returns_panel(display):
    before = [Inset(text="Before.", position="before")]
    after = [Inset(text="After.", position="after")]
    assert isinstance(display._node_panel("Title", "Body.", before, after), Panel)


# ------------------------------------------------------------------
# _strip_pause_tokens
# ------------------------------------------------------------------

def test_strip_pause_tokens_removes_single_token():
    assert _strip_pause_tokens("Hello{pause}World") == "HelloWorld"

def test_strip_pause_tokens_removes_multiple_tokens():
    assert _strip_pause_tokens("{pause}A{pause}B{pause}") == "AB"

def test_strip_pause_tokens_no_token_unchanged():
    assert _strip_pause_tokens("Hello World") == "Hello World"

def test_strip_pause_tokens_empty_string():
    assert _strip_pause_tokens("") == ""


def test_show_node_strips_pause_token_when_typewriter_off(display):
    display._cfg["typewriter"]["enabled"] = False
    display.show_node("Title", ["Hello{pause}World"], [], [])
    panel = next(
        (c[0][0] for c in display.console.print.call_args_list if c[0] and isinstance(c[0][0], Panel)),
        None,
    )
    assert panel is not None, "No Panel found in print calls"
    cons = Console(file=StringIO(), width=80, legacy_windows=False)
    cons.print(panel)
    rendered = cons.file.getvalue()
    assert "{pause}" not in rendered
    assert "HelloWorld" in rendered


def test_show_ending_strips_pause_token_when_typewriter_off(display):
    display._cfg["typewriter"]["enabled"] = False
    display.show_ending(["The end{pause}."], "good", [])
    panel = next(
        (c[0][0] for c in display.console.print.call_args_list if c[0] and isinstance(c[0][0], Panel)),
        None,
    )
    assert panel is not None, "No Panel found in print calls"
    cons = Console(file=StringIO(), width=80, legacy_windows=False)
    cons.print(panel)
    rendered = cons.file.getvalue()
    assert "{pause}" not in rendered
    assert "The end." in rendered


# ------------------------------------------------------------------
# _typewrite: {pause} token
# ------------------------------------------------------------------

def test_typewrite_pause_token_sleeps_pause_ms():
    """Between {pause} segments, time.sleep is called with pause_ms / 1000."""
    d = Display()
    d.console = MagicMock()
    d._cfg["typewriter"]["pause_ms"] = 400
    d._cfg["typewriter"]["punctuation_pauses"] = {}

    sleep_calls = []
    mock_live = MagicMock()
    mock_live.__enter__ = MagicMock(return_value=mock_live)
    mock_live.__exit__ = MagicMock(return_value=False)

    with patch("src.display.time.sleep", side_effect=lambda s: sleep_calls.append(s)), \
         patch("src.display._key_pending", return_value=False), \
         patch("src.display.Live", return_value=mock_live):
        d._typewrite(lambda t: t, ["A{pause}B"], 0.0)

    assert pytest.approx(0.4) in sleep_calls


def test_typewrite_no_pause_token_no_extra_sleep():
    """Without {pause}, the inter-segment sleep is never called."""
    d = Display()
    d.console = MagicMock()
    d._cfg["typewriter"]["pause_ms"] = 400
    d._cfg["typewriter"]["punctuation_pauses"] = {}

    sleep_calls = []
    mock_live = MagicMock()
    mock_live.__enter__ = MagicMock(return_value=mock_live)
    mock_live.__exit__ = MagicMock(return_value=False)

    with patch("src.display.time.sleep", side_effect=lambda s: sleep_calls.append(s)), \
         patch("src.display._key_pending", return_value=False), \
         patch("src.display.Live", return_value=mock_live):
        d._typewrite(lambda t: t, ["Hello"], 0.0)

    assert pytest.approx(0.4) not in sleep_calls


def test_typewrite_skip_during_pause_shows_clean_text():
    """If a key is pressed during a {pause} wait, the full text shown has {pause} stripped."""
    d = Display()
    d.console = MagicMock()
    d._cfg["typewriter"]["pause_ms"] = 500
    d._cfg["typewriter"]["punctuation_pauses"] = {}

    shown = []
    mock_live = MagicMock()
    mock_live.__enter__ = MagicMock(return_value=mock_live)
    mock_live.__exit__ = MagicMock(return_value=False)
    mock_live.update = lambda p: shown.append(p)
    mock_live.refresh = MagicMock()

    with patch("src.display._key_pending", return_value=True), \
         patch("src.display._consume_key"), \
         patch("src.display.time.sleep"), \
         patch("src.display.Live", return_value=mock_live):
        d._typewrite(lambda t: t, ["A{pause}B"], 0.0)

    assert all("{pause}" not in str(p) for p in shown), \
        f"'{'{pause}'}' appeared in shown text: {shown}"
    assert any("AB" in str(p) for p in shown), \
        f"Expected 'AB' in shown text but got: {shown}"


# ------------------------------------------------------------------
# Chrome / indicators
# ------------------------------------------------------------------

def test_clear_screen_calls_console_clear(display):
    display.clear_screen()
    display.console.clear.assert_called_once()


def test_show_title_screen_prints(display):
    display.show_title_screen()
    display.console.print.assert_called()


def test_show_no_stories_prints(display):
    display.show_no_stories()
    display.console.print.assert_called()


def test_show_picker_error_prints(display):
    display.show_picker_error("story.json", "bad field")
    display.console.print.assert_called()


def test_show_save_indicator_prints(display):
    display.show_save_indicator()
    display.console.print.assert_called()


def test_show_clear_complete_prints(display):
    display.show_clear_complete()
    display.console.print.assert_called()


# ------------------------------------------------------------------
# Story picker
# ------------------------------------------------------------------

def test_show_story_picker_normal_entry(display):
    entries = [{"index": 1, "label": "My Story", "error": False, "has_save": False,
                "node_count": 10, "ending_count": 3, "endings_found": 1,
                "est_time": "~15 min", "has_warnings": False}]
    display.show_story_picker(entries)
    display.console.print.assert_called()


def test_show_story_picker_error_entry(display):
    display.show_story_picker([{"index": 1, "label": "broken", "error": True}])
    display.console.print.assert_called()


def test_show_story_picker_resume_and_warning_entry(display):
    entries = [{"index": 1, "label": "My Story", "error": False, "has_save": True,
                "node_count": 5, "ending_count": 2, "endings_found": 0,
                "est_time": "", "has_warnings": True}]
    display.show_story_picker(entries)
    display.console.print.assert_called()


def test_truncate_author_short_name_unchanged():
    assert _truncate_author("Tester") == "Tester"


def test_truncate_author_long_name_gets_ellipsis():
    long_name = "A Very Long Collective Author Name"
    result = _truncate_author(long_name)
    assert result == long_name[:MAX_AUTHOR_LEN].rstrip() + "..."
    assert len(result) <= MAX_AUTHOR_LEN + 3


def test_show_story_picker_byline_truncates_long_author(display):
    long_name = "A Very Long Collective Author Name"
    entries = [{"index": 1, "label": "My Story", "error": False, "has_save": False,
                "node_count": 5, "ending_count": 2, "endings_found": 0,
                "est_time": "", "has_warnings": False,
                "author": long_name, "version": "1.0"}]
    display.show_story_picker(entries)
    printed = " ".join(str(c) for c in display.console.print.call_args_list)
    assert "..." in printed
    assert long_name not in printed


def test_show_story_picker_byline_author_and_version(display):
    entries = [{"index": 1, "label": "My Story", "error": False, "has_save": False,
                "node_count": 5, "ending_count": 2, "endings_found": 0,
                "est_time": "", "has_warnings": False,
                "author": "Tester", "version": "1.0"}]
    display.show_story_picker(entries)
    printed = " ".join(str(c) for c in display.console.print.call_args_list)
    assert "by Tester" in printed
    assert "v1.0" in printed


def test_show_story_picker_no_byline_when_meta_absent(display):
    entries = [{"index": 1, "label": "My Story", "error": False, "has_save": False,
                "node_count": 5, "ending_count": 2, "endings_found": 0,
                "est_time": "", "has_warnings": False}]
    display.show_story_picker(entries)
    printed = " ".join(str(c) for c in display.console.print.call_args_list)
    assert "by " not in printed


# ------------------------------------------------------------------
# Toggle typewriter
# ------------------------------------------------------------------

def test_toggle_typewriter_off_to_on(display):
    display._cfg["typewriter"]["enabled"] = False
    display.toggle_typewriter()
    assert display._cfg["typewriter"]["enabled"] is True


def test_toggle_typewriter_on_to_off(display):
    display._cfg["typewriter"]["enabled"] = True
    display.toggle_typewriter()
    assert display._cfg["typewriter"]["enabled"] is False


# ------------------------------------------------------------------
# show_node / show_choices / show_ending (typewriter off)
# ------------------------------------------------------------------

def test_show_node_prints_panel(display):
    display._cfg["typewriter"]["enabled"] = False
    display.show_node("My Story", "You begin.", [], [])
    display.console.print.assert_called()


def test_show_node_with_scene_prints_rule_then_panel(display):
    display._cfg["typewriter"]["enabled"] = False
    display.show_node("My Story", "You begin.", [], [], current_scene="Act I")
    assert display.console.print.call_count >= 2


def test_show_choices_prints_each_choice(display):
    display._cfg["typewriter"]["enabled"] = False
    choices = [Choice(label="Go", next="a"), Choice(label="Stay", next="b")]
    display.show_choices(choices, [], [])
    assert display.console.print.call_count >= 2


def test_show_choices_with_before_and_after_overlays(display):
    display._cfg["typewriter"]["enabled"] = False
    choices = [Choice(label="Go", next="a")]
    before = [Overlay(text="Before.", position="before")]
    after = [Overlay(text="After.", position="after")]
    display.show_choices(choices, before, after)
    display.console.print.assert_called()


def test_show_ending_prints_panel(display):
    display._cfg["typewriter"]["enabled"] = False
    display.show_ending("You win.", "good", [])
    display.console.print.assert_called()


def test_show_ending_with_overlay(display):
    display._cfg["typewriter"]["enabled"] = False
    display.show_ending("The end.", "bad", [Overlay(text="A final whisper.")])
    display.console.print.assert_called()


# ------------------------------------------------------------------
# Prompt: story select
# ------------------------------------------------------------------

def test_prompt_story_select_valid_number(display):
    display.console.input.return_value = "2"
    assert display.prompt_story_select(3) == 2


def test_prompt_story_select_quit(display):
    display.console.input.return_value = "q"
    assert display.prompt_story_select(3) is None


def test_prompt_story_select_clear(display):
    display.console.input.return_value = "c"
    assert display.prompt_story_select(3) == "clear"


def test_prompt_story_select_toggle(display):
    display.console.input.return_value = "t"
    assert display.prompt_story_select(3) == "toggle_typewriter"


def test_prompt_story_select_settings(display):
    display.console.input.return_value = "s"
    assert display.prompt_story_select(3) == "settings"


def test_prompt_story_select_re_prompts_on_invalid(display):
    display.console.input.side_effect = ["x", "99", "1"]
    assert display.prompt_story_select(3) == 1


# ------------------------------------------------------------------
# Prompt: confirm / continue / choice / play-again
# ------------------------------------------------------------------

def test_prompt_clear_confirm_true_on_y(display):
    display.console.input.return_value = "y"
    assert display.prompt_clear_confirm() is True


def test_prompt_clear_confirm_false_on_other(display):
    display.console.input.return_value = "n"
    assert display.prompt_clear_confirm() is False


def test_prompt_continue_or_new_true_on_c(display):
    display.console.input.return_value = "c"
    assert display.prompt_continue_or_new() is True


def test_prompt_continue_or_new_false_on_n(display):
    display.console.input.return_value = "n"
    assert display.prompt_continue_or_new() is False


def test_prompt_continue_or_new_re_prompts_on_invalid(display):
    display.console.input.side_effect = ["x", "n"]
    assert display.prompt_continue_or_new() is False


def test_prompt_choice_returns_index(display):
    choices = [Choice(label="Go", next="a"), Choice(label="Stay", next="b")]
    display.console.input.return_value = "2"
    assert display.prompt_choice(choices) == 2


def test_prompt_choice_returns_none_on_q(display):
    display.console.input.return_value = "q"
    assert display.prompt_choice([Choice(label="Go", next="a")]) is None


def test_prompt_choice_re_prompts_on_out_of_range(display):
    display.console.input.side_effect = ["5", "1"]
    assert display.prompt_choice([Choice(label="Go", next="a")]) == 1


def test_prompt_play_again_true_on_y(display):
    display.console.input.return_value = "y"
    assert display.prompt_play_again() is True


def test_prompt_play_again_false_on_n(display):
    display.console.input.return_value = "n"
    assert display.prompt_play_again() is False


def test_prompt_play_again_re_prompts_on_invalid(display):
    display.console.input.side_effect = ["x", "y"]
    assert display.prompt_play_again() is True


def test_show_content_warnings_true_on_yes(display):
    display.console.input.return_value = "y"
    assert display.show_content_warnings("My Story", ["Violence"]) is True


def test_show_content_warnings_false_on_no(display):
    display.console.input.return_value = "n"
    assert display.show_content_warnings("My Story", ["Violence"]) is False


def test_show_content_warnings_re_prompts_on_invalid(display):
    display.console.input.side_effect = ["x", "n"]
    assert display.show_content_warnings("My Story", ["Horror"]) is False


# ------------------------------------------------------------------
# Settings screen
# ------------------------------------------------------------------

def test_show_settings_screen_discard_on_x(display):
    display.console.input.return_value = "x"
    display.show_settings_screen()  # must return without raising


def test_show_settings_screen_save_on_s(display):
    display.console.input.side_effect = ["s", ""]  # s=save, ""=press-enter-to-return
    with patch("src.display.save_settings") as mock_save:
        display.show_settings_screen()
        mock_save.assert_called_once()


def test_show_settings_screen_edit_number_row_then_discard(display):
    # "2" edits Stories per page (number row), "5" sets value, "x" discards
    display.console.input.side_effect = ["2", "5", "x"]
    display.show_settings_screen()  # must not raise


def test_show_settings_screen_edit_text_row_then_discard(display):
    # "4" edits Player name (text row), "" keeps current, "x" discards
    display.console.input.side_effect = ["4", "", "x"]
    display.show_settings_screen()


def test_show_settings_screen_edit_speed_then_discard(display):
    # "2" enters speed edit, "1" picks Slowest, "x" discards
    display.console.input.side_effect = ["2", "1", "x"]
    display.show_settings_screen()


def test_settings_edit_speed_preset(display):
    tw = {"delay_ms": 35}
    display.console.input.return_value = "2"  # Slow = 40 ms
    display._settings_edit_speed(tw)
    assert tw["delay_ms"] == 40


def test_settings_edit_speed_custom(display):
    tw = {"delay_ms": 35}
    display.console.input.side_effect = ["6", "25"]
    display._settings_edit_speed(tw)
    assert tw["delay_ms"] == 25


def test_settings_edit_speed_invalid_then_valid(display):
    tw = {"delay_ms": 35}
    display.console.input.side_effect = ["x", "3"]  # invalid, then Normal=35
    display._settings_edit_speed(tw)
    assert tw["delay_ms"] == 35


def test_settings_edit_speed_custom_invalid_then_valid(display):
    tw = {"delay_ms": 35}
    display.console.input.side_effect = ["6", "abc", "10"]
    display._settings_edit_speed(tw)
    assert tw["delay_ms"] == 10


from src.config import SETTINGS_SECTIONS


def test_format_row_value_boolean_true(display):
    row = {"type": "boolean"}
    result = display._format_row_value(row, True)
    assert "on" in result


def test_format_row_value_boolean_false(display):
    row = {"type": "boolean"}
    result = display._format_row_value(row, False)
    assert "off" in result


def test_format_row_value_number_with_unit(display):
    row = {"type": "number", "unit": "ms"}
    result = display._format_row_value(row, 35)
    assert "35" in result
    assert "ms" in result


def test_format_row_value_number_no_unit(display):
    row = {"type": "number", "unit": ""}
    result = display._format_row_value(row, 5)
    assert "5" in result


def test_format_row_value_cycle(display):
    row = {"type": "cycle", "values": ["consistent", "random"]}
    result = display._format_row_value(row, "consistent")
    assert "consistent" in result


def test_format_row_value_text(display):
    row = {"type": "text"}
    result = display._format_row_value(row, "Felix")
    assert "Felix" in result


# ------------------------------------------------------------------
# Debug mode: style labels
# ------------------------------------------------------------------

@pytest.fixture
def debug_display():
    d = Display(debug={"enabled": True, "all": False})
    d.console = MagicMock()
    return d


@pytest.fixture
def debug_all_display():
    d = Display(debug={"enabled": True, "all": True})
    d.console = MagicMock()
    return d


def test_inset_renderable_debug_named_style_appends_tag(debug_display):
    inset = Inset(text="She whispers.", style="memory")
    result = debug_display._inset_renderable(inset)
    assert "[memory]" in result.plain


def test_inset_renderable_debug_empty_style_appends_empty_tag(debug_display):
    inset = Inset(text="Ambient.", style="")
    result = debug_display._inset_renderable(inset)
    assert "[empty]" in result.plain


def test_inset_renderable_debug_absent_style_no_tag(debug_display):
    inset = Inset(text="Plain.")  # style defaults to None
    result = debug_display._inset_renderable(inset)
    assert "[" not in result.plain


def test_inset_renderable_no_debug_no_tag():
    d = Display()
    d.console = MagicMock()
    inset = Inset(text="She whispers.", style="memory")
    result = d._inset_renderable(inset)
    assert "[memory]" not in result.plain


def test_render_overlay_debug_appends_tag(debug_display):
    debug_display._render_overlay(Overlay(text="Whisper.", style="whisper"))
    printed = str(debug_display.console.print.call_args)
    assert "[whisper]" in printed


def test_render_overlay_debug_empty_style_appends_empty_tag(debug_display):
    debug_display._render_overlay(Overlay(text="Plain.", style=""))
    printed = str(debug_display.console.print.call_args)
    assert "[empty]" in printed


def test_render_overlay_no_debug_no_tag():
    d = Display()
    d.console = MagicMock()
    d._render_overlay(Overlay(text="Whisper.", style="whisper"))
    printed = str(d.console.print.call_args)
    assert "[whisper]" not in printed


# ------------------------------------------------------------------
# Debug mode: flag panel + obfuscated tag
# ------------------------------------------------------------------

def test_show_choices_debug_panel_renders_with_state(debug_display):
    debug_display._cfg["typewriter"]["enabled"] = False
    choices = [Choice(label="Go", next="a")]
    debug_display.show_choices(choices, [], [], debug_state={"trust": True})
    # Find the Panel in the call_args_list and render it to check its content
    panel = None
    for call in debug_display.console.print.call_args_list:
        if call[0] and isinstance(call[0][0], Panel):
            panel = call[0][0]
            break
    assert panel is not None, "No Panel found in print calls"
    cons = Console(file=StringIO(), width=80, legacy_windows=False)
    cons.print(panel)
    panel_str = cons.file.getvalue()
    assert "debug: flags" in panel_str
    assert "trust" in panel_str


def test_show_choices_debug_panel_hides_visited_in_author_mode(debug_display):
    debug_display._cfg["typewriter"]["enabled"] = False
    choices = [Choice(label="Go", next="a")]
    debug_display.show_choices(choices, [], [], debug_state={"visited_intro": True, "trust": False})
    # Find the Panel in the call_args_list and render it to check its content
    panel = None
    for call in debug_display.console.print.call_args_list:
        if call[0] and isinstance(call[0][0], Panel):
            panel = call[0][0]
            break
    assert panel is not None, "No Panel found in print calls"
    cons = Console(file=StringIO(), width=80, legacy_windows=False)
    cons.print(panel)
    panel_str = cons.file.getvalue()
    assert "trust" in panel_str
    assert "visited_intro" not in panel_str


def test_show_choices_debug_all_shows_visited(debug_all_display):
    debug_all_display._cfg["typewriter"]["enabled"] = False
    choices = [Choice(label="Go", next="a")]
    debug_all_display.show_choices(choices, [], [], debug_state={"visited_intro": True, "trust": True})
    # Find the Panel in the call_args_list and render it to check its content
    panel = None
    for call in debug_all_display.console.print.call_args_list:
        if call[0] and isinstance(call[0][0], Panel):
            panel = call[0][0]
            break
    assert panel is not None, "No Panel found in print calls"
    cons = Console(file=StringIO(), width=80, legacy_windows=False)
    cons.print(panel)
    panel_str = cons.file.getvalue()
    assert "visited_intro" in panel_str


def test_show_choices_debug_empty_state_shows_no_flags_set(debug_display):
    debug_display._cfg["typewriter"]["enabled"] = False
    choices = [Choice(label="Go", next="a")]
    debug_display.show_choices(choices, [], [], debug_state={})
    # Find the Panel in the call_args_list and render it to check its content
    panel = None
    for call in debug_display.console.print.call_args_list:
        if call[0] and isinstance(call[0][0], Panel):
            panel = call[0][0]
            break
    assert panel is not None, "No Panel found in print calls"
    cons = Console(file=StringIO(), width=80, legacy_windows=False)
    cons.print(panel)
    panel_str = cons.file.getvalue()
    assert "no flags set" in panel_str


def test_show_choices_obfuscated_debug_shows_redacted_tag(debug_display):
    debug_display._cfg["typewriter"]["enabled"] = False
    choices = [Choice(label="Secret passage", next="a", obfuscated=True)]
    debug_display.show_choices(choices, [], [], debug_state={})
    found = False
    for call in debug_display.console.print.call_args_list:
        if call[0]:
            arg = call[0][0]
            cons = Console(file=StringIO(), width=80, legacy_windows=False)
            cons.print(arg)
            if "[redacted]" in cons.file.getvalue():
                found = True
                break
    assert found, "[redacted] tag not visible in rendered output"


def test_show_choices_no_debug_no_panel():
    d = Display()
    d.console = MagicMock()
    d._cfg["typewriter"]["enabled"] = False
    choices = [Choice(label="Go", next="a")]
    d.show_choices(choices, [], [], debug_state={"trust": True})
    all_prints = " ".join(str(c) for c in d.console.print.call_args_list)
    assert "debug: flags" not in all_prints


# ------------------------------------------------------------------
# Prompt: protagonist name
# ------------------------------------------------------------------

def test_prompt_protagonist_name_returns_entered_name(display) -> None:
    display.console.input.return_value = "Aria"
    result = display.prompt_protagonist_name("What is your name?", prefill="Felix")
    assert result == "Aria"


def test_prompt_protagonist_name_q_returns_none(display) -> None:
    display.console.input.return_value = "q"
    result = display.prompt_protagonist_name("What is your name?", prefill="Felix")
    assert result is None


def test_prompt_protagonist_name_empty_returns_empty_string(display) -> None:
    display.console.input.return_value = ""
    result = display.prompt_protagonist_name("What is your name?", prefill="Felix")
    assert result == ""


# ------------------------------------------------------------------
# _assemble_text
# ------------------------------------------------------------------

def _make_display_obj(cfg_overrides: dict | None = None):
    """Return a Display instance with a mocked console and optional config overrides."""
    import copy
    from src.config import load_settings
    from src.display import Display
    d = Display.__new__(Display)
    d.console = MagicMock()
    base_cfg = load_settings(Path("nonexistent_settings.json"))
    if cfg_overrides:
        base_cfg.update(cfg_overrides)
    d._cfg = base_cfg
    d._debug = {"enabled": False, "all": False}
    return d


def test_assemble_text_plain_strip_pause() -> None:
    from src.display import _assemble_text
    from src.config import load_settings
    cfg = load_settings(Path("nonexistent_settings.json"))["corruption"]
    charset = ["█"]
    result = _assemble_text(["hello{pause}world"], charset, cfg)
    assert result == "helloworld"


def test_assemble_text_with_span_enabled() -> None:
    from src.display import _assemble_text
    from src.config import load_settings
    cfg = load_settings(Path("nonexistent_settings.json"))["corruption"]
    charset = ["█"]
    span = CorruptedSpan(text="aaa", intensity=1.0, mode="consistent", seed=0)
    result = _assemble_text(["before ", span, " after"], charset, cfg)
    assert result.startswith("before ")
    assert result.endswith(" after")
    assert "█" in result   # corrupted chars present


def test_assemble_text_with_span_disabled() -> None:
    from src.display import _assemble_text
    cfg = {"enabled": False, "intensity": 1.0}
    charset = ["█"]
    span = CorruptedSpan(text="hello", intensity=1.0, mode="consistent", seed=0)
    result = _assemble_text([span], charset, cfg)
    assert result == "hello"   # original text when disabled


def test_assemble_text_intensity_default_used_when_span_unset() -> None:
    from src.display import _assemble_text
    charset = ["█"]
    span = CorruptedSpan(text="hello", intensity=None, mode="consistent", seed=0)
    cfg = {"enabled": True, "intensity": 1.0}
    result = _assemble_text([span], charset, cfg)
    assert "█" in result


def test_assemble_text_story_intensity_ignores_global_default() -> None:
    """Story-defined intensity fully overrides the global default — no scaling."""
    from src.display import _assemble_text
    charset = ["█"]
    span = CorruptedSpan(text="hello", intensity=0.9, mode="consistent", seed=0)
    cfg = {"enabled": True, "intensity": 0.0}   # would have killed corruption under the old formula
    result = _assemble_text([span], charset, cfg)
    assert "█" in result


def test_assemble_text_intensity_multiplier_kills_corruption() -> None:
    from src.display import _assemble_text
    charset = ["█"]
    span = CorruptedSpan(text="hello", intensity=0.9, mode="consistent", seed=0)
    cfg = {"enabled": True, "intensity_multiplier": 0.0}
    result = _assemble_text([span], charset, cfg)
    assert result == "hello"


def test_assemble_text_mode_default_used_when_span_unset() -> None:
    from src.display import _assemble_text
    charset = ["█"]
    span = CorruptedSpan(text="abcdefghij", intensity=1.0, mode=None, seed=0)
    cfg = {"enabled": True, "mode": "random"}
    result = _assemble_text([span], charset, cfg)
    assert result == "█" * 10


def test_assemble_text_resolving_span_renders_clean() -> None:
    from src.display import _assemble_text
    charset = ["█"]
    span = CorruptedSpan(text="hello", intensity=1.0, mode="consistent", seed=0, resolve_style="decay")
    cfg = {"enabled": True, "intensity": 1.0}
    result = _assemble_text([span], charset, cfg)
    assert result == "hello"


# ------------------------------------------------------------------
# _typewrite: TextSegments
# ------------------------------------------------------------------

def test_typewrite_plain_segments_streams_chars(tmp_path) -> None:
    """_typewrite assembles and renders all chars from plain TextSegments."""
    from src.display import Display
    from unittest.mock import patch, MagicMock
    import io
    d = _make_display_obj({"typewriter": {"enabled": True, "delay_ms": 0,
                                           "pause_ms": 0, "punctuation_pauses": {}}})
    panels = []
    def make(t):
        panels.append(t)
        return MagicMock()
    with patch("src.display._key_pending", return_value=False), \
         patch("src.display.time") as mock_time, \
         patch("rich.live.Live.__enter__", return_value=MagicMock()), \
         patch("rich.live.Live.__exit__", return_value=False):
        d._typewrite(make, ["abc"], 0.0)
    # make was called with progressively longer strings ending in "abc"
    assert "abc" in panels


# ------------------------------------------------------------------
# _section_subscreen
# ------------------------------------------------------------------

def _make_draft():
    from src.config import load_settings
    return load_settings()


def test_section_subscreen_x_returns_back(display):
    display.console.input = MagicMock(side_effect=["x"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    result = display._section_subscreen(section, draft)
    assert result == "back"


def test_section_subscreen_m_returns_save_exit(display):
    display.console.input = MagicMock(side_effect=["m"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    with patch("src.display.save_settings"):
        result = display._section_subscreen(section, draft)
    assert result == "save_exit"


def test_section_subscreen_q_returns_discard_exit(display):
    display.console.input = MagicMock(side_effect=["q"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    result = display._section_subscreen(section, draft)
    assert result == "discard_exit"


def test_section_subscreen_r_resets_section(display):
    # R+Y resets values; S (save) confirms — draft keeps reset value.
    display.console.input = MagicMock(side_effect=["r", "y", "s", ""])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    draft["corruption"]["intensity"] = 0.1
    with patch("src.display.save_settings"):
        display._section_subscreen(section, draft)
    from src.config import _DEFAULTS
    assert draft["corruption"]["intensity"] == _DEFAULTS["corruption"]["intensity"]


def test_section_subscreen_x_restores_snapshot(display):
    # X discards all changes made inside the subscreen, including resets.
    display.console.input = MagicMock(side_effect=["r", "y", "x"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    draft["corruption"]["intensity"] = 0.1
    display._section_subscreen(section, draft)
    assert draft["corruption"]["intensity"] == 0.1


def test_section_subscreen_r_cancel_no_change(display):
    display.console.input = MagicMock(side_effect=["r", "n", "x"])
    section = next(s for s in SETTINGS_SECTIONS if s["id"] == "corruption")
    draft = _make_draft()
    draft["corruption"]["intensity"] = 0.1
    display._section_subscreen(section, draft)
    assert draft["corruption"]["intensity"] == 0.1


def test_typewrite_corrupted_span_uses_final_form(tmp_path) -> None:
    """After scramble, settle phase streams the final corrupted form."""
    from src.display import Display, _assemble_text
    from src.corruption import CorruptedSpan
    from unittest.mock import patch, MagicMock
    span = CorruptedSpan(text="hello", intensity=1.0, mode="consistent", seed=42)
    d = _make_display_obj({
        "typewriter": {"enabled": True, "delay_ms": 0, "pause_ms": 0, "punctuation_pauses": {}},
        "corruption": {"enabled": True, "intensity": 1.0, "mode": "consistent",
                       "charset": "blocks", "custom_chars": "█▓▒░",
                       "animate": False, "scramble_frames": 2, "scramble_delay_ms": 0},
    })
    panels = []
    def make(t):
        panels.append(t)
        return MagicMock()
    with patch("src.display._key_pending", return_value=False), \
         patch("src.display.time") as mock_time, \
         patch("rich.live.Live.__enter__", return_value=MagicMock()), \
         patch("rich.live.Live.__exit__", return_value=False):
        d._typewrite(make, [span], 0.0)
    final = panels[-1]
    assert final != "hello"    # corrupted
    assert len(final) == len("hello")  # same length


# ------------------------------------------------------------------
# _show_reset_selector
# ------------------------------------------------------------------

def test_show_reset_selector_cancel_returns_empty(display):
    display.console.input = MagicMock(side_effect=["x"])
    draft = _make_draft()
    result = display._show_reset_selector(draft)
    assert result == ""


def test_show_reset_selector_nothing_checked_is_noop(display):
    # Y with no checkboxes checked — returns empty, no changes
    display.console.input = MagicMock(side_effect=["y", "x"])
    draft = _make_draft()
    original_tw = copy.deepcopy(draft.get("typewriter", {}))
    result = display._show_reset_selector(draft)
    # first Y does nothing (nothing selected), then x exits
    assert result == ""
    assert draft.get("typewriter") == original_tw


def test_show_reset_selector_resets_selected_section(display):
    # Toggle typewriter (1), then confirm (y)
    display.console.input = MagicMock(side_effect=["1", "y"])
    draft = _make_draft()
    draft["typewriter"]["enabled"] = False
    draft["typewriter"]["delay_ms"] = 999
    result = display._show_reset_selector(draft)
    assert draft["typewriter"]["enabled"] is True
    assert draft["typewriter"]["delay_ms"] == 35
    assert "Typewriter" in result


def test_show_reset_selector_preserves_unchecked_section(display):
    # Toggle typewriter (1) only, confirm (y) — corruption unchanged
    display.console.input = MagicMock(side_effect=["1", "y"])
    draft = _make_draft()
    draft["corruption"]["intensity"] = 0.2
    display._show_reset_selector(draft)
    assert draft["corruption"]["intensity"] == 0.2  # untouched


def test_show_reset_selector_feedback_lists_section_names(display):
    display.console.input = MagicMock(side_effect=["1", "3", "y"])
    draft = _make_draft()
    result = display._show_reset_selector(draft)
    assert "Typewriter" in result
    assert "Corruption" in result
