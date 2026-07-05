from __future__ import annotations
import pytest
from src.corruption import (
    CorruptedSpan, TextSegments, CHARSETS,
    corrupt_string, resolve_corruption, _text_seed,
)

_BLOCKS = CHARSETS["blocks"]
_PUNCT = set(".,!?…—;:'\"()-\n ")


# --- _text_seed ---

def test_text_seed_is_deterministic() -> None:
    assert _text_seed("hello", 0) == _text_seed("hello", 0)

def test_text_seed_differs_by_text() -> None:
    assert _text_seed("hello", 0) != _text_seed("world", 0)

def test_text_seed_differs_by_index() -> None:
    assert _text_seed("hello", 0) != _text_seed("hello", 1)

def test_text_seed_returns_uint32() -> None:
    seed = _text_seed("abc", 5)
    assert 0 <= seed < 2**32


# --- corrupt_string ---

def test_zero_intensity_returns_original() -> None:
    assert corrupt_string("hello world", 0.0, "consistent", 0, _BLOCKS) == "hello world"

def test_full_intensity_replaces_all_alpha() -> None:
    result = corrupt_string("hello", 1.0, "consistent", 42, _BLOCKS)
    assert all(c in _BLOCKS for c in result)

def test_spaces_never_corrupted() -> None:
    result = corrupt_string("a b c d e", 1.0, "random", 0, _BLOCKS)
    assert result[1] == " " and result[3] == " " and result[5] == " "

def test_punctuation_never_corrupted() -> None:
    result = corrupt_string("a.b!c?", 1.0, "random", 0, _BLOCKS)
    assert result[1] == "." and result[3] == "!" and result[5] == "?"

def test_output_same_length_as_input() -> None:
    text = "The signal fades."
    assert len(corrupt_string(text, 0.5, "consistent", 1, _BLOCKS)) == len(text)

def test_consistent_mode_is_reproducible() -> None:
    text = "The door is open."
    r1 = corrupt_string(text, 0.5, "consistent", 99, _BLOCKS)
    r2 = corrupt_string(text, 0.5, "consistent", 99, _BLOCKS)
    assert r1 == r2

def test_random_mode_varies_across_calls() -> None:
    text = "abcdefghijklmnopqrstuvwxyz"
    results = {corrupt_string(text, 0.8, "random", 0, _BLOCKS) for _ in range(10)}
    assert len(results) > 1

def test_consistent_mode_different_seeds_differ() -> None:
    text = "The wall breathes."
    r1 = corrupt_string(text, 0.6, "consistent", 10, _BLOCKS)
    r2 = corrupt_string(text, 0.6, "consistent", 20, _BLOCKS)
    assert r1 != r2

def test_symbols_charset_used() -> None:
    charset = CHARSETS["symbols"]
    result = corrupt_string("hello", 1.0, "consistent", 1, charset)
    assert all(c in charset for c in result)

def test_empty_charset_returns_original() -> None:
    assert corrupt_string("hello", 1.0, "consistent", 0, []) == "hello"

def test_only_punctuation_returns_original() -> None:
    assert corrupt_string("...", 1.0, "consistent", 0, _BLOCKS) == "..."


# --- resolve_corruption ---

def test_no_spans_returns_single_string_segment() -> None:
    segs = resolve_corruption("plain text", None)
    assert segs == ["plain text"]

def test_span_produces_corrupted_span_object() -> None:
    segs = resolve_corruption("{corrupt}broken{/corrupt}", None)
    assert len(segs) == 1
    assert isinstance(segs[0], CorruptedSpan)
    assert segs[0].text == "broken"

def test_span_with_intensity_override() -> None:
    segs = resolve_corruption("{corrupt:0.8}text{/corrupt}", None)
    span = segs[0]
    assert isinstance(span, CorruptedSpan)
    assert span.intensity == pytest.approx(0.8)

def test_span_with_mode_override() -> None:
    segs = resolve_corruption("{corrupt:random}text{/corrupt}", None)
    span = segs[0]
    assert span.mode == "random"

