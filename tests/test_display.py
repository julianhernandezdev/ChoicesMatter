from unittest.mock import MagicMock, patch

import pytest
from rich.panel import Panel

from display import Display
from story import Choice, Inset, Overlay


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
    with patch("display.save_settings") as mock_save:
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
