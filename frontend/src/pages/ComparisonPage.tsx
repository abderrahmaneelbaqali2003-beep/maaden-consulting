import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { getRecommendation } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { RecommendationResponse } from "@/types/api";

export default function ComparisonPage() {
  const [searchParams] = useSearchParams();
  const runId = searchParams.get("run");
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(!!runId);

  useEffect(() => {
    if (!runId) return;
    getRecommendation(Number(runId))
      .then(setData)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, [runId]);

  if (!runId) {
    return (
      <div>
        <PageHeader title="Comparaison" description="Comparez les meilleures configurations d'un calcul." />
        <p className="text-sm text-muted-foreground">
          Aucun calcul selectionne. Lancez un{" "}
          <Link to="/nouveau-calcul" className="text-secondary hover:underline">
            nouveau calcul
          </Link>{" "}
          ou choisissez-en un depuis l'
          <Link to="/historique" className="text-secondary hover:underline">
            historique
          </Link>
          .
        </p>
      </div>
    );
  }

  if (loading) return <p className="text-sm text-muted-foreground">Chargement...</p>;
  if (error)
    return <div className="rounded-md border border-destructive-bg bg-destructive-bg p-4 text-sm text-destructive">{error}</div>;
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
        <TableHeader>
          <TableRow>
            <TableHead>Critere</TableHead>
            {data.recommendations.map((item) => (
              <TableHead key={item.rank}>Configuration n°{item.rank}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell className="font-medium">Score global</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank} className="font-semibold">
                {item.overall_score}/100
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Driver</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank}>
                {item.driver.manufacturer} {item.driver.reference}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Module LED</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank}>
                {item.module.manufacturer} {item.module.reference}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Lentille</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank}>
                {item.lens ? `${item.lens.manufacturer} ${item.lens.reference}` : "Aucune"}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Electrique (/35)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank}>{item.scores.electrical}</TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Flux / CCT (/25)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank}>{item.scores.photometric}</TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Mecanique / optique (/20)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank}>{item.scores.mechanical}</TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Thermique (/10)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank}>{item.scores.thermal}</TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Qualite des donnees (/10)</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank}>{item.scores.data_quality}</TableCell>
            ))}
          </TableRow>
          <TableRow>
            <TableCell className="font-medium">Avertissements</TableCell>
            {data.recommendations.map((item) => (
              <TableCell key={item.rank}>{item.warnings.length}</TableCell>
            ))}
          </TableRow>
        </TableBody>
      </Table>

      <div className="mt-4">
        <Link to={`/resultats/${data.run_id}`} className="text-sm text-secondary hover:underline">
          Voir le detail complet des explications
        </Link>
      </div>
    </div>
  );
}
