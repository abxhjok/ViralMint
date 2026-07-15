# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Deterministic caption segmentation from an ordered word list.

Segmentation is rule-based and does not require AI. It never reorders,
duplicates, or silently drops valid words.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator

from backend.caption_core.models import CaptionSegment, CaptionWord


class SegmentationConfig(BaseModel):
    """Configuration for the word segmentation algorithm."""

    max_words_per_segment: int = Field(default=3, ge=1)
    max_chars_per_segment: Optional[int] = Field(default=None, ge=1)
    max_duration_ms: Optional[int] = Field(default=None, ge=1)
    max_gap_ms: Optional[int] = Field(default=None, ge=0)
    prefer_punctuation: bool = True

    @model_validator(mode="after")
    def _consistent_constraints(self) -> "SegmentationConfig":
        if self.max_chars_per_segment is not None and self.max_chars_per_segment < self.max_words_per_segment:
            # Each word is at least one character; if max_chars is lower than
            # max_words the char limit wins per-word.
            pass
        return self


def _is_sentence_end(word: CaptionWord) -> bool:
    """Return True if the word text ends with sentence-terminating punctuation."""
    if not word.text:
        return False
    return word.text[-1] in ".!?"


def segment_words(words: list[CaptionWord], config: SegmentationConfig) -> list[CaptionSegment]:
    """Segment an ordered list of words into ``CaptionSegment`` objects.

    Rules (applied in order):

    1. ``max_gap_ms`` — a gap larger than this between consecutive words forces
       a new segment before the next word.
    2. ``max_words_per_segment`` — a segment may contain at most this many words.
    3. ``max_chars_per_segment`` — a segment may contain at most this many characters.
    4. ``max_duration_ms`` — a segment may span at most this many milliseconds.
    5. ``prefer_punctuation`` — when a hard limit is reached, try to close the
       segment at the most recent sentence-ending punctuation point. If no such
       point exists, close immediately before the word that would exceed the limit.

    Words are never reordered, duplicated, or dropped. A single word that
    itself exceeds ``max_chars_per_segment`` is placed in its own segment rather
    than being split.
    """
    if not words:
        return []

    segments: list[CaptionSegment] = []
    current: list[CaptionWord] = []
    current_chars = 0
    last_split_idx: Optional[int] = None

    def _close_up_to(idx: Optional[int]) -> None:
        """Close ``current[:idx]`` as a segment and keep ``current[idx:]``."""
        nonlocal current, current_chars, last_split_idx
        if idx is None or idx <= 0 or idx >= len(current):
            # Close the whole current buffer.
            if current:
                segments.append(CaptionSegment(words=current))
            current = []
            current_chars = 0
            last_split_idx = None
            return

        to_close = current[:idx]
        carry = current[idx:]
        segments.append(CaptionSegment(words=to_close))
        current = carry
        current_chars = sum(len(w.text) for w in carry)
        # Recalculate last split point within the carry buffer.
        last_split_idx = None
        for j, w in enumerate(current):
            if _is_sentence_end(w):
                last_split_idx = j + 1

    for word in words:
        # 1. Large speech gap: close current and start fresh.
        if (
            config.max_gap_ms is not None
            and current
            and word.start_ms - current[-1].end_ms > config.max_gap_ms
        ):
            _close_up_to(None)

        # 2. Check whether adding ``word`` would violate any hard limit.
        needs_close = False
        prospective_text_len = 0
        if current:
            if len(current) + 1 > config.max_words_per_segment:
                needs_close = True
            if config.max_chars_per_segment is not None:
                prospective_text_len = len(" ".join([w.text for w in current] + [word.text]))
                if prospective_text_len > config.max_chars_per_segment:
                    needs_close = True
            if config.max_duration_ms is not None and word.end_ms - current[0].start_ms > config.max_duration_ms:
                needs_close = True

        if needs_close:
            # Prefer to close at the last punctuation split point.
            if config.prefer_punctuation and last_split_idx is not None and last_split_idx <= len(current):
                _close_up_to(last_split_idx)
            else:
                _close_up_to(None)

        # Add the word to the current segment.
        current.append(word)
        if config.max_chars_per_segment is not None:
            current_chars = len(" ".join(w.text for w in current))
        else:
            current_chars += len(word.text)

        if config.prefer_punctuation and _is_sentence_end(word):
            last_split_idx = len(current)

    # Close any remaining words.
    if current:
        segments.append(CaptionSegment(words=current))

    return segments
