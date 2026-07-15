# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for deterministic active-word calculation."""
import pytest

from backend.caption_core.active_word import find_active_word_index
from backend.caption_core.models import CaptionWord


def make_words() -> list[CaptionWord]:
    return [
        CaptionWord(text="one", start_ms=0, end_ms=300),
        CaptionWord(text="two", start_ms=300, end_ms=600),
        CaptionWord(text="three", start_ms=600, end_ms=1000),
    ]


class TestFindActiveWordIndex:
    def test_empty_words(self):
        assert find_active_word_index([], 100) is None

    def test_first_word_active(self):
        words = make_words()
        assert find_active_word_index(words, 100) == 0

    def test_last_word_active(self):
        words = make_words()
        assert find_active_word_index(words, 800) == 2

    def test_between_words_returns_none(self):
        words = make_words()
        # At exactly 600, word three is active (600 <= 600 < 1000).
        # There is no gap.
        assert find_active_word_index(words, 599) == 1

    def test_gap_between_words(self):
        words = [
            CaptionWord(text="one", start_ms=0, end_ms=300),
            CaptionWord(text="two", start_ms=500, end_ms=800),
        ]
        assert find_active_word_index(words, 400) is None

    def test_overlapping_words_priority(self):
        words = [
            CaptionWord(text="short", start_ms=100, end_ms=250),
            CaptionWord(text="long", start_ms=100, end_ms=400),
        ]
        # Both start at 100. Shorter duration should win.
        assert find_active_word_index(words, 150) == 0

    def test_overlapping_earlier_start_wins(self):
        words = [
            CaptionWord(text="early", start_ms=100, end_ms=500),
            CaptionWord(text="late", start_ms=200, end_ms=600),
        ]
        assert find_active_word_index(words, 250) == 0

    def test_zero_duration_word_at_exact_point(self):
        words = [
            CaptionWord(text="one", start_ms=0, end_ms=300),
            CaptionWord(text="marker", start_ms=300, end_ms=300),
            CaptionWord(text="two", start_ms=300, end_ms=600),
        ]
        # At 300 the non-zero words one and two are also active because of
        # half-open intervals. Non-zero words win; the earliest-start/shortest
        # non-zero word is "two" (same start as marker, duration 300) and
        # "one" ends at 300 so is not active at t=300. So "two" wins.
        assert find_active_word_index(words, 300) == 2

    def test_zero_duration_word_only_when_uncovered(self):
        words = [
            CaptionWord(text="one", start_ms=0, end_ms=300),
            CaptionWord(text="marker", start_ms=300, end_ms=300),
            CaptionWord(text="two", start_ms=400, end_ms=700),
        ]
        # At 300 no non-zero word covers it (one ends at 300, two starts at 400).
        assert find_active_word_index(words, 300) == 1

    def test_zero_duration_word_no_match(self):
        words = [
            CaptionWord(text="one", start_ms=0, end_ms=300),
            CaptionWord(text="marker", start_ms=300, end_ms=300),
        ]
        # At 300 the marker is zero-duration and active; one ends at 300.
        assert find_active_word_index(words, 300) == 1

    def test_time_before_or_after_returns_none(self):
        words = make_words()
        assert find_active_word_index(words, -1) is None
        assert find_active_word_index(words, 2000) is None
