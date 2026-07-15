# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for frame/time conversion and AnimationContext."""
import pytest

from backend.caption_core.animation.context import AnimationContext, frame_to_ms, ms_to_frame
from backend.caption_core.models import CaptionWord, CaptionSegment, CaptionAnimation


def test_frame_to_ms_24fps():
    assert frame_to_ms(0, 24) == 0
    assert frame_to_ms(1, 24) == 42
    assert frame_to_ms(24, 24) == 1000


def test_frame_to_ms_30fps():
    assert frame_to_ms(0, 30) == 0
    assert frame_to_ms(1, 30) == 33
    assert frame_to_ms(30, 30) == 1000


def test_frame_to_ms_60fps():
    assert frame_to_ms(0, 60) == 0
    assert frame_to_ms(1, 60) == 17
    assert frame_to_ms(60, 60) == 1000


def test_frame_to_ms_invalid_fps():
    with pytest.raises(ValueError):
        frame_to_ms(0, 0)
    with pytest.raises(ValueError):
        frame_to_ms(0, -24)


def test_frame_to_ms_negative_frame():
    with pytest.raises(ValueError):
        frame_to_ms(-1, 24)


def test_ms_to_frame_round_trip():
    for fps in (24, 30, 60):
        for frame in (0, 1, 5, 10, 29, 30, 59, 60):
            ms = frame_to_ms(frame, fps)
            recovered = ms_to_frame(ms, fps)
            assert recovered == frame


def test_animation_context_from_word():
    word = CaptionWord(text="hello", start_ms=100, end_ms=400)
    segment = CaptionSegment(words=[word])
    anim = CaptionAnimation(type="fade")
    ctx = AnimationContext.from_word(
        word=word,
        word_index=0,
        active_word_index=0,
        segment=segment,
        animation_config=anim,
        frame=10,
        fps=30,
    )
    assert ctx.frame == 10
    assert ctx.fps == 30
    assert ctx.current_time_ms == 333
    assert ctx.word.text == "hello"


def test_unknown_trigger_rejected():
    word = CaptionWord(text="hello", start_ms=0, end_ms=100)
    segment = CaptionSegment(words=[word])
    anim = CaptionAnimation(type="fade")
    with pytest.raises(ValueError):
        AnimationContext(
            frame=0,
            fps=30,
            current_time_ms=0,
            word=word,
            word_index=0,
            segment=segment,
            animation_config=anim,
            trigger="UNKNOWN",
            trigger_time_ms=0,
        )
