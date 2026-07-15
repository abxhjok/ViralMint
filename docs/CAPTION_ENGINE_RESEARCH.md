# Caption Engine Research

This document compares the existing ViralMint caption engine with the open-source projects and documentation referenced for the short-form clipping workstation. It is a research summary; no implementation is prescribed here.

## 1. Existing ViralMint Caption Engine

### Files

- `backend/services/caption_service.py`
- `backend/services/ffmpeg_service.py` (`add_captions`, `extract_clip`, `stitch_clips`)
- `backend/api/captions.py`
- `backend/models/caption_style.py`

### How it works

1. `WhisperService` produces word-level timestamps (per word: `start`, `end`, `word`).
2. `caption_service.py` flattens segments and groups words by `words_per_group` (default 3). It enforces monotonic start/end ordering.
3. ASS dialogue events are generated for each group, with one active word highlighted using an inline color override (`{\1c&H...}`).
4. The ASS file is written to disk and burned with FFmpeg `-vf ass=path/to.ass`.
5. `EMOJI_KEYWORDS` triggers emoji insertion for mapped words (`none`, `moderate`, `aggressive`).

### Built-in ASS styles (`CAPTION_STYLES`)

- `viral`, `classic`, `bold`, `neon`, `minimal`, `karaoke`, `glow`

Each style is a dictionary of:

- `font`, `font_size_portrait`, `font_size_landscape`
- `primary_color`, `highlight_color`, `outline_color`
- `outline_width`, `shadow_depth`
- `alignment`, `margin_v`, `words_per_group`

The API (`backend/api/captions.py`) stores custom user-defined styles in the `CaptionStyle` SQLAlchemy model with the same fields plus `is_ai_generated` and `description`.

### Strengths

- Pure FFmpeg + Python; no browser or headless rendering.
- Offline, fast for simple color-swap captions.
- Customizable fonts, colors, outline, shadow, margins.

### Limitations

- ASS subtitle styling is limited to ASS tags; advanced motion (bounce, spring, per-letter typewriter, glitch, karaoke wipes) is cumbersome or unsupported.
- Highlighting is per group, not per individual word, so the active-word accuracy is coarse.
- No layout engine to prevent long lines from overflowing.
- Only 7 presets; no categorization into VIRAL, PODCAST, CINEMATIC, etc.

---

## 2. `ahgsql/remotion-subtitles`

- **License:** MIT
- **Source:** `https://github.com/ahgsql/remotion-subtitles`
- **Path examined:** `/home/ubuntu/research/remotion-subtitles`

### Components

- `src/SubtitleSequence.tsx` — maps an SRT `Subtitle` array to `Sequence` components.
- `src/captions/` contains one React component per visual style (17 total):
  - `Bounce`, `Explosive`, `Glitch`, `Typewriter`
  - `Blur`, `Boxed`, `Boxed2`, `Clean`, `Color`, `Curtain`, `Default`, `Faded`, `Flicker`, `Glowing`, `Karaoke`, `Lightning`, `Neon`, `Outline`, `Reverse`

### Architecture

- Reads an SRT subtitle file and converts it to a typed `Subtitle[]` array (`startTime`, `endTime`, `text`).
- Each subtitle is rendered as a `<Sequence>` over its time range.
- Each style component receives `text` and `T` (progress 0–1 for the duration of that subtitle) and uses Remotion's `interpolate`, `spring`, and `Easing` to animate the whole text block.
- `subtitleLine.ts` adds text backgrounds using a dynamic `maxWidth`.

### Relevance to requested presets

The requested initial presets `Bounce`, `Explosive`, `Glitch`, `Typewriter` are all present. `Karaoke` is also present. This repository is useful for phrase-level, timed animation patterns. However:

- It does **not** implement word-by-word active highlighting; it animates the entire subtitle entry.
- Styles are coded inside individual Remotion components, not a declarative preset schema.

---

## 3. `francozanardi/pycaps`

