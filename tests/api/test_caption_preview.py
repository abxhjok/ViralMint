# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Integration tests for the animated caption preview API."""
import pytest

from fastapi.testclient import TestClient
from backend.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_list_preview_presets(client):
    r = client.get("/api/captions/preview/presets")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["presets"]}
    assert ids == {"bounce", "explosive", "glitch", "typewriter", "karaoke"}


SAMPLE_WORDS = [
    {"text": "Create", "start_ms": 0, "end_ms": 400},
    {"text": "viral", "start_ms": 400, "end_ms": 900},
    {"text": "shorts", "start_ms": 900, "end_ms": 1400},
]


def _preview_request(**overrides):
    body = {
        "words": SAMPLE_WORDS,
        "preset_id": "bounce",
        "fps": 30,
        "start_frame": 0,
        "end_frame": 60,
        "frame_step": 1,
    }
    body.update(overrides)
    return body


def test_preview_valid_returns_frames(client):
    r = client.post("/api/captions/preview", json=_preview_request(preset_id="bounce"))
    assert r.status_code == 200
    data = r.json()
    assert data["frame_count"] == 61
    assert data["fps"] == 30
    assert len(data["frames"]) == 61
    first_frame = data["frames"][0]
    assert "frame" in first_frame and "time_ms" in first_frame
    assert len(first_frame["words"]) == len(SAMPLE_WORDS)
    for word in first_frame["words"]:
        assert "opacity" in word and "scale" in word and "reveal_progress" in word


def test_preview_bounce_active_word_moves_or_scales(client):
    r = client.post("/api/captions/preview", json=_preview_request(preset_id="bounce"))
    assert r.status_code == 200
    frames = r.json()["frames"]
    scales = {w["scale"] for f in frames for w in f["words"]}
    translations = {w["translate_y"] for f in frames for w in f["words"]}
    assert any(s != 1.0 for s in scales) or any(t != 0.0 for t in translations)


def test_preview_empty_words(client):
    r = client.post("/api/captions/preview", json=_preview_request(words=[]))
    assert r.status_code == 422


def test_preview_unknown_preset(client):
    r = client.post("/api/captions/preview", json=_preview_request(preset_id="nope"))
    assert r.status_code == 422


def test_preview_invalid_fps(client):
    r = client.post("/api/captions/preview", json=_preview_request(fps=0))
    assert r.status_code == 422


def test_preview_frame_range_limit(client):
    r = client.post("/api/captions/preview", json=_preview_request(end_frame=500))
    assert r.status_code == 422


def test_preview_end_before_start(client):
    r = client.post("/api/captions/preview", json=_preview_request(start_frame=10, end_frame=0))
    assert r.status_code == 422


def test_preview_deterministic(client):
    body = _preview_request(preset_id="glitch")
    a = client.post("/api/captions/preview", json=body).json()
    b = client.post("/api/captions/preview", json=body).json()
    assert a == b
