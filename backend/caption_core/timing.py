# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Pure timing utilities for clip-local caption coordinates.

All timestamps are integer milliseconds. Input floats are assumed to be in
seconds and are rounded to the nearest millisecond. Clip boundaries use a
half-open interval: ``start_ms <= t < end_ms``.
"""
from __future__ import annotations

from backend.caption_core.models import CaptionWord


def seconds_to_ms(seconds: float) -> int:
    """Round a seconds value to the nearest millisecond."""
    return int(seconds * 1000.0 + 0.5)


def ms_to_seconds(ms: int) -> float:
    """Convert milliseconds to seconds as a float."""
    return ms / 1000.0


def to_clip_local_time(source_ms: int, clip_start_ms: int) -> int:
    """Convert a source timestamp to clip-local time."""
    return source_ms - clip_start_ms


def to_source_time(local_ms: int, clip_start_ms: int) -> int:
    """Convert a clip-local timestamp back to source time."""
    return local_ms + clip_start_ms


def shift_words(words: list[CaptionWord], shift_ms: int) -> list[CaptionWord]:
    """Return a new list of words with timestamps shifted by ``shift_ms``.

    Does not mutate the input list or the original word objects.
    """
    return [
        word.model_copy(update={"start_ms": word.start_ms + shift_ms, "end_ms": word.end_ms + shift_ms})
        for word in words
    ]


def trim_words_to_clip(
    words: list[CaptionWord],
    clip_start_ms: int,
    clip_end_ms: int,
    inclusive_end: bool = False,
) -> list[CaptionWord]:
    """Return the subset of words that overlap with the clip window.

    Default overlap test is half-open: ``word.start < clip_end`` and
    ``word.end > clip_start``. If ``inclusive_end`` is ``True`` the end
    boundary is treated as inclusive.
    """
    if clip_end_ms < clip_start_ms:
        raise ValueError(
            f"clip_end_ms ({clip_end_ms}) must be >= clip_start_ms ({clip_start_ms})"
        )

    def _overlaps(word: CaptionWord) -> bool:
        if inclusive_end:
            return word.start_ms <= clip_end_ms and word.end_ms >= clip_start_ms
        return word.start_ms < clip_end_ms and word.end_ms > clip_start_ms

    return [w for w in words if _overlaps(w)]


def normalize_words_to_clip(
    words: list[CaptionWord],
    clip_start_ms: int,
    clip_end_ms: int,
    inclusive_end: bool = False,
) -> list[CaptionWord]:
    """Trim words to a clip and convert their timestamps to clip-local time.

    Words that partially overlap the clip have their local timestamps clamped
    to ``[0, clip_end_ms - clip_start_ms]``. Negative local times and values
    beyond the clip duration are clamped away, which safely handles minor
    floating-point rounding at the edges.

    The returned list is a deep copy; input objects are not mutated.
    """
    if clip_end_ms < clip_start_ms:
        raise ValueError(
            f"clip_end_ms ({clip_end_ms}) must be >= clip_start_ms ({clip_start_ms})"
        )

    duration_ms = clip_end_ms - clip_start_ms
    trimmed = trim_words_to_clip(words, clip_start_ms, clip_end_ms, inclusive_end=inclusive_end)

    normalized: list[CaptionWord] = []
    for word in trimmed:
        local_start = max(word.start_ms - clip_start_ms, 0)
        local_end = min(word.end_ms - clip_start_ms, duration_ms)

        # Clamp small rounding overshoots so no word ever leaks outside the
        # clip-local coordinate system.
        if local_start > duration_ms:
            local_start = duration_ms
        if local_end < 0:
            local_end = 0
        if local_end < local_start:
            local_end = local_start

        # Drop zero-duration words that only touch a boundary.
        if local_start == local_end:
            continue

        normalized.append(
            word.model_copy(update={"start_ms": local_start, "end_ms": local_end})
        )

    return normalized