def test_span_with_both_params() -> None:
    segs = resolve_corruption("{corrupt:0.7:random}text{/corrupt}", None)
    span = segs[0]
    assert span.intensity == pytest.approx(0.7)
    assert span.mode == "random"

def test_span_inherits_node_intensity() -> None:
    segs = resolve_corruption("{corrupt}text{/corrupt}", 0.4)
    assert segs[0].intensity == pytest.approx(0.4)

def test_span_inherits_node_dict() -> None:
    segs = resolve_corruption("{corrupt}text{/corrupt}", {"intensity": 0.3, "mode": "random"})
    assert segs[0].intensity == pytest.approx(0.3)
    assert segs[0].mode == "random"

def test_span_overrides_node() -> None:
    segs = resolve_corruption("{corrupt:0.9}text{/corrupt}", 0.3)
    assert segs[0].intensity == pytest.approx(0.9)

def test_mixed_plain_and_span() -> None:
    segs = resolve_corruption("before {corrupt}bad{/corrupt} after", None)
    assert len(segs) == 3
    assert segs[0] == "before "
    assert isinstance(segs[1], CorruptedSpan)
    assert segs[1].text == "bad"
    assert segs[2] == " after"

def test_seed_is_deterministic_from_text_and_index() -> None:
    segs1 = resolve_corruption("{corrupt}word{/corrupt}", None)
    segs2 = resolve_corruption("{corrupt}word{/corrupt}", None)
    assert segs1[0].seed == segs2[0].seed

def test_intensity_is_none_when_unspecified_anywhere() -> None:
    """Story-side resolution no longer bakes in a default — that's Display's job now."""
    segs = resolve_corruption("{corrupt}text{/corrupt}", None)
    assert segs[0].intensity is None

def test_mode_is_none_when_unspecified_anywhere() -> None:
    segs = resolve_corruption("{corrupt}text{/corrupt}", None)
    assert segs[0].mode is None


# --- resolve_style ---

def test_span_with_resolve_style_decay() -> None:
    segs = resolve_corruption("{corrupt:0.8:consistent:decay}text{/corrupt}", None)
    assert segs[0].resolve_style == "decay"

def test_span_with_resolve_style_cascade() -> None:
    segs = resolve_corruption("{corrupt:0.8:random:cascade}text{/corrupt}", None)
    assert segs[0].resolve_style == "cascade"

def test_resolve_style_omitted_is_none() -> None:
    segs = resolve_corruption("{corrupt}text{/corrupt}", None)
    assert segs[0].resolve_style is None

def test_resolve_style_alone_skips_intensity_and_mode() -> None:
    """A single trailing param still parses correctly when the earlier params are omitted."""
    segs = resolve_corruption("{corrupt:decay}text{/corrupt}", None)
    assert segs[0].resolve_style == "decay"
    assert segs[0].intensity is None
    assert segs[0].mode is None

def test_resolve_style_with_intensity_only_skips_mode() -> None:
    segs = resolve_corruption("{corrupt:0.6:decay}text{/corrupt}", None)
    assert segs[0].intensity == pytest.approx(0.6)
    assert segs[0].mode is None
    assert segs[0].resolve_style == "decay"

def test_resolve_style_inherits_from_node_dict() -> None:
    segs = resolve_corruption("{corrupt}text{/corrupt}", {"resolve_style": "cascade"})
    assert segs[0].resolve_style == "cascade"

def test_resolve_style_span_overrides_node() -> None:
    segs = resolve_corruption("{corrupt:decay}text{/corrupt}", {"resolve_style": "cascade"})
    assert segs[0].resolve_style == "decay"

def test_node_float_corruption_leaves_resolve_style_none() -> None:
    """A bare float node.corruption (no dict) never sets resolve_style."""
    segs = resolve_corruption("{corrupt}text{/corrupt}", 0.5)
    assert segs[0].resolve_style is None


# --- effective_mode / effective_intensity ---

from src.corruption import effective_mode, effective_intensity


def test_effective_mode_uses_span_value_when_set() -> None:
    assert effective_mode("random", {"mode": "consistent"}) == "random"

def test_effective_mode_falls_back_to_cfg_default_when_span_none() -> None:
    assert effective_mode(None, {"mode": "random"}) == "random"

