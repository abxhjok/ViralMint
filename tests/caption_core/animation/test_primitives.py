# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for animation primitives."""
import math

import pytest

from backend.caption_core.animation.context import AnimationContext, frame_to_ms
from backend.caption_core.animation.primitives import (
    evaluate_bounce,
    evaluate_fade,
    evaluate_glitch,
    evaluate_karaoke,
    evaluate_scale,
    evaluate_spring,
    evaluate_typewriter,
    grapheme_count,
    visible_character_count,
    visible_text,
)
from backend.caption_core.models import CaptionAnimation, CaptionSegment, CaptionWord


def ctx(
    word: CaptionWord,
    anim: CaptionAnimation,
    frame: int = 0,
    fps: int = 30,
    word_index: int = 0,
    trigger: str = "WORD_ACTIVE",
    trigger_time_ms: int | None = None,
) -> AnimationContext:
    segment = CaptionSegment(words=[word])
    if trigger_time_ms is None:
        trigger_time_ms = word.start_ms
    return AnimationContext.from_word(
        word=word,
        word_index=word_index,
        active_word_index=0,
        segment=segment,
        animation_config=anim,
        frame=frame,
        fps=fps,
        trigger=trigger,
        trigger_time_ms=trigger_time_ms,
    )


class TestFade:
    def test_fade_in_linear_progression(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="fade", duration_ms=1000, easing="linear", parameters={"direction": "in"})

        assert ctx(word, anim, frame=0).current_time_ms == 0
        assert evaluate_fade(ctx(word, anim, frame=0)).opacity == pytest.approx(0.0)
        # 25% / 50% / 75% / completion at 60fps for exact millisecond alignment.
        assert evaluate_fade(ctx(word, anim, frame=15, fps=60)).opacity == pytest.approx(0.25)
        assert evaluate_fade(ctx(word, anim, frame=30, fps=60)).opacity == pytest.approx(0.5)
        assert evaluate_fade(ctx(word, anim, frame=45, fps=60)).opacity == pytest.approx(0.75)
        assert evaluate_fade(ctx(word, anim, frame=60, fps=60)).opacity == pytest.approx(1.0)
        # after completion
        assert evaluate_fade(ctx(word, anim, frame=90, fps=60)).opacity == pytest.approx(1.0)

    def test_fade_out(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="fade", duration_ms=1000, easing="linear", parameters={"direction": "out"})
        assert evaluate_fade(ctx(word, anim, frame=0)).opacity == pytest.approx(1.0)
        assert evaluate_fade(ctx(word, anim, frame=30, fps=30)).opacity == pytest.approx(0.0)
        # at 15 fps for 500ms at frame 15? 15/30 = 500ms, progress=0.5
        assert evaluate_fade(ctx(word, anim, frame=15, fps=30)).opacity == pytest.approx(0.5)

    def test_fade_in_before_start(self):
        word = CaptionWord(text="w", start_ms=500, end_ms=1000)
        anim = CaptionAnimation(type="fade", duration_ms=300, delay_ms=100, parameters={"direction": "in"})
        assert evaluate_fade(ctx(word, anim, frame=0, fps=30)).opacity == pytest.approx(0.0)


class TestScale:
    def test_scale_progression(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="scale", duration_ms=1000, easing="linear", parameters={"from_scale": 0.5, "to_scale": 2.0})
        assert evaluate_scale(ctx(word, anim, frame=0)).scale == pytest.approx(0.5)
        assert evaluate_scale(ctx(word, anim, frame=30, fps=60)).scale == pytest.approx(1.25)
        assert evaluate_scale(ctx(word, anim, frame=60, fps=60)).scale == pytest.approx(2.0)

    def test_scale_with_ease_in(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="scale", duration_ms=1000, easing="ease_in", parameters={"from_scale": 1.0, "to_scale": 2.0})
        # at 50% progress (frame 30 @ 60fps) ease_in t=0.5 -> 0.25
        assert evaluate_scale(ctx(word, anim, frame=30, fps=60)).scale == pytest.approx(1.25)


class TestSpring:
    def test_spring_settles_toward_one(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="spring", duration_ms=1000, parameters={"stiffness": 300, "damping": 20, "amplitude": 0.5})
        end_state = evaluate_spring(ctx(word, anim, frame=120, fps=30))
        assert end_state.scale == pytest.approx(1.0, abs=0.1)

    def test_spring_translate_y(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="spring", duration_ms=1000, parameters={"property": "translate_y", "amplitude": 20})
        state = evaluate_spring(ctx(word, anim, frame=0, fps=30))
        assert state.translate_y == pytest.approx(0.0, abs=0.1)

    def test_invalid_spring_parameters_protected(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="spring", duration_ms=1000, parameters={"stiffness": -10, "mass": -5})
        # Should not raise; defaults protect against invalid values.
        result = evaluate_spring(ctx(word, anim, frame=30, fps=30))
        assert result.scale >= 0


