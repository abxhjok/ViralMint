# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for animation registry and dispatcher."""
import pytest

from backend.caption_core.animation.context import AnimationContext
from backend.caption_core.animation.registry import ANIMATION_PRIMITIVES, dispatch_animation
from backend.caption_core.models import CaptionAnimation, CaptionSegment, CaptionWord


def test_registry_keys():
    assert set(ANIMATION_PRIMITIVES.keys()) == {"fade", "scale", "spring", "bounce", "glitch", "typewriter", "karaoke"}


def test_dispatch_unknown_type():
    word = CaptionWord(text="w", start_ms=0, end_ms=100)
    segment = CaptionSegment(words=[word])
    anim = CaptionAnimation.model_construct(type="not_registered", duration_ms=100, parameters={})
    ctx = AnimationContext.from_word(
        word=word,
        word_index=0,
        active_word_index=0,
        segment=segment,
        animation_config=anim,
        frame=0,
        fps=30,
    )
    with pytest.raises(ValueError, match="Unknown animation type"):
        dispatch_animation(ctx)


def test_dispatch_fade():
    word = CaptionWord(text="w", start_ms=0, end_ms=1000)
    segment = CaptionSegment(words=[word])
    anim = CaptionAnimation(type="fade", duration_ms=1000, parameters={"direction": "in"})
    ctx = AnimationContext.from_word(
        word=word,
        word_index=0,
        active_word_index=0,
        segment=segment,
        animation_config=anim,
        frame=30,
        fps=30,
    )
    result = dispatch_animation(ctx)
    assert result.opacity == pytest.approx(1.0)
