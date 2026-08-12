import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Check, ChevronDown, ChevronUp, PlusCircle, X } from "lucide-react";
import { PageHeader } from "@/components/PageHeader";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  listRequirements,
  updateRequirement,
  addManualRequirement,
  confirmRequirements,
  runStudy,
} from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { ExtractedRequirementOut } from "@/types/api";

const STATUS_LABEL: Record<string, { label: string; variant: "success" | "warning" | "info" | "destructive" | "default" }> = {
  detected: { label: "Detectee", variant: "info" },
  confirmed: { label: "Confirmee", variant: "success" },
  modified: { label: "Modifiee", variant: "success" },
  manual: { label: "Saisie manuelle", variant: "success" },
  ignored: { label: "Ignoree", variant: "default" },
};

const CONFIDENCE_LABEL: Record<string, string> = { high: "Confiance elevee", medium: "Confiance moyenne", low: "Confiance faible" };

// Perimetre volontairement restreint (a la demande du consultant) aux seules grandeurs
// necessaires pour lancer l'etude : flux, CCT, puissance, tension nominale, courant,
// protocole de commande, geometrie routiere. Le couple (scope, field_name) doit
// correspondre EXACTEMENT a REQUEST_FIELD_MAP cote backend (app/cps/service.py) --
// d'ou ce menu deroulant plutot qu'une saisie de texte pour le nom du champ.
const MAPPABLE_FIELDS: { scope: string; field_name: string; label: string; unit: string | null }[] = [
  { scope: "luminaire", field_name: "required_flux_lm", label: "Flux lumineux (lumen)", unit: "lm" },
  { scope: "luminaire", field_name: "cct_k", label: "Temperature de couleur (CCT)", unit: "K" },
  { scope: "luminaire", field_name: "max_power_w", label: "Puissance maximale", unit: "W" },
  { scope: "module", field_name: "voltage_nominal_v", label: "Tension nominale", unit: "V" },
  { scope: "module", field_name: "current_nominal_ma", label: "Courant nominal", unit: "mA" },
  { scope: "driver", field_name: "protocol", label: "Protocole de commande (DALI, DALI-2, D4i, 0-10V, 1-10V)", unit: null },
  { scope: "road", field_name: "pole_height_m", label: "Geometrie routiere — Hauteur du mat", unit: "m" },
  { scope: "road", field_name: "pole_spacing_m", label: "Geometrie routiere — Espacement des mats", unit: "m" },
  { scope: "road", field_name: "road_width_m", label: "Geometrie routiere — Largeur de chaussee", unit: "m" },
  { scope: "road", field_name: "road_length_m", label: "Geometrie routiere — Longueur du troncon", unit: "m" },
  { scope: "system", field_name: "layout_type", label: "Geometrie routiere — Type d'implantation", unit: null },
];

