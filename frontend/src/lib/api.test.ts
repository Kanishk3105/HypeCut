import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, request, uploadProjectFile, waitForJob } from "./api";

function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: "status text",
    json: async () => body,
  } as Response;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("request", () => {
  it("parses JSON on success and sets JSON content type for bodies", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ a: 1 }));
    vi.stubGlobal("fetch", fetchMock);
    await expect(
      request<{ a: number }>("/api/x", { method: "POST", body: '{"b":2}' }),
    ).resolves.toEqual({ a: 1 });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/x");
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("throws ApiError with backend detail message", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ detail: "project not found" }, 404)),
    );
    await expect(request("/api/x")).rejects.toThrowError(
      expect.objectContaining({ message: "project not found", status: 404 }),
    );
  });

  it("joins FastAPI validation array details", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        jsonResponse(
          { detail: [{ msg: "field required" }, { msg: "not an integer" }] },
          422,
        ),
      ),
    );
    await expect(request("/api/x")).rejects.toThrow("field required; not an integer");
  });

  it("falls back to status text when body is not JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Server exploded",
        json: async () => {
          throw new Error("nope");
        },
      } as unknown as Response),
    );
    await expect(request("/api/x")).rejects.toThrow("Server exploded");
  });
});

describe("uploadProjectFile", () => {
  class FakeProgressEvent {
    constructor(
      public lengthComputable: boolean,
      public loaded: number,
      public total: number,
    ) {}
  }

  class FakeXHR {
    static last: FakeXHR | null = null;
    upload: { onprogress: ((e: FakeProgressEvent) => void) | null } = {
      onprogress: null,
    };
    status = 0;
    statusText = "";
    responseText = "";
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    onabort: (() => void) | null = null;
    method = "";
    url = "";
    body: unknown = null;

    constructor() {
      FakeXHR.last = this;
    }

    open(method: string, url: string) {
      this.method = method;
      this.url = url;
    }

    send(body: unknown) {
      this.body = body;
      this.upload.onprogress?.(new FakeProgressEvent(true, 50, 100));
      this.status = 201;
      this.responseText = JSON.stringify({ project: { id: "p1" }, job: { id: "j1" } });
      this.onload?.();
    }

    abort() {
      this.onabort?.();
    }
  }

  it("reports progress and posts multipart form data", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXHR);
    const onProgress = vi.fn();
    const file = new File(["hello"], "clip.mp4", { type: "video/mp4" });

    const result = await uploadProjectFile(file, {
      name: "My clip",
      onProgress,
    });

    expect(result.project.id).toBe("p1");
    expect(result.job.id).toBe("j1");
    expect(onProgress).toHaveBeenCalledWith(50);
    expect(FakeXHR.last?.method).toBe("POST");
    expect(FakeXHR.last?.url).toBe("/api/projects/upload?name=My%20clip");
    expect(FakeXHR.last?.body).toBeInstanceOf(FormData);
  });

  it("rejects with backend detail on HTTP error", async () => {
    class FailingXHR extends FakeXHR {
      override send() {
        this.status = 500;
        this.responseText = JSON.stringify({ detail: "disk full" });
        this.onload?.();
      }
    }
    vi.stubGlobal("XMLHttpRequest", FailingXHR);
    const file = new File(["x"], "a.mp4");
    await expect(uploadProjectFile(file)).rejects.toThrow("disk full");
  });

  it("rejects when the upload is aborted", async () => {
    class AbortingXHR extends FakeXHR {
      override send() {
        this.onabort?.();
      }
    }
    vi.stubGlobal("XMLHttpRequest", AbortingXHR);
    const controller = new AbortController();
    controller.abort();
    await expect(
      uploadProjectFile(new File(["x"], "a.mp4"), { signal: controller.signal }),
    ).rejects.toThrow("Upload cancelled");
  });
});

describe("waitForJob", () => {
  it("polls until the job reaches a terminal status", async () => {
    const statuses = ["queued", "running", "succeeded"] as const;
    let i = 0;
    vi.spyOn(api, "getJob").mockImplementation(async () =>
      ({
        id: "j1",
        type: "t",
        project_id: null,
        status: statuses[Math.min(i++, statuses.length - 1)],
        stage: null,
        progress: null,
        message: null,
        result: null,
        error: null,
        created_at: "a",
        updated_at: "b",
      }) as never,
    );
    const ticks: string[] = [];
    const job = await waitForJob("j1", {
      intervalMs: 1,
      onTick: (j) => ticks.push(j.status),
    });
    expect(job.status).toBe("succeeded");
    expect(ticks).toEqual(["queued", "running", "succeeded"]);
  });

  it("returns a failed job instead of throwing (caller decides)", async () => {
    vi.spyOn(api, "getJob").mockResolvedValue({
      id: "j1",
      type: "t",
      project_id: null,
      status: "failed",
      stage: null,
      progress: null,
      message: null,
      result: null,
      error: "Video unavailable",
      created_at: "a",
      updated_at: "b",
    });
    const job = await waitForJob("j1", { intervalMs: 1 });
    expect(job.status).toBe("failed");
    expect(job.error).toBe("Video unavailable");
  });

  it("times out instead of polling forever", async () => {
    vi.spyOn(api, "getJob").mockResolvedValue({
      id: "j1",
      type: "t",
      project_id: null,
      status: "running",
      stage: null,
      progress: null,
      message: null,
      result: null,
      error: null,
      created_at: "a",
      updated_at: "b",
    });
    await expect(
      waitForJob("j1", { intervalMs: 1, timeoutMs: 0 }),
    ).rejects.toThrow("Timed out");
  });

  it("stops when the caller aborts", async () => {
    const controller = new AbortController();
    controller.abort();
    vi.spyOn(api, "getJob");
    await expect(
      waitForJob("j1", { signal: controller.signal }),
    ).rejects.toThrowError(expect.objectContaining({ status: 0 }));
    expect(api.getJob).not.toHaveBeenCalled();
  });
});

describe("ApiError", () => {
  it("carries an HTTP status", () => {
    const err = new ApiError("nope", 409);
    expect(err.status).toBe(409);
    expect(err.message).toBe("nope");
    expect(err).toBeInstanceOf(Error);
  });
});
