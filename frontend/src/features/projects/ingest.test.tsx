import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { NewProjectPage } from "./NewProjectPage";
import { api, uploadProjectFile, waitForJob } from "../../lib/api";
import type { Job, Project } from "../../lib/api";

vi.mock("../../lib/api", () => {
  class ApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.name = "ApiError";
      this.status = status;
    }
  }
  return {
    ApiError,
    api: {
      createProject: vi.fn(),
      fetchMetadata: vi.fn(),
      getProject: vi.fn(),
      updateProject: vi.fn(),
      downloadVideo: vi.fn(),
      cancelJob: vi.fn(),
    },
    uploadProjectFile: vi.fn(),
    waitForJob: vi.fn(),
  };
});

const mockedApi = vi.mocked(api);
const mockedUpload = vi.mocked(uploadProjectFile);
const mockedWait = vi.mocked(waitForJob);

function makeJob(over: Partial<Job> = {}): Job {
  return {
    id: "job-1",
    type: "youtube_metadata",
    project_id: "proj-1",
    status: "queued",
    stage: null,
    progress: null,
    message: null,
    result: null,
    error: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...over,
  };
}

function makeProject(over: Partial<Project> = {}): Project {
  return {
    id: "proj-1",
    name: "YouTube video",
    source_type: "youtube",
    source_ref: "https://youtu.be/jNQXAC9IVRw",
    status: "created",
    metadata: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...over,
  };
}

const metadataProject = makeProject({
  name: "Me at the zoo",
  status: "metadata_ready",
  metadata: {
    title: "Me at the zoo",
    channel: "jawed",
    duration_seconds: 19,
    has_heatmap: true,
    qualities: [
      { height: 1080, label: "1080p" },
      { height: 720, label: "720p" },
    ],
  },
});

function renderPage() {
  return render(
    <MemoryRouter>
      <NewProjectPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.resetAllMocks();
});

