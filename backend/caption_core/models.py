# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Validated Pydantic models for the deterministic caption core."""
from __future__ import annotations

import re
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.caption_core.enums import CaptionAnimationType, CaptionCategory, CaptionEasing


def _new_id() -> str:
    return str(uuid4())


def _to_ass_color(color: str) -> str:
    """Convert #RRGGBB or #AARRGGBB (and &H pass-through) to ASS BGR &H format.

    ASS colors are stored as ``&HAABBGGRR``. The alpha byte is ``00`` for
    fully opaque unless an 8-character hex string supplies one.
    """
    color = (color or "#FFFFFF").strip()
    if color.startswith("&H"):
        return color
    if not color.startswith("#"):
        raise ValueError(f"Unsupported color format: {color!r}. Expected hex (#RRGGBB) or ASS (&H...).")
    hex_part = color[1:]
    if len(hex_part) == 6:
        r, g, b = hex_part[0:2], hex_part[2:4], hex_part[4:6]
        return f"&H00{b}{g}{r}"
    if len(hex_part) == 8:
        a, r, g, b = hex_part[0:2], hex_part[2:4], hex_part[4:6], hex_part[6:8]
        return f"&H{a}{b}{g}{r}"
    raise ValueError(f"Unsupported hex color length: {color!r}")


class CaptionWord(BaseModel):
    """A single timed word.

    Timestamps are in milliseconds. ``end_ms`` may equal ``start_ms`` to
    represent a zero-duration marker word.
    """

    id: str = Field(default_factory=_new_id)
    text: str
    start_ms: int = Field(ge=0)
    end_ms: int
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    speaker_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    emphasis: bool = False

    @field_validator("text")
    @classmethod
    def _text_must_be_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("CaptionWord.text cannot be empty")
        return value

    @model_validator(mode="after")
    def _end_must_not_be_before_start(self) -> "CaptionWord":
        if self.end_ms < self.start_ms:
            raise ValueError(
                f"CaptionWord end_ms ({self.end_ms}) must be >= start_ms ({self.start_ms})"
            )
        return self

    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms

    def is_zero_duration(self) -> bool:
        return self.end_ms == self.start_ms

    def model_copy(self, **kwargs: Any) -> "CaptionWord":
        return super().model_copy(**kwargs)


class CaptionSegment(BaseModel):
    """A contiguous display segment containing an ordered list of words."""

    id: str = Field(default_factory=_new_id)
    start_ms: int = Field(default=0, ge=0)
    end_ms: int = Field(default=0, ge=0)
    words: list[CaptionWord] = Field(default_factory=list)
    speaker_id: Optional[str] = None

    @model_validator(mode="after")
    def _sync_from_words(self) -> "CaptionSegment":
        if self.words:
            # Preserve stable order; sort by start, then end, then original index.
            indexed = list(enumerate(self.words))
            indexed.sort(key=lambda item: (item[1].start_ms, item[1].end_ms, item[0]))
            self.words = [item[1] for item in indexed]
            self.start_ms = min(self.start_ms, self.words[0].start_ms)
            self.end_ms = max(self.end_ms, self.words[-1].end_ms)
        if self.end_ms < self.start_ms:
            raise ValueError(
                f"CaptionSegment end_ms ({self.end_ms}) must be >= start_ms ({self.start_ms})"
            )
        return self

    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


