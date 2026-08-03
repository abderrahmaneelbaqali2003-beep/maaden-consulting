import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { CheckCircle2, XCircle, AlertTriangle, ArrowLeft } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { getRecommendation, validateRecommendation, rejectRecommendation } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { RecommendationItem, RecommendationResponse } from "@/types/api";

function ScoreBar({ label, value, max }: { label: string; value: number; max: number }) {
  const percent = Math.max(0, Math.min(100, (value / max) * 100));
  return (
    <div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span>
          {value}/{max}
        </span>
      </div>
      <div className="mt-1 h-2 w-full rounded-full bg-muted">
        <div className="h-2 rounded-full bg-secondary" style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
}

function ConfigurationCard({ item }: { item: RecommendationItem }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>
            Configuration n°{item.rank} — score {item.overall_score}/100
          </CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          <div className="rounded-md border border-border p-3">
            <p className="text-xs font-medium uppercase text-muted-foreground">Driver</p>
            <p className="text-sm font-semibold">{item.driver.manufacturer}</p>
            <p className="text-sm text-muted-foreground">{item.driver.reference}</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="text-xs font-medium uppercase text-muted-foreground">Module LED</p>
            <p className="text-sm font-semibold">{item.module.manufacturer}</p>
            <p className="text-sm text-muted-foreground">{item.module.reference}</p>
          </div>
          <div className="rounded-md border border-border p-3">
            <p className="text-xs font-medium uppercase text-muted-foreground">Lentille</p>
            {item.lens ? (
              <>
                <p className="text-sm font-semibold">{item.lens.manufacturer}</p>
                <p className="text-sm text-muted-foreground">{item.lens.reference}</p>
              </>
            ) : (
              <p className="text-sm text-warning">Aucune lentille trouvee — a completer manuellement</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <ScoreBar label="Electrique" value={item.scores.electrical} max={35} />
          <ScoreBar label="Flux / CCT" value={item.scores.photometric} max={25} />
          <ScoreBar label="Mecanique / optique" value={item.scores.mechanical} max={20} />
          <ScoreBar label="Thermique" value={item.scores.thermal} max={10} />
          <ScoreBar label="Qualite des donnees" value={item.scores.data_quality} max={10} />
        </div>

        <p className="text-sm text-foreground">{item.explanation}</p>

        {item.validated_rules.length > 0 && (
          <div>
            <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-success">
              <CheckCircle2 className="h-4 w-4" /> Raisons techniques
            </p>
            <ul className="ml-6 list-disc space-y-0.5 text-sm text-muted-foreground">
              {item.validated_rules.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          </div>
        )}

        {item.warnings.length > 0 && (
          <div>
            <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-warning">
              <AlertTriangle className="h-4 w-4" /> Avertissements
            </p>
            <ul className="ml-6 list-disc space-y-0.5 text-sm text-muted-foreground">
              {item.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {item.blocking_reasons.length > 0 && (
          <div>
            <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-destructive">
              <XCircle className="h-4 w-4" /> Raisons de refus
            </p>
            <ul className="ml-6 list-disc space-y-0.5 text-sm text-muted-foreground">
              {item.blocking_reasons.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function ResultsPage() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState<RecommendationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const load = () => {
    if (!runId) return;
    setLoading(true);
    getRecommendation(Number(runId))
      .then(setData)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [runId]);

  const handleValidate = async () => {
    if (!runId) return;
    await validateRecommendation(Number(runId));
    setActionMessage("Configuration validee.");
    load();
  };

  const handleReject = async () => {
    if (!runId) return;
    await rejectRecommendation(Number(runId));
    setActionMessage("Configuration rejetee.");
    load();
  };

  if (loading) return <p className="text-sm text-muted-foreground">Chargement des resultats...</p>;
  if (error)
    return <div className="rounded-md border border-destructive-bg bg-destructive-bg p-4 text-sm text-destructive">{error}</div>;
  if (!data) return null;

  return (
    <div>
      <button
        onClick={() => navigate(-1)}
        className="mb-3 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" /> Retour
      </button>

      <PageHeader title="Resultats de la recommandation" description={data.message} />

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <StatusBadge status={data.status} />
        {data.recommendations.length > 1 && (
          <Link to={`/comparaison?run=${data.run_id}`} className="text-sm text-secondary hover:underline">
            Comparer les {data.recommendations.length} configurations
          </Link>
        )}
        {actionMessage && <span className="text-sm text-success">{actionMessage}</span>}
      </div>

      {data.blocking_reasons.length > 0 && (
        <Card className="mb-6 border-destructive-bg">
          <CardContent className="pt-5">
            <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-destructive">
              <XCircle className="h-4 w-4" /> Raisons du blocage
            </p>
            <ul className="ml-6 list-disc space-y-0.5 text-sm text-foreground">
              {data.blocking_reasons.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
            {data.suggestions.length > 0 && (
              <>
                <p className="mt-3 mb-1 text-sm font-semibold text-foreground">Suggestions</p>
                <ul className="ml-6 list-disc space-y-0.5 text-sm text-muted-foreground">
                  {data.suggestions.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </>
            )}
          </CardContent>
        </Card>
      )}

      <div className="space-y-6">
        {data.recommendations.map((item) => (
          <ConfigurationCard key={item.rank} item={item} />
        ))}
      </div>

      {data.recommendations.length > 0 && (
        <div className="mt-6 flex gap-3">
          <Button variant="default" onClick={handleValidate}>
            <CheckCircle2 className="h-4 w-4" /> Valider la meilleure configuration
          </Button>
          <Button variant="outline" onClick={handleReject}>
            <XCircle className="h-4 w-4" /> Rejeter
          </Button>
        </div>
      )}

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Composants rejetes</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-3 gap-4 pt-0 text-sm">
          <div>
            <p className="text-2xl font-semibold text-foreground">{data.rejected_summary.drivers_rejected}</p>
            <p className="text-muted-foreground">Drivers rejetes</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-foreground">{data.rejected_summary.modules_rejected}</p>
            <p className="text-muted-foreground">Modules rejetes</p>
          </div>
          <div>
            <p className="text-2xl font-semibold text-foreground">{data.rejected_summary.lenses_rejected}</p>
            <p className="text-muted-foreground">Lentilles rejetees</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
