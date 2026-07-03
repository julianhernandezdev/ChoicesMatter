from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from src.engine import Engine
from src.gallery import GalleryManager
from src.save import SaveManager, SaveState
from src.story import Choice, Node, Story


def _make_story(nodes: dict[str, Node], start: str = "start") -> Story:
    return Story(
        id="test_story",
        title="Test Story",
        version="1.0",
        author="Tester",
        start_node=start,
        nodes=nodes,
        source_path=Path("test_story.json"),
    )


def _make_display(choices: list = None, play_again: bool = False, continue_save: bool = False):
    display = MagicMock()
    display.prompt_choice.return_value = 1
    display.prompt_play_again.return_value = play_again
    display.prompt_continue_or_new.return_value = continue_save
    return display


@pytest.fixture
def two_node_story() -> Story:
    return _make_story({
        "start": Node(
            text="You begin.",
            choices=[Choice(label="Go", next="ending")],
        ),
        "ending": Node(
            text="You win.",
            choices=[],
            is_ending=True,
            ending_type="good",
        ),
    })


def test_advance_moves_to_next_node(saves_dir: Path, two_node_story: Story) -> None:
    display = _make_display(play_again=False)
    sm = SaveManager(saves_dir)
    engine = Engine(two_node_story, sm, display)
    engine.run()

    display.show_node.assert_any_call("Test Story", "You begin.", [], [], None)
    display.show_ending.assert_any_call("You win.", "good", overlays=[])


def test_autosave_called_on_advance(saves_dir: Path, two_node_story: Story) -> None:
    display = _make_display(play_again=False)
    sm = SaveManager(saves_dir)
    engine = Engine(two_node_story, sm, display)
    engine.run()

    display.show_save_indicator.assert_called_once()
    assert sm.has_save("test_story") is False  # deleted on ending


def test_ending_deletes_save(saves_dir: Path, two_node_story: Story) -> None:
    display = _make_display(play_again=False)
    sm = SaveManager(saves_dir)
    sm.write(SaveState(story_id="test_story", current_node="ending"))

    display.prompt_continue_or_new.return_value = False  # new game
    engine = Engine(two_node_story, sm, display)
    engine.run()

    assert sm.has_save("test_story") is False


