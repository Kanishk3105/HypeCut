import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { Sparkles } from "lucide-react";

export function HighlightsPage() {
  return (
    <div data-testid="page-highlights">
      <SectionHeader
        title="AI Highlights"
        description="Locally scored clip candidates with transparent reasons and signal provenance."
      />
      <EmptyState
        icon={<Sparkles size={20} aria-hidden />}
        title="No candidates yet"
        description="Analysis combines replay interest, audio excitement, transcript context and visual activity into explainable 0–100 estimates. Scores are labelled as estimates, never as measured popularity."
        phase="Not implemented yet — Phases 13–16"
      />
    </div>
  );
}
