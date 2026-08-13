import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { addManualRequirement, rerunPreliminaryStudy } from "@/api/endpoints";
import { extractErrorMessage } from "@/api/client";
import type { CpsAnalysisResponse, MissingFieldOut } from "@/types/api";

/** Formulaire de completion rapide des champs obligatoires manquants, partage entre le
 * mode CPS et le mode "Decrire mon besoin" (assistant IA) : les deux relancent la meme
 * pre-analyse une fois les champs completes (aucune logique dupliquee cote frontend,
 * miroir du backend qui reutilise `CpsService`/`CpsAnalysisService` pour les deux). */
export function MissingFieldsForm({
  projectId, missingFields, onCompleted,
}: {
  projectId: number; missingFields: MissingFieldOut[]; onCompleted: (result: CpsAnalysisResponse) => void;
}) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    const entries = missingFields.map((f) => ({ field: f.field, value: (values[f.field] ?? "").trim() }));
    if (entries.some((e) => !e.value)) {
      setError("Renseignez toutes les valeurs pour relancer l'analyse.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      for (const entry of entries) {
        await addManualRequirement(projectId, {
          category: "manual",
          scope: entry.field === "protocol" ? "driver" : entry.field.startsWith("required_") || entry.field === "max_power_w" ? "luminaire" : "module",
          field_name: entry.field === "required_cct_k" ? "cct_k" : entry.field,
          value: entry.value,
          validated_by: "Consultant",
        });
      }
      const result = await rerunPreliminaryStudy(projectId);
      onCompleted(result);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      {missingFields.map((f) => (
        <div key={f.field} className="max-w-xs">
          <Label htmlFor={`missing_${f.field}`}>{f.label}</Label>
          <Input
            id={`missing_${f.field}`}
            value={values[f.field] ?? ""}
            onChange={(e) => setValues((v) => ({ ...v, [f.field]: e.target.value }))}
            className="mt-1"
          />
        </div>
      ))}
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button size="sm" onClick={handleSubmit} disabled={submitting}>
        {submitting ? "Relance..." : "Relancer l'analyse"}
      </Button>
    </div>
  );
}
