import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Link2,
  Loader2,
  X,
} from "lucide-react";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import { api, ApiError, waitForJob, type Job, type Project } from "../../lib/api";
import { formatDuration } from "./format";
import { MediaSummary } from "./MediaSummary";

type Phase = "idle" | "fetching" | "ready" | "downloading" | "done";

const YOUTUBE_HOSTS = /(youtube\.com|youtu\.be)/i;

export function YouTubeIngestPanel() {
  const [url, setUrl] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [selectedHeight, setSelectedHeight] = useState<number | null>(null);

  const metadata = project?.metadata ?? null;
  const qualities = metadata?.qualities ?? [];
  const busy = phase === "fetching" || phase === "downloading";

  async function handleFetch(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    const trimmed = url.trim();
    setError(null);
    if (!trimmed || !YOUTUBE_HOSTS.test(trimmed)) {
      setError("That does not look like a YouTube link. Paste a full video URL.");
      return;
    }
    setPhase("fetching");
    setProject(null);
    setJob(null);
    setSelectedHeight(null);
    try {
      const created = await api.createProject({
        name: "YouTube video",
        source_type: "youtube",
        source_ref: trimmed,
      });
      const metadataJob = await api.fetchMetadata(created.id);
      const finished = await waitForJob(metadataJob.id, {
        onTick: setJob,
        timeoutMs: 60_000,
      });
      if (finished.status !== "succeeded") {
        throw new ApiError(finished.error ?? "Metadata retrieval failed", 0);
      }
      const refreshed = await api.getProject(created.id);
      const title = refreshed.metadata?.title;
      if (title && title !== refreshed.name) {
        await api.updateProject(refreshed.id, { name: title });
        refreshed.name = title;
      }
      if (refreshed.metadata?.qualities?.length) {
        setSelectedHeight(refreshed.metadata.qualities[0].height);
      }
      setProject(refreshed);
      setPhase("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setPhase("idle");
    }
  }

  async function handleDownload() {
    if (!project || busy) return;
    setError(null);
    setPhase("downloading");
    try {
      const downloadJob = await api.downloadVideo(
        project.id,
        selectedHeight ?? undefined,
      );
      setJob(downloadJob);
      const finished = await waitForJob(downloadJob.id, { onTick: setJob });
      if (finished.status === "cancelled") {
        setPhase("ready");
        setError(null);
        return;
      }
      if (finished.status !== "succeeded") {
        throw new ApiError(finished.error ?? "Download failed", 0);
      }
      const refreshed = await api.getProject(project.id);
      setProject(refreshed);
      setPhase("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Download failed");
      setPhase("ready");
    }
  }

  async function handleCancel() {
    if (!job) return;
    try {
      await api.cancelJob(job.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not cancel");
    }
  }

  function handleReset() {
    setUrl("");
    setPhase("idle");
    setError(null);
    setProject(null);
    setJob(null);
    setSelectedHeight(null);
  }

  const progress =
    job?.progress != null ? Math.max(0, Math.min(100, job.progress)) : null;

  return (
    <div className="space-y-4" data-testid="youtube-ingest">
      <form onSubmit={handleFetch} className="space-y-3">
        <label
          htmlFor="youtube-url"
          className="block text-sm font-medium text-zinc-300"
        >
          YouTube video URL
        </label>
        <div className="flex flex-col gap-2 sm:flex-row">
          <div className="relative flex-1">
            <Link2
              size={16}
              aria-hidden
              className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500"
            />
            <input
              id="youtube-url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=..."
              disabled={busy}
              className="w-full rounded-md border border-line bg-surface-950 py-2 pl-9 pr-3 text-sm text-zinc-100 placeholder-zinc-600 focus:border-accent-500 focus:outline-none focus:ring-1 focus:ring-accent-500 disabled:opacity-60"
            />
          </div>
          <Button type="submit" disabled={busy}>
            {phase === "fetching" ? (
              <>
                <Loader2 size={16} className="animate-spin" aria-hidden />
                Fetching…
              </>
            ) : (
              "Fetch details"
            )}
          </Button>
        </div>
      </form>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-md border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-300"
        >
          <AlertTriangle size={16} aria-hidden className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {phase === "fetching" && !error && (
        <p className="text-sm text-zinc-500">
          Reading the video page… no download has started yet.
        </p>
      )}

      {(phase === "ready" || phase === "downloading" || phase === "done") &&
        project && (
          <Card className="space-y-4">
            <div className="flex gap-4">
              {metadata?.thumbnail && (
                <img
                  src={metadata.thumbnail}
                  alt=""
                  className="h-24 w-40 shrink-0 rounded-md object-cover"
                />
              )}
              <div className="min-w-0 space-y-1">
                <h3 className="truncate text-sm font-semibold text-zinc-100">
                  {metadata?.title ?? project.name}
                </h3>
                <p className="text-xs text-zinc-500">
                  {metadata?.channel ?? "Unknown channel"} ·{" "}
                  {formatDuration(metadata?.duration_seconds)}
                </p>
                <p className="text-xs">
                  {metadata?.has_heatmap ? (
                    <span className="text-emerald-400">
                      Audience heatmap available
                    </span>
                  ) : (
                    <span className="text-zinc-500">
                      No heatmap data for this video
                    </span>
                  )}
                </p>
              </div>
            </div>

            {qualities.length > 0 && (
              <fieldset disabled={phase === "downloading"}>
                <legend className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">
                  Download quality
                </legend>
                <div className="flex flex-wrap gap-2">
                  {qualities.map((q) => (
                    <label
                      key={q.height}
                      className={`cursor-pointer rounded-md border px-3 py-1.5 text-xs transition-colors ${
                        selectedHeight === q.height
                          ? "border-accent-500 bg-accent-500/10 text-accent-300"
                          : "border-line bg-surface-950 text-zinc-400 hover:border-zinc-600"
                      }`}
                    >
                      <input
                        type="radio"
                        name="quality"
                        value={q.height}
                        checked={selectedHeight === q.height}
                        onChange={() => setSelectedHeight(q.height)}
                        className="sr-only"
                      />
                      {q.label}
                    </label>
                  ))}
                </div>
              </fieldset>
            )}

            {phase === "ready" && (
              <div className="flex flex-wrap gap-2">
                <Button onClick={handleDownload}>
                  <Download size={16} aria-hidden />
                  Download video
                </Button>
                <Button variant="ghost" onClick={handleReset}>
                  Start over
                </Button>
              </div>
            )}

            {phase === "downloading" && (
              <div className="space-y-2">
                <div
                  role="progressbar"
                  aria-valuenow={progress ?? undefined}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  className="h-2 overflow-hidden rounded-full bg-surface-800"
                >
                  <div
                    className={`h-full rounded-full bg-accent-500 transition-all ${
                      progress == null ? "w-1/3 animate-pulse" : ""
                    }`}
                    style={progress != null ? { width: `${progress}%` } : undefined}
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs text-zinc-500">
                    {job?.message || job?.stage || "Working…"}
                    {progress != null ? ` · ${Math.round(progress)}%` : ""}
                  </p>
                  <Button variant="secondary" onClick={handleCancel}>
                    <X size={16} aria-hidden />
                    Cancel
                  </Button>
                </div>
              </div>
            )}

            {phase === "done" && (
              <div className="space-y-3">
                <p className="flex items-center gap-2 text-sm text-emerald-400">
                  <CheckCircle2 size={16} aria-hidden />
                  Download complete
                </p>
                <MediaSummary
                  projectId={project.id}
                  fileLabel={
                    project.metadata?.source_path ?? "file in workspace"
                  }
                  hasThumbnail={Boolean(project.metadata?.thumbnail_path)}
                  width={project.metadata?.width}
                  height={project.metadata?.height}
                  fps={project.metadata?.fps}
                  video={project.metadata?.video}
                  audio={project.metadata?.audio}
                  sizeBytes={project.metadata?.file_size_bytes}
                />
                <div className="flex flex-wrap gap-2">
                  <Link to="/library">
                    <Button variant="secondary">Open library</Button>
                  </Link>
                  <Button variant="ghost" onClick={handleReset}>
                    Import another
                  </Button>
                </div>
              </div>
            )}
          </Card>
        )}
    </div>
  );
}
