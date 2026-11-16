# HYPECUT LOCAL — ULTIMATE MASTER BUILD SPECIFICATION

## A complete, zero-cost, local-first AI video intelligence, clipping and editing studio

**ROLE**

Operate as an elite autonomous engineering team comprising:

- Principal Software Architect
- Senior Full-Stack Engineer
- Senior Python Engineer
- AI/ML Engineer
- Computer Vision Engineer
- Audio Processing Engineer
- Video Rendering Engineer
- Frontend/UI/UX Architect
- Windows Systems Engineer
- Security Engineer
- QA and Automation Engineer

Your responsibility is to research, architect, implement, integrate, test, debug and deliver a genuinely functional Windows application named **HypeCut Local**.

This is an engineering execution task, not a brainstorming exercise.

Do not stop after producing a plan, architecture diagram, landing page, mockup or collection of disconnected components.

Build the actual application.

---

# PART 1 — PRODUCT VISION

## 1. What we are building

HypeCut Local is a private, local-first AI video clipping studio inspired by:

- OpusClip
- Vizard AI
- 2short.ai
- SharkyClips
- OpenShorts
- Professional short-form video editing applications

The application must combine their most useful capabilities into one independently branded desktop-friendly application.

The primary objective:

A user pastes a YouTube video URL or imports a local video.

HypeCut automatically:

1. Retrieves available video information.
2. Downloads an authorized source or imports the supplied file.
3. Analyses YouTube's public Most Replayed heatmap where available.
4. Finds the most interesting moments using actual available audience signals.
5. Transcribes the video locally.
6. Detects exciting, funny, surprising and memorable moments.
7. Ranks potential clips.
8. Generates multiple separate clips.
9. Automatically creates synchronized subtitles.
10. Adds attractive animated captions and contextual emojis.
11. Automatically reframes the video where appropriate.
12. Renders clean MP4 files.
13. Provides individual download options.

The application should require minimal manual intervention.

## 2. Fundamental product principles

Non-negotiable:

- ₹0 investment.
- No paid subscriptions.
- No credit system.
- No paid AI APIs.
- No OpenAI API.
- No Gemini API.
- No Claude API.
- No ElevenLabs API.
- No fal.ai.
- No cloud AI inference.
- No mandatory login.
- No compulsory cloud account.
- No application-generated watermarks.
- No forced branded outro.
- No telemetry.
- No unnecessary third-party dependencies.
- No artificial clip-generation limits.
- No fake progress.
- No fabricated engagement statistics.
- No fake AI analysis.
- No nonfunctional controls.

All AI processing must run locally using free models and open-source software.

Clarification: Internet access is needed when retrieving authorized YouTube videos, accessing public video metadata and downloading selected models. The prohibition is on paid APIs and external AI inference, not ordinary internet connectivity.

Never bypass YouTube DRM, authentication, access controls or download restrictions.

The user must have the right to download and repurpose the source material.

---

# PART 2 — RESEARCH BEFORE DEVELOPMENT

## 3. Study existing open-source projects

Before implementing the system, inspect the following repositories and their current source code.

### Primary reference: SharkyClips

