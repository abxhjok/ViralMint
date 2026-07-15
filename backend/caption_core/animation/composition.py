# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Composition rules for combining animation primitive contributions."""
from __future__ import annotations

from backend.caption_core.animation.state import CaptionVisualState


def _apply_contribution(base: CaptionVisualState, contribution: CaptionVisualState) -> CaptionVisualState:
    """Combine a single contribution onto a running state using documented rules."""
    return CaptionVisualState(
        opacity=base.opacity * contribution.opacity,
        scale=base.scale * contribution.scale,
        translate_x=base.translate_x + contribution.translate_x,
        translate_y=base.translate_y + contribution.translate_y,
        rotation=base.rotation + contribution.rotation,
        blur=max(0.0, base.blur + contribution.blur),
        glow=max(0.0, base.glow + contribution.glow),
        letter_spacing=base.letter_spacing + contribution.letter_spacing,
        highlight_progress=max(base.highlight_progress, contribution.highlight_progress),
        reveal_progress=max(base.reveal_progress, contribution.reveal_progress),
    )


def compose_animations(
    base: CaptionVisualState,
    contributions: list[CaptionVisualState],
) -> CaptionVisualState:
    """Compose an ordered list of primitive contributions onto a base state.

    Composition rules (applied in input order):

    - ``opacity`` → multiplicative
    - ``scale`` → multiplicative
    - ``translate_x`` / ``translate_y`` → additive
    - ``rotation`` → additive
    - ``blur`` → additive, minimum ``0`` (enforced by ``CaptionVisualState``)
    - ``glow`` → additive, minimum ``0``
    - ``letter_spacing`` → additive
    - ``highlight_progress`` → maximum
    - ``reveal_progress`` → maximum

    The input ``base`` object is never mutated. A new ``CaptionVisualState``
    instance is returned.
    """
    result = base.model_copy()
    for contribution in contributions:
        result = _apply_contribution(result, contribution)
    return result
