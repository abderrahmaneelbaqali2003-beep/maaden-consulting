import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ProjectRequirementsPage from "./ProjectRequirementsPage";
import { listRequirements, updateRequirement, confirmRequirements, runStudy, addManualRequirement } from "@/api/endpoints";
import type { ExtractedRequirementOut } from "@/types/api";

const navigateMock = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("@/api/endpoints", () => ({
  listRequirements: vi.fn(),
  updateRequirement: vi.fn(),
  addManualRequirement: vi.fn(),
  confirmRequirements: vi.fn(),
  runStudy: vi.fn(),
}));

function buildRequirement(overrides: Partial<ExtractedRequirementOut> = {}): ExtractedRequirementOut {
  return {
    id: 1,
    project_id: 7,
    cps_document_id: 1,
    category: "lighting",
    scope: "luminaire",
    field_name: "required_flux_lm",
    operator: ">=",
    raw_value: "6000",
    numeric_value: 6000,
    unit: "lm",
    source_page: 41,
    source_excerpt: "flux allant jusqu'a 6000 lumens",
    extraction_confidence: "medium",
    validation_status: "detected",
    validated_value: null,
    validated_by: null,
    validated_at: null,
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/projets/7/exigences"]}>
      <Routes>
        <Route path="/projets/:projectId/exigences" element={<ProjectRequirementsPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ProjectRequirementsPage", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    vi.mocked(listRequirements).mockReset();
    vi.mocked(updateRequirement).mockReset();
    vi.mocked(addManualRequirement).mockReset();
    vi.mocked(confirmRequirements).mockReset();
    vi.mocked(runStudy).mockReset();
  });

  it("affiche les exigences detectees avec leur page source", async () => {
    vi.mocked(listRequirements).mockResolvedValue([buildRequirement()]);
    renderPage();

    await waitFor(() => expect(screen.getByText(/required_flux_lm/i)).toBeInTheDocument());
    expect(screen.getByText(/Page 41/)).toBeInTheDocument();
  });

  it("exige le nom du consultant avant de confirmer une exigence", async () => {
    vi.mocked(listRequirements).mockResolvedValue([buildRequirement()]);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /^Confirmer$/i }));

    expect(await screen.findByText(/Renseignez le nom du consultant/i)).toBeInTheDocument();
    expect(updateRequirement).not.toHaveBeenCalled();
  });

  it("confirme une exigence quand le consultant est renseigne", async () => {
    vi.mocked(listRequirements).mockResolvedValue([buildRequirement()]);
    vi.mocked(updateRequirement).mockResolvedValue(buildRequirement({ validation_status: "confirmed" }));
    const user = userEvent.setup();
    renderPage();

    await user.type(await screen.findByLabelText(/Nom du consultant/i), "Jean Dupont");
    await user.click(screen.getByRole("button", { name: /^Confirmer$/i }));

    await waitFor(() =>
      expect(updateRequirement).toHaveBeenCalledWith(7, 1, { action: "confirm", validated_value: null, validated_by: "Jean Dupont" })
    );
  });

  it("ignore une exigence", async () => {
    vi.mocked(listRequirements).mockResolvedValue([buildRequirement()]);
    vi.mocked(updateRequirement).mockResolvedValue(buildRequirement({ validation_status: "ignored" }));
    const user = userEvent.setup();
    renderPage();

    await user.type(await screen.findByLabelText(/Nom du consultant/i), "Jean Dupont");
    await user.click(screen.getByRole("button", { name: /Ignorer/i }));

    await waitFor(() =>
      expect(updateRequirement).toHaveBeenCalledWith(7, 1, { action: "ignore", validated_value: null, validated_by: "Jean Dupont" })
    );
  });

  it("modifie la valeur d'une exigence", async () => {
    vi.mocked(listRequirements).mockResolvedValue([buildRequirement()]);
    vi.mocked(updateRequirement).mockResolvedValue(buildRequirement({ validation_status: "modified", numeric_value: 6500 }));
    const user = userEvent.setup();
    renderPage();

    await user.type(await screen.findByLabelText(/Nom du consultant/i), "Jean Dupont");
    await user.click(screen.getByRole("button", { name: /^Modifier$/i }));
    const input = screen.getByDisplayValue("6000");
    await user.clear(input);
    await user.type(input, "6500");
    await user.click(screen.getByRole("button", { name: /Enregistrer/i }));

    await waitFor(() =>
      expect(updateRequirement).toHaveBeenCalledWith(7, 1, { action: "modify", validated_value: "6500", validated_by: "Jean Dupont" })
    );
  });

  it("bloque la confirmation du projet si des exigences restent en attente", async () => {
    vi.mocked(listRequirements).mockResolvedValue([buildRequirement()]);
    vi.mocked(confirmRequirements).mockRejectedValue({
      isAxiosError: true,
      response: { data: { detail: "1 exigence(s) detectee(s) restent a traiter." } },
    });
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Confirmer les exigences du projet/i }));

    expect(await screen.findByText("1 exigence(s) detectee(s) restent a traiter.")).toBeInTheDocument();
  });

  it("ajoute une exigence manuelle avec le field_name exact attendu par le moteur (pas un libelle libre)", async () => {
    vi.mocked(listRequirements).mockResolvedValue([]);
    vi.mocked(addManualRequirement).mockResolvedValue(buildRequirement({ field_name: "voltage_nominal_v" }));
    const user = userEvent.setup();
    renderPage();

    await user.type(await screen.findByLabelText(/Nom du consultant/i), "Jean Dupont");
    await user.click(screen.getByRole("button", { name: /Ajouter une exigence manuelle/i }));
    await user.selectOptions(screen.getByLabelText(/Champ a renseigner/i), "module|voltage_nominal_v");
    await user.type(screen.getByLabelText(/^Valeur$/i), "48");
    await user.click(screen.getByRole("button", { name: /^Ajouter$/i }));

    await waitFor(() =>
      expect(addManualRequirement).toHaveBeenCalledWith(7, {
        category: "manual", scope: "module", field_name: "voltage_nominal_v", operator: "==",
        value: "48", unit: "V", validated_by: "Jean Dupont",
      })
    );
  });

  it("lance l'etude et navigue vers la page des scenarios", async () => {
    vi.mocked(listRequirements).mockResolvedValue([buildRequirement({ validation_status: "confirmed" })]);
    vi.mocked(runStudy).mockResolvedValue([]);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Lancer l'etude MAADEN/i }));

    await waitFor(() => expect(runStudy).toHaveBeenCalledWith(7, undefined));
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/projets/7/scenarios"));
  });
});