[https://github.com/utkualsir/sharkyclips](https://github.com/utkualsir/sharkyclips)

Study:

- Existing video ingestion.
- Local AI processing.
- Highlight detection.
- Hype Map.
- Streamer and gameplay detection.
- Audio analysis.
- Chat replay analysis.
- Whisper integration.
- Ollama integration.
- FFmpeg rendering.
- Subtitle generation.
- Job queues.
- Resource management.
- Windows installation.

Treat this as the primary technical reference because it already implements many of our target capabilities.

### Audience intelligence reference: YouTube Context MCP

[https://github.com/realiti4/youtube-context-mcp](https://github.com/realiti4/youtube-context-mcp)

Study:

- get_most_replayed
- get_transcript
- get_video_metadata
- get_video_frame
- get_video_preview
- YouTube replay heatmap extraction.
- Relative intensity calculation.
- Opening artifact filtering.
- Missing heatmap handling.

Check the actual source code and MIT licence.

Understand the exact returned data structures before integrating anything.

### Additional reference: OpenShorts

[https://github.com/moha700m/OpenShorts](https://github.com/moha700m/OpenShorts)

Study:

- Automatic clipping.
- Subtitle timing.
- Smart aspect-ratio conversion.
- Face tracking.
- Split-screen layouts.
- Clip preview.

Do not make its Gemini, ElevenLabs, fal.ai or Docker-dependent capabilities mandatory.

### Additional technical references

[https://github.com/SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)

[https://github.com/Breakthrough/PySceneDetect](https://github.com/Breakthrough/PySceneDetect)

[https://github.com/FFmpeg/FFmpeg](https://github.com/FFmpeg/FFmpeg)

[https://github.com/yt-dlp/yt-dlp](https://github.com/yt-dlp/yt-dlp)

## 4. Repository strategy

Do not reinvent working components unnecessarily.

First determine whether extending SharkyClips is better than rebuilding all functionality from scratch.

Preferred approach:

- Reuse or adapt reliable MIT-licensed components.
- Preserve required copyright and attribution notices.
- Keep HypeCut's own identity, interface and project structure.
- Integrate the audience intelligence functionality properly.
- Remove dependencies on paid services from any reused workflow.
- Do not copy proprietary branding, templates or assets.
- Audit the licences of every added dependency and model.

Do not assume a feature exists merely because the reference repository documents it.

Actually inspect and test the source code.

If adapting SharkyClips would create technical conflicts, explain the reason and build the necessary component independently.

---

# PART 3 — VERIFIED HARDWARE PROFILE

## 5. Target development machine

The application must be designed specifically around this machine.

Laptop: ASUS VivoBook 15 X507UF

Operating system:

- Windows 11 Home Single Language, 64-bit.
- Build 26200.

CPU:

- Intel Core i5-8250U.
- 1.60 GHz.
- 4 physical cores and 8 logical processors.

RAM:

- 8 GB system memory.

Dedicated GPU:

- NVIDIA GeForce MX130.
- Approximately 2 GB dedicated VRAM.

Integrated GPU:

- Intel UHD Graphics 620.
- Shared graphics memory.

NVIDIA driver shown in DxDiag:

- Version 30.0.15.1169.
- February 2022.

Free storage:

- Approximately 50–100 GB.

Important:
The 4 GB shared graphics memory is not dedicated VRAM. Never treat the combined graphics-memory figure as the GPU's dedicated VRAM.

## 6. Hardware optimization

The application must always have a working CPU-only mode.

Recommended defaults:

- faster-whisper.
- Whisper Tiny for fast processing.
- Whisper Base INT8 as the standard transcription option.
- Whisper Small as an optional higher-quality model.
- Local deterministic highlight detection.
- CPU-first video analysis.
- Single-job processing by default.

Local LLM:

- Optional.
- Disabled by default.
- Never necessary for the core application.
- Never automatically downloads a large model.
- Never assumes sufficient VRAM.
- Only enabled after actual resource compatibility testing.

GPU:

- Test NVIDIA CUDA compatibility.
- Test whether FFmpeg supports NVENC.
- Test Intel Quick Sync independently.
- Do not assume compatibility from the GPU name.
- Do not assume modern CUDA support on the old driver.
- Fall back to CPU without crashing.

Memory:

- Avoid multiple simultaneous inference jobs.
- Release model memory after use.
- Process long video/audio in chunks.
- Use disk-backed temporary files when sensible.
- Keep previews lightweight.
- Prevent browser memory exhaustion.
- Implement a configurable cache limit.
- Show actual RAM, VRAM and storage usage when available.

Rendering:

- 720p and 1080p should be the primary targets.
- 1440p and 2160p must remain available as advanced options.
- Show performance warnings for high-resolution rendering.
- Never claim native 4K when the source is lower resolution.

Do not promise real-time processing or fast 4K rendering on this machine.

The coding agent must run actual hardware diagnostics before enabling optional features.

---

# PART 4 — TECHNICAL ARCHITECTURE

## 7. Frontend

Preferred technologies:

- React.
- TypeScript.
- Vite.
- Tailwind CSS.
- Framer Motion.
- Lucide icons.
- A reliable video preview player.
- Accessible component architecture.

Use a maintainable modular structure.

Do not produce an oversized single React component.

## 8. Backend

Preferred technologies:

- Python 3.11–3.13, subject to package compatibility.
- FastAPI.
- Uvicorn.
- Pydantic.
- SQLite.
- Persistent job queue.
- Structured logging.
- Typed service interfaces.

## 9. Video and AI components

Use:

- FFmpeg.
- FFprobe.
- yt-dlp.
- faster-whisper.
- NumPy.
- SciPy.
- librosa.
- OpenCV.
- PySceneDetect.
- YouTube Context MCP functionality or its properly licensed extracted components.
- Optional Ollama for compatible hardware.

For the YouTube replay component, prefer a direct local Python integration where practical.

Do not introduce a hosted MCP service or paid API as a dependency.

If local MCP integration is more reliable, use a local subprocess or local service bound to 127.0.0.1.

Pin compatible dependency versions.

---

# PART 5 — COMPLETE APPLICATION INTERFACE

## 10. Design language

Create a genuinely premium AI video production interface.

Design direction:

- Professional creative software.
- Sophisticated dark theme.
- Optional light theme.
- Modern typography.
- Clean spacing.
- Subtle gradients.
- Restrained Framer Motion animations.
- High-quality video thumbnails.
- Interactive timeline.
- Professional cards.
- Consistent component system.
- Responsive layouts.
- Clear errors and loading states.

Avoid:

- Generic AI landing-page designs.
- Excessive gradients.
- Random glowing effects.
- Decorative charts with invented data.
- Unnecessary dashboard metrics.
- Nonfunctional buttons.
- Fake processing animations.

## 11. Navigation

Create these functional sections:

1. Dashboard
2. New Project
3. Video Library
4. Audience Intelligence
5. AI Highlights
6. Clip Studio
7. Render Queue
8. Export History
9. Model Manager
10. Hardware & Performance
11. Settings

Every navigation item must lead to a functioning page.

## 12. Dashboard

Show real information:

- Recent projects.
- Imported videos.
- Number of generated clips.
- Completed exports.
- Current processing tasks.
- Model installation status.
- Available storage.
- Hardware status.
- Recent activity.

Never fabricate usage statistics.

Display an empty-state experience when no projects exist.

---

# PART 6 — VIDEO INGESTION

## 13. YouTube video import

Support:

- youtube.com/watch URLs.
- youtu.be URLs.
- Supported public YouTube videos.
- Public livestream replays where accessible.

Process:

1. Accept URL.
2. Validate URL.
3. Show source confirmation.
4. Retrieve actual video metadata.
5. Show title.
6. Show thumbnail.
7. Show channel name.
8. Show duration.
9. Show source resolution options when available.
10. Retrieve replay heatmap data when available.
11. Let the user select source quality.
12. Download using yt-dlp when permitted.
13. Show actual progress, download speed and status.
14. Support cancellation and retry.
15. Save the source to the managed workspace.

Handle:

- Unavailable videos.
- Deleted videos.
- Private videos.
- Region restrictions.
- Missing subtitles.
- Videos with no replay graph.
- Temporary network errors.
- Unsupported source formats.

Never silently claim successful downloading when it failed.

Do not bypass authentication, DRM or YouTube access restrictions.

## 14. Local file import

Support:

- MP4.
- MKV.
- MOV.
- AVI.
- WebM.
- Other FFmpeg-readable formats.

Allow:

- File picker.
- Drag and drop.
- Large file imports.
- Batch imports.
- Project-based organization.

Use FFprobe to retrieve actual media metadata.

---

# PART 7 — AUDIENCE INTELLIGENCE ENGINE

## 15. This is a top-priority feature

Build the Audience Intelligence Engine as a first-class module, not an optional cosmetic dashboard.

Its purpose is to determine which sections of a source video have evidence of audience interest and help the AI discover the strongest clip candidates.

The system must distinguish between actual audience signals and algorithmic predictions.

There is no legitimate way to access exact private audience-retention analytics for somebody else's channel without authorization.

Do not claim otherwise.

## 16. Data-source hierarchy

Implement four explicitly distinguished signal types.

### Source A — PUBLIC_YOUTUBE_REPLAY

Use YouTube's public Most Replayed heatmap where available.

Reference:

[https://github.com/realiti4/youtube-context-mcp](https://github.com/realiti4/youtube-context-mcp)

Investigate:

get_most_replayed(video, top_n=8)

Study and validate the exact returned structure.

Relevant documented fields include:

- has_data.
- peak_label.
- region_label.
- url.
- chapter.
- relative_intensity.
- is_opening.

Use returned information rather than inventing replacement values.

Requirements:

1. Retrieve the video heatmap.
2. Extract distinct replay peaks.
3. Extract peak timestamps.
4. Extract normalized relative intensity.
5. Identify their corresponding regions.
6. Exclude the opening playback-start artifact from meaningful replay ranking.
7. Preserve valid content peaks.
8. Merge duplicate or closely overlapping regions sensibly.
9. Match peaks with local transcript timestamps.
10. Match replay peaks with audio-analysis results.

Very important:

Most Replayed indicates relative replay interest, not:

- Exact viewer count.
- Number of unique viewers.
- Exact number of replays.
- Percentage of viewers watching a section.
- Guaranteed viral potential.

If has_data is false, explicitly mark PUBLIC_YOUTUBE_REPLAY as unavailable.

Never fill missing data with invented peaks.

### Source B — OWNER_RETENTION

Support authorized audience-retention reports from a video owner.

Implement:

- Manual CSV import.
- Supported structured data import.
- Timestamp mapping.
- Retention percentage visualization.
- Spike and dip analysis.
- Data validation.

Do not scrape private Studio information.

Do not require a paid API.

Do not request OAuth merely to make the feature work.

Explain how the owner can export or obtain the data they are authorized to use.

### Source C — LOCAL_AI_ESTIMATE

Analyse the video locally.

Use:

- Audio intensity.
- Audio peaks.
- Speech activity.
- Silence patterns.
- Transcript context.
- Interesting statements.
- Laughter and excitement where detectable.
- Scene transitions.
- Visual changes.
- Reaction intensity.
- Conversation boundaries.

Label all such signals as estimates.

Never call them actual YouTube audience statistics.

### Source D — MANUAL_MARKER

Allow the user to add their own timestamps.

Examples:

- 00:12:34
- 00:22:18
- 01:03:45

Support:

- Manual timestamps.
- Start/end timestamp pairs.
- Optional descriptions.
- Import/export of JSON or CSV markers.
- Jump directly to a marker.
- Generate a clip from a marker.

---

# PART 8 — REPLAY HEATMAP AND TIMELINE

## 17. Audience visualization

Create a professional interactive heatmap timeline.

The timeline must show:

- Full video duration.
- Public replay-interest regions.
- Replay peak timestamps.
- Relative replay intensity.
- Owner retention curve, if supplied.
- Local audio intensity.
- Local AI candidate regions.
- Manual markers.
- Selected clip ranges.

Use different visual styles for different signal origins.

The user must be able to:

- Hover to inspect timestamp information.
- Click a peak to jump to the player.
- Zoom into a timeline region.
- Select a region.
- Add or remove markers.
- Compare replay and local-AI signals.
- Generate a candidate from a selected region.

Do not draw a heatmap using fabricated data.

Show an informative empty state when no real heatmap is available.

## 18. Heatmap extraction resilience

YouTube's page structure and data availability can change.

Implement:

- Versioned extraction adapter.
- Defensive response parsing.
- Timeouts.
- Error handling.
- Retry with bounded attempts.
- Parser tests.
- Fixtures for valid and invalid responses.
- Missing-data detection.
- Compatibility tests against the selected open-source implementation.

Never attempt to bypass access restrictions, bot challenges, DRM or private video protections.

If automatic extraction fails, offer manual timestamp entry and local AI analysis.

Do not falsely mark an extraction as successful.

---

# PART 9 — AI VIDEO INTELLIGENCE

## 19. Multi-signal analysis engine

The local analysis engine must identify meaningful moments instead of cutting arbitrary equal intervals.

### Audio analysis

Implement:

- RMS energy.
- Loudness changes.
- Audio peaks.
- Sudden excitement.
- Speech activity.
- Silence detection.
- Voice intensity changes.
- Optional laughter detection.
- Optional cheering detection.
- Speech density.
- Audio-event segmentation.

### Transcript analysis

Use local Whisper transcription.

Identify:

- Interesting statements.
- Punchlines.
- Surprise expressions.
- Strong reactions.
- Funny comments.
- Questions.
- Unexpected statements.
- Memorable commentary.
- Emotional language.
- Exciting dialogue.

Use transcript context, not individual keywords alone.

### Visual analysis

Implement:

- Scene change detection.
- Large frame changes.
- Face detection.
- Optional face tracking.
- Subject movement.
- Optional OCR.
- Gameplay scene analysis where practical.

Do not require heavyweight computer vision models for basic operation.

## 20. Gaming and streamer intelligence

Provide a dedicated Gaming / Streamer analysis mode.

Look for:

- Sudden screaming.
- Loud reactions.
- Genuine surprise.
- Unexpected gameplay outcomes.
- Laughing.
- Emotional reactions.
- Memorable streamer commentary.
- Exciting game events.
- Strong interaction between speakers.
- Funny moments.
- Sudden changes in scene activity.

If an accessible replayed chat log exists, optionally analyse chat activity.

Possible signals:

- Message bursts.
- Repeated emotes.
- Sudden activity increases.
- Relevant audience reactions.

Keep chat analysis optional.

Never pretend chat replay exists when it cannot be retrieved.

Do not use paid streaming analytics APIs.

## 21. Automatic clip ranking

Create a transparent scoring engine.

Each candidate receives:

- Candidate ID.
- Start timestamp.
- End timestamp.
- Duration.
- Estimated engagement score, 0–100.
- Highlight category.
- Source-signal provenance.
- Reason for selection.
- Transcript excerpt.
- Confidence label.

Suggested initial scoring when replay information is available:

- Public replay interest: 40%.
- Audio excitement: 25%.
- Transcript quality and context: 20%.
- Visual activity: 10%.
- Boundary and clip completeness: 5%.

Treat these as configurable heuristic weights, not statistically validated probabilities.

When replay information is unavailable:

- Remove the replay contribution.
- Recalculate the remaining weights proportionally.
- Clearly label the result as LOCAL_AI_ESTIMATE.

Allow the user to adjust scoring sensitivity.

Implement:

- Duplicate detection.
- Overlapping candidate suppression.
- Minimum separation.
- Context-aware boundaries.
- Sentence-aware start/end points.
- Maximum and minimum duration.
- Natural beginnings and endings.
- Ranking from highest to lowest estimated score.

Do not call the result measured popularity.

Do not promise virality.

---

# PART 10 — HIGHLIGHT REVIEW

## 22. Candidate review interface

After analysis, present all real candidate clips.

Each card must include:

- Thumbnail.
- Start time.
- End time.
- Duration.
- Estimated score.
- Highlight category.
- Signal provenance.
- Transcript excerpt.
- Selection checkbox.
- Preview button.
- Generate button.
- Favourite button.
- Reject button.

Support:

- Select all.
- Multi-select.
- Generate selected.
- Generate all.
- Sort by estimated score.
- Filter by category.
- Filter by actual replay signal availability.
- Change clip duration.
- Adjust candidate boundaries.
- Open the original source at the relevant timestamp.

The candidate review stage must happen before final rendering.

---

# PART 11 — AUTOMATIC SUBTITLES

## 23. Local transcription

Use faster-whisper.

Requirements:

- Automatic language detection.
- English.
- Hindi where supported.
- Hinglish as best-effort.
- Word-level timing when available.
- Sentence segmentation.
- Punctuation.
- Speaker handling where practical.
- Manual subtitle correction.
- Accurate timestamp preservation.

Do not claim perfect Hinglish recognition.

Make model selection dependent on hardware.

## 24. Caption engine

Build original caption styles.

Templates:

1. Default.
2. Modern.
3. Kinetic.
4. Bold.
5. Bouncy.
6. Streamer.
7. Gaming.
8. Podcast.
9. Minimal.
10. Custom.

Features:

- Word-by-word highlighting.
- Active-word colour.
- Keyword emphasis.
- Subtle animation.
- Optional contextual emojis.
- Adjustable typography.
- Font weight.
- Text outline.
- Background.
- Shadow.
- Caption positioning.
- Maximum words per line.
- Safe margins.
- Custom colour palette.
- Text correction.
- Live preview.

Emoji rules:

- Match emojis to transcript context.
- Do not insert random emojis.
- Allow emoji generation to be disabled.

Provide actual SRT, VTT and ASS subtitle exports.

The rendered captions must match the editor preview.

---

# PART 12 — SMART VIDEO REFRAMING

## 25. Supported aspect ratios

Implement:

- 9:16 portrait.
- 16:9 landscape.
- 1:1 square.

Keep the original aspect ratio as an additional option.

### Portrait mode

- Subject-aware cropping.
- Face detection.
- Optional face tracking.
- Stable crop movement.
- Smooth transitions.
- Manual focal position.

### Gameplay mode

Gameplay is not the same as podcast video.

Do not blindly crop the centre of a wide game screen.

Use:

- Gameplay preservation.
- Blurred background fill.
- Adjustable focus region.
- Optional facecam split layout.
- Intelligent composition when reliable.

### Streamer mode

Support optional layouts:

- Facecam with gameplay.
- Split screen.
- Stacked video.
- Full gameplay.
- Full facecam.

All output must retain readable subtitles and important content.

---

# PART 13 — CLIP STUDIO

## 26. Functional editing interface

Implement a lightweight but genuine editing workspace.

Features:

- Video preview.
- Timeline.
- Start/end trimming.
- Clip boundary adjustment.
- Subtitle corrections.
- Caption template selection.
- Emoji toggle.
- Caption position.
- Crop positioning.
- Aspect ratio.
- Clip title.
- Volume.
- Mute.
- Output profile.
- Render button.

Keep the editor focused.

Do not build an unnecessarily complicated Premiere Pro replacement.

Every control must work.

---

# PART 14 — RENDERING AND EXPORT

## 27. Video rendering engine

Use FFmpeg and real rendering commands.

Output:

- MP4.
- H.264.
- AAC audio.
- Optional HEVC when supported.
- Correct frame rate.
- High-quality video.
- Synchronized audio.
- Burned-in captions when selected.

No HypeCut branding or watermark.

No forced end card.

Do not alter or remove any source creator's embedded branding or watermark.

## 28. Resolution settings

Support the following profiles:

720p:

- 1280 × 720 landscape.
- 720 × 1280 portrait.

1080p:

- 1920 × 1080 landscape.
- 1080 × 1920 portrait.

1440p:

- 2560 × 1440 landscape.
- 1440 × 2560 portrait.

2160p:

- 3840 × 2160 landscape.
- 2160 × 3840 portrait.

Check original source resolution.

Show a clear warning when upscaling is necessary.

Never label upscaled output as native-resolution source quality.

## 29. Encoding modes

Provide:

- CPU software encoding.
- NVIDIA encoding if compatible.
- Intel Quick Sync if compatible.
- Automatic fallback.

Verify available encoders through actual FFmpeg capabilities and test renders.

Provide:

- Fast.
- Balanced.
- High Quality.

Use single-render concurrency by default.

Provide genuine export progress and cancellation.

---

# PART 15 — PROJECT AND LIBRARY MANAGEMENT

## 30. Project structure

Every source video should have its own project.

Store:

- Original source reference.
- Downloaded source when applicable.
- Metadata.
- Transcripts.
- Replay heatmap results.
- Audience-retention imports.
- Local analysis.
- Candidate clips.
- Manual markers.
- Subtitle files.
- Render settings.
- Generated clips.
- Processing history.

Use SQLite for project metadata.

Use local folders for media.

Avoid storing duplicate copies unnecessarily.

Provide:

- Project rename.
- Project deletion.
- Export deletion.
- Storage management.
- Project recovery.
- Backup and restore.

Never delete the original source video without explicit approval.

---

# PART 16 — MODEL AND HARDWARE MANAGER

## 31. Model Manager

Show:

- Installed speech models.
- Model size.
- Download status.
- Storage usage.
- Selected model.
- CPU/GPU execution mode.
- Compatibility information.

Allow:

- Model download.
- Model selection.
- Model deletion.
- Storage inspection.

Do not silently download enormous models.

Do not require Ollama for basic operation.

## 32. Hardware & Performance

Create a working diagnostic page.

Show:

- CPU name.
- Physical and logical cores.
- System RAM.
- GPU names.
- Dedicated GPU memory.
- Shared GPU memory.
- Driver versions.
- FFmpeg version.
- FFmpeg encoders.
- CUDA capability when detectable.
- Available disk space.
- Model compatibility.
- Current workload.

For the verified laptop, apply the conservative hardware profile described earlier.

All measurements must be real.

---

# PART 17 — RESOURCE MANAGEMENT AND JOB QUEUE

## 33. Persistent processing

Every operation must be represented by a persistent task.

Possible stages:

1. Validation.
2. Metadata retrieval.
3. Download.
4. Media inspection.
5. Replay heatmap retrieval.
6. Transcription.
7. Audio analysis.
8. Visual analysis.
9. Audience intelligence.
10. Highlight scoring.
11. Clip candidate generation.
12. Caption preparation.
13. Rendering.
14. Export verification.

Show the actual current stage.

Support:

- Real progress.
- Cancellation.
- Retry.
- Pause when safely supported.
- Recovery after restart.
- Error reporting.
- Caching.

Never invent percentage completion or an estimated time when the underlying process cannot provide reliable progress.

---

# PART 18 — PRIVACY AND SECURITY

## 34. Local-first security

- Bind the backend to 127.0.0.1.
- No remote public server.
- No compulsory cloud service.
- No source-video uploads.
- No transcript uploads.
- No telemetry.
- No analytics tracking.
- No API keys.
- No unnecessary authentication.
- Secure local storage.
- Safe path validation.
- Safe subprocess execution.
- No shell=True for untrusted input.
- Controlled download destinations.
- SSRF protection.
- Temporary file cleanup.
- Explicit project deletion.

Do not expose the application to the local network by default.

No online service may be required for normal local rendering and analysis.

---

# PART 19 — WINDOWS INSTALLATION

## 35. One-click application setup

Create:

- install.bat
- run.bat
- stop.bat
- doctor.bat
- update.bat
- uninstall.bat

The installation process must:

1. Check Windows version.
2. Check Python.
3. Check Node.js if required.
4. Check FFmpeg.
5. Check FFprobe.
6. Check Git.
7. Detect CPU, RAM and GPU.
8. Create an isolated Python virtual environment.
9. Install dependencies.
10. Configure model storage.
11. Offer suitable model downloads.
12. Initialize SQLite.
13. Run diagnostics.
14. Run initial integration tests.
15. Build the frontend.
16. Start the local application.

No Docker requirement.

No unnecessary administrator permissions.

Provide readable error messages.

Never run downloaded installation scripts without showing the user what is being installed and where it comes from.

---

# PART 20 — TESTING

## 36. Backend tests

Test:

- URL validation.
- Source metadata.
- Video downloading.
- Local video import.
- FFprobe.
- Whisper.
- Transcript timestamps.
- Heatmap parsing.
- Relative-intensity normalization.
- Opening-artifact filtering.
- Missing heatmap handling.
- CSV retention imports.
- Manual timestamps.
- Audio analysis.
- Highlight scoring.
- Duplicate detection.
- Clip boundaries.
- Subtitle rendering.
- FFmpeg output.
- Resolution validation.
- Job recovery.
- Memory failure handling.

## 37. Frontend tests

Test:

- Navigation.
- Dashboard.
- Project creation.
- YouTube URL form.
- Local file import.
- Video preview.
- Audience heatmap.
- Timeline interactions.
- Clip candidate cards.
- Filtering.
- Subtitle editor.
- Caption presets.
- Export settings.
- Render queue.
- Error messages.
- Hardware diagnostics.

## 38. Integration tests

Generate suitable synthetic videos using FFmpeg.

Run the videos through the real pipeline.

Check:

- Metadata correctness.
- Actual transcription.
- Candidate timestamps.
- Highlight score calculations.
- Video dimensions.
- Output duration.
- Audio synchronization.
- Subtitle presence.
- Playable MP4 output.
- No application watermark.
- Cancellation.
- Recovery.
- CPU fallback.

Test audience heatmap extraction using saved fixtures for:

- Valid replay data.
- Multiple peaks.
- Opening artifact.
- No heatmap.
- Malformed response.
- Network failure.

Also test at least one real, eligible public YouTube video where lawful access is available.

Never invent successful live tests.

Use pytest, appropriate frontend testing tools and Playwright.

Run actual build, lint, type-check and test commands.

Fix failures before declaring completion.

---

# PART 21 — DEVELOPMENT EXECUTION PLAN

## 39. Implementation phases

Do not attempt to build every feature as a disconnected prototype.

Develop and integrate in the following order.

PHASE 1 — Workspace and environment audit.

PHASE 2 — Existing open-source repository review and architecture decision.

PHASE 3 — Windows hardware diagnostics.

PHASE 4 — Frontend design system and functional navigation.

PHASE 5 — Backend, SQLite and persistent jobs.

PHASE 6 — Video URL and local-file ingestion.

PHASE 7 — FFmpeg metadata and thumbnail generation.

PHASE 8 — Local Whisper transcription.

PHASE 9 — Public YouTube replay heatmap integration.

PHASE 10 — Owner-retention data import.

PHASE 11 — Manual timestamp support.

PHASE 12 — Interactive Audience Intelligence timeline.

PHASE 13 — Audio and scene analysis.

PHASE 14 — Gaming and streamer analysis.

PHASE 15 — Highlight ranking and duplicate detection.

PHASE 16 — Candidate-review interface.

PHASE 17 — Automatic subtitles and templates.

PHASE 18 — Smart reframing.

PHASE 19 — Functional Clip Studio.

PHASE 20 — FFmpeg rendering.

PHASE 21 — Resolution and quality profiles.

PHASE 22 — Model management and resource governor.

PHASE 23 — Windows launcher and installer.

PHASE 24 — Full integration testing.

PHASE 25 — Documentation and final verification.

After each phase:

- Run appropriate tests.
- Fix regressions.
- Preserve previously working functionality.
- Update documentation.
- Follow the mandatory GitHub checkpoint procedure in PART 25 after every successfully verified phase. A phase is not considered published until its commit is pushed and verified on the remote repository.

Do not create fake screens for future functionality.

If a feature is not implemented, label it clearly.

Do not stop after a progress report.

Continue working through the phases within the available environment and report any genuine blockers.

---

# PART 22 — REQUIRED DELIVERABLES

## 40. Final repository

Deliver a complete working project with:

- Frontend source.
- Backend source.
- Processing pipeline.
- Audience intelligence engine.
- Highlight ranking engine.
- Subtitle engine.
- Rendering engine.
- Model manager.
- Database.
- Windows installation scripts.
- Test suite.
- Documentation.
- Third-party notices.

Required documentation:

README.md

docs/ARCHITECTURE.md

docs/INSTALLATION.md

docs/USER_GUIDE.md

docs/AUDIENCE_INTELLIGENCE.md

docs/AI_MODELS.md

docs/HARDWARE_COMPATIBILITY.md

docs/TESTING.md

docs/PRIVACY.md

docs/KNOWN_LIMITATIONS.md

docs/DEVELOPMENT_PROGRESS.md

THIRD_PARTY_NOTICES.md

.gitignore

.github/workflows/ci.yml

## 41. Final acceptance criteria

The project must not be marked complete unless:

[ ] Windows application launches.

[ ] Dashboard works.

[ ] YouTube URL import works for an accessible, authorized video.

[ ] Local video import works.

[ ] Source metadata is accurate.

[ ] Replay heatmap is retrieved where available.

[ ] Missing heatmaps are handled correctly.

[ ] Relative intensity is never represented as actual viewer counts.

[ ] Opening replay artifact is excluded from meaningful candidate ranking.

[ ] Audience signals are visualized correctly.

[ ] Owner-retention import works.

[ ] Manual timestamps work.

[ ] Whisper transcription runs locally.

[ ] Local AI analysis works without a paid key.

[ ] Multiple meaningful clip candidates are generated.

[ ] Ranking is explainable.

[ ] Duplicate clips are suppressed.

[ ] User can preview candidate clips.

[ ] Automatic subtitles work.

[ ] Caption animation works.

[ ] Contextual emoji controls work.

[ ] 9:16 and 16:9 outputs work.

[ ] 1:1 output works.

[ ] 720p and 1080p exports work.

[ ] 1440p and 2160p export profiles work subject to the source and hardware capabilities.

[ ] Audio and subtitles are synchronized.

[ ] MP4 files are playable.

[ ] No HypeCut-generated watermark exists.

[ ] No mandatory external AI API exists.

[ ] CPU-only fallback works.

[ ] Project history survives restarting the application.

[ ] Application works within the verified laptop's hardware constraints.

[ ] Automated tests pass.

[ ] Installation instructions are usable.

[ ] Known limitations are documented.

[ ] Git repository is correctly configured for Kanishk3105/HypeCut.

[ ] Every verified development phase has its own descriptive commit.

[ ] Every completed phase commit has been pushed to origin/main and verified remotely, unless a clearly documented authentication or remote-service blocker prevents it.

[ ] .gitignore excludes media, model weights, generated clips, databases containing personal data, caches, secrets and large temporary files.

[ ] docs/DEVELOPMENT_PROGRESS.md records implementation, tests, commit hashes and push status.

[ ] GitHub Actions CI runs the relevant free build, lint and test checks on pushes and pull requests, without requiring paid services.

---

# PART 23 — ENGINEERING RULES TO PREVENT HALLUCINATION

## 42. Mandatory execution discipline

These rules take precedence over convenience.

1. Never report a feature as complete because its interface exists.
2. Never simulate successful AI processing.
3. Never use hardcoded candidate timestamps as real results.
4. Never invent YouTube heatmap results.
5. Never invent replay intensity.
6. Never invent video metadata.
7. Never create fake progress indicators.
8. Never fabricate tests.
9. Never silently replace a failed AI operation with random timestamps.
10. Never promise unsupported GPU acceleration.
11. Never claim native 4K if footage was upscaled.
12. Never require paid services to complete core functions.
13. Never delete or overwrite existing user data without permission.
14. Never introduce unnecessary dependencies.
15. Never leave nonfunctional buttons in the interface.
16. Never suppress errors just to make a test pass.
17. Never silently abandon an incomplete phase.
18. Never use private analytics for which the user does not have authorization.
19. Never bypass video platform access controls.
20. Never compromise existing working features to satisfy a new visual requirement.

When encountering a missing dependency, incompatible model or unavailable source:

- Identify the exact cause.
- Check documentation.
- Attempt a suitable local fallback.
- Record what is unavailable.
- Never pretend the original operation succeeded.

Prefer stable, maintainable and testable engineering over unnecessary complexity.

---

# PART 24 — FINAL EXECUTION INSTRUCTION

You are not being asked to describe how HypeCut Local could be built.

You are being instructed to build it.

Start with:

1. Inspect the current workspace.
2. Inspect the actual hardware.
3. Review the primary open-source repository.
4. Inspect the YouTube Context MCP implementation.
5. Decide whether to extend existing components or build missing modules.
6. Create the implementation.
7. Run it.
8. Test it.
9. Fix it.
10. Continue until the required verified functionality is complete.

Do not ask repetitive questions when the specification already provides the answer.

Use sensible defaults.

Keep development work organized into independently testable modules.

Do not sacrifice accuracy to produce an impressive-looking dashboard.

The finished result must be a practical, stable, watermark-free and locally operated AI clipping studio.

**PRODUCT NAME: HYPECUT LOCAL**

**PRIMARY USER: PERSONAL USE ON WINDOWS 11**

**HARDWARE: INTEL i5-8250U / 8 GB RAM / NVIDIA MX130 2 GB VRAM**

**BUDGET: ₹0**

**CORE PROMISE: YOUTUBE VIDEO OR LOCAL FILE IN → AUDIENCE INTELLIGENCE + LOCAL AI HIGHLIGHTS → AUTOMATIC SUBTITLED CLIPS → CLEAN MP4 EXPORTS.**

**BEGIN IMPLEMENTATION NOW.**

---

# PART 25 — MANDATORY GITHUB VERSION CONTROL, COMMITS AND PUSHES

This is a non-negotiable development requirement.

Every successfully completed development phase and every independently completed major feature MUST be committed and pushed to the user's GitHub repository. GitHub publishing is part of the definition of done for each phase, not a final cleanup task.

The GitHub repository is the permanent version-control and development backup for HypeCut Local.

## 1. OFFICIAL GITHUB REPOSITORY

Repository owner: Kanishk3105

Repository name: HypeCut

Remote URL:
https://github.com/Kanishk3105/HypeCut.git

Primary branch: main

GitHub repository:
https://github.com/Kanishk3105/HypeCut

## 2. INITIAL GIT AUDIT

Before modifying Git configuration or repository history:

1. Check whether Git is installed.
2. Check whether the current project directory is already a Git repository.
3. Check the current branch.
4. Inspect `git status` and `git diff`.
5. Inspect `git log`.
6. Inspect all configured remotes.
7. Verify the GitHub remote URL.
8. Check Git authentication without exposing credentials.
9. Fetch and inspect the remote branch, if it exists.
10. Verify that local and remote histories are compatible.

Do not blindly run `git init`, replace a remote, overwrite a branch or discard existing work.

If no Git repository exists, initialize it in the actual HypeCut project root and use `main` as the primary branch.

If `origin` is missing, add:

`git remote add origin https://github.com/Kanishk3105/HypeCut.git`

If `origin` already exists, verify its URL. If it points somewhere else, report the conflict and obtain a safe resolution rather than silently replacing it.

The repository shown by the user is currently intended to be `Kanishk3105/HypeCut`. Inspect its actual remote state before the first push; do not assume it is empty merely because an earlier screenshot showed GitHub's quick-setup page.

If GitHub already contains commits, fetch and reconcile the histories safely. Never force-push or overwrite existing remote history.

## 3. MANDATORY COMMIT AFTER EVERY COMPLETED PHASE

The implementation plan contains 25 development phases. After successfully completing EVERY phase:

1. Finish the phase implementation.
2. Run relevant backend tests.
3. Run relevant frontend tests.
4. Run lint and type checks where applicable.
5. Run the relevant integration tests.
6. Inspect the actual code changes.
7. Inspect `git status` and `git diff`.
8. Check for accidental secrets, personal information, copyrighted media and oversized files.
9. Stage only the intended phase changes.
10. Create a descriptive commit.
11. Push the commit to GitHub immediately.
12. Verify that the remote `main` branch contains the pushed commit.
13. Record the commit hash, test results and push status in `docs/DEVELOPMENT_PROGRESS.md`.

Do not wait until the entire application is complete.

Do not accumulate all phases into one final commit.

Every completed phase must have its own identifiable commit. Independently completed major features and important bug fixes should also receive separate commits when they are not naturally part of the current phase.

Use this commit naming convention:

- `feat(phase-01): initialize project architecture`
- `feat(phase-02): complete repository research and architecture`
- `feat(phase-03): implement hardware diagnostics`
- `feat(phase-04): build frontend design system`
- `feat(phase-05): implement backend and persistent job queue`

Continue with the actual phase number and a truthful description.

For bug fixes:

- `fix: resolve video transcription failure`

For testing:

- `test: add audience intelligence integration tests`

For documentation:

- `docs: complete installation and architecture guides`

For infrastructure:

- `chore: configure Windows development environment`

Commit messages must accurately represent the changes. Never create an empty commit merely to satisfy this rule.

If there are no intended changes, report that fact rather than manufacturing a commit.

If relevant tests fail, the phase is not verified. Fix the failures before marking it complete or publishing it as a completed phase.

## 4. GITHUB PUSH COMMANDS

For an already initialized and correctly configured repository, after reviewing the intended changes:

```bash
git status --short
git diff --check
git add <intended-files-or-directories>
git diff --cached --check
git diff --cached --stat
git commit -m "feat(phase-XX): describe completed implementation"
git push origin main
```

For the first upstream push, when appropriate:

```bash
git push -u origin main
```

Use `git add -A` only after confirming that `.gitignore` is correct and that all listed changes belong to this phase. Prefer explicitly staging intended paths when unrelated or user-created changes exist.

Never stage or commit unrelated user work.

After pushing, verify the remote commit, for example by fetching and comparing the remote branch and local `HEAD`:

```bash
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
git status --short --branch
```

The commit must be present on `origin/main`. Do not report a successful push based solely on the command having started; verify its result.

## 5. GITIGNORE — CRITICAL

Create and verify a comprehensive `.gitignore` before importing dependencies, downloading models or generating media.

Never commit:

- `node_modules/`
- `.venv/`
- `venv/`
- `__pycache__/`
- `.pytest_cache/`
- `.mypy_cache/`
- `.ruff_cache/`
- `dist/`
- `build/`
- `coverage/`
- `.env`
- `.env.local`
- secret-bearing environment files
- API keys
- passwords
- authentication tokens
- private credentials
- SQLite runtime databases containing personal data
- downloaded YouTube videos
- original livestream recordings
- generated clips
- exported videos
- Whisper model binaries
- Ollama model weights
- large temporary video files
- render caches
- application logs
- personal screenshots
- private test data
- personal configuration files

Use `.env.example` only when it contains placeholders and no real secrets.

Keep model weights, temporary processing files, databases containing personal project data and exported media outside Git. Include only source code, safe configuration, documentation, licence notices, tests and appropriate small synthetic test assets.

Do not commit copyrighted source videos or generated clips.

Add a `.gitignore` test or review checklist so media and model files are not accidentally staged later.

## 6. PUBLIC REPOSITORY SECURITY

The HypeCut repository is public.

Before every push:

- Inspect staged changes.
- Check that no credentials are present.
- Check that no personal information is present.
- Check that no personal media is staged.
- Check that no private configuration is staged.
- Check that no model binaries are staged.
- Check that no unexpectedly large files are staged.
- Check that third-party licence notices are preserved.

Use Git Credential Manager or another secure Git authentication method.

Never place GitHub access tokens in source code, scripts, logs or remote URLs.
Never print authentication tokens or passwords.
Never commit `.env` files containing secrets.

If a secret is accidentally committed, do not merely delete it in a later commit. Stop, report the incident, rotate/revoke the exposed credential and follow a safe repository remediation process. Do not rewrite public history or force-push without explicit authorization.

## 7. FAILURE AND RECOVERY HANDLING

If GitHub authentication fails:

- Preserve all local changes.
- Report the actual authentication error without exposing credentials.
- Provide the necessary Git Credential Manager or GitHub authentication instructions.
- Do not falsely mark the phase as PUSHED.
- Retry after authentication is restored.

If a push is rejected:

- Inspect remote changes.
- Fetch the latest history.
- Reconcile safely.
- Resolve conflicts without discarding existing user work.
- Re-run affected tests.
- Push again only after verifying the resulting history.

Never use:

`git push --force`

Never use destructive reset, checkout or clean operations to hide repository conflicts or erase local work.

Never delete local work to make a push succeed.

If a remote-service or authentication blocker prevents publishing, retain the local commit, mark the phase as `VERIFIED — PUSH BLOCKED`, record the exact blocker and resume publishing when possible. Do not claim that GitHub contains the commit until it has been verified there.

## 8. DEVELOPMENT PROGRESS TRACKING

Maintain:

`docs/DEVELOPMENT_PROGRESS.md`

For every phase, record:

- Phase number.
- Phase description.
- Implementation status.
- Files created or changed.
- Tests executed.
- Tests passed.
- Tests failed.
- Known limitations.
- Local commit hash.
- Remote commit hash, when verified.
- GitHub push status.
- Completion date.

Use these statuses:

- `NOT_STARTED`
- `IN_PROGRESS`
- `IMPLEMENTED`
- `TESTING`
- `VERIFIED`
- `PUSHED`
- `VERIFIED — PUSH BLOCKED`

A phase is complete only after its required implementation and tests have passed.

A phase is `PUSHED` only after the remote `main` branch has been verified to contain its commit.

Update the progress record after the push result is known. If that update creates another change, commit and push the progress update too. It is acceptable to create a small follow-up documentation commit so the progress file truthfully records the verified remote status.

## 9. GITHUB CHECKPOINT POLICY

Follow this exact sequence after every phase:

```text
IMPLEMENT
   ↓
RUN RELEVANT TESTS
   ↓
FIX FAILURES
   ↓
INSPECT CHANGES
   ↓
CHECK SECRETS, MEDIA AND LARGE FILES
   ↓
STAGE INTENDED FILES
   ↓
COMMIT PHASE
   ↓
PUSH TO GITHUB
   ↓
VERIFY REMOTE COMMIT
   ↓
UPDATE DEVELOPMENT_PROGRESS.md
   ↓
COMMIT/PUSH THE PROGRESS UPDATE IF NEEDED
   ↓
START NEXT PHASE
```

Apply this process to all 25 implementation phases and every independently completed major feature.

Do not postpone publishing until final delivery.

Do not begin treating the next phase as published until the previous phase's remote status is resolved. If publishing is blocked, make that blocker explicit and preserve all local commits.

## 10. GITHUB ACTIONS CONTINUOUS INTEGRATION

Create a GitHub Actions workflow at:

`.github/workflows/ci.yml`

Configure it to run on pushes to `main` and pull requests targeting `main`.

The workflow should, where supported by the project:

- Install the supported Node.js and Python versions.
- Install frontend and backend dependencies using lockfiles.
- Run frontend linting.
- Run TypeScript type checks.
- Run frontend tests.
- Run Python linting and type checks where configured.
- Run backend unit tests.
- Build the frontend.
- Run lightweight integration tests that do not require large AI model downloads, private media or GPU hardware.

Use public GitHub-hosted runners and existing free usage allowances. Do not add paid CI services, paid runners, secrets or external AI APIs. Do not make CI download multi-gigabyte model weights or copyrighted videos.

Clearly distinguish CI checks from hardware-specific tests that must run locally on the user's laptop.

## 11. FINAL GITHUB DELIVERY REPORT

At project completion, report:

1. GitHub repository URL.
2. Primary branch.
3. Total number of completed phases.
4. Number of successful phase commits.
5. Number of successful pushes.
6. Latest commit hash.
7. Git working-tree status.
8. Test results.
9. GitHub Actions status, when available.
10. Any incomplete or blocked phases.
11. Exact commands for future development and pushing.

Verify that the latest local completed commit is present on GitHub.

The user must be able to clone the repository on another computer and recover the complete application source code without requiring private files, media, model weights or credentials.

FINAL RULES:

NO VERIFIED PHASE WITHOUT A DESCRIPTIVE GIT COMMIT.

NO COMPLETED PHASE COMMIT LEFT ONLY ON THE LOCAL MACHINE WHEN GITHUB PUSH IS AVAILABLE.

NEVER FORCE-PUSH OR DISCARD USER WORK.

COMMIT AND PUSH EVERY COMPLETED DEVELOPMENT PHASE TO:

https://github.com/Kanishk3105/HypeCut.git

