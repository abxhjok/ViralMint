# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for animation composition rules."""
from backend.caption_core.animation.composition import compose_animations
from backend.caption_core.animation.state import CaptionVisualState


def test_base_state_preserved():
    base = CaptionVisualState(opacity=0.8, scale=1.2)
    result = compose_animations(base, [])
    assert result.opacity == 0.8
    assert result.scale == 1.2


def test_opacity_multiplicative():
    base = CaptionVisualState(opacity=0.5)
    result = compose_animations(base, [CaptionVisualState(opacity=0.5)])
    assert result.opacity == 0.25


def test_scale_multiplicative():
    base = CaptionVisualState(scale=2.0)
    result = compose_animations(base, [CaptionVisualState(scale=1.5)])
    assert result.scale == 3.0


def test_translate_additive():
    base = CaptionVisualState(translate_x=10, translate_y=5)
    result = compose_animations(base, [CaptionVisualState(translate_x=20, translate_y=-3)])
    assert result.translate_x == 30
    assert result.translate_y == 2


def test_rotation_additive():
    base = CaptionVisualState(rotation=45)
    result = compose_animations(base, [CaptionVisualState(rotation=15)])
    assert result.rotation == 60


def test_blur_glow_additive_and_clamped():
    base = CaptionVisualState(blur=2, glow=3)
    result = compose_animations(base, [CaptionVisualState(blur=-5, glow=4)])
    assert result.blur == 0
    assert result.glow == 7


def test_letter_spacing_additive():
    base = CaptionVisualState(letter_spacing=2)
    result = compose_animations(base, [CaptionVisualState(letter_spacing=3)])
    assert result.letter_spacing == 5


def test_highlight_progress_maximum():
    base = CaptionVisualState(highlight_progress=0.2)
    result = compose_animations(base, [CaptionVisualState(highlight_progress=0.8)])
    assert result.highlight_progress == 0.8


def test_reveal_progress_maximum():
    base = CaptionVisualState(reveal_progress=0.1)
    result = compose_animations(base, [CaptionVisualState(reveal_progress=0.9)])
    assert result.reveal_progress == 0.9


def test_input_not_mutated():
    base = CaptionVisualState(opacity=1.0)
    contribution = CaptionVisualState(opacity=0.5)
    compose_animations(base, [contribution])
    assert base.opacity == 1.0
    assert contribution.opacity == 0.5
