import { SectionHeader } from "../../components/SectionHeader";
import { EmptyState } from "../../components/EmptyState";
import { Settings } from "lucide-react";

export function SettingsPage() {
  return (
    <div data-testid="page-settings">
      <SectionHeader
        title="Settings"
        description="Language, defaults, cache limits, privacy and storage preferences."
      />
      <EmptyState
        icon={<Settings size={20} aria-hidden />}
        title="Settings not persisted yet"
        description="Preferences are stored locally only — no accounts, no telemetry, no cloud sync. Backend-backed settings arrive with the API phase."
        phase="Not implemented yet — Phase 05"
      />
    </div>
  );
}
