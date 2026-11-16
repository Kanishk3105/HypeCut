import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";
import { EmptyState } from "./EmptyState";
import { Card } from "./Card";
import { SectionHeader } from "./SectionHeader";

describe("design system", () => {
  it("button fires click handlers", async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Generate clips</Button>);
    await user.click(screen.getByRole("button", { name: "Generate clips" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("empty state shows honest phase labelling", () => {
    render(
      <EmptyState
        icon={<span aria-hidden>x</span>}
        title="Nothing here"
        description="Details"
        phase="Not implemented yet — Phase 99"
      />,
    );
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Not implemented yet — Phase 99")).toBeInTheDocument();
  });

  it("section header renders title, description and actions", () => {
    render(
      <SectionHeader title="Render Queue" description="Jobs" actions={<Button>Pause</Button>} />,
    );
    expect(screen.getByRole("heading", { name: "Render Queue" })).toBeInTheDocument();
    expect(screen.getByText("Jobs")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Pause" })).toBeInTheDocument();
  });

  it("card wraps content", () => {
    render(<Card>inside</Card>);
    expect(screen.getByText("inside")).toBeInTheDocument();
  });
});
