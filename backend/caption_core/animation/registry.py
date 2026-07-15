# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Animation primitive registry and dispatcher."""
from __future__ import annotations

from backend.caption_core.animation.context import AnimationContext
from backend.caption_core.animation.primitives import (
    evaluate_bounce,
    evaluate_fade,
    evaluate_glitch,
    evaluate_karaoke,
    evaluate_scale,
    evaluate_spring,
    evaluate_typewriter,
)
from backend.caption_core.animation.state import CaptionVisualState
from backend.caption_core.enums import CaptionAnimationType


AnimationPrimitive = "callable[[AnimationContext], CaptionVisualState]"

ANIMATION_PRIMITIVES: dict[str, AnimationPrimitive] = {
    "fade": evaluate_fade,
    "scale": evaluate_scale,
    "spring": evaluate_spring,
    "bounce": evaluate_bounce,
    "glitch": evaluate_glitch,
    "typewriter": evaluate_typewriter,
    "karaoke": evaluate_karaoke,
}


def dispatch_animation(ctx: AnimationContext) -> CaptionVisualState:
    """Evaluate ``ctx.animation_config`` through the registered primitive."""
    type_value = ctx.animation_config.type
    anim_type = type_value.value if isinstance(type_value, CaptionAnimationType) else str(type_value)
    primitive = ANIMATION_PRIMITIVES.get(anim_type)
    if primitive is None:
        known = ", ".join(sorted(ANIMATION_PRIMITIVES.keys()))
        raise ValueError(f"Unknown animation type {anim_type!r}. Known: {known}")
    return primitive(ctx)
