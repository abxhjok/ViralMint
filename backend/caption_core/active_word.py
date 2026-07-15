# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Deterministic active-word calculation.

Active-word lookup is a pure function of word timestamps and a query time.
It does not use wall-clock timers.

Boundary behavior
-----------------
A word is considered active at ``current_time_ms`` when
``start_ms <= current_time_ms < end_ms`` (half-open interval). Words with
``start_ms == end_ms`` are zero-duration markers; they are active only at
that exact millisecond when no non-zero-duration word covers it.

Overlapping words
-----------------
If multiple words satisfy the interval, the winner is chosen by this
deterministic priority:

1. Non-zero-duration words beat zero-duration words.
2. Earlier ``start_ms`` beats later ``start_ms``.
3. Shorter duration beats longer duration.
4. Lower list index beats higher list index (stable tie-breaker).
"""
from __future__ import annotations

from backend.caption_core.models import CaptionWord


def find_active_word_index(words: list[CaptionWord], current_time_ms: int) -> int | None:
    """Return the index of the active word at ``current_time_ms``, or ``None``.

    The half-open interval ``[start, end)`` is used for non-zero-duration
    words. Zero-duration words are considered active only at their exact
    ``start_ms == end_ms`` timestamp and only if no non-zero-duration word
    covers that timestamp.
    """
    if not words:
        return None

    candidates: list[int] = []
    for i, word in enumerate(words):
        if word.start_ms <= current_time_ms < word.end_ms:
            candidates.append(i)

    if candidates:
        # Sort by (start, duration, original index) for deterministic priority.
        candidates.sort(key=lambda i: (words[i].start_ms, words[i].duration_ms(), i))
        # Prefer non-zero-duration words over zero-duration words.
        non_zero = [i for i in candidates if words[i].duration_ms() > 0]
        if non_zero:
            return non_zero[0]
        return candidates[0]

    # No interval match — check zero-duration marker words at exact point.
    for i, word in enumerate(words):
        if word.is_zero_duration() and word.start_ms == current_time_ms:
            return i

    return None
