import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "./StatusBadge";

describe("StatusBadge", () => {
  it("affiche le libelle francais pour le statut compatible", () => {
    render(<StatusBadge status="compatible" />);
    expect(screen.getByText("Compatible")).toBeInTheDocument();
  });

  it("affiche le libelle pour compatible_with_warning", () => {
    render(<StatusBadge status="compatible_with_warning" />);
    expect(screen.getByText("Compatible (avertissement)")).toBeInTheDocument();
  });

  it("affiche le libelle pour impossible", () => {
    render(<StatusBadge status="impossible" />);
    expect(screen.getByText("Impossible")).toBeInTheDocument();
  });

  it("affiche le libelle pour manual_validation_required", () => {
    render(<StatusBadge status="manual_validation_required" />);
    expect(screen.getByText("Validation manuelle requise")).toBeInTheDocument();
  });
});
