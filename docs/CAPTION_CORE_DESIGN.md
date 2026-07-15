# Caption-Core Design

This document describes the deterministic caption timing core introduced in
Phase 1 and the deterministic frame-based animation engine added in Phase 2.
Both layers live under the existing ASS/FFmpeg pipeline and do not replace it.

## Scope

Phase 1 intentionally stopped at timing, structure, and an ASS compatibility bridge.
Phase 2 adds a renderer-independent animation composition engine:

- **In scope:** `CaptionWord`, `CaptionSegment`, timing coordinate systems,
  active-word lookup, deterministic segmentation, a bridge to the current
  ASS renderer, and the `backend/caption_core/animation/` engine.
- **Out of scope:** Remotion rendering, 60 presets, clipping scoring,
  boundary snapping, and smart reframe. The ASS pipeline does not yet consume
  the animation state.

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

Tests live in `tests/caption_core/` and `tests/caption_core/animation/`.

## Visual-state model

`CaptionVisualState` in `backend/caption_core/animation/state.py` is an
immutable Pydantic model that describes how one word is drawn at one frame.

Renderer-neutral units:

| property | default | unit | clamp |
|----------|---------|------|-------|
| `opacity` | `1.0` | dimensionless | `[0, 1]` |
| `scale` | `1.0` | multiplier | `>= 0` |
| `translate_x` / `translate_y` | `0.0` | screen units (logical px) | none |
| `rotation` | `0.0` | degrees | none |
| `blur` | `0.0` | screen units | final `>= 0` |
| `glow` | `0.0` | screen units | final `>= 0` |
| `letter_spacing` | `0.0` | screen units | none |
| `highlight_progress` | `0.0` | dimensionless | `[0, 1]` |
| `reveal_progress` | `0.0` | dimensionless | `[0, 1]` |

`reveal_progress` is a Phase 2 extension used by the typewriter primitive.

## Frame/time conversion

`backend/caption_core/animation/context.py` provides:

- `frame_to_ms(frame, fps) -> int`: rounds to the nearest millisecond.
- `ms_to_frame(ms, fps) -> int`: rounds to the nearest frame.
- `AnimationContext`: the deterministic context passed to every primitive,
  containing `frame`, `fps`, `current_time_ms`, the target `word`, `segment`,
  `word_index`, `active_word_index`, `animation_config`, `trigger`, and
  `trigger_time_ms`.

No `time.time()`, `datetime.now()`, JavaScript timers, or browser state is used.

## Animation composition rules

`compose_animations(base, contributions)` in
`backend/caption_core/animation/composition.py` applies an ordered list of
primitive outputs to a base state:

- `opacity` → multiplicative
- `scale` → multiplicative
- `translate_x` / `translate_y` → additive
- `rotation` → additive
- `blur` / `glow` → additive, clamped to a final minimum of `0`
- `letter_spacing` → additive
- `highlight_progress` → maximum
- `reveal_progress` → maximum

The base object is never mutated.

## Easing

`backend/caption_core/animation/easing.py` provides pure functions:

- `ease_linear`, `ease_in`, `ease_out`, `ease_in_out`
- `clamp01`, `lerp(start, end, t)`
- `calculate_progress(start_ms, duration_ms, current_time_ms)` with handling for
  zero duration, negative time, and post-completion.

## Primitives

All primitives are pure functions `AnimationContext -> CaptionVisualState` in
`backend/caption_core/animation/primitives.py`:

- `evaluate_fade` — fade in or out (`direction`, `duration_ms`, `delay_ms`, `easing`).
- `evaluate_scale` — scale between `from_scale` and `to_scale`.
- `evaluate_spring` / `_spring_displacement` — deterministic underdamped
  harmonic oscillator `x(t) = A * exp(-zeta * omega * t) * sin(omega_d * t)`.
- `evaluate_bounce` — vertical or scale bounce using the spring function.
- `evaluate_glitch` — deterministic jitter derived from a SHA-256 seed of
  `word.id`, `word_index`, and `frame`.
