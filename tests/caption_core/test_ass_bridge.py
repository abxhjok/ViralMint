# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for the ASS bridge between caption-core and the existing renderer."""
import asyncio
from pathlib import Path

from backend.caption_core.ass_bridge import (
    core_style_to_legacy_dict,
    generate_captions_from_core,
    words_to_legacy_segments,
)
from backend.caption_core.models import CaptionStyle, CaptionWord
from backend.services import caption_service


def test_words_to_legacy_segments():
    words = [
        CaptionWord(text="hello", start_ms=0, end_ms=500),
        CaptionWord(text="world", start_ms=500, end_ms=1000),
    ]
    segments = words_to_legacy_segments(words)
    assert len(segments) == 1
    assert segments[0]["text"] == "hello world"
    assert segments[0]["start"] == 0.0
    assert segments[0]["end"] == 1.0
    assert len(segments[0]["words"]) == 2
    assert segments[0]["words"][0]["text"] == "hello"


def test_core_style_to_legacy_dict_matches_viral():
    style = CaptionStyle(name="Viral")
    legacy = core_style_to_legacy_dict(style)
    viral = caption_service.CAPTION_STYLES["viral"]
    for key in ["font", "font_size_portrait", "font_size_landscape", "alignment", "margin_v", "words_per_group", "outline_width"]:
        assert legacy[key] == viral[key], key
    assert legacy["primary_color"] == viral["primary_color"]
    assert legacy["highlight_color"] == viral["highlight_color"]
    assert legacy["outline_color"] == viral["outline_color"]


def test_generate_captions_from_core_matches_legacy(tmp_path: Path):
    words = [
        CaptionWord(text="hello", start_ms=0, end_ms=500),
        CaptionWord(text="world", start_ms=500, end_ms=1000),
    ]
    style = CaptionStyle(name="Viral")
    core_path = tmp_path / "core.ass"
    legacy_path = tmp_path / "legacy.ass"

    core_result = asyncio.run(generate_captions_from_core(
        words, style, aspect_ratio="9:16", output_path=core_path, emoji_style="none"
    ))
    legacy_segments = words_to_legacy_segments(words)
    legacy_result = asyncio.run(caption_service.generate_captions_ass(
        legacy_segments,
        style="viral",
        aspect_ratio="9:16",
        output_path=legacy_path,
        emoji_style="none",
    ))

    assert core_result.exists()
    assert legacy_result.exists()
    core_content = core_path.read_text()
    legacy_content = legacy_path.read_text()
    assert "[Events]" in core_content
    assert core_content == legacy_content
