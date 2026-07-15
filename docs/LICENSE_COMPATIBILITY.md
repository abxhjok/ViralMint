# License Compatibility

This document records the license status of the ViralMint project and the open-source projects/dependencies researched during Phase 0. It is intended to guide future incorporation of third-party code, algorithms, and assets.

## 1. ViralMint

- **Project:** `ViralMint` (`https://github.com/abxhjok/ViralMint`)
- **License:** GNU Affero General Public License v3.0 only (`AGPL-3.0-only`)
- **Evidence:** `LICENSE` file contains the full AGPL-3.0 text; `pyproject.toml` declares `license = { text = "AGPL-3.0-only" }`; source files carry SPDX headers `# SPDX-License-Identifier: AGPL-3.0-only`.

### Key obligations

- The complete source code must be provided to anyone who interacts with the software over a network.
- Modifications distributed or publicly used must be under AGPL-3.0.
- No proprietary/closed-source modules may be linked into the public network version unless their license is compatible with AGPL-3.0.

## 2. Referenced Open-Source Projects

| Project | License | Compatible with AGPL-3.0? | Notes |
|---------|---------|---------------------------|-------|
| `itsjwill/vanta` | MIT | Yes | Copyright notice must be preserved. Source can be read, algorithms adapted, and original code used if license is included. No code was copied in Phase 0. |
| `ahgsql/remotion-subtitles` | MIT | Yes | Same as above. 17 Remotion caption components; no code copied in Phase 0. |
| `francozanardi/pycaps` | MIT | Yes | Same as above. Python caption/clip pipeline; no code copied in Phase 0. |
| `AgriciDaniel/claude-shorts` | MIT | Yes | Same as above. Contains scoring rubric, boundary snapping, reframe, and Remotion render scripts; no code copied in Phase 0. |
| `@remotion/captions` | MIT (per `packages/captions/package.json`) | Yes | The data primitives package is MIT. If used, preserve copyright notice. |
| Remotion core renderer (`remotion-dev/remotion`) | Custom dual free/company license | **Conditional** | Free for individuals, non-profits, and for-profits with ≤3 employees; company license required for larger for-profit use. Network use triggers AGPL-style source obligations when combined with an AGPL project. See https://github.com/remotion-dev/remotion/blob/main/LICENSE.md. |

## 3. Key Dependency Licenses

The full dependency list is in `THIRD_PARTY_NOTICES.md`. The following categories are particularly important for an AGPL project:

| Dependency | License | Notes |
|------------|---------|-------|
| `fastapi`, `uvicorn`, `sqlalchemy`, `aiosqlite` | MIT / BSD-3-Clause | Compatible. |
| `faster-whisper` | MIT | Compatible. Model weights are OpenAI Whisper (research license; see `openai/whisper`). |
| `moviepy` | MIT | Compatible. |
| `Pillow` | MIT-CMU | Compatible. |
| `anthropic`, `openai` Python SDKs | MIT / Apache-2.0 | Compatible. Usage is subject to each provider's Terms of Service. |
| `yt-dlp` | Unlicense | Public domain; compatible. |
| `edge-tts` | LGPL-3.0-only | Compatible with AGPL. The library uses the public Microsoft Edge TTS endpoint; end users must respect Microsoft's terms. |
| `python-telegram-bot` | LGPL-3.0-only | Compatible. |
| `playwright` | Apache-2.0 | Compatible. Browser binaries have their own licenses (Chromium, Firefox, WebKit). |
| `react`, `react-dom`, `vite`, `@mui/*`, `zustand`, `axios`, `lucide-react` | MIT / ISC | Compatible. |
| `@fontsource/inter` | OFL-1.1 (font) | Font is redistributable under SIL Open Font License with attribution. |
| `caniuse-lite` | CC-BY-4.0 | Data license; compatible for build-time use. |

## 4. What Can Be Incorporated

### Safe to incorporate (with attribution)

- **MIT-licensed code** from `vanta`, `remotion-subtitles`, `pycaps`, `claude-shorts`, `@remotion/captions`, and MIT npm packages, as long as the original copyright notice and permission notice are preserved in `THIRD_PARTY_NOTICES.md` and source files where code is copied/adapted.
- **Apache-2.0 code** (e.g., `playwright`, `openai` SDK, Google API clients) can be used in an AGPL-3.0 project; preserve NOTICE files and license headers.
- **LGPL-3.0 libraries** (e.g., `edge-tts`, `python-telegram-bot`) can be dynamically linked/used in AGPL projects.
- **Unlicense code** (`yt-dlp`) can be used freely.

### Requires additional care

- **Remotion renderer itself.** Using `@remotion/renderer`, `@remotion/bundler`, or any render entrypoint to produce video may require a company license depending on the legal entity and usage. The `@remotion/captions` MIT package alone does not require a company license, but it is only data primitives. Any plan to render with Remotion must include a licensing review.
- **Fonts and media assets.** Only use fonts and media assets with explicit redistribution rights (OFL, CC-BY with appropriate attribution, self-created). Do not copy CapCut, TikTok, or other proprietary assets, fonts, or branding.
- **Model weights.** `faster-whisper` uses OpenAI Whisper model weights. These are typically used under OpenAI's Whisper license (non-exclusive, research-oriented). Review the model license before redistribution of the weights.

## 5. What Must Be Avoided

- **Proprietary code, assets, templates, fonts, or branding** from CapCut, TikTok, Instagram, YouTube, or any closed source. This is explicitly forbidden by the project instructions.
- **GPL-incompatible components** that would force a license change or prevent network-distribution under AGPL. When in doubt, check the FSF license list or OSI list.
- **Remotion unlicensed use** by organizations that exceed the free-license employee limit.

## 6. Record-keeping Requirements

Before adapting code or assets from another project in future phases:

1. Verify the current license from the source repository or package metadata.
2. Check package-level licensing where the project is a monorepo (e.g., Remotion).
3. Confirm compatibility with `AGPL-3.0-only`.
4. Preserve copyright notices and license text.
5. Record copied or substantially adapted code in `THIRD_PARTY_NOTICES.md`.
6. Add SPDX or header comments in source files where third-party code is embedded.

## 7. Summary

All referenced open-source projects from the Phase 0 spec (`vanta`, `remotion-subtitles`, `pycaps`, `claude-shorts`) are MIT-licensed and compatible with ViralMint's AGPL-3.0 license, provided copyright notices are preserved. The Remotion core renderer has a special dual license and must be evaluated separately before use. The existing dependency stack is broadly AGPL-compatible. No third-party source code was copied during Phase 0.
