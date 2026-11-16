import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { FolderOpen } from "lucide-react";

export function DashboardPage() {
  return (
    <div data-testid="page-dashboard">
      <SectionHeader
        title="Dashboard"
        description="Projects, processing activity, model status and storage at a glance."
      />
      <EmptyState
        icon={<FolderOpen size={20} aria-hidden />}
        title="No projects yet"
        description="Create your first project from a YouTube URL or a local video file. Project statistics, recent activity and hardware status will appear here once the backend pipeline (Phase 05 onward) is connected."
        phase="Dashboard shell live · data lands with Phase 05"
      />
    </div>
  );
}
