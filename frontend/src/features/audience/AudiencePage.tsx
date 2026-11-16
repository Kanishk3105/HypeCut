import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { Radar } from "lucide-react";

export function AudiencePage() {
  return (
    <div data-testid="page-audience">
      <SectionHeader
        title="Audience Intelligence"
        description="Public replay heatmap, owner retention imports, local AI estimates and manual markers on one timeline."
      />
      <EmptyState
        icon={<Radar size={20} aria-hidden />}
        title="No audience signals for a project yet"
        description="The interactive timeline distinguishes PUBLIC_YOUTUBE_REPLAY, OWNER_RETENTION, LOCAL_AI_ESTIMATE and MANUAL_MARKER signals. Missing heatmaps are shown as unavailable — never filled with invented peaks."
        phase="Not implemented yet — Phases 09–12"
      />
    </div>
  );
}
