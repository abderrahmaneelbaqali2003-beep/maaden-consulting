import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProjectScenariosPage from "./ProjectScenariosPage";
import { getProject, listScenarios, selectScenario, downloadProjectReport } from "@/api/endpoints";
import type { Project, ProjectScenarioOut, RecommendationItem } from "@/types/api";

vi.mock("@/api/endpoints", () => ({
  getProject: vi.fn(),
  listScenarios: vi.fn(),
  selectScenario: vi.fn(),
  downloadProjectReport: vi.fn(),
}));

function buildRecommendation(overrides: Partial<RecommendationItem> = {}): RecommendationItem {
  return {
    id: 100,
    rank: 1,
    overall_score: 88,
    driver: { id: 1, manufacturer: "Mean Well", reference: "ELG-100" },
    module: { id: 2, manufacturer: "Samsung", reference: "MOD-1" },
    lens: null,
    scores: { electrical: 32, photometric: 22, mechanical: 18, thermal: 8, data_quality: 8 },
    validated_rules: [],
    warnings: [],
    blocking_reasons: [],
    explanation: "Configuration compatible.",
    validation_status: "pending",
    ...overrides,
  };
}

function buildScenario(overrides: Partial<ProjectScenarioOut> = {}): ProjectScenarioOut {
  return {
    id: 1,
    project_id: 7,
    scenario_code: "A",
    run_type: "final",
    selected: false,
    selected_by: null,
    selected_at: null,
    selection_comment: null,
    recommendation: buildRecommendation(),
    run_id: 55,
    ...overrides,
  };
}

function buildProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 7, reference: "MC-PROJ-2026-0001", name: "BHNS Rabat", client_name: "RRM", description: null,
    status: "scenario_selection", created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    cps_document_count: 1, requirement_count: 5, requirements_confirmed_count: 5, requirements_to_review_count: 0,
    preliminary_scenario_count: 0, scenario_count: 2, selected_scenario_code: null,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/projets/7/scenarios"]}>
      <Routes>
        <Route path="/projets/:projectId/scenarios" element={<ProjectScenariosPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProjectScenariosPage", () => {
  beforeEach(() => {
    vi.mocked(getProject).mockReset();
    vi.mocked(listScenarios).mockReset();
    vi.mocked(selectScenario).mockReset();
    vi.mocked(downloadProjectReport).mockReset();
  });

  it("affiche les scenarios et la comparaison", async () => {
    vi.mocked(getProject).mockResolvedValue(buildProject());
    vi.mocked(listScenarios).mockResolvedValue([
      buildScenario({ id: 1, scenario_code: "A" }),
      buildScenario({ id: 2, scenario_code: "B", recommendation: buildRecommendation({ id: 101, overall_score: 80 }) }),
    ]);
    renderPage();

    await waitFor(() => expect(screen.getByRole("heading", { name: "Scenario A" })).toBeInTheDocument());
    expect(screen.getByRole("heading", { name: "Scenario B" })).toBeInTheDocument();
    expect(screen.getByText("Comparaison")).toBeInTheDocument();
  });

  it("affiche un message si aucun scenario n'a ete trouve", async () => {
    vi.mocked(getProject).mockResolvedValue(buildProject({ scenario_count: 0 }));
    vi.mocked(listScenarios).mockResolvedValue([]);
    renderPage();

    await waitFor(() => expect(screen.getByText(/Aucune configuration compatible trouvee/i)).toBeInTheDocument());
  });

  it("selectionne un scenario via la modale", async () => {
    vi.mocked(getProject).mockResolvedValue(buildProject());
    vi.mocked(listScenarios).mockResolvedValue([buildScenario({ id: 1, scenario_code: "A" })]);
    vi.mocked(selectScenario).mockResolvedValue(buildScenario({ id: 1, scenario_code: "A", selected: true }));
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Selectionner ce scenario/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/Consultant/i), "Jean Dupont");
    await user.click(within(dialog).getByRole("button", { name: /^Confirmer$/i }));

    await waitFor(() =>
      expect(selectScenario).toHaveBeenCalledWith(7, 1, { selected_by: "Jean Dupont", selection_comment: null })
    );
  });

  it("affiche le bouton de telechargement du rapport quand un scenario est retenu", async () => {
    vi.mocked(getProject).mockResolvedValue(buildProject({ selected_scenario_code: "A" }));
    vi.mocked(listScenarios).mockResolvedValue([buildScenario({ id: 1, scenario_code: "A", selected: true })]);
    vi.mocked(downloadProjectReport).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderPage();

    const button = await screen.findByRole("button", { name: /Telecharger le rapport du projet/i });
    await user.click(button);

    await waitFor(() => expect(downloadProjectReport).toHaveBeenCalledWith(7));
  });

  it("affiche les scenarios preliminaires dans leur propre section avec un badge et sans bouton de selection", async () => {
    vi.mocked(getProject).mockResolvedValue(buildProject({ preliminary_scenario_count: 1, scenario_count: 0 }));
    vi.mocked(listScenarios).mockResolvedValue([
      buildScenario({ id: 1, scenario_code: "A", run_type: "preliminary" }),
    ]);
    renderPage();

    await waitFor(() => expect(screen.getByText("Resultats preliminaires")).toBeInTheDocument());
    expect(screen.getByText("PRELIMINAIRE")).toBeInTheDocument();
    expect(screen.getByText(/doivent etre confirmes apres validation/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Selectionner ce scenario/i })).not.toBeInTheDocument();
  });

  it("separe les scenarios preliminaires et definitifs et affiche l'etude finale en attente sans resultats finaux", async () => {
    vi.mocked(getProject).mockResolvedValue(buildProject({ preliminary_scenario_count: 1, scenario_count: 0 }));
    vi.mocked(listScenarios).mockResolvedValue([
      buildScenario({ id: 1, scenario_code: "A", run_type: "preliminary" }),
    ]);
    renderPage();

    await waitFor(() => expect(screen.getByText("Resultats preliminaires")).toBeInTheDocument());
    expect(screen.getByText(/Etude definitive en attente/i)).toBeInTheDocument();
    expect(screen.queryByText("Comparaison")).not.toBeInTheDocument();
  });
});
