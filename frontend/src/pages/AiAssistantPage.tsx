import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle, Loader2, Search, Sparkles } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { interpretText, createRecommendation } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { AiInterpretResponse, RecommendationRequest } from "@/types/api";

const MAX_LENGTH = 2000;
const PLACEHOLDER =
  'Ex : "Avenue de 7 m de largeur, mats de 10 m espaces de 30 m, eclairage 3000 K, ' +
  'environ 19 500 lm, puissance maximale 140 W, tension nominale 48 V, courant nominal 1050 mA, driver DALI."';

type ManualValues = Record<string, string>;

export default function AiAssistantPage() {
  const navigate = useNavigate();

  const [text, setText] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);
  const [result, setResult] = useState<AiInterpretResponse | null>(null);
  const [manualValues, setManualValues] = useState<ManualValues>({});
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  const handleAnalyze = async () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setAnalyzing(true);
    setAnalyzeError(null);
    setSearchError(null);
    setResult(null);
    setManualValues({});
    try {
      const r = await interpretText(trimmed);
      setResult(r);
    } catch (err) {
      setAnalyzeError(extractErrorMessage(err));
    } finally {
      setAnalyzing(false);
    }
  };

  const buildPayload = (): RecommendationRequest | null => {
    if (!result) return null;
    const payload: Record<string, unknown> = {};
    for (const field of result.fields) {
      payload[field.request_attr] = field.numeric_value ?? field.value;
    }
    for (const missing of result.missing_fields) {
      const raw = manualValues[missing.request_attr];
      if (raw !== undefined && raw.trim() !== "") {
        payload[missing.request_attr] = Number(raw);
      }
    }
    return payload as unknown as RecommendationRequest;
  };

  const missingStillEmpty = result?.missing_fields.some((m) => !manualValues[m.request_attr]?.trim()) ?? false;
  const canSearch = !!result && (result.can_search || !missingStillEmpty);

  const handleSearch = async () => {
    const payload = buildPayload();
    if (!payload) return;
    setSearching(true);
    setSearchError(null);
    try {
      const response = await createRecommendation(payload);
      navigate(`/resultats/${response.run_id}`);
    } catch (err) {
      setSearchError(extractErrorMessage(err));
    } finally {
      setSearching(false);
    }
  };

  return (
    <div>
      <PageHeader
        title="Assistant IA"
        description="Decrivez un besoin d'eclairage public avec vos propres mots. L'IA extrait les exigences depuis le texte ; MAADEN reste seul decideur de la compatibilite, du score et de la conformite, calcules a partir du catalogue en base."
      />

      <Card>
        <CardHeader>
          <CardTitle>Decrire le besoin</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value.slice(0, MAX_LENGTH))}
            rows={5}
            maxLength={MAX_LENGTH}
            placeholder={PLACEHOLDER}
            disabled={analyzing}
            className="w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground placeholder:text-[#9a9fa1] focus-visible:border-secondary focus-visible:outline-none"
          />
          <div className="flex items-center justify-between gap-3">
            <span className="text-xs text-muted-foreground">{text.length}/{MAX_LENGTH}</span>
            <Button onClick={handleAnalyze} disabled={analyzing || !text.trim()}>
              {analyzing ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Comprehension du besoin...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" aria-hidden="true" /> Analyser avec l'IA
                </>
              )}
            </Button>
          </div>
          {analyzeError && (
            <div className="rounded-md border border-warning-bg bg-warning-bg p-3 text-sm text-warning">{analyzeError}</div>
          )}
        </CardContent>
      </Card>

      {result && (
        <div className="mt-6 space-y-4">
          {result.summary && (
            <div className="rounded-md border border-border bg-accent p-3 text-sm">
              <p className="mb-1 flex items-center gap-1.5 font-semibold text-accent-foreground">
                <Sparkles className="h-4 w-4" aria-hidden="true" /> Ce que l'IA a compris
              </p>
              <p className="text-foreground">{result.summary}</p>
            </div>
          )}

          {result.ambiguous_fields.length > 0 && (
            <div className="rounded-md border border-warning-bg bg-warning-bg p-3 text-sm">
              <p className="mb-2 flex items-center gap-1.5 font-semibold text-warning">
                <AlertTriangle className="h-4 w-4" aria-hidden="true" /> Informations ambigues
              </p>
              <ul className="space-y-1 text-foreground">
                {result.ambiguous_fields.map((f, i) => (
                  <li key={i}>
                    &ldquo;{f.source_text}&rdquo; — {f.message}
                  </li>
                ))}
              </ul>
              <p className="mt-2 text-xs text-muted-foreground">Renseignez la valeur exacte manuellement pour lever l'ambiguite.</p>
            </div>
          )}

          {result.fields.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>Exigences extraites du texte</CardTitle>
              </CardHeader>
              <CardContent className="pt-0">
                <ul className="space-y-1.5 text-sm">
                  {result.fields.map((f, i) => (
                    <li key={i} className="flex flex-wrap items-center gap-2">
                      <span className="text-muted-foreground">{f.label} :</span>
                      <span className="font-medium text-foreground">
                        {f.value} {f.unit ?? ""}
                      </span>
                      <Badge variant={f.confidence === "high" ? "success" : f.confidence === "medium" ? "warning" : "default"}>
                        {f.confidence}
                      </Badge>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {result.missing_fields.length > 0 && (
            <Card className="border-warning">
              <CardHeader>
                <CardTitle>Informations manquantes</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 pt-0">
                <p className="text-sm text-muted-foreground">
                  Completez les elements suivants (non deduits du texte) pour lancer la recherche :
                </p>
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  {result.missing_fields.map((m) => (
                    <div key={m.request_attr}>
                      <Label htmlFor={`missing_${m.request_attr}`}>{m.label}</Label>
                      <Input
                        id={`missing_${m.request_attr}`}
                        type="number"
                        className="mt-1"
                        value={manualValues[m.request_attr] ?? ""}
                        onChange={(e) => setManualValues((prev) => ({ ...prev, [m.request_attr]: e.target.value }))}
                      />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="flex flex-col items-start gap-2">
            <Button onClick={handleSearch} disabled={!canSearch || searching}>
              {searching ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> Recherche en cours...
                </>
              ) : (
                <>
                  <Search className="h-4 w-4" aria-hidden="true" /> Rechercher les configurations compatibles
                </>
              )}
            </Button>
            {searchError && <p className="text-sm text-destructive">{searchError}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
