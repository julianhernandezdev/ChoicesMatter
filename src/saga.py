"""Pure saga (chapter graph) logic. No I/O and no rich: everything is derived
from ChapterInfo records plus a SagaProgress snapshot the host builds."""
from __future__ import annotations

import re
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .story import Story

_INT_RE = re.compile(r"^-?\d+$")
_UNREACHED_DEPTH = 10**6


@dataclass(frozen=True)
class ChainEdge:
    node_id: str
    target: str
    exports: tuple[str, ...]
    transition: bool


@dataclass(frozen=True)
class ChapterInfo:
    story_id: str
    path: Path
    title: str
    saga_id: str | None
    saga_title: str | None
    chapter_label: str | None
    edges: tuple[ChainEdge, ...]
    saga_end_nodes: frozenset[str]
    ending_count: int
    author: str = ""
    version: str = ""

    @property
    def next_targets(self) -> frozenset[str]:
        return frozenset(edge.target for edge in self.edges)


@dataclass(frozen=True)
class SagaProgress:
    saves: frozenset[str] = frozenset()
    seeds: frozenset[str] = frozenset()
    found: dict[str, frozenset[str]] = field(default_factory=dict)
    activity: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SagaStats:
    chapters_reached: int
    chapters_total: int
    endings_found: int
    endings_total: int


@dataclass(frozen=True)
class Saga:
    saga_id: str
    title: str
    entry: str | None
    chapters: tuple[str, ...]
    problems: tuple[str, ...]
    has_dangling: bool


class SagaGraph:
    def __init__(
        self,
        chapters: dict[str, ChapterInfo],
        sagas: dict[str, Saga],
        depths: dict[str, int],
        children: dict[str, tuple[str, ...]],
    ) -> None:
        self._chapters = chapters
        self.sagas = sagas
        self._depths = depths
        self._children = children
        self._saga_by_chapter = {
            cid: saga.saga_id for saga in sagas.values() for cid in saga.chapters
        }

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    @classmethod
    def build(cls, chapters: Iterable[ChapterInfo]) -> SagaGraph:
        by_id: dict[str, ChapterInfo] = {}
        grouped: dict[str, list[ChapterInfo]] = {}
        duplicates: dict[str, set[str]] = {}
        for info in chapters:
            if info.saga_id is None:
                continue
            if info.story_id in by_id:
                duplicates.setdefault(info.saga_id, set()).add(info.story_id)
                duplicates.setdefault(by_id[info.story_id].saga_id, set()).add(info.story_id)
                continue
            by_id[info.story_id] = info
            grouped.setdefault(info.saga_id, []).append(info)

        sagas: dict[str, Saga] = {}
        depths: dict[str, int] = {}
        children: dict[str, tuple[str, ...]] = {}
        for saga_id, members in grouped.items():
            ids = [m.story_id for m in members]
            id_set = set(ids)
            problems: list[str] = []
            has_dangling = False
            internal: dict[str, list[str]] = {cid: [] for cid in ids}
            for member in members:
                for edge in member.edges:
                    if edge.target in id_set:
                        if edge.target not in internal[member.story_id]:
                            internal[member.story_id].append(edge.target)
                    elif edge.target in by_id:
                        problems.append(
                            f"chapter '{member.story_id}' node '{edge.node_id}' targets "
                            f"'{edge.target}', which belongs to a different saga"
                        )
                    else:
                        has_dangling = True
            for dup in sorted(duplicates.get(saga_id, ())):
                problems.append(f"duplicate story id '{dup}'")

            incoming = {target for targets in internal.values() for target in targets}
            entries = [cid for cid in ids if cid not in incoming]
            cycle = cls._find_cycle(ids, internal)
            if cycle:
                problems.append("cycle: " + " -> ".join(cycle))
            if len(entries) > 1:
                problems.append(
                    "multiple entry chapters (nothing chains into them): " + ", ".join(entries)
                )
            entry = entries[0] if len(entries) == 1 else None

            if entry is not None and len(ids) >= 2:
                if not by_id[entry].saga_title:
                    problems.append(f"entry chapter '{entry}' must declare saga_title")
                for member in members:
                    if member.story_id != entry and member.saga_title:
                        problems.append(
                            f"chapter '{member.story_id}' declares saga_title "
                            "but is not the entry chapter"
                        )

            depth: dict[str, int] = {}
            if entry is not None:
                depth[entry] = 0
                queue = deque([entry])
                while queue:
                    current = queue.popleft()
                    for nxt in internal[current]:
                        if nxt not in depth:
                            depth[nxt] = depth[current] + 1
                            queue.append(nxt)
            ordered = sorted(
                ids, key=lambda cid: (depth.get(cid, _UNREACHED_DEPTH), by_id[cid].title, cid)
            )

            if entry is not None and by_id[entry].saga_title:
                title = by_id[entry].saga_title
            elif len(ids) == 1:
                title = by_id[ids[0]].title
            else:
                title = next((m.saga_title for m in members if m.saga_title), saga_id)

            sagas[saga_id] = Saga(
                saga_id=saga_id,
                title=title,
                entry=entry,
                chapters=tuple(ordered),
                problems=tuple(problems),
                has_dangling=has_dangling,
            )
            depths.update(depth)
            children.update({cid: tuple(targets) for cid, targets in internal.items()})
        return cls(by_id, sagas, depths, children)

    @staticmethod
    def _find_cycle(ids: list[str], internal: dict[str, list[str]]) -> list[str] | None:
        white, grey, black = 0, 1, 2
        color = {cid: white for cid in ids}
        stack: list[str] = []

        def visit(node: str) -> list[str] | None:
            color[node] = grey
            stack.append(node)
            for nxt in internal[node]:
                if color[nxt] == grey:
                    return stack[stack.index(nxt):] + [nxt]
                if color[nxt] == white:
                    found = visit(nxt)
                    if found:
                        return found
            stack.pop()
            color[node] = black
            return None

        for cid in ids:
            if color[cid] == white:
                found = visit(cid)
                if found:
                    return found
        return None

    # ------------------------------------------------------------------
    # Structure
    # ------------------------------------------------------------------

    @property
    def known_ids(self) -> frozenset[str]:
        return frozenset(self._chapters)

    def chapter(self, story_id: str) -> ChapterInfo | None:
        return self._chapters.get(story_id)

    def chapters_of(self, saga: Saga) -> list[ChapterInfo]:
        return [self._chapters[cid] for cid in saga.chapters]

    def saga_of(self, story_id: str) -> Saga | None:
        saga_id = self._saga_by_chapter.get(story_id)
        return self.sagas.get(saga_id) if saga_id else None

    def depth(self, story_id: str) -> int | None:
        return self._depths.get(story_id)

    def descendants(self, story_id: str) -> frozenset[str]:
        seen: set[str] = set()
        queue = deque(self._children.get(story_id, ()))
        while queue:
            current = queue.popleft()
            if current in seen or current == story_id:
                continue
            seen.add(current)
            queue.extend(self._children.get(current, ()))
        return frozenset(seen)

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def reached(self, saga: Saga, progress: SagaProgress) -> tuple[str, ...]:
        return tuple(
            cid
            for cid in saga.chapters
            if cid == saga.entry or cid in progress.saves or cid in progress.seeds
        )

    def active(self, saga: Saga, progress: SagaProgress) -> tuple[str, ...]:
        return tuple(
            cid for cid in saga.chapters if cid in progress.saves or cid in progress.seeds
        )

    def is_complete(self, saga: Saga, progress: SagaProgress) -> bool:
        return any(
            progress.found.get(cid, frozenset()) & self._chapters[cid].saga_end_nodes
            for cid in saga.chapters
        )

    def stats(self, saga: Saga, progress: SagaProgress) -> SagaStats:
        return SagaStats(
            chapters_reached=len(self.reached(saga, progress)),
            chapters_total=len(saga.chapters),
            endings_found=sum(len(progress.found.get(cid, ())) for cid in saga.chapters),
            endings_total=sum(self._chapters[cid].ending_count for cid in saga.chapters),
        )

    def default_chapter(self, saga: Saga, progress: SagaProgress) -> str:
        active = self.active(saga, progress)
        if active:
            return max(
                active,
                key=lambda cid: (progress.activity.get(cid, ""), -saga.chapters.index(cid)),
            )
        return saga.entry or saga.chapters[0]


