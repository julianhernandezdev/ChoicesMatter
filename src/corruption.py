from __future__ import annotations

import random as _random
import re
import dataclasses

_PUNCT = frozenset(".,!?…—;:'\"()-\n ")

CHARSETS: dict[str, list[str]] = {
    "blocks":    ["█", "▓", "▒", "░"],
    "symbols":   ["#", "@", "!", "?", "&", "*", "~"],
    "diacritics": ["̈", "̊", "̃", "̂", "̄"],
}

_LCG_A: int = 1664525
_LCG_C: int = 1013904223
_LCG_M: int = 2 ** 32

_CORRUPT_RE = re.compile(
    r"\{corrupt(?::([0-9]*\.?[0-9]+))?(?::(consistent|random))?(?::(decay|cascade))?\}(.*?)\{/corrupt\}",
    re.DOTALL,
)


@dataclasses.dataclass(frozen=True)
class CorruptedSpan:
    text: str
    intensity: float | None
    mode: str | None
    seed: int
    resolve_style: str | None = None


TextSegments = list[str | CorruptedSpan]


def _text_seed(text: str, index: int) -> int:
    combined = text + str(index)
    return sum(ord(c) * (i + 1) for i, c in enumerate(combined)) % (2 ** 32)


def _lcg_select(n_total: int, n_select: int, seed: int) -> list[int]:
    """Return n_select indices from range(n_total) via seeded Fisher-Yates (LCG)."""
    a, c, m = _LCG_A, _LCG_C, _LCG_M
    state = seed % m
    indices = list(range(n_total))
    for i in range(n_total - 1, n_total - n_select - 1, -1):
        state = (a * state + c) % m
        j = state % (i + 1)
        indices[i], indices[j] = indices[j], indices[i]
    return sorted(indices[n_total - n_select:])


def corrupt_string(
    text: str,
    intensity: float,
    mode: str,
    seed: int,
    charset: list[str],
) -> str:
    if not charset or intensity <= 0.0:
        return text
    corruptible = [i for i, c in enumerate(text) if c not in _PUNCT]
    count = int(len(corruptible) * min(intensity, 1.0))
    if count == 0:
        return text
    if mode == "consistent":
        positions = set(_lcg_select(len(corruptible), count, seed))
        a, c, m = _LCG_A, _LCG_C, _LCG_M
        state = seed % m
        chars = list(text)
        for pos_idx, char_idx in enumerate(corruptible):
            if pos_idx in positions:
                state = (a * state + c) % m
                chars[char_idx] = charset[state % len(charset)]
    else:
        positions = set(_random.sample(range(len(corruptible)), count))
        chars = list(text)
        for pos_idx, char_idx in enumerate(corruptible):
            if pos_idx in positions:
                chars[char_idx] = _random.choice(charset)
    return "".join(chars)


def resolve_corruption(
    text: str,
    node_corruption: float | dict | None,
) -> TextSegments:
    node_intensity: float | None = None
    node_mode: str | None = None
    node_resolve_style: str | None = None
    if isinstance(node_corruption, (int, float)):
        node_intensity = float(node_corruption)
    elif isinstance(node_corruption, dict):
        if "intensity" in node_corruption:
            node_intensity = float(node_corruption["intensity"])
        if "mode" in node_corruption:
            node_mode = node_corruption["mode"]
        if "resolve_style" in node_corruption:
            node_resolve_style = node_corruption["resolve_style"]

    segments: TextSegments = []
    last_end = 0
    span_index = 0

    for match in _CORRUPT_RE.finditer(text):
        if match.start() > last_end:
            segments.append(text[last_end:match.start()])
        raw_intensity, raw_mode, raw_resolve_style, span_text = (
            match.group(1), match.group(2), match.group(3), match.group(4)
        )
        intensity = float(raw_intensity) if raw_intensity is not None else node_intensity
        mode = raw_mode if raw_mode is not None else node_mode
        resolve_style = raw_resolve_style if raw_resolve_style is not None else node_resolve_style
        seed = _text_seed(span_text, span_index)
        segments.append(CorruptedSpan(
            text=span_text, intensity=intensity, mode=mode, seed=seed, resolve_style=resolve_style,
        ))
        last_end = match.end()
        span_index += 1

    if last_end < len(text):
        segments.append(text[last_end:])

    if not segments:
        return [text]
    return segments


def effective_mode(span_mode: str | None, cfg_corruption: dict) -> str:
    return span_mode or cfg_corruption.get("mode", "consistent")


def effective_intensity(span_intensity: float | None, cfg_corruption: dict) -> float:
    resolved = span_intensity if span_intensity is not None else cfg_corruption.get("intensity", 1.0)
    multiplier = cfg_corruption.get("intensity_multiplier", 1.0)
    return min(resolved * multiplier, 1.0)


def cascade_reveal_order(positions: list[int], mode: str, seed: int) -> list[int]:
    """Given a list of already-corrupted character indices (e.g. the diff between
    a corrupted string and its clean original), return them shuffled into the
    order they should be revealed (set back to clean) during a cascade resolve.

    Takes the exact positions rather than recomputing them from (text, intensity)
    so the reveal order always matches whatever corrupt_string actually corrupted,
    including for mode="random" where independent recomputation would draw a
    different, unrelated random sample."""
    order = list(positions)
    if mode == "consistent":
        a, c, m = _LCG_A, _LCG_C, _LCG_M
        state = seed % m
        for i in range(len(order) - 1, 0, -1):
            state = (a * state + c) % m
            j = state % (i + 1)
            order[i], order[j] = order[j], order[i]
    else:
        _random.shuffle(order)
    return order
