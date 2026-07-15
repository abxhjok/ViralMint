# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for deterministic caption segmentation."""
import pytest

from backend.caption_core.models import CaptionWord
from backend.caption_core.segmentation import SegmentationConfig, segment_words


def make_words(texts: list[str]) -> list[CaptionWord]:
    words = []
    t = 0
    for i, text in enumerate(texts):
        start = t
        end = t + 200
        words.append(CaptionWord(text=text, start_ms=start, end_ms=end))
        t = end
    return words


class TestSegmentWords:
    def test_short_sentence(self):
        words = make_words(["Hello", "world"])
        config = SegmentationConfig(max_words_per_segment=5)
        segments = segment_words(words, config)
        assert len(segments) == 1
        assert segments[0].text() == "Hello world"

    def test_long_sentence_split_by_word_count(self):
        words = make_words(["one", "two", "three", "four", "five"])
        config = SegmentationConfig(max_words_per_segment=2)
        segments = segment_words(words, config)
        assert len(segments) == 3
        assert segments[0].text() == "one two"
        assert segments[1].text() == "three four"
        assert segments[2].text() == "five"

    def test_punctuation_boundary(self):
        words = make_words(["Hello", "world.", "How", "are", "you?"])
        config = SegmentationConfig(max_words_per_segment=4)
        segments = segment_words(words, config)
        # The first punctuation split after "world." should be respected.
        assert len(segments) >= 2
        assert segments[0].text() == "Hello world."

    def test_max_char_count(self):
        words = make_words(["hello", "world", "this", "is", "longword"])
        config = SegmentationConfig(max_words_per_segment=10, max_chars_per_segment=15)
        segments = segment_words(words, config)
        for seg in segments:
            assert len(seg.text()) <= 15

    def test_large_speech_gap(self):
        words = [
            CaptionWord(text="one", start_ms=0, end_ms=200),
            CaptionWord(text="two", start_ms=5000, end_ms=5200),
        ]
        config = SegmentationConfig(max_words_per_segment=10, max_gap_ms=1000)
        segments = segment_words(words, config)
        assert len(segments) == 2
        assert segments[0].text() == "one"
        assert segments[1].text() == "two"

    def test_single_word(self):
        words = make_words(["hello"])
        config = SegmentationConfig(max_words_per_segment=3)
        segments = segment_words(words, config)
        assert len(segments) == 1
        assert segments[0].text() == "hello"

    def test_empty_input(self):
        segments = segment_words([], SegmentationConfig())
        assert segments == []

    def test_max_duration(self):
        words = [
            CaptionWord(text="one", start_ms=0, end_ms=900),
            CaptionWord(text="two", start_ms=900, end_ms=1200),
            CaptionWord(text="three", start_ms=1200, end_ms=1500),
        ]
        config = SegmentationConfig(max_words_per_segment=10, max_duration_ms=1000)
        segments = segment_words(words, config)
        assert len(segments) >= 2

    def test_words_not_reordered(self):
        words = make_words(["a", "b", "c", "d"])
        config = SegmentationConfig(max_words_per_segment=2)
        segments = segment_words(words, config)
        all_texts = " ".join(s.text() for s in segments)
        assert all_texts == "a b c d"

    def test_no_words_dropped(self):
        words = make_words(["one", "two.", "three", "four.", "five"])
        config = SegmentationConfig(max_words_per_segment=2, prefer_punctuation=True)
        segments = segment_words(words, config)
        returned = [w.text for seg in segments for w in seg.words]
        assert returned == ["one", "two.", "three", "four.", "five"]
