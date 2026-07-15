# Clipping Engine Research

This document compares ViralMint's existing clip extraction pipeline with the open-source clipping/reframe/scoring approaches found in the referenced projects. It is a research summary; no implementation is prescribed here.

## 1. Existing ViralMint Clipping Engine

### Files

- `backend/services/clip_extractor.py`
- `backend/services/ffmpeg_service.py`
- `backend/services/whisper_service.py`
- `backend/services/caption_service.py`
- `backend/core/task_runner.py`
- `backend/api/videos.py`
- `frontend/src/pages/ClipStudio.jsx`

### Pipeline

1. Source video is loaded from `DownloadedVideo`.
2. `WhisperService.transcribe()` produces word-level timestamped segments.
3. `extract_viral_clips()` estimates clip count and builds an AI prompt (`CLIP_SELECTION_PROMPT`).
4. The AI returns a JSON array of candidate clips:
   - `start`, `end`, `title`, `hook`, `reason`, `virality_score` (1–10).
5. `_remove_overlapping_clips()` deduplicates with a 2-second overlap tolerance, keeping earlier/higher-scored clips.
6. `_process_clips_parallel()` runs for each selected window:
   - `extract_clip()` → 9:16 reframe with blur-fill for landscape.
   - `generate_captions_ass()` + `burn_captions()`.
   - Thumbnail + metadata.
7. Results are saved as `GeneratedVideo` rows with `clip_*` fields.

### Reframe

`ffmpeg_service.extract_clip()` uses a fixed FFmpeg filter chain:

```
split[original][bg];
[bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[blurred];
[original]scale=1080:1920:force_original_aspect_ratio=decrease[scaled];
[blurred][scaled]overlay=(W-w)/2:(H-h)/2
```

This produces a vertically-centered 9:16 output with the original frame inset on a blurred background. It does not track faces, speakers, or objects.

### Scoring

- `clip_virality_score` comes from the LLM response, not from a deterministic formula.
- The prompt includes qualitative criteria (hook, coherence, value density, payoff, curiosity gap, speech energy).
- The Phase 0 spec weights (Hook Strength 30%, Standalone Coherence 20%, Emotional Intensity 15%, Value Density 15%, Payoff Quality 10%, Curiosity Gap 5%, Speech Energy 5%) are **not yet implemented** as numeric code.

### Strengths

- End-to-end pipeline already exists in the repo.
- Parallel processing of multiple clips.
- Integration with the ClipStudio UI and job runner.

### Limitations

- No content-type detection (talking-head vs podcast vs screen recording).
- No silence-based or sentence-boundary snapping.
- No face/speaker/object tracking for reframing.
- Scoring is entirely prompt-driven and can be inconsistent or expensive.
- No proxy/low-resolution editing workflow; transcoding and transcription run on the original file.

---

## 2. `AgriciDaniel/claude-shorts`

- **License:** MIT
- **Source:** `https://github.com/AgriciDaniel/claude-shorts`
- **Path examined:** `/home/ubuntu/research/claude-shorts`

### Components

- `docs/scoring-rubric.md` — defines a quantitative clip scoring rubric.
- `scripts/detect_content.py` — classifies video content type from sampled frames using MediaPipe face detection.
- `scripts/snap_boundaries.py` — snaps AI-selected cut points to silence and sentence boundaries.
- `scripts/compute_reframe.py` — computes crop keyframes for 9:16 reframing using face tracking and cursor motion.
- `remotion/render.mjs` — bundle-once, render-many orchestrator.

### Scoring rubric (`docs/scoring-rubric.md`)

- 1–10 scale across five dimensions:
  1. **Hook Strength** — first 3 seconds grab attention and promise value.
  2. **Standalone Coherence** — clip makes sense without prior context.
  3. **Emotional Intensity** — excitement, curiosity, anger, humor, awe.
  4. **Value Density** — insight, entertainment, or education per minute.
  5. **Payoff Quality** — satisfying conclusion or clear takeaway.
- Recommended weighting mirrors the Phase 0 spec: Hook highest, then Coherence, then Emotional/Value, then Payoff.
- Provides candidate selection guidelines and multi-pass pruning rules.

### Content-type detection (`scripts/detect_content.py`)

- Samples 10 evenly spaced frames.
- Runs MediaPipe Face Detection on each frame.
- Classifies into:
  - `talking-head` — one large centered face.
  - `podcast` — 2+ consistent medium faces.
  - `screen` — no/small/off-center faces (screen recording, webcam PiP).

### Boundary snapping (`scripts/snap_boundaries.py`)

- Uses FFmpeg `silencedetect` to find silence regions.
- Snaps `start` to the nearest sentence start or silence end.
- Snaps `end` to the nearest sentence end, silence start, or natural pause.
- Pads by configurable margins and clamps to `min_duration`/`max_duration`.

### Reframe (`scripts/compute_reframe.py`)

- For talking-head/person content:
  - Detects the largest face per frame and smooths center-of-face movement over time.
  - Outputs crop rectangles (`x`, `y`, `w`, `h`) with optional `crop_keyframes`.
- For screen content:
  - Tracks cursor movement using frame differencing on downscaled frames.
  - Keeps the cropped window following the cursor.

### Render orchestrator (`remotion/render.mjs`)

