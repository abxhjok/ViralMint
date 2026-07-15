# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Frame-based, deterministic caption animation engine.

All animation state is a pure function of ``(frame, fps, caption timing, preset)``.
No wall-clock time, browser timers, or FFmpeg/ASS/React is used at the
evaluation layer.
"""
from backend.caption_core.animation.context import AnimationContext, frame_to_ms
from backend.caption_core.animation.evaluator import evaluate_caption_word_state
from backend.caption_core.animation.presets import get_preset
from backend.caption_core.animation.registry import ANIMATION_PRIMITIVES, dispatch_animation
from backend.caption_core.animation.state import CaptionVisualState

__all__ = [
    "AnimationContext",
    "ANIMATION_PRIMITIVES",
    "CaptionVisualState",
    "dispatch_animation",
    "evaluate_caption_word_state",
    "frame_to_ms",
    "get_preset",
]
