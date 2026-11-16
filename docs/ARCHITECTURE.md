# HypeCut Local — Architecture

Status: Phase 02 deliverable. Decisions below are based on direct source inspection of the three reference repositories (cloned 2026-11-17, commit depth 1), not on documentation claims.

## 1. Extend vs. rebuild — decision

**Decision: rebuild HypeCut fresh on the spec's stack (Part 4), selectively adapting MIT-licensed components where they are proven, isolated and conflict-free.**

### Why not fork SharkyClips

Inspected: `utkualsir/sharkyclips` (MIT, 15.5 MB, v1.2.50). Backend is FastAPI + faster-whisper + yt-dlp + librosa + sherpa-onnx + opencv + rapidocr; frontend is React 18 + Vite + TypeScript with plain CSS (no Tailwind, no Framer Motion). Verified conflicts with HypeCut's requirements:

- **Identity and UI stack**: SharkyClips is a streamer-publishing product (TikTok/YouTube/Instagram auto-publish via browser automation, 7-language i18n, tray icon, auto-updater). HypeCut requires a Tailwind + Framer Motion design system and none of the publishing surface.
- **OAuth/API-key machinery**: `backend/sharkyclips/youtube.py` implements YouTube Data API OAuth client storage (`google_client.json`), quota accounting and retention purges for the *user's own* uploads. HypeCut forbids mandatory API keys/OAuth; its audience signal is the *public* replay heatmap, which SharkyClips does not extract (its "Hype Map" is local-analysis-driven — `analyze.py`, `highlights/signals/*`).
- **Coupling**: highlights pipeline, captions, render and project code are tightly interwoven with publishing, chat, game-HUD and LLM features we must not ship.
- **No public-replay heatmap code exists there** — the one component HypeCut prioritizes (Part 7) must come from elsewhere anyway.

SharkyClips remains the **primary pattern reference** (single job lane, render flow, signal/scorer structure, facecam detection) — copied ideas, not code.

### Why not fork OpenShorts

Inspected: `moha700m/OpenShorts` (MIT core, 19.7 MB). Verified problems:

- **Licence trap**: `NOTICE` places everything under `cloud/` under the *OpenShorts Commercial License*, not MIT. Never copy from `cloud/`.
- **Paid/heavy stack**: `requirements.txt` includes `google-genai` (Gemini), `boto3` (S3), full `torch`/`ultralytics`/`mediapipe`. Spec forbids paid APIs; torch is unjustified on 8 GB RAM.

Used only as a pattern reference for scene detection, reframing, subtitle timing and split layouts, per-file licence audit before any adaptation.

### What is actually reused

| Component | Source | Licence | How |
|---|---|---|---|
| Replay-heatmap parsing (peak extraction, opening-artifact hold-out, relative-intensity normalization, NMS, region shoulders, 12-bucket profile, `has_data=False` handling) | `realiti4/youtube-context-mcp` → `src/youtube_context_mcp/metadata.py` (`_to_most_replayed`, helpers), tests in `tests/test_metadata.py` | MIT (Onur Cetinkol, 2026) | Adapted into `backend/hypecut/audience/replay.py` as a pure function over yt-dlp's `info["heatmap"]`; attribution in `THIRD_PARTY_NOTICES.md`; fixture-driven tests ported |
| yt-dlp fetch layer (`_extract_info`, error mapping) | same repo | MIT | Adapted; proxy env vars dropped (no proxy requirement in HypeCut) |
| Pipeline/job/render patterns | `utkualsir/sharkyclips` | MIT | Ideas only — no file copied |
| Scene/reframe/subtitle patterns | `moha700m/OpenShorts` (never `cloud/`) | MIT (core) | Ideas only — no file copied |

**Verified heatmap contract** (from `metadata.py:32-50` and `tests/test_metadata.py`):

- Input: yt-dlp `info["heatmap"]` ≈ 100 `{start_time, end_time, value}` segments, value normalized 0..1.
- Output `MostReplayed`: `{video_id, has_data, duration_seconds, peaks[], profile[≤12], note}`.
- Peak: `{peak_label, region_label, peak_start_seconds, region_start_seconds, region_end_seconds, relative_intensity, url, chapter, is_opening}`.
- Rules proven by their tests: opening spike at t≈0 kept but flagged `is_opening` and excluded from content baseline; content floor = `max(0.05, 0.4 × strongest non-opening peak)`; min peak gap = 4% of timeline; missing heatmap ⇒ `has_data=False`, empty peaks, explanatory note — never fabricated values.

