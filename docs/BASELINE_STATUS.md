# Baseline Status

This document records the exact commands executed and their results to establish the Phase 0 baseline for ViralMint. All runs were performed in `/home/ubuntu/repos/viralmint` unless otherwise noted.

## Environment

- **OS:** Ubuntu (Devin sandbox)
- **Original Python:** `3.10.12` (did not satisfy `requires-python = ">=3.11"` in `pyproject.toml` / `run.py`)
- **Installed Python:** `3.11.0rc1` via `apt` (`python3.11`, `python3.11-venv`, `python3.11-dev`)
- **Node.js:** `v20.18.1`
- **npm:** `10.8.2`
- **FFmpeg:** `4.4.2`
- **FFprobe:** `4.4.2`
- **ImageMagick:** `convert` present at `/usr/bin/convert`; no `magick` binary.

## Installation and Verification Commands

### 1. Python virtual environment (3.11) and dependencies

```bash
python3.11 -m venv venv311
source venv311/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Result: dependencies installed successfully into `venv311`.

### 2. Backend tests

Command:

```bash
source venv311/bin/activate
pytest tests/ -q
```

Output:

```
........................................................................ [ 66%]
....................................                                     [100%]
=============================== warnings summary ===============================
venv311/lib/python3.11/site-packages/_pytest/config/__init__.py:1464
  /home/ubuntu/repos/viralmint/venv311/lib/python3.11/site-packages/_pytest/config/__init__.py:1464: PytestConfigWarning: Unknown config option: asyncio_mode

    self._warn_or_fail_on_strict(f"Unknown config option: {key}\n")

-- Docs: https://docs.pytest.org/en/stable/warnings.html
108 passed, 1 warning in 0.42s
```

Status: **PASS**. The warning is a pytest config parsing warning (`asyncio_mode` is set in `pyproject.toml` but is provided by `pytest-asyncio`, which is not installed).

### 3. Ruff lint

Command:

```bash
source venv311/bin/activate
ruff check backend tests --select=E9,F63,F7,F82 --output-format=github
```

Output:

```
```

(Empty output, exit code 0.)

Status: **PASS**.

### 4. Frontend build

Command:

```bash
cd frontend
npm install
npm run build
```

Output (truncated to key lines):

```
> viralmint-ui@1.0.0 build
> vite build

vite v5.4.21 building for production...
transforming...
✓ 1373 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                             1.20 kB │ gzip:   0.63 kB
...
dist/assets/index-maFGmaVE.js                             731.76 kB │ gzip: 231.24 kB

(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rollupOptions.output.manualChunks to improve chunking: https://rollupjs.org/configuration-options/#output-manualchunks
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
✓ built in 4.96s
```

Status: **PASS** with a Vite chunk-size warning. The production bundle was emitted successfully to `frontend/dist/`.

### 5. Application startup (`run.py`)

Command:

```bash
source venv311/bin/activate
python run.py
```

Output (key lines):

```
🔥 ViralMint starting up...

✅ Python 3.11.0rc1
📋 Created .env from .env.example — please fill in your API keys
✅ Storage directories ready
✅ ImageMagick found
✅ Node.js v20.18.1
✅ Database ready
🏗️  Building frontend...
✅ Frontend built
✅ API server started at http://localhost:16888 (PID ...)
✨ ViralMint running at http://localhost:16888
```

Status: **PASS**. The server started, served the built SPA, and responded to API requests.

Runtime warnings observed:

```
neonize unavailable — WhatsApp channel disabled: ImportError: failed to find libmagic
```

This is non-fatal; Telegram/Discord/Slack messaging may still initialize if configured. WhatsApp support is disabled because `python-magic`/libmagic is not available in the environment.

### 6. API smoke test

Command:

```bash
curl -s http://127.0.0.1:16888/api/videos | head -c 200
```

Output:

```json
{"total":0,"videos":[]}
```

Status: **PASS**. The FastAPI backend serves API routes and the SPA catch-all works.

## Pre-existing Issues / Notes

1. **Python 3.11 requirement.** `run.py` and `pyproject.toml` require Python 3.11+. The default system Python was 3.10.12, so `run.py` exited immediately before Python 3.11 was installed. Workaround applied: installed `python3.11` and created `venv311`.
2. **pytest warning.** `pyproject.toml` sets `asyncio_mode = "auto"` under `[tool.pytest.ini_options]`, but `pytest-asyncio` is not in `requirements.txt` or `pyproject.toml`. pytest therefore logs: `PytestConfigWarning: Unknown config option: asyncio_mode`. Tests still pass because the suite is synchronous or uses FastAPI `AsyncClient` correctly.
3. **Frontend chunk size.** Vite warns that `dist/assets/index-maFGmaVE.js` is > 500 kB after minification. This is a build optimization issue, not a failure.
4. **WhatsApp dependency.** `neonize` raises `ImportError: failed to find libmagic` at startup, causing WhatsApp messaging to be disabled. This is environment-specific and can be resolved by installing `libmagic1` (system package) and ensuring `python-magic` binaries are visible.
5. **FFmpeg 4.4.2.** The build is older. For future phases that add modern filters or `libass` features, verify filter availability with `ffmpeg -filters` and `ffmpeg -buildconf`.
6. **No `.env` on first run.** `run.py` created `.env` from `.env.example`; `SECRET_KEY` and `ENCRYPTION_KEY` are auto-generated by `backend/config.py` at runtime.

## Baseline Conclusion

The repository is installable, testable, lint-clean, and runnable on Python 3.11. The frontend builds. The backend starts and serves the SPA and API. Phase 0 baseline is established and ready for Phase 1.