- `evaluate_typewriter` — computes `reveal_progress`.
- `evaluate_karaoke` — computes `highlight_progress` over a word.

`visible_character_count` and `visible_text` support Unicode grapheme clusters.

## Spring implementation

The spring uses the standard underdamped equation:

```
omega = sqrt(k / m)
zeta  = c / (2 * sqrt(m * k))
omega_d = omega * sqrt(1 - zeta^2)
x(t) = A * exp(-zeta * omega * t) * sin(omega_d * t)
```

Invalid or unstable parameters are protected by clamping `zeta` to `< 1` and
ensuring `omega` and `mass` are positive.

## Deterministic glitch seeding

`evaluate_glitch` builds a stable SHA-256 seed from:

```
{seed_offset}:{word_index}:{word.id}:{frame // frequency}
```

The digest is converted to deterministic signed floats. The same
`(word, word_index, frame, frequency, seed_offset)` tuple always returns the
same `translate_x`, `translate_y`, `rotation`, `opacity`, `glow`, and `blur`
values.

## Animation registry

`backend/caption_core/animation/registry.py` maps these animation type
identifiers to primitive implementations:

`fade`, `scale`, `spring`, `bounce`, `glitch`, `typewriter`, `karaoke`.

Unknown types raise `ValueError` from `dispatch_animation`.

## Event evaluation semantics

`backend/caption_core/animation/events.py` provides `is_event_active(trigger,
word, segment, current_time_ms, animation, ...)`. Conceptual triggers are:

- `SEGMENT_ENTER`
- `SEGMENT_EXIT`
- `WORD_ENTER`
- `WORD_ACTIVE`
- `WORD_EXIT`

This is a pure timing check, not a runtime event emitter. `WORD_ACTIVE` is
active for the inclusive word interval and is restricted to the active word.
Enter/exit/segment events are active for their configured `duration_ms` after
a trigger-time plus `delay_ms`.

## Frame-state evaluator

`evaluate_caption_word_state(word, word_index, segment, preset, frame, fps)`
in `backend/caption_core/animation/evaluator.py` is the canonical API:

1. Convert `frame`/`fps` to `current_time_ms`.
2. Find `active_word_index`.
3. Collect applicable `AnimationContext` objects by checking each trigger.
4. Dispatch each context through `dispatch_animation`.
5. `compose_animations` into a final `CaptionVisualState`.

A word is visible (base opacity `1`) when it is the active word or is affected
by an enter/exit/segment event; otherwise the base opacity is `0` so
word-by-word presets hide inactive words.

## Initial presets

`backend/caption_core/animation/presets.py` defines five engine-verification
presets via configuration only:

- `Bounce` — spring vertical bounce on active word.
- `Explosive` — fade in + scale up + scale bounce on entry.
- `Glitch` — deterministic jitter while active.
- `Typewriter` — character reveal by active word.
- `Karaoke` — highlight progress mapped to word duration.

## Phase 3: Animated caption preview

### Preview transport architecture

The frontend does not run animation formulas. Instead, it requests a short,
pre-computed frame-state timeline from the backend and renders it:

```
frontend AnimatedCaptionPreview
  -> useCaptionPreview
  -> POST /api/captions/preview
  -> backend PreviewRequest validation
  -> evaluate_preview_batch
  -> evaluate_caption_word_state per word, per frame
  -> JSON array of frames, each with per-word CaptionVisualState
  -> frontend maps state to CSS (opacity, transform, filter, text-shadow, etc.)
```

This keeps the canonical evaluator as the single source of truth for all
animation math.

### Batch evaluation

`backend/caption_core/animation/preview.py` provides `evaluate_preview_batch`.
It accepts a `PreviewRequest` (`words`, `preset_id`, `fps`, `start_frame`,
`end_frame`, `frame_step`) and returns every requested frame. To keep requests
small and responsive:

