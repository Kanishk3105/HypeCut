import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { ListVideo } from "lucide-react";

export function RenderQueuePage() {
  return (
    <div data-testid="page-queue">
      <SectionHeader
        title="Render Queue"
        description="Persistent single-lane jobs with real stage, progress, retry and cancellation."
      />
      <EmptyState
        icon={<ListVideo size={20} aria-hidden />}
        title="Queue is empty"
        description="Jobs survive restarts and report the actual pipeline stage. Percentages only appear when the underlying process can provide reliable progress — never invented estimates."
        phase="Not implemented yet — Phases 05, 20"
      />
    </div>
  );
}
