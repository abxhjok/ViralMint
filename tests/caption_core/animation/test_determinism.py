# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Determinism and integration tests for the animation engine."""
import pytest

from backend.caption_core.animation.context import frame_to_ms
from backend.caption_core.animation.evaluator import evaluate_caption_word_state
from backend.caption_core.animation.presets import get_preset
from backend.caption_core.models import CaptionSegment, CaptionStyle, CaptionWord, CaptionPreset, CaptionAnimation


def make_segment():
    word = CaptionWord(text="hello", start_ms=0, end_ms=1000)
    return word, CaptionSegment(words=[word])


@pytest.mark.parametrize("fps", [24, 30, 60])
@pytest.mark.parametrize("preset_name", ["bounce", "explosive", "glitch", "typewriter", "karaoke"])
def test_evaluate_deterministic_across_fps(fps, preset_name):
    word, seg = make_segment()
    preset = get_preset(preset_name)
    frame = int(fps / 2)  # half-second
    s1 = evaluate_caption_word_state(word, 0, seg, preset, frame=frame, fps=fps)
    s2 = evaluate_caption_word_state(word, 0, seg, preset, frame=frame, fps=fps)
    assert s1.model_dump() == s2.model_dump()


@pytest.mark.parametrize("fps", [24, 30, 60])
def test_time_conversion_consistency(fps):
    word, seg = make_segment()
    preset = get_preset("karaoke")
    for frame in (0, fps // 4, fps // 2, fps - 1, fps):
        ms = frame_to_ms(frame, fps)
        s_ms = evaluate_caption_word_state(word, 0, seg, preset, frame=frame, fps=fps)
        # Re-evaluating with the same frame/fps must be identical.
        s_ms2 = evaluate_caption_word_state(word, 0, seg, preset, frame=frame, fps=fps)
        assert s_ms.model_dump() == s_ms2.model_dump()


def test_repeated_evaluation_same_inputs():
    word, seg = make_segment()
    preset = get_preset("glitch")
    results = [evaluate_caption_word_state(word, 0, seg, preset, frame=10, fps=30) for _ in range(20)]
    first = results[0].model_dump()
    assert all(r.model_dump() == first for r in results)


def test_invalid_fps_rejected():
    word, seg = make_segment()
    preset = get_preset("karaoke")
    with pytest.raises(ValueError):
        evaluate_caption_word_state(word, 0, seg, preset, frame=0, fps=0)


def test_unknown_animation_type_in_preset():
    word, seg = make_segment()
    preset = CaptionPreset(
        name="Bad",
        style=CaptionStyle(name="Bad"),
        active_word_animation=CaptionAnimation.model_construct(type="not_real", duration_ms=100, parameters={}),
    )
    with pytest.raises(ValueError, match="Unknown animation type"):
        evaluate_caption_word_state(word, 0, seg, preset, frame=0, fps=30)
