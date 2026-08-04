import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import {
  Cpu,
  Lightbulb,
  Aperture,
  Percent,
  Sparkles,
  SlidersHorizontal,
  UploadCloud,
  Boxes,
  FileSpreadsheet,
  ChevronRight,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { buttonVariants } from "@/components/ui/button";
import { StatusBadge } from "@/components/StatusBadge";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { cn } from "@/lib/utils";
import { getDashboardSummary } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { DashboardSummary } from "@/types/api";

const CHART_COLORS = ["#4f5557", "#c99a32", "#7a8082"];

const QUICK_ACTIONS = [
  { to: "/nouveau-calcul", label: "Nouvelle recommandation", icon: Sparkles, variant: "default" as const },
  { to: "/nouveau-calcul", label: "Configuration manuelle", icon: SlidersHorizontal, variant: "outline" as const },
  { to: "/imports", label: "Importer une base", icon: UploadCloud, variant: "outline" as const },
  { to: "/catalogue", label: "Consulter le catalogue", icon: Boxes, variant: "secondary" as const },
];

function StatCard({
  icon: Icon,
  label,
  value,
  sublabel,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sublabel?: string;
}) {
  return (
    <Card className="border-t-2 border-t-secondary">
      <CardContent className="flex items-center gap-4 pt-5">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[#f6edd8] text-[#9a711a]">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </div>
        <div>
          <p className="text-2xl font-semibold text-foreground">{value}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
          {sublabel && <p className="text-xs text-muted-foreground">{sublabel}</p>}
        </div>
      </CardContent>
    </Card>
  );
}

interface ChartTooltipProps {
  active?: boolean;
  payload?: { value: number; payload: { name: string } }[];
}

function ChartTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload?.length) return null;
  const entry = payload[0];
  return (
    <div className="rounded-md border border-border bg-card px-3 py-2 text-sm shadow-[0_4px_14px_rgba(37,41,43,0.1)]">
      <p className="text-foreground">{entry.payload.name}</p>
      <p className="font-semibold text-secondary">{entry.value}</p>
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    getDashboardSummary()
      .then(setSummary)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div>
      <PageHeader
        title="Tableau de bord"
        description="Vue d'ensemble du catalogue et des recommandations recentes."
      />

      <div className="mb-6 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {QUICK_ACTIONS.map(({ to, label, icon: Icon, variant }) => (
          <Link key={label} to={to} className={cn(buttonVariants({ variant, size: "lg" }), "w-full")}>
            <Icon className="h-4 w-4" aria-hidden="true" />
            {label}
          </Link>
        ))}
      </div>

      {loading && <LoadingState rows={4} />}
      {error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && summary && (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={Cpu} label="Drivers actifs" value={summary.drivers_count} />
            <StatCard icon={Lightbulb} label="Modules LED actifs" value={summary.modules_count} />
            <StatCard icon={Aperture} label="Lentilles actives" value={summary.lenses_count} />
            <StatCard
              icon={Percent}
              label="Taux compatible"
              value={`${summary.compatible_rate_percent}%`}
              sublabel={`Sur ${summary.recommendation_runs_count} calcul${summary.recommendation_runs_count === 1 ? "" : "s"}`}
            />
          </div>

          <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Repartition du catalogue</CardTitle>
              </CardHeader>
              <CardContent className="h-64 pt-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={[
                      { name: "Drivers", total: summary.drivers_count },
                      { name: "Modules LED", total: summary.modules_count },
                      { name: "Lentilles", total: summary.lenses_count },
                    ]}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e3df" />
                    <XAxis dataKey="name" tick={{ fontSize: 12 }} stroke="#737a7c" />
                    <YAxis tick={{ fontSize: 12 }} stroke="#737a7c" allowDecimals={false} />
                    <Tooltip content={<ChartTooltip />} />
                    <Bar dataKey="total" radius={[5, 5, 0, 0]}>
                      {CHART_COLORS.map((color, index) => (
                        <Cell key={color} fill={color} fillOpacity={index === 1 ? 1 : 0.9} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Derniers imports</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                {summary.recent_imports.length === 0 ? (
                  <EmptyState icon={FileSpreadsheet} title="Aucun import realise pour le moment." />
                ) : (
                  <ul className="divide-y divide-border">
                    {summary.recent_imports.map((imp) => (
                      <li
                        key={imp.id}
                        className="flex items-center justify-between gap-3 py-2.5 text-sm transition-colors hover:bg-muted/60"
                      >
                        <div className="flex items-center gap-2.5">
                          <FileSpreadsheet className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                          <div>
                            <p className="font-medium text-foreground">{imp.file_name}</p>
                            <p className="text-xs text-muted-foreground">
                              {imp.entity_type} — {imp.rows_imported}/{imp.rows_total} lignes importees
                            </p>
                          </div>
                        </div>
                        <span className="shrink-0 text-xs text-muted-foreground">
                          {new Date(imp.started_at).toLocaleDateString("fr-FR")}
                        </span>
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          </div>

          <Card className="mt-6">
            <CardHeader>
              <CardTitle>Dernieres recommandations</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              {summary.recent_recommendations.length === 0 ? (
                <EmptyState
                  icon={Sparkles}
                  title="Aucun calcul realise pour le moment."
                  description='Lancez votre premier calcul depuis "Nouveau calcul".'
                />
              ) : (
                <ul className="divide-y divide-border">
                  {summary.recent_recommendations.map((rec) => (
                    <li
                      key={rec.run_id}
                      className="flex items-center justify-between gap-3 py-2.5 text-sm transition-colors hover:bg-muted/60"
                    >
                      <div className="flex items-center gap-3">
                        <StatusBadge status={rec.status} />
                        <span className="text-muted-foreground">{rec.message}</span>
                      </div>
                      <Link
                        to={`/resultats/${rec.run_id}`}
                        className="flex items-center gap-1 text-accent-foreground hover:underline"
                      >
                        Voir le detail
                        <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
