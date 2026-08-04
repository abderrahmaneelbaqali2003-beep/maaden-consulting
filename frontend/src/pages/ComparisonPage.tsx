import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { RecommendedBadge } from "@/components/RecommendedBadge";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { cn } from "@/lib/utils";
import { getRecommendation } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { RecommendationItem, RecommendationResponse } from "@/types/api";

function bestColumnClass(item: RecommendationItem) {
  return item.rank === 1 ? "bg-accent/50" : undefined;
}

export default function ComparisonPage() {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run");
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!runId);

  const load = () => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    getRecommendation(Number(runId))
      .then(setData)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [runId]);

  if (!runId) {
    return (
      <div>
        <PageHeader title="Comparaison" description="Comparez les meilleures configurations d'un calcul." />
        <p className="text-sm text-muted-foreground">
          Aucun calcul selectionne. Lancez un{" "}
          <Link to="/nouveau-calcul" className="text-accent-foreground hover:underline">
            nouveau calcul
          </Link>{" "}
          ou choisissez-en un depuis l'
          <Link to="/historique" className="text-accent-foreground hover:underline">
            historique
          </Link>
          .
        </p>
      </div>
    );
  }

  if (loading) return <LoadingState rows={5} />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data) return null;

  return (
    <div>
      <PageHeader
        title="Comparaison des configurations"
        description={`Calcul #${data.run_id} — ${data.message}`}
      />
      <div className="mb-4">
        <StatusBadge status={data.status} />
      </div>

      <Table>
        <TableHeader className="sticky top-0 z-10">
          <TableRow>
            <TableHead className="sticky left-0 z-10 min-w-[180px] bg-[#f1f1ed]">Critere</TableHead>
            {data.recommendations.map((item) => (
              <TableHead key={item.rank} className={cn("min-w-[180px]", bestColumnClass(item))}>
                <div className="flex flex-col gap-1">
                  <span className={item.rank === 1 ? "text-accent-foreground" : undefined}>
                    Configuration n°{item.rank}
                  </span>
                  {item.rank === 1 && <RecommendedBadge className="w-fit" />}
                </div>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Score global</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={cn("font-semibold", bestColumnClass(item))}>
                {item.overall_score}/100
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Driver</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={bestColumnClass(item)}>
                {item.driver.manufacturer} {item.driver.reference}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Module LED</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={bestColumnClass(item)}>
                {item.module.manufacturer} {item.module.reference}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Lentille</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={bestColumnClass(item)}>
                {item.lens ? `${item.lens.manufacturer} ${item.lens.reference}` : "Aucune"}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Electrique (/35)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={bestColumnClass(item)}>
                {item.scores.electrical}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Flux / CCT (/25)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={bestColumnClass(item)}>
                {item.scores.photometric}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Mecanique / optique (/20)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={bestColumnClass(item)}>
                {item.scores.mechanical}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Thermique (/10)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={bestColumnClass(item)}>
                {item.scores.thermal}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Qualite des donnees (/10)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={bestColumnClass(item)}>
                {item.scores.data_quality}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="sticky left-0 z-10 bg-card font-medium">Avertissements</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className={bestColumnClass(item)}>
                {item.warnings.length}
              </TableCell>
            ))}
          </TableRow>
        </TableBody>
      </Table>

      <div className="mt-4">
        <Link to={`/resultats/${data.run_id}`} className="text-sm text-accent-foreground hover:underline">
          Voir le detail complet des explications
        </Link>
      </div>
    </div>
  );
}
