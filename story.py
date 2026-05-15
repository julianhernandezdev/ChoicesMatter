from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


class StoryValidationError(Exception):
    pass


_SAFE_STORY_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
_ENDING_TYPES = {"good", "bad", "neutral"}
_OVERLAY_POSITIONS = {"before", "after"}


@dataclass
class Choice:
    label: str
    next: str
    requires: dict[str, bool] = field(default_factory=dict)
    sets: dict[str, bool] = field(default_factory=dict)
    color: str | None = None


@dataclass
class Overlay:
    text: str
    requires: dict[str, bool] = field(default_factory=dict)
    position: str = "after"  # "before" | "after"
    style: str = ""           # named style key; "" = default overlay config


@dataclass
class Inset:
    text: str
    position: str = "before"  # "before" | "after" relative to node text
    style: str = ""            # named style key; "" = dim italic default
    requires: dict[str, bool] = field(default_factory=dict)


@dataclass
class Node:
    text: str
    choices: list[Choice]
    is_ending: bool = False
    ending_type: str = "neutral"
    overlays: list[Overlay] = field(default_factory=list)
    insets: list[Inset] = field(default_factory=list)
    scene: str | None = None
    choice_number_color: str | None = None


@dataclass
class Story:
    id: str
    title: str
    version: str
    author: str
    start_node: str
    nodes: dict[str, Node]
    source_path: Path
    node_count: int = 0
    ending_count: int = 0
    est_time: str = ""
    warnings: list[str] = field(default_factory=list)

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

        if not isinstance(raw, dict):
            raise StoryValidationError(f"'{path.name}': root must be a JSON object")

        meta = raw.get("meta")
        if not isinstance(meta, dict):
            raise StoryValidationError(f"'{path.name}': missing 'meta' block")

        story_id = StoryLoader._required_string(meta, "id", path.name, "meta")
        if not _SAFE_STORY_ID.fullmatch(story_id):
            raise StoryValidationError(
                f"'{path.name}': meta field 'id' may only contain letters, numbers, "
                "dots, underscores, and hyphens"
            )

        title = StoryLoader._required_string(meta, "title", path.name, "meta")
        version = StoryLoader._required_string(meta, "version", path.name, "meta")
        author = StoryLoader._required_string(meta, "author", path.name, "meta")
        start = StoryLoader._required_string(meta, "start_node", path.name, "meta")

        raw_nodes = raw.get("nodes")
        if not isinstance(raw_nodes, dict):
            raise StoryValidationError(f"'{path.name}': missing 'nodes' block")

        if start not in raw_nodes:
            raise StoryValidationError(
                f"'{path.name}': start_node '{start}' not found in nodes"
            )

        nodes: dict[str, Node] = {}
        for node_id, node_data in raw_nodes.items():
            if not isinstance(node_data, dict):
                raise StoryValidationError(
                    f"'{path.name}': node '{node_id}' must be an object"
                )

            text = StoryLoader._required_string(node_data, "text", path.name, f"node '{node_id}'")
            choices = StoryLoader._parse_choices(node_data, node_id, path.name)
            overlays = StoryLoader._parse_overlays(node_data, node_id, path.name)
            insets = StoryLoader._parse_insets(node_data, node_id, path.name)

            is_ending = node_data.get("is_ending", False)
            if not isinstance(is_ending, bool):
                raise StoryValidationError(
                    f"'{path.name}': node '{node_id}' field 'is_ending' must be true or false"
                )

            ending_type = node_data.get("ending_type", "neutral")
            if ending_type not in _ENDING_TYPES:
                raise StoryValidationError(
                    f"'{path.name}': node '{node_id}' field 'ending_type' must be one of: bad, good, neutral"
                )

            scene_raw = node_data.get("scene")
            scene: str | None = None
            if scene_raw is not None:
                if not isinstance(scene_raw, str) or not scene_raw.strip():
                    raise StoryValidationError(
                        f"'{path.name}': node '{node_id}' field 'scene' must be a non-empty string if provided"
                    )
                scene = scene_raw.strip()

            cnc_raw = node_data.get("choice_number_color")
            choice_number_color: str | None = None
            if cnc_raw is not None:
                if not isinstance(cnc_raw, str) or not cnc_raw.strip():
                    raise StoryValidationError(
                        f"'{path.name}': node '{node_id}' field 'choice_number_color' must be a non-empty string if provided"
                    )
                choice_number_color = cnc_raw.strip()

            nodes[node_id] = Node(
                text=text,
                choices=choices,
                is_ending=is_ending,
                ending_type=ending_type,
                overlays=overlays,
                insets=insets,
                scene=scene,
                choice_number_color=choice_number_color,
            )

        for node_id, node in nodes.items():
            for choice in node.choices:
                if choice.next not in nodes:
                    raise StoryValidationError(
                        f"'{path.name}': node '{node_id}' choice '{choice.label}' "
                        f"references nonexistent node '{choice.next}'"
                    )

        node_count = len(nodes)
        ending_count = sum(1 for n in nodes.values() if n.is_ending or not n.choices)

        est_time_raw = meta.get("est_time")
        if est_time_raw is not None:
            if not isinstance(est_time_raw, str) or not est_time_raw.strip():
                raise StoryValidationError(
                    f"'{path.name}': meta field 'est_time' must be a non-empty string if provided"
                )
            est_time = est_time_raw.strip()
        else:
            est_time = StoryLoader._compute_est_time(nodes)

        raw_warnings = meta.get("warnings")
        warnings: list[str] = []
        if raw_warnings is not None:
            if not isinstance(raw_warnings, list) or not all(
                isinstance(w, str) and w.strip() for w in raw_warnings
            ):
                raise StoryValidationError(
                    f"'{path.name}': meta field 'warnings' must be a list of non-empty strings"
                )
            warnings = [w.strip() for w in raw_warnings]

        return Story(
            id=story_id,
            title=title,
            version=version,
            author=author,
            start_node=start,
            nodes=nodes,
            source_path=path,
            node_count=node_count,
            ending_count=ending_count,
            est_time=est_time,
            warnings=warnings,
        )

    @staticmethod
    def _compute_est_time(nodes: dict[str, "Node"]) -> str:
        total_words = sum(len(n.text.split()) for n in nodes.values())
        raw_minutes = total_words / 130 * 1.3
        minutes = max(5, round(raw_minutes / 5) * 5)
        return f"~{minutes} min"

    @staticmethod
    def _required_string(data: dict, field_name: str, file_name: str, location: str) -> str:
        if field_name not in data:
            raise StoryValidationError(
                f"'{file_name}': {location} missing required field '{field_name}'"
            )
        value = data[field_name]
        if not isinstance(value, str) or not value.strip():
            raise StoryValidationError(
                f"'{file_name}': {location} field '{field_name}' must be a non-empty string"
            )
        return value

    @staticmethod
    def _parse_choices(node_data: dict, node_id: str, file_name: str) -> list[Choice]:
        if "choices" not in node_data:
            raise StoryValidationError(
                f"'{file_name}': node '{node_id}' missing 'choices'"
            )
        raw_choices = node_data["choices"]
        if not isinstance(raw_choices, list):
            raise StoryValidationError(
                f"'{file_name}': node '{node_id}' field 'choices' must be a list"
            )

        choices = []
        for idx, choice_data in enumerate(raw_choices, start=1):
            location = f"node '{node_id}' choice #{idx}"
            if not isinstance(choice_data, dict):
                raise StoryValidationError(f"'{file_name}': {location} must be an object")
            color_raw = choice_data.get("color")
            choice_color: str | None = None
            if color_raw is not None:
                if not isinstance(color_raw, str) or not color_raw.strip():
                    raise StoryValidationError(
                        f"'{file_name}': {location} field 'color' must be a non-empty string if provided"
                    )
                choice_color = color_raw.strip()
            choices.append(
                Choice(
                    label=StoryLoader._required_string(choice_data, "label", file_name, location),
                    next=StoryLoader._required_string(choice_data, "next", file_name, location),
                    requires=StoryLoader._parse_flags(choice_data.get("requires", {}), file_name, f"{location} field 'requires'"),
                    sets=StoryLoader._parse_flags(choice_data.get("sets", {}), file_name, f"{location} field 'sets'"),
                    color=choice_color,
                )
            )
        return choices

    @staticmethod
    def _parse_overlays(node_data: dict, node_id: str, file_name: str) -> list[Overlay]:
        raw_overlays = node_data.get("overlays", [])
        if not isinstance(raw_overlays, list):
            raise StoryValidationError(
                f"'{file_name}': node '{node_id}' field 'overlays' must be a list"
            )

        overlays = []
        for idx, overlay_data in enumerate(raw_overlays, start=1):
            location = f"node '{node_id}' overlay #{idx}"
            if not isinstance(overlay_data, dict):
                raise StoryValidationError(f"'{file_name}': {location} must be an object")
            position = overlay_data.get("position", "after")
            if position not in _OVERLAY_POSITIONS:
                raise StoryValidationError(
                    f"'{file_name}': {location} field 'position' must be 'before' or 'after'"
                )
            overlays.append(
                Overlay(
                    text=StoryLoader._required_string(overlay_data, "text", file_name, location),
                    requires=StoryLoader._parse_flags(overlay_data.get("requires", {}), file_name, f"{location} field 'requires'"),
                    position=position,
                    style=overlay_data.get("style", ""),
                )
            )
        return overlays

    @staticmethod
    def _parse_insets(node_data: dict, node_id: str, file_name: str) -> list[Inset]:
        raw_insets = node_data.get("insets", [])
        if not isinstance(raw_insets, list):
            raise StoryValidationError(
                f"'{file_name}': node '{node_id}' field 'insets' must be a list"
            )

        insets = []
        for idx, inset_data in enumerate(raw_insets, start=1):
            location = f"node '{node_id}' inset #{idx}"
            if not isinstance(inset_data, dict):
                raise StoryValidationError(f"'{file_name}': {location} must be an object")
            position = inset_data.get("position", "before")
            if position not in _OVERLAY_POSITIONS:
                raise StoryValidationError(
                    f"'{file_name}': {location} field 'position' must be 'before' or 'after'"
                )
            insets.append(
                Inset(
                    text=StoryLoader._required_string(inset_data, "text", file_name, location),
                    position=position,
                    style=inset_data.get("style", ""),
                    requires=StoryLoader._parse_flags(inset_data.get("requires", {}), file_name, f"{location} field 'requires'"),
                )
            )
        return insets

    @staticmethod
    def _parse_flags(value: object, file_name: str, location: str) -> dict[str, bool]:
        if not isinstance(value, dict):
            raise StoryValidationError(f"'{file_name}': {location} must be an object")
        for flag, flag_value in value.items():
            if not isinstance(flag, str) or not isinstance(flag_value, bool):
                raise StoryValidationError(
                    f"'{file_name}': {location} must map string flags to true/false values"
                )
        return dict(value)
