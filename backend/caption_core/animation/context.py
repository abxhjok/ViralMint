# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""AnimationContext: deterministic render-time context for one word/frame."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.caption_core.models import CaptionAnimation, CaptionSegment, CaptionWord


def frame_to_ms(frame: int, fps: float) -> int:
    """Convert a frame number to the wall-clock milliseconds at that frame.

    Frame 0 starts at time 0. Result is rounded to the nearest millisecond.
    This is the only frame/time conversion used by the animation engine.
    """
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    if frame < 0:
        raise ValueError(f"frame must be non-negative, got {frame}")
    return int(frame * 1000.0 / fps + 0.5)


def ms_to_frame(ms: int, fps: float) -> int:
    """Return the frame index whose start time is nearest to ``ms``.

    Rounding to the nearest frame keeps ``ms_to_frame(frame_to_ms(frame))``
    consistent for the representative frames used by the animation engine.
    """
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    if ms < 0:
        return 0
    return int(ms * fps / 1000.0 + 0.5)


class AnimationContext(BaseModel):
    """All information needed to evaluate a single animation primitive at a frame.

    No real-time or wall-clock values are stored; ``current_time_ms`` is always
    derived from ``frame`` and ``fps``.
    """

    frame: int = Field(ge=0)
    fps: float = Field(gt=0.0)
    current_time_ms: int = Field(ge=0)
    word: CaptionWord
    word_index: int = Field(ge=0)
    active_word_index: Optional[int] = None
    segment: CaptionSegment
    animation_config: CaptionAnimation
    trigger: str = "WORD_ACTIVE"
    trigger_time_ms: int = Field(default=0, ge=0)

    @field_validator("trigger")
    @classmethod
    def _trigger_must_be_known(cls, value: str) -> str:
        allowed = {"SEGMENT_ENTER", "SEGMENT_EXIT", "WORD_ENTER", "WORD_ACTIVE", "WORD_EXIT"}
        if value not in allowed:
            raise ValueError(f"Unknown trigger {value!r}; expected one of {allowed}")
        return value

    @classmethod
    def from_word(
        cls,
        word: CaptionWord,
        word_index: int,
        active_word_index: Optional[int],
        segment: CaptionSegment,
        animation_config: CaptionAnimation,
        frame: int,
        fps: float,
        trigger: str = "WORD_ACTIVE",
        trigger_time_ms: Optional[int] = None,
    ) -> "AnimationContext":
        current_time_ms = frame_to_ms(frame, fps)
        if trigger_time_ms is None:
            trigger_time_ms = word.start_ms
        return cls(
            frame=frame,
            fps=fps,
            current_time_ms=current_time_ms,
            word=word,
            word_index=word_index,
            active_word_index=active_word_index,
            segment=segment,
            animation_config=animation_config,
            trigger=trigger,
            trigger_time_ms=trigger_time_ms,
        )
