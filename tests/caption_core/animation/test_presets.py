# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for the five initial animation presets."""
import pytest

from backend.caption_core.animation.evaluator import evaluate_caption_word_state
from backend.caption_core.animation.presets import get_preset, bounce_preset, explosive_preset, glitch_preset, typewriter_preset, karaoke_preset
from backend.caption_core.models import CaptionSegment, CaptionWord


def make_segment():
    word = CaptionWord(text="hello", start_ms=0, end_ms=1000)
    return word, CaptionSegment(words=[word])


@pytest.mark.parametrize("name", ["bounce", "explosive", "glitch", "typewriter", "karaoke"])
def test_get_preset(name):
    preset = get_preset(name)
    assert preset.name.lower() == name


def test_bounce_preset_active_word():
    word, seg = make_segment()
    preset = bounce_preset()
    state = evaluate_caption_word_state(word, 0, seg, preset, frame=5, fps=60)
    assert state.translate_y != 0.0


def test_explosive_preset_entry():
    word, seg = make_segment()
    preset = explosive_preset()
    state = evaluate_caption_word_state(word, 0, seg, preset, frame=10, fps=60)
    # Entry fade + scale + bounce effect.
    assert state.opacity > 0.0


def test_glitch_preset():
    word, seg = make_segment()
    preset = glitch_preset()
    state = evaluate_caption_word_state(word, 0, seg, preset, frame=10, fps=60)
    # Glitch should cause some displacement.
    assert (state.translate_x, state.translate_y, state.rotation) != (0.0, 0.0, 0.0)


def test_typewriter_preset():
    word, seg = make_segment()
    preset = typewriter_preset()
    state_start = evaluate_caption_word_state(word, 0, seg, preset, frame=0, fps=30)
    state_end = evaluate_caption_word_state(word, 0, seg, preset, frame=30, fps=30)
    assert state_start.reveal_progress == pytest.approx(0.0)
    assert state_end.reveal_progress == pytest.approx(1.0)


def test_karaoke_preset():
    word, seg = make_segment()
    preset = karaoke_preset()
    state_start = evaluate_caption_word_state(word, 0, seg, preset, frame=0, fps=30)
    state_mid = evaluate_caption_word_state(word, 0, seg, preset, frame=15, fps=30)
    assert state_start.highlight_progress == pytest.approx(0.0)
    assert state_mid.highlight_progress > 0.0
