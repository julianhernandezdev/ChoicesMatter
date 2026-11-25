"""The Last Customer Support Representative: the freed toaster shows up for the evacuation.

The evacuation scene has a sentence that only appears if you freed BREADLEY-7 earlier.
It tested a flag called toaster_free, and nothing in the story ever set it, so the
toaster's finest hour was cut from every playthrough.
"""
from pathlib import Path
from unittest.mock import MagicMock

from src.engine import Engine
from src.save import SaveManager
from src.story import StoryLoader

STORY = Path(__file__).resolve().parents[1] / "stories" / "the_last_customer_support_representative.json"


def _evacuation_text(saves_dir: Path, toaster_stop: str) -> str:
    """Play to the manual evacuation, stopping at the given toaster node on the way. Returns that scene's text."""
    route = iter([
        "login_professional", "ticket_clone", "clone_escalate", "ticket_toaster", toaster_stop,
        "ticket_moon_miners", "posters_disable", "ticket_therapy_bot", "therapy_support", "midshift",
        "corporate_status", "corp_leak", "evacuation_start", "evac_manual", "ending_walkout",
    ])
    display = MagicMock()
    display.prompt_play_again.return_value = False
    display.prompt_continue_or_new.return_value = False

    def pick(visible):
        wanted = next(route)
        on_offer = [c.next for c in visible]
        assert wanted in on_offer, f"no choice leads to {wanted!r}. On offer: {on_offer}"
        return on_offer.index(wanted) + 1

    display.prompt_choice.side_effect = pick
    engine = Engine(StoryLoader.load(STORY), SaveManager(saves_dir), display, initial_state={"player_name": "Felix"})
    seen: dict[str, str] = {}
    display.show_node.side_effect = lambda title, text, *rest: seen.__setitem__(
        engine._current_node, "".join(part for part in text if isinstance(part, str))
    )
    engine.run()
    return seen["evac_manual"]


def test_freeing_the_toaster_is_remembered_at_the_evacuation(saves_dir: Path) -> None:
    text = _evacuation_text(saves_dir, toaster_stop="toaster_free")
    assert "BREADLEY-7, now liberated, leads a squad of appliances" in text


def test_unionising_the_toaster_still_gets_its_own_line(saves_dir: Path) -> None:
    """The neighbouring branch already worked. This pins it so the fix cannot have disturbed it."""
    text = _evacuation_text(saves_dir, toaster_stop="toaster_union")
    assert "now liberated" not in text
