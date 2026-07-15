# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Frame-state evaluator: the canonical animation calculation API."""
from __future__ import annotations

from backend.caption_core.active_word import find_active_word_index
from backend.caption_core.animation.composition import compose_animations
from backend.caption_core.animation.context import AnimationContext, frame_to_ms
from backend.caption_core.animation.events import _is_active_word, is_event_active
from backend.caption_core.animation.registry import dispatch_animation
from backend.caption_core.animation.state import CaptionVisualState
from backend.caption_core.models import CaptionAnimation, CaptionPreset, CaptionSegment, CaptionWord


def _trigger_time_ms(trigger: str, word: CaptionWord, segment: CaptionSegment) -> int:
    """Return the absolute time at which ``trigger`` fires."""
    if trigger == "WORD_ENTER":
        return word.start_ms
    if trigger == "WORD_EXIT":
        return word.end_ms
    if trigger == "WORD_ACTIVE":
        return word.start_ms
    if trigger == "SEGMENT_ENTER":
        return segment.start_ms
    if trigger == "SEGMENT_EXIT":
        return segment.end_ms
    return word.start_ms


def _collect_applicable_contexts(
    word: CaptionWord,
    word_index: int,
    segment: CaptionSegment,
    preset: CaptionPreset,
    frame: int,
    fps: float,
) -> list[AnimationContext]:
    """Build the ordered list of active ``AnimationContext`` objects for ``word``."""
    current_time_ms = frame_to_ms(frame, fps)
    active_word_index = find_active_word_index(segment.words, current_time_ms)

    contexts: list[AnimationContext] = []

    def add(animation: CaptionAnimation, trigger: str):
        contexts.append(
            AnimationContext.from_word(
                word=word,
                word_index=word_index,
                active_word_index=active_word_index,
                segment=segment,
                animation_config=animation,
                frame=frame,
                fps=fps,
                trigger=trigger,
                trigger_time_ms=_trigger_time_ms(trigger, word, segment),
            )
        )

    if preset.entry_animation is not None:
        if is_event_active("WORD_ENTER", word, segment, current_time_ms, preset.entry_animation):
            add(preset.entry_animation, "WORD_ENTER")

    if preset.active_word_animation is not None:
        if is_event_active(
            "WORD_ACTIVE",
            word,
            segment,
            current_time_ms,
            preset.active_word_animation,
            word_index=word_index,
            active_word_index=active_word_index,
        ):
            add(preset.active_word_animation, "WORD_ACTIVE")

    if preset.exit_animation is not None:
        if is_event_active("WORD_EXIT", word, segment, current_time_ms, preset.exit_animation):
            add(preset.exit_animation, "WORD_EXIT")

    for effect in preset.effects:
        trigger = str(effect.parameters.get("trigger", "WORD_ACTIVE")).upper()
        kwargs = {}
        if trigger == "WORD_ACTIVE":
            kwargs = {"word_index": word_index, "active_word_index": active_word_index}
        if is_event_active(trigger, word, segment, current_time_ms, effect, **kwargs):
            add(effect, trigger)

    return contexts


def evaluate_caption_word_state(
    word: CaptionWord,
    word_index: int,
    segment: CaptionSegment,
    preset: CaptionPreset,
    frame: int,
    fps: float,
) -> CaptionVisualState:
    """Return the deterministic visual state of ``word`` at ``frame``/``fps``.

    This is the canonical animation calculation API. It is renderer-independent
    and depends only on caption timing, the preset, frame, and fps.

    A word is visible (base opacity ``1``) when it is the active word or when
    an enter/exit/segment event is currently affecting it. Otherwise the base
    opacity is ``0`` so inactive words stay hidden for word-by-word presets.
    """
    current_time_ms = frame_to_ms(frame, fps)
    active_word_index = find_active_word_index(segment.words, current_time_ms)
    contexts = _collect_applicable_contexts(word, word_index, segment, preset, frame, fps)
    contributions = [dispatch_animation(ctx) for ctx in contexts]

    has_non_active_event = any(ctx.trigger != "WORD_ACTIVE" for ctx in contexts)
    if active_word_index is not None:
        is_active = active_word_index == word_index
    else:
        # At exact boundaries/zero-duration markers no interval covers the time,
        # but the inclusive animation layer may still consider this word active.
        is_active = _is_active_word(word, current_time_ms)
    base_opacity = 1.0 if (is_active or has_non_active_event) else 0.0
    base = CaptionVisualState(opacity=base_opacity)
    return compose_animations(base, contributions)
