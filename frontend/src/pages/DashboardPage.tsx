import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Cpu, Lightbulb, Aperture, Percent } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/StatusBadge";
import { getDashboardSummary } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { DashboardSummary } from "@/types/api";

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType;
  label: string;
  value: string | number;
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 pt-5">
        <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-accent text-secondary">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <p className="text-2xl font-semibold text-foreground">{value}</p>
          <p className="text-sm text-muted-foreground">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardSummary()
      .then(setSummary)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-muted-foreground">Chargement du tableau de bord...</p>;
  if (error)
    return (
      <div className="rounded-md border border-destructive-bg bg-destructive-bg p-4 text-sm text-destructive">
        {error}
      </div>
    );
  if (!summary) return null;

  const chartData = [
    { name: "Drivers", total: summary.drivers_count },
    { name: "Modules LED", total: summary.modules_count },
    { name: "Lentilles", total: summary.lenses_count },
  ];

  return (
    <div>
      <PageHeader
        title="Tableau de bord"
        description="Vue d'ensemble du catalogue et des recommandations recentes."
      />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Cpu} label="Drivers actifs" value={summary.drivers_count} />
        <StatCard icon={Lightbulb} label="Modules LED actifs" value={summary.modules_count} />
        <StatCard icon={Aperture} label="Lentilles actives" value={summary.lenses_count} />
        <StatCard
          icon={Percent}
          label={`Taux compatible (${summary.recommendation_runs_count} calculs)`}
          value={`${summary.compatible_rate_percent}%`}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Repartition du catalogue</CardTitle>
          </CardHeader>
          <CardContent className="h-64 pt-0">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} stroke="var(--muted-foreground)" />
                <YAxis tick={{ fontSize: 12 }} stroke="var(--muted-foreground)" allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="total" fill="var(--secondary)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Derniers imports</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            {summary.recent_imports.length === 0 && (
              <p className="text-sm text-muted-foreground">Aucun import realise pour le moment.</p>
            )}
            <ul className="divide-y divide-border">
              {summary.recent_imports.map((imp) => (
                <li key={imp.id} className="flex items-center justify-between py-2 text-sm">
                  <div>
                    <p className="font-medium text-foreground">{imp.file_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {imp.entity_type} — {imp.rows_imported}/{imp.rows_total} lignes importees
                    </p>
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(imp.started_at).toLocaleDateString("fr-FR")}
                  </span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Dernieres recommandations</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          {summary.recent_recommendations.length === 0 && (
            <p className="text-sm text-muted-foreground">
              Aucun calcul realise pour le moment. Lancez votre premier calcul depuis "Nouveau calcul".
            </p>
          )}
          <ul className="divide-y divide-border">
            {summary.recent_recommendations.map((rec) => (
              <li key={rec.run_id} className="flex items-center justify-between py-2.5 text-sm">
                <div className="flex items-center gap-3">
                  <StatusBadge status={rec.status} />
                  <span className="text-muted-foreground">{rec.message}</span>
                </div>
                <Link to={`/resultats/${rec.run_id}`} className="text-secondary hover:underline">
                  Voir le detail
                </Link>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