function RequirementRow({ requirement, validatorName, onChanged }: { requirement: ExtractedRequirementOut; validatorName: string; onChanged: () => void }) {
  const [showSource, setShowSource] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState(requirement.raw_value);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const status = STATUS_LABEL[requirement.validation_status] ?? { label: requirement.validation_status, variant: "default" as const };

  const runAction = async (action: "confirm" | "modify" | "ignore", value?: string) => {
    if (!validatorName.trim()) {
      setError("Renseignez le nom du consultant en haut de page avant de valider une exigence.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await updateRequirement(requirement.project_id, requirement.id, {
        action,
        validated_value: value ?? null,
        validated_by: validatorName.trim(),
      });
      setEditing(false);
      onChanged();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <li className="rounded-md border border-border p-3">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-foreground">
            {requirement.field_name} <span className="text-muted-foreground">({requirement.scope})</span>
          </p>
          <p className="text-sm text-foreground">
            {requirement.operator} {requirement.validated_value ?? requirement.raw_value} {requirement.unit ?? ""}
          </p>
          <p className="text-xs text-muted-foreground">
            {requirement.source_page ? `Page ${requirement.source_page}` : "Saisie manuelle"}
            {requirement.extraction_confidence && ` — ${CONFIDENCE_LABEL[requirement.extraction_confidence] ?? requirement.extraction_confidence}`}
          </p>
        </div>
        <Badge variant={status.variant}>{status.label}</Badge>
      </div>

      {requirement.source_excerpt && (
        <button type="button" onClick={() => setShowSource((v) => !v)} className="mt-2 flex items-center gap-1 text-xs font-medium text-accent-foreground hover:underline">
          {showSource ? <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" /> : <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />}
          {showSource ? "Masquer la source" : "Voir la source"}
        </button>
      )}
      {showSource && requirement.source_excerpt && (
        <p className="mt-2 rounded bg-muted p-2 text-sm text-muted-foreground">{requirement.source_excerpt}</p>
      )}

      {editing && (
        <div className="mt-2 flex items-center gap-2">
          <Input value={editValue} onChange={(e) => setEditValue(e.target.value)} className="h-8 max-w-[160px]" />
          <Button size="sm" disabled={busy} onClick={() => runAction("modify", editValue)}>
            Enregistrer
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setEditing(false)}>
            Annuler
          </Button>
        </div>
      )}

      {!editing && (
        <div className="mt-2 flex flex-wrap gap-2">
          {requirement.validation_status !== "confirmed" && (
            <Button size="sm" disabled={busy} onClick={() => runAction("confirm")}>
              <Check className="h-3.5 w-3.5" aria-hidden="true" /> Confirmer
            </Button>
          )}
          <Button size="sm" variant="outline" disabled={busy} onClick={() => setEditing(true)}>
            Modifier
          </Button>
          {requirement.validation_status !== "ignored" && (
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => runAction("ignore")}>
              <X className="h-3.5 w-3.5" aria-hidden="true" /> Ignorer
            </Button>
          )}
        </div>
      )}

      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
    </li>
  );
}

