import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { History } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { getRecommendationHistory } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { RecommendationResponse } from "@/types/api";

export default function HistoryPage() {
  const [items, setItems] = useState<RecommendationResponse[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    setError(null);
    getRecommendationHistory(page, 10)
      .then((res) => {
        setItems(res.items);
        setTotalPages(res.total_pages || 1);
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [page]);

  return (
    <div>
      <PageHeader title="Historique" description="Anciens calculs de recommandation et leur validation." />

      {loading && <LoadingState rows={5} />}
      {!loading && error && <ErrorState message={error} onRetry={load} />}

      {!loading && !error && items.length === 0 && (
        <EmptyState icon={History} title="Aucun calcul realise pour le moment." />
      )}

      {!loading && !error && items.length > 0 && (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Statut</TableHead>
                <TableHead>Message</TableHead>
                <TableHead>Meilleure configuration</TableHead>
                <TableHead>Validation</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((run) => {
                const top = run.recommendations[0];
                return (
                  <TableRow key={run.run_id}>
                    <TableCell>{new Date(run.created_at).toLocaleString("fr-FR")}</TableCell>
                    <TableCell>
                      <StatusBadge status={run.status} />
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-sm text-muted-foreground">
                      {run.message}
                    </TableCell>
                    <TableCell className="text-sm">
                      {top ? `${top.driver.reference} / ${top.module.reference}` : "—"}
                    </TableCell>
                    <TableCell className="text-sm">
                      {top?.validation_status === "validated" && (
                        <span className="text-success">Validee</span>
                      )}
                      {top?.validation_status === "rejected" && (
                        <span className="text-destructive">Rejetee</span>
                      )}
                      {(!top || top.validation_status === "pending" || !top.validation_status) && (
                        <span className="text-muted-foreground">En attente</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Link to={`/resultats/${run.run_id}`} className="text-sm text-accent-foreground hover:underline">
                        Voir
                      </Link>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>

          <div className="mt-3 flex items-center justify-between text-sm">
            <span className="text-muted-foreground">
              Page {page} / {totalPages}
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Precedent
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Suivant
              </Button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
