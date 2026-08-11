import type { CalculationResult, CalculationValue } from "@/types/api";

function formatValue(item: CalculationValue, decimals = 1): string {
  if (item.value === null || item.value === undefined) return "—";
  const formatted = item.value.toLocaleString("fr-FR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return item.unit ? `${formatted} ${item.unit}` : formatted;
}

/** Bloc compact "CALCULS DE LA CONFIGURATION" affiche sous chaque configuration recommandee.
 * N'affiche que les grandeurs reellement calculables (jamais une donnee manquante inventee). */
export function TechnicalCalculationsSection({ calculations }: { calculations: CalculationResult }) {
  const rows: { item: CalculationValue; decimals?: number }[] = [
    { item: calculations.electrical.module_power_w },
    { item: calculations.electrical.driver_required_power_w },
    { item: calculations.electrical.driver_loading_percent },
    { item: calculations.electrical.driver_power_margin_percent },
    { item: calculations.electrical.luminous_efficacy_lm_w },
    { item: calculations.geometry.spacing_height_ratio, decimals: 2 },
    { item: calculations.thermal.tightest_thermal_margin_c },
    { item: calculations.energy.annual_energy_kwh },
  ].filter((row) => row.item.status !== "not_calculable");

  if (rows.length === 0) return null;

  return (
    <div className="border-t border-border pt-4">
      <p className="mb-2 text-sm font-semibold text-foreground">Calculs de la configuration</p>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-1.5 text-sm sm:grid-cols-2">
        {rows.map(({ item, decimals }) => (
          <div key={item.key} className="flex items-center justify-between gap-2 border-b border-border/60 py-1">
            <dt className="text-muted-foreground">{item.label}</dt>
            <dd className="font-medium text-foreground">{formatValue(item, decimals)}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
