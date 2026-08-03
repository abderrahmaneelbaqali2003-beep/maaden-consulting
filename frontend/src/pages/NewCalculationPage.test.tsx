import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import NewCalculationPage from "./NewCalculationPage";
import { createRecommendation } from "@/api/endpoints";
import { getConfiguratorOptions, listConfiguratorModules } from "@/api/configurator";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("@/api/endpoints", () => ({
  createRecommendation: vi.fn(),
  listDrivers: vi.fn(),
  listLenses: vi.fn(),
}));

vi.mock("@/api/configurator", () => ({
  getConfiguratorOptions: vi.fn(),
  listConfiguratorModules: vi.fn(),
  listConfiguratorDrivers: vi.fn(),
  listConfiguratorLenses: vi.fn(),
  validateConfiguration: vi.fn(),
  recommendMissing: vi.fn(),
  saveConfiguration: vi.fn(),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <NewCalculationPage />
    </MemoryRouter>
  );
}

describe("NewCalculationPage", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    vi.mocked(createRecommendation).mockReset();
    vi.mocked(getConfiguratorOptions).mockReset();
    vi.mocked(getConfiguratorOptions).mockResolvedValue({
      selection_modes: [],
      protocols: [],
      manufacturers: { drivers: [], modules: [], lenses: [] },
      counts: { drivers: 0, modules: 0, lenses: 0 },
    });
    vi.mocked(listConfiguratorModules).mockReset();
    vi.mocked(listConfiguratorModules).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10, total_pages: 1 });
  });

  it("affiche les 5 champs obligatoires avec leur unite", () => {
    renderPage();
    expect(screen.getByText(/Flux lumineux demande/)).toBeInTheDocument();
    expect(screen.getByText(/Puissance totale maximale/)).toBeInTheDocument();
    expect(screen.getByText(/Temperature de couleur/)).toBeInTheDocument();
    expect(screen.getByText(/Tension nominale du module/)).toBeInTheDocument();
    expect(screen.getByText(/Courant nominal/)).toBeInTheDocument();
    expect(screen.getByText("lm")).toBeInTheDocument();
    expect(screen.getByText("W")).toBeInTheDocument();
  });

  it("affiche des erreurs de validation en francais si le formulaire est vide", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Lancer la recommandation/i }));

    await waitFor(() => {
      expect(screen.getByText("Le flux lumineux est obligatoire.")).toBeInTheDocument();
    });
    expect(createRecommendation).not.toHaveBeenCalled();
  });

  it("soumet le formulaire et navigue vers la page de resultats en cas de succes", async () => {
    vi.mocked(createRecommendation).mockResolvedValue({
      status: "compatible",
      request_id: "abc",
      run_id: 42,
      message: "ok",
      recommendations: [],
      rejected_summary: { drivers_rejected: 0, modules_rejected: 0, lenses_rejected: 0 },
      blocking_reasons: [],
      suggestions: [],
      created_at: new Date().toISOString(),
    });

    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText("Ex: en lm"), "6000");
    await user.type(screen.getByPlaceholderText("Ex: en W"), "60");
    await user.type(screen.getByPlaceholderText("Ex: en K"), "4000");
    await user.type(screen.getByPlaceholderText("Ex: en V"), "48");
    await user.type(screen.getByPlaceholderText("Ex: en mA"), "1050");

    await user.click(screen.getByRole("button", { name: /Lancer la recommandation/i }));

    await waitFor(() => {
      expect(createRecommendation).toHaveBeenCalledWith(
        expect.objectContaining({
          required_flux_lm: 6000,
          max_power_w: 60,
          required_cct_k: 4000,
          voltage_nominal_v: 48,
          current_nominal_ma: 1050,
        })
      );
    });
    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith("/resultats/42"));
  });

  it("bascule vers la selection manuelle assistee quand on clique sur la carte correspondante", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(screen.getByRole("button", { name: /Lancer la recommandation$/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Selection manuelle assistee/i }));

    expect(screen.queryByRole("button", { name: /Lancer la recommandation$/i })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("1. Module LED")).toBeInTheDocument());
  });

  it("bascule vers la selection semi-automatique quand on clique sur la carte correspondante", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Selection semi-automatique/i }));

    await waitFor(() => expect(screen.getByText("Composant(s) impose(s)")).toBeInTheDocument());
  });
});
