# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Pure easing and interpolation utilities.

All functions accept a normalized progress value ``t`` and return a normalized
output value. Inputs outside ``[0, 1]`` are clamped before the easing curve is
applied, except where noted.
"""
from __future__ import annotations

from backend.caption_core.enums import CaptionEasing


def clamp01(value: float) -> float:
    """Clamp ``value`` to the closed unit interval."""
    return min(1.0, max(0.0, value))


def lerp(start: float, end: float, t: float) -> float:
    """Linearly interpolate between ``start`` and ``end`` using progress ``t``.

    ``t`` is clamped to ``[0, 1]``.
    """
    t = clamp01(t)
    return start + (end - start) * t


def ease_linear(t: float) -> float:
    """``f(t) = t`` clamped to ``[0, 1]``."""
    return clamp01(t)


def ease_in(t: float) -> float:
    """Quadratic ease-in: ``t^2``."""
    t = clamp01(t)
    return t * t


def ease_out(t: float) -> float:
    """Quadratic ease-out: ``1 - (1 - t)^2``."""
    t = clamp01(t)
    return 1.0 - (1.0 - t) * (1.0 - t)


def ease_in_out(t: float) -> float:
    """Quadratic ease-in-out."""
    t = clamp01(t)
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0


def get_easing_function(easing: CaptionEasing):
    """Return the pure easing function for a ``CaptionEasing`` value."""
    mapping = {
        CaptionEasing.LINEAR: ease_linear,
        CaptionEasing.EASE_IN: ease_in,
        CaptionEasing.EASE_OUT: ease_out,
        CaptionEasing.EASE_IN_OUT: ease_in_out,
    }
    fn = mapping.get(easing)
    if fn is None:
        raise ValueError(f"Unsupported easing: {easing}")
    return fn


def calculate_progress(start_ms: int, duration_ms: int, current_time_ms: int) -> float:
    """Return normalized progress for an animation window.

    - ``t < 0`` (before start) returns ``0``.
    - ``0 <= t <= 1`` returns the linear progress within the window.
    - ``t > 1`` (after completion) returns ``1``.
    - ``duration_ms <= 0`` returns ``0`` if ``current_time_ms < start_ms``,
      otherwise ``1``.
    """
    if duration_ms <= 0:
        return 0.0 if current_time_ms < start_ms else 1.0
    progress = (current_time_ms - start_ms) / duration_ms
    if progress <= 0.0:
        return 0.0
    if progress >= 1.0:
        return 1.0
    return progress
