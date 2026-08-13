import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProjectDetailPage from "./ProjectDetailPage";
import {
  getProject,
  listCpsDocuments,
  analyzeCpsDocument,
  addManualRequirement,
  rerunPreliminaryStudy,
} from "@/api/endpoints";
import type { CpsAnalysisResponse, Project, RecommendationItem } from "@/types/api";

vi.mock("@/api/endpoints", () => ({
  getProject: vi.fn(),
  listCpsDocuments: vi.fn(),
  analyzeCpsDocument: vi.fn(),
  addManualRequirement: vi.fn(),
  rerunPreliminaryStudy: vi.fn(),
}));

function buildProject(overrides: Partial<Project> = {}): Project {
  return {
    id: 7, reference: "MC-PROJ-2026-0001", name: "BHNS Rabat", client_name: "RRM", description: null,
    status: "requirements_review", created_at: new Date().toISOString(), updated_at: new Date().toISOString(),
    cps_document_count: 0, requirement_count: 0, requirements_confirmed_count: 0, requirements_to_review_count: 0,
    preliminary_scenario_count: 0, scenario_count: 0, selected_scenario_code: null,
    ...overrides,
  };
}

function buildRecommendation(overrides: Partial<RecommendationItem> = {}): RecommendationItem {
  return {
    id: 100, rank: 1, overall_score: 88,
    driver: { id: 1, manufacturer: "Mean Well", reference: "ELG-100" },
    module: { id: 2, manufacturer: "Samsung", reference: "MOD-1" },
    lens: null,
    scores: { electrical: 32, photometric: 22, mechanical: 18, thermal: 8, data_quality: 8 },
    validated_rules: [], warnings: [], blocking_reasons: [], explanation: "Configuration compatible.",
    validation_status: "pending",
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/projets/7"]}>
      <Routes>
        <Route path="/projets/:projectId" element={<ProjectDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProjectDetailPage", () => {
  beforeEach(() => {
    vi.mocked(getProject).mockReset();
    vi.mocked(listCpsDocuments).mockReset();
    vi.mocked(analyzeCpsDocument).mockReset();
    vi.mocked(addManualRequirement).mockReset();
    vi.mocked(rerunPreliminaryStudy).mockReset();
    vi.mocked(getProject).mockResolvedValue(buildProject());
    vi.mocked(listCpsDocuments).mockResolvedValue([]);
  });

  it("affiche le bouton unique d'import et analyse le CPS en un seul clic", async () => {
    const successResult: CpsAnalysisResponse = {
      document: { id: 1, project_id: 7, original_filename: "CCTP.pdf", document_type: "pdf", page_count: 3, uploaded_at: new Date().toISOString(), extraction_status: "extracted", extraction_message: null },
      requirements: [],
      analysis: { can_run_preliminary_study: true, missing_fields: [], requirements_detected_count: 12, requirements_confirmed_count: 0, requirements_to_review_count: 12 },
      scenarios: [
        { id: 1, project_id: 7, scenario_code: "A", run_type: "preliminary", selected: false, selected_by: null, selected_at: null, selection_comment: null, recommendation: buildRecommendation(), run_id: 55 },
      ],
    };
    vi.mocked(analyzeCpsDocument).mockResolvedValue(successResult);
    const user = userEvent.setup();
    renderPage();

    const button = await screen.findByRole("button", { name: /Importer et analyser le CPS/i });
    await screen.findByRole("button", { name: /Importer et analyser le CPS/i });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["%PDF-1.4"], "CCTP.pdf", { type: "application/pdf" });
    await user.upload(fileInput, file);

    await waitFor(() => expect(analyzeCpsDocument).toHaveBeenCalledWith(7, file));
    expect(button).toBeInTheDocument();
    expect(await screen.findByText(/CPS analyse avec succes/i)).toBeInTheDocument();
    expect(screen.getByText(/1 configuration\(s\) preliminaire\(s\) trouvee\(s\)/i)).toBeInTheDocument();
    expect(screen.getByText("PRELIMINAIRE")).toBeInTheDocument();
  });

  it("affiche les champs manquants et permet de completer puis relancer l'analyse", async () => {
    const missingResult: CpsAnalysisResponse = {
      document: { id: 1, project_id: 7, original_filename: "CCTP.pdf", document_type: "pdf", page_count: 3, uploaded_at: new Date().toISOString(), extraction_status: "extracted", extraction_message: null },
      requirements: [],
      analysis: {
        can_run_preliminary_study: false,
        missing_fields: [
          { field: "voltage_nominal_v", label: "Tension nominale du module" },
          { field: "current_nominal_ma", label: "Courant nominal du module" },
        ],
        requirements_detected_count: 8, requirements_confirmed_count: 0, requirements_to_review_count: 8,
      },
      scenarios: [],
    };
    vi.mocked(analyzeCpsDocument).mockResolvedValue(missingResult);
    const rerunResult: CpsAnalysisResponse = {
      document: null, requirements: null,
      analysis: { can_run_preliminary_study: true, missing_fields: [], requirements_detected_count: 10, requirements_confirmed_count: 2, requirements_to_review_count: 8 },
      scenarios: [
        { id: 2, project_id: 7, scenario_code: "A", run_type: "preliminary", selected: false, selected_by: null, selected_at: null, selection_comment: null, recommendation: buildRecommendation(), run_id: 56 },
      ],
    };
    vi.mocked(addManualRequirement).mockResolvedValue({} as never);
    vi.mocked(rerunPreliminaryStudy).mockResolvedValue(rerunResult);
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("button", { name: /Importer et analyser le CPS/i });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["%PDF-1.4"], "CCTP.pdf", { type: "application/pdf" });
    await user.upload(fileInput, file);

    expect((await screen.findAllByText("Tension nominale du module")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Courant nominal du module").length).toBeGreaterThan(0);

    await user.type(screen.getByLabelText("Tension nominale du module"), "48");
    await user.type(screen.getByLabelText("Courant nominal du module"), "1050");
    await user.click(screen.getByRole("button", { name: /Relancer l'analyse/i }));

    await waitFor(() =>
      expect(addManualRequirement).toHaveBeenCalledWith(
        7,
        expect.objectContaining({ field_name: "voltage_nominal_v", value: "48" })
      )
    );
    await waitFor(() =>
      expect(addManualRequirement).toHaveBeenCalledWith(
        7,
        expect.objectContaining({ field_name: "current_nominal_ma", value: "1050" })
      )
    );
    await waitFor(() => expect(rerunPreliminaryStudy).toHaveBeenCalledWith(7));
    expect(await screen.findByText(/CPS analyse avec succes/i)).toBeInTheDocument();
  });

  it("indique qu'aucune configuration n'est trouvee meme si les donnees sont suffisantes", async () => {
    const noConfigResult: CpsAnalysisResponse = {
      document: { id: 1, project_id: 7, original_filename: "CCTP.pdf", document_type: "pdf", page_count: 3, uploaded_at: new Date().toISOString(), extraction_status: "extracted", extraction_message: null },
      requirements: [],
      analysis: { can_run_preliminary_study: true, missing_fields: [], requirements_detected_count: 5, requirements_confirmed_count: 0, requirements_to_review_count: 5 },
      scenarios: [],
    };
    vi.mocked(analyzeCpsDocument).mockResolvedValue(noConfigResult);
    const user = userEvent.setup();
    renderPage();

    await screen.findByRole("button", { name: /Importer et analyser le CPS/i });
    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["%PDF-1.4"], "CCTP.pdf", { type: "application/pdf" });
    await user.upload(fileInput, file);

    expect(await screen.findByText(/Aucune configuration compatible trouvee/i)).toBeInTheDocument();
  });

  it("propose un lien vers l'assistant IA autonome plutot qu'un panneau embarque", async () => {
    renderPage();

    const link = await screen.findByRole("link", { name: /Ouvrir l'assistant IA/i });
    expect(link).toHaveAttribute("href", "/assistant-ia");
  });
});
