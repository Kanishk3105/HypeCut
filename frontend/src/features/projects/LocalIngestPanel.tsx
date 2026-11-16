import { useRef, useState, type ChangeEvent } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  FileVideo,
  Loader2,
  Upload,
} from "lucide-react";
import { Button } from "../../components/Button";
import { Card } from "../../components/Card";
import {
  ApiError,
  uploadProjectFile,
  waitForJob,
  type Job,
  type Project,
} from "../../lib/api";
import { formatBytes, formatDuration } from "./format";
import { MediaSummary } from "./MediaSummary";

type Phase = "idle" | "uploading" | "importing" | "done";

export function LocalIngestPanel() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [uploadPercent, setUploadPercent] = useState<number | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [project, setProject] = useState<Project | null>(null);

  const busy = phase === "uploading" || phase === "importing";

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    setError(null);
    const chosen = event.target.files?.[0] ?? null;
    setFile(chosen);
    setPhase("idle");
    setUploadPercent(null);
    setJob(null);
    setProject(null);
  }

  async function handleUpload() {
    if (!file || busy) return;
    setError(null);
    setPhase("uploading");
    setUploadPercent(0);
    try {
      const { project: created, job: importJob } = await uploadProjectFile(file, {
        name: file.name.replace(/\.[^.]+$/, "") || file.name,
        onProgress: setUploadPercent,
      });
      setProject(created);
      setJob(importJob);
      setPhase("importing");
      const finished = await waitForJob(importJob.id, { onTick: setJob });
      if (finished.status !== "succeeded") {
        throw new ApiError(finished.error ?? "Import failed", 0);
      }
      setPhase("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      setPhase("idle");
      setUploadPercent(null);
    }
  }

  function handleReset() {
    setFile(null);
    setPhase("idle");
    setError(null);
    setUploadPercent(null);
    setJob(null);
    setProject(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const importProgress = job?.progress != null ? Math.round(job.progress) : null;

  return (
    <div className="space-y-4" data-testid="local-ingest">
      <div className="space-y-2">
        <label htmlFor="local-file" className="block text-sm font-medium text-zinc-300">
          Video file
        </label>
        <input
          ref={inputRef}
          id="local-file"
          type="file"
          accept="video/*,.mkv,.mov,.avi,.webm"
          onChange={handleFileChange}
          disabled={busy}
          className="block w-full cursor-pointer rounded-md border border-dashed border-line bg-surface-950 px-3 py-3 text-sm text-zinc-400 file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-surface-800 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-zinc-200 disabled:opacity-60"
        />
        {file && (
          <p className="flex items-center gap-2 text-xs text-zinc-500">
            <FileVideo size={14} aria-hidden />
            {file.name} · {formatBytes(file.size)}
          </p>
        )}
      </div>

      {error && (
        <div
          role="alert"
          className="flex items-start gap-2 rounded-md border border-red-900/60 bg-red-950/40 px-3 py-2 text-sm text-red-300"
        >
          <AlertTriangle size={16} aria-hidden className="mt-0.5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {!busy && phase !== "done" && (
        <Button onClick={handleUpload} disabled={!file}>
          <Upload size={16} aria-hidden />
          Upload &amp; import
        </Button>
      )}

      {busy && (
        <Card className="space-y-3">
          <p className="flex items-center gap-2 text-sm text-zinc-300">
            <Loader2 size={16} className="animate-spin" aria-hidden />
            {phase === "uploading"
              ? `Uploading… ${uploadPercent ?? 0}%`
              : "Validating the video file…"}
          </p>
          <div
            role="progressbar"
            aria-valuenow={phase === "uploading" ? (uploadPercent ?? 0) : (importProgress ?? undefined)}
            aria-valuemin={0}
            aria-valuemax={100}
            className="h-2 overflow-hidden rounded-full bg-surface-800"
          >
            <div
              className="h-full rounded-full bg-accent-500 transition-all"
              style={{
                width: `${
                  phase === "uploading"
                    ? (uploadPercent ?? 0)
                    : (importProgress ?? 15)
                }%`,
                opacity: phase === "importing" && importProgress == null ? 0.5 : 1,
              }}
            />
          </div>
          <p className="text-xs text-zinc-500">
            {job?.message || job?.stage || "Working…"}
          </p>
        </Card>
      )}

      {phase === "done" && project && (
        <Card className="space-y-3">
          <p className="flex items-center gap-2 text-sm text-emerald-400">
            <CheckCircle2 size={16} aria-hidden />
            Import complete
          </p>
          <MediaSummary
            projectId={project.id}
            fileLabel={
              project.metadata?.file_name ?? project.name
            }
            hasThumbnail={Boolean(project.metadata?.thumbnail_path)}
            width={project.metadata?.width}
            height={project.metadata?.height}
            fps={project.metadata?.fps}
            video={project.metadata?.video}
            audio={project.metadata?.audio}
            sizeBytes={project.metadata?.file_size_bytes}
          />
          <p className="text-xs text-zinc-500">
            {project.metadata?.duration_seconds != null
              ? `Duration ${formatDuration(project.metadata.duration_seconds)}`
              : "Duration unknown"}
          </p>
          <div className="flex flex-wrap gap-2">
            <Link to="/library">
              <Button variant="secondary">Open library</Button>
            </Link>
            <Button variant="ghost" onClick={handleReset}>
              Import another
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
