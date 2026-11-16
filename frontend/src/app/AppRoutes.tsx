import { Routes, Route } from "react-router-dom";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { NewProjectPage } from "../features/projects/NewProjectPage";
import { LibraryPage } from "../features/projects/LibraryPage";
import { AudiencePage } from "../features/audience/AudiencePage";
import { HighlightsPage } from "../features/highlights/HighlightsPage";
import { ClipStudioPage } from "../features/studio/ClipStudioPage";
import { RenderQueuePage } from "../features/queue/RenderQueuePage";
import { ExportHistoryPage } from "../features/exports/ExportHistoryPage";
import { ModelManagerPage } from "../features/models/ModelManagerPage";
import { HardwarePage } from "../features/hardware/HardwarePage";
import { SettingsPage } from "../features/settings/SettingsPage";

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<DashboardPage />} />
      <Route path="/projects/new" element={<NewProjectPage />} />
      <Route path="/library" element={<LibraryPage />} />
      <Route path="/audience" element={<AudiencePage />} />
      <Route path="/highlights" element={<HighlightsPage />} />
      <Route path="/studio" element={<ClipStudioPage />} />
      <Route path="/queue" element={<RenderQueuePage />} />
      <Route path="/exports" element={<ExportHistoryPage />} />
      <Route path="/models" element={<ModelManagerPage />} />
      <Route path="/hardware" element={<HardwarePage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<DashboardPage />} />
    </Routes>
  );
}