class CaptionStyle(BaseModel):
    """A caption style definition.

    This model stores both ASS-compatible properties and future animation
    properties. Properties that cannot be represented directly by the current
    ASS renderer are preserved for later renderers but ignored by the ASS
    bridge (see ``to_ass_style_dict``).
    """

    id: str = Field(default_factory=_new_id)
    name: str
    font_family: str = "Arial"
    font_size_portrait: int = Field(default=56, ge=1)
    font_size_landscape: int = Field(default=42, ge=1)
    font_weight: Literal["normal", "bold"] = "bold"
    text_color: str = "#FFFFFF"
    active_word_color: str = "#FFFF00"
    stroke_color: str = "#000000"
    stroke_width: int = Field(default=3, ge=0)
    shadow_color: Optional[str] = None
    shadow_blur: float = Field(default=0.0, ge=0.0)
    shadow_offset_x: float = 0.0
    shadow_offset_y: float = 1.0
    background_color: Optional[str] = None
    background_opacity: float = Field(default=1.0, ge=0.0, le=1.0)
    alignment: int = Field(default=5, ge=1, le=9)
    letter_spacing: float = 0.0
    line_height: float = Field(default=1.2, ge=0.0)
    text_transform: Literal["none", "uppercase", "lowercase", "capitalize"] = "none"
    words_per_group: int = Field(default=3, ge=1)
    margin_v: int = Field(default=80, ge=0)

    @field_validator("text_color", "active_word_color", "stroke_color")
    @classmethod
    def _colors_must_be_valid(cls, value: str) -> str:
        _to_ass_color(value)
        return value

    @field_validator("name")
    @classmethod
    def _name_must_be_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("CaptionStyle.name cannot be empty")
        return value

    def is_bold(self) -> bool:
        return self.font_weight == "bold"

    def to_ass_style_dict(self) -> dict[str, Any]:
        """Return a dict compatible with ``backend.services.caption_service`` ASS rendering.

        Unsupported properties (``shadow_blur``, ``background_color``,
        ``letter_spacing``, ``line_height``, ``text_transform``, etc.) are not
        included in the returned dict because the current ASS renderer does not
        implement them.
        """
        font = self.font_family
        if self.is_bold() and not re.search(r"\bbold\b", font, re.IGNORECASE):
            font = f"{font} Bold"

        # Map shadow offset to the integer depth value used by the ASS renderer.
        shadow_depth = int(max(abs(self.shadow_offset_x), abs(self.shadow_offset_y)))

        return {
            "font": font,
            "font_size_portrait": self.font_size_portrait,
            "font_size_landscape": self.font_size_landscape,
            "primary_color": _to_ass_color(self.text_color),
            "highlight_color": _to_ass_color(self.active_word_color),
            "outline_color": _to_ass_color(self.stroke_color),
            "outline_width": self.stroke_width,
            "shadow_depth": shadow_depth,
            "alignment": self.alignment,
            "margin_v": self.margin_v,
            "words_per_group": self.words_per_group,
        }


class CaptionAnimation(BaseModel):
    """A reusable animation configuration.

    This is data only — no rendering code. It is used for entry, active-word,
    exit, and effect animations.
    """

    id: str = Field(default_factory=_new_id)
    type: CaptionAnimationType = CaptionAnimationType.FADE
    duration_ms: int = Field(default=300, ge=0)
    delay_ms: int = Field(default=0, ge=0)
    easing: CaptionEasing = CaptionEasing.LINEAR
    spring: Optional[dict] = None
    intensity: float = Field(default=1.0, ge=0.0, le=2.0)
    parameters: dict = Field(default_factory=dict)


class CaptionLayout(BaseModel):
    """Layout and segmentation constraints for a preset."""

    max_words_per_line: int = Field(default=3, ge=1)
    max_chars_per_line: Optional[int] = Field(default=None, ge=1)
    max_line_duration_ms: Optional[int] = Field(default=None, ge=1)
    max_gap_ms: Optional[int] = Field(default=None, ge=0)
    position: str = "center-center"
    line_spacing: float = Field(default=1.2, ge=0.0)
    padding_x: int = Field(default=0, ge=0)
    padding_y: int = Field(default=0, ge=0)


class CaptionPreset(BaseModel):
    """A complete caption preset: style + layout + animations + rules."""

    id: str = Field(default_factory=_new_id)
    name: str
    category: CaptionCategory = CaptionCategory.VIRAL
    description: Optional[str] = None
    style: CaptionStyle
    layout: CaptionLayout = Field(default_factory=CaptionLayout)
    entry_animation: Optional[CaptionAnimation] = None
    active_word_animation: Optional[CaptionAnimation] = None
    exit_animation: Optional[CaptionAnimation] = None
    effects: list[CaptionAnimation] = Field(default_factory=list)
    tag_rules: list[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _name_must_be_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("CaptionPreset.name cannot be empty")
        return value
