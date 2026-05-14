from pathlib import Path
from unittest.mock import MagicMock, call

import pytest

from engine import Engine
from save import SaveManager, SaveState
from story import Choice, Node, Story


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

    display.show_node.assert_any_call("Test Story", "You begin.")
    display.show_node.assert_any_call("Test Story", "You win.")


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
