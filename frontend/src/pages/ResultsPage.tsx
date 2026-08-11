import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  ArrowDown,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { RecommendedBadge } from "@/components/RecommendedBadge";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { TechnicalCalculationsSection } from "@/features/configurator/TechnicalCalculationsSection";
import { cn } from "@/lib/utils";
import { getRecommendation, validateRecommendation, rejectRecommendation } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type {
  ComponentRef,
  DocumentaryAnalysisOut,
  DocumentaryConfidence,
  EvidenceOut,
  RecommendationItem,
  RecommendationResponse,
} from "@/types/api";

const CONFIDENCE_CONFIG: Record<
  DocumentaryConfidence,
  { label: string; variant: "success" | "warning" | "info" | "default"; icon: typeof ShieldCheck }
> = {
  high: { label: "Elevee", variant: "success", icon: ShieldCheck },
  medium: { label: "Moyenne", variant: "warning", icon: ShieldQuestion },
  low: { label: "Faible", variant: "info", icon: ShieldAlert },
  insufficient_evidence: { label: "Preuve insuffisante", variant: "default", icon: ShieldAlert },
};

const EVIDENCE_CATEGORY_LABELS: Record<string, string> = {
  road_lighting: "Eclairage routier",
  photometric: "Performance photometrique",
  driver_standard: "Securite driver LED",
  module_standard: "Performance / securite module LED",
  luminaire_standard: "Securite du luminaire",
  lens_photometry: "Photometrie de la lentille",
  smart_lighting: "Commande numerique (DALI / D4i)",
  safety: "Securite",
  performance: "Performance",
  measurement: "Mesure",
};

