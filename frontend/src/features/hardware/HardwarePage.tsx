import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { Gauge } from "lucide-react";

export function HardwarePage() {
  return (
    <div data-testid="page-hardware">
      <SectionHeader
        title="Hardware & Performance"
        description="Real CPU, RAM, GPU, driver, FFmpeg encoder and disk measurements."
      />
      <EmptyState
        icon={<Gauge size={20} aria-hidden />}
        title="Diagnostics not wired to this page yet"
        description="The diagnostics engine already exists and runs from the CLI: python -m hypecut.hardware (backend venv). It reports verified encoder capabilities — including failures such as NVENC being unavailable on this driver — and this page will display those live results once the API arrives."
        phase="Engine ready (Phase 03) · UI wiring in Phase 05"
      />
    </div>
  );
}
