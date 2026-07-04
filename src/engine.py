from __future__ import annotations

import dataclasses
import re

from .corruption import CorruptedSpan, TextSegments, resolve_corruption
from .display import Display
from .gallery import GalleryManager
from .save import SaveManager, SaveState
from .story import Choice, Story

_DELTA_RE = re.compile(r"^[+-]\d+$")
_INLINE_RE = re.compile(r"\{(\w+)\?([^|{}]*?)(?:\|([^{}]*?))?\}")
_SUBST_RE = re.compile(r"\{(\w+)\}")


class Engine:
    def __init__(
        self,
        story: Story,
        save_manager: SaveManager,
        display: Display,
        gallery_manager: GalleryManager | None = None,
        initial_state: dict[str, bool | int | str] | None = None,
    ) -> None:
        self.story = story
        self.save_manager = save_manager
        self.display = display
        self.gallery_manager = gallery_manager
        self._initial_state: dict[str, bool | int | str] = dict(initial_state) if initial_state else {}
        self._current_node: str = story.start_node
        self._history: list[str] = []
        self._state: dict[str, bool | int | str] = {}
        self._current_scene: str | None = None

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._resolve_start()
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
                self.display.show_ending(node_text, node.ending_type, overlays=before + after)
                if self.gallery_manager:
                    self.gallery_manager.record_ending(self.story.id, self._current_node)
                self.save_manager.delete(self.story.id)
                if self.display.prompt_play_again():
                    self._reset()
                    continue
                return

            self.display.show_node(self.story.title, node_text, before_insets, after_insets, self._current_scene)
            self.display.show_choices(visible, before, after, node.choice_number_color, debug_state=self._state)
            idx = self.display.prompt_choice(visible)
            if idx is None:
                return
            choice = visible[idx - 1]
            self._advance(choice)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _check_requires(self, requires: dict) -> bool:
        for key, condition in requires.items():
            current = self._state.get(key)
            if isinstance(condition, bool):
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

    def _resolve_start(self) -> None:
        if self.save_manager.has_save(self.story.id):
            saved = self.save_manager.load(self.story.id)
            if saved and saved.current_node in self.story.nodes:
                if self.display.prompt_continue_or_new():
                    self._current_node = saved.current_node
                    self._history = saved.history
                    self._state = dict(saved.state)
                    return
        self._current_node = self.story.start_node
        self._history = []
        self._state = dict(self._initial_state)

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

    def _reset(self) -> None:
        self._current_node = self.story.start_node
        self._history = []
        self._state = dict(self._initial_state)
        self._current_scene = None
        self.save_manager.delete(self.story.id)

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
