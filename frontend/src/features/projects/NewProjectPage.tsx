import { useState } from "react";
import { FilePlus2, Link2, Upload } from "lucide-react";
import { SectionHeader } from "../../components/SectionHeader";
import { Card } from "../../components/Card";
import { YouTubeIngestPanel } from "./YouTubeIngestPanel";
import { LocalIngestPanel } from "./LocalIngestPanel";

type Tab = "youtube" | "local";

const tabs: { id: Tab; label: string; icon: typeof Link2 }[] = [
  { id: "youtube", label: "YouTube URL", icon: Link2 },
  { id: "local", label: "Local file", icon: Upload },
];

export function NewProjectPage() {
  const [tab, setTab] = useState<Tab>("youtube");

  return (
    <div data-testid="page-new-project" className="space-y-5">
      <SectionHeader
        title="New Project"
        description="Fetch a YouTube video's details before any download, or import a file from this machine."
      />

      <div
        role="tablist"
        aria-label="Import source"
        className="flex gap-1 rounded-lg border border-line bg-surface-950 p-1"
      >
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            role="tab"
            aria-selected={tab === id}
            onClick={() => setTab(id)}
            className={`flex items-center gap-2 rounded-md px-3.5 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-400 ${
              tab === id
                ? "bg-surface-800 text-zinc-100 shadow-sm"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            <Icon size={16} aria-hidden />
            {label}
          </button>
        ))}
      </div>

      <Card>
        <div className="mb-4 flex items-start gap-2 text-xs text-zinc-500">
          <FilePlus2 size={14} aria-hidden className="mt-0.5 shrink-0" />
          {tab === "youtube"
            ? "Nothing downloads until you have seen the video's title, length and available quality."
            : "The file stays on this machine. It is copied into the project workspace, never uploaded anywhere."}
        </div>
        {tab === "youtube" ? <YouTubeIngestPanel /> : <LocalIngestPanel />}
      </Card>
    </div>
  );
}
