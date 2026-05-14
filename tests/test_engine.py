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
