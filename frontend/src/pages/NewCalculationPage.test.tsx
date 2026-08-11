import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import NewCalculationPage from "./NewCalculationPage";
import { createRecommendation, previewCalculations } from "@/api/endpoints";
import { getConfiguratorOptions, listConfiguratorModules } from "@/api/configurator";
import type { CalculationResult, CalculationValue } from "@/types/api";

const navigateMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("@/api/endpoints", () => ({
  createRecommendation: vi.fn(),
  previewCalculations: vi.fn(),
  listDrivers: vi.fn(),
  listLenses: vi.fn(),
}));

function calcValue(
  overrides: Partial<CalculationValue> & Pick<CalculationValue, "key" | "label" | "status">
): CalculationValue {
  return { value: null, unit: null, formula: null, inputs: {}, is_estimate: false, warning: null, ...overrides };
}

function buildCalculationResult(modulePowerW: number | null = 33.6): CalculationResult {
  const modulePowerStatus = modulePowerW === null ? "not_calculable" : "calculated";
  return {
    electrical: {
      module_power_w: calcValue({
        key: "module_power_w",
        label: "Puissance module",
        status: modulePowerStatus,
        value: modulePowerW,
        unit: "W",
        warning: modulePowerW === null ? "Tension et/ou courant du module manquant(s)." : null,
      }),
      module_power_consistency_percent: calcValue({ key: "module_power_consistency_percent", label: "Ecart puissance", status: "not_calculable" }),
      driver_required_power_w: calcValue({ key: "driver_required_power_w", label: "Puissance driver requise", status: "not_calculable" }),
      driver_loading_percent: calcValue({ key: "driver_loading_percent", label: "Charge driver", status: "not_calculable" }),
      driver_power_margin_percent: calcValue({ key: "driver_power_margin_percent", label: "Marge driver", status: "not_calculable" }),
      luminous_efficacy_lm_w: calcValue({ key: "luminous_efficacy_lm_w", label: "Efficacite lumineuse", status: "not_calculable" }),
    },
    geometry: {
      spacing_height_ratio: calcValue({ key: "spacing_height_ratio", label: "Ratio S/H", status: "not_calculable" }),
      road_segment_area_m2: calcValue({ key: "road_segment_area_m2", label: "Surface routiere elementaire", status: "not_calculable" }),
      estimated_luminaire_count: calcValue({ key: "estimated_luminaire_count", label: "Nombre estimatif de luminaires", status: "not_calculable" }),
    },
    thermal: {
      driver_thermal_margin_c: calcValue({ key: "driver_thermal_margin_c", label: "Marge thermique driver", status: "not_calculable" }),
      lens_thermal_margin_c: calcValue({ key: "lens_thermal_margin_c", label: "Marge thermique lentille", status: "not_calculable" }),
      tightest_thermal_margin_c: calcValue({ key: "tightest_thermal_margin_c", label: "Marge thermique la plus contraignante", status: "not_calculable" }),
    },
    energy: {
      total_installed_power_kw: calcValue({ key: "total_installed_power_kw", label: "Puissance totale installee", status: "not_calculable" }),
      annual_energy_kwh: calcValue({ key: "annual_energy_kwh", label: "Consommation annuelle", status: "not_calculable" }),
      annual_energy_with_dimming_kwh: calcValue({ key: "annual_energy_with_dimming_kwh", label: "Consommation avec gradation", status: "not_calculable" }),
      energy_saving_percent: calcValue({ key: "energy_saving_percent", label: "Economie energetique", status: "not_calculable" }),
      energy_saved_kwh_year: calcValue({ key: "energy_saved_kwh_year", label: "Energie economisee", status: "not_calculable" }),
      annual_energy_cost: calcValue({ key: "annual_energy_cost", label: "Cout energetique annuel", status: "not_calculable" }),
    },
    photometric: {
      estimated_average_illuminance_lux: calcValue({ key: "estimated_average_illuminance_lux", label: "Eclairement moyen estimatif", status: "not_calculable" }),
      uniformity_u0: calcValue({ key: "uniformity_u0", label: "Uniformite U0", status: "not_calculable" }),
    },
    warnings: [],
  };
}

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
    vi.mocked(previewCalculations).mockReset();
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

    await user.click(screen.getByRole("button", { name: /Rechercher les configurations compatibles/i }));

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

    await user.click(screen.getByRole("button", { name: /Rechercher les configurations compatibles/i }));

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

    expect(screen.getByRole("button", { name: /Rechercher les configurations compatibles$/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Selection manuelle assistee/i }));

    expect(screen.queryByRole("button", { name: /Rechercher les configurations compatibles$/i })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("1. Module LED")).toBeInTheDocument());
  });

  it("bascule vers la selection semi-automatique quand on clique sur la carte correspondante", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /Selection semi-automatique/i }));

    await waitFor(() => expect(screen.getByText("Composant(s) impose(s)")).toBeInTheDocument());
  });

  it("calcule les grandeurs techniques au clic sur Calculer et affiche le resultat", async () => {
    vi.mocked(previewCalculations).mockResolvedValue(buildCalculationResult(33.6));
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByPlaceholderText("Ex: en V"), "48");
    await user.type(screen.getByPlaceholderText("Ex: en mA"), "700");

    await user.click(screen.getByRole("button", { name: /^Calculer$/i }));

    await waitFor(() => expect(previewCalculations).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText("33,6 W")).toBeInTheDocument());
    // Le bouton de recommandation n'est jamais verrouille par le calcul.
    expect(screen.getByRole("button", { name: /Rechercher les configurations compatibles/i })).toBeEnabled();
  });

  it("affiche une grandeur non calculable sans planter quand une donnee manque", async () => {
    vi.mocked(previewCalculations).mockResolvedValue(buildCalculationResult(null));
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /^Calculer$/i }));

    await waitFor(() => expect(previewCalculations).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText("Puissance module")).toBeInTheDocument());
    // Jamais un 0 W invente : le KPI affiche un tiret pour une donnee manquante.
    expect(screen.queryByText("0 W")).not.toBeInTheDocument();
  });
});