def test_play_again_true_resets_to_start(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(text="Begin.", choices=[Choice(label="Go", next="end")]),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = MagicMock()
    display.prompt_choice.return_value = 1
    display.prompt_continue_or_new.return_value = False
    # First play-again: True (loop again), second: False (exit)
    display.prompt_play_again.side_effect = [True, False]

    sm = SaveManager(saves_dir)
    engine = Engine(story, sm, display)
    engine.run()

    # show_node called twice for "start" (once per play-through)
    start_calls = [c for c in display.show_node.call_args_list if c.args[1] == "Begin."]
    assert len(start_calls) == 2


def test_play_again_false_returns(saves_dir: Path, two_node_story: Story) -> None:
    display = _make_display(play_again=False)
    sm = SaveManager(saves_dir)
    engine = Engine(two_node_story, sm, display)
    engine.run()  # must return (not loop forever)
    display.prompt_play_again.assert_called_once()


# ------------------------------------------------------------------
# Flag system tests
# ------------------------------------------------------------------

@pytest.fixture
def flag_story() -> Story:
    """Story where the only path to the good ending requires a flag."""
    return _make_story({
        "start": Node(
            text="Begin.",
            choices=[
                Choice(label="Set flag", next="middle", sets={"key_found": True}),
                Choice(label="Skip flag", next="middle"),
            ],
        ),
        "middle": Node(
            text="You are here.",
            choices=[
                Choice(label="Normal end", next="bad_end"),
                Choice(label="Flag end", next="good_end", requires={"key_found": True}),
            ],
        ),
        "bad_end": Node(text="Bad.", choices=[], is_ending=True, ending_type="bad"),
        "good_end": Node(text="Good.", choices=[], is_ending=True, ending_type="good"),
    })


def test_unmet_requires_hides_choice(saves_dir: Path, flag_story: Story) -> None:
    display = MagicMock()
    display.prompt_continue_or_new.return_value = False
    display.prompt_play_again.return_value = False
    # Choose "Skip flag" (index 2) at start, then "Normal end" (index 1) at middle
    display.prompt_choice.side_effect = [2, 1]

    sm = SaveManager(saves_dir)
    engine = Engine(flag_story, sm, display)
    engine.run()

    # At "middle" node without the flag, only "Normal end" should be visible
    middle_show_call = [
        c for c in display.show_choices.call_args_list
        if any(ch.label == "Normal end" for ch in c.args[0])
    ]
    assert len(middle_show_call) == 1
    visible = middle_show_call[0].args[0]
    assert all(c.label != "Flag end" for c in visible)


def test_met_requires_shows_choice(saves_dir: Path, flag_story: Story) -> None:
    display = MagicMock()
    display.prompt_continue_or_new.return_value = False
    display.prompt_play_again.return_value = False
    # Choose "Set flag" (index 1) at start, then "Flag end" (index 2) at middle
    display.prompt_choice.side_effect = [1, 2]

    sm = SaveManager(saves_dir)
    engine = Engine(flag_story, sm, display)
    engine.run()

    middle_show_call = [
        c for c in display.show_choices.call_args_list
        if any(ch.label == "Normal end" for ch in c.args[0])
    ]
    visible = middle_show_call[0].args[0]
    assert any(c.label == "Flag end" for c in visible)


def test_sets_applies_flag_after_advance(saves_dir: Path, flag_story: Story) -> None:
    display = MagicMock()
    display.prompt_continue_or_new.return_value = False
    display.prompt_play_again.return_value = False
    display.prompt_choice.side_effect = [1, 2]  # Set flag → Flag end

    sm = SaveManager(saves_dir)
    engine = Engine(flag_story, sm, display)
    engine.run()

    # After advancing past "start" with sets={"key_found": True}, the save should include it
    # (save is deleted on ending, so check via engine's internal state through side effects)
    # The fact that "Flag end" was reachable proves the flag was applied
    display.show_ending.assert_called_once()
    args = display.show_ending.call_args.args
    assert args[0] == "Good."  # reached the good ending


def test_state_saved_and_restored(saves_dir: Path, flag_story: Story) -> None:
    sm = SaveManager(saves_dir)

    # First run: set the flag, stop at middle (simulate by writing save manually)
    sm.write(SaveState(
        story_id="test_story",
        current_node="middle",
        history=["start"],
        state={"key_found": True},
    ))

    display = MagicMock()
    display.prompt_continue_or_new.return_value = True  # continue saved game
    display.prompt_play_again.return_value = False
    display.prompt_choice.return_value = 2  # choose "Flag end" (index 2 when flag is set)

    engine = Engine(flag_story, sm, display)
    engine.run()

    # Flag end is only reachable if state was restored correctly
    display.show_ending.assert_called_once()
    assert display.show_ending.call_args.args[0] == "Good."


def test_overlay_with_unmet_requires_not_passed_to_show_choices(saves_dir: Path) -> None:
    from src.story import Overlay
    story = _make_story({
        "start": Node(
            text="Here.",
            choices=[Choice(label="Go", next="end")],
            overlays=[Overlay(text="Secret.", requires={"secret_flag": True}, position="after")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    Engine(story, SaveManager(saves_dir), display).run()

    call = display.show_choices.call_args_list[0]
    after = call.args[2] if len(call.args) > 2 else call.kwargs.get("after_overlays", [])
    assert not after  # Overlay objects filtered out by requires


def test_overlay_with_met_requires_passed_to_show_choices(saves_dir: Path) -> None:
    from src.story import Overlay
    story = _make_story({
        "start": Node(
            text="Here.",
            choices=[Choice(label="Set flag", next="mid", sets={"secret_flag": True})],
        ),
        "mid": Node(
            text="Middle.",
            choices=[Choice(label="End", next="end")],
            overlays=[Overlay(text="Secret revealed.", requires={"secret_flag": True}, position="after")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    Engine(story, SaveManager(saves_dir), display).run()

    mid_call = display.show_choices.call_args_list[1]
    after = mid_call.args[2] if len(mid_call.args) > 2 else mid_call.kwargs.get("after_overlays", [])
    assert len(after) == 1 and after[0].text == "Secret revealed."


def test_before_and_after_overlays_split_correctly(saves_dir: Path) -> None:
    from src.story import Overlay
    story = _make_story({
        "start": Node(
            text="Scene.",
            choices=[Choice(label="Go", next="end")],
            overlays=[
                Overlay(text="Before whisper.", position="before"),
                Overlay(text="After whisper.", position="after"),
            ],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    Engine(story, SaveManager(saves_dir), display).run()

    call = display.show_choices.call_args_list[0]
    before = call.args[1] if len(call.args) > 1 else call.kwargs.get("before_overlays", [])
    after  = call.args[2] if len(call.args) > 2 else call.kwargs.get("after_overlays", [])
    assert len(before) == 1 and before[0].text == "Before whisper."
    assert len(after)  == 1 and after[0].text  == "After whisper."


def test_insets_with_unmet_requires_not_passed_to_show_node(saves_dir: Path) -> None:
    from src.story import Inset
    story = _make_story({
        "start": Node(
            text="Scene.",
            choices=[Choice(label="Go", next="end")],
            insets=[Inset(text="Secret.", requires={"secret": True}, position="before")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    Engine(story, SaveManager(saves_dir), display).run()

    call = display.show_node.call_args_list[0]
    before_insets = call.args[2] if len(call.args) > 2 else call.kwargs.get("before_insets", [])
    assert not before_insets


def test_insets_with_met_requires_passed_to_show_node(saves_dir: Path) -> None:
    from src.story import Inset
    story = _make_story({
        "start": Node(
            text="Scene.",
            choices=[Choice(label="Reveal", next="mid", sets={"secret": True})],
        ),
        "mid": Node(
            text="Middle.",
            choices=[Choice(label="End", next="end")],
            insets=[Inset(text="The secret.", requires={"secret": True}, position="after")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    Engine(story, SaveManager(saves_dir), display).run()

    mid_call = display.show_node.call_args_list[1]
    after_insets = mid_call.args[3] if len(mid_call.args) > 3 else mid_call.kwargs.get("after_insets", [])
    assert len(after_insets) == 1 and after_insets[0].text == "The secret."


def test_before_and_after_insets_split_correctly(saves_dir: Path) -> None:
    from src.story import Inset
    story = _make_story({
        "start": Node(
            text="Scene.",
            choices=[Choice(label="Go", next="end")],
            insets=[
                Inset(text="Header.", position="before"),
                Inset(text="Footer.", position="after"),
            ],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    Engine(story, SaveManager(saves_dir), display).run()

    call = display.show_node.call_args_list[0]
    before = call.args[2] if len(call.args) > 2 else call.kwargs.get("before_insets", [])
    after  = call.args[3] if len(call.args) > 3 else call.kwargs.get("after_insets", [])
    assert len(before) == 1 and before[0].text == "Header."
    assert len(after)  == 1 and after[0].text  == "Footer."


# ------------------------------------------------------------------
# Gallery integration tests
# ------------------------------------------------------------------

def test_gallery_records_ending_node(saves_dir: Path, two_node_story: Story) -> None:
    display = _make_display(play_again=False)
    sm = SaveManager(saves_dir)
    gm = GalleryManager(saves_dir)
    Engine(two_node_story, sm, display, gm).run()

    assert gm.get_count("test_story") == 1
    assert "ending" in gm.get_found("test_story")


def test_gallery_accumulates_across_playthroughs(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(text="Begin.", choices=[
            Choice(label="Good path", next="good_end"),
            Choice(label="Bad path", next="bad_end"),
        ]),
        "good_end": Node(text="Good.", choices=[], is_ending=True, ending_type="good"),
        "bad_end": Node(text="Bad.", choices=[], is_ending=True, ending_type="bad"),
    })
    display = MagicMock()
    display.prompt_continue_or_new.return_value = False
    display.prompt_play_again.side_effect = [True, False]
    # First run: good path (choice 1), second run: bad path (choice 2)
    display.prompt_choice.side_effect = [1, 2]

    gm = GalleryManager(saves_dir)
    Engine(story, SaveManager(saves_dir), display, gm).run()

    assert gm.get_count("test_story") == 2
    assert gm.get_found("test_story") == {"good_end", "bad_end"}


def test_gallery_not_required(saves_dir: Path, two_node_story: Story) -> None:
    display = _make_display(play_again=False)
    sm = SaveManager(saves_dir)
    # No gallery_manager passed — should run without error
    Engine(two_node_story, sm, display).run()


def test_scene_tracked_in_show_node(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(text="Begin.", choices=[Choice(label="Go", next="end")], scene="Act I"),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    Engine(story, SaveManager(saves_dir), display).run()
    display.show_node.assert_any_call("Test Story", "Begin.", [], [], "Act I")


def test_quit_to_menu_returns_without_ending(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(text="Begin.", choices=[Choice(label="Go", next="end")]),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.return_value = None
    Engine(story, SaveManager(saves_dir), display).run()
    display.show_ending.assert_not_called()


# ------------------------------------------------------------------
# Node revisit flags
# ------------------------------------------------------------------

def test_visited_flag_set_on_advance(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(text="Begin.", choices=[Choice(label="Go", next="end")]),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    # visited_end is set when we navigate to "end"
    assert engine._state.get("visited_end") is True


def test_visited_flag_not_set_when_auto_off(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(text="Begin.", choices=[Choice(label="Go", next="end")]),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    story.auto_visited_flags = False
    display = _make_display(play_again=False)
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert "visited_end" not in engine._state


def test_visited_flag_gates_revisit_choice(saves_dir: Path) -> None:
    """A choice requiring visited_loop only appears after returning to the node."""
    story = _make_story({
        "start": Node(
            text="Corridor.",
            choices=[
                Choice(label="Go to room", next="room"),
                Choice(label="You've been here before", next="secret", requires={"visited_start": True}),
            ],
        ),
        "room": Node(text="A room.", choices=[Choice(label="Back", next="start")]),
        "secret": Node(text="Secret.", choices=[], is_ending=True, ending_type="good"),
    })
    display = MagicMock()
    display.prompt_continue_or_new.return_value = False
    display.prompt_play_again.return_value = False
    # First visit to start: only "Go to room" visible (index 1)
    # At room: back to start (index 1)
    # Second visit to start: "You've been here before" now visible (index 2)
    display.prompt_choice.side_effect = [1, 1, 2]

    Engine(story, SaveManager(saves_dir), display).run()

    # Should reach the secret ending
    display.show_ending.assert_called_once()
    assert display.show_ending.call_args.args[0] == "Secret."


def test_reset_clears_state(saves_dir: Path, flag_story: Story) -> None:
    display = MagicMock()
    display.prompt_continue_or_new.return_value = False
    # Play once setting flag, then play again without setting it
    display.prompt_play_again.side_effect = [True, False]
    # First run: Set flag → Flag end; Second run: Skip flag → Normal end
    display.prompt_choice.side_effect = [1, 2, 2, 1]

    sm = SaveManager(saves_dir)
    engine = Engine(flag_story, sm, display)
    engine.run()

    ending_calls = display.show_ending.call_args_list
    assert len(ending_calls) == 2
    assert ending_calls[0].args[0] == "Good."   # first run reached good end
    assert ending_calls[1].args[0] == "Bad."    # second run state was cleared


# ------------------------------------------------------------------
# Non-boolean state: _check_requires
# ------------------------------------------------------------------

def test_int_threshold_met(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[Choice(label="Build trust", next="mid", sets={"trust": 5})],
        ),
        "mid": Node(
            text="Middle.",
            choices=[Choice(label="Use power", next="end", requires={"trust": 3})],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="good"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert display.show_ending.call_args.args[0] == "Done."


def test_int_threshold_not_met_hides_choice(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[
                Choice(label="Use power", next="gated_end", requires={"trust": 3}),
                Choice(label="Fallback", next="fallback_end"),
            ],
        ),
        "gated_end": Node(text="Power.", choices=[], is_ending=True, ending_type="good"),
        "fallback_end": Node(text="Fallback.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    engine = Engine(story, SaveManager(saves_dir), display)
    engine._state["trust"] = 1  # 1 < 3
    engine.run()
    assert display.show_ending.call_args.args[0] == "Fallback."


def test_int_threshold_unset_key_treated_as_zero(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[
                Choice(label="Use power", next="gated_end", requires={"trust": 1}),
                Choice(label="Fallback", next="fallback_end"),
            ],
        ),
        "gated_end": Node(text="Power.", choices=[], is_ending=True, ending_type="good"),
        "fallback_end": Node(text="Fallback.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    engine = Engine(story, SaveManager(saves_dir), display)
    # trust not set → treated as 0 → 0 < 1 → choice hidden
    engine.run()
    assert display.show_ending.call_args.args[0] == "Fallback."


def test_string_exact_match_requires(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[Choice(label="Join red", next="mid", sets={"allegiance": "red"})],
        ),
        "mid": Node(
            text="Choose.",
            choices=[
                Choice(label="Red path", next="red_end", requires={"allegiance": "red"}),
                Choice(label="Default", next="default_end"),
            ],
        ),
        "red_end": Node(text="Red.", choices=[], is_ending=True, ending_type="good"),
        "default_end": Node(text="Default.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert display.show_ending.call_args.args[0] == "Red."


def test_list_membership_requires_met(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[Choice(label="Join blue", next="mid", sets={"allegiance": "blue"})],
        ),
        "mid": Node(
            text="Choose.",
            choices=[
                Choice(label="Allied", next="allied_end", requires={"allegiance": ["red", "blue"]}),
                Choice(label="Neutral", next="neutral_end"),
            ],
        ),
        "allied_end": Node(text="Allied.", choices=[], is_ending=True, ending_type="good"),
        "neutral_end": Node(text="Neutral.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert display.show_ending.call_args.args[0] == "Allied."


def test_list_membership_requires_not_met(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[
                Choice(label="Allied", next="allied_end", requires={"allegiance": ["red", "blue"]}),
                Choice(label="Neutral", next="neutral_end"),
            ],
        ),
        "allied_end": Node(text="Allied.", choices=[], is_ending=True, ending_type="good"),
        "neutral_end": Node(text="Neutral.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    engine = Engine(story, SaveManager(saves_dir), display)
    engine._state["allegiance"] = "green"
    engine.run()
    assert display.show_ending.call_args.args[0] == "Neutral."


# ------------------------------------------------------------------
# Non-boolean state: _apply_sets
# ------------------------------------------------------------------

def test_delta_increments_from_zero(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[Choice(label="Gain trust", next="end", sets={"trust": "+3"})],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert engine._state.get("trust") == 3


def test_delta_accumulates_over_multiple_advances(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[Choice(label="Go", next="mid", sets={"trust": "+2"})],
        ),
        "mid": Node(
            text="Middle.",
            choices=[Choice(label="Go", next="end", sets={"trust": "+3"})],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert engine._state.get("trust") == 5


def test_delta_decrements(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[Choice(label="Set trust", next="mid", sets={"trust": 5})],
        ),
        "mid": Node(
            text="Middle.",
            choices=[Choice(label="Lose trust", next="end", sets={"trust": "-1"})],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert engine._state.get("trust") == 4


def test_absolute_int_assignment(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[Choice(label="Go", next="end", sets={"level": 7})],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert engine._state.get("level") == 7


def test_string_assignment(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Begin.",
            choices=[Choice(label="Join red", next="end", sets={"allegiance": "red"})],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert engine._state.get("allegiance") == "red"


def test_counter_gates_choice_integration(saves_dir: Path) -> None:
    """Delta sets accumulate trust; threshold requires unlocks a choice at trust >= 4."""
    story = _make_story({
        "start": Node(
            text="Meet the contact.",
            choices=[Choice(label="Help them", next="helped", sets={"trust": "+2"})],
        ),
        "helped": Node(
            text="They nod.",
            choices=[Choice(label="Again", next="helped2", sets={"trust": "+2"})],
        ),
        "helped2": Node(
            text="Trust grows.",
            choices=[
                Choice(label="Ask the secret", next="secret_end", requires={"trust": 4}),
                Choice(label="Leave", next="neutral_end"),
            ],
        ),
        "secret_end": Node(text="They tell you.", choices=[], is_ending=True, ending_type="good"),
        "neutral_end": Node(text="You leave.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1, 1]
    engine = Engine(story, SaveManager(saves_dir), display)
    engine.run()
    assert engine._state.get("trust") == 4
    assert display.show_ending.call_args.args[0] == "They tell you."


# ------------------------------------------------------------------
# Conditional inline text: _resolve_inline unit tests
# ------------------------------------------------------------------

def test_resolve_inline_true_branch() -> None:
    assert Engine._resolve_inline("{flag?yes|no}", {"flag": True}) == "yes"


def test_resolve_inline_false_branch() -> None:
    assert Engine._resolve_inline("{flag?yes|no}", {"flag": False}) == "no"


def test_resolve_inline_missing_flag_returns_false_branch() -> None:
    assert Engine._resolve_inline("{flag?yes|no}", {}) == "no"


def test_resolve_inline_no_false_branch_when_true() -> None:
    assert Engine._resolve_inline("{flag?shown}", {"flag": True}) == "shown"


def test_resolve_inline_no_false_branch_collapses_when_false() -> None:
    assert Engine._resolve_inline("{flag?shown}", {"flag": False}) == ""


def test_resolve_inline_no_false_branch_collapses_when_missing() -> None:
    assert Engine._resolve_inline("{flag?shown}", {}) == ""


def test_resolve_inline_multiple_spans() -> None:
    text = "{a?hello|goodbye}, {b?world|earth}."
    assert Engine._resolve_inline(text, {"a": True, "b": False}) == "hello, earth."


def test_resolve_inline_unmatched_braces_left_intact() -> None:
    # {player_name} has no ? — must not be consumed (reserved for variable substitution)
    assert Engine._resolve_inline("{player_name} arrives.", {"player_name": "Mira"}) == "{player_name} arrives."


def test_resolve_inline_int_truthy() -> None:
    assert Engine._resolve_inline("{score?pass|fail}", {"score": 5}) == "pass"


def test_resolve_inline_int_zero_falsy() -> None:
    assert Engine._resolve_inline("{score?pass|fail}", {"score": 0}) == "fail"


def test_resolve_inline_no_patterns_unchanged() -> None:
    assert Engine._resolve_inline("Plain text.", {"flag": True}) == "Plain text."


def test_resolve_inline_string_truthy() -> None:
    assert Engine._resolve_inline("{msg?loaded|waiting}", {"msg": "ready"}) == "loaded"


def test_resolve_inline_empty_string_falsy() -> None:
    assert Engine._resolve_inline("{msg?loaded|waiting}", {"msg": ""}) == "waiting"


# ------------------------------------------------------------------
# Conditional inline text: integration tests through Engine.run()
# ------------------------------------------------------------------

def test_inline_resolved_in_node_text(saves_dir: Path) -> None:
    """node.text spans are resolved against state before show_node is called."""
    story = _make_story({
        "start": Node(
            text="You enter.",
            choices=[Choice(label="Go", next="hall", sets={"met_guard": True})],
        ),
        "hall": Node(
            text="{met_guard?A familiar face.|A stranger.}",
            choices=[Choice(label="Leave", next="end")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True),
    })
    display = _make_display(play_again=False)
    Engine(story, SaveManager(saves_dir), display).run()

    hall_call = display.show_node.call_args_list[1]
    assert hall_call.args[1] == "A familiar face."


def test_inline_resolved_in_inset_text(saves_dir: Path) -> None:
    """Visible inset text spans are resolved before show_node is called."""
    from src.story import Inset
    story = _make_story({
        "start": Node(
            text="You enter.",
            choices=[Choice(label="Go", next="hall", sets={"is_staff": True})],
        ),
        "hall": Node(
            text="The lobby.",
            choices=[Choice(label="Leave", next="end")],
            insets=[Inset(text="{is_staff?STAFF ACCESS GRANTED}", style="system", position="before")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True),
    })
    display = _make_display(play_again=False)
    Engine(story, SaveManager(saves_dir), display).run()

    hall_call = display.show_node.call_args_list[1]
    before_insets = hall_call.args[2]
    assert len(before_insets) == 1
    assert before_insets[0].text == "STAFF ACCESS GRANTED"


def test_inline_resolved_in_overlay_text(saves_dir: Path) -> None:
    """Visible overlay text spans are resolved before show_choices is called."""
    from src.story import Overlay
    story = _make_story({
        "start": Node(
            text="You enter.",
            choices=[Choice(label="Go", next="hall", sets={"alarm": True})],
        ),
        "hall": Node(
            text="The corridor.",
            choices=[Choice(label="Leave", next="end")],
            overlays=[Overlay(text="{alarm?ALARM SOUNDS.|Silence.}", position="after")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True),
    })
    display = _make_display(play_again=False)
    Engine(story, SaveManager(saves_dir), display).run()

    hall_choices_call = display.show_choices.call_args_list[1]
    after_overlays = hall_choices_call.args[2]
    assert len(after_overlays) == 1
    assert after_overlays[0].text == "ALARM SOUNDS."


# ------------------------------------------------------------------
# Variable text substitution: _substitute_vars unit tests
# ------------------------------------------------------------------

def test_substitute_vars_replaces_key_with_string_value() -> None:
    assert Engine._substitute_vars("Hello, {name}!", {"name": "Mira"}) == "Hello, Mira!"


def test_substitute_vars_missing_key_left_intact() -> None:
    assert Engine._substitute_vars("Hello, {name}!", {}) == "Hello, {name}!"


def test_substitute_vars_int_coerced_to_str() -> None:
    assert Engine._substitute_vars("Score: {score}", {"score": 42}) == "Score: 42"


def test_substitute_vars_bool_coerced_to_str() -> None:
    assert Engine._substitute_vars("Done: {done}", {"done": True}) == "Done: True"


def test_substitute_vars_replaces_multiple_keys() -> None:
    assert Engine._substitute_vars("{a} and {b}", {"a": "one", "b": "two"}) == "one and two"


def test_substitute_vars_does_not_touch_conditional_syntax() -> None:
    # {flag?yes|no} must not be partially consumed — the ? prevents the regex matching
    assert Engine._substitute_vars("{flag?yes|no}", {"flag": "yes"}) == "{flag?yes|no}"


def test_substitute_vars_leaves_pause_token_intact_when_not_in_state() -> None:
    assert Engine._substitute_vars("wait.{pause}go.", {}) == "wait.{pause}go."


def test_substitute_vars_no_patterns_unchanged() -> None:
    assert Engine._substitute_vars("Plain text.", {"name": "Mira"}) == "Plain text."


# ------------------------------------------------------------------
# Variable text substitution: integration tests through run()
# ------------------------------------------------------------------

def test_var_sub_applied_to_node_text(saves_dir: Path) -> None:
    story = _make_story({
        "start": Node(
            text="Name set.",
            choices=[Choice(label="Go", next="mid", sets={"player_name": "Mira"})],
        ),
        "mid": Node(
            text="Hello, {player_name}!",
            choices=[Choice(label="End", next="end")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    Engine(story, SaveManager(saves_dir), display).run()

    mid_call = display.show_node.call_args_list[1]
    assert mid_call.args[1] == "Hello, Mira!"


def test_var_sub_applied_to_inset_text(saves_dir: Path) -> None:
    from src.story import Inset
    story = _make_story({
        "start": Node(
            text="Go.",
            choices=[Choice(label="Go", next="mid", sets={"rank": "Captain"})],
        ),
        "mid": Node(
            text="A door.",
            choices=[Choice(label="End", next="end")],
            insets=[Inset(text="Rank: {rank}", position="before")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    Engine(story, SaveManager(saves_dir), display).run()

    mid_call = display.show_node.call_args_list[1]
    before_insets = mid_call.args[2]
    assert len(before_insets) == 1 and before_insets[0].text == "Rank: Captain"


def test_var_sub_applied_to_overlay_text(saves_dir: Path) -> None:
    from src.story import Overlay
    story = _make_story({
        "start": Node(
            text="Go.",
            choices=[Choice(label="Go", next="mid", sets={"mood": "tense"})],
        ),
        "mid": Node(
            text="A room.",
            choices=[Choice(label="End", next="end")],
            overlays=[Overlay(text="The air feels {mood}.", position="after")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    Engine(story, SaveManager(saves_dir), display).run()

    mid_call = display.show_choices.call_args_list[1]
    after = mid_call.args[2] if len(mid_call.args) > 2 else mid_call.kwargs.get("after_overlays", [])
    assert len(after) == 1 and after[0].text == "The air feels tense."


def test_var_sub_before_inline_resolution(saves_dir: Path) -> None:
    # {player_name} is substituted first, then {known?...} is resolved.
    # If known is true, the result should use the substituted name.
    story = _make_story({
        "start": Node(
            text="Setup.",
            choices=[Choice(label="Go", next="mid", sets={"player_name": "Mira", "known": True})],
        ),
        "mid": Node(
            text="{known?Hello, {player_name}!|Hello, stranger!}",
            choices=[Choice(label="End", next="end")],
        ),
        "end": Node(text="Done.", choices=[], is_ending=True, ending_type="neutral"),
    })
    display = _make_display(play_again=False)
    display.prompt_choice.side_effect = [1, 1]
    Engine(story, SaveManager(saves_dir), display).run()

    mid_call = display.show_node.call_args_list[1]
    assert mid_call.args[1] == "Hello, Mira!"


# ------------------------------------------------------------------
# initial_state parameter tests
# ------------------------------------------------------------------

def test_initial_state_seeds_state_on_new_game(saves_dir: Path, two_node_story: Story) -> None:
    display = _make_display(play_again=False)
    sm = SaveManager(saves_dir)
    engine = Engine(two_node_story, sm, display, initial_state={"player_name": "Felix"})
    engine._resolve_start()
    assert engine._state["player_name"] == "Felix"


def test_initial_state_not_overwritten_on_save_resume(saves_dir: Path, two_node_story: Story) -> None:
    sm = SaveManager(saves_dir)
    sm.write(SaveState(
        story_id="test_story",
        current_node="start",
        history=[],
        state={"player_name": "Saved Name"},
    ))
    display = _make_display(continue_save=True)
    engine = Engine(two_node_story, sm, display, initial_state={"player_name": "Felix"})
    engine._resolve_start()
    assert engine._state["player_name"] == "Saved Name"


def test_reset_reseeds_from_initial_state(saves_dir: Path, two_node_story: Story) -> None:
    display = _make_display()
    sm = SaveManager(saves_dir)
    engine = Engine(two_node_story, sm, display, initial_state={"player_name": "Felix"})
    engine._state["player_name"] = "Modified"
    engine._reset()
    assert engine._state["player_name"] == "Felix"


def test_no_initial_state_defaults_to_empty(saves_dir: Path, two_node_story: Story) -> None:
    display = _make_display(play_again=False)
    sm = SaveManager(saves_dir)
    engine = Engine(two_node_story, sm, display)
    engine._resolve_start()
    assert "player_name" not in engine._state
