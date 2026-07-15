# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Deterministic caption-event evaluation.

This module answers: *which animation configurations apply to this word at this
frame?* It does not emit runtime events; it is a pure function of timing.
"""
from __future__ import annotations

from backend.caption_core.models import CaptionAnimation, CaptionSegment, CaptionWord


def _is_active_word(word: CaptionWord, current_time_ms: int) -> bool:
    """Return True if ``current_time_ms`` falls inside ``word`` (inclusive).

    The animation engine uses an inclusive boundary so a word is still
    considered active on the frame that aligns with its end boundary. This
    does not change the Phase 1 active-word lookup semantics used elsewhere.
    """
    return word.start_ms <= current_time_ms <= word.end_ms


def _event_window(trigger: str, word: CaptionWord, segment: CaptionSegment, delay_ms: int, duration_ms: int) -> tuple[int, int]:
    """Return the [start, end] applicability window for a conceptual trigger."""
    if trigger == "WORD_ENTER":
        start = word.start_ms + delay_ms
        end = start + duration_ms
    elif trigger == "WORD_EXIT":
        start = word.end_ms + delay_ms
        end = start + duration_ms
    elif trigger == "WORD_ACTIVE":
        # Active for the whole word interval; the primitive handles its own
        # duration/playback using ``duration_mode`` and ``duration_ms``.
        start = word.start_ms + delay_ms
        end = word.end_ms
    elif trigger == "SEGMENT_ENTER":
        start = segment.start_ms + delay_ms
        end = start + duration_ms
    elif trigger == "SEGMENT_EXIT":
        start = segment.end_ms + delay_ms
        end = start + duration_ms
    else:
        start = word.start_ms + delay_ms
        end = start + duration_ms
    return start, end


def is_event_active(
    trigger: str,
    word: CaptionWord,
    segment: CaptionSegment,
    current_time_ms: int,
    animation: CaptionAnimation,
    word_index: int | None = None,
    active_word_index: int | None = None,
) -> bool:
    """Return True if ``animation`` is currently applicable to ``word``."""
    if trigger == "WORD_ACTIVE":
        # Only the currently active word receives the active-word animation.
        if active_word_index is not None and word_index != active_word_index:
            return False
        if not _is_active_word(word, current_time_ms):
            return False

    start, end = _event_window(trigger, word, segment, animation.delay_ms, animation.duration_ms)

    if animation.duration_ms <= 0 and trigger not in ("WORD_ACTIVE",):
        # Instant one-shot trigger event: active exactly at the trigger time.
        return current_time_ms == start

    return start <= current_time_ms <= end
