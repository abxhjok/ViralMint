# Repository Analysis

This document captures the real architecture discovered in the ViralMint repository during Phase 0. It is not a design spec; it reflects files and behavior that exist today.

## Repository Metadata

- **Repository path on disk:** `/home/ubuntu/repos/viralmint`
- **Upstream:** `https://github.com/abxhjok/ViralMint`
- **License:** GNU Affero General Public License v3.0 (`AGPL-3.0-only`)
- **Primary language/framework stack:**
  - Backend: Python 3.11+, FastAPI, SQLAlchemy 2.0 async, SQLite via `aiosqlite`
  - Frontend: React 18, Vite 5.4, MUI 7, Zustand, React Router 6
  - Video/Audio: FFmpeg 4.4.2, FFprobe 4.4.2, Pillow 12.3, MoviePy 1.0.3
  - AI transcription: `faster-whisper` (local Whisper with word timestamps)
  - AI orchestration: BYOK Anthropic / OpenAI / OpenRouter clients
  - Runtime: Uvicorn serving FastAPI; `run.py` as the entry point

## Directory Layout

```
ViralMint/
├── backend/            # FastAPI backend + agents + services + models
│   ├── main.py         # Application factory and lifespan
│   ├── config.py       # Pydantic Settings + .env handling + secret generation
│   ├── database.py     # SQLAlchemy async engine, session, init, WAL pragmas
│   ├── api/            # FastAPI routers
│   ├── core/           # Logging, AI provider, exceptions, plugins, task runner
│   ├── services/       # Whisper, FFmpeg, captions, clip extraction, TTS, etc.
│   ├── models/         # SQLAlchemy declarative models
│   └── agents/         # Planner, Scout, Analyzer, Generator, Uploader, Downloader
├── frontend/           # Vite + React SPA
│   ├── src/
│   │   ├── pages/      # ClipStudio, Videos, Settings, Chat, Channels, Messaging, etc.
│   │   ├── components/ # Reusable UI and page-specific sections
│   │   └── hooks/      # Zustand-backed data hooks
│   └── package.json    # React 18, MUI 7, Vite 5.4, Zustand, axios, react-router-dom
├── tests/              # pytest suite (108 tests pass)
├── run.py              # Entry point: checks, .env init, npm build, uvicorn
├── requirements.txt    # Python dependencies
├── pyproject.toml      # Project metadata + ruff + pytest config
└── .env.example        # BYOK API keys and loopback app config
```

## Backend Architecture

### Application Factory (`backend/main.py`)

- `create_app()` builds the FastAPI app with an async `lifespan`.
- Lifespan performs, with guarded exception handling:
  1. `init_db()` to create tables and idempotent migrations.
  2. Marks orphaned `pending`/`running` jobs as failed.
  3. Calls `ensure_sfx_dir()` for sound effects.
  4. Calls `check_ytdlp_version()`.
  5. Starts messaging channels (Telegram, WhatsApp, Discord, Slack) and wires the `PlannerAgent` callback.
- CORS allows `FRONTEND_URL`, `http://localhost:5173`, and `http://localhost:3000`.
- API routers are mounted under `/api`:
  - `chat`, `jobs`, `scout`, `settings`, `videos`, `downloaded`, `chat_sessions`, `media`, `config`, `channels`, `news`, `generate`, `templates`, `captions`, `tools`, `messaging`.
- Proprietary overlay support via `backend/core/plugins`.
- Serves the built frontend SPA from `frontend/dist` (or `VIRALMINT_FRONTEND_DIST`), with `/assets` static mount and a catch-all route for SPA navigation.

### Configuration (`backend/config.py`)

- Pydantic `Settings` reads `.env` with `case_sensitive=False`, `extra="ignore"`.
- Defaults:
  - `HOST=127.0.0.1`, `PORT=16888`
  - `DATABASE_URL="sqlite+aiosqlite:///./viralmint.db"`
  - `FRONTEND_URL="http://localhost:5173"`
- BYOK fields: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, plus `YOUTUBE_API_KEY`, `TIKHUB_API_KEY`, `PEXELS_API_KEY`.
- `SECRET_KEY` and `ENCRYPTION_KEY` are auto-generated and appended to `.env` on first run.
- Storage paths are `Path` properties (`storage/videos`, `storage/audio`, `storage/generated`, `storage/thumbnails`, `storage/tmp`).

### Database (`backend/database.py`)

- Async engine: `create_async_engine(settings.DATABASE_URL, echo=DEBUG, check_same_thread=False)`.
- Pragmas at connection (WAL mode, `synchronous=NORMAL`, `busy_timeout=5000`, `cache_size=-64000`, `foreign_keys=ON`).
- `get_db()` yields async sessions with auto-rollback on failure.
- `init_db()` imports all models and calls `Base.metadata.create_all()`.
- Idempotent migrations are performed with `_add_column_if_missing()` for fields such as `transcript_segments_json`, `source_type`, `clip_*`, `caption_status`, `metadata_status`, and encrypted BYOK fields on `user_settings`.
- Zombies (`pending`/`running` jobs) are marked as failed on startup.

