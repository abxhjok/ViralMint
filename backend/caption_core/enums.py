# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Enumerations used by the caption core."""
from enum import Enum


class CaptionCategory(str, Enum):
    """Preset categories aligned with short-form content use cases."""

    VIRAL = "viral"
    PODCAST = "podcast"
    CLEAN = "clean"
    STORY = "story"
    GAMING = "gaming"
    DOCUMENTARY = "documentary"
    EDUCATIONAL = "educational"
    MOTIVATION = "motivation"
    MEME = "meme"
    HIGH_ENERGY = "high_energy"
    KARAOKE = "karaoke"
    CINEMATIC = "cinematic"


class CaptionAnimationType(str, Enum):
    """Supported caption animation types.

    Only the animation *configuration* lives here. Actual rendering is a
    future-phase concern (Phase 1 stops at the model/timing layer).
    """

    FADE = "fade"
    SCALE = "scale"
    SPRING = "spring"
    BOUNCE = "bounce"
    SLIDE = "slide"
    ZOOM = "zoom"
    GLITCH = "glitch"
    TYPEWRITER = "typewriter"
    KARAOKE = "karaoke"
    EXPLOSIVE = "explosive"
    GLOW = "glow"
    POP = "pop"


class CaptionEasing(str, Enum):
    """Animation easing curves."""

    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    SPRING = "spring"
