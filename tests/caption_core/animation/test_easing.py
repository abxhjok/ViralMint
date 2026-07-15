# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for easing and progress utilities."""
import pytest

from backend.caption_core.animation.easing import (
    calculate_progress,
    clamp01,
    ease_in,
    ease_in_out,
    ease_linear,
    ease_out,
    get_easing_function,
    lerp,
)
from backend.caption_core.enums import CaptionEasing


def test_clamp01():
    assert clamp01(-0.5) == 0.0
    assert clamp01(0.5) == 0.5
    assert clamp01(1.5) == 1.0


def test_lerp():
    assert lerp(0, 100, 0.25) == 25.0
    assert lerp(0, 100, -0.1) == 0.0
    assert lerp(0, 100, 1.1) == 100.0


@pytest.mark.parametrize("ease_fn,expected", [
    (ease_linear, 0.25),
    (ease_in, 0.0625),
    (ease_out, 0.4375),
])
def test_ease_at_quarter(ease_fn, expected):
    assert ease_fn(0.25) == pytest.approx(expected)


def test_ease_in_out_symmetric():
    assert ease_in_out(0.0) == 0.0
    assert ease_in_out(0.5) == 0.5
    assert ease_in_out(1.0) == 1.0


def test_calculate_progress_before_and_after():
    assert calculate_progress(100, 200, 50) == 0.0
    assert calculate_progress(100, 200, 300) == 1.0


def test_calculate_progress_inside():
    assert calculate_progress(100, 200, 150) == 0.25
    assert calculate_progress(100, 200, 200) == 0.5


def test_calculate_progress_zero_duration():
    assert calculate_progress(100, 0, 50) == 0.0
    assert calculate_progress(100, 0, 100) == 1.0
    assert calculate_progress(100, 0, 200) == 1.0


def test_calculate_progress_negative_time():
    assert calculate_progress(100, 200, -100) == 0.0


def test_get_easing_function():
    assert get_easing_function(CaptionEasing.LINEAR) is ease_linear
    assert get_easing_function(CaptionEasing.EASE_IN) is ease_in
    assert get_easing_function(CaptionEasing.EASE_OUT) is ease_out
    assert get_easing_function(CaptionEasing.EASE_IN_OUT) is ease_in_out


def test_get_easing_function_spring_not_supported():
    with pytest.raises(ValueError):
        get_easing_function(CaptionEasing.SPRING)
