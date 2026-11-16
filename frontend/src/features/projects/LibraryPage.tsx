import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { FolderOpen } from "lucide-react";

export function LibraryPage() {
  return (
    <div data-testid="page-library">
      <SectionHeader
        title="Video Library"
        description="Every imported source, its project, transcripts and generated clips."
      />
      <EmptyState
        icon={<FolderOpen size={20} aria-hidden />}
        title="Library is empty"
        description="Imported videos and their projects will be listed here with real metadata read from the local SQLite database once ingestion and project storage land."
        phase="Not implemented yet — Phases 05–06"
      />
    </div>
  );
}
