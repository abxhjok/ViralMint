# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Batch caption-preview computation and bounded caching.

The preview system is a thin orchestration layer around the canonical Phase 2
frame-state evaluator. It returns normalized visual-state data that the frontend
renders; no animation formulas are duplicated in JavaScript.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from backend.caption_core.animation.context import frame_to_ms
from backend.caption_core.animation.evaluator import evaluate_caption_word_state
from backend.caption_core.animation.presets import get_preset
from backend.caption_core.models import CaptionSegment, CaptionWord


MAX_PREVIEW_FRAMES = 180
MAX_PREVIEW_WORDS = 50
MAX_PREVIEW_DURATION_MS = 6_000


class PreviewWord(BaseModel):
    """Minimal word input for preview."""

    text: str
    start_ms: int = Field(ge=0)
    end_ms: int = Field(ge=0)

    @field_validator("end_ms")
    @classmethod
    def _end_after_start(cls, v: int, info) -> int:
        if v < info.data.get("start_ms", 0):
            raise ValueError("end_ms must be >= start_ms")
        return v


class PreviewRequest(BaseModel):
    """Validated request for a deterministic caption preview."""

    words: list[PreviewWord]
    preset_id: str
    fps: int = Field(default=30, ge=1, le=120)
    start_frame: int = Field(default=0, ge=0)
    end_frame: int = Field(default=60, ge=0)
    frame_step: int = Field(default=1, ge=1)

    @field_validator("end_frame")
    @classmethod
    def _frame_range(cls, v: int, info) -> int:
        start = info.data.get("start_frame", 0)
        step = info.data.get("frame_step", 1)
        if v < start:
            raise ValueError("end_frame must be >= start_frame")
        count = (v - start + step - 1) // max(1, step)
        if count > MAX_PREVIEW_FRAMES:
            raise ValueError(
                f"Requested {count} frames exceeds the maximum of {MAX_PREVIEW_FRAMES}. "
                f"Reduce the frame range or increase frame_step."
            )
        return v

    @field_validator("preset_id")
    @classmethod
    def _preset_known(cls, v: str) -> str:
        try:
            get_preset(v)
        except ValueError as e:
            raise ValueError(str(e)) from e
        return v


class PreviewState(BaseModel):
    """One word's deterministic visual state at one frame."""

    text: str
    word_index: int
    active: bool
    opacity: float
    scale: float
    translate_x: float
    translate_y: float
    rotation: float
    blur: float
    glow: float
    letter_spacing: float
    highlight_progress: float
    reveal_progress: float


class PreviewFrame(BaseModel):
    """All word states at a single frame."""

    frame: int
    time_ms: int
    words: list[PreviewState]


class PreviewCache:
    """Bounded LRU cache for preview results.

    Key covers caption timing/content, preset, fps, and frame range. The cache
    is process-local and bounded by both entry count and TTL so memory does not
    grow unbounded.
    """

    def __init__(self, maxsize: int = 128, ttl_seconds: float = 300.0):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, tuple[float, list[dict]]] = OrderedDict()

    def _make_key(self, request: PreviewRequest) -> str:
        payload = {
            "words": [w.model_dump() for w in request.words],
            "preset_id": request.preset_id,
            "fps": request.fps,
            "start_frame": request.start_frame,
            "end_frame": request.end_frame,
            "frame_step": request.frame_step,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    def get(self, request: PreviewRequest) -> Optional[list[dict]]:
        key = self._make_key(request)
        now = time.time()
        if key in self._cache:
            ts, value = self._cache[key]
            if now - ts <= self.ttl_seconds:
                self._cache.move_to_end(key)
                return value
            del self._cache[key]
        return None

    def set(self, request: PreviewRequest, value: list[dict]) -> None:
        key = self._make_key(request)
        now = time.time()
        self._cache[key] = (now, value)
        self._cache.move_to_end(key)
        while len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    def invalidate(self) -> None:
        self._cache.clear()


_preview_cache = PreviewCache()


def _state_to_preview_state(word: CaptionWord, word_index: int, active: bool, state) -> PreviewState:
    return PreviewState(
        text=word.text,
        word_index=word_index,
        active=active,
        opacity=state.opacity,
        scale=state.scale,
        translate_x=state.translate_x,
        translate_y=state.translate_y,
        rotation=state.rotation,
        blur=state.blur,
        glow=state.glow,
        letter_spacing=state.letter_spacing,
        highlight_progress=state.highlight_progress,
        reveal_progress=state.reveal_progress,
    )


def evaluate_preview_batch(request: PreviewRequest) -> list[dict]:
    """Compute (or fetch from cache) the preview frames for a request."""
    cached = _preview_cache.get(request)
    if cached is not None:
        return cached

    if len(request.words) > MAX_PREVIEW_WORDS:
        raise ValueError(f"Maximum {MAX_PREVIEW_WORDS} words allowed per preview")

    def _stable_id(i: int, w: PreviewWord) -> str:
        seed = f"{i}:{w.text}:{w.start_ms}:{w.end_ms}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]

    words = [
        CaptionWord(id=_stable_id(i, w), text=w.text, start_ms=w.start_ms, end_ms=w.end_ms)
        for i, w in enumerate(request.words)
    ]
    segment = CaptionSegment(words=words)
    preset = get_preset(request.preset_id)

    last_time = frame_to_ms(request.end_frame, request.fps)
    if last_time > MAX_PREVIEW_DURATION_MS:
        raise ValueError(
            f"Preview duration {last_time}ms exceeds maximum {MAX_PREVIEW_DURATION_MS}ms. "
            "Reduce end_frame or fps."
        )

    frames: list[dict] = []
    for frame in range(request.start_frame, request.end_frame + 1, request.frame_step):
        time_ms = frame_to_ms(frame, request.fps)
        word_states: list[PreviewState] = []
        for word_index, word in enumerate(words):
            state = evaluate_caption_word_state(
                word=word,
                word_index=word_index,
                segment=segment,
                preset=preset,
                frame=frame,
                fps=request.fps,
            )
            # Active is true when the word is visible at this frame.
            active = state.opacity > 0
            word_states.append(_state_to_preview_state(word, word_index, active, state))
        frames.append(PreviewFrame(frame=frame, time_ms=time_ms, words=word_states).model_dump())

    _preview_cache.set(request, frames)
    return frames
