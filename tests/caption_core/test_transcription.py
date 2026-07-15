# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for the transcription-to-CaptionWord adapter."""
import pytest

from backend.caption_core.models import CaptionWord
from backend.caption_core.transcription import words_from_transcription


class TestWordsFromTranscription:
    def test_normal_word(self):
        segments = [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "hello world",
                "words": [
                    {"word": "hello", "start": 0.0, "end": 0.5, "probability": 0.95},
                    {"word": "world", "start": 0.5, "end": 1.0, "probability": 0.90},
                ],
            }
        ]
        words = words_from_transcription(segments)
        assert len(words) == 2
        assert words[0].text == "hello"
        assert words[0].start_ms == 0
        assert words[0].end_ms == 500
        assert words[0].confidence == 0.95

    def test_missing_confidence(self):
        segments = [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "hello",
                "words": [{"word": "hello", "start": 0.0, "end": 1.0}],
            }
        ]
        words = words_from_transcription(segments)
        assert words[0].confidence is None

    def test_missing_speaker(self):
        segments = [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "hello",
                "words": [{"word": "hello", "start": 0.0, "end": 1.0}],
            }
        ]
        words = words_from_transcription(segments)
        assert words[0].speaker_id is None

    def test_floating_point_conversion(self):
        segments = [
            {
                "start": 1.234,
                "end": 2.567,
                "text": "hello",
                "words": [{"word": "hello", "start": 1.234, "end": 2.567}],
            }
        ]
        words = words_from_transcription(segments)
        assert words[0].start_ms == 1234
        assert words[0].end_ms == 2567

    def test_zero_duration_word(self):
        segments = [
            {
                "start": 1.0,
                "end": 1.0,
                "text": "",
                "words": [{"word": "marker", "start": 1.0, "end": 1.0}],
            }
        ]
        words = words_from_transcription(segments)
        assert words[0].text == "marker"
        assert words[0].start_ms == 1000
        assert words[0].end_ms == 1000

    def test_invalid_reversed_timestamps(self):
        segments = [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "hello",
                "words": [{"word": "hello", "start": 1.0, "end": 0.0}],
            }
        ]
        with pytest.raises(ValueError):
            words_from_transcription(segments)

    def test_flat_word_list_input(self):
        words_input = [
            {"text": "hello", "start": 0.0, "end": 0.5},
            {"text": "world", "start": 0.5, "end": 1.0},
        ]
        words = words_from_transcription(words_input)
        assert [w.text for w in words] == ["hello", "world"]

    def test_speaker_inheritance(self):
        segments = [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "hello",
                "speaker": "speaker_1",
                "words": [{"word": "hello", "start": 0.0, "end": 1.0}],
            }
        ]
        words = words_from_transcription(segments)
        assert words[0].speaker_id == "speaker_1"

    def test_fallback_segment_splitting(self):
        segments = [
            {
                "start": 0.0,
                "end": 0.6,
                "text": "hello world",
            }
        ]
        words = words_from_transcription(segments)
        assert len(words) == 2
        assert words[0].text == "hello"
        assert words[1].text == "world"
