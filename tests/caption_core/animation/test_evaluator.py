# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for the frame-state evaluator and event evaluation."""
import pytest

from backend.caption_core.animation.evaluator import evaluate_caption_word_state
from backend.caption_core.animation.events import is_event_active
from backend.caption_core.animation.state import CaptionVisualState
from backend.caption_core.models import CaptionAnimation, CaptionPreset, CaptionSegment, CaptionStyle, CaptionWord


def segment(words: list[CaptionWord]) -> CaptionSegment:
    return CaptionSegment(words=words)


def test_evaluate_empty_segment():
    preset = CaptionPreset(name="Test", style=CaptionStyle(name="Test"))
    word = CaptionWord(text="w", start_ms=0, end_ms=1000)
    seg = segment([])
    state = evaluate_caption_word_state(word, 0, seg, preset, frame=0, fps=30)
    assert isinstance(state, CaptionVisualState)


def test_word_active_fade_in():
    word = CaptionWord(text="hello", start_ms=0, end_ms=1000)
    preset = CaptionPreset(
        name="Fade In",
        style=CaptionStyle(name="Fade"),
        active_word_animation=CaptionAnimation(type="fade", duration_ms=1000, parameters={"direction": "in"}),
    )
    seg = segment([word])
    state_start = evaluate_caption_word_state(word, 0, seg, preset, frame=0, fps=30)
    state_mid = evaluate_caption_word_state(word, 0, seg, preset, frame=15, fps=30)
    state_end = evaluate_caption_word_state(word, 0, seg, preset, frame=30, fps=30)
    assert state_start.opacity == pytest.approx(0.0)
    assert state_mid.opacity == pytest.approx(0.5)
    assert state_end.opacity == pytest.approx(1.0)


def test_first_middle_last_words():
    words = [
        CaptionWord(text="one", start_ms=0, end_ms=300),
        CaptionWord(text="two", start_ms=300, end_ms=600),
        CaptionWord(text="three", start_ms=600, end_ms=900),
    ]
    preset = CaptionPreset(
        name="Karaoke",
        style=CaptionStyle(name="Karaoke"),
        active_word_animation=CaptionAnimation(type="karaoke", duration_ms=0, parameters={"duration_mode": "word"}),
    )
    seg = segment(words)
    s1 = evaluate_caption_word_state(words[0], 0, seg, preset, frame=5, fps=60)
    s2 = evaluate_caption_word_state(words[1], 1, seg, preset, frame=20, fps=60)
    s3 = evaluate_caption_word_state(words[2], 2, seg, preset, frame=44, fps=60)
    assert s1.highlight_progress > 0.0
    assert s2.highlight_progress > 0.0
    assert s3.highlight_progress > 0.0


def test_word_gaps_no_active():
    words = [
        CaptionWord(text="one", start_ms=0, end_ms=200),
        CaptionWord(text="two", start_ms=500, end_ms=700),
    ]
    preset = CaptionPreset(
        name="Fade",
        style=CaptionStyle(name="Fade"),
        active_word_animation=CaptionAnimation(type="fade", duration_ms=200),
    )
    seg = segment(words)
    # 300ms is in the gap.
    state = evaluate_caption_word_state(words[0], 0, seg, preset, frame=9, fps=30)
    assert state.opacity == pytest.approx(0.0)


def test_overlapping_words_deterministic():
    words = [
        CaptionWord(text="one", start_ms=0, end_ms=500),
        CaptionWord(text="two", start_ms=400, end_ms=800),
    ]
    preset = CaptionPreset(
        name="Karaoke",
        style=CaptionStyle(name="Karaoke"),
        active_word_animation=CaptionAnimation(type="karaoke", duration_ms=0, parameters={"duration_mode": "word"}),
    )
    seg = segment(words)
    # At 450ms both are technically active by interval; Phase 1 semantics pick the earlier-start.
    s0 = evaluate_caption_word_state(words[0], 0, seg, preset, frame=27, fps=60)
    s1 = evaluate_caption_word_state(words[1], 1, seg, preset, frame=27, fps=60)
    assert s0.highlight_progress > 0.0
    assert s1.highlight_progress == pytest.approx(0.0)


