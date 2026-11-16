import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { History } from "lucide-react";

export function ExportHistoryPage() {
  return (
    <div data-testid="page-exports">
      <SectionHeader
        title="Export History"
        description="Rendered MP4 files with profiles, durations and individual downloads."
      />
      <EmptyState
        icon={<History size={20} aria-hidden />}
        title="No exports yet"
        description="Finished clips land here with real resolution, duration and file size read from disk. No watermarks or branded outros are ever added to exports."
        phase="Not implemented yet — Phase 20"
      />
    </div>
  );
}
