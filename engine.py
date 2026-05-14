from __future__ import annotations

from display import Display
from save import SaveManager, SaveState
from story import Story


class Engine:
    def __init__(self, story: Story, save_manager: SaveManager, display: Display) -> None:
        self.story = story
        self.save_manager = save_manager
        self.display = display
        self._current_node: str = story.start_node
        self._history: list[str] = []

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self) -> None:
        self._resolve_start()

        while True:
            node = self.story.get_node(self._current_node)
            self.display.show_node(self.story.title, node.text)

            if node.is_ending or not node.choices:
                self.display.show_ending(node.text, node.ending_type)
                self.save_manager.delete(self.story.id)
                if self.display.prompt_play_again():
                    self._reset()
                    continue
                return

            self.display.show_choices(node.choices)
            idx = self.display.prompt_choice(node.choices)
            choice = node.choices[idx - 1]
            self._advance(choice)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _resolve_start(self) -> None:
        if self.save_manager.has_save(self.story.id):
            state = self.save_manager.load(self.story.id)
            if state and state.current_node in self.story.nodes:
                if self.display.prompt_continue_or_new():
                    self._current_node = state.current_node
                    self._history = state.history
                    return
        self._current_node = self.story.start_node
        self._history = []

    def _advance(self, choice) -> None:
        self._history.append(self._current_node)
        self._current_node = choice.next
        state = SaveState(
            story_id=self.story.id,
            current_node=self._current_node,
            history=list(self._history),
        )
        self.save_manager.write(state)
        self.display.show_save_indicator()

    def _reset(self) -> None:
        self._current_node = self.story.start_node
        self._history = []
        self.save_manager.delete(self.story.id)