- **License:** MIT
- **Source:** `https://github.com/francozanardi/pycaps`
- **Path examined:** `/home/ubuntu/research/pycaps`

### Architecture

- A Python pipeline that turns video + transcript into captioned short-form clips.
- Key modules:
  - `transcriber/` — Whisper transcription and sentence/char splitters.
  - `renderer/` — `CssSubtitleRenderer` and `PlaywrightScreenshotCapturer`.
  - `animation/` — preset and primitive animation definitions (`pop_in`, `pop_in_bounce`, `zoom_in`, `zoom_out`, `slide_in`, `slide_out`, `fade_in`).
  - `layout/` — word-size calculation, line splitting, positions.
  - `template/preset/` — CSS-based style templates: `default`, `minimalist`, `vibrant`, `retro-gaming`, `neo-minimal`, `hype`, `fast`, `word-focus`, `classic`, `line-focus`, `explosive`.

### Rendering approach

- Uses **Playwright + Chromium** to screenshot HTML/CSS for each word/line.
- `RendererPage` builds an HTML page; JS injects word spans with CSS classes.
- `render_word()` captures each word's bounding box with `page.screenshot(clip=..., omit_background=True)`.
- `CssSubtitleRenderer` caches rendered word PNGs and assembles them into a video.

### Relevance

- Demonstrates a Python-first, CSS-driven word-level caption renderer.
- Preset/template structure can inform a declarative caption-preset schema for ViralMint.
- `animation/builtin/preset/pop_in_bounce.py` directly relates to the requested `Bounce` preset.
- The `explosive` template relates to the requested `Explosive` preset.

### Caveats

- Playwright rendering is slower than FFmpeg ASS and requires Chromium.
- The codebase uses a custom internal DOM; porting would mean adapting it to a ViralMint pipeline rather than copying wholesale.

---

## 4. `AgriciDaniel/claude-shorts`

- **License:** MIT
- **Source:** `https://github.com/AgriciDaniel/claude-shorts`
- **Path examined:** `/home/ubuntu/research/claude-shorts`

### Components

- `scripts/transcribe.py` — runs `faster-whisper` and outputs both WhisperX-style segments and Remotion `Caption[]` entries (`text`, `startMs`, `endMs`).
- `remotion/` — a Remotion project that renders vertical short-form videos.
- `remotion/render.mjs` — bundles once, opens a shared Chrome, and renders each approved segment sequentially.
- `remotion/src/Captions.tsx` — uses `@remotion/captions` `useCurrentFrame`/`useVideoConfig` and per-word layout.

### Caption approach

- Relies on Remotion's `@remotion/captions` package.
- Each caption word becomes an element that can be highlighted at its `startMs`/`endMs`.
- `createTikTokStyleCaptions()` builds word arrays with timing and supports `startFrom`, `endAt`, `onlyCaptionContent`.
- Render props allow a `captionStyle` string such as `bold`/`bounce`/`clean` to change visual styling.

### Relevance

- Produces word-level, timestamp-accurate animated captions inside a React/Remotion timeline.
- The `bundle-once-render-many` pattern in `render.mjs` is a useful high-throughput approach for batch export.
- The `Caption` type from `@remotion/captions` is a good interoperability target.

### Caveats

- Requires a Remotion license for the core renderer in certain commercial/company settings.
- `@remotion/captions` itself is MIT, but it is part of the Remotion monorepo.

---

## 5. `itsjwill/vanta`

- **License:** MIT
- **Source:** `https://github.com/itsjwill/vanta`
- **Path examined:** `/home/ubuntu/research/vanta`

### Components

- `src/lib/animated-captions.ts` — defines conceptual animation presets:
  - `Bouncy`, `Bold`, `Elegant`, `Clean`, `Minimal`, `Modern`, `Karaoke`, `Typewriter`, `Stylish`, `MinimalText`, `Glitch`.