### Models

Key SQLAlchemy models observed:
- `UserSettings` — BYOK provider, model, keys, Whisper quality, TTS, caption style, SFX, music, upload preferences.
- `GeneratedVideo` — rendered video paths, platform metadata, upload status, `source_type`, `source_downloaded_video_id`, clip fields (`clip_start_seconds`, `clip_end_seconds`, `clip_virality_score`, `clip_virality_reason`, `caption_status`, `metadata_status`).
- `DownloadedVideo` — downloaded source videos, transcripts (`transcript_segments_json`), metadata.
- `CaptionStyle` — custom CSS-style caption presets (font, colors, sizes, outline, alignment, margin, `words_per_group`, `is_ai_generated`, `description`).
- `Job` — async job status tracking.

### Services

#### Whisper Service (`backend/services/whisper_service.py`)

- Singleton `WhisperService` loads `faster-whisper` on CPU with `int8`.
- `WHISPER_QUALITY_MAP`: `fast→base`, `balanced→small`, `accurate→medium`, `best→large-v3`.
- `transcribe()` returns text, language, segments, and word-level timestamps.

#### Caption Service (`backend/services/caption_service.py`)

- `EMOJI_KEYWORDS` map triggers automatic emoji insertion for phrases such as "love", "fire", "rocket", "money", etc.
- `CAPTION_STYLES` defines built-in ASS presets: `viral`, `classic`, `bold`, `neon`, `minimal`, `karaoke`, `glow`. Each contains font, colors, outline, shadow, alignment, margin, `words_per_group`.
- `_extract_word_timestamps()` flattens Whisper segments into words, enforcing monotonic start/end ordering.
- `_generate_ass_events()` groups words by `words_per_group` and emits ASS dialogue lines with a single highlighted word per event using `{\1c&H...}` color override.
- `generate_captions_ass()` writes an ASS file to disk.
- `burn_captions()` invokes FFmpeg `ass=` filter.
- ASS output supports `insert_emojis_into_words()` with `none`, `moderate`, `aggressive` modes.

##### Caption Core (`backend/caption_core/`)

Phase 1 added a deterministic, validated caption timing layer underneath the
ASS pipeline. It provides `CaptionWord`, `CaptionSegment`, `CaptionStyle`,
`CaptionAnimation`, and `CaptionPreset` models, source/clip-local timing helpers,
active-word lookup, and deterministic segmentation. The existing ASS renderer is
consumed through a small bridge in `backend/caption_core/ass_bridge.py` that
converts core structures into the legacy segment/style dictionaries expected by
`caption_service.generate_captions_ass()`. See `docs/CAPTION_CORE_DESIGN.md`.

#### FFmpeg Service (`backend/services/ffmpeg_service.py`)

- `extract_clip()` cuts a source video between start/end and reframes to 9:16 with blur-fill for landscape input using an FFmpeg filter graph:

  ```
  split[original][bg];
  [bg]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5[blurred];
  [original]scale=1080:1920:force_original_aspect_ratio=decrease[scaled];
  [blurred][scaled]overlay=(W-w)/2:(H-h)/2
  ```

- Also implements `add_captions` (SRT-based with `-vf subtitles=`), `stitch_clips`, `add_audio_to_video`, `extract_thumbnail`, `generate_text_video` (Pillow + ffmpeg slide), and `generate_kenburns_video`.

#### Clip Extractor (`backend/services/clip_extractor.py`)

This is the core short-form clipping engine.

- Entry point: `extract_viral_clips(video, user_settings, max_clips=3, caption_style="viral", whisper_quality="balanced", force_retranscribe=False, job_id=None, user_id="local", min_duration=None, max_duration=None)`.
- Pipeline:
  1. Load/transcribe the source video if not cached.
  2. Estimate realistic clip count from duration/requested max.
  3. Build an AI prompt (`CLIP_SELECTION_PROMPT`) that asks the model to return a JSON array of clips with `start`, `end`, `title`, `hook`, `reason`, `virality_score` (1–10).
  4. Retry/chunk the AI call if JSON parsing fails.
  5. Validate and deduplicate windows with `_remove_overlapping_clips()` (2 s tolerance).
  6. `_process_clips_parallel()` extracts each clip (`extract_clip`), burns captions (`generate_captions_ass` + `burn_captions`), generates thumbnails, and writes metadata.