def test_effective_mode_falls_back_to_consistent_when_cfg_missing_too() -> None:
    assert effective_mode(None, {}) == "consistent"

def test_effective_intensity_uses_span_value_when_set() -> None:
    """Story-defined intensity fully overrides the global default — no multiplication."""
    assert effective_intensity(0.9, {"intensity": 0.1}) == pytest.approx(0.9)

def test_effective_intensity_falls_back_to_cfg_default_when_span_none() -> None:
    assert effective_intensity(None, {"intensity": 0.6}) == pytest.approx(0.6)

def test_effective_intensity_falls_back_to_1_when_cfg_missing_too() -> None:
    assert effective_intensity(None, {}) == pytest.approx(1.0)

def test_effective_intensity_zero_is_not_treated_as_unset() -> None:
    """0.0 is a valid author intensity — must not be treated as falsy/unset."""
    assert effective_intensity(0.0, {"intensity": 0.9}) == pytest.approx(0.0)

def test_effective_intensity_multiplier_applies_to_story_value() -> None:
    assert effective_intensity(0.9, {"intensity_multiplier": 0.3}) == pytest.approx(0.27)

def test_effective_intensity_multiplier_applies_to_default_value() -> None:
    assert effective_intensity(None, {"intensity": 0.6, "intensity_multiplier": 0.3}) == pytest.approx(0.18)

def test_effective_intensity_multiplier_can_kill_corruption_entirely() -> None:
    assert effective_intensity(0.9, {"intensity_multiplier": 0.0}) == pytest.approx(0.0)

def test_effective_intensity_result_capped_at_1() -> None:
    assert effective_intensity(0.9, {"intensity_multiplier": 2.0}) == pytest.approx(1.0)


# --- cascade_reveal_order ---

def test_cascade_reveal_order_returns_corrupted_position_count() -> None:
    from src.corruption import cascade_reveal_order
    order = cascade_reveal_order("hello world", 1.0, "consistent", 0)
    # "hello world" has 10 corruptible chars (space excluded)
    assert len(order) == 10

def test_cascade_reveal_order_zero_intensity_is_empty() -> None:
    from src.corruption import cascade_reveal_order
    assert cascade_reveal_order("hello", 0.0, "consistent", 0) == []

def test_cascade_reveal_order_consistent_mode_is_reproducible() -> None:
    from src.corruption import cascade_reveal_order
    o1 = cascade_reveal_order("The door is open.", 0.5, "consistent", 99)
    o2 = cascade_reveal_order("The door is open.", 0.5, "consistent", 99)
    assert o1 == o2

def test_cascade_reveal_order_random_mode_varies_across_calls() -> None:
    from src.corruption import cascade_reveal_order
    text = "abcdefghijklmnopqrstuvwxyz"
    orders = {tuple(cascade_reveal_order(text, 0.8, "random", 0)) for _ in range(10)}
    assert len(orders) > 1

def test_cascade_reveal_order_indices_are_valid_and_unique() -> None:
    from src.corruption import cascade_reveal_order
    text = "The signal fades."
    order = cascade_reveal_order(text, 0.6, "consistent", 5)
    assert len(order) == len(set(order))
    assert all(0 <= i < len(text) for i in order)
    assert all(text[i] not in _PUNCT for i in order)


# --- decay monotonic-subset property (via corrupt_string) ---

def test_decay_corrupted_positions_shrink_monotonically() -> None:
    """For a fixed seed, the corrupted-position set at a lower intensity is always
    a subset of the set at a higher intensity — the property the decay resolve
    style depends on to 'heal' positions one at a time without re-corrupting."""
    text = "abcdefghijklmnopqrstuvwxyz" * 2
    seed = 7
    prev_positions: set[int] | None = None
    for steps in range(10, 0, -1):
        intensity = steps / 10
        result = corrupt_string(text, intensity, "consistent", seed, _BLOCKS)
        positions = {i for i, (a, b) in enumerate(zip(text, result)) if a != b}
        if prev_positions is not None:
            assert positions <= prev_positions, f"positions grew at intensity {intensity}"
        prev_positions = positions