- These are typed `AnimatedCaptionOptions` objects that select font families, font sizes, colors, stroke widths, positions, animation timings, and highlight modes.

### Relevance

- Provides a clean **declarative preset schema** with categories such as `viral`, `podcast`, `story`, `educational`, `gaming`, `meme`, `high_energy`, `karaoke`.
- Can be used as a reference for how to structure a `CaptionPreset` config object (fonts, weights, colors, layout, animation name) in ViralMint.

### Caveats

- The repository is conceptual/types-only; it does not include a rendering engine.
- No implementation was copied during Phase 0.

---

## 6. Remotion Caption Documentation

- **Package:** `@remotion/captions`
- **Docs:** `https://www.remotion.dev/docs/captions`
- **Package license (per `packages/captions/package.json`):** MIT
- **Monorepo license (Remotion core renderer):** custom dual free/company license

### Key concepts

- `Caption` type:

  ```ts
  type Caption = {
    text: string;
    startMs: number;
    endMs: number;
    confidence?: number;
  };
  ```

- Converters are provided for:
  - `@remotion/install-whisper-cpp`
  - `@remotion/whisper-web`
  - `@remotion/openai-whisper`
  - `@remotion/elevenlabs`

- The package does not render captions itself; it provides timing primitives and helper functions such as `createTikTokStyleCaptions()` and word-index helpers for React components.

### Relevance

- If ViralMint moves to a Remotion-based render path, `@remotion/captions` is the canonical data structure for word-level timing.
- It enables frame-accurate, per-word highlight animations and dynamic layouts in React.

---

## 7. Comparative Summary

| Engine | License | Word-level highlight | Motion effects | Offline | Speed | Notes |
|--------|---------|----------------------|----------------|---------|-------|-------|
| ViralMint ASS | AGPL-3.0 (project) | Partial (per group) | Limited | Yes | Fast | Current baseline; 7 presets. |
| `remotion-subtitles` | MIT | No (per subtitle) | Yes (per style component) | No (requires browser) | Medium | 17 style components; useful phrase-level motion. |
| `pycaps` | MIT | Yes | Yes (CSS/JS + Playwright screenshots) | No (Chromium) | Slower | Python-first; template/preset structure. |
| `claude-shorts` / `@remotion/captions` | MIT / Remotion dual | Yes | Yes (Remotion + CSS) | No (browser render) | Medium | Word-level `Caption` type; bundle-once-render-many pattern. |
| `vanta` | MIT | No implementation | N/A | N/A | N/A | Useful declarative preset schema reference. |

## 8. Implications for the 60+ Preset Goal

To reach 60+ original presets across categories (`VIRAL`, `PODCAST`, `CLEAN`, `STORY`, `GAMING`, `DOCUMENTARY`, `EDUCATIONAL`, `MOTIVATION`, `MEME`, `HIGH_ENERGY`, `KARAOKE`, `CINEMATIC`), ViralMint will likely need:

1. A declarative preset schema (font family, weight, color palette, highlight mode, animation name, layout, category). `vanta` is a good reference.
2. A rendering backend that can execute per-word animations. Options:
   - Keep ASS/FFmpeg and extend with ASS `\t` tag animation (limited expressiveness).
   - Add a CSS + Playwright screenshot renderer similar to `pycaps`.
   - Add a Remotion rendering path similar to `claude-shorts` / `remotion-subtitles`.
3. A word-layout engine to split lines and prevent overflow, as seen in `pycaps` `layout/` and `remotion-subtitles` `subtitleLine.ts`.
4. A way to map requested style names (`Bounce`, `Explosive`, `Glitch`, `Typewriter`, `Karaoke`) to concrete animation parameters. Existing repositories show that:
   - `Bounce` and `Explosive` are spring/interpolate animations.
   - `Glitch` and `Typewriter` are per-character or per-word reveal effects.
   - `Karaoke` is a fill/wipe progress effect tied to word timing.

No source code from these projects was copied during Phase 0; all notes are derived from inspection and documentation.
