import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { AccordionItem } from "@/components/ui/accordion";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { cn } from "@/lib/utils";
import type { CalculationResult, CalculationValue } from "@/types/api";

const STATUS_LABELS: Record<CalculationValue["status"], string> = {
  calculated: "Calculee",
  estimate: "Estimation",
  not_calculable: "Non calculable",
  to_validate: "A valider",
};

function formatValue(item: CalculationValue, decimals = 1): string {
  if (item.value === null || item.value === undefined) return "—";
  const formatted = item.value.toLocaleString("fr-FR", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
  return item.unit ? `${formatted} ${item.unit}` : formatted;
}

function flattenCalculationResult(result: CalculationResult): CalculationValue[] {
  return [
    ...Object.values(result.electrical),
    ...Object.values(result.geometry),
    ...Object.values(result.thermal),
    ...Object.values(result.energy),
    ...Object.values(result.photometric),
  ];
}

function KpiCard({ item, decimals = 1 }: { item: CalculationValue; decimals?: number }) {
  const isKnown = item.status !== "not_calculable";
  return (
    <Card className="border-t-2 border-t-secondary">
      <CardContent className="pt-5 text-center">
        <p className="text-2xl font-semibold text-foreground">{isKnown ? formatValue(item, decimals) : "—"}</p>
        <p className="mt-1 text-sm text-muted-foreground">{item.label}</p>
        <p
          className={cn(
            "mt-2 text-xs font-medium",
            item.status === "not_calculable" && "text-muted-foreground",
            item.status === "estimate" && "text-accent-foreground",
            item.status === "calculated" && "text-success",
            item.status === "to_validate" && "text-warning"
          )}
        >
          {STATUS_LABELS[item.status]}
        </p>
      </CardContent>
    </Card>
  );
}

function AnalysisLine({ item }: { item: CalculationValue }) {
  const hasWarning = Boolean(item.warning);
  const Icon = hasWarning ? AlertTriangle : CheckCircle2;
  return (
    <li className={cn("flex items-start gap-2 text-sm", hasWarning ? "text-warning" : "text-success")}>
      <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
      <span className="text-foreground">
        {item.label} {item.value !== null ? `: ${formatValue(item, item.key.includes("ratio") ? 2 : 1)}` : ""}
        {hasWarning && <span className="block text-xs text-warning">{item.warning}</span>}
      </span>
    </li>
  );
}

interface CalculationPreviewProps {
  result: CalculationResult | null;
  loading: boolean;
  error: string | null;
}

export function CalculationPreview({ result, loading, error }: CalculationPreviewProps) {
  if (loading) return <LoadingState rows={3} />;
  if (error) return <ErrorState title="Calcul impossible" message={error} />;
  if (!result) return null;

  const allValues = flattenCalculationResult(result);
  const analysisValues = allValues.filter((v) => v.status !== "not_calculable");
  const missingValues = allValues.filter((v) => v.status === "not_calculable");

  const primary = [
    result.electrical.module_power_w,
    result.electrical.luminous_efficacy_lm_w,
    result.geometry.spacing_height_ratio,
    result.thermal.tightest_thermal_margin_c,
    result.energy.annual_energy_kwh,
  ];
  const primaryDecimals = [1, 1, 2, 1, 1];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Resultats des calculs
        </h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {primary.map((item, i) => (
            <KpiCard key={item.key} item={item} decimals={primaryDecimals[i]} />
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-muted-foreground">
          Analyse technique
        </h3>
        <Card>
          <CardContent className="space-y-2 pt-5">
            {analysisValues.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                Aucune grandeur calculable pour l&apos;instant — completez les donnees du projet ci-dessus.
              </p>
            ) : (
              <ul className="space-y-2">
                {analysisValues.map((item) => (
                  <AnalysisLine key={item.key} item={item} />
                ))}
              </ul>
            )}
            {missingValues.length > 0 && (
              <p className="pt-2 text-xs text-muted-foreground">
                {missingValues.length} grandeur(s) non calculable(s) par manque de donnees (jamais estimee(s) a zero).
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <AccordionItem title="Voir le detail des calculs">
        <dl className="space-y-4">
          {allValues
            .filter((v) => v.status !== "not_calculable" && v.formula)
            .map((item) => (
              <div key={item.key} className="text-sm">
                <dt className="font-medium text-foreground">{item.label}</dt>
                <dd className="mt-0.5 font-mono text-xs text-muted-foreground">{item.formula}</dd>
                <dd className="mt-0.5 font-mono text-xs text-muted-foreground">
                  {Object.entries(item.inputs)
                    .filter(([, v]) => v !== null && v !== undefined)
                    .map(([k, v]) => `${k} = ${v}`)
                    .join(" ; ")}
                </dd>
                <dd className="mt-0.5 text-sm font-semibold text-accent-foreground">
                  = {formatValue(item, item.key.includes("ratio") ? 2 : 1)}
                </dd>
              </div>
            ))}
        </dl>
      </AccordionItem>
    </div>
  );
}
