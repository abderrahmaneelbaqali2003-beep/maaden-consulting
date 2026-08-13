import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import AiAssistantPage from "./AiAssistantPage";
import { interpretText, createRecommendation } from "@/api/endpoints";
import type { AiInterpretResponse, RecommendationResponse } from "@/types/api";

vi.mock("@/api/endpoints", () => ({
  interpretText: vi.fn(),
  createRecommendation: vi.fn(),
}));

const navigateMock = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

function buildRecommendationResponse(overrides: Partial<RecommendationResponse> = {}): RecommendationResponse {
  return {
    status: "compatible", request_id: "11111111-1111-1111-1111-111111111111", run_id: 42,
    message: "OK", recommendations: [], rejected_summary: { drivers_rejected: 0, modules_rejected: 0, lenses_rejected: 0 },
    blocking_reasons: [], suggestions: [], created_at: new Date().toISOString(),
    ...overrides,
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/assistant-ia"]}>
      <Routes>
        <Route path="/assistant-ia" element={<AiAssistantPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("AiAssistantPage", () => {
  beforeEach(() => {
    vi.mocked(interpretText).mockReset();
    vi.mocked(createRecommendation).mockReset();
    navigateMock.mockReset();
  });

  it("analyse un texte complet et lance directement la recherche de configurations", async () => {
    const aiResult: AiInterpretResponse = {
      fields: [
        { field_name: "required_flux_lm", scope: "luminaire", label: "Flux lumineux requis", request_attr: "required_flux_lm", operator: "==", value: 6000, numeric_value: 6000, unit: "lm", confidence: "high", source_text: "6000 lumens" },
        { field_name: "max_power_w", scope: "luminaire", label: "Puissance maximale", request_attr: "max_power_w", operator: "<=", value: 60, numeric_value: 60, unit: "W", confidence: "high", source_text: "60 W" },
        { field_name: "cct_k", scope: "luminaire", label: "Temperature de couleur (CCT)", request_attr: "required_cct_k", operator: "==", value: 4000, numeric_value: 4000, unit: "K", confidence: "high", source_text: "4000 K" },
        { field_name: "voltage_nominal_v", scope: "module", label: "Tension nominale du module", request_attr: "voltage_nominal_v", operator: "==", value: 48, numeric_value: 48, unit: "V", confidence: "high", source_text: "48 V" },
        { field_name: "current_nominal_ma", scope: "module", label: "Courant nominal du module", request_attr: "current_nominal_ma", operator: "==", value: 1050, numeric_value: 1050, unit: "mA", confidence: "high", source_text: "1050 mA" },
      ],
      ambiguous_fields: [],
      summary: "J'ai identifie un flux d'environ 6000 lm et un protocole DALI.",
      missing_fields: [],
      can_search: true,
    };
    vi.mocked(interpretText).mockResolvedValue(aiResult);
    vi.mocked(createRecommendation).mockResolvedValue(buildRecommendationResponse());
    const user = userEvent.setup();
    renderPage();

    const textarea = await screen.findByPlaceholderText(/Avenue de 7 m/i);
    await user.type(textarea, "Avenue de 7 m, 6000 lumens, 4000 K, DALI.");
    await user.click(screen.getByRole("button", { name: /Analyser avec l'IA/i }));

    await waitFor(() => expect(interpretText).toHaveBeenCalledWith("Avenue de 7 m, 6000 lumens, 4000 K, DALI."));
    expect(await screen.findByText(/Ce que l'IA a compris/i)).toBeInTheDocument();
    expect(screen.getByText(/J'ai identifie un flux d'environ 6000 lm/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Rechercher les configurations compatibles/i }));

    await waitFor(() =>
      expect(createRecommendation).toHaveBeenCalledWith(
        expect.objectContaining({
          required_flux_lm: 6000, max_power_w: 60, required_cct_k: 4000, voltage_nominal_v: 48, current_nominal_ma: 1050,
        })
      )
    );
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/resultats/42"));
  });

  it("affiche les champs manquants et permet de les completer avant de rechercher", async () => {
    const aiResult: AiInterpretResponse = {
      fields: [
        { field_name: "required_flux_lm", scope: "luminaire", label: "Flux lumineux requis", request_attr: "required_flux_lm", operator: "==", value: 6000, numeric_value: 6000, unit: "lm", confidence: "high", source_text: "6000 lumens" },
      ],
      ambiguous_fields: [],
      summary: null,
      missing_fields: [
        { request_attr: "voltage_nominal_v", label: "Tension nominale du module" },
        { request_attr: "current_nominal_ma", label: "Courant nominal du module" },
      ],
      can_search: false,
    };
    vi.mocked(interpretText).mockResolvedValue(aiResult);
    vi.mocked(createRecommendation).mockResolvedValue(buildRecommendationResponse());
    const user = userEvent.setup();
    renderPage();

    const textarea = await screen.findByPlaceholderText(/Avenue de 7 m/i);
    await user.type(textarea, "6000 lumens.");
    await user.click(screen.getByRole("button", { name: /Analyser avec l'IA/i }));

    expect(await screen.findByText(/Informations manquantes/i)).toBeInTheDocument();
    const searchButton = screen.getByRole("button", { name: /Rechercher les configurations compatibles/i });
    expect(searchButton).toBeDisabled();

    await user.type(screen.getByLabelText("Tension nominale du module"), "48");
    await user.type(screen.getByLabelText("Courant nominal du module"), "1050");
    expect(searchButton).not.toBeDisabled();

    await user.click(searchButton);

    await waitFor(() =>
      expect(createRecommendation).toHaveBeenCalledWith(
        expect.objectContaining({ required_flux_lm: 6000, voltage_nominal_v: 48, current_nominal_ma: 1050 })
      )
    );
  });

  it("affiche les ambiguites renvoyees par l'assistant IA", async () => {
    const aiResult: AiInterpretResponse = {
      fields: [],
      ambiguous_fields: [{ field_name: "cct_k", scope: "luminaire", source_text: "eclairage chaud", message: "Temperature de couleur non explicitement indiquee." }],
      summary: null,
      missing_fields: [{ request_attr: "required_flux_lm", label: "Flux lumineux requis" }],
      can_search: false,
    };
    vi.mocked(interpretText).mockResolvedValue(aiResult);
    const user = userEvent.setup();
    renderPage();

    const textarea = await screen.findByPlaceholderText(/Avenue de 7 m/i);
    await user.type(textarea, "Je veux un eclairage chaud.");
    await user.click(screen.getByRole("button", { name: /Analyser avec l'IA/i }));

    expect(await screen.findByText(/Informations ambigues/i)).toBeInTheDocument();
    expect(screen.getByText(/Temperature de couleur non explicitement indiquee/i)).toBeInTheDocument();
  });

  it("affiche un message de repli si l'assistant IA est indisponible", async () => {
    vi.mocked(interpretText).mockRejectedValue({
      isAxiosError: true,
      response: { status: 503, data: { detail: "L'analyse IA est temporairement indisponible. Vous pouvez continuer avec la saisie manuelle ou l'import CPS/CCTP." } },
    });
    const user = userEvent.setup();
    renderPage();

    const textarea = await screen.findByPlaceholderText(/Avenue de 7 m/i);
    await user.type(textarea, "6000 lumens.");
    await user.click(screen.getByRole("button", { name: /Analyser avec l'IA/i }));

    expect(await screen.findByText(/temporairement indisponible/i)).toBeInTheDocument();
  });
});