- Maximum 180 frames per preview.
- Maximum 6,000ms preview duration.
- Maximum 50 words per preview.
- Optional `frame_step` lets the client trade smoothness for payload size
  (preset cards use `frame_step=2`).

Batch results are verified against direct `evaluate_caption_word_state` calls
in `tests/caption_core/animation/test_preview.py`.

### Preview API contract

`POST /api/captions/preview` returns:

```json
{
  "preset_id": "bounce",
  "fps": 30,
  "start_frame": 0,
  "end_frame": 72,
  "frame_step": 1,
  "frame_count": 73,
  "frames": [
    {
      "frame": 0,
      "time_ms": 0,
      "words": [
        {
          "text": "Create",
          "word_index": 0,
          "active": true,
          "opacity": 1.0,
          "scale": 1.0,
          "translate_x": 0.0,
          "translate_y": 0.0,
          "rotation": 0.0,
          "blur": 0.0,
          "glow": 0.0,
          "letter_spacing": 0.0,
          "highlight_progress": 0.0,
          "reveal_progress": 0.0
        }
      ]
    }
  ]
}
```

`GET /api/captions/preview/presets` lists the five Phase 2 presets.
`POST /api/captions/preview/invalidate-cache` clears the process-local cache.

### Frontend renderer mapping

`frontend/src/components/captions/AnimatedCaptionPreview.jsx` maps each
backend state field to browser presentation:

| state field | CSS / DOM mapping |
|-------------|-------------------|
| `opacity` | `style.opacity` |
| `scale`, `translate_*`, `rotation` | `transform: translate(...) scale(...) rotate(...)` |
| `blur` | `filter: blur(...)` |
| `glow` | `text-shadow: 0 0 ${glow}px currentColor` |
| `letter_spacing` | `letterSpacing` |
| `reveal_progress` | `visibleText(text, reveal_progress)` slices Unicode grapheme clusters |
| `highlight_progress` | overlay span clipped to `progress * 100%` width |

No spring, bounce, glitch, typewriter, or karaoke math is performed in JS.

### Video-time-to-frame conversion

The current preview is standalone (sample caption) and not tied to a loaded
`<video>`. When integrated with a video element in the future, the rule is:

```
frame = round(currentTime * fps)
```

The frame is always derived from `video.currentTime` on each `timeupdate` or
`requestAnimationFrame` tick, not by incrementing a fake counter. This avoids
cumulative drift. The same `frame` and `fps` always resolve to the same
`current_time_ms` on the backend.

### Preview cache

`PreviewCache` in `backend/caption_core/animation/preview.py` is an in-process,
bounded LRU with TTL:

- Key = SHA-256 of the serialized preview request (words, preset, fps, frame
  range, frame step).
- `maxsize` = 128 entries.
- `ttl_seconds` = 300.
- Invalidation is implicit because any input change produces a new key; the
  `invalidate` endpoint clears all entries.

### Known preview limitations

- The preview uses a short sample caption in the `ToolCaptions` page; real clip
  transcripts are not yet wired in (that requires clip-local timing + transcript
  storage on generated clips, which is out of Phase 3 scope).
- Video playback scrubbing is not yet implemented because the preview is not
  currently attached to a video element. The deterministic frame-state evaluator
  supports it; only the player glue is missing.
- Preset cards intentionally use `frame_step=2` and a 1.6s duration to keep
  payloads small and avoid per-card full-FFmpeg rendering.
- The front-end `Intl.Segmenter` is the preferred grapheme splitter; the
  fallback `Array.from(text)` splits by code point, which is safe but not
  cluster-perfect for complex combining marks.

## ASS integration status

The existing `caption_service.py` ASS renderer is unchanged. The animation
engine in `backend/caption_core/animation/` is a parallel, renderer-neutral
state layer. It is not consumed by the ASS pipeline in this phase; that
integration belongs to a later phase.
