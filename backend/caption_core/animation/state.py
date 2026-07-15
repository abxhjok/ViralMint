# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Immutable normalized visual-state model for caption animation."""
from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class CaptionVisualState(BaseModel):
    """A renderer-independent snapshot of how a single word should be drawn.

    Units are intentionally renderer-neutral:

    - ``opacity``: dimensionless, clamped ``[0, 1]``.
    - ``scale``: dimensionless multiplier around the word's base size,
      neutral default ``1``.
    - ``translate_x`` / ``translate_y``: screen units (typically logical
      pixels), relative to the word's baseline position.
    - ``rotation``: degrees.
    - ``blur``: blur radius in screen units, minimum ``0``.
    - ``glow``: glow radius / intensity in screen units, minimum ``0``.
    - ``letter_spacing``: extra spacing added between characters, screen units.
    - ``highlight_progress``: dimensionless ``[0, 1]`` for karaoke-style
      word highlighting.
    - ``reveal_progress``: dimensionless ``[0, 1]`` for typewriter-style
      character reveal.

    Values are clamped after construction so the final state is always valid,
    but intermediate contributions may be negative (e.g. reducing blur).
    """

    opacity: float = Field(default=1.0)
    scale: float = Field(default=1.0)
    translate_x: float = Field(default=0.0)
    translate_y: float = Field(default=0.0)
    rotation: float = Field(default=0.0)
    blur: float = Field(default=0.0)
    glow: float = Field(default=0.0)
    letter_spacing: float = Field(default=0.0)
    highlight_progress: float = Field(default=0.0)
    reveal_progress: float = Field(default=0.0)

    @model_validator(mode="after")
    def _clamp_values(self) -> "CaptionVisualState":
        # Normalized [0, 1] properties.
        self.opacity = min(1.0, max(0.0, self.opacity))
        self.highlight_progress = min(1.0, max(0.0, self.highlight_progress))
        self.reveal_progress = min(1.0, max(0.0, self.reveal_progress))
        # scale must remain non-negative as a multiplier.
        self.scale = max(0.0, self.scale)
        # blur and glow are additive deltas that composition clamps to a
        # final minimum of zero; the model accepts negative contributions.
        return self

    def model_copy(self, **kwargs):
        return super().model_copy(**kwargs)