function EvidenceRow({ item }: { item: EvidenceOut }) {
  const [open, setOpen] = useState(false);
  const relevancePercent = Math.round(Math.min(1, Math.max(0, item.relevance_score)) * 100);

  return (
    <li className="rounded-md border border-border p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-foreground">{item.document}</p>
          <p className="text-xs text-muted-foreground">
            {item.section ? `Section : ${item.section}` : "Section non identifiee"}
            {item.page ? ` — Page ${item.page}` : ""}
          </p>
        </div>
        <span className="shrink-0 text-xs font-medium text-accent-foreground">Pertinence : {relevancePercent}%</span>
      </div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="mt-2 flex items-center gap-1 text-xs font-medium text-accent-foreground hover:underline"
      >
        {open ? <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" /> : <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />}
        {open ? "Masquer le passage" : "Afficher le passage"}
      </button>
      {open && <p className="mt-2 text-sm text-muted-foreground">{item.summary}</p>}
    </li>
  );
}

function DocumentaryAnalysisSection({ analysis }: { analysis: DocumentaryAnalysisOut }) {
  const confidenceConfig = CONFIDENCE_CONFIG[analysis.confidence] ?? CONFIDENCE_CONFIG.insufficient_evidence;
  const ConfidenceIcon = confidenceConfig.icon;
  const uniqueByCategory = Array.from(new Map(analysis.evidence.map((e) => [e.category, e])).values());

  return (
    <div className="space-y-4 border-t border-border pt-4">
      {uniqueByCategory.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold text-foreground">References normatives</p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {uniqueByCategory.map((item) => (
              <div key={item.category} className="rounded-md bg-muted px-3 py-2 text-sm">
                <p className="font-medium text-foreground">{EVIDENCE_CATEGORY_LABELS[item.category] ?? item.category}</p>
                <p className="text-xs text-muted-foreground">{item.document}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {analysis.evidence.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold text-foreground">Justification documentaire</p>
          <ul className="space-y-2">
            {analysis.evidence.map((item, i) => (
              <EvidenceRow key={i} item={item} />
            ))}
          </ul>
        </div>
      )}

      {analysis.missing_evidence.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-semibold text-foreground">Validations restantes</p>
          <ul className="space-y-1">
            {analysis.missing_evidence.map((m, i) => (
              <li key={i} className="flex items-center gap-1.5 text-sm text-warning">
                <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden="true" /> {m}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <p className="mb-2 text-sm font-semibold text-foreground">Confiance documentaire</p>
        <Badge variant={confidenceConfig.variant}>
          <ConfidenceIcon className="h-3.5 w-3.5" aria-hidden="true" /> {confidenceConfig.label.toUpperCase()}
        </Badge>
      </div>
    </div>
  );
}

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

function ComponentBlock({
  label,
  data,
  emptyText,
}: {
  label: string;
  data: ComponentRef | null;
  emptyText?: string;
}) {
  return (
    <div className="flex-1 rounded-md border border-border p-3">
      <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
      {data ? (
        <>
          <p className="text-sm font-semibold text-foreground">{data.manufacturer}</p>
          <p className="text-sm text-muted-foreground">{data.reference}</p>
        </>
      ) : (
        <p className="text-sm text-warning">{emptyText}</p>
      )}
    </div>
  );
}

function FlowArrow() {
  return (
    <div className="flex items-center justify-center text-muted-foreground" aria-hidden="true">
      <ArrowDown className="h-4 w-4 sm:hidden" />
      <ArrowRight className="hidden h-4 w-4 sm:block" />
    </div>
  );
}

function ConfigurationCard({ item, isBest }: { item: RecommendationItem; isBest: boolean }) {
  return (
    <Card
      className={cn(isBest && "border-secondary shadow-[0_6px_18px_rgba(201,154,50,0.10)]")}
    >
      <CardHeader className="flex flex-row items-center justify-between gap-3">
        <CardTitle>Configuration n°{item.rank}</CardTitle>
        <div className="flex items-center gap-2">
          {isBest && <RecommendedBadge />}
          <span className={cn("text-sm font-semibold", isBest ? "text-lg text-secondary" : "text-muted-foreground")}>
            {item.overall_score}/100
          </span>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-0">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-stretch">
          <ComponentBlock label="Driver" data={item.driver} />
          <FlowArrow />
          <ComponentBlock label="Module LED" data={item.module} />
          <FlowArrow />
          <ComponentBlock
            label="Lentille"
            data={item.lens}
            emptyText="Aucune lentille trouvee — a completer manuellement"
          />
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <ScoreBar label="Electrique" value={item.scores.electrical} max={35} />
          <ScoreBar label="Flux / CCT" value={item.scores.photometric} max={25} />
          <ScoreBar label="Mecanique / optique" value={item.scores.mechanical} max={20} />
          <ScoreBar label="Thermique" value={item.scores.thermal} max={10} />
          <ScoreBar label="Qualite des donnees" value={item.scores.data_quality} max={10} />
        </div>

        {item.technical_calculations && (
          <TechnicalCalculationsSection calculations={item.technical_calculations} />
        )}

        <p className="text-sm text-foreground">{item.explanation}</p>

        {item.validated_rules.length > 0 && (
          <div>
            <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-success">
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Raisons techniques
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
              <AlertTriangle className="h-4 w-4" aria-hidden="true" /> Avertissements
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
              <XCircle className="h-4 w-4" aria-hidden="true" /> Raisons de refus
            </p>
            <ul className="ml-6 list-disc space-y-0.5 text-sm text-muted-foreground">
              {item.blocking_reasons.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          </div>
        )}

        {item.documentary_analysis && <DocumentaryAnalysisSection analysis={item.documentary_analysis} />}
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
  const [actionError, setActionError] = useState<string | null>(null);

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

  const handleValidate = async () => {
    if (!runId) return;
    if (!window.confirm("Confirmer la validation de la meilleure configuration ?")) return;
    setActionError(null);
    try {
      await validateRecommendation(Number(runId));
      setActionMessage("Configuration validee.");
      load();
    } catch (err) {
      setActionError(extractErrorMessage(err));
    }
  };

  const handleReject = async () => {
    if (!runId) return;
    if (!window.confirm("Confirmer le rejet de cette recommandation ?")) return;
    setActionError(null);
    try {
      await rejectRecommendation(Number(runId));
      setActionMessage("Configuration rejetee.");
      load();
    } catch (err) {
      setActionError(extractErrorMessage(err));
    }
  };

  if (loading) return <LoadingState rows={5} />;
  if (error) return <ErrorState message={error} onRetry={load} />;
  if (!data) return null;

  return (
    <div>
      <button
        onClick={() => navigate(-1)}
        className="mb-3 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Retour
      </button>

      <PageHeader title="Resultats de la recommandation" description={data.message} />

      <div className="mb-6 flex flex-wrap items-center gap-4">
        <StatusBadge status={data.status} />
        {data.recommendations.length > 1 && (
          <Link to={`/comparaison?run=${data.run_id}`} className="text-sm text-accent-foreground hover:underline">
            Comparer les {data.recommendations.length} configurations
          </Link>
        )}
        {actionMessage && <span className="text-sm text-success">{actionMessage}</span>}
      </div>

      {actionError && (
        <div className="mb-6">
          <ErrorState title="Action impossible" message={actionError} />
        </div>
      )}

      {data.blocking_reasons.length > 0 && (
        <Card className="mb-6 border-destructive-bg">
          <CardContent className="pt-5">
            <p className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-destructive">
              <XCircle className="h-4 w-4" aria-hidden="true" /> Raisons du blocage
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
          <ConfigurationCard key={item.rank} item={item} isBest={item.rank === 1} />
        ))}
      </div>

      {data.recommendations.length > 0 && (
        <div className="mt-6 flex gap-3">
          <Button variant="default" onClick={handleValidate}>
            <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> Valider la meilleure configuration
          </Button>
          <Button variant="destructive" onClick={handleReject}>
            <XCircle className="h-4 w-4" aria-hidden="true" /> Rejeter
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
