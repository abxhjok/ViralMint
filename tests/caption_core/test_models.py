# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for caption-core Pydantic models."""
import pytest

from backend.caption_core.models import (
    CaptionAnimation,
    CaptionLayout,
    CaptionPreset,
    CaptionSegment,
    CaptionStyle,
    CaptionWord,
)


class TestCaptionWord:
    def test_valid_word(self):
        w = CaptionWord(text="hello", start_ms=100, end_ms=400)
        assert w.text == "hello"
        assert w.start_ms == 100
        assert w.end_ms == 400
        assert w.duration_ms() == 300

    def test_zero_duration_word(self):
        w = CaptionWord(text="marker", start_ms=500, end_ms=500)
        assert w.is_zero_duration()

    def test_reversed_timestamps_rejected(self):
        with pytest.raises(ValueError):
            CaptionWord(text="bad", start_ms=400, end_ms=100)

    def test_empty_text_rejected(self):
        with pytest.raises(ValueError):
            CaptionWord(text="   ", start_ms=0, end_ms=100)

    def test_negative_start_rejected(self):
        with pytest.raises(ValueError):
            CaptionWord(text="word", start_ms=-1, end_ms=100)

    def test_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            CaptionWord(text="word", start_ms=0, end_ms=100, confidence=1.5)

    def test_text_is_stripped(self):
        w = CaptionWord(text="  spaced  ", start_ms=0, end_ms=100)
        assert w.text == "spaced"


class TestCaptionSegment:
    def test_valid_segment(self):
        words = [
            CaptionWord(text="one", start_ms=0, end_ms=100),
            CaptionWord(text="two", start_ms=100, end_ms=250),
        ]
        seg = CaptionSegment(words=words)
        assert seg.start_ms == 0
        assert seg.end_ms == 250
        assert seg.text() == "one two"

    def test_segment_sorts_words(self):
        words = [
            CaptionWord(text="second", start_ms=100, end_ms=200),
            CaptionWord(text="first", start_ms=0, end_ms=100),
        ]
        seg = CaptionSegment(words=words)
        assert seg.words[0].text == "first"
        assert seg.words[1].text == "second"

    def test_reversed_segment_times_rejected(self):
        with pytest.raises(ValueError):
            CaptionSegment(start_ms=100, end_ms=0)


class TestCaptionStyle:
    def test_default_to_ass_style_dict(self):
        style = CaptionStyle(name="Viral")
        ass = style.to_ass_style_dict()
        assert ass["font"] == "Arial Bold"
        assert ass["primary_color"] == "&H00FFFFFF"
        assert ass["highlight_color"] == "&H0000FFFF"
        assert ass["outline_color"] == "&H00000000"
        assert ass["alignment"] == 5

    def test_hex_color_conversion(self):
        style = CaptionStyle(
            name="Custom",
            text_color="#FF0000",
            active_word_color="#00FF00",
            stroke_color="#0000FF",
        )
        ass = style.to_ass_style_dict()
        # ASS BGR: red -> blue, green -> green, blue -> red
        assert ass["primary_color"] == "&H000000FF"
        assert ass["highlight_color"] == "&H0000FF00"
        assert ass["outline_color"] == "&H00FF0000"

    def test_invalid_color_rejected(self):
        with pytest.raises(ValueError):
            CaptionStyle(name="Bad", text_color="not-a-color")

    def test_bold_font_appended(self):
        style = CaptionStyle(name="Bold", font_family="Helvetica", font_weight="bold")
        assert style.to_ass_style_dict()["font"] == "Helvetica Bold"

    def test_non_bold_does_not_append(self):
        style = CaptionStyle(name="Regular", font_family="Arial", font_weight="normal")
        assert style.to_ass_style_dict()["font"] == "Arial"

    def test_words_per_group_positive(self):
        with pytest.raises(ValueError):
            CaptionStyle(name="Bad", words_per_group=0)


class TestCaptionPreset:
    def test_preset_defaults(self):
        preset = CaptionPreset(name="Viral", style=CaptionStyle(name="Viral"))
        assert preset.layout.max_words_per_line == 3
        assert preset.entry_animation is None
        assert preset.effects == []

    def test_preset_animation(self):
        anim = CaptionAnimation(type="bounce", duration_ms=200)
        preset = CaptionPreset(
            name="Bouncy",
            style=CaptionStyle(name="Bouncy"),
            active_word_animation=anim,
        )
        assert preset.active_word_animation.type.value == "bounce"
