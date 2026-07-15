# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Five engine-verification preset configurations.

These are not the final 60-preset library; they exercise the animation engine
with common short-form caption styles.
"""
from __future__ import annotations

from backend.caption_core.animation.state import CaptionVisualState
from backend.caption_core.enums import CaptionAnimationType, CaptionCategory
from backend.caption_core.models import CaptionAnimation, CaptionLayout, CaptionPreset, CaptionStyle


def _default_style(name: str = "Preset") -> CaptionStyle:
    return CaptionStyle(name=name)


def bounce_preset() -> CaptionPreset:
    """Vertical spring bounce on the active word."""
    return CaptionPreset(
        name="Bounce",
        category=CaptionCategory.HIGH_ENERGY,
        description="Vertical spring bounce on each active word.",
        style=_default_style("Bounce"),
        layout=CaptionLayout(max_words_per_line=3),
        active_word_animation=CaptionAnimation(
            type=CaptionAnimationType.BOUNCE,
            duration_ms=400,
            parameters={"direction": "vertical", "stiffness": 300, "damping": 15, "amplitude": 15},
        ),
    )


def explosive_preset() -> CaptionPreset:
    """Explosive entry: fade in while scaling up with a bounce overshoot."""
    return CaptionPreset(
        name="Explosive",
        category=CaptionCategory.VIRAL,
        description="Fade-in + scale-up with a spring overshoot on word entry.",
        style=_default_style("Explosive"),
        layout=CaptionLayout(max_words_per_line=3),
        entry_animation=CaptionAnimation(
            type=CaptionAnimationType.FADE,
            duration_ms=300,
            parameters={"direction": "in"},
        ),
        active_word_animation=CaptionAnimation(
            type=CaptionAnimationType.SCALE,
            duration_ms=400,
            parameters={"from_scale": 0.6, "to_scale": 1.1, "easing": "ease_out"},
        ),
        effects=[
            CaptionAnimation(
                type=CaptionAnimationType.BOUNCE,
                duration_ms=400,
                parameters={
                    "trigger": "WORD_ENTER",
                    "direction": "scale",
                    "stiffness": 400,
                    "damping": 20,
                    "amplitude": 0.4,
                },
            ),
        ],
    )


def glitch_preset() -> CaptionPreset:
    """Active-word glitch with a subtle fade-in."""
    return CaptionPreset(
        name="Glitch",
        category=CaptionCategory.MEME,
        description="Deterministic glitch jitter while the word is active.",
        style=_default_style("Glitch"),
        layout=CaptionLayout(max_words_per_line=4),
        active_word_animation=CaptionAnimation(
            type=CaptionAnimationType.FADE,
            duration_ms=100,
            parameters={"direction": "in"},
        ),
        effects=[
            CaptionAnimation(
                type=CaptionAnimationType.GLITCH,
                duration_ms=300,
                parameters={"intensity": 0.8, "frequency": 2, "seed_offset": "glitch"},
            ),
        ],
    )


def typewriter_preset() -> CaptionPreset:
    """Character-by-character typewriter reveal."""
    return CaptionPreset(
        name="Typewriter",
        category=CaptionCategory.DOCUMENTARY,
        description="Typewriter-style character reveal on word entry.",
        style=_default_style("Typewriter"),
        layout=CaptionLayout(max_words_per_line=5),
        active_word_animation=CaptionAnimation(
            type=CaptionAnimationType.TYPEWRITER,
            duration_ms=500,
            parameters={"duration_mode": "word"},
        ),
    )


def karaoke_preset() -> CaptionPreset:
    """Karaoke highlight that sweeps across the active word."""
    return CaptionPreset(
        name="Karaoke",
        category=CaptionCategory.KARAOKE,
        description="Highlight sweep synchronized to the active word duration.",
        style=_default_style("Karaoke"),
        layout=CaptionLayout(max_words_per_line=3),
        active_word_animation=CaptionAnimation(
            type=CaptionAnimationType.KARAOKE,
            duration_ms=0,
            parameters={"duration_mode": "word"},
        ),
    )


def get_preset(name: str) -> CaptionPreset:
    """Return one of the five built-in engine-verification presets."""
    presets = {
        "bounce": bounce_preset,
        "explosive": explosive_preset,
        "glitch": glitch_preset,
        "typewriter": typewriter_preset,
        "karaoke": karaoke_preset,
    }
    factory = presets.get(name.lower())
    if factory is None:
        raise ValueError(f"Unknown preset {name!r}; known: {list(presets.keys())}")
    return factory()
