# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Compatibility bridge between the caption-core models and the existing ASS/FFmpeg renderer.

The bridge converts ``CaptionWord`` and ``CaptionStyle`` objects into the
legacy segment/style dictionaries expected by ``backend.services.caption_service``.
No ASS rendering logic is duplicated here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.caption_core.models import CaptionStyle, CaptionWord
from backend.caption_core.timing import ms_to_seconds


def words_to_legacy_segments(words: list[CaptionWord]) -> list[dict[str, Any]]:
    """Convert core words into the segment-with-words format used by the ASS renderer.

    The legacy renderer expects seconds as floats and a top-level ``words`` list.
    All words are placed in a single synthetic segment whose start/end encloses
    the full word range.
    """
    if not words:
        return []

    legacy_words = []
    for word in words:
        legacy_words.append({
            "text": word.text,
            "start": ms_to_seconds(word.start_ms),
            "end": ms_to_seconds(word.end_ms),
        })

    start_s = ms_to_seconds(min(w.start_ms for w in words))
    end_s = ms_to_seconds(max(w.end_ms for w in words))

    return [{
        "start": start_s,
        "end": end_s,
        "text": " ".join(w.text for w in words),
        "words": legacy_words,
    }]


def core_style_to_legacy_dict(style: CaptionStyle) -> dict[str, Any]:
    """Return a legacy-style dict compatible with ``caption_service`` ASS rendering."""
    return style.to_ass_style_dict()


async def generate_captions_from_core(
    words: list[CaptionWord],
    style: CaptionStyle,
    aspect_ratio: str = "9:16",
    output_path: Path | None = None,
    emoji_style: str = "moderate",
) -> Path:
    """Generate an ASS file from core caption data using the existing renderer.

    This is the minimal integration point: convert core data to the legacy
    shape, then call ``caption_service.generate_captions_ass``.
    """
    from backend.services import caption_service

    segments = words_to_legacy_segments(words)
    style_config = core_style_to_legacy_dict(style)
    return await caption_service.generate_captions_ass(
        segments,
        style="viral",  # ignored when style_config is supplied
        aspect_ratio=aspect_ratio,
        output_path=output_path,
        emoji_style=emoji_style,
        style_config=style_config,
    )
