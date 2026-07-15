# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for caption-core timing utilities."""
import pytest

from backend.caption_core.models import CaptionWord
from backend.caption_core.timing import (
    normalize_words_to_clip,
    seconds_to_ms,
    shift_words,
    to_clip_local_time,
    to_source_time,
    trim_words_to_clip,
)


def make_words() -> list[CaptionWord]:
    return [
        CaptionWord(text="one", start_ms=0, end_ms=500),
        CaptionWord(text="two", start_ms=500, end_ms=1000),
        CaptionWord(text="three", start_ms=1000, end_ms=1500),
        CaptionWord(text="four", start_ms=1500, end_ms=2000),
    ]


class TestSecondsToMs:
    def test_rounding(self):
        assert seconds_to_ms(0.0) == 0
        assert seconds_to_ms(1.5) == 1500
        assert seconds_to_ms(0.1234) == 123
        assert seconds_to_ms(0.1236) == 124


class TestClipLocalTime:
    def test_source_to_local(self):
        assert to_clip_local_time(5000, 2000) == 3000

    def test_local_to_source(self):
        assert to_source_time(3000, 2000) == 5000


class TestShiftWords:
    def test_shift_does_not_mutate(self):
        words = make_words()
        shifted = shift_words(words, 1000)
        assert words[0].start_ms == 0
        assert words[0].end_ms == 500
        assert shifted[0].start_ms == 1000
        assert shifted[0].end_ms == 1500

    def test_negative_shift(self):
        words = make_words()
        shifted = shift_words(words, -500)
        assert shifted[0].start_ms == -500


class TestTrimWordsToClip:
    def test_clip_beginning_at_zero(self):
        words = make_words()
        clip = trim_words_to_clip(words, 0, 1000)
        assert len(clip) == 2
        assert [w.text for w in clip] == ["one", "two"]

    def test_clip_beginning_after_zero(self):
        words = make_words()
        clip = trim_words_to_clip(words, 500, 1500)
        assert [w.text for w in clip] == ["two", "three"]

    def test_word_exactly_on_start_boundary(self):
        words = make_words()
        # Word "two" starts exactly at 500.
        clip = trim_words_to_clip(words, 500, 2000)
        assert "two" in [w.text for w in clip]

    def test_word_exactly_on_end_boundary(self):
        words = make_words()
        # Word "two" ends exactly at 1000.
        clip = trim_words_to_clip(words, 0, 1000)
        assert "two" in [w.text for w in clip]

    def test_word_partially_overlapping_start(self):
        words = [CaptionWord(text="overlap", start_ms=800, end_ms=1200)]
        clip = trim_words_to_clip(words, 1000, 2000)
        assert len(clip) == 1
        assert clip[0].text == "overlap"

    def test_word_partially_overlapping_end(self):
        words = [CaptionWord(text="overlap", start_ms=1800, end_ms=2200)]
        clip = trim_words_to_clip(words, 1000, 2000)
        assert len(clip) == 1

    def test_word_completely_outside(self):
        words = [CaptionWord(text="outside", start_ms=2500, end_ms=3000)]
        clip = trim_words_to_clip(words, 1000, 2000)
        assert clip == []

    def test_reversed_clip_boundaries_rejected(self):
        with pytest.raises(ValueError):
            trim_words_to_clip(make_words(), 2000, 1000)


class TestNormalizeWordsToClip:
    def test_negative_local_time_prevention(self):
        words = [CaptionWord(text="overlap", start_ms=800, end_ms=1200)]
        local = normalize_words_to_clip(words, 1000, 2000)
        assert local[0].start_ms == 0
        assert local[0].end_ms == 200

    def test_millisecond_rounding(self):
        # 0.1234s -> 123ms, 0.1236s -> 124ms
        words = [CaptionWord(text="w", start_ms=123, end_ms=124)]
        local = normalize_words_to_clip(words, 0, 200)
        assert local[0].start_ms == 123
        assert local[0].end_ms == 124

    def test_end_clamped_to_duration(self):
        words = [CaptionWord(text="overlap", start_ms=1800, end_ms=2200)]
        local = normalize_words_to_clip(words, 1000, 2000)
        assert local[0].start_ms == 800
        assert local[0].end_ms == 1000

    def test_original_objects_not_mutated(self):
        words = [CaptionWord(text="w", start_ms=800, end_ms=1200)]
        _ = normalize_words_to_clip(words, 1000, 2000)
        assert words[0].start_ms == 800
        assert words[0].end_ms == 1200

    def test_boundary_touching_word_dropped(self):
        # Word that ends exactly where clip starts should become zero-duration
        # after clamping and be dropped.
        words = [CaptionWord(text="touch", start_ms=0, end_ms=1000)]
        local = normalize_words_to_clip(words, 1000, 2000)
        assert local == []
