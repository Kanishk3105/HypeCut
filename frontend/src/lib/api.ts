export interface ProjectMetadata {
  title?: string;
  channel?: string;
  duration_seconds?: number;
  thumbnail?: string;
  has_heatmap?: boolean;
  qualities?: { height: number; label: string }[];
  format_count?: number;
  source_path?: string;
  downloaded_height?: number;
  file_name?: string;
  video?: string;
  audio?: string;
  format_name?: string;
  [key: string]: unknown;
}

export interface Project {
  id: string;
  name: string;
  source_type: "youtube" | "local";
  source_ref: string;
  status: string;
  metadata: ProjectMetadata | null;
  created_at: string;
  updated_at: string;
}

export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "cancelled";

export interface Job {
  id: string;
  type: string;
  project_id: string | null;
  status: JobStatus;
  stage: string | null;
  progress: number | null;
  message: string | null;
  result: unknown;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function extractDetail(body: unknown, fallback: string): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) =>
          d && typeof d === "object" && "msg" in d
            ? String((d as { msg: unknown }).msg)
            : JSON.stringify(d),
        )
        .join("; ");
    }
    if (detail != null) return JSON.stringify(detail);
  }
  return fallback;
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const res = await fetch(path, { ...init, headers });
  if (!res.ok) {
    let detail = res.statusText || `HTTP ${res.status}`;
    try {
      detail = extractDetail(await res.json(), detail);
    } catch {
      /* keep status text */
    }
    throw new ApiError(detail, res.status);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  createProject(input: {
    name: string;
    source_type: "youtube" | "local";
    source_ref: string;
  }): Promise<Project> {
    return request<Project>("/api/projects", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  getProject(id: string): Promise<Project> {
    return request<Project>(`/api/projects/${id}`);
  },

  updateProject(
    id: string,
    patch: Partial<Pick<Project, "name" | "status">>,
  ): Promise<Project> {
    return request<Project>(`/api/projects/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
  },

  deleteProject(id: string): Promise<void> {
    return request<void>(`/api/projects/${id}`, { method: "DELETE" });
  },

  fetchMetadata(projectId: string): Promise<Job> {
    return request<Job>(`/api/projects/${projectId}/fetch-metadata`, {
      method: "POST",
    });
  },

  downloadVideo(projectId: string, maxHeight?: number): Promise<Job> {
    return request<Job>(`/api/projects/${projectId}/download`, {
      method: "POST",
      body: JSON.stringify(maxHeight ? { max_height: maxHeight } : {}),
    });
  },

  importLocal(projectId: string): Promise<Job> {
    return request<Job>(`/api/projects/${projectId}/import`, { method: "POST" });
  },

  getJob(jobId: string): Promise<Job> {
    return request<Job>(`/api/jobs/${jobId}`);
  },

  cancelJob(jobId: string): Promise<Job> {
    return request<Job>(`/api/jobs/${jobId}/cancel`, { method: "POST" });
  },

  retryJob(jobId: string): Promise<Job> {
    return request<Job>(`/api/jobs/${jobId}/retry`, { method: "POST" });
  },
};

export function uploadProjectFile(
  file: File,
  options: {
    name?: string;
    onProgress?: (percent: number) => void;
    signal?: AbortSignal;
  } = {},
): Promise<{ project: Project; job: Job }> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const params = options.name
      ? `?name=${encodeURIComponent(options.name)}`
      : "";
    xhr.open("POST", `/api/projects/upload${params}`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && event.total > 0 && options.onProgress) {
        options.onProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)));
      }
    };

    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        /* non-JSON response */
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        if (body && typeof body === "object") {
          resolve(body as { project: Project; job: Job });
        } else {
          reject(new ApiError("Upload succeeded but the response was malformed", xhr.status));
        }
      } else {
        reject(new ApiError(extractDetail(body, xhr.statusText || "Upload failed"), xhr.status));
      }
    };

    xhr.onerror = () => reject(new ApiError("Network error during upload", 0));
    xhr.onabort = () => reject(new ApiError("Upload cancelled", 0));

    if (options.signal) {
      if (options.signal.aborted) {
        xhr.abort();
        return;
      }
      options.signal.addEventListener("abort", () => xhr.abort(), { once: true });
    }

    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export function isTerminalJobStatus(status: JobStatus): boolean {
  return status === "succeeded" || status === "failed" || status === "cancelled";
}

export async function waitForJob(
  jobId: string,
  options: {
    intervalMs?: number;
    timeoutMs?: number;
    onTick?: (job: Job) => void;
    signal?: AbortSignal;
  } = {},
): Promise<Job> {
  const intervalMs = options.intervalMs ?? 400;
  const timeoutMs = options.timeoutMs ?? 15 * 60 * 1000;
  const deadline = Date.now() + timeoutMs;

  for (;;) {
    if (options.signal?.aborted) {
      throw new ApiError("Cancelled", 0);
    }
    const job = await api.getJob(jobId);
    options.onTick?.(job);
    if (isTerminalJobStatus(job.status)) return job;
    if (Date.now() >= deadline) {
      throw new ApiError("Timed out waiting for the job to finish", 0);
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}