- Bundles the Remotion project once.
- Opens a shared Chrome instance (`openBrowser`).
- Starts a local HTTP server to serve clipped MP4s to Remotion (Remotion only accepts `http/https` URLs).
- For each segment:
  - Filters captions to the segment range and offsets them to clip-local time.
  - Builds `inputProps` with `clipSrc`, `crop`, `cropKeyframes`, `captions`, `captionStyle`, `hookLine1/2`.
  - Uses `selectComposition()` + `renderMedia()` to render each short.
- Uses `calculateMetadata` for dynamic per-segment duration.

### Relevance

- The scoring rubric can be translated into a deterministic weighted scoring function for ViralMint.
- Content detection and boundary snapping directly address current ViralMint gaps.
- The reframe/crop keyframe approach can inform face/cursor tracking in ViralMint.
- The bundle-once-render-many pattern is useful for a high-volume batch export phase.

### Caveats

- Requires MediaPipe, OpenCV, and NumPy.
- Remotion rendering has the same licensing considerations as noted in `CAPTION_ENGINE_RESEARCH.md`.

---

## 3. `francozanardi/pycaps`

- **License:** MIT
- **Source:** `https://github.com/francozanardi/pycaps`
- **Path examined:** `/home/ubuntu/research/pycaps`

### Components

- `src/pycaps/pipeline/caps_pipeline.py` and `caps_pipeline_builder.py` — orchestrates clip creation.
- `src/pycaps/selector/` — `time_event_selector.py`, `tag_based_selector.py`, `word_clip_selector.py`.
- `src/pycaps/tag/tagger/` — semantic/structure/AI taggers that label transcript segments.
- `src/pycaps/effect/clip/` — `typewriting_effect.py`, `animate_segment_emojis_effect.py`.
- `src/pycaps/effect/text/` — emoji insertion and text effects.

### Relevance

- Demonstrates a Python-only pipeline for selecting clip boundaries from transcripts using tag-based and word-based selectors.
- Effect system (`Effect`, `ClipEffect`, `TextEffect`) provides a modular way to attach post-processing such as emoji animation and typewriter text.
- The `tag/definitions.py` and `tag/tag_condition.py` approach could inform a rule-based or hybrid scoring layer in ViralMint.

### Caveats

- The pipeline is tightly coupled to its own data model; direct reuse would require adaptation.
- No face/cursor reframe logic was observed.

---

## 4. `itsjwill/vanta`

- **License:** MIT
- **Source:** `https://github.com/itsjwill/vanta`

### Relevance

- `vanta` is primarily a caption-style/types reference repository. It does not contain a clipping engine.
- Its category list (`viral`, `podcast`, `story`, `educational`, `gaming`, etc.) is useful for organizing clip and caption presets, but not for selecting cut points.

---

## 5. `ahgsql/remotion-subtitles`

- **License:** MIT
- **Source:** `https://github.com/ahgsql/remotion-subtitles`

### Relevance

- Primarily a caption template library. It does not contain clip selection, scoring, or reframe logic.
- Its `SubtitleSequence.tsx` demonstrates how to render a list of clips with per-subtitle timings in Remotion.

---

## 6. Comparative Summary

| Capability | ViralMint today | `claude-shorts` | `pycaps` |
|------------|------------------|-----------------|----------|
| Content type detection | No | MediaPipe face detection (talking-head/podcast/screen) | No |
| Scoring rubric | Prompt-only | Documented 5-dimension rubric with weights | Tag-based selectors |
| Deterministic scoring | No | Partial (rubric + AI) | Rule/tag based |
| Boundary snapping | No | Silence + sentence boundaries | Word/sentence selectors |
| Face-tracking reframe | Static blur-fill | Yes (crop keyframes) | No |
| Cursor-tracking reframe | No | Yes | No |
| Batch render | Parallel clips | Bundle-once-render-many (Remotion) | Python pipeline |
| Proxy/low-res editing | No | No explicit proxy pipeline | No |

## 7. Implications for Phase 1+

To move from the current ViralMint pipeline to the target workflow (`IMPORT VIDEO → CREATE PROXY → TRANSCRIBE → ANALYZE → DETECT VIRAL MOMENTS → SCORE CLIPS → SNAP CUT BOUNDARIES → AUTO REFRAME → GENERATE ANIMATED CAPTIONS → REVIEW → BATCH EXPORT`), the following research findings are most relevant:

1. **Scoring function.** Translate the 7 weights from the Phase 0 spec into a numeric scoring helper, using `claude-shorts/docs/scoring-rubric.md` as a reference. The LLM can still provide per-dimension ratings or rationales; the final score should be computed deterministically.
2. **Content detection.** Add a `detect_content_type()` step using MediaPipe (as in `claude-shorts/scripts/detect_content.py`) to choose the right reframe strategy.
3. **Boundary snapping.** Implement a `snap_boundaries()` function using FFmpeg `silencedetect` and transcript sentence boundaries before finalizing `clip_start_seconds`/`clip_end_seconds`.
4. **Auto reframe.**
   - For talking-head/podcast: face-tracking crop with smoothing and keyframes.
   - For screen: cursor/mouse tracking crop.
   - Fall back to the existing blur-fill center crop for unsupported content.
5. **Batch export.** The `claude-shorts/remotion/render.mjs` pattern of bundle-once-render-many is a useful model, but an FFmpeg-only batch exporter may be preferable for a local-first, no-browser path.
6. **Proxy workflow.** For high-volume work, a proxy step (low-resolution H.264 or HLS preview) would reduce CPU/IO during review. This is not present in any of the researched repos and would need original design.

No source code from the referenced projects was copied during Phase 0; all notes are derived from inspection and documentation.
