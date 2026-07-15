# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Tests for the caption preview batch evaluator and API-facing models."""
import pytest

from backend.caption_core.animation.context import frame_to_ms
from backend.caption_core.animation.evaluator import evaluate_caption_word_state
from backend.caption_core.animation.preview import (
    PreviewRequest,
    evaluate_preview_batch,
    _preview_cache,
)
from backend.caption_core.animation.presets import get_preset
from backend.caption_core.models import CaptionSegment, CaptionWord


def sample_request(preset_id="bounce", fps=30, end_frame=60, frame_step=1):
    return PreviewRequest(
        words=[
            {"text": "Create", "start_ms": 0, "end_ms": 400},
            {"text": "viral", "start_ms": 400, "end_ms": 900},
            {"text": "shorts", "start_ms": 900, "end_ms": 1400},
        ],
        preset_id=preset_id,
        fps=fps,
        start_frame=0,
        end_frame=end_frame,
        frame_step=frame_step,
    )


def test_preview_request_validation_unknown_preset():
    with pytest.raises(ValueError):
        PreviewRequest(
            words=[{"text": "w", "start_ms": 0, "end_ms": 100}],
            preset_id="unknown",
        )


def test_preview_request_validation_invalid_fps():
    with pytest.raises(ValueError):
        PreviewRequest(
            words=[{"text": "w", "start_ms": 0, "end_ms": 100}],
            preset_id="bounce",
            fps=0,
        )


def test_preview_request_validation_frame_range():
    with pytest.raises(ValueError):
        PreviewRequest(
            words=[{"text": "w", "start_ms": 0, "end_ms": 100}],
            preset_id="bounce",
            end_frame=500,
        )


def test_preview_request_validation_end_before_start():
    with pytest.raises(ValueError):
        PreviewRequest(
            words=[{"text": "w", "start_ms": 0, "end_ms": 100}],
            preset_id="bounce",
            start_frame=10,
            end_frame=0,
        )


def test_preview_request_empty_words_allowed_by_model():
    # The model allows empty words; the endpoint rejects them.
    req = PreviewRequest(words=[], preset_id="bounce")
    assert req.words == []


def test_evaluate_preview_batch_matches_direct_evaluator():
    """Batch output for a single frame must match direct evaluator output."""
    _preview_cache.invalidate()
    req = sample_request(preset_id="karaoke", fps=30, end_frame=30)
    words = [CaptionWord(**w.model_dump()) for w in req.words]
    segment = CaptionSegment(words=words)
    preset = get_preset(req.preset_id)

    frames = evaluate_preview_batch(req)
    assert len(frames) == 31
    for frame in frames:
        fnum = frame["frame"]
        for word_state in frame["words"]:
            word_index = word_state["word_index"]
            direct = evaluate_caption_word_state(
                word=words[word_index],
                word_index=word_index,
                segment=segment,
                preset=preset,
                frame=fnum,
                fps=req.fps,
            )
            assert word_state["opacity"] == pytest.approx(direct.opacity)
            assert word_state["scale"] == pytest.approx(direct.scale)
            assert word_state["highlight_progress"] == pytest.approx(direct.highlight_progress)
            assert word_state["reveal_progress"] == pytest.approx(direct.reveal_progress)


def test_preview_cache_reuses_result():
    _preview_cache.invalidate()
    req = sample_request(preset_id="typewriter", end_frame=30)
    first = evaluate_preview_batch(req)
    second = evaluate_preview_batch(req)
    assert first is second


def test_preview_frame_time_ms():
    _preview_cache.invalidate()
    req = sample_request(fps=60, end_frame=60)
    frames = evaluate_preview_batch(req)
    for frame in frames:
        assert frame["time_ms"] == frame_to_ms(frame["frame"], req.fps)


def test_preview_all_five_presets():
    _preview_cache.invalidate()
    for preset_id in ["bounce", "explosive", "glitch", "typewriter", "karaoke"]:
        req = sample_request(preset_id=preset_id, end_frame=60)
        frames = evaluate_preview_batch(req)
        assert len(frames) == 61
        # At least one frame should have a visible word for each preset.
        assert any(w["opacity"] > 0 for f in frames for w in f["words"])


def test_preview_determinism():
    _preview_cache.invalidate()
    req = sample_request(preset_id="glitch", end_frame=60)
    a = evaluate_preview_batch(req)
    _preview_cache.invalidate()
    b = evaluate_preview_batch(req)
    assert a == b