def test_zero_duration_word():
    word = CaptionWord(text="w", start_ms=500, end_ms=500)
    preset = CaptionPreset(
        name="Karaoke",
        style=CaptionStyle(name="Karaoke"),
        active_word_animation=CaptionAnimation(type="karaoke", duration_ms=0, parameters={"duration_mode": "word"}),
    )
    seg = segment([word])
    state = evaluate_caption_word_state(word, 0, seg, preset, frame=15, fps=30)
    assert state.highlight_progress == pytest.approx(1.0)


def test_word_enter_event_only_at_start():
    word = CaptionWord(text="w", start_ms=100, end_ms=1000)
    preset = CaptionPreset(
        name="Scale Entry",
        style=CaptionStyle(name="Scale"),
        entry_animation=CaptionAnimation(type="scale", duration_ms=200, parameters={"from_scale": 0.5, "to_scale": 1.5}),
    )
    seg = segment([word])
    state_before = evaluate_caption_word_state(word, 0, seg, preset, frame=0, fps=30)
    state_during = evaluate_caption_word_state(word, 0, seg, preset, frame=5, fps=30)
    state_after = evaluate_caption_word_state(word, 0, seg, preset, frame=30, fps=30)
    assert state_before.scale == pytest.approx(1.0)
    assert state_during.scale != pytest.approx(1.0)
    assert state_after.scale == pytest.approx(1.0)


def test_word_exit_event():
    word = CaptionWord(text="w", start_ms=0, end_ms=500)
    preset = CaptionPreset(
        name="Fade Out",
        style=CaptionStyle(name="Fade"),
        exit_animation=CaptionAnimation(type="fade", duration_ms=200, parameters={"direction": "out"}),
    )
    seg = segment([word])
    state_active = evaluate_caption_word_state(word, 0, seg, preset, frame=14, fps=30)
    state_exiting = evaluate_caption_word_state(word, 0, seg, preset, frame=20, fps=30)
    assert state_active.opacity == pytest.approx(1.0)
    assert state_exiting.opacity < 1.0


def test_determinism_same_inputs():
    word = CaptionWord(text="hello", start_ms=0, end_ms=1000)
    preset = CaptionPreset(
        name="Fade",
        style=CaptionStyle(name="Fade"),
        active_word_animation=CaptionAnimation(type="fade", duration_ms=1000),
    )
    seg = segment([word])
    s1 = evaluate_caption_word_state(word, 0, seg, preset, frame=10, fps=30)
    s2 = evaluate_caption_word_state(word, 0, seg, preset, frame=10, fps=30)
    assert s1.model_dump() == s2.model_dump()


def test_is_event_active_word_active():
    word = CaptionWord(text="w", start_ms=100, end_ms=400)
    seg = segment([word])
    anim = CaptionAnimation(type="fade", duration_ms=300)
    assert is_event_active("WORD_ACTIVE", word, seg, 250, anim) is True
    assert is_event_active("WORD_ACTIVE", word, seg, 50, anim) is False
    # Inclusive boundary: the word is still active at its exact end for rendering.
    assert is_event_active("WORD_ACTIVE", word, seg, 400, anim) is True
    assert is_event_active("WORD_ACTIVE", word, seg, 399, anim) is True


def test_is_event_active_word_enter():
    word = CaptionWord(text="w", start_ms=100, end_ms=400)
    seg = segment([word])
    anim = CaptionAnimation(type="scale", duration_ms=100)
    assert is_event_active("WORD_ENTER", word, seg, 100, anim) is True
    assert is_event_active("WORD_ENTER", word, seg, 250, anim) is False


def test_is_event_active_segment_enter():
    word = CaptionWord(text="w", start_ms=100, end_ms=400)
    seg = segment([word])
    seg.start_ms = 100
    seg.end_ms = 400
    anim = CaptionAnimation(type="scale", duration_ms=50)
    assert is_event_active("SEGMENT_ENTER", word, seg, 120, anim) is True