def chapter_info_from_story(story: Story) -> ChapterInfo:
    edges = tuple(
        ChainEdge(
            node_id=node_id,
            target=node.next_story,
            exports=tuple(node.exports),
            transition=node.chapter_transition,
        )
        for node_id, node in story.nodes.items()
        if node.next_story
    )
    return ChapterInfo(
        story_id=story.id,
        path=story.source_path,
        title=story.title,
        saga_id=story.saga_id,
        saga_title=story.saga_title,
        chapter_label=story.chapter_label,
        edges=edges,
        saga_end_nodes=frozenset(nid for nid, node in story.nodes.items() if node.saga_end),
        ending_count=story.ending_count,
        author=story.author,
        version=story.version,
    )


def chapter_label_text(info: ChapterInfo) -> str:
    return f"{info.chapter_label} — {info.title}" if info.chapter_label else info.title


def parse_seed_arg(text: str) -> dict[str, bool | int | str]:
    """Parse 'key=value,key=value'. true/false -> bool, integers -> int, else str."""
    result: dict[str, bool | int | str] = {}
    for pair in text.split(","):
        pair = pair.strip()
        if not pair:
            raise ValueError("empty pair in seed list")
        if "=" not in pair:
            raise ValueError(f"'{pair}' is not key=value")
        key, value = pair.split("=", 1)
        key, value = key.strip(), value.strip()
        if not key:
            raise ValueError(f"'{pair}' has an empty key")
        lowered = value.lower()
        if lowered == "true":
            result[key] = True
        elif lowered == "false":
            result[key] = False
        elif _INT_RE.match(value):
            result[key] = int(value)
        else:
            result[key] = value
    return result
