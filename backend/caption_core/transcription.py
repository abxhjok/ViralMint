# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Adapter from existing Whisper/faster-whisper transcription to CaptionWord.

The existing transcription word representation is a list of segment dicts:

    [
      {
        "start": 0.0,
        "end": 5.0,
        "text": "Hello world",
        "words": [
          {"word": "Hello", "start": 0.0, "end": 0.5, "probability": 0.98},
          ...
        ]
      }
    ]

or a flat list of word dicts from ``caption_service._extract_word_timestamps``:

    [{"text": "Hello", "start": 0.0, "end": 0.5}]

This adapter normalizes both into deterministic ``CaptionWord`` objects with
integer millisecond timestamps.
"""
from __future__ import annotations

from typing import Any, Optional

from backend.caption_core.models import CaptionWord
from backend.caption_core.timing import seconds_to_ms


def _extract_confidence(word_data: dict) -> Optional[float]:
    """Return a normalized confidence value in [0, 1] when available."""
    for key in ("probability", "confidence"):
        value = word_data.get(key)
        if value is not None:
            try:
                f = float(value)
                if 0.0 <= f <= 1.0:
                    return f
                # Whisper probabilities are in [0, 1]; if not, ignore.
            except (TypeError, ValueError):
                continue
    return None


def _extract_speaker(word_data: dict, segment_data: dict) -> Optional[str]:
    """Return a speaker identifier if one exists at word or segment level."""
    for key in ("speaker", "speaker_id"):
        value = word_data.get(key)
        if value is not None and value != "":
            return str(value)
    for key in ("speaker", "speaker_id"):
        value = segment_data.get(key)
        if value is not None and value != "":
            return str(value)
    return None


def _parse_word_text(word_data: dict) -> str:
    """Extract and clean the word text, preferring the explicit ``word`` key."""
    text = word_data.get("word") or word_data.get("text") or ""
    return str(text).strip()


def _make_word(
    text: str,
    start: float,
    end: float,
    confidence: Optional[float],
    speaker_id: Optional[str],
) -> CaptionWord:
    """Create a CaptionWord, rejecting reversed timestamps."""
    start_ms = seconds_to_ms(start)
    end_ms = seconds_to_ms(end)
    if end_ms < start_ms:
        raise ValueError(
            f"Reversed timestamps for word {text!r}: start={start}s ({start_ms}ms), "
            f"end={end}s ({end_ms}ms)"
        )
    return CaptionWord(
        text=text,
        start_ms=start_ms,
        end_ms=end_ms,
        confidence=confidence,
        speaker_id=speaker_id,
    )


def _words_from_segment(segment: dict) -> list[CaptionWord]:
    """Convert one Whisper segment into CaptionWord objects."""
    if not isinstance(segment, dict):
        return []

    raw_words = segment.get("words")
    if isinstance(raw_words, list) and raw_words:
        words: list[CaptionWord] = []
        for w in raw_words:
            if not isinstance(w, dict):
                continue
            text = _parse_word_text(w)
            if not text:
                continue
            try:
                start = float(w.get("start", 0.0))
                end = float(w.get("end", 0.0))
            except (TypeError, ValueError):
                continue
            confidence = _extract_confidence(w)
            speaker_id = _extract_speaker(w, segment)
            words.append(_make_word(text, start, end, confidence, speaker_id))
        return words

    # Fallback: split segment text evenly across the segment duration.
    seg_text = segment.get("text", "")
    if not isinstance(seg_text, str):
        return []
    tokens = seg_text.strip().split()
    if not tokens:
        return []

    try:
        seg_start = max(float(segment.get("start", 0.0)), 0.0)
        seg_end = float(segment.get("end", seg_start + len(tokens) * 0.3))
    except (TypeError, ValueError):
        return []

    if seg_end <= seg_start:
        seg_end = seg_start + len(tokens) * 0.3

    duration = seg_end - seg_start
    per_word = duration / len(tokens)

    words = []
    for i, token in enumerate(tokens):
        w_start = seg_start + i * per_word
        w_end = w_start + per_word
        speaker_id = _extract_speaker({}, segment)
        words.append(_make_word(token, w_start, w_end, None, speaker_id))
    return words


def words_from_transcription(segments: list[dict]) -> list[CaptionWord]:
    """Convert legacy Whisper transcription segments into ``CaptionWord`` objects.

    Args:
        segments: Legacy segment dicts (or a flat list of word dicts). Each
            item must contain ``start``/``end`` and either ``words`` or ``text``.

    Returns:
        Ordered list of ``CaptionWord`` objects with millisecond timestamps.

    Raises:
        ValueError: If a word has reversed timestamps.
    """
    if not segments:
        return []

    # If the top-level list is already word dicts (not segments), wrap them
    # into one synthetic segment.
    if isinstance(segments, list) and segments and isinstance(segments[0], dict):
        first = segments[0]
        if "words" not in first and "word" in first:
            segments = [{"start": 0.0, "end": 0.0, "text": "", "words": segments}]

    words: list[CaptionWord] = []
    for segment in segments:
        words.extend(_words_from_segment(segment))
    return words
