import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { Boxes } from "lucide-react";

export function ModelManagerPage() {
  return (
    <div data-testid="page-models">
      <SectionHeader
        title="Model Manager"
        description="Installed speech models, sizes, storage use and CPU/GPU execution mode."
      />
      <EmptyState
        icon={<Boxes size={20} aria-hidden />}
        title="No models installed"
        description="Whisper models are only downloaded when you choose them — nothing large is fetched silently. Default is faster-whisper Base INT8, sized for this machine."
        phase="Not implemented yet — Phase 22"
      />
    </div>
  );
}
