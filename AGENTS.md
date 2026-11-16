# AGENTS.md

## What this repo is

Greenfield build of **HypeCut Local**: a free, local-first AI video clipping studio (Windows 11 desktop app). No application code exists yet.

**`HYPECUT_MASTER_PROMPT.md` is the authoritative spec** (2055 lines, Parts 1–25). Read it before building anything. When AGENTS.md and the spec conflict, the spec wins.

## Non-negotiable constraints (from the spec)

- **₹0 budget**: no paid APIs (OpenAI/Gemini/Claude/ElevenLabs/fal.ai), no cloud AI inference, no telemetry, no watermarks, no login. Internet only for yt-dlp downloads and model fetches.
- **Never fake anything**: no fabricated metrics, fake progress, invented heatmap data, hardcoded timestamps as results, or fabricated tests. If a feature is unbuilt, label it as such.
- **Never bypass YouTube DRM/auth/access controls.** Only download videos the user is authorized to use.
- **Backend binds to 127.0.0.1 only**; no `shell=True` with untrusted input.
- **Target hardware** (verified): i5-8250U, 8 GB RAM, MX130 2 GB VRAM, ~50–100 GB free disk. CPU-first, single job at a time, faster-whisper tiny/base default. The 4 GB shared GPU memory is NOT dedicated VRAM. Never assume CUDA/NVENC works — probe FFmpeg capabilities and fall back to CPU.

## Planned stack (spec Part 4)

- Frontend: React + TypeScript + Vite + Tailwind + Framer Motion. Modular components, never one oversized component.
- Backend: Python 3.11–3.13, FastAPI, Uvicorn, Pydantic, SQLite, persistent job queue.
- Pipeline: FFmpeg/FFprobe, yt-dlp, faster-whisper, librosa, OpenCV, PySceneDetect.
- Target repo: `https://github.com/Kanishk3105/HypeCut.git`, branch `main`. Not yet a git repo — init it if building here, but audit first (check existing remotes/history; never force-push or discard work).

## Workflow the spec mandates

1. Work in the spec's 25 phases (PART 21), in order. Do not skip ahead or build disconnected prototypes.
2. Per phase: implement → run relevant tests → fix failures → inspect diff → check for secrets/media/large files → stage intended files only → commit → push → verify commit on `origin/main` → update `docs/DEVELOPMENT_PROGRESS.md` → next phase.
3. Commit convention: `feat(phase-NN): <truthful description>` (also `fix:`, `test:`, `docs:`, `chore:`). One commit per verified phase; never empty commits; never claim PUSHED without verifying remotely. If push is blocked, mark `VERIFIED — PUSH BLOCKED` and record the blocker.
4. A phase is not done until its tests pass. No phase is published until its commit is verified on the remote.

## Git safety (public repo)

- Never stage: `.env`, secrets, model weights, SQLite DBs with user data, downloaded/generated video, logs, `node_modules/`, `.venv/`. Create a comprehensive `.gitignore` before downloading models or media.
- Inspect staged changes before every push. No force-push, no destructive reset/checkout/clean.
- If a secret lands in history: stop, report, rotate the credential — do not silently rewrite history.

## Tests (spec Part 20)

- Backend: pytest. Frontend: testing tools + Playwright.
- Integration tests generate synthetic videos with FFmpeg (no copyrighted media, no multi-GB model downloads in CI).
- Heatmap extraction must be tested against saved fixtures: valid data, multiple peaks, opening artifact, no heatmap, malformed response, network failure.
- CI: `.github/workflows/ci.yml` on push/PR to `main` — free runners only; keep hardware-specific tests local.

## First steps when starting a build session

1. Inspect workspace + actual hardware diagnostics (CPU/RAM/GPU/FFmpeg encoders) before enabling optional features.
2. Research the reference repos (spec PART 2): SharkyClips (primary), realiti4/youtube-context-mcp (replay heatmap — verify actual return structures and MIT licence), moha700m/OpenShorts. Decide extend-vs-rebuild based on real source inspection, not docs.
3. Create `.gitignore` first, then scaffold.