function AddManualRequirementForm({ projectId, validatorName, onAdded }: { projectId: number; validatorName: string; onAdded: () => void }) {
  const [open, setOpen] = useState(false);
  const [selectedKey, setSelectedKey] = useState(`${MAPPABLE_FIELDS[0].scope}|${MAPPABLE_FIELDS[0].field_name}`);
  const [value, setValue] = useState("");
  const [unit, setUnit] = useState(MAPPABLE_FIELDS[0].unit ?? "");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const selectedField = MAPPABLE_FIELDS.find((f) => `${f.scope}|${f.field_name}` === selectedKey)!;

  const handleAdd = async () => {
    if (!validatorName.trim()) {
      setError("Renseignez le nom du consultant en haut de page.");
      return;
    }
    if (!value.trim()) {
      setError("La valeur est obligatoire.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await addManualRequirement(projectId, {
        category: "manual", scope: selectedField.scope, field_name: selectedField.field_name, operator: "==",
        value: value.trim(), unit: unit.trim() || null, validated_by: validatorName.trim(),
      });
      setValue("");
      setOpen(false);
      onAdded();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) {
    return (
      <Button variant="outline" size="sm" onClick={() => setOpen(true)}>
        <PlusCircle className="h-4 w-4" aria-hidden="true" /> Ajouter une exigence manuelle
      </Button>
    );
  }

  return (
    <div className="rounded-md border border-border p-3">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <div>
          <Label htmlFor="manual_field_select">Champ a renseigner</Label>
          <select
            id="manual_field_select"
            value={selectedKey}
            onChange={(e) => {
              setSelectedKey(e.target.value);
              const field = MAPPABLE_FIELDS.find((f) => `${f.scope}|${f.field_name}` === e.target.value);
              setUnit(field?.unit ?? "");
            }}
            className="mt-1 flex h-10 w-full rounded-md border border-input bg-card px-3 text-sm"
          >
            {MAPPABLE_FIELDS.map((f) => (
              <option key={`${f.scope}|${f.field_name}`} value={`${f.scope}|${f.field_name}`}>
                {f.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <Label htmlFor="manual_value">Valeur</Label>
          <Input id="manual_value" value={value} onChange={(e) => setValue(e.target.value)} className="mt-1" />
        </div>
        <div>
          <Label htmlFor="manual_unit">Unite</Label>
          <Input id="manual_unit" value={unit} onChange={(e) => setUnit(e.target.value)} className="mt-1" placeholder="Optionnel" />
        </div>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Ce champ alimentera directement le calculateur et le moteur de recommandation MAADEN.
      </p>
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      <div className="mt-3 flex gap-2">
        <Button size="sm" disabled={submitting} onClick={handleAdd}>
          {submitting ? "Ajout..." : "Ajouter"}
        </Button>
        <Button size="sm" variant="ghost" onClick={() => setOpen(false)}>
          Annuler
        </Button>
      </div>
    </div>
  );
}

export default function ProjectRequirementsPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [requirements, setRequirements] = useState<ExtractedRequirementOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [validatorName, setValidatorName] = useState("");
  const [confirmError, setConfirmError] = useState<string | null>(null);
  const [studyError, setStudyError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [launching, setLaunching] = useState(false);
  const [readyForStudy, setReadyForStudy] = useState(false);

  const load = () => {
    if (!projectId) return;
    setLoading(true);
    setError(null);
    listRequirements(Number(projectId))
      .then(setRequirements)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  };

  useEffect(load, [projectId]);

  const pendingCount = requirements.filter((r) => r.validation_status === "detected").length;

  const handleConfirmAll = async () => {
    if (!projectId) return;
    setConfirming(true);
    setConfirmError(null);
    try {
      await confirmRequirements(Number(projectId));
      setReadyForStudy(true);
    } catch (err) {
      setConfirmError(extractErrorMessage(err));
    } finally {
      setConfirming(false);
    }
  };

  const handleRunStudy = async () => {
    if (!projectId) return;
    setLaunching(true);
    setStudyError(null);
    try {
      await runStudy(Number(projectId), validatorName.trim() || undefined);
      navigate(`/projets/${projectId}/scenarios`);
    } catch (err) {
      setStudyError(extractErrorMessage(err));
    } finally {
      setLaunching(false);
    }
  };

  if (loading) return <LoadingState rows={5} />;
  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div>
      <Link to={`/projets/${projectId}`} className="mb-3 flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Retour au projet
      </Link>

      <PageHeader title="Exigences detectees dans le CPS" description="Verifiez, confirmez ou modifiez chaque exigence avant de lancer l'etude." />

      <div className="mb-4 max-w-xs">
        <Label htmlFor="validator_name">Nom du consultant</Label>
        <Input id="validator_name" value={validatorName} onChange={(e) => setValidatorName(e.target.value)} className="mt-1" placeholder="Ex: Jean Dupont" />
      </div>

      {requirements.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Aucune exigence exploitable detectee. Importez un CPS depuis la page projet, ou ajoutez des exigences manuellement.
        </p>
      ) : (
        <ul className="space-y-3">
          {requirements.map((r) => (
            <RequirementRow key={r.id} requirement={r} validatorName={validatorName} onChanged={load} />
          ))}
        </ul>
      )}

      <div className="mt-4">
        <AddManualRequirementForm projectId={Number(projectId)} validatorName={validatorName} onAdded={load} />
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Lancer l'etude</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
          <p className="text-sm text-muted-foreground">
            {pendingCount > 0
              ? `${pendingCount} exigence(s) detectee(s) restent a traiter (confirmer, modifier ou ignorer).`
              : "Toutes les exigences ont ete traitees."}
          </p>
          <div className="flex flex-wrap gap-3">
            <Button variant="outline" onClick={handleConfirmAll} disabled={confirming}>
              {confirming ? "Verification..." : "Confirmer les exigences du projet"}
            </Button>
            <Button onClick={handleRunStudy} disabled={launching}>
              {launching ? "Lancement..." : "Lancer l'etude MAADEN"}
            </Button>
          </div>
          {confirmError && <p className="text-sm text-destructive">{confirmError}</p>}
          {readyForStudy && !confirmError && <p className="text-sm text-success">Exigences confirmees, vous pouvez lancer l'etude.</p>}
          {studyError && <p className="text-sm text-destructive">{studyError}</p>}
        </CardContent>
      </Card>
    </div>
  );
}
