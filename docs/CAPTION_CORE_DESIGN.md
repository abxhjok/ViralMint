# Caption-Core Design

This document describes the deterministic caption timing core introduced in
Phase 1. It lives under the existing ASS/FFmpeg pipeline and does not replace it.

## Scope

Phase 1 intentionally stops at timing, structure, and an ASS compatibility bridge:

- **In scope:** `CaptionWord`, `CaptionSegment`, timing coordinate systems,
  active-word lookup, deterministic segmentation, and a bridge to the current
  ASS renderer.
- **Out of scope:** animation primitives, Remotion rendering, 60 presets, clipping
  scoring, boundary snapping, and smart reframe. These are reserved for later
  phases.

## Core models

Defined in `backend/caption_core/models.py` as Pydantic v2 models:

- `CaptionWord`: `id`, `text`, `start_ms`, `end_ms`, `confidence`, `speaker_id`,
  `tags`, `emphasis`. Rejects `end_ms < start_ms`; zero-duration words are valid.
- `CaptionSegment`: `id`, `start_ms`, `end_ms`, `words`, `speaker_id`. Derives
  its time bounds from the ordered words it contains.
- `CaptionStyle`: ASS-compatible fields (`font_family`, `font_size_*`, `font_weight`,
  `text_color`, `active_word_color`, `stroke_*`, `alignment`, `words_per_group`,
  etc.) plus future-animation fields (`shadow_blur`, `background_color`,
  `letter_spacing`, `line_height`, `text_transform`). The `to_ass_style_dict()`
  method converts only the supported subset to the legacy ASS dict shape.
- `CaptionAnimation`: pure configuration (`type`, `duration_ms`, `delay_ms`,
  `easing`, `spring`, `intensity`, `parameters`).
- `CaptionPreset`: `id`, `name`, `category`, `description`, `style`, `layout`,
  `entry_animation`, `active_word_animation`, `exit_animation`, `effects`,
  `tag_rules`.

## Timing coordinate systems

All core timestamps are integer milliseconds.

- Source time: milliseconds from the original media start.
- Clip-local time: `source_ms - clip_start_ms`.
- `to_clip_local_time` / `to_source_time` are pure arithmetic.
- `shift_words` returns new `CaptionWord` objects with shifted timestamps.
- `trim_words_to_clip` selects words that overlap the clip window using a
  half-open interval (`word.start < clip_end` and `word.end > clip_start`).
- `normalize_words_to_clip` trims and rewrites timestamps to clip-local time,
  clamping partial overlaps to `[0, clip_duration]` and dropping any word that
  becomes zero-duration at a boundary.

## Active-word boundary behavior

`find_active_word_index(words, current_time_ms)` in
`backend/caption_core/active_word.py`:

- Uses `start_ms <= current_time_ms < end_ms` (half-open).
- Returns `None` for empty arrays or times in gaps.
- For overlapping words, deterministic priority is:
  1. non-zero-duration words over zero-duration marker words,
  2. earlier `start_ms`,
  3. shorter duration,
  4. lower list index.
- Zero-duration words (`start_ms == end_ms`) are active only at that exact
  millisecond when no non-zero-duration word covers it.

## Segmentation rules

`segment_words(words, SegmentationConfig)` in `backend/caption_core/segmentation.py`:

- Input: ordered `CaptionWord` list.
- Output: ordered `CaptionSegment` list.
- Constraint order:
  1. `max_gap_ms` — a silence gap larger than this forces a new segment.
  2. `max_words_per_segment`.
  3. `max_chars_per_segment` (calculated on joined text including spaces).
  4. `max_duration_ms`.
  5. `prefer_punctuation` — when a hard limit is reached, the segment is closed
     at the most recent sentence-ending punctuation split point if one exists;
     otherwise it is closed immediately before the word that would exceed the
     limit.
- Words are never reordered, duplicated, or silently dropped.

## Transcription adapter

`words_from_transcription` in `backend/caption_core/transcription.py` converts the
existing faster-whisper / legacy segment format into `CaptionWord` objects:

- Reads `word` or `text`, `start`, `end`, `probability`/`confidence`, and
  `speaker`/`speaker_id`.
- Rounds seconds to integer milliseconds.
- Preserves confidence and speaker when present; uses safe `None` defaults when
  they are missing.
- Falls back to evenly splitting segment `text` when per-word timestamps are not
  available.

## ASS compatibility bridge

`backend/caption_core/ass_bridge.py` provides:

- `words_to_legacy_segments`: converts `list[CaptionWord]` into the
  `{"start", "end", "text", "words"}` shape consumed by `caption_service`.
- `core_style_to_legacy_dict`: converts `CaptionStyle` to the legacy style dict.
- `generate_captions_from_core`: generates an ASS file from core data by calling
  the existing `caption_service.generate_captions_ass` with a `style_config`
  override.

`backend/services/caption_service.py` was updated to accept an optional
`style_config` dict. When supplied, it bypasses the style-name lookup and uses
that config directly, so the existing ASS renderer can consume the new core
structures without being rewritten.

## File layout

```text
backend/caption_core/
  __init__.py
  enums.py          # CaptionCategory, CaptionAnimationType, CaptionEasing
  models.py         # Pydantic models
  timing.py         # source/clip-local utilities
  active_word.py    # deterministic active word
  segmentation.py   # deterministic segmentation
  transcription.py  # Whisper -> CaptionWord adapter
  ass_bridge.py     # bridge to existing ASS pipeline
```

Tests live in `tests/caption_core/`.
