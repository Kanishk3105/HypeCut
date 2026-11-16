import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { NavLayout } from "./NavLayout";
import { AppRoutes } from "./AppRoutes";
import { navItems } from "./navItems";

function renderApp(initialPath = "/") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <NavLayout>
        <AppRoutes />
      </NavLayout>
    </MemoryRouter>,
  );
}

describe("navigation", () => {
  it("shows all 11 sections in the sidebar", () => {
    renderApp();
    const nav = screen.getByRole("navigation", { name: "Primary" });
    for (const item of navItems) {
      expect(screen.getByRole("link", { name: item.label })).toBeInTheDocument();
    }
    expect(nav.querySelectorAll("a")).toHaveLength(navItems.length);
  });

  it("renders the dashboard by default", () => {
    renderApp();
    expect(screen.getByRole("heading", { name: "Dashboard", level: 1 })).toBeInTheDocument();
    expect(screen.getByTestId("page-dashboard")).toBeInTheDocument();
  });

  it("navigates to every section and shows its page", async () => {
    const user = userEvent.setup();
    renderApp();
    for (const item of navItems) {
      await user.click(screen.getByRole("link", { name: item.label }));
      expect(screen.getByTestId(`page-${pageIdFor(item.path)}`)).toBeInTheDocument();
      expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(item.label);
    }
  });

  it("marks the active section with aria-current", async () => {
    const user = userEvent.setup();
    renderApp();
    const dashboard = screen.getByRole("link", { name: "Dashboard" });
    expect(dashboard).toHaveAttribute("aria-current", "page");
    await user.click(screen.getByRole("link", { name: "Settings" }));
    expect(screen.getByRole("link", { name: "Settings" })).toHaveAttribute("aria-current", "page");
    expect(dashboard).not.toHaveAttribute("aria-current");
  });

  it("keeps a minimal honest empty state on unbuilt pages", async () => {
    const user = userEvent.setup();
    renderApp();
    await user.click(screen.getByRole("link", { name: "AI Highlights" }));
    expect(screen.getByText(/Not implemented yet/)).toBeInTheDocument();
  });
});

function pageIdFor(path: string): string {
  const map: Record<string, string> = {
    "/": "dashboard",
    "/projects/new": "new-project",
    "/library": "library",
    "/audience": "audience",
    "/highlights": "highlights",
    "/studio": "studio",
    "/queue": "queue",
    "/exports": "exports",
    "/models": "models",
    "/hardware": "hardware",
    "/settings": "settings",
  };
  return map[path];
}