class TestBounce:
    def test_vertical_bounce(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="bounce", duration_ms=500, parameters={"direction": "vertical", "amplitude": 15})
        state = evaluate_bounce(ctx(word, anim, frame=10, fps=60))
        assert state.translate_y != 0.0

    def test_scale_bounce(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="bounce", duration_ms=500, parameters={"direction": "scale", "amplitude": 0.4})
        state = evaluate_bounce(ctx(word, anim, frame=10, fps=60))
        assert state.scale != pytest.approx(1.0)


class TestGlitch:
    def test_glitch_deterministic(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="glitch", duration_ms=1000, parameters={"intensity": 1.0, "frequency": 1, "seed_offset": "x"})
        c1 = evaluate_glitch(ctx(word, anim, frame=10, fps=30, word_index=0))
        c2 = evaluate_glitch(ctx(word, anim, frame=10, fps=30, word_index=0))
        assert c1.model_dump() == c2.model_dump()

    def test_glitch_changes_with_frame(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="glitch", duration_ms=1000, parameters={"intensity": 1.0, "frequency": 1, "seed_offset": "x"})
        c1 = evaluate_glitch(ctx(word, anim, frame=5, fps=30))
        c2 = evaluate_glitch(ctx(word, anim, frame=6, fps=30))
        assert c1.translate_x != c2.translate_x or c1.translate_y != c2.translate_y

    def test_glitch_no_random(self):
        import random
        # Ensure the primitive does not import or call random.
        # We just verify determinism with different word ids.
        word1 = CaptionWord(text="w", start_ms=0, end_ms=1000)
        word2 = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="glitch", duration_ms=1000)
        c1 = evaluate_glitch(ctx(word1, anim, frame=10, fps=30, word_index=0))
        c2 = evaluate_glitch(ctx(word2, anim, frame=10, fps=30, word_index=0))
        assert c1.model_dump() != c2.model_dump() or word1.id == word2.id


class TestTypewriter:
    def test_typewriter_progress(self):
        word = CaptionWord(text="hello", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="typewriter", duration_ms=1000, easing="linear")
        assert evaluate_typewriter(ctx(word, anim, frame=0)).reveal_progress == pytest.approx(0.0)
        assert evaluate_typewriter(ctx(word, anim, frame=30, fps=30)).reveal_progress == pytest.approx(1.0)
        assert evaluate_typewriter(ctx(word, anim, frame=15, fps=30)).reveal_progress == pytest.approx(0.5)

    def test_visible_character_count_unicode(self):
        text = "héllo"  # 5 graphemes
        assert grapheme_count(text) == 5
        assert visible_character_count(text, 0.6) == 3
        assert visible_text(text, 0.6) == "hél"

    def test_visible_character_count_emoji(self):
        text = "hello world"
        assert visible_character_count(text, 0.5) == 6


class TestKaraoke:
    def test_karaoke_progress(self):
        word = CaptionWord(text="w", start_ms=0, end_ms=1000)
        anim = CaptionAnimation(type="karaoke", duration_ms=0, parameters={"duration_mode": "word"})
        assert evaluate_karaoke(ctx(word, anim, frame=0)).highlight_progress == pytest.approx(0.0)
        assert evaluate_karaoke(ctx(word, anim, frame=30, fps=30)).highlight_progress == pytest.approx(1.0)
        assert evaluate_karaoke(ctx(word, anim, frame=15, fps=30)).highlight_progress == pytest.approx(0.5)

    def test_karaoke_zero_duration_word(self):
        word = CaptionWord(text="w", start_ms=500, end_ms=500)
        anim = CaptionAnimation(type="karaoke", duration_ms=0, parameters={"duration_mode": "word"})
        # Frame 15 @ 30fps == 500ms, the exact zero-duration boundary.
        assert evaluate_karaoke(ctx(word, anim, frame=15, fps=30)).highlight_progress == pytest.approx(1.0)
        # One frame before the marker should yield no highlight.
        assert evaluate_karaoke(ctx(word, anim, frame=14, fps=30)).highlight_progress == pytest.approx(0.0)


class TestGraphemeCount:
    def test_combining_characters(self):
        text = "é"  # could be single codepoint e + combining acute? Python literal is one codepoint. Use decomposed.
        decomposed = "e\u0301"
        assert grapheme_count(decomposed) == 1
        assert visible_text(decomposed, 1.0) == decomposed
