import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProjectsPage from "./ProjectsPage";
import { createProject, listProjects } from "@/api/endpoints";
import type { Project } from "@/types/api";

const navigateMock = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("@/api/endpoints", () => ({
  createProject: vi.fn(),
  listProjects: vi.fn(),
}));

function buildProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 1,
    reference: "MC-PROJ-2026-0001",
    name: "BHNS Rabat",
    client_name: "RRM",
    description: null,
    status: "draft",
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    cps_document_count: 0,
    requirement_count: 0,
    scenario_count: 0,
    selected_scenario_code: null,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<ProjectsPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProjectsPage", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    vi.mocked(createProject).mockReset();
    vi.mocked(listProjects).mockReset();
  });

  it("affiche la liste des projets", async () => {
    vi.mocked(listProjects).mockResolvedValue({
      items: [buildProject()], total: 1, page: 1, page_size: 20, total_pages: 1,
    });
    renderPage();

    await waitFor(() => expect(screen.getByText("BHNS Rabat")).toBeInTheDocument());
    expect(screen.getByText("MC-PROJ-2026-0001")).toBeInTheDocument();
  });

  it("affiche un etat vide si aucun projet", async () => {
    vi.mocked(listProjects).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
    renderPage();

    await waitFor(() => expect(screen.getByText(/Aucun projet pour le moment/i)).toBeInTheDocument());
  });

  it("cree un projet et navigue vers sa page de detail", async () => {
    vi.mocked(listProjects).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
    vi.mocked(createProject).mockResolvedValue(buildProject({ id: 42, name: "Nouveau projet" }));
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Nouveau projet/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/Nom du projet/i), "Nouveau projet");
    await user.click(within(dialog).getByRole("button", { name: /Creer le projet/i }));

    await waitFor(() =>
      expect(createProject).toHaveBeenCalledWith({ name: "Nouveau projet", client_name: null })
    );
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/projets/42"));
  });

  it("exige un nom pour creer un projet", async () => {
    vi.mocked(listProjects).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Nouveau projet/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /Creer le projet/i }));

    expect(await screen.findByText("Le nom du projet est obligatoire.")).toBeInTheDocument();
    expect(createProject).not.toHaveBeenCalled();
  });
});
