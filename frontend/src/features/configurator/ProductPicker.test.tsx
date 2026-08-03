import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProductPicker } from "./ProductPicker";
import { listConfiguratorModules } from "@/api/configurator";
import type { ConfiguratorOptionItem, PaginatedResponse } from "@/types/api";

vi.mock("@/api/configurator", () => ({
  listConfiguratorModules: vi.fn(),
  listConfiguratorDrivers: vi.fn(),
  listConfiguratorLenses: vi.fn(),
}));

const PAGE: PaginatedResponse<ConfiguratorOptionItem> = {
  items: [
    {
      id: 1,
      external_ref: "MOD-0001",
      manufacturer: "TCI",
      reference: "SLM70",
      product_family: null,
      key_specs: { flux_lm: 6000, cct_k: 4000, power_w: 50, led_package: "3535" },
      status: "compatible",
      is_active: true,
    },
    {
      id: 2,
      external_ref: "MOD-0002",
      manufacturer: "OSRAM",
      reference: "XYZ",
      product_family: null,
      key_specs: { flux_lm: 500, cct_k: 2700, power_w: 5, led_package: "5050" },
      status: "not_compatible",
      is_active: true,
    },
  ],
  total: 2,
  page: 1,
  page_size: 10,
  total_pages: 1,
};

describe("ProductPicker", () => {
  beforeEach(() => {
    vi.mocked(listConfiguratorModules).mockReset();
    vi.mocked(listConfiguratorModules).mockResolvedValue(PAGE);
  });

  it("masque par defaut les composants incompatibles", async () => {
    render(
      <ProductPicker entityType="module" requirement={{}} manufacturers={["TCI", "OSRAM"]} selectedId={null} onSelect={() => {}} label="module" />
    );

    await waitFor(() => expect(screen.getByText(/TCI SLM70/)).toBeInTheDocument());
    expect(screen.queryByText(/OSRAM XYZ/)).not.toBeInTheDocument();
  });

  it("masque le composant incompatible tant que le bouton dedie n'est pas active, puis l'affiche", async () => {
    const user = userEvent.setup();
    render(
      <ProductPicker entityType="module" requirement={{}} manufacturers={["TCI", "OSRAM"]} selectedId={null} onSelect={() => {}} label="module" />
    );

    await waitFor(() => expect(screen.getByText(/TCI SLM70/)).toBeInTheDocument());
    expect(screen.queryByText(/OSRAM XYZ/)).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Afficher les incompatibles/i }));

    await waitFor(() => expect(screen.getByText(/OSRAM XYZ/)).toBeInTheDocument());
    expect(screen.getByText("Incompatible")).toBeInTheDocument();
  });

  it("appelle onSelect avec le composant compatible choisi", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <ProductPicker entityType="module" requirement={{}} manufacturers={["TCI"]} selectedId={null} onSelect={onSelect} label="module" />
    );

    await waitFor(() => expect(screen.getByText(/TCI SLM70/)).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Choisir" }));

    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 1, reference: "SLM70" }));
  });
});
