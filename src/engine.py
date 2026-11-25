from __future__ import annotations

import dataclasses
import re
from collections.abc import Callable, Collection

from .corruption import CorruptedSpan, TextSegments, resolve_corruption
from .display import Display
from .gallery import GalleryManager
from .save import HandoffRecord, SaveManager, SaveState
from .story import Choice, Story

_DELTA_RE = re.compile(r"^[+-]\d+$")
_INLINE_RE = re.compile(r"\{(\w+)\?([^|{}]*?)(?:\|([^{}]*?))?\}")
_SUBST_RE = re.compile(r"\{(\w+)\}")
_CLOSING_LINES = {"saga_end": "End of saga", "dangling": "To be continued"}


@dataclasses.dataclass(frozen=True)
class ChainResult:
    """Returned by Engine.run() when the player continues into the next chapter."""

    next_story: str
    from_story: str


class Engine:
    def __init__(
        self,
        story: Story,
        save_manager: SaveManager,
        display: Display,
        gallery_manager: GalleryManager | None = None,
        initial_state: dict[str, bool | int | str] | None = None,
        fresh_run_state: Callable[[], dict[str, bool | int | str] | None] | None = None,
        known_chapter_ids: Collection[str] = (),
    ) -> None:
        self.story = story
        self.save_manager = save_manager
        self.display = display
        self.gallery_manager = gallery_manager
        self._initial_state: dict[str, bool | int | str] = dict(initial_state) if initial_state else {}
        self._fresh_run_state = fresh_run_state
        self._known_chapter_ids = frozenset(known_chapter_ids)
        self._current_node: str = story.start_node
        self._history: list[str] = []
        self._state: dict[str, bool | int | str] = {}
        self._current_scene: str | None = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> ChainResult | None:
        if not self._resolve_start():
            return None
        self.display.clear_screen()

        while True:
            node = self.story.get_node(self._current_node)
            if node.scene:
                self._current_scene = node.scene

            visible = [c for c in node.choices if self._check_requires(c.requires)]

            visible_overlays = [o for o in node.overlays if self._check_requires(o.requires)]
            before = [o for o in visible_overlays if o.position == "before"]
            after  = [o for o in visible_overlays if o.position == "after"]

            visible_insets = [i for i in node.insets if self._check_requires(i.requires)]
            before_insets = [i for i in visible_insets if i.position == "before"]
            after_insets  = [i for i in visible_insets if i.position == "after"]

            def _pt(text: str) -> TextSegments:
                resolved = self._resolve_inline(
                    self._substitute_vars(text, self._state), self._state
                )
                return resolve_corruption(resolved, node.corruption)

            node_text     = _pt(node.text)
            before_insets = [dataclasses.replace(i, text=_pt(i.text)) for i in before_insets]
            after_insets  = [dataclasses.replace(i, text=_pt(i.text)) for i in after_insets]
            before        = [dataclasses.replace(o, text=_pt(o.text)) for o in before]
            after         = [dataclasses.replace(o, text=_pt(o.text)) for o in after]

            if node.is_ending or not visible:
                kind = self._ending_kind(node)
                overlays = before + after
                if kind == "transition":
                    # Bookkeeping first so quitting during the panel loses nothing.
                    self._finish_ending()
                    self._write_seed(node)
                    self.display.show_chapter_transition(
                        self.story.title, node_text, before_insets, after_insets,
                        self._current_scene, overlays,
                    )
                    return ChainResult(next_story=node.next_story, from_story=self.story.id)
                closing = _CLOSING_LINES.get(kind)
                if closing:
                    self.display.show_ending(node_text, node.ending_type, overlays=overlays, closing=closing)
                else:
                    self.display.show_ending(node_text, node.ending_type, overlays=overlays)
                self._finish_ending()
                if kind == "chain":
                    self._write_seed(node)
                    answer = self.display.prompt_chapter_transition()
                    if answer == "continue":
                        return ChainResult(next_story=node.next_story, from_story=self.story.id)
                    if answer == "again":
                        # Undo the seed just written; by the invariant nothing else downstream exists.
                        self.save_manager.delete_handoff(node.next_story)
                        if not self._reset():
                            return None
                        continue
                    return None
                if self.display.prompt_play_again():
                    if not self._reset():
                        return None
                    continue
                return None

            self.display.show_node(self.story.title, node_text, before_insets, after_insets, self._current_scene)
            self.display.show_choices(visible, before, after, node.choice_number_color, debug_state=self._state)
            idx = self.display.prompt_choice(visible)
            if idx is None:
                return None
            choice = visible[idx - 1]
            self._advance(choice)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _ending_kind(self, node) -> str:
        if node.saga_end:
            return "saga_end"
        if node.next_story:
            if node.next_story not in self._known_chapter_ids:
                return "dangling"
            return "transition" if node.chapter_transition else "chain"
        return "plain"

    def _finish_ending(self) -> None:
        if self.gallery_manager:
            self.gallery_manager.record_ending(self.story.id, self._current_node)
        self.save_manager.delete(self.story.id)

    def _write_seed(self, node) -> None:
        seed = {name: self._state[name] for name in node.exports if name in self._state}
        if "player_name" in self._state:
            seed["player_name"] = self._state["player_name"]
        self.save_manager.write_handoff(
            HandoffRecord(story_id=node.next_story, from_story=self.story.id, state=seed)
        )

    def _check_requires(self, requires: dict) -> bool:
        for key, condition in requires.items():
            current = self._state.get(key)
            if isinstance(condition, bool):
                # A flag nobody ever set counts as false. We do not hold it
                # accountable for sins it never had the chance to commit.
                #
                # Before this, "requires: {has_key: false}" only matched if some earlier
                # choice had gone out of its way to set has_key to false. A flag the
                # player simply never touched matched neither true nor false, so the
                # choice stayed hidden forever and nobody was told. Numbers already
                # treat "never set" as 0 and inline text already treats it as false.
                # This makes true/false play by the same rule.
                if current is None:
                    current = False
                if current != condition:
                    return False
            elif isinstance(condition, int):
                val = current if isinstance(current, int) and not isinstance(current, bool) else 0
                if val < condition:
                    return False
            elif isinstance(condition, str):
                if current != condition:
                    return False
            elif isinstance(condition, list):
                if current not in condition:
                    return False
        return True

    def _apply_sets(self, sets: dict) -> None:
        for key, value in sets.items():
            if isinstance(value, str) and _DELTA_RE.fullmatch(value):
                delta = int(value)
                current = self._state.get(key, 0)
                self._state[key] = (current if isinstance(current, int) and not isinstance(current, bool) else 0) + delta
            else:
                self._state[key] = value

    def _resolve_start(self) -> bool:
        """Set up the run's starting state. Returns False if the host aborted a fresh start."""
        if self.save_manager.has_save(self.story.id):
            saved = self.save_manager.load(self.story.id)
            if saved and saved.current_node in self.story.nodes:
                if self.display.prompt_continue_or_new():
                    self._current_node = saved.current_node
                    self._history = saved.history
                    self._state = dict(saved.state)
                    return True
        return self._begin_fresh()

    def _begin_fresh(self) -> bool:
        """Start a fresh run. Asks the host for seed state if it supplied a provider.

        Returns False (touching nothing) when the provider returns None, meaning
        the player backed out.
        """
        if self._fresh_run_state is not None:
            seed = self._fresh_run_state()
            if seed is None:
                return False
            self._initial_state = dict(seed)
        self._current_node = self.story.start_node
        self._history = []
        self._state = dict(self._initial_state)
        self._current_scene = None
        return True

    def _advance(self, choice: Choice) -> None:
        self._apply_sets(choice.sets)
        self._history.append(self._current_node)
        self._current_node = choice.next
        if self.story.auto_visited_flags:
            self._state[f"visited_{self._current_node}"] = True
        state = SaveState(
            story_id=self.story.id,
            current_node=self._current_node,
            history=list(self._history),
            state=dict(self._state),
        )
        self.save_manager.write(state)
        self.display.show_save_indicator()

    def _reset(self) -> bool:
        self.save_manager.delete(self.story.id)
        return self._begin_fresh()

    @staticmethod
    def _substitute_vars(text: str, state: dict) -> str:
        def _replace(m: re.Match) -> str:
            val = state.get(m.group(1))
            return str(val) if val is not None else m.group(0)
        return _SUBST_RE.sub(_replace, text)

    @staticmethod
    def _resolve_inline(text: str, state: dict) -> str:
        def _replace(m: re.Match) -> str:
            true_b = m.group(2)
            false_b = m.group(3) or ""
            return true_b if state.get(m.group(1)) else false_b
        return _INLINE_RE.sub(_replace, text)
