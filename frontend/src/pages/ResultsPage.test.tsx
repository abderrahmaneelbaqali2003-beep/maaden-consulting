import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ResultsPage from "./ResultsPage";
import {
  getRecommendation,
  validateRecommendationResult,
  rejectRecommendationResult,
  downloadRecommendationReport,
} from "@/api/endpoints";
import type { RecommendationItem, RecommendationResponse } from "@/types/api";

vi.mock("@/api/endpoints", () => ({
  getRecommendation: vi.fn(),
  validateRecommendationResult: vi.fn(),
  rejectRecommendationResult: vi.fn(),
  downloadRecommendationReport: vi.fn(),
}));

function buildItem(overrides: Partial<RecommendationItem> = {}): RecommendationItem {
  return {
    id: 7,
    rank: 1,
    overall_score: 88,
    driver: { id: 1, manufacturer: "Mean Well", reference: "ELG-100" },
    module: { id: 2, manufacturer: "Samsung", reference: "MOD-1" },
    lens: { id: 3, manufacturer: "Ledil", reference: "LEN-1" },
    scores: { electrical: 32, photometric: 22, mechanical: 18, thermal: 8, data_quality: 8 },
    validated_rules: [],
    warnings: [],
    blocking_reasons: [],
    explanation: "Configuration compatible.",
    validation_status: "pending",
    ...overrides,
  };
}

function buildResponse(item: RecommendationItem): RecommendationResponse {
  return {
    status: "compatible",
    request_id: "abc",
    run_id: 42,
    message: "ok",
    recommendations: [item],
    rejected_summary: { drivers_rejected: 0, modules_rejected: 0, lenses_rejected: 0 },
    blocking_reasons: [],
    suggestions: [],
    created_at: new Date().toISOString(),
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/resultats/42"]}>
      <Routes>
        <Route path="/resultats/:runId" element={<ResultsPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ResultsPage - validation par configuration", () => {
  beforeEach(() => {
    vi.mocked(getRecommendation).mockReset();
    vi.mocked(validateRecommendationResult).mockReset();
    vi.mocked(rejectRecommendationResult).mockReset();
    vi.mocked(downloadRecommendationReport).mockReset();
  });

  it("affiche le bouton de choix pour une configuration en attente, sans bouton de validation ni PDF", async () => {
    vi.mocked(getRecommendation).mockResolvedValue(buildResponse(buildItem({ validation_status: "pending" })));
    renderPage();

    await waitFor(() => expect(screen.getByRole("button", { name: /Choisir cette configuration/i })).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /Valider cette configuration/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Telecharger le rapport PDF/i })).not.toBeInTheDocument();
  });

  it("affiche le bouton de validation apres avoir choisi la configuration", async () => {
    vi.mocked(getRecommendation).mockResolvedValue(buildResponse(buildItem({ validation_status: "pending" })));
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Choisir cette configuration/i }));

    expect(screen.getByText(/CONFIGURATION CHOISIE/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Valider cette configuration/i })).toBeInTheDocument();
  });

  it("affiche le badge REJETEE et aucun bouton PDF pour une configuration rejetee", async () => {
    vi.mocked(getRecommendation).mockResolvedValue(buildResponse(buildItem({ validation_status: "rejected" })));
    renderPage();

    await waitFor(() => expect(screen.getByText(/CONFIGURATION REJETEE/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /Telecharger le rapport PDF/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Choisir cette configuration/i })).not.toBeInTheDocument();
  });

  it("affiche le badge VALIDEE et le bouton de telechargement pour une configuration validee", async () => {
    vi.mocked(getRecommendation).mockResolvedValue(buildResponse(buildItem({ validation_status: "validated" })));
    renderPage();

    await waitFor(() => expect(screen.getByText(/CONFIGURATION VALIDEE/i)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /Telecharger le rapport PDF/i })).toBeInTheDocument();
  });

  it("exige un nom de consultant pour valider une configuration", async () => {
    vi.mocked(getRecommendation).mockResolvedValue(buildResponse(buildItem({ validation_status: "pending" })));
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Choisir cette configuration/i }));
    await user.click(screen.getByRole("button", { name: /Valider cette configuration/i }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: /Valider la configuration/i }));

    expect(await screen.findByText("Le nom du consultant est obligatoire.")).toBeInTheDocument();
    expect(validateRecommendationResult).not.toHaveBeenCalled();
  });

  it("valide la configuration avec le nom de consultant saisi", async () => {
    const item = buildItem({ id: 9, validation_status: "pending" });
    vi.mocked(getRecommendation).mockResolvedValue(buildResponse(item));
    vi.mocked(validateRecommendationResult).mockResolvedValue({ status: "validated", recommendation_result_id: 9 });
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Choisir cette configuration/i }));
    await user.click(screen.getByRole("button", { name: /Valider cette configuration/i }));
    const dialog = await screen.findByRole("dialog");
    await user.type(within(dialog).getByLabelText(/Nom du consultant/i), "Jean Dupont");
    await user.click(within(dialog).getByRole("button", { name: /Valider la configuration/i }));

    await waitFor(() =>
      expect(validateRecommendationResult).toHaveBeenCalledWith(9, { validator_name: "Jean Dupont", comment: null })
    );
    await waitFor(() => expect(getRecommendation).toHaveBeenCalledTimes(2));
  });

  it("declenche le telechargement du rapport PDF au clic", async () => {
    vi.mocked(getRecommendation).mockResolvedValue(buildResponse(buildItem({ id: 11, validation_status: "validated" })));
    vi.mocked(downloadRecommendationReport).mockResolvedValue(undefined);
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Telecharger le rapport PDF/i }));

    await waitFor(() => expect(downloadRecommendationReport).toHaveBeenCalledWith(11));
  });

  it("affiche un message de repli si le telechargement echoue sans reponse exploitable", async () => {
    vi.mocked(getRecommendation).mockResolvedValue(buildResponse(buildItem({ validation_status: "validated" })));
    vi.mocked(downloadRecommendationReport).mockRejectedValue(new Error("network error"));
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Telecharger le rapport PDF/i }));

    expect(await screen.findByText("Impossible de telecharger le rapport PDF.")).toBeInTheDocument();
  });

  it("affiche le vrai message backend (409) quand le telechargement echoue avec un detail exploitable", async () => {
    vi.mocked(getRecommendation).mockResolvedValue(buildResponse(buildItem({ validation_status: "validated" })));
    const blob = new Blob(
      [JSON.stringify({ detail: "La configuration doit etre validee avant la generation du rapport final." })],
      { type: "application/json" }
    );
    vi.mocked(downloadRecommendationReport).mockRejectedValue({
      isAxiosError: true,
      response: { status: 409, data: blob },
    });
    const user = userEvent.setup();
    renderPage();

    await user.click(await screen.findByRole("button", { name: /Telecharger le rapport PDF/i }));

    expect(
      await screen.findByText("La configuration doit etre validee avant la generation du rapport final.")
    ).toBeInTheDocument();
  });
});
