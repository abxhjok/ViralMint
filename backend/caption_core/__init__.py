# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Deterministic caption timing and style core.

This package sits underneath the existing ASS/FFmpeg caption pipeline.
It provides typed models, timing utilities, segmentation, and an ASS bridge
so that the current renderer can consume deterministic, validated caption data.
"""
