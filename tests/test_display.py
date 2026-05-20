from unittest.mock import MagicMock, patch
from io import StringIO

import pytest
from rich.console import Console
from rich.panel import Panel

from src.display import Display, _strip_pause_tokens
from src.story import Choice, Inset, Overlay


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
    display.show_node("Title", "Hello{pause}World", [], [])
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
    display.show_ending("The end{pause}.", "good", [])
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
        d._typewrite(lambda t: t, "A{pause}B", 0.0)

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
        d._typewrite(lambda t: t, "Hello", 0.0)

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
        d._typewrite(lambda t: t, "A{pause}B", 0.0)

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


def test_show_settings_screen_toggle_enabled_then_discard(display):
    display.console.input.side_effect = ["1", "x"]
    display.show_settings_screen()  # must not raise


def test_show_settings_screen_edit_pause_then_discard(display):
    # "3" enters pause edit for '.', "" keeps current, "x" discards from main menu
    display.console.input.side_effect = ["3", "", "x"]
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


def test_settings_edit_pause_sets_value(display):
    pauses = {".": 550}
    display.console.input.return_value = "300"
    display._settings_edit_pause(pauses, ".", 550)
    assert pauses["."] == 300


def test_settings_edit_pause_keep_on_empty(display):
    pauses = {".": 550}
    display.console.input.return_value = ""
    display._settings_edit_pause(pauses, ".", 550)
    assert pauses["."] == 550


def test_settings_edit_pause_invalid_then_valid(display):
    pauses = {".": 550}
    display.console.input.side_effect = ["abc", "200"]
    display._settings_edit_pause(pauses, ".", 550)
    assert pauses["."] == 200


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
