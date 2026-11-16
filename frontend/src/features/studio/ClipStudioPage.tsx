import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { Scissors } from "lucide-react";

export function ClipStudioPage() {
  return (
    <div data-testid="page-studio">
      <SectionHeader
        title="Clip Studio"
        description="Trim boundaries, fix subtitles, pick caption templates and reframe before rendering."
      />
      <EmptyState
        icon={<Scissors size={20} aria-hidden />}
        title="No clip loaded"
        description="The focused editor provides preview, timeline trimming, caption styling and aspect-ratio controls. Every control in this workspace will be functional before the phase is marked complete."
        phase="Not implemented yet — Phase 19"
      />
    </div>
  );
}