describe("NewProjectPage", () => {
  it("shows both import tabs with YouTube selected by default", async () => {
    const user = userEvent.setup();
    renderPage();
    expect(screen.getByRole("tab", { name: /YouTube URL/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
    await user.click(screen.getByRole("tab", { name: /Local file/i }));
    expect(screen.getByTestId("local-ingest")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /Local file/i })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("rejects a non-YouTube URL before calling the backend", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.type(screen.getByLabelText(/YouTube video URL/i), "https://vimeo.com/1");
    await user.click(screen.getByRole("button", { name: "Fetch details" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      /does not look like a YouTube link/i,
    );
    expect(mockedApi.createProject).not.toHaveBeenCalled();
  });

  it("fetches metadata, shows the video details, then downloads at the chosen quality", async () => {
    const user = userEvent.setup();
    mockedApi.createProject.mockResolvedValue(makeProject());
    mockedApi.fetchMetadata.mockResolvedValue(makeJob({ id: "meta-job" }));
    mockedWait
      .mockResolvedValueOnce(makeJob({ id: "meta-job", status: "succeeded" }))
      .mockResolvedValueOnce(
        makeJob({ id: "dl-job", type: "youtube_download", status: "succeeded" }),
      );
    mockedApi.getProject
      .mockResolvedValueOnce(
        makeProject({
          status: "metadata_ready",
          metadata: metadataProject.metadata,
        }),
      )
      .mockResolvedValueOnce(
        makeProject({
          name: "Me at the zoo",
          status: "downloaded",
          metadata: {
            ...metadataProject.metadata!,
            source_path: "C:/HypeCut/data/workspace/proj-1/source.mp4",
          },
        }),
      );
    mockedApi.updateProject.mockResolvedValue(metadataProject);
    mockedApi.downloadVideo.mockResolvedValue(
      makeJob({ id: "dl-job", type: "youtube_download" }),
    );

    renderPage();
    await user.type(
      screen.getByLabelText(/YouTube video URL/i),
      "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    );
    await user.click(screen.getByRole("button", { name: "Fetch details" }));

    expect(await screen.findByText("Me at the zoo")).toBeInTheDocument();
    expect(screen.getByText(/jawed · 19s/)).toBeInTheDocument();
    expect(screen.getByText("Audience heatmap available")).toBeInTheDocument();
    expect(mockedApi.createProject).toHaveBeenCalledWith(
      expect.objectContaining({
        source_type: "youtube",
        source_ref: "https://www.youtube.com/watch?v=jNQXAC9IVRw",
      }),
    );
    expect(mockedApi.updateProject).toHaveBeenCalledWith("proj-1", {
      name: "Me at the zoo",
    });

    await user.click(screen.getByRole("radio", { name: "720p" }));
    await user.click(screen.getByRole("button", { name: /Download video/i }));

    expect(await screen.findByText(/Downloaded to/)).toBeInTheDocument();
    expect(mockedApi.downloadVideo).toHaveBeenCalledWith("proj-1", 720);
    expect(screen.getByRole("button", { name: /Open library/i })).toBeInTheDocument();
  });

  it("returns to the ready state when the download is cancelled", async () => {
    const user = userEvent.setup();
    mockedApi.createProject.mockResolvedValue(makeProject());
    mockedApi.fetchMetadata.mockResolvedValue(makeJob({ id: "meta-job" }));
    mockedWait
      .mockResolvedValueOnce(makeJob({ id: "meta-job", status: "succeeded" }))
      .mockResolvedValueOnce(
        makeJob({ id: "dl-job", type: "youtube_download", status: "cancelled" }),
      );
    mockedApi.getProject.mockResolvedValue(metadataProject);
    mockedApi.updateProject.mockResolvedValue(metadataProject);
    mockedApi.downloadVideo.mockResolvedValue(
      makeJob({ id: "dl-job", type: "youtube_download" }),
    );
    mockedApi.cancelJob.mockResolvedValue(
      makeJob({ id: "dl-job", status: "cancelled" }),
    );

    renderPage();
    await user.type(
      screen.getByLabelText(/YouTube video URL/i),
      "https://youtu.be/jNQXAC9IVRw",
    );
    await user.click(screen.getByRole("button", { name: "Fetch details" }));
    await screen.findByText("Me at the zoo");
    await user.click(screen.getByRole("button", { name: /Download video/i }));

    expect(await screen.findByRole("button", { name: /Download video/i })).toBeInTheDocument();
    expect(screen.queryByText(/Downloaded to/)).not.toBeInTheDocument();
  });

  it("surfaces a metadata failure from the backend", async () => {
    const user = userEvent.setup();
    mockedApi.createProject.mockResolvedValue(makeProject());
    mockedApi.fetchMetadata.mockResolvedValue(makeJob({ id: "meta-job" }));
    mockedWait.mockResolvedValue(
      makeJob({ id: "meta-job", status: "failed", error: "Video unavailable" }),
    );

    renderPage();
    await user.type(
      screen.getByLabelText(/YouTube video URL/i),
      "https://youtu.be/jNQXAC9IVRw",
    );
    await user.click(screen.getByRole("button", { name: "Fetch details" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Video unavailable");
    expect(
      screen.getByRole("button", { name: /Fetch details/i }),
    ).toBeEnabled();
  });

  it("uploads a local file and waits for the import job", async () => {
    const user = userEvent.setup();
    const file = new File(["fake-bytes"], "clip.mp4", { type: "video/mp4" });
    mockedUpload.mockResolvedValue({
      project: makeProject({
        id: "proj-local",
        source_type: "local",
        name: "clip",
        metadata: { file_name: "clip.mp4" },
      }),
      job: makeJob({ id: "import-job", type: "local_import" }),
    });
    mockedWait.mockResolvedValue(
      makeJob({
        id: "import-job",
        type: "local_import",
        status: "succeeded",
        result: { file_name: "clip.mp4", duration_seconds: 1 },
      }),
    );

    renderPage();
    await user.click(screen.getByRole("tab", { name: /Local file/i }));
    await user.upload(screen.getByLabelText(/Video file/i), file);
    await user.click(screen.getByRole("button", { name: /Upload & import/i }));

    expect(await screen.findByText(/Imported clip\.mp4/)).toBeInTheDocument();
    expect(mockedUpload).toHaveBeenCalledTimes(1);
    expect(mockedWait).toHaveBeenCalledWith(
      "import-job",
      expect.objectContaining({ onTick: expect.any(Function) }),
    );
  });

  it("blocks upload until a file is chosen", async () => {
    renderPage();
    await userEvent.click(screen.getByRole("tab", { name: /Local file/i }));
    expect(screen.getByRole("button", { name: /Upload & import/i })).toBeDisabled();
    expect(mockedUpload).not.toHaveBeenCalled();
  });
});
