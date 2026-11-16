import { useState } from "react";
import { thumbnailUrl } from "../../lib/api";
import { formatBytes, formatFps, formatResolution } from "./format";

interface MediaSummaryProps {
  projectId: string;
  fileLabel: string;
  hasThumbnail?: boolean;
  width?: number;
  height?: number;
  fps?: number;
  video?: string;
  audio?: string;
  sizeBytes?: number;
}

export function MediaSummary({
  projectId,
  fileLabel,
  hasThumbnail = false,
  width,
  height,
  fps,
  video,
  audio,
  sizeBytes,
}: MediaSummaryProps) {
  const [thumbFailed, setThumbFailed] = useState(false);
  const showThumb = hasThumbnail && !thumbFailed;

  return (
    <div className="flex gap-4" data-testid="media-summary">
      {showThumb && (
        <img
          src={thumbnailUrl(projectId)}
          alt=""
          onError={() => setThumbFailed(true)}
          className="h-20 w-36 shrink-0 rounded-md border border-line object-cover"
        />
      )}
      <div className="min-w-0 space-y-1">
        <p className="truncate text-sm text-zinc-300">{fileLabel}</p>
        <p className="text-xs text-zinc-500">
          {formatResolution(width, height)} · {formatFps(fps)}
          {video ? ` · ${video}` : ""}
          {audio ? ` / ${audio}` : ""}
          {sizeBytes ? ` · ${formatBytes(sizeBytes)}` : ""}
        </p>
      </div>
    </div>
  );
}
