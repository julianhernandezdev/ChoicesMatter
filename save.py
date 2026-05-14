from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class SaveState:
    story_id: str
    current_node: str
    history: list[str] = field(default_factory=list)
    state: dict[str, bool] = field(default_factory=dict)
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "story_id": self.story_id,
            "current_node": self.current_node,
            "history": self.history,
            "state": self.state,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SaveState:
        return cls(
            story_id=data["story_id"],
            current_node=data["current_node"],
            history=data.get("history", []),
            state=data.get("state", {}),
            timestamp=data.get("timestamp", ""),
        )


class SaveManager:
    def __init__(self, saves_dir: Path) -> None:
        self.saves_dir = saves_dir
        saves_dir.mkdir(parents=True, exist_ok=True)

    def save_path(self, story_id: str) -> Path:
        return self.saves_dir / f"{story_id}.save.json"

    def has_save(self, story_id: str) -> bool:
        return self.save_path(story_id).exists()

    def load(self, story_id: str) -> SaveState | None:
        path = self.save_path(story_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return SaveState.from_dict(data)

    def write(self, state: SaveState) -> None:
        state.timestamp = datetime.now(timezone.utc).isoformat()
        self.save_path(state.story_id).write_text(
            json.dumps(state.to_dict(), indent=2), encoding="utf-8"
        )

    def delete(self, story_id: str) -> None:
        path = self.save_path(story_id)
        if path.exists():
            path.unlink()
