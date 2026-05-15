from __future__ import annotations

from display import Display
from gallery import GalleryManager
from save import SaveManager, SaveState
from story import Choice, Story


class Engine:
    def __init__(
        self,
        story: Story,
        save_manager: SaveManager,
        display: Display,
        gallery_manager: GalleryManager | None = None,
    ) -> None:
        self.story = story
        self.save_manager = save_manager
        self.display = display
        self.gallery_manager = gallery_manager
        self._current_node: str = story.start_node
        self._history: list[str] = []
        self._state: dict[str, bool] = {}
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

            visible = [c for c in node.choices if self._flag_check(c.requires)]

            visible_overlays = [o for o in node.overlays if self._flag_check(o.requires)]
            before = [o for o in visible_overlays if o.position == "before"]
            after  = [o for o in visible_overlays if o.position == "after"]

            visible_insets = [i for i in node.insets if self._flag_check(i.requires)]
            before_insets = [i for i in visible_insets if i.position == "before"]
            after_insets  = [i for i in visible_insets if i.position == "after"]

            if node.is_ending or not visible:
                self.display.show_ending(node.text, node.ending_type, overlays=before + after)
                if self.gallery_manager:
                    self.gallery_manager.record_ending(self.story.id, self._current_node)
                self.save_manager.delete(self.story.id)
                if self.display.prompt_play_again():
                    self._reset()
                    continue
                return

            self.display.show_node(self.story.title, node.text, before_insets, after_insets, self._current_scene)
            self.display.show_choices(visible, before, after, node.choice_number_color)
            idx = self.display.prompt_choice(visible)
            if idx is None:
                return
            choice = visible[idx - 1]
            self._advance(choice)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _flag_check(self, requires: dict[str, bool]) -> bool:
        return all(self._state.get(k) == v for k, v in requires.items())

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
        self._state = {}

    def _advance(self, choice: Choice) -> None:
        self._state.update(choice.sets)
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
        self._state = {}
        self._current_scene = None
        self.save_manager.delete(self.story.id)
