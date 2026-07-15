# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for the visual-state model."""
import pytest

from backend.caption_core.animation.state import CaptionVisualState


def test_defaults():
    state = CaptionVisualState()
    assert state.opacity == 1.0
    assert state.scale == 1.0
    assert state.translate_x == 0.0
    assert state.translate_y == 0.0
    assert state.rotation == 0.0
    assert state.blur == 0.0
    assert state.glow == 0.0
    assert state.letter_spacing == 0.0
    assert state.highlight_progress == 0.0
    assert state.reveal_progress == 0.0


def test_clamping():
    state = CaptionVisualState(opacity=-0.5, scale=-2.0, blur=-1.0, glow=-3.0, highlight_progress=1.5, reveal_progress=-0.1)
    assert state.opacity == 0.0
    assert state.scale == 0.0
    # blur and glow are additive deltas and may be negative until composed.
    assert state.blur == -1.0
    assert state.glow == -3.0
    assert state.highlight_progress == 1.0
    assert state.reveal_progress == 0.0


def test_model_copy_immutable():
    state = CaptionVisualState()
    copy = state.model_copy(update={"opacity": 0.5})
    assert state.opacity == 1.0
    assert copy.opacity == 0.5


def test_units_documented_in_docstring():
    assert "screen units" in CaptionVisualState.__doc__
