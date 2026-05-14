from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class StoryValidationError(Exception):
    pass


@dataclass
class Choice:
    label: str
    next: str
    requires: dict[str, bool] = field(default_factory=dict)
    sets: dict[str, bool] = field(default_factory=dict)


@dataclass
class Overlay:
    text: str
    requires: dict[str, bool] = field(default_factory=dict)
    position: str = "after"  # "before" | "after"


@dataclass
class Node:
    text: str
    choices: list[Choice]
    is_ending: bool = False
    ending_type: str = "neutral"
    overlays: list[Overlay] = field(default_factory=list)


@dataclass
class Story:
    id: str
    title: str
    version: str
    author: str
    start_node: str
    nodes: dict[str, Node]
    source_path: Path

    def get_node(self, node_id: str) -> Node:
        return self.nodes[node_id]


class StoryLoader:
    @staticmethod
    def discover(stories_dir: Path) -> list[Path]:
        if not stories_dir.exists():
            return []
        return sorted(stories_dir.glob("*.json"))

    @staticmethod
    def load(path: Path) -> Story:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise StoryValidationError(f"Invalid JSON in '{path.name}': {e}") from e

        meta = raw.get("meta")
        if not isinstance(meta, dict):
            raise StoryValidationError(f"'{path.name}': missing 'meta' block")

        for field_name in ("id", "title", "version", "author", "start_node"):
            if field_name not in meta:
                raise StoryValidationError(
                    f"'{path.name}': meta missing required field '{field_name}'"
                )

        raw_nodes = raw.get("nodes")
        if not isinstance(raw_nodes, dict):
            raise StoryValidationError(f"'{path.name}': missing 'nodes' block")

        start = meta["start_node"]
        if start not in raw_nodes:
            raise StoryValidationError(
                f"'{path.name}': start_node '{start}' not found in nodes"
            )

        nodes: dict[str, Node] = {}
        for node_id, node_data in raw_nodes.items():
            if "text" not in node_data:
                raise StoryValidationError(
                    f"'{path.name}': node '{node_id}' missing 'text'"
                )
            if "choices" not in node_data:
                raise StoryValidationError(
                    f"'{path.name}': node '{node_id}' missing 'choices'"
                )

            choices = [
                Choice(
                    label=c["label"],
                    next=c["next"],
                    requires=c.get("requires", {}),
                    sets=c.get("sets", {}),
                )
                for c in node_data["choices"]
            ]
            overlays = [
                Overlay(
                    text=o["text"],
                    requires=o.get("requires", {}),
                    position=o.get("position", "after"),
                )
                for o in node_data.get("overlays", [])
            ]
            nodes[node_id] = Node(
                text=node_data["text"],
                choices=choices,
                is_ending=node_data.get("is_ending", False),
                ending_type=node_data.get("ending_type", "neutral"),
                overlays=overlays,
            )

        for node_id, node in nodes.items():
            for choice in node.choices:
                if choice.next not in nodes:
                    raise StoryValidationError(
                        f"'{path.name}': node '{node_id}' choice '{choice.label}' "
                        f"references nonexistent node '{choice.next}'"
                    )

        return Story(
            id=meta["id"],
            title=meta["title"],
            version=meta["version"],
            author=meta["author"],
            start_node=meta["start_node"],
            nodes=nodes,
            source_path=path,
        )
