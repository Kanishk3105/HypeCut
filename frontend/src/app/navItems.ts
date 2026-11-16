import type { LucideIcon } from "lucide-react";
import {
  Boxes,
  FolderOpen,
  Gauge,
  History,
  LayoutDashboard,
  ListVideo,
  Radar,
  Scissors,
  Settings,
  Sparkles,
  FilePlus2,
} from "lucide-react";

export interface NavItem {
  label: string;
  path: string;
  icon: LucideIcon;
}

export const navItems: NavItem[] = [
  { label: "Dashboard", path: "/", icon: LayoutDashboard },
  { label: "New Project", path: "/projects/new", icon: FilePlus2 },
  { label: "Video Library", path: "/library", icon: FolderOpen },
  { label: "Audience Intelligence", path: "/audience", icon: Radar },
  { label: "AI Highlights", path: "/highlights", icon: Sparkles },
  { label: "Clip Studio", path: "/studio", icon: Scissors },
  { label: "Render Queue", path: "/queue", icon: ListVideo },
  { label: "Export History", path: "/exports", icon: History },
  { label: "Model Manager", path: "/models", icon: Boxes },
  { label: "Hardware & Performance", path: "/hardware", icon: Gauge },
  { label: "Settings", path: "/settings", icon: Settings },
];