- Deduplication: `_remove_overlapping_clips()` keeps the first (already scored) clip and drops any later clip that overlaps by more than 2 s.
- Selection: `_select_clip_windows()` iteratively calls `_get_ai_client` for JSON suggestions, trims to `min_duration`/`max_duration`, and removes overlaps.
- Output is a list of dicts containing `video_path`, `thumbnail_path`, `title`, `hook`, `reason`, `virality_score`, `start`, `end`, etc.

The scoring weights from the Phase 0 spec (Hook Strength 30%, Standalone Coherence 20%, etc.) are **not encoded as a formula** in the current code; they are only part of the prompt instructions. The AI returns a 1–10 `virality_score`.

#### AI Provider (`backend/core/ai_provider.py`)

- `AIClient` abstraction supports Anthropic, OpenAI, OpenRouter.
- Provider defaults:
  - Anthropic: `claude-sonnet-4-6`
  - OpenAI: `gpt-5.4-mini`
  - OpenRouter: `anthropic/claude-opus-4.7`

### Task Runner / Agents (`backend/core/task_runner.py` and `backend/agents/`)

- `task_runner.py` exposes an in-process asyncio task runner with `dispatch()`, `run_generate`, `run_scout`, `run_download`, `run_batch_download`, `run_upload`, etc.
- `agents/generator.py`, `agents/generator_video.py`, `agents/uploader.py`, `agents/scout.py`, `agents/downloader.py`, `agents/analyzer.py`, `agents/planner.py`, and `agents/news_scout.py` implement the agent logic.
- `agents/job_helper.py` creates `Job` rows and updates progress/status.

### API Routers (`backend/api/`)

- `videos.py` — list/get generated videos, with self-healing pruning of orphaned rows.
- `generate.py` — stock footage generation and `split-scenes` AI script splitting.
- `captions.py` — CRUD for custom caption styles and built-in style list.
- `tools.py` — 18 single-purpose tools: captions, reframe, audio-enhance, watermark, merge-clips, remove-silence, translate, hook-analysis, voiceover, transform, enhance-prompt, etc.
- `settings.py` — user settings, provider/key management, OAuth callbacks.
- `scout.py`, `channels.py`, `messaging.py`, `chat_sessions.py`, `config.py`, `jobs.py`, `templates.py`, `media.py`, `downloaded.py`, `news.py`, `tools.py`.

## Frontend Architecture

- Vite SPA served from `frontend/dist`.
- `vite.config.js` proxies `/api` and `/ws` to `localhost:16888` in dev mode.
- React Router 6 routes are defined in `App.jsx`.
- Key pages:
  - `ClipStudio.jsx` — main short-form workstation: source sidebar, clip filmstrip, video preview, metadata editing, extract dialog (`whisper_quality`, `caption_style` selection).
  - `Videos.jsx` — library of generated videos and downloaded sources.
  - `Settings.jsx` — AI provider, BYOK keys, health dashboard.
  - `Chat.jsx` — streaming WebSocket planner interface.
  - `Channels.jsx`, `Messaging.jsx` — integrations.
- Zustand stores manage settings, jobs, clips, source videos.
- MUI 7 + Emotion for styling; `lucide-react` for icons.

## Configuration and Runtime Entry Point

- `run.py` enforces Python 3.11+, creates `.env` from `.env.example` if missing, ensures storage dirs, checks ImageMagick (`magick` or `convert`), checks Node.js, runs `init_db()`, installs npm deps, builds the frontend, and starts uvicorn.
- The script binds to `127.0.0.1` by default to honor the "100% local" claim.

## What Currently Works

- Backend installs and starts with Python 3.11.
- `pytest` reports `108 passed`.
- `ruff check backend tests --select=E9,F63,F7,F82` is clean.
- `npm run build` produces `frontend/dist/` (with a chunk-size warning from Vite but no errors).
- The API serves the SPA and responds to `/api/videos` etc.

## Known Gaps / Observations Relevant to Phase 1

- The clip extractor is entirely prompt-driven for scoring; there is no deterministic weighted scoring formula or numeric rubric exposed in code.
- No automated proxy/low-resolution workflow; transcription runs on the original source file.
- No silence-based cut-boundary snapping; cut points come directly from AI JSON.
- Auto-reframe is limited to a static blur-fill center crop for landscape sources. There is no face tracking, speaker tracking, or content-aware crop keyframing.
- Caption system is ASS-based and generates color overrides per group of words. It is not frame-accurate to individual words and is not as visually flexible as Remotion/CSS-based approaches.
- Only 7 built-in ASS caption styles exist (`viral`, `classic`, `bold`, `neon`, `minimal`, `karaoke`, `glow`). The requested 60+ style presets (Bounce, Explosive, Glitch, Typewriter, Karaoke, etc.) will require a new preset schema and likely a new rendering path.
- FFmpeg 4.4.2 is older; some modern filters may be unavailable. Verify before relying on newer `libass` features.
