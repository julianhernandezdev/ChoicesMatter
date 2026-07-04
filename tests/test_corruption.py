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

def test_default_intensity_is_1_when_no_node_corruption() -> None:
    segs = resolve_corruption("{corrupt}text{/corrupt}", None)
    assert segs[0].intensity == pytest.approx(1.0)

def test_default_mode_is_consistent() -> None:
    segs = resolve_corruption("{corrupt}text{/corrupt}", None)
    assert segs[0].mode == "consistent"
