import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ValidationMatrix } from "./ValidationMatrix";
import type { ConfiguratorResultResponse } from "@/types/api";

const BASE_RESULT: ConfiguratorResultResponse = {
  selection_mode: "manual",
  status: "compatible_with_warning",
  is_compatible: true,
  needs_manual_validation: true,
  driver: { id: 1, manufacturer: "Mean Well", reference: "ELG-100" },
  module: { id: 2, manufacturer: "TCI", reference: "SLM70" },
  lens: null,
  scores: { electrical: 30, photometric: 20, mechanical: 10, thermal: 8, data_quality: 7 },
  validated_rules: ["Tension module (48 V) dans la plage 30-54 V."],
  warnings: ["Aucun fichier IES/LDT disponible."],
  blocking_reasons: [],
  criteria: [
    { criterion: "tension", label: "Tension", status: "valid", detail: "48 V dans la plage 30-54 V." },
    { criterion: "courant", label: "Courant", status: "valid", detail: "1050 mA accepte." },
    { criterion: "puissance", label: "Puissance", status: "warning", detail: "Marge de 8%." },
    { criterion: "protocole", label: "Protocole", status: "valid", detail: "DALI-2 supporte." },
    { criterion: "photometrie", label: "Photometrie (IES/LDT)", status: "warning", detail: "Fichier IES/LDT absent." },
  ],
  explanation: "Configuration classee n°1 avec un score global de 75/100.",
  suggestions: [],
  alternatives: [],
};

describe("ValidationMatrix", () => {
  it("affiche une ligne par critere avec son libelle et son detail", () => {
    render(<ValidationMatrix result={BASE_RESULT} />);

    expect(screen.getByText("Tension")).toBeInTheDocument();
    expect(screen.getByText("48 V dans la plage 30-54 V.")).toBeInTheDocument();
    expect(screen.getByText("Marge de 8%.")).toBeInTheDocument();
  });

  it("affiche le statut global et le score total", () => {
    render(<ValidationMatrix result={BASE_RESULT} />);

    expect(screen.getByText("75/100")).toBeInTheDocument();
  });

  it("affiche les avertissements", () => {
    render(<ValidationMatrix result={BASE_RESULT} />);
    expect(screen.getByText("Aucun fichier IES/LDT disponible.")).toBeInTheDocument();
  });

  it("affiche les raisons bloquantes quand la configuration est incompatible", () => {
    render(
      <ValidationMatrix
        result={{
          ...BASE_RESULT,
          status: "not_compatible",
          is_compatible: false,
          blocking_reasons: ["Tension module hors plage du driver."],
        }}
      />
    );
    expect(screen.getByText("Tension module hors plage du driver.")).toBeInTheDocument();
  });
});