## 2. System architecture

```
┌──────────────────────────────┐        HTTP (127.0.0.1:8756)      ┌──────────────────────────────┐
│  Frontend (Vite/React/TS)    │ ◄───────────────────────────────► │  Backend (FastAPI + Uvicorn)  │
│  Tailwind + Framer Motion    │        REST + SSE progress        │  Pydantic schemas             │
│  11 routed sections          │                                   │  SQLite (projects/jobs/clips) │
└──────────────────────────────┘                                   │  Persistent job queue (1 lane)│
                                                                   └──────────────┬───────────────┘
                                                                                  │ subprocess (no shell=True)
                                       ┌──────────────────────────────────────────┼───────────────────┐
                                       ▼                                          ▼                   ▼
                                 yt-dlp (download/metadata/heatmap)      faster-whisper (ASR)   FFmpeg/FFprobe
                                       │                                          │                   │
                                       └──────────────► audience/replay.py ◄──────┘                   │
                                                      highlight scoring (4 signals)                  │
                                                      captions + reframing ◄────────────────────────┘
```

### Backend layout (grows by phase)

```
backend/
  hypecut/
    audit.py              # Phase 01 — environment/workspace audit (done)
    hardware.py           # Phase 03 — hardware diagnostics + encoder probe
    db.py                 # Phase 05 — SQLite schema + connection
    jobs.py               # Phase 05 — persistent single-lane job queue
    api.py / main.py      # Phase 05 — FastAPI app, bound to 127.0.0.1
    ingest/               # Phase 06 — URL validation, yt-dlp, local import
    media.py              # Phase 07 — ffprobe metadata, thumbnails
    transcribe.py         # Phase 08 — faster-whisper
    audience/
      replay.py           # Phase 09 — adapted heatmap parser (MIT, attributed)
      retention.py        # Phase 10 — owner CSV import
      markers.py          # Phase 11 — manual timestamps
    analysis/             # Phase 13/14 — audio, scene, gaming signals
    scoring.py            # Phase 15 — ranking + duplicate suppression
    captions/             # Phase 17 — SRT/VTT/ASS + templates
    render.py             # Phase 20/21 — FFmpeg render, profiles, encoder fallback
  tests/
```

### Frontend layout (Phase 04)

```
frontend/
  src/
    app/          # router, layout, nav (11 sections)
    components/   # design-system primitives (cards, timeline, player, forms)
    features/     # dashboard, ingest, audience, highlights, studio, queue, models, hw, settings
    lib/          # API client (fetch + SSE), types, formatters
```

### Key runtime rules

- Backend binds `127.0.0.1` only; frontend dev server proxies `/api` to it.
- One heavy job at a time (matches spec Part 17 and the verified 8 GB machine); queue persists in SQLite and recovers after restart.
- All subprocess calls use argument arrays (`shell=False`), timeouts and output caps.
- Signal provenance is first-class: every score carries `PUBLIC_YOUTUBE_REPLAY | OWNER_RETENTION | LOCAL_AI_ESTIMATE | MANUAL_MARKER`; missing replay ⇒ weights renormalized and result labelled `LOCAL_AI_ESTIMATE`.
- Encoder selection is probed from real `ffmpeg -encoders` output at runtime (Phase 03), never assumed from GPU name.

## 3. Licence audit summary

| Repo | Licence | Notes |
|---|---|---|
| realiti4/youtube-context-mcp | MIT | Source of the heatmap adapter; keep copyright notice |
| utkualsir/sharkyclips | MIT | Patterns only; do not copy branding/assets |
| moha700m/OpenShorts | MIT (core) + **Commercial (cloud/**) | Never copy `cloud/`; audit any adapted file |
| faster-whisper / FFmpeg / yt-dlp / PySceneDetect | MIT / LGPL-2.1+ / Unlicense / Apache-2.0 | invoked as libraries/binaries; notices collected in `THIRD_PARTY_NOTICES.md` at Phase 25 |

All model downloads (Whisper) are user-initiated via the Model Manager; CI never downloads weights.
