# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Renderer-independent animation primitive implementations.

Every primitive is a pure function ``AnimationContext -> CaptionVisualState``.
No wall-clock time or randomness is used."""
from __future__ import annotations

import hashlib
import math
import unicodedata
from typing import Iterator

from backend.caption_core.animation.context import AnimationContext
from backend.caption_core.animation.easing import calculate_progress, get_easing_function
from backend.caption_core.animation.state import CaptionVisualState


def _effective_duration_ms(ctx: AnimationContext) -> int:
    """Return the animation duration, respecting ``duration_mode`` overrides."""
    mode = ctx.animation_config.parameters.get("duration_mode", "fixed")
    if mode == "word":
        return max(0, ctx.word.duration_ms())
    if mode == "segment":
        return max(0, ctx.segment.duration_ms())
    return ctx.animation_config.duration_ms


def _animation_start_ms(ctx: AnimationContext) -> int:
    """Return the absolute start time for the current animation instance."""
    return ctx.trigger_time_ms + ctx.animation_config.delay_ms


def _animation_progress(ctx: AnimationContext) -> float:
    """Return the eased normalized progress for the current animation."""
    start_ms = _animation_start_ms(ctx)
    duration_ms = _effective_duration_ms(ctx)
    t = calculate_progress(start_ms, duration_ms, ctx.current_time_ms)
    return get_easing_function(ctx.animation_config.easing)(t)


def evaluate_fade(ctx: AnimationContext) -> CaptionVisualState:
    """Fade in or out.

    Parameters:
        direction (str): ``"in"`` (default) or ``"out"``.
        intensity (float): retained for future use; does not change opacity math.
    """
    params = ctx.animation_config.parameters
    direction = str(params.get("direction", "in")).lower()
    t = _animation_progress(ctx)
    if direction == "out":
        opacity = 1.0 - t
    else:
        opacity = t
    return CaptionVisualState(opacity=opacity)


def evaluate_scale(ctx: AnimationContext) -> CaptionVisualState:
    """Scale from ``from_scale`` to ``to_scale``.

    Parameters:
        from_scale (float): starting scale multiplier, default ``1``.
        to_scale (float): ending scale multiplier, default ``2``.
    """
    params = ctx.animation_config.parameters
    from_scale = float(params.get("from_scale", 1.0))
    to_scale = float(params.get("to_scale", 2.0))
    t = _animation_progress(ctx)
    return CaptionVisualState(scale=from_scale + (to_scale - from_scale) * t)


def _spring_displacement(ctx: AnimationContext) -> float:
    """Deterministic damped-harmonic-oscillator displacement.

    Uses the standard underdamped solution:

        x(t) = A * exp(-zeta * omega * t) * sin(omega_d * t)

    where ``omega = sqrt(k/m)``, ``zeta = c / (2*sqrt(m*k))``,
    ``omega_d = omega * sqrt(1 - zeta^2)``.

    Parameters:
        stiffness (float): spring constant ``k``, default ``170``.
        damping (float): damping coefficient ``c``, default ``20``.
        mass (float): mass ``m``, default ``1``.
        amplitude (float): initial displacement ``A``, default ``0.4``.

    Invalid or overdamped parameters are protected against by clamping the
    damping ratio to ``0.99`` and ensuring ``omega`` is positive.
    """
    params = ctx.animation_config.parameters
    stiffness = float(params.get("stiffness", 170.0))
    damping = float(params.get("damping", 20.0))
    mass = float(params.get("mass", 1.0))
    amplitude = float(params.get("amplitude", 0.4))

    if mass <= 0.0:
        mass = 1.0
    if stiffness <= 0.0:
        stiffness = 1.0
    if damping < 0.0:
        damping = 0.0
    if amplitude < 0.0:
        amplitude = 0.0

    omega = math.sqrt(stiffness / mass)
    zeta = damping / (2.0 * math.sqrt(mass * stiffness))

    # Guard against critical/overdamping and division by zero.
    if zeta >= 1.0:
        zeta = 0.99
    if omega <= 0.0:
        omega = 1.0

    omega_d = omega * math.sqrt(max(0.0, 1.0 - zeta * zeta))

    start_ms = _animation_start_ms(ctx)
    elapsed_s = max(0.0, (ctx.current_time_ms - start_ms) / 1000.0)

    if omega_d < 1e-6:
        # Avoid very slow oscillations; fall back to exponential decay.
        return amplitude * math.exp(-zeta * omega * elapsed_s)

    return amplitude * math.exp(-zeta * omega * elapsed_s) * math.sin(omega_d * elapsed_s)


def evaluate_spring(ctx: AnimationContext) -> CaptionVisualState:
    """Generic spring oscillator primitive.

    Parameters:
        property (str): ``"scale"`` (default) or ``"translate_y"``.
        stiffness, damping, mass, amplitude: passed to ``_spring_displacement``.
    """
    displacement = _spring_displacement(ctx)
    prop = str(ctx.animation_config.parameters.get("property", "scale")).lower()
    if prop == "translate_y":
        return CaptionVisualState(translate_y=displacement)
    return CaptionVisualState(scale=1.0 + displacement)


def evaluate_bounce(ctx: AnimationContext) -> CaptionVisualState:
    """Bounce primitive backed by the spring displacement function.

    Parameters:
        direction (str): ``"vertical"`` (default) or ``"scale"``.
        stiffness, damping, mass, amplitude: passed through.
    """
    displacement = _spring_displacement(ctx)
    direction = str(ctx.animation_config.parameters.get("direction", "vertical")).lower()
    if direction == "scale":
        return CaptionVisualState(scale=1.0 + displacement)
    return CaptionVisualState(translate_y=displacement)


def _hash_seed(*parts: str) -> bytes:
    """Deterministic 32-byte digest for a string seed."""
    seed = ":".join(parts)
    return hashlib.sha256(seed.encode("utf-8")).digest()


def _bytes_to_floats(data: bytes, count: int) -> list[float]:
    """Convert SHA-256 digest into ``count`` floats in ``[-1, 1]``.

    Each float uses two bytes interpreted as a signed 16-bit integer.
    """
    values: list[float] = []
    for i in range(count):
        offset = (i * 2) % len(data)
        raw = int.from_bytes(data[offset : offset + 2], "big", signed=True)
        values.append(raw / 32767.0)
    return values


def evaluate_glitch(ctx: AnimationContext) -> CaptionVisualState:
    """Deterministic glitch jitter.

    The seed is derived from ``word.id``, ``word_index``, and ``frame`` so the
    same word and frame always yields the same output. ``frequency`` controls
    how many frames the jitter values persist (default ``1``).

    Parameters:
        intensity (float): overall strength multiplier, default ``1``.
        frequency (int): frames per jitter slot, default ``1``.
        seed_offset (str): arbitrary salt for deterministic variation.
    """
    params = ctx.animation_config.parameters
    intensity = float(params.get("intensity", 1.0))
    frequency = int(params.get("frequency", 1))
    seed_offset = str(params.get("seed_offset", ""))
    if frequency <= 0:
        frequency = 1

    slot = ctx.frame // frequency
    digest = _hash_seed(seed_offset, str(ctx.word_index), str(ctx.word.id), str(slot))
    values = _bytes_to_floats(digest, 8)

    tx = values[0] * intensity * 10.0
    ty = values[1] * intensity * 10.0
    rotation = values[2] * intensity * 15.0
    opacity_jitter = values[3]
    glow_jitter = abs(values[4])
    blur_jitter = abs(values[5])

    # Opacity disturbance multiplies the base, so keep it near 1.
    opacity = max(0.0, 1.0 - abs(opacity_jitter) * intensity * 0.5)
    glow = glow_jitter * intensity * 20.0
    blur = blur_jitter * intensity * 10.0

    return CaptionVisualState(
        translate_x=tx,
        translate_y=ty,
        rotation=rotation,
        opacity=opacity,
        glow=glow,
        blur=blur,
    )


def _grapheme_clusters(text: str) -> Iterator[str]:
    """Yield simple Unicode grapheme clusters.

    Combines a base character with subsequent combining marks and variation
    selectors. This is safer than byte splitting and handles common accented
    scripts; complex Emoji ZWJ sequences are treated as the code points they
    contain, which is acceptable for caption rendering.
    """
    cluster = ""
    for char in text:
        category = unicodedata.category(char)
        cp = ord(char)
        is_combiner = category in ("Mn", "Mc", "Me")
        is_variation = (0xFE00 <= cp <= 0xFE0F) or (0xE0100 <= cp <= 0xE01EF)
        if is_combiner or is_variation:
            cluster += char
        else:
            if cluster:
                yield cluster
            cluster = char
    if cluster:
        yield cluster


def grapheme_count(text: str) -> int:
    """Return the number of user-perceived characters in ``text``."""
    return sum(1 for _ in _grapheme_clusters(text))


def visible_character_count(text: str, reveal_progress: float) -> int:
    """Return how many grapheme clusters of ``text`` are revealed.

    ``reveal_progress`` is clamped to ``[0, 1]``.
    """
    total = grapheme_count(text)
    if total == 0:
        return 0
    progress = min(1.0, max(0.0, reveal_progress))
    return min(total, max(0, int(total * progress + 0.5)))


def visible_text(text: str, reveal_progress: float) -> str:
    """Return the substring of ``text`` containing the revealed grapheme clusters."""
    count = visible_character_count(text, reveal_progress)
    clusters = list(_grapheme_clusters(text))
    return "".join(clusters[:count])


def evaluate_typewriter(ctx: AnimationContext) -> CaptionVisualState:
    """Typewriter reveal progress.

    The actual character slicing is exposed through ``visible_text`` / ``visible_character_count``;
    this primitive only computes ``reveal_progress``.

    Parameters:
        duration_ms (int): from the animation config.
        delay_ms (int): from the animation config.
        easing (CaptionEasing): from the animation config.
    """
    t = _animation_progress(ctx)
    return CaptionVisualState(reveal_progress=t)


def evaluate_karaoke(ctx: AnimationContext) -> CaptionVisualState:
    """Karaoke-style highlight progress over the active word.

    Parameters:
        duration_mode (str): ``"word"`` (default) uses the word duration,
            ``"fixed"`` uses ``animation_config.duration_ms``.
    """
    params = ctx.animation_config.parameters
    duration_ms = _effective_duration_ms(ctx)
    start_ms = _animation_start_ms(ctx)

    if duration_ms <= 0:
        # Zero-duration word: highlighted if we are at/past the start.
        progress = 1.0 if ctx.current_time_ms >= start_ms else 0.0
    else:
        progress = calculate_progress(start_ms, duration_ms, ctx.current_time_ms)

    progress = get_easing_function(ctx.animation_config.easing)(progress)
    return CaptionVisualState(highlight_progress=progress)
